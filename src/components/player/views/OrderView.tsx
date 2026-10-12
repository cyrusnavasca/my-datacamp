"use client";

import { DndContext, KeyboardSensor, PointerSensor, closestCenter, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, arrayMove, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useId, useState } from "react";
import { GripVertical, IndentDecrease, IndentIncrease } from "lucide-react";
import { Markdown } from "@/components/Markdown";
import { Button, cx } from "@/components/ui";
import type { PublicExercise } from "@/lib/exercises";
import { api } from "../api";
import { HintControls } from "../HintControls";
import type { ViewApi } from "../Player";
import { ExerciseTitle } from "./Split";

type Ordering = Extract<PublicExercise, { type: "order" | "parsons" }>;
type Row = { id: string; text: string; indent: number };

const INDENT = "    ";

/** "order": put items in sequence. "parsons": arrange and indent lines of code. */
export function OrderView({ exercise: e, view }: { exercise: Ordering; view: ViewApi }) {
  const isCode = e.type === "parsons";
  const source = isCode ? e.lines : e.items;
  const [rows, setRows] = useState<Row[]>(() => source.map((text, i) => ({ id: `r${i}`, text, indent: 0 })));
  const [wrong, setWrong] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState(false);
  const dndId = useId();
  const sensors = useSensors(useSensor(PointerSensor), useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }));

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    setRows((r) => arrayMove(r, r.findIndex((x) => x.id === active.id), r.findIndex((x) => x.id === over.id)));
    setWrong(new Set());
  };
  const indent = (id: string, d: number) => {
    setRows((r) => r.map((x) => (x.id === id ? { ...x, indent: Math.max(0, Math.min(4, x.indent + d)) } : x)));
    setWrong(new Set());
  };
  const answer = () => rows.map((r) => (isCode ? INDENT.repeat(r.indent) : "") + r.text);

  const submit = async () => {
    setBusy(true);
    view.clearFeedback();
    try {
      const r = await api.submit(view.exerciseKey, { answer: answer() });
      setWrong(new Set(r.wrong ?? []));
      view.onResult(r);
    } catch (err) {
      view.onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl space-y-5 p-5 py-10">
        <ExerciseTitle title={e.title} kind={isCode ? "Arrange the code" : "Put in order"} />
        <Markdown>{e.prompt}</Markdown>
        <p className="text-xs text-text-muted">
          Drag to reorder, or focus a handle and press Space, then the arrow keys.{isCode && " Use the indent buttons to set the indentation."}
        </p>
        <DndContext id={dndId} sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
          <SortableContext items={rows.map((r) => r.id)} strategy={verticalListSortingStrategy}>
            <ol className={cx("space-y-2", isCode && "rounded-lg bg-code-bg p-3")}>
              {rows.map((r, i) => (
                <SortableRow key={r.id} row={r} isCode={isCode} wrong={wrong.has(i)} onIndent={indent} disabled={view.done} />
              ))}
            </ol>
          </SortableContext>
        </DndContext>
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={submit} loading={busy} disabled={view.done}>
            Check order
          </Button>
          <span className="text-xs text-text-muted tabular-nums">{view.done ? `${view.xpNow} XP earned` : `${view.xpNow} XP`}</span>
        </div>
        <HintControls
          baseXp={e.xp}
          hint={view.hint}
          hintUsed={view.hintUsed}
          solutionUsed={view.solutionUsed}
          done={view.done}
          onHint={() => view.takeHint()}
          onSolution={async () => {
            const r = await view.revealSolution();
            if (Array.isArray(r.answer))
              setRows(
                r.answer.map((line, i) => {
                  const indentLen = line.length - line.trimStart().length;
                  return { id: `s${i}`, text: line.trim(), indent: Math.round(indentLen / 4) };
                }),
              );
            setWrong(new Set());
          }}
        />
        {view.feedback}
      </div>
    </div>
  );
}

function SortableRow({ row, isCode, wrong, onIndent, disabled }: { row: Row; isCode: boolean; wrong: boolean; onIndent: (id: string, d: number) => void; disabled: boolean }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: row.id, disabled });
  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cx(
        "flex items-center gap-2 rounded-md border p-2",
        isCode ? "border-code-surface bg-code-surface font-mono text-sm text-code-text" : "border-border bg-bg text-sm",
        wrong && "border-danger",
        isDragging && "z-10 shadow-pop",
      )}
    >
      <button {...attributes} {...listeners} className="cursor-grab touch-none rounded p-1 text-text-muted" aria-label={`Move: ${row.text}`}>
        <GripVertical className="size-4" aria-hidden />
      </button>
      <span className="min-w-0 flex-1 break-words whitespace-pre-wrap" style={{ paddingLeft: `${row.indent * 2}ch` }}>
        {row.text}
      </span>
      {isCode && !disabled && (
        <span className="flex shrink-0">
          <button className="rounded p-1 text-code-muted hover:text-code-text" onClick={() => onIndent(row.id, -1)} aria-label={`Unindent: ${row.text}`} disabled={row.indent === 0}>
            <IndentDecrease className="size-4" aria-hidden />
          </button>
          <button className="rounded p-1 text-code-muted hover:text-code-text" onClick={() => onIndent(row.id, 1)} aria-label={`Indent: ${row.text}`}>
            <IndentIncrease className="size-4" aria-hidden />
          </button>
        </span>
      )}
    </li>
  );
}
