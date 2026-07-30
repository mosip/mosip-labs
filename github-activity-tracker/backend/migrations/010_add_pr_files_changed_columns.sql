-- Track file changes per PR event and aggregate per repo/user.
ALTER TABLE activity_events ADD COLUMN IF NOT EXISTS files_changed INTEGER;

ALTER TABLE repo_users ADD COLUMN IF NOT EXISTS pr_files_changed_total INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_activity_events_pr_files_changed_backfill
  ON activity_events (repo_id)
  WHERE event_type = 'pr' AND files_changed IS NULL;
