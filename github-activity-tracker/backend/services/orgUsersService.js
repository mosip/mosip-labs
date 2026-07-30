const db = require("../db/dbPool");
const { EXCLUDED_GITHUB_LOGINS } = require("../config/excludedGitHubLogins");

const DEFAULT_LIMIT = 20;

function getDateRanges(period) {
  const periods = {
    daily: 1,
    weekly: 7,
    monthly: 30,
    yearly: 365,
  };

  const days = periods[period];
  if (!days) {
    throw new Error("Invalid period");
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

function sortUsers(results, sortBy, sortOrder) {
  const direction = sortOrder === "asc" ? 1 : -1;

  if (sortBy === "prs") {
    results.sort((a, b) => (a.prs - b.prs) * direction);
    return;
  }

  if (sortBy === "reviews") {
    results.sort((a, b) => (a.reviews - b.reviews) * direction);
    return;
  }

  if (sortBy === "issues") {
    results.sort((a, b) => (a.issues - b.issues) * direction);
    return;
  }

  results.sort((a, b) => {
    if (a.total_activity !== b.total_activity) {
      return (a.total_activity - b.total_activity) * direction;
    }
    if (a.is_active !== b.is_active) {
      return a.is_active ? -1 : 1;
    }
    return String(a.login).localeCompare(String(b.login));
  });
}

async function fetchAssignments(orgId, role) {
  const params = [String(orgId).toLowerCase()];
  let query = `
    SELECT
      ud.id AS assignment_id,
      u.id AS user_id,
      u.login AS login,
      u.name AS name,
      u.avatar_url AS avatar,
      ur.name AS role,
      ud.active AS is_active,
      ud.active_from AS active_from,
      ud.active_to AS active_to
    FROM github_users u
    JOIN user_details ud ON ud.user_id = u.id
    LEFT JOIN user_roles ur ON ur.id = ud.role_id
    LEFT JOIN organizations o ON o.id = ud.organization_id
  `;

  // Assignments explicitly tied to another organization are excluded; rows
  // without an organization remain visible for every org.
  const whereClauses = [
    "(ud.active = true OR ud.role_id IS NOT NULL)",
    "(ud.organization_id IS NULL OR LOWER(o.slug) = $1)",
  ];

  if (Array.isArray(EXCLUDED_GITHUB_LOGINS) && EXCLUDED_GITHUB_LOGINS.length > 0) {
    params.push(EXCLUDED_GITHUB_LOGINS.map((l) => String(l).toLowerCase()));
    whereClauses.push(`LOWER(u.login) <> ALL($${params.length})`);
  }

  if (role) {
    params.push(role);
    whereClauses.push(`ur.name = $${params.length}`);
  }

  query += ` WHERE ${whereClauses.join(" AND ")} `;
  query += " ORDER BY u.login ASC, ud.active DESC, ud.active_from DESC, ud.id DESC";

  const result = await db.query(query, params);
  return result.rows;
}

async function fetchAssignmentActivityMap(orgId, role, start, end) {
  const params = [String(orgId).toLowerCase()];
  let query = `
    SELECT
      ud.id AS assignment_id,
      COUNT(*) FILTER (WHERE e.event_type = 'commit') AS commits,
      COUNT(*) FILTER (WHERE e.event_type = 'pr') AS prs,
      COALESCE(SUM(e.files_changed) FILTER (WHERE e.event_type = 'pr'), 0) AS pr_files_changed,
      COUNT(*) FILTER (WHERE e.event_type = 'review') AS reviews,
      COUNT(*) FILTER (WHERE e.event_type = 'issue') AS issues
    FROM activity_events e
    JOIN github_users u ON u.id = e.user_id
    JOIN repos r ON r.github_repo_id = e.repo_id
    JOIN user_details ud ON ud.user_id = e.user_id
      AND ud.active_from <= e.created_at
      AND (ud.active_to IS NULL OR e.created_at < ud.active_to)
    LEFT JOIN user_roles ur ON ur.id = ud.role_id
    WHERE LOWER(r.owner) = $1
      AND (ud.active = true OR ud.role_id IS NOT NULL)
  `;

  if (Array.isArray(EXCLUDED_GITHUB_LOGINS) && EXCLUDED_GITHUB_LOGINS.length > 0) {
    params.push(EXCLUDED_GITHUB_LOGINS.map((l) => String(l).toLowerCase()));
    query += ` AND LOWER(u.login) <> ALL($${params.length})`;
  }

  if (role) {
    params.push(role);
    query += ` AND ur.name = $${params.length}`;
  }

  params.push(start.toISOString(), end.toISOString());
  query += ` AND e.created_at BETWEEN $${params.length - 1} AND $${params.length}`;
  query += " GROUP BY ud.id";

  const result = await db.query(query, params);
  const map = {};

  result.rows.forEach((row) => {
    map[row.assignment_id] = {
      commits: Number(row.commits) || 0,
      prs: Number(row.prs) || 0,
      pr_files_changed: Number(row.pr_files_changed) || 0,
      reviews: Number(row.reviews) || 0,
      issues: Number(row.issues) || 0,
    };
  });

  return map;
}

const getOrgUsers = async (
  orgId,
  period = "weekly",
  page = 1,
  limit = DEFAULT_LIMIT,
  role = null,
  search = null,
  sortBy = null,
  sortOrder = "desc"
) => {
  page = Math.max(1, parseInt(page, 10) || 1);
  limit = Math.max(1, parseInt(limit, 10) || DEFAULT_LIMIT);

  const { start, end, prevStart, prevEnd } = getDateRanges(period);
  const assignments = await fetchAssignments(orgId, role);
  const currentMap = await fetchAssignmentActivityMap(orgId, role, start, end);
  const previousMap = await fetchAssignmentActivityMap(orgId, role, prevStart, prevEnd);

  const final = assignments.map((row) => {
    const current = currentMap[row.assignment_id] || { commits: 0, prs: 0, pr_files_changed: 0, reviews: 0, issues: 0 };
    const previous = previousMap[row.assignment_id] || { commits: 0, prs: 0, pr_files_changed: 0, reviews: 0, issues: 0 };

    return {
      assignment_id: row.assignment_id,
      login: row.login,
      name: row.name || null,
      avatar: row.avatar,
      role: row.role || null,
      is_active: Boolean(row.is_active),
      active_from: row.active_from,
      active_to: row.active_to,
      commits: current.commits,
      prs: current.prs,
      pr_files_changed: current.pr_files_changed,
      reviews: current.reviews,
      issues: current.issues,
      diffCommits: diff(current.commits, previous.commits),
      diffPRs: diff(current.prs, previous.prs),
      diffReviews: diff(current.reviews, previous.reviews),
      diffIssues: diff(current.issues, previous.issues),
      total_activity: current.prs + current.reviews + current.issues,
    };
  });

  sortUsers(final, sortBy, sortOrder);

  const term = search ? String(search).trim().toLowerCase() : "";
  const results = term
    ? final.filter(
        (u) =>
          (u.login || "").toLowerCase().includes(term)
          || (u.name || "").toLowerCase().includes(term)
      )
    : final;

  const totalUsers = results.length;
  const totalPages = Math.ceil(totalUsers / limit);
  const startIndex = (page - 1) * limit;
  const usersPage = results.slice(startIndex, startIndex + limit);

  return {
    users: usersPage,
    page,
    limit,
    totalUsers,
    totalPages,
  };
};

module.exports = {
  getOrgUsers,
};


