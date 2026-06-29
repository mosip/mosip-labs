const pool = require("../db/dbPool");
const dayjs = require("dayjs");
const { EXCLUDED_GITHUB_LOGINS } = require("../config/excludedGitHubLogins");
const { buildProjectFilter } = require("../utils/projectFilter");

/**
 * Returns org-wide daily activity for chosen period, optionally filtered by project.
 */
async function getOrgActivity(period, projectId = "all") {
  const periods = { daily: 1, weekly: 7, monthly: 30 };
  const days = periods[period];
  if (!days) {
    throw new Error("Invalid period");
  }

  const end = dayjs().endOf("day");
  const start = end.subtract(days - 1, "day").startOf("day");

  const params = [];
  let paramIndex = 1;

  const projectFilter = buildProjectFilter(projectId, { paramIndex });
  paramIndex = projectFilter.nextIndex;
  params.push(...projectFilter.params);

  const whereClauses = [];

  if (Array.isArray(EXCLUDED_GITHUB_LOGINS) && EXCLUDED_GITHUB_LOGINS.length > 0) {
    params.push(EXCLUDED_GITHUB_LOGINS.map((l) => String(l).toLowerCase()));
    whereClauses.push(`LOWER(u.login) <> ALL($${paramIndex})`);
    paramIndex += 1;
  }

  if (projectFilter.whereClause) {
    whereClauses.push(projectFilter.whereClause.replace(/^ AND /, ''));
  }

  params.push(start.toDate(), end.toDate());
  whereClauses.push(`e.created_at BETWEEN $${paramIndex} AND $${paramIndex + 1}`);

  const result = await pool.query(
    `
    SELECT
      DATE(e.created_at) AS date,
      COUNT(*) FILTER (WHERE e.event_type = 'commit') AS commits,
      COUNT(*) FILTER (WHERE e.event_type = 'pr') AS prs,
      COUNT(*) FILTER (WHERE e.event_type = 'review') AS reviews
    FROM activity_events e
    JOIN github_users u ON u.id = e.user_id
    ${projectFilter.joinClause}
    WHERE ${whereClauses.join(" AND ")}
    GROUP BY DATE(e.created_at)
    ORDER BY DATE(e.created_at);
    `,
    params
  );

  const labels = [];
  const commits = [];
  const prs = [];
  const reviews = [];
  const total = [];

  const map = {};
  result.rows.forEach((r) => {
    map[dayjs(r.date).format("YYYY-MM-DD")] = r;
  });

  for (let i = 0; i < days; i++) {
    const d = start.add(i, "day").format("YYYY-MM-DD");
    labels.push(d);

    const row = map[d] || { commits: 0, prs: 0, reviews: 0 };

    const c = Number(row.commits);
    const p = Number(row.prs);
    const r = Number(row.reviews);
    commits.push(c);
    prs.push(p);
    reviews.push(r);
    total.push(c + p + r);
  }

  return { labels, commits, prs, reviews, total, project: projectId };
}

module.exports = { getOrgActivity };
