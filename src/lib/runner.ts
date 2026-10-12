import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { DATA_DIR } from "./content/loader";

const RESULT_MARKER = "\x00__MYDC_RESULT__\x00";
const HARNESS = path.join(process.cwd(), "runner", "harness.py");

export type RunRequest = {
  mode: "run" | "submit";
  pre_code?: string;
  code: string;
  solution?: string;
  tests?: string;
  timeoutSec?: number;
};

export type RunResult = {
  stdout: string;
  error: string | null;
  images: string[];
  correct?: boolean;
  feedback?: string;
  ms: number;
  timedOut?: boolean;
};

export function pythonBin() {
  if (process.env.PYTHON) return process.env.PYTHON;
  const venv = path.join(process.cwd(), ".venv", "bin", "python");
  return fs.existsSync(venv) ? venv : "python3";
}

/**
 * Runs learner code in a fresh Python process. This executes arbitrary code on
 * this machine, which is why the dev server only listens on 127.0.0.1.
 */
export function runPython(req: RunRequest): Promise<RunResult> {
  const started = Date.now();
  const timeoutMs = (req.timeoutSec ?? 30) * 1000;
  return new Promise((resolve) => {
    const child = spawn(pythonBin(), ["-u", HARNESS], {
      cwd: process.cwd(),
      env: { ...process.env, MPLBACKEND: "Agg", PYTHONHASHSEED: "0" },
      detached: true, // own process group so a timeout kills everything it started
      stdio: ["pipe", "pipe", "pipe"],
    });
    let out = "";
    let err = "";
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      try {
        process.kill(-child.pid!, "SIGKILL");
      } catch {
        child.kill("SIGKILL");
      }
    }, timeoutMs);

    child.stdout.on("data", (d) => (out += d));
    child.stderr.on("data", (d) => (err += d));
    child.on("error", (e) => {
      clearTimeout(timer);
      resolve({ stdout: "", error: `Could not start Python (${pythonBin()}): ${e.message}. Run \`npm run setup:python\`.`, images: [], ms: Date.now() - started });
    });
    child.on("close", () => {
      clearTimeout(timer);
      const ms = Date.now() - started;
      if (timedOut) {
        resolve({ stdout: out.slice(0, 20000), error: `Stopped after ${timeoutMs / 1000}s. Is there an infinite loop?`, images: [], ms, timedOut: true, correct: false, feedback: "Your code took too long to run." });
        return;
      }
      const i = out.lastIndexOf(RESULT_MARKER);
      if (i === -1) {
        resolve({ stdout: out, error: err.trim() || "The runner exited without a result.", images: [], ms, correct: false, feedback: "Something went wrong running your code." });
        return;
      }
      const parsed = JSON.parse(out.slice(i + RESULT_MARKER.length).trim()) as Omit<RunResult, "ms">;
      resolve({ ...parsed, ms });
    });

    child.stdin.end(
      JSON.stringify({
        mode: req.mode,
        pre_code: req.pre_code ?? "",
        code: req.code,
        solution: req.solution ?? "",
        tests: req.tests ?? "",
        data_dir: DATA_DIR,
      }),
    );
  });
}
