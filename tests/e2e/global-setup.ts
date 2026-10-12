import fs from "node:fs";

export default function globalSetup() {
  for (const f of ["data/e2e.db", "data/e2e.db-wal", "data/e2e.db-shm"]) fs.rmSync(f, { force: true });
}
