ALTER TABLE publish_runs
ADD COLUMN execution_mode TEXT NOT NULL DEFAULT 'mock';
