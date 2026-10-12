import fs from "node:fs";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";

// One SQLite file for all learner state. Content never goes in here.
// Migrations: src/lib/db/migrations/NNN_name.sql, applied in order on first
// connection; `pragma user_version` records the last one applied. Never edit
// an applied migration; add a new file.

const DB_PATH = process.env.PROGRESS_DB ?? path.join(process.cwd(), "data", "progress.db");
const MIGRATIONS = path.join(process.cwd(), "src", "lib", "db", "migrations");

const globalForDb = globalThis as unknown as { __db?: DatabaseSync; __migrationsMtime?: number };

export function migrate(d: DatabaseSync) {
  const current = Number((d.prepare("pragma user_version").get() as { user_version: number }).user_version);
  const files = fs
    .readdirSync(MIGRATIONS)
    .filter((f) => /^\d{3}_.+\.sql$/.test(f))
    .sort();
  for (const f of files) {
    const version = Number(f.slice(0, 3));
    if (version <= current) continue;
    d.exec("begin");
    try {
      d.exec(fs.readFileSync(path.join(MIGRATIONS, f), "utf8"));
      d.exec(`pragma user_version = ${version}`);
      d.exec("commit");
    } catch (e) {
      d.exec("rollback");
      throw new Error(`migration ${f} failed: ${(e as Error).message}`);
    }
  }
}

const migrationsMtime = () => fs.statSync(MIGRATIONS).mtimeMs;

export function db(): DatabaseSync {
  // The connection outlives hot reloads in dev, so a migration added while
  // `next dev` runs would never apply. Re-check when the folder changes.
  if (globalForDb.__db && process.env.NODE_ENV !== "production" && migrationsMtime() !== globalForDb.__migrationsMtime) {
    migrate(globalForDb.__db);
    globalForDb.__migrationsMtime = migrationsMtime();
  }
  if (!globalForDb.__db) {
    if (DB_PATH !== ":memory:") fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
    const d = new DatabaseSync(DB_PATH);
    d.exec("pragma journal_mode = wal; pragma foreign_keys = on; pragma busy_timeout = 3000;");
    migrate(d);
    globalForDb.__db = d;
    globalForDb.__migrationsMtime = migrationsMtime();
  }
  return globalForDb.__db;
}

/** Test helper: drop the cached connection (used with PROGRESS_DB=:memory:). */
export function resetDbForTests() {
  globalForDb.__db?.close();
  globalForDb.__db = undefined;
}
