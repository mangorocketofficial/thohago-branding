CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  shop_display_name TEXT NOT NULL,
  summary TEXT DEFAULT '',
  project_folder_path TEXT NOT NULL,
  media_folder_path TEXT NOT NULL,
  hero_media_asset_id TEXT DEFAULT NULL,
  preflight_json TEXT DEFAULT NULL,
  status TEXT NOT NULL DEFAULT 'created',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS media_assets (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  source_file_path TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_name TEXT NOT NULL,
  mime_type TEXT DEFAULT NULL,
  experience_order INTEGER NOT NULL DEFAULT 0,
  is_hero INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interview_sessions (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'pending',
  preflight_json TEXT DEFAULT NULL,
  turn1_question TEXT DEFAULT NULL,
  turn1_answer TEXT DEFAULT NULL,
  turn2_question TEXT DEFAULT NULL,
  turn2_answer TEXT DEFAULT NULL,
  turn3_question TEXT DEFAULT NULL,
  turn3_answer TEXT DEFAULT NULL,
  planner_turn2_json TEXT DEFAULT NULL,
  planner_turn3_json TEXT DEFAULT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
