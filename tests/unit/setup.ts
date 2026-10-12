import path from "node:path";

process.env.CONTENT_DIR = path.join(import.meta.dirname, "fixtures", "content");
process.env.PROGRESS_DB = ":memory:";
