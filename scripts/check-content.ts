/**
 * Validates every content file and runs every solution against its tests.
 *
 *   npm run content:check                       # everything
 *   npm run content:check -- python-for-data-science   # one course
 *   npm run content:check -- --no-run           # schema and references only
 *
 * Exit code 1 when anything is wrong, so the lesson builder can loop until it is clean.
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import YAML from "yaml";
import { CONTENT_DIR, ContentError, getCourse, getLesson, listTracks } from "../src/lib/content/loader";
import { CourseFile } from "../src/lib/content/schema";
import { pythonBin, runPython } from "../src/lib/runner";

const args = process.argv.slice(2);
const noRun = args.includes("--no-run");
const only = args.find((a) => !a.startsWith("--"));

const errors: string[] = [];
const warnings: string[] = [];
const err = (where: string, msg: string) => errors.push(`✗ ${where}: ${msg}`);
const warn = (where: string, msg: string) => warnings.push(`! ${where}: ${msg}`);

function guard<T>(fn: () => T): T | null {
  try {
    return fn();
  } catch (e) {
    if (e instanceof ContentError) e.issues.forEach((i) => err(e.file, i));
    else err("?", (e as Error).message);
    return null;
  }
}

async function main() {
  const tracks = guard(listTracks) ?? [];
  const courseDir = path.join(CONTENT_DIR, "courses");
  const allCourses = fs.existsSync(courseDir) ? fs.readdirSync(courseDir).filter((d) => fs.statSync(path.join(courseDir, d)).isDirectory()) : [];
  const inTracks = new Set(tracks.flatMap((t) => t.courses));

  for (const t of tracks)
    for (const c of t.courses) if (!allCourses.includes(c)) err(`tracks/${t.slug}.yaml`, `course "${c}" has no content/courses/${c}/course.yaml`);
  for (const c of allCourses) if (!inTracks.has(c)) warn(`courses/${c}`, "not part of any track, so it is not reachable from the UI");

  let exercisesChecked = 0;
  let solutionsRun = 0;
  const python = pythonBin();

  for (const slug of allCourses) {
    if (only && slug !== only) continue;
    const course = guard(() => getCourse(slug));
    if (!course) continue;
    for (const p of course.prerequisites) if (!allCourses.includes(p)) err(`courses/${slug}/course.yaml`, `prerequisite "${p}" does not exist`);

    // Lesson files on disk that the course does not list.
    const raw = CourseFile.parse(YAML.parse(fs.readFileSync(path.join(courseDir, slug, "course.yaml"), "utf8")));
    for (const ch of raw.chapters) {
      const dir = path.join(courseDir, slug, ch.id);
      if (fs.existsSync(dir))
        for (const f of fs.readdirSync(dir).filter((f) => f.endsWith(".yaml")))
          if (!ch.lessons.includes(f.replace(/\.yaml$/, ""))) warn(`courses/${slug}/${ch.id}/${f}`, "not listed in the chapter's lessons, so it is hidden");
    }
    const chapterIds = raw.chapters.map((c) => c.id);
    if (new Set(chapterIds).size !== chapterIds.length) err(`courses/${slug}/course.yaml`, "duplicate chapter ids");

    if (course.requires.length && !noRun) {
      const probe = spawnSync(python, ["-c", course.requires.map((r) => `import ${r.replace(/-/g, "_")}`).join("; ")], { encoding: "utf8" });
      if (probe.status !== 0) warn(`courses/${slug}`, `needs ${course.requires.join(", ")} but the runner cannot import them (pip install -r runner/requirements-ai.txt)`);
    }

    for (const ch of course.chapters)
      for (const l of ch.lessons) {
        const where = `courses/${slug}/${ch.id}/${l.id}.yaml`;
        if (l.error) {
          err(where, l.error.replace(/^[^:]+: /, ""));
          continue;
        }
        if (l.exercises === null) {
          warn(where, "listed in course.yaml but the file does not exist yet");
          continue;
        }
        const lesson = guard(() => getLesson(slug, ch.id, l.id));
        if (!lesson) continue;
        const ids = lesson.exercises.map((e) => e.id);
        if (new Set(ids).size !== ids.length) err(where, "duplicate exercise ids");
        if (lesson.exercises[0]?.type !== "video") warn(where, "lessons usually start with a video (slides) exercise");

        for (const e of lesson.exercises) {
          exercisesChecked++;
          if (noRun) continue;
          const at = `${where} → ${e.id}`;
          if (e.type === "coding") {
            solutionsRun++;
            const r = await runPython({ mode: "submit", pre_code: e.pre_code, code: e.solution, solution: e.solution, tests: e.tests, timeoutSec: e.timeout });
            if (!r.correct) err(at, `solution fails its own tests: ${r.error ?? r.feedback}`);
            if (e.sample_code.trim() === e.solution.trim()) err(at, "sample_code is identical to the solution");
            if (!/_{3,}/.test(e.sample_code) && e.sample_code.trim()) warn(at, "sample_code has no ____ blanks");
            // The sample code as given must not already pass.
            const s = await runPython({ mode: "submit", pre_code: e.pre_code, code: e.sample_code, solution: e.solution, tests: e.tests, timeoutSec: e.timeout });
            if (s.correct) err(at, "the untouched sample_code already passes the tests; the tests are too weak");
          }
          if (e.type === "sequential") {
            for (const [i, st] of e.steps.entries()) {
              solutionsRun++;
              const pre = [e.pre_code, ...e.steps.slice(0, i).map((x) => x.solution)].join("\n");
              const r = await runPython({ mode: "submit", pre_code: pre, code: st.solution, solution: st.solution, tests: st.tests, timeoutSec: e.timeout });
              if (!r.correct) err(`${at} step ${i + 1}`, `solution fails its own tests: ${r.error ?? r.feedback}`);
              const s = await runPython({ mode: "submit", pre_code: pre, code: st.sample_code, solution: st.solution, tests: st.tests, timeoutSec: e.timeout });
              if (s.correct) err(`${at} step ${i + 1}`, "the untouched sample_code already passes the tests");
            }
          }
          if (e.type === "mc" && e.pre_code?.trim()) {
            const r = await runPython({ mode: "run", pre_code: e.pre_code, code: "" });
            if (r.error) err(at, `pre_code fails: ${r.error}`);
          }
          if (e.type === "parsons" && e.lines.some((x) => (x.length - x.trimStart().length) % 4 !== 0))
            err(at, "parsons indentation must be multiples of 4 spaces");
          if ((e.type === "order" || e.type === "parsons") && new Set(e.type === "order" ? e.items : e.lines.map((x) => x.trim())).size !== (e.type === "order" ? e.items : e.lines).length)
            err(at, "items must be unique (duplicates make the order ambiguous)");
          if (e.type === "classify") {
            const texts = e.items.map((i) => i.text);
            if (new Set(texts).size !== texts.length) err(at, "item texts must be unique");
          }
        }
      }
  }

  for (const w of warnings) console.log(w);
  for (const e of errors) console.log(e);
  console.log(
    `\n${tracks.length} tracks, ${allCourses.length} courses, ${exercisesChecked} exercises checked` +
      (noRun ? " (solutions not run)" : `, ${solutionsRun} solutions run`) +
      `. ${errors.length} errors, ${warnings.length} warnings.`,
  );
  process.exit(errors.length ? 1 : 0);
}

main();
