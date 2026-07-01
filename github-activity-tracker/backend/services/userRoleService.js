const pool = require('../db/dbPool');
const { isValidUserRole } = require('../config/userRoles');

async function findUserByLogin(login) {
  const result = await pool.query(
    `
      SELECT id, github_user_id, login, name, role
      FROM github_users
      WHERE LOWER(login) = LOWER($1)
    `,
    [login]
  );

  return result.rows[0] || null;
}

async function getUserRole(login) {
  const user = await findUserByLogin(login);

  if (!user) {
    return null;
  }

  return {
    user_id: user.id,
    github_user_id: user.github_user_id,
    login: user.login,
    name: user.name || null,
    role: user.role || null,
  };
}

async function setUserRole({ login, role }) {
  if (!login || typeof login !== 'string') {
    throw new Error('login is required');
  }

  if (!role || typeof role !== 'string') {
    throw new Error('role is required');
  }

  const trimmedRole = role.trim();

  if (!isValidUserRole(trimmedRole)) {
    throw new Error('Invalid role value');
  }

  const user = await findUserByLogin(login);

  if (!user) {
    return null;
  }

  const result = await pool.query(
    `
      UPDATE github_users
      SET role = $1, updated_at = CURRENT_TIMESTAMP
      WHERE id = $2
      RETURNING id, github_user_id, login, name, role
    `,
    [trimmedRole, user.id]
  );

  const updated = result.rows[0];

  return {
    user_id: updated.id,
    github_user_id: updated.github_user_id,
    login: updated.login,
    name: updated.name || null,
    role: updated.role,
  };
}

module.exports = {
  getUserRole,
  setUserRole,
};
