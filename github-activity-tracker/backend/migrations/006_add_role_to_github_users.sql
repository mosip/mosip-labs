-- Job role for team members (set manually until admin update API exists).
-- Allowed values: Developer, Tech Lead, Architect, Product Owner, Leadership, QA Engineer, DevOps Engineer
ALTER TABLE github_users
  ADD COLUMN IF NOT EXISTS role VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_github_users_role ON github_users(role);
