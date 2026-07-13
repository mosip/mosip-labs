-- Assignable user roles and tracked organizations (lookup/reference tables).
-- Default rows are seeded here via migration, same as other schema tables.
-- To add more later, copy migrations/009_add_lookup_values.sql.example to a new
-- numbered .sql file and run npm run migrate.

CREATE TABLE IF NOT EXISTS user_roles (
  id SERIAL PRIMARY KEY,
  name VARCHAR(50) NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS organizations (
  id SERIAL PRIMARY KEY,
  slug VARCHAR(255) NOT NULL UNIQUE,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO user_roles (name) VALUES
  ('Developer'),
  ('Tech Lead'),
  ('Architect'),
  ('Product Owner'),
  ('Leadership'),
  ('QA Engineer'),
  ('DevOps Engineer')
ON CONFLICT (name) DO NOTHING;

INSERT INTO organizations (slug, name) VALUES
  ('mosip', 'MOSIP'),
  ('inji', 'INJI')
ON CONFLICT (slug) DO NOTHING;
