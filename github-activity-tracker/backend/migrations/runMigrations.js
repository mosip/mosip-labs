/**
 * Run SQL migrations in order (001_*.sql, 002_*.sql, ...).
 * Migrations are idempotent. Run manually: npm run migrate
 */
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const pool = require('../db/dbPool');

async function runMigrations({ closePool = true } = {}) {
  const migrationsDir = path.join(__dirname);
  const files = fs.readdirSync(migrationsDir)
    .filter((file) => file.endsWith('.sql'))
    .sort();

  console.log(`Found ${files.length} migration file(s)`);

  for (const file of files) {
    const filePath = path.join(migrationsDir, file);
    const sql = fs.readFileSync(filePath, 'utf8');

    console.log(`Running migration: ${file}`);
    try {
      await pool.query(sql);
      console.log(`✓ Successfully ran ${file}`);
    } catch (error) {
      console.error(`✗ Error running ${file}:`, error.message);
      throw error;
    }
  }

  console.log('All migrations completed successfully!');

  if (closePool) {
    await pool.end();
  }
}

module.exports = { runMigrations };

if (require.main === module) {
  runMigrations().catch((error) => {
    console.error('Migration failed:', error);
    process.exit(1);
  });
}
