-- GitHub profile display name (from GET /users/{login} or GraphQL User.name).
ALTER TABLE github_users
  ADD COLUMN IF NOT EXISTS name VARCHAR(255);
