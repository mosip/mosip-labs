const db = require("../db/dbPool");
const { EXCLUDED_GITHUB_LOGINS } = require("../config/excludedGitHubLogins");
const { buildProjectFilter } = require("../utils/projectFilter");

function getDateRanges(period) {
  const now = new Date();

  let currentStart, previousStart, currentEnd, previousEnd;

  switch (period) {
    case "daily":
      currentStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      previousStart = new Date(currentStart);
      previousStart.setDate(previousStart.getDate() - 1);

      currentEnd = new Date(now);
      previousEnd = new Date(currentStart);
      break;

    case "weekly":
      currentStart = new Date();
      currentStart.setDate(currentStart.getDate() - 7);

      previousStart = new Date();
      previousStart.setDate(previousStart.getDate() - 14);

      currentEnd = new Date();
      previousEnd = new Date(currentStart);
      break;

    case "monthly":
      currentStart = new Date();
      currentStart.setDate(currentStart.getDate() - 30);

      previousStart = new Date();
      previousStart.setDate(previousStart.getDate() - 60);

      currentEnd = new Date();
      previousEnd = new Date(currentStart);
      break;

    default:
      throw new Error("Invalid period value");
  }

  return {
    currentStart,
    currentEnd,
    previousStart,
    previousEnd,
  };
}

async function fetchCounts(start, end, projectId) {
  const params = [];
  let paramIndex = 1;

  const projectFilter = buildProjectFilter(projectId, { paramIndex });
  paramIndex = projectFilter.nextIndex;
  params.push(...projectFilter.params);

  let query = `
    SELECT event_type, COUNT(*) AS count
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

  params.push(start, end);
  whereClauses.push(
    `e.created_at >= $${paramIndex} AND e.created_at < $${paramIndex + 1}`
  );
  paramIndex += 2;

  query += `
    WHERE ${whereClauses.join(" AND ")}
    GROUP BY event_type;
  `;

  const result = await db.query(query, params);

  const summary = {
    commits: 0,
    prs: 0,
    reviews: 0,
    activity: 0,
  };

  result.rows.forEach((row) => {
    if (row.event_type === "commit") summary.commits = Number(row.count);
    if (row.event_type === "pr") summary.prs = Number(row.count);
    if (row.event_type === "review") summary.reviews = Number(row.count);
  });

  summary.activity = summary.commits + summary.prs + summary.reviews;

  return summary;
}

function calculateChange(current, previous) {
  const safePercent = (c, p) => {
    if (p === 0) {
      return c === 0 ? 0 : 100;
    }

    return Number((((c - p) / p) * 100).toFixed(1));
  };

  return {
    commits: safePercent(current.commits, previous.commits),
    prs: safePercent(current.prs, previous.prs),
    reviews: safePercent(current.reviews, previous.reviews),
    activity: safePercent(current.activity, previous.activity),
  };
}

async function getOrgSummary(period, projectId = "all") {
  const { currentStart, currentEnd, previousStart, previousEnd } =
    getDateRanges(period);

  const current = await fetchCounts(
    currentStart,
    new Date(currentEnd.getTime() + 1),
    projectId
  );
  const previous = await fetchCounts(previousStart, previousEnd, projectId);

  const change = calculateChange(current, previous);

  return {
    total_commits: current.commits,
    total_prs: current.prs,
    total_reviews: current.reviews,
    total_activity: current.activity,
    change,
  };
}

module.exports = {
  getOrgSummary,
};
