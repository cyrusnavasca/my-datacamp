"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { CheckCircle2, X } from "lucide-react";
import { ExerciseIcon } from "@/components/ExerciseIcon";
import { cx } from "@/components/ui";
import type { ExerciseType } from "@/lib/content/schema";

export type OutlineChapter = {
  id: string;
  title: string;
  lessons: { id: string; title: string; exercises: { key: string; title: string; type: ExerciseType; href: string }[] }[];
};

export function Outline({
  open,
  onClose,
  chapters,
  currentKey,
  completed,
  courseTitle,
}: {
  open: boolean;
  onClose: () => void;
  chapters: OutlineChapter[];
  currentKey: string;
  completed: Set<string>;
  courseTitle: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => e.target === ref.current && onClose()}
      aria-label="Course outline"
      className="m-0 ml-auto h-dvh max-h-dvh w-[min(360px,100vw)] max-w-none bg-bg p-0 text-text shadow-pop backdrop:bg-text/30"
    >
      <div className="flex h-full flex-col">
        <div className="flex items-center justify-between border-b border-border p-4">
          <h2 className="truncate font-semibold">{courseTitle}</h2>
          <button className="rounded-md p-2 hover:bg-surface-2" onClick={onClose} aria-label="Close outline">
            <X className="size-4" aria-hidden />
          </button>
        </div>
        <ol className="flex-1 overflow-y-auto p-4">
          {chapters.map((c, i) => (
            <li key={c.id} className="mb-5">
              <p className="mb-1 text-sm font-semibold text-text-muted">
                Chapter {i + 1}: {c.title}
              </p>
              {c.lessons.map((l) => (
                <div key={l.id} className="mb-2">
                  <p className="px-2 py-1 text-sm font-medium">{l.title}</p>
                  <ul>
                    {l.exercises.map((e) => (
                      <li key={e.key}>
                        <Link
                          href={e.href}
                          onClick={onClose}
                          aria-current={e.key === currentKey ? "page" : undefined}
                          className={cx(
                            "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-surface",
                            e.key === currentKey && "bg-accent-soft text-accent-text",
                          )}
                        >
                          <ExerciseIcon type={e.type} />
                          <span className="min-w-0 flex-1 truncate">{e.title}</span>
                          {completed.has(e.key) && <CheckCircle2 className="size-4 text-success" aria-label="Done" />}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              {c.lessons.every((l) => l.exercises.length === 0) && <p className="px-2 text-sm text-text-muted">No lessons yet.</p>}
            </li>
          ))}
        </ol>
      </div>
    </dialog>
  );
}
