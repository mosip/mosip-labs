const pool = require('./dbPool');

function parseCommaList(value) {
  return (value || '')
    .split(',')
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function parseUserRolesFromEnv(value = process.env.USER_ROLES) {
  return parseCommaList(value);
}

function parseOrganizationsFromEnv(value = process.env.GITHUB_ORG) {
  return parseCommaList(value).map((slug) => slug.toLowerCase());
}

async function ensureLookupTables() {
  const roles = parseUserRolesFromEnv();
  const orgs = parseOrganizationsFromEnv();

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
    rolesAdded,
    orgsAdded,
  };
}

module.exports = {
  ensureLookupTables,
};
