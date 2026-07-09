const pool = require('../db/dbPool');
const { parseUserRolesFromEnv } = require('../config/defaultUserRoles');

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

module.exports = {
  getAllUserRoles,
  getUserRoleNames,
  isValidUserRole,
  getUserRoleIdByName,
};
