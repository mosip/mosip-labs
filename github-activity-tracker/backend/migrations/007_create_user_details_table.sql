-- User role/organization assignments with history. One active row per user at a time.
-- Lookup tables (user_roles, organizations) are created at app startup from .env.

CREATE TABLE IF NOT EXISTS user_details (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES github_users(id) ON DELETE CASCADE,
  role_id INTEGER REFERENCES user_roles(id),
  organization_id INTEGER REFERENCES organizations(id),
  active BOOLEAN NOT NULL DEFAULT true,
  active_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  active_to TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE user_details
  ADD COLUMN IF NOT EXISTS role_id INTEGER REFERENCES user_roles(id),
  ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES organizations(id);

ALTER TABLE user_details
  DROP COLUMN IF EXISTS login,
  DROP COLUMN IF EXISTS name,
  DROP COLUMN IF EXISTS github_user_id;

CREATE INDEX IF NOT EXISTS idx_user_details_user_id ON user_details(user_id);
CREATE INDEX IF NOT EXISTS idx_user_details_role_id ON user_details(role_id);
CREATE INDEX IF NOT EXISTS idx_user_details_organization_id ON user_details(organization_id);
CREATE INDEX IF NOT EXISTS idx_user_details_active_from ON user_details(active_from);
CREATE INDEX IF NOT EXISTS idx_user_details_active_to ON user_details(active_to);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_details_one_active_per_user
  ON user_details(user_id)
  WHERE active = true;

-- GitHub profile name lives on github_users; assignments live in user_details.
ALTER TABLE github_users
  ADD COLUMN IF NOT EXISTS name VARCHAR(255);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'user_details'
      AND column_name = 'name'
  ) THEN
    UPDATE github_users u
    SET
      name = ud.name,
      updated_at = CURRENT_TIMESTAMP
    FROM user_details ud
    WHERE ud.user_id = u.id
      AND ud.active = true
      AND ud.name IS NOT NULL
      AND (u.name IS NULL OR u.name = '');
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'github_users'
      AND column_name = 'role'
  ) THEN
    INSERT INTO user_details (user_id, role_id, active, active_from, active_to)
    SELECT
      u.id,
      ur.id,
      true,
      COALESCE(u.updated_at, u.inserted_at, CURRENT_TIMESTAMP),
      NULL
    FROM github_users u
    JOIN user_roles ur ON ur.name = u.role
    WHERE u.role IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM user_details ud WHERE ud.user_id = u.id AND ud.active = true
      );
  END IF;
END $$;

DROP INDEX IF EXISTS idx_github_users_role;
ALTER TABLE github_users
  DROP COLUMN IF EXISTS role;
