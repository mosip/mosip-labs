const pool = require('./dbPool');
const { parseUserRolesFromEnv } = require('../config/defaultUserRoles');

function parseOrganizationsFromEnv(value = process.env.GITHUB_ORG) {
  return (value || '')
    .split(',')
    .map((slug) => slug.trim().toLowerCase())
    .filter(Boolean);
}

async function tableExists(tableName) {
  const result = await pool.query(
    `
      SELECT 1
      FROM information_schema.tables
      WHERE table_schema = 'public' AND table_name = $1
      LIMIT 1
    `,
    [tableName]
  );
  return result.rowCount > 0;
}

async function ensureLookupTables() {
  const roles = parseUserRolesFromEnv();
  const orgs = parseOrganizationsFromEnv();
  const createdTables = [];

  if (!(await tableExists('user_roles'))) {
    await pool.query(`
      CREATE TABLE user_roles (
        id SERIAL PRIMARY KEY,
        name VARCHAR(50) NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    createdTables.push('user_roles');
  }

  if (!(await tableExists('organizations'))) {
    await pool.query(`
      CREATE TABLE organizations (
        id SERIAL PRIMARY KEY,
        slug VARCHAR(255) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    createdTables.push('organizations');
  }

  let rolesAdded = 0;
  for (const name of roles) {
    const result = await pool.query(
      `
        INSERT INTO user_roles (name)
        VALUES ($1)
        ON CONFLICT (name) DO NOTHING
        RETURNING id
      `,
      [name]
    );
    if (result.rowCount > 0) {
      rolesAdded += 1;
    }
  }

  let orgsAdded = 0;
  for (const slug of orgs) {
    const result = await pool.query(
      `
        INSERT INTO organizations (slug, name)
        VALUES ($1, $2)
        ON CONFLICT (slug) DO NOTHING
        RETURNING id
      `,
      [slug, slug.toUpperCase()]
    );
    if (result.rowCount > 0) {
      orgsAdded += 1;
    }
  }

  return {
    roles,
    orgs,
    createdTables,
    rolesAdded,
    orgsAdded,
  };
}

module.exports = {
  ensureLookupTables,
  parseOrganizationsFromEnv,
};
