const pool = require('../db/dbPool');
const { EXCLUDED_GITHUB_LOGINS } = require('../config/excludedGitHubLogins');

/* ---------------------------------------------
   Calculate date ranges
--------------------------------------------- */
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

/* ---------------------------------------------
   MAIN SERVICE
--------------------------------------------- */
const getLeaderboard = async (orgId, period = "weekly", limit = 10) => {
  limit = parseInt(limit) || 10;

  const { start, end } = getDateRange(period);

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
  `;

  const params = [];
  const whereClauses = [];

  if (Array.isArray(EXCLUDED_GITHUB_LOGINS) && EXCLUDED_GITHUB_LOGINS.length > 0) {
    params.push(EXCLUDED_GITHUB_LOGINS.map((l) => String(l).toLowerCase()));
    whereClauses.push(`LOWER(u.login) <> ALL($${params.length})`);
  }

  if (start && end) {
    params.push(start.toISOString(), end.toISOString());
    whereClauses.push(
      `e.created_at BETWEEN $${params.length - 1} AND $${params.length}`
    );
  }

  if (whereClauses.length) {
    query += ` WHERE ${whereClauses.join(' AND ')} `;
  }

  query += `
    GROUP BY u.id, u.login, u.avatar_url
    ORDER BY score DESC
    LIMIT ${limit};
  `;

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
    leaderboard,
  };
};

module.exports = {
  getLeaderboard,
};