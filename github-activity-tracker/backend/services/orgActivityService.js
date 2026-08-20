const pool = require("../db/dbPool");
const dayjs = require("dayjs");
const { EXCLUDED_GITHUB_LOGINS } = require("../config/excludedGitHubLogins");

/**
 * Returns org-wide daily activity for chosen period
 */
async function getOrgActivity(period) {
  let days = 7;

  if (period === "daily") days = 1;
  if (period === "monthly") days = 30;

  const end = dayjs().endOf("day");
  const start = end.subtract(days - 1, "day").startOf("day");

  const params = [];
  const whereClauses = [];

  if (Array.isArray(EXCLUDED_GITHUB_LOGINS) && EXCLUDED_GITHUB_LOGINS.length > 0) {
    params.push(EXCLUDED_GITHUB_LOGINS.map((l) => String(l).toLowerCase()));
    whereClauses.push(`LOWER(u.login) <> ALL($${params.length})`);
  }

  params.push(start.toDate(), end.toDate());
  whereClauses.push(`e.created_at BETWEEN $${params.length - 1} AND $${params.length}`);

  const result = await pool.query(
    `
    SELECT
      DATE(e.created_at) AS date,
      COUNT(*) FILTER (WHERE e.event_type = 'commit') AS commits,
      COUNT(*) FILTER (WHERE e.event_type = 'pr') AS prs,
      COUNT(*) FILTER (WHERE e.event_type = 'review') AS reviews
    FROM activity_events e
    JOIN github_users u ON u.id = e.user_id
    WHERE ${whereClauses.join(" AND ")}
    GROUP BY DATE(e.created_at)
    ORDER BY DATE(e.created_at);
    `,
    params
  );

  // Generate empty date → fill zeros
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

    commits.push(Number(row.commits));
    prs.push(Number(row.prs));
    reviews.push(Number(row.reviews));
    total.push(row.commits + row.prs + row.reviews);
  }

  return { labels, commits, prs, reviews, total };
}

module.exports = { getOrgActivity };