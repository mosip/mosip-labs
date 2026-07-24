-- Support GitHub issue sync: watermark on repos, counter on repo_users.
ALTER TABLE repos ADD COLUMN IF NOT EXISTS last_issues_sync_at TIMESTAMP;

ALTER TABLE repo_users ADD COLUMN IF NOT EXISTS issues_count INTEGER DEFAULT 0;
