-- Non-blocking index for PR file-count backfill (must be the only statement in this migration).
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_events_pr_files_changed_backfill
  ON activity_events (repo_id)
  WHERE event_type = 'pr' AND files_changed IS NULL;
