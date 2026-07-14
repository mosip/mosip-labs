const pool = require('../db/dbPool');

async function getAllOrganizations() {
  const result = await pool.query(
    'SELECT id, slug, name FROM organizations ORDER BY name ASC'
  );
  return result.rows;
}

async function getOrganizationSlugs() {
  const organizations = await getAllOrganizations();
  return organizations.map((organization) => organization.slug);
}

async function getOrganizationNames() {
  return getOrganizationSlugs();
}

function normalizeOrganization(organization) {
  return String(organization).trim().toLowerCase();
}

async function isValidOrganization(organization) {
  if (!organization || typeof organization !== 'string') {
    return false;
  }

  const normalized = normalizeOrganization(organization);
  const result = await pool.query(
    'SELECT 1 FROM organizations WHERE slug = $1 LIMIT 1',
    [normalized]
  );
  return result.rowCount > 0;
}

async function getOrganizationIdBySlug(organization) {
  if (!organization || typeof organization !== 'string') {
    return null;
  }

  const result = await pool.query(
    'SELECT id FROM organizations WHERE slug = $1 LIMIT 1',
    [normalizeOrganization(organization)]
  );
  return result.rows[0]?.id || null;
}

module.exports = {
  getAllOrganizations,
  getOrganizationSlugs,
  getOrganizationNames,
  normalizeOrganization,
  isValidOrganization,
  getOrganizationIdBySlug,
};
