const fs = require("node:fs");
const path = require("node:path");
const initSqlJs = require("sql.js");

async function createDatabase({ dbPath, migrationsDir, logger = () => {} }) {
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });

  const SQL = await initSqlJs({
    locateFile(file) {
      return require.resolve(`sql.js/dist/${file}`);
    },
  });

  const db = fs.existsSync(dbPath)
    ? new SQL.Database(fs.readFileSync(dbPath))
    : new SQL.Database();

  const persist = () => {
    const data = db.export();
    fs.writeFileSync(dbPath, Buffer.from(data));
  };

  db.run(`
    CREATE TABLE IF NOT EXISTS schema_migrations (
      name TEXT PRIMARY KEY,
      applied_at TEXT NOT NULL
    );
  `);

  const migrationFiles = fs
    .readdirSync(migrationsDir)
    .filter((file) => file.endsWith(".sql"))
    .sort();

  for (const file of migrationFiles) {
    const alreadyApplied = get(
      db,
      "SELECT name FROM schema_migrations WHERE name = ?",
      [file]
    );
    if (alreadyApplied) {
      continue;
    }

    const sql = fs.readFileSync(path.join(migrationsDir, file), "utf8");
    logger(`applying migration ${file}`);
    db.run(sql);
    db.run(
      "INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?)",
      [file, new Date().toISOString()]
    );
  }

  persist();

  return {
    dbPath,
    run(sql, params = []) {
      db.run(sql, params);
      persist();
    },
    get(sql, params = []) {
      return get(db, sql, params);
    },
    all(sql, params = []) {
      return all(db, sql, params);
    },
    persist,
  };
}

function get(db, sql, params = []) {
  const stmt = db.prepare(sql, params);
  try {
    if (!stmt.step()) {
      return null;
    }
    return stmt.getAsObject();
  } finally {
    stmt.free();
  }
}

function all(db, sql, params = []) {
  const stmt = db.prepare(sql, params);
  const rows = [];
  try {
    while (stmt.step()) {
      rows.push(stmt.getAsObject());
    }
    return rows;
  } finally {
    stmt.free();
  }
}

module.exports = {
  createDatabase,
};
