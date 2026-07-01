const githubClient = require('../utils/githubClient');
const pool = require('../db/dbPool');

const NAME_FETCH_DELAY_MS = 120;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isBotType(type) {
  return String(type || '').toLowerCase() === 'bot';
}

/**
 * Fetch GitHub profile display name for a login. Returns null when unset or on failure.
 */
async function fetchGitHubUserName(login) {
  if (!login) return null;

  try {
    const { data } = await githubClient.get(`/users/${encodeURIComponent(login)}`);
    const name = data?.name;
    return name && String(name).trim() ? String(name).trim() : null;
  } catch (error) {
    const status = error?.response?.status;
    if (status === 404) {
      console.warn(`GitHub user not found while fetching name: ${login}`);
      return null;
    }
    console.warn(`Failed to fetch GitHub name for ${login}:`, error.message);
    return null;
  }
}

/**
 * Resolve display name: use provided value, existing DB value, or fetch from GitHub.
 */
async function resolveGitHubUserName({ github_user_id, login, type, name }) {
  if (name && String(name).trim()) {
    return String(name).trim();
  }

  if (!login || isBotType(type)) {
    return null;
  }

  const existing = await pool.query(
    'SELECT name FROM github_users WHERE github_user_id = $1',
    [github_user_id]
  );

  const storedName = existing.rows[0]?.name;
  if (storedName && String(storedName).trim()) {
    return String(storedName).trim();
  }

  return fetchGitHubUserName(login);
}

/**
 * Upsert a GitHub user and return the internal github_users.id.
 */
async function upsertGitHubUser({
  github_user_id,
  login,
  avatar_url,
  html_url,
  type,
  name,
}) {
  const displayName = await resolveGitHubUserName({
    github_user_id,
    login,
    type,
    name,
  });

  const userResult = await pool.query(
    `
      INSERT INTO github_users (github_user_id, login, avatar_url, html_url, type, name)
      VALUES ($1, $2, $3, $4, $5, $6)
      ON CONFLICT (github_user_id)
      DO UPDATE SET
        login = EXCLUDED.login,
        avatar_url = EXCLUDED.avatar_url,
        html_url = EXCLUDED.html_url,
        type = EXCLUDED.type,
        name = COALESCE(EXCLUDED.name, github_users.name),
        updated_at = CURRENT_TIMESTAMP
      RETURNING id
    `,
    [
      github_user_id,
      login,
      avatar_url || null,
      html_url || null,
      type || null,
      displayName,
    ]
  );

  return userResult.rows[0].id;
}

/**
 * Backfill profile names for users that do not have one stored yet.
 */
async function backfillMissingUserNames() {
  const result = await pool.query(
    `
      SELECT id, login, type
      FROM github_users
      WHERE name IS NULL
        AND login IS NOT NULL
        AND (type IS NULL OR LOWER(type) <> 'bot')
      ORDER BY id
    `
  );

  let namesFetched = 0;

  for (const user of result.rows) {
    const name = await fetchGitHubUserName(user.login);
    await pool.query(
      `
        UPDATE github_users
        SET name = $1, updated_at = CURRENT_TIMESTAMP
        WHERE id = $2
      `,
      [name, user.id]
    );

    if (name) {
      namesFetched += 1;
    }

    await sleep(NAME_FETCH_DELAY_MS);
  }

  return {
    users_checked: result.rows.length,
    names_fetched: namesFetched,
  };
}

module.exports = {
  fetchGitHubUserName,
  upsertGitHubUser,
  backfillMissingUserNames,
};
