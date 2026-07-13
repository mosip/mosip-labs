// Matches assignments by their validity window (active_from/active_to) rather
// than the active flag, so closed historical assignments still cover events
// that happened while they were in effect.
function userAssignmentWindowSql() {
  return `
    ud.user_id = u.id
    AND ud.active_from <= e.created_at
    AND (ud.active_to IS NULL OR e.created_at < ud.active_to)`;
}

function userDetailsRoleNameMatchSql(roleParam) {
  return `
    ud.role_id IS NOT NULL
    AND EXISTS (
      SELECT 1
      FROM user_roles ur_match
      WHERE ur_match.id = ud.role_id
        AND ur_match.name = ${roleParam}
    )`;
}

function userDetailsExistsSql(roleParam = null) {
  const roleClause = roleParam
    ? `AND ${userDetailsRoleNameMatchSql(roleParam)}`
    : '';

  return `
    EXISTS (
      SELECT 1
      FROM user_details ud
      WHERE ${userAssignmentWindowSql()}
        ${roleClause}
    )`;
}

function userDetailsJoinSql(roleParam = null) {
  const roleClause = roleParam
    ? `AND ${userDetailsRoleNameMatchSql(roleParam)}`
    : '';

  return `
    JOIN user_details ud ON ${userAssignmentWindowSql()}
      ${roleClause}`;
}

// Used by userDetailsService when scoping a single known user.
function userDetailsRoleFilterSql(roleParam) {
  return userDetailsRoleNameMatchSql(roleParam);
}

/**
 * Build the user_details join, pushing the role param when a filter is set.
 * Keeps the role-filter SQL logic in one place for all analytics services.
 */
function pushRoleUserDetailsJoin(params, role) {
  if (!role) {
    return userDetailsJoinSql(null);
  }

  params.push(role);
  return userDetailsJoinSql(`$${params.length}`);
}

module.exports = {
  userAssignmentWindowSql,
  userDetailsRoleFilterSql,
  userDetailsJoinSql,
  userDetailsExistsSql,
  pushRoleUserDetailsJoin,
};
