CREATE TABLE IF NOT EXISTS generation_runs (
  id TEXT PRIMARY KEY,
  content_spec_id TEXT NOT NULL REFERENCES content_specs(id) ON DELETE CASCADE,
  mode TEXT NOT NULL,
  directive_json TEXT NOT NULL,
  spec_json TEXT NOT NULL,
  artifact_path TEXT DEFAULT NULL,
  preview_artifact_path TEXT DEFAULT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
