const pool = require('../db/dbPool');
const { isValidUserRole, getUserRoleIdByName } = require('./userRolesService');
const {
  isValidOrganization,
  normalizeOrganization,
  getOrganizationIdBySlug,
} = require('./organizationsService');

async function findUserByLogin(login) {
  const result = await pool.query(
    `
      SELECT id, github_user_id, login, name
      FROM github_users
      WHERE LOWER(login) = LOWER($1)
    `,
    [login]
  );

  return result.rows[0] || null;
}

function formatUserRoleResponse(user, details) {
  return {
    user_id: user.id,
    github_user_id: user.github_user_id,
    login: user.login,
    name: user.name || null,
    role: details?.role || null,
    organization: details?.organization || null,
  };
}

async function getUserRole(login) {
  const user = await findUserByLogin(login);

  if (!user) {
    return null;
  }

  const detailsResult = await pool.query(
    `
      SELECT ur.name AS role, o.slug AS organization
      FROM user_details ud
      LEFT JOIN user_roles ur ON ur.id = ud.role_id
      LEFT JOIN organizations o ON o.id = ud.organization_id
      WHERE ud.user_id = $1 AND ud.active = true
    `,
    [user.id]
  );

  return formatUserRoleResponse(user, detailsResult.rows[0] || null);
}

async function resolveFirstAssignmentActiveFrom(client, userId) {
  const earliestResult = await client.query(
    `
      SELECT MIN(active_from) AS earliest
      FROM user_details
      WHERE user_id = $1
    `,
    [userId]
  );

  const activityResult = await client.query(
    `
      SELECT MIN(e.created_at) AS earliest
      FROM activity_events e
      WHERE e.user_id = $1
    `,
    [userId]
  );

  const candidates = [
    earliestResult.rows[0]?.earliest,
    activityResult.rows[0]?.earliest,
  ].filter(Boolean);

  if (candidates.length === 0) {
    return new Date();
  }

  return new Date(
    Math.min(...candidates.map((value) => new Date(value).getTime()))
  );
}

async function setUserRole({ login, role, organization }) {
  if (!login || typeof login !== 'string') {
    throw new Error('login is required');
  }

  if (!role || typeof role !== 'string') {
    throw new Error('role is required');
  }

  if (!organization || typeof organization !== 'string') {
    throw new Error('organization is required');
  }

  const trimmedRole = role.trim();
  const normalizedOrganization = normalizeOrganization(organization);

  if (!(await isValidUserRole(trimmedRole))) {
    throw new Error('Invalid role value');
  }

  if (!(await isValidOrganization(normalizedOrganization))) {
    throw new Error('Invalid organization value');
  }

  const roleId = await getUserRoleIdByName(trimmedRole);
  const organizationId = await getOrganizationIdBySlug(normalizedOrganization);

  if (!roleId || !organizationId) {
    throw new Error('Invalid role or organization value');
  }

  const user = await findUserByLogin(login);

  if (!user) {
    return null;
  }

  const client = await pool.connect();

  try {
    await client.query('BEGIN');

    const activeResult = await client.query(
      `
        SELECT id, role_id, organization_id, active_from
        FROM user_details
        WHERE user_id = $1 AND active = true
        ORDER BY active_from DESC, id DESC
        FOR UPDATE
      `,
      [user.id]
    );

    const activeRows = activeResult.rows;
    const active = activeRows[0] || null;

    if (
      active
      && active.role_id === roleId
      && active.organization_id === organizationId
    ) {
      await client.query('COMMIT');
      return formatUserRoleResponse(user, {
        role: trimmedRole,
        organization: normalizedOrganization,
      });
    }

    const roleHistoryResult = await client.query(
      `
        SELECT 1
        FROM user_details
        WHERE user_id = $1
          AND role_id IS NOT NULL
        LIMIT 1
      `,
      [user.id]
    );
    const hasEverAssignedRole = roleHistoryResult.rowCount > 0;
    const isFirstAssignment = !hasEverAssignedRole;
    const activeFrom = isFirstAssignment
      ? await resolveFirstAssignmentActiveFrom(client, user.id)
      : new Date();

    if (activeRows.length > 0) {
      await client.query(
        `
          UPDATE user_details
          SET active = false,
              active_to = $2,
              updated_at = CURRENT_TIMESTAMP
          WHERE user_id = $1
            AND active = true
        `,
        [user.id, activeFrom]
      );
    }

    await client.query(
      `
        INSERT INTO user_details (
          user_id,
          role_id,
          organization_id,
          active,
          active_from,
          active_to
        )
        VALUES ($1, $2, $3, true, $4, NULL)
      `,
      [user.id, roleId, organizationId, activeFrom]
    );

    await client.query('COMMIT');
    return formatUserRoleResponse(user, {
      role: trimmedRole,
      organization: normalizedOrganization,
    });
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
}

module.exports = {
  getUserRole,
  setUserRole,
};
