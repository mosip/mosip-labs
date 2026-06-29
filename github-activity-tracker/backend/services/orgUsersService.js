const db = require("../db/dbPool");
const { EXCLUDED_GITHUB_LOGINS } = require("../config/excludedGitHubLogins");
const { buildProjectFilter } = require("../utils/projectFilter");

const DEFAULT_LIMIT = 20;

function getDateRanges(period) {
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

  const prevEnd = new Date(start.getTime() - 1);
  const prevStart = new Date(prevEnd);
  prevStart.setUTCDate(prevEnd.getUTCDate() - (days - 1));
  prevStart.setUTCHours(0, 0, 0, 0);

  return { start, end, prevStart, prevEnd };
}

function diff(current, previous) {
  return current - previous;
}

function buildActivityQuery(projectId) {
  const params = [];
  let paramIndex = 1;
  const projectFilter = buildProjectFilter(projectId, { paramIndex });
  paramIndex = projectFilter.nextIndex;
  params.push(...projectFilter.params);

  const whereClauses = [];
  if (projectFilter.whereClause) {
    whereClauses.push(projectFilter.whereClause.replace(/^ AND /, ''));
  }

  if (Array.isArray(EXCLUDED_GITHUB_LOGINS) && EXCLUDED_GITHUB_LOGINS.length > 0) {
    params.push(EXCLUDED_GITHUB_LOGINS.map((l) => String(l).toLowerCase()));
    whereClauses.push(`LOWER(u.login) <> ALL($${paramIndex})`);
    paramIndex += 1;
  }

  const dateStartIndex = paramIndex;
  params.push(null, null);
  whereClauses.push(
    `e.created_at BETWEEN $${dateStartIndex} AND $${dateStartIndex + 1}`
  );

  const query = `
    SELECT
      e.user_id AS user_id,
      COUNT(*) FILTER (WHERE event_type = 'commit') AS commits,
      COUNT(*) FILTER (WHERE event_type = 'pr') AS prs,
      COUNT(*) FILTER (WHERE event_type = 'review') AS reviews
    FROM activity_events e
    JOIN github_users u ON u.id = e.user_id
    ${projectFilter.joinClause}
    WHERE ${whereClauses.join(' AND ')}
    GROUP BY e.user_id;
  `;

  return { query, baseParams: params.slice(0, -2), dateStartIndex };
}

const getOrgUsers = async (
  projectId = "all",
  period = "weekly",
  page = 1,
  limit = DEFAULT_LIMIT,
) => {
  page = Math.max(1, parseInt(page, 10) || 1);
  const parsedLimit = parseInt(limit, 10);
  limit = parsedLimit === 0 ? 0 : Math.max(1, parsedLimit || DEFAULT_LIMIT);

  const { start, end, prevStart, prevEnd } = getDateRanges(period);
  const { query: activityQuery, baseParams } = buildActivityQuery(projectId);

  const projectFilter = buildProjectFilter(projectId, { paramIndex: 1 });
  const usersParams = [...projectFilter.params];
  const userWhere = [];

  if (projectFilter.whereClause) {
    userWhere.push(projectFilter.whereClause.replace(/^ AND /, ''));
  }
  if (Array.isArray(EXCLUDED_GITHUB_LOGINS) && EXCLUDED_GITHUB_LOGINS.length > 0) {
    usersParams.push(EXCLUDED_GITHUB_LOGINS.map((l) => String(l).toLowerCase()));
    userWhere.push(`LOWER(u.login) <> ALL($${usersParams.length})`);
  }

  let usersQuery = `
    SELECT DISTINCT u.id, u.login AS login, u.avatar_url AS avatar
    FROM github_users u
    JOIN activity_events e ON e.user_id = u.id
    ${projectFilter.joinClause}
  `;
  if (userWhere.length) {
    usersQuery += ` WHERE ${userWhere.join(' AND ')} `;
  }
  usersQuery += ` ORDER BY u.login ASC; `;

  const usersRes = await db.query(usersQuery, usersParams);
  const users = usersRes.rows;

  const currentRes = await db.query(activityQuery, [
    ...baseParams,
    start.toISOString(),
    end.toISOString(),
  ]);

  const currentMap = {};
  currentRes.rows.forEach((row) => {
    currentMap[row.user_id] = {
      commits: Number(row.commits),
      prs: Number(row.prs),
      reviews: Number(row.reviews),
    };
  });

  const previousRes = await db.query(activityQuery, [
    ...baseParams,
    prevStart.toISOString(),
    prevEnd.toISOString(),
  ]);

  const previousMap = {};
  previousRes.rows.forEach((row) => {
    previousMap[row.user_id] = {
      commits: Number(row.commits),
      prs: Number(row.prs),
      reviews: Number(row.reviews),
    };
  });

  const final = users.map((u) => {
    const current = currentMap[u.id] || { commits: 0, prs: 0, reviews: 0 };
    const previous = previousMap[u.id] || { commits: 0, prs: 0, reviews: 0 };

    return {
      login: u.login,
      avatar: u.avatar,
      commits: current.commits,
      prs: current.prs,
      reviews: current.reviews,
      diffCommits: diff(current.commits, previous.commits),
      diffPRs: diff(current.prs, previous.prs),
      diffReviews: diff(current.reviews, previous.reviews),
      total_activity: current.commits + current.prs + current.reviews,
    };
  });

  final.sort((a, b) => b.total_activity - a.total_activity);

  const totalUsers = final.length;
  const totalPages = limit > 0 ? Math.ceil(totalUsers / limit) : 1;
  const startIndex = limit > 0 ? (page - 1) * limit : 0;

  return {
    users: limit > 0 ? final.slice(startIndex, startIndex + limit) : final,
    page,
    limit: limit > 0 ? limit : totalUsers,
    totalUsers,
    totalPages,
    project: projectId,
  };
};

module.exports = {
  getOrgUsers,
};
