CREATE TABLE IF NOT EXISTS publish_runs (
  id TEXT PRIMARY KEY,
  content_spec_id TEXT NOT NULL REFERENCES content_specs(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  status TEXT NOT NULL,
  permalink TEXT DEFAULT NULL,
  result_json TEXT NOT NULL,
  artifact_path TEXT DEFAULT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
