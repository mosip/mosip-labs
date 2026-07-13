/**
 * Full GitHub data sync: repos → commits → PRs → reviews → user names.
 */
require('dotenv').config({ path: require('path').join(__dirname, '..', '.env') });
const { syncRepos } = require('../services/syncRepos');
const { syncCommits } = require('../services/commitSyncService');
const { syncPRs } = require('../services/prSyncService');
const { syncReviews } = require('../services/reviewSyncService');
const { backfillMissingUserNames } = require('../services/githubUserService');
const pool = require('../db/dbPool');
const { DELAY_BETWEEN_REPOS_MS } = require('../config/syncConfig');

function parseOrgs() {
  return (process.env.GITHUB_ORG || '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean);
}

async function loadRepos() {
  const result = await pool.query(
    'SELECT github_repo_id, owner, name, full_name FROM repos ORDER BY github_repo_id'
  );
  return result.rows;
}

async function syncAllRepos(orgs) {
  let reposProcessed = 0;
  for (const org of orgs) {
    reposProcessed += await syncRepos(org);
  }
  return reposProcessed;
}

async function syncForAllRepos(label, syncFn) {
  const repos = await loadRepos();
  let processed = 0;
  let total = 0;

  for (let i = 0; i < repos.length; i += 1) {
    const repo = repos[i];
    const repoName = repo.full_name || `${repo.owner}/${repo.name}`;

    try {
      console.log(`[${label} ${i + 1}/${repos.length}] ${repoName}`);
      const count = await syncFn(repo.github_repo_id);
      processed += count;
      console.log(`  done: ${count} ${label}`);
    } catch (error) {
      console.error(`  error for ${repoName}:`, error.message);
    }

    if (i < repos.length - 1) {
      await new Promise((resolve) => setTimeout(resolve, DELAY_BETWEEN_REPOS_MS));
    }
  }

  return { repos_processed: repos.length, total_repos: repos.length, [`${label}_processed`]: processed };
}

async function main() {
  const orgs = parseOrgs();
  if (orgs.length === 0) {
    throw new Error('Set GITHUB_ORG in backend/.env');
  }

  console.log('=== GitHub Activity Tracker – full sync ===');
  console.log(`Organizations: ${orgs.join(', ')}\n`);

  console.log('1/5 Syncing repositories...');
  const reposProcessed = await syncAllRepos(orgs);
  console.log(`Repos result: ${reposProcessed} repos\n`);

  console.log('2/5 Syncing commits...');
  const commitsResult = await syncForAllRepos('commits', syncCommits);
  console.log('Commits result:', commitsResult, '\n');

  console.log('3/5 Syncing pull requests...');
  const prsResult = await syncForAllRepos('prs', syncPRs);
  console.log('PRs result:', prsResult, '\n');

  console.log('4/5 Syncing reviews...');
  const reviewsResult = await syncForAllRepos('reviews', syncReviews);
  console.log('Reviews result:', reviewsResult, '\n');

  console.log('5/5 Backfilling user names...');
  const namesUpdated = await backfillMissingUserNames();
  console.log(`User names updated: ${namesUpdated}\n`);

  console.log('=== Sync complete ===');
}

main()
  .catch((error) => {
    console.error('Sync failed:', error);
    process.exitCode = 1;
  })
  .finally(() => pool.end());
