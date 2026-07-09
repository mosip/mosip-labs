function userAssignmentWindowSql() {
  return `
    ud.user_id = u.id
    AND ud.active = true
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

module.exports = {
  userAssignmentWindowSql,
  userDetailsRoleFilterSql,
  userDetailsJoinSql,
  userDetailsExistsSql,
};
