import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import type { TrackCourse } from "@/lib/course-progress";
import { Badge, ProgressBar, cx } from "./ui";

const LEVEL = { beginner: "Beginner", intermediate: "Intermediate", advanced: "Advanced" } as const;

export function StatusBadge({ state }: { state: "empty" | "todo" | "progress" | "done" }) {
  if (state === "done")
    return (
      <Badge tone="done">
        <CheckCircle2 className="size-3" aria-hidden /> Done
      </Badge>
    );
  if (state === "progress") return <Badge tone="progress">In progress</Badge>;
  if (state === "empty") return <span className="text-xs text-text-muted">Content coming</span>;
  return <span className="text-xs text-text-muted">Not started</span>;
}

/** Numbered course row inside a track (S03). A list, not a stack of cards. */
export function CourseStep({ n, item }: { n: number; item: TrackCourse }) {
  const { course, status, slug, error } = item;
  const state = status?.state ?? "empty";
  const muted = state === "empty";
  return (
    <li>
      <Link href={`/courses/${slug}`} className="group flex gap-5 py-5">
        <span
          className={cx("w-6 shrink-0 pt-0.5 text-right text-sm font-semibold tabular-nums", state === "progress" ? "text-accent-text" : "text-text-muted")}
          aria-hidden
        >
          {state === "done" ? <CheckCircle2 className="ml-auto size-4 text-success" /> : n}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <h3 className={cx("font-semibold break-words group-hover:underline", muted && "text-text-muted")}>{course?.title ?? slug}</h3>
            <StatusBadge state={state} />
          </div>
          {course && <p className="mt-1 line-clamp-2 text-sm text-text-muted">{course.description}</p>}
          <p className="mt-2 text-xs text-text-muted">
            {course
              ? [LEVEL[course.level], `${course.est_hours} h`, `${course.chapters.length} chapters`, status && status.total > 0 ? `${status.total} exercises` : null]
                  .filter(Boolean)
                  .join(" · ")
              : <span className="text-danger">{error ?? "course.yaml missing"}</span>}
          </p>
          {status && status.state === "progress" && (
            <div className="mt-3 max-w-sm">
              <ProgressBar value={status.done} max={status.total} label={`${course?.title} progress`} thin />
            </div>
          )}
        </div>
      </Link>
    </li>
  );
}
