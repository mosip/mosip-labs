const pool = require('../db/dbPool');

async function getAllUserRoles() {
  const result = await pool.query(
    'SELECT id, name FROM user_roles ORDER BY name ASC'
  );
  return result.rows;
}

async function getUserRoleNames() {
  const roles = await getAllUserRoles();
  return roles.map((role) => role.name);
}

async function isValidUserRole(roleName) {
  if (!roleName || typeof roleName !== 'string') {
    return false;
  }

  const trimmed = roleName.trim();
  const result = await pool.query(
    'SELECT 1 FROM user_roles WHERE name = $1 LIMIT 1',
    [trimmed]
  );
  return result.rowCount > 0;
}

async function getUserRoleIdByName(roleName) {
  if (!roleName || typeof roleName !== 'string') {
    return null;
  }

  const result = await pool.query(
    'SELECT id FROM user_roles WHERE name = $1 LIMIT 1',
    [roleName.trim()]
  );
  return result.rows[0]?.id || null;
}

/**
 * Validate an optional role query value and normalize it into a filter.
 * Returns { error } when the role is invalid, otherwise { roleFilter }
 * where roleFilter is null for missing/"all" roles.
 */
async function resolveRoleFilter(role) {
  const normalizedRole = typeof role === 'string' ? role.trim() : role;

  if (!normalizedRole || normalizedRole === 'all') {
    return { roleFilter: null };
  }

  if (!(await isValidUserRole(normalizedRole))) {
    return { error: 'Invalid role value' };
  }

  return { roleFilter: normalizedRole };
}

module.exports = {
  getAllUserRoles,
  getUserRoleNames,
  isValidUserRole,
  getUserRoleIdByName,
  resolveRoleFilter,
};
