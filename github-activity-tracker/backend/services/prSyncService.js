const githubClient = require('../utils/githubClient');
const pool = require('../db/dbPool');
const { GITHUB, POSTGRES } = require('../config/errorCodes');
const { isExcludedGitHubLogin } = require('../config/excludedGitHubLogins');
const { upsertGitHubUser } = require('./githubUserService');

const SEARCH_SYNC_CONFIG = {
  pr: {
    searchType: 'pr',
    eventType: 'pr',
    lastSyncColumn: 'last_prs_sync_at',
    countColumn: 'prs_count',
    itemLabel: 'PR',
    incompleteMessage: 'PR sync incomplete; not advancing last_prs_sync_at',
    fetchErrorMessage: 'Error fetching PRs from GitHub API:',
  },
  issue: {
    searchType: 'issue',
    eventType: 'issue',
    lastSyncColumn: 'last_issues_sync_at',
    countColumn: 'issues_count',
    itemLabel: 'issue',
    incompleteMessage: 'Issue sync incomplete; not advancing last_issues_sync_at',
    fetchErrorMessage: 'Error fetching issues from GitHub API:',
  },
};

/**
 * Sync GitHub search items (PRs or issues) for a single repository.
 */
async function syncSearchItems(repoId, syncKind) {
  const config = SEARCH_SYNC_CONFIG[syncKind];
  if (!config) {
    throw new Error(`Unsupported search sync kind: ${syncKind}`);
  }

  if (!repoId) {
    throw new Error(`Repository ID is required for sync${syncKind === 'pr' ? 'PRs' : 'Issues'}`);
  }

  const {
    searchType,
    eventType,
    lastSyncColumn,
    countColumn,
    itemLabel,
    incompleteMessage,
    fetchErrorMessage,
  } = config;

  const repoResult = await pool.query(
    `SELECT owner, name, ${lastSyncColumn} AS last_sync_at FROM repos WHERE github_repo_id = $1`,
    [repoId]
  );

  if (repoResult.rows.length === 0) {
    throw new Error(`Repository with ID ${repoId} not found`);
  }

  const { owner, name, last_sync_at } = repoResult.rows[0];
  if (!owner || !name) {
    throw new Error(`Repository ${repoId} missing owner or name`);
  }

  let sinceDate = null;
  if (last_sync_at) {
    sinceDate = new Date(last_sync_at);
  } else {
    sinceDate = new Date();
    sinceDate.setFullYear(sinceDate.getFullYear() - 1);
  }
  const sinceDateStr = sinceDate.toISOString().split('T')[0];

  const perPage = 100;
  const maxPage = 10;
  let page = 1;
  let totalProcessed = 0;
  let hadProcessingErrors = false;
  let hitSearchCap = false;

  const userIdCache = new Map();

  while (page <= maxPage) {
    try {
      const q = `repo:${owner}/${name} type:${searchType} created:>=${sinceDateStr}`;
      const response = await githubClient.get('/search/issues', {
        params: {
          q,
          sort: 'created',
          order: 'desc',
          per_page: perPage,
          page,
        },
      });

      const items = response.data?.items || [];
      const incompleteResults = response.data?.incomplete_results || false;
      if (!Array.isArray(items) || items.length === 0) {
        break;
      }

      let shouldStopPagination = false;
      for (const item of items) {
        const itemId = item.id;
        const itemNumber = item.number;
        const createdAt = item.created_at;
        const author = item.user;

        if (!author || !author.id) {
          continue;
        }
        if (isExcludedGitHubLogin(author.login)) {
          continue;
        }

        if (sinceDate) {
          const itemDate = new Date(createdAt);
          if (itemDate < sinceDate) {
            shouldStopPagination = true;
            break;
          }
        }

        try {
          const {
            login,
            id: github_user_id,
            avatar_url,
            html_url,
            type,
          } = author;

          let userId = userIdCache.get(github_user_id);
          if (userId === undefined) {
            userId = await upsertGitHubUser({
              github_user_id,
              login,
              avatar_url,
              html_url,
              type,
            });
            userIdCache.set(github_user_id, userId);
          }

          const eventInsert = await pool.query(
            `
              INSERT INTO activity_events (event_type, event_id, repo_id, user_id, html_url, created_at)
              VALUES ($1, $2, $3, $4, $5, $6)
              ON CONFLICT (event_type, event_id)
              DO NOTHING
              RETURNING id
            `,
            [eventType, String(itemId), repoId, userId, item.html_url || null, createdAt]
          );

          if (eventInsert.rowCount === 0) {
            await pool.query(
              `
                INSERT INTO repo_users (repo_id, user_id, first_seen_at, last_seen_at)
                VALUES ($1, $2, $3, $3)
                ON CONFLICT (repo_id, user_id)
                DO UPDATE SET
                  last_seen_at = GREATEST(repo_users.last_seen_at, EXCLUDED.last_seen_at),
                  first_seen_at = LEAST(COALESCE(repo_users.first_seen_at, EXCLUDED.first_seen_at), EXCLUDED.first_seen_at)
              `,
              [repoId, userId, createdAt]
            );

            if (item.html_url) {
              await pool.query(
                `
                  UPDATE activity_events
                  SET html_url = COALESCE(activity_events.html_url, $1)
                  WHERE event_type = $2 AND event_id = $3
                `,
                [item.html_url, eventType, String(itemId)]
              );
            }

            continue;
          }

          await pool.query(
            `
              INSERT INTO repo_users (repo_id, user_id, ${countColumn}, first_seen_at, last_seen_at)
              VALUES ($1, $2, 1, $3, $3)
              ON CONFLICT (repo_id, user_id)
              DO UPDATE SET
                ${countColumn} = repo_users.${countColumn} + 1,
                last_seen_at = GREATEST(repo_users.last_seen_at, EXCLUDED.last_seen_at),
                first_seen_at = LEAST(COALESCE(repo_users.first_seen_at, EXCLUDED.first_seen_at), EXCLUDED.first_seen_at)
            `,
            [repoId, userId, createdAt]
          );

          totalProcessed += 1;
        } catch (itemError) {
          hadProcessingErrors = true;
          if (itemError.code === POSTGRES.UNIQUE_VIOLATION) {
            continue;
          }
          console.error(`Error processing ${itemLabel} #${itemNumber} (id ${itemId}):`, itemError.message);
        }
      }

      if (page === maxPage && items.length === perPage) {
        hitSearchCap = true;
      }
      if (incompleteResults) {
        hitSearchCap = true;
      }

      if (shouldStopPagination || items.length < perPage) {
        break;
      }
      page += 1;
    } catch (apiError) {
      console.error(fetchErrorMessage, apiError.message);
      if (apiError.response) {
        console.error('GitHub API status:', apiError.response.status);
        console.error('GitHub API response:', apiError.response.data);
        if (apiError.response.status === GITHUB.VALIDATION_FAILED) {
          const msg = apiError.response.data?.message || 'Validation Failed';
          const hint =
            'Your token may not have access to this repository, or the repo owner/name may be invalid.';
          const err = new Error(`${msg}. ${hint}`);
          err.statusCode = GITHUB.VALIDATION_FAILED;
          err.githubResponse = apiError.response.data;
          throw err;
        }
      }
      throw apiError;
    }
  }

  if (hadProcessingErrors || hitSearchCap) {
    throw new Error(incompleteMessage);
  }

  await pool.query(
    `UPDATE repos SET ${lastSyncColumn} = NOW() WHERE github_repo_id = $1`,
    [repoId]
  );

  return totalProcessed;
}

/**
 * Sync pull requests for a single repository.
 */
async function syncPRs(repoId) {
  return syncSearchItems(repoId, 'pr');
}

/**
 * Sync GitHub issues for a single repository.
 */
async function syncIssues(repoId) {
  return syncSearchItems(repoId, 'issue');
}

module.exports = {
  syncPRs,
  syncIssues,
};
