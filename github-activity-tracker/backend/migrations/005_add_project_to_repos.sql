-- Add project identifier to repos so activity can be filtered per project.
ALTER TABLE repos ADD COLUMN IF NOT EXISTS project_id VARCHAR(255);

-- Backfill existing rows (legacy MOSIP data) before enforcing NOT NULL.
UPDATE repos SET project_id = 'mosip' WHERE project_id IS NULL;

ALTER TABLE repos ALTER COLUMN project_id SET NOT NULL;
ALTER TABLE repos ALTER COLUMN project_id SET DEFAULT 'mosip';

CREATE INDEX IF NOT EXISTS idx_repos_project_id ON repos(project_id);
