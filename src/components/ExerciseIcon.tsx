import { Code2, GripVertical, Layers, ListChecks, PlayCircle, Shapes } from "lucide-react";
import type { ExerciseType } from "@/lib/content/schema";

const ICONS = {
  video: { Icon: PlayCircle, label: "Lesson slides" },
  coding: { Icon: Code2, label: "Coding exercise" },
  mc: { Icon: ListChecks, label: "Multiple choice" },
  order: { Icon: GripVertical, label: "Put in order" },
  parsons: { Icon: GripVertical, label: "Arrange the code" },
  classify: { Icon: Shapes, label: "Sort into groups" },
  sequential: { Icon: Layers, label: "Multi-step exercise" },
} as const;

export function ExerciseIcon({ type, className = "size-4 text-text-muted" }: { type: ExerciseType; className?: string }) {
  const { Icon, label } = ICONS[type];
  return <Icon className={className} aria-label={label} />;
}

export const exerciseTypeLabel = (t: ExerciseType) => ICONS[t].label;
