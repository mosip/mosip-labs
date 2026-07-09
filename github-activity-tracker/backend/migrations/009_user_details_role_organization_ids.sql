-- Store role/organization assignments as FKs to user_roles and organizations.

ALTER TABLE user_details
  ADD COLUMN IF NOT EXISTS role_id INTEGER REFERENCES user_roles(id),
  ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES organizations(id);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'user_details'
      AND column_name = 'role'
  ) THEN
    UPDATE user_details ud
    SET role_id = ur.id
    FROM user_roles ur
    WHERE ud.role IS NOT NULL
      AND ur.name = ud.role
      AND ud.role_id IS NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'user_details'
      AND column_name = 'organization'
  ) THEN
    UPDATE user_details ud
    SET organization_id = o.id
    FROM organizations o
    WHERE ud.organization IS NOT NULL
      AND o.slug = LOWER(ud.organization)
      AND ud.organization_id IS NULL;
  END IF;
END $$;

ALTER TABLE user_details
  DROP COLUMN IF EXISTS role,
  DROP COLUMN IF EXISTS organization;

DROP INDEX IF EXISTS idx_user_details_role;
CREATE INDEX IF NOT EXISTS idx_user_details_role_id ON user_details(role_id);
CREATE INDEX IF NOT EXISTS idx_user_details_organization_id ON user_details(organization_id);
