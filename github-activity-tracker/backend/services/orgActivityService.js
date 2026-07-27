const pool = require("../db/dbPool");

const dayjs = require("dayjs");

const { EXCLUDED_GITHUB_LOGINS } = require("../config/excludedGitHubLogins");
const { pushRoleUserDetailsJoin } = require("../utils/userRoleSql");



/**

 * Returns org-wide daily activity for chosen period, scoped to repos owned by orgId.

 */

async function getOrgActivity(orgId, period, role) {

  const periods = { daily: 1, weekly: 7, monthly: 30, yearly: 365 };

  const days = periods[period];

  if (!days) {

    throw new Error("Invalid period");

  }



  const end = dayjs().endOf("day");

  const start = end.subtract(days - 1, "day").startOf("day");



  const params = [String(orgId).toLowerCase()];

  const whereClauses = [`LOWER(r.owner) = $${params.length}`];



  if (Array.isArray(EXCLUDED_GITHUB_LOGINS) && EXCLUDED_GITHUB_LOGINS.length > 0) {

    params.push(EXCLUDED_GITHUB_LOGINS.map((l) => String(l).toLowerCase()));

    whereClauses.push(`LOWER(u.login) <> ALL($${params.length})`);

  }



  params.push(start.toDate(), end.toDate());

  whereClauses.push(`e.created_at BETWEEN $${params.length - 1} AND $${params.length}`);



  const userDetailsJoin = pushRoleUserDetailsJoin(params, role);



  const result = await pool.query(

    `

    SELECT

      DATE(e.created_at) AS date,

      COUNT(*) FILTER (WHERE e.event_type = 'commit') AS commits,

      COUNT(*) FILTER (WHERE e.event_type = 'pr') AS prs,

      COUNT(*) FILTER (WHERE e.event_type = 'review') AS reviews,

      COUNT(*) FILTER (WHERE e.event_type = 'issue') AS issues

    FROM activity_events e

    JOIN github_users u ON u.id = e.user_id

    ${userDetailsJoin}

    JOIN repos r ON r.github_repo_id = e.repo_id

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

  const issues = [];

  const total = [];



  const map = {};

  result.rows.forEach((r) => {

    map[dayjs(r.date).format("YYYY-MM-DD")] = r;

  });



  for (let i = 0; i < days; i++) {

    const d = start.add(i, "day").format("YYYY-MM-DD");

    labels.push(d);



    const row = map[d] || { commits: 0, prs: 0, reviews: 0, issues: 0 };



    const c = Number(row.commits);

    const p = Number(row.prs);

    const rv = Number(row.reviews);

    const issueCount = Number(row.issues);

    commits.push(c);

    prs.push(p);

    reviews.push(rv);

    issues.push(issueCount);

    total.push(c + p + rv + issueCount);

  }



  return { labels, commits, prs, reviews, issues, total };

}



module.exports = { getOrgActivity };


