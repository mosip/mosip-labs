const pool = require('../db/dbPool');
const { EXCLUDED_GITHUB_LOGINS } = require('../config/excludedGitHubLogins');
const { buildProjectFilter } = require('../utils/projectFilter');

function getDateRange(period) {
  if (period === "all") {
    return { start: null, end: null };
  }

  const periods = { daily: 1, weekly: 7, monthly: 30 };
  const days = periods[period];
  if (!days) {
    throw new Error('Invalid period');
  }

  const end = new Date();
  end.setUTCHours(23, 59, 59, 999);

  const start = new Date(end);
  start.setUTCDate(end.getUTCDate() - (days - 1));
  start.setUTCHours(0, 0, 0, 0);

  return { start, end };
}

const getLeaderboard = async (projectId = "all", period = "weekly", limit = 10) => {
  limit = parseInt(limit) || 10;

  const { start, end } = getDateRange(period);

  const params = [];
  let paramIndex = 1;

  const projectFilter = buildProjectFilter(projectId, { paramIndex });
  paramIndex = projectFilter.nextIndex;
  params.push(...projectFilter.params);

  let query = `
    SELECT
      u.login,
      u.avatar_url AS avatar,
      COUNT(*) FILTER (WHERE e.event_type = 'commit') AS commits,
      COUNT(*) FILTER (WHERE e.event_type = 'pr') AS prs,
      COUNT(*) FILTER (WHERE e.event_type = 'review') AS reviews,
      COUNT(*) AS score
    FROM activity_events e
    JOIN github_users u ON u.id = e.user_id
    ${projectFilter.joinClause}
  `;

  const whereClauses = [];

  if (Array.isArray(EXCLUDED_GITHUB_LOGINS) && EXCLUDED_GITHUB_LOGINS.length > 0) {
    params.push(EXCLUDED_GITHUB_LOGINS.map((l) => String(l).toLowerCase()));
    whereClauses.push(`LOWER(u.login) <> ALL($${paramIndex})`);
    paramIndex += 1;
  }

  if (projectFilter.whereClause) {
    whereClauses.push(projectFilter.whereClause.replace(/^ AND /, ''));
  }

  if (start && end) {
    params.push(start.toISOString(), end.toISOString());
    whereClauses.push(
      `e.created_at BETWEEN $${paramIndex} AND $${paramIndex + 1}`
    );
    paramIndex += 2;
  }

  if (whereClauses.length) {
    query += ` WHERE ${whereClauses.join(' AND ')} `;
  }

  query += `
    GROUP BY u.id, u.login, u.avatar_url
    ORDER BY score DESC
  `;

  if (limit > 0) {
    query += ` LIMIT ${limit}`;
  }

  query += ';';

  const result = await pool.query(query, params);

  const leaderboard = result.rows.map((row, index) => ({
    rank: index + 1,
    login: row.login,
    avatar: row.avatar,
    commits: Number(row.commits),
    prs: Number(row.prs),
    reviews: Number(row.reviews),
    score: Number(row.score),
  }));

  return {
    period,
    project: projectId,
    leaderboard,
  };
};

module.exports = {
  getLeaderboard,
};
