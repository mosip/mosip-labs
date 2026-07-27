const db = require("../db/dbPool");
const { EXCLUDED_GITHUB_LOGINS } = require("../config/excludedGitHubLogins");
const { pushRoleUserDetailsJoin } = require("../utils/userRoleSql");

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

      currentEnd = new Date(now);
      previousEnd = new Date(currentStart);
      break;

    case "monthly":
      currentStart = new Date();
      currentStart.setDate(currentStart.getDate() - 30);

      previousStart = new Date();
      previousStart.setDate(previousStart.getDate() - 60);

      currentEnd = new Date(now);
      previousEnd = new Date(currentStart);
      break;

    case "yearly":
      currentStart = new Date();
      currentStart.setDate(currentStart.getDate() - 365);

      previousStart = new Date();
      previousStart.setDate(previousStart.getDate() - 730);

      currentEnd = new Date(now);
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

async function fetchCounts(orgId, start, end, role) {
  const params = [];
  let query = `
    SELECT event_type, COUNT(*) AS count
    FROM activity_events e
    JOIN github_users u ON u.id = e.user_id
    JOIN repos r ON r.github_repo_id = e.repo_id
  `;

  const whereClauses = [];

  params.push(String(orgId).toLowerCase());
  whereClauses.push(`LOWER(r.owner) = $${params.length}`);

  if (Array.isArray(EXCLUDED_GITHUB_LOGINS) && EXCLUDED_GITHUB_LOGINS.length > 0) {
    params.push(EXCLUDED_GITHUB_LOGINS.map((l) => String(l).toLowerCase()));
    whereClauses.push(`LOWER(u.login) <> ALL($${params.length})`);
  }

  params.push(start, end);
  whereClauses.push(`e.created_at BETWEEN $${params.length - 1} AND $${params.length}`);

  const userDetailsJoin = pushRoleUserDetailsJoin(params, role);

  query += `
    ${userDetailsJoin}
    WHERE ${whereClauses.join(" AND ")}
    GROUP BY event_type;
  `;

  const result = await db.query(query, params);

  const summary = {
    commits: 0,
    prs: 0,
    reviews: 0,
    issues: 0,
    activity: 0,
  };

  result.rows.forEach((row) => {
    if (row.event_type === "commit") summary.commits = Number(row.count);
    if (row.event_type === "pr") summary.prs = Number(row.count);
    if (row.event_type === "review") summary.reviews = Number(row.count);
    if (row.event_type === "issue") summary.issues = Number(row.count);
  });

  summary.activity = summary.prs + summary.reviews + summary.issues;

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
    issues: safePercent(current.issues, previous.issues),
    activity: safePercent(current.activity, previous.activity),
  };
}

async function getOrgSummary(orgId, period, role) {
  const { currentStart, currentEnd, previousStart, previousEnd } =
    getDateRanges(period);

  const current = await fetchCounts(orgId, currentStart, currentEnd, role);
  const previous = await fetchCounts(orgId, previousStart, previousEnd, role);

  const change = calculateChange(current, previous);

  return {
    total_commits: current.commits,
    total_prs: current.prs,
    total_reviews: current.reviews,
    total_issues: current.issues,
    total_activity: current.activity,
    change,
  };
}

module.exports = {
  getOrgSummary,
};
