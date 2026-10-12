import { z } from "zod";

// The contract between the app and whoever writes lessons (the lesson-builder agent).
// Every content file is validated against these schemas; see content/README.md.

const slug = z
  .string()
  .regex(/^[a-z0-9]+(-[a-z0-9]+)*$/, "use lowercase-kebab-case (a-z, 0-9, -)");

const markdown = z.string().min(1);

export const DEFAULT_XP = {
  video: 50,
  coding: 100,
  mc: 50,
  order: 50,
  parsons: 50,
  classify: 50,
  sequential: 100,
} as const;

const base = {
  id: slug,
  title: z.string().min(1).max(120),
  xp: z.number().int().positive().max(1000).optional(),
};

const codeFields = {
  context: markdown,
  instructions: z.array(markdown).min(1).max(6),
  hint: markdown,
  pre_code: z.string().default(""),
  sample_code: z.string(),
  solution: z.string().min(1),
  tests: z.string().min(1),
  success_msg: z.string().optional(),
  timeout: z.number().int().positive().max(300).optional(),
};

export const VideoExercise = z.object({
  ...base,
  type: z.literal("video"),
  slides: markdown,
});

export const CodingExercise = z.object({
  ...base,
  type: z.literal("coding"),
  ...codeFields,
});

export const McExercise = z.object({
  ...base,
  type: z.literal("mc"),
  question: markdown,
  context: markdown.optional(),
  options: z
    .array(z.object({ text: markdown, correct: z.boolean().default(false), feedback: markdown }))
    .min(2)
    .max(6)
    .refine((o) => o.filter((x) => x.correct).length === 1, "exactly one option must have correct: true"),
  hint: markdown,
  // When set, the learner gets a console to explore with this code preloaded.
  pre_code: z.string().optional(),
});

export const OrderExercise = z.object({
  ...base,
  type: z.literal("order"),
  prompt: markdown,
  hint: markdown,
  items: z.array(z.string().min(1)).min(2).max(12), // listed in the correct order
});

export const ParsonsExercise = z.object({
  ...base,
  type: z.literal("parsons"),
  prompt: markdown,
  hint: markdown,
  // Correct order. Indentation (multiples of 4 spaces) is part of the answer.
  lines: z.array(z.string().min(1)).min(2).max(15),
});

export const ClassifyExercise = z
  .object({
    ...base,
    type: z.literal("classify"),
    prompt: markdown,
    hint: markdown,
    zones: z.array(z.string().min(1)).min(2).max(4),
    items: z.array(z.object({ text: z.string().min(1), zone: z.string().min(1) })).min(2).max(12),
  })
  .refine((e) => e.items.every((i) => e.zones.includes(i.zone)), "every item.zone must be one of zones");

export const SequentialStep = z.object({
  instructions: z.array(markdown).min(1).max(6),
  hint: markdown,
  sample_code: z.string(),
  solution: z.string().min(1),
  tests: z.string().min(1),
});

export const SequentialExercise = z.object({
  ...base,
  type: z.literal("sequential"),
  context: markdown,
  pre_code: z.string().default(""),
  steps: z.array(SequentialStep).min(2).max(6),
  success_msg: z.string().optional(),
  timeout: z.number().int().positive().max(300).optional(),
});

export const Exercise = z.union([
  VideoExercise,
  CodingExercise,
  McExercise,
  OrderExercise,
  ParsonsExercise,
  ClassifyExercise,
  SequentialExercise,
]);

export const LessonFile = z.object({
  title: z.string().min(1).max(120),
  description: z.string().optional(),
  exercises: z.array(Exercise).min(1),
});

export const ChapterDef = z.object({
  id: slug,
  title: z.string().min(1).max(120),
  description: z.string().default(""),
  // Lesson ids, in order. Each must have a file <course>/<chapter-id>/<lesson-id>.yaml.
  lessons: z.array(slug).default([]),
});

export const CourseFile = z.object({
  title: z.string().min(1).max(120),
  description: z.string().min(1),
  language: z.enum(["python"]).default("python"),
  level: z.enum(["beginner", "intermediate", "advanced"]).default("beginner"),
  est_hours: z.number().positive().max(40).default(4),
  prerequisites: z.array(slug).default([]),
  // What the learner can do after the course; guides the lesson builder.
  objectives: z.array(z.string()).default([]),
  // Extra pip packages the runner needs for this course (informational, checked by content:check).
  requires: z.array(z.string()).default([]),
  chapters: z.array(ChapterDef).min(1).max(8),
});

export const TrackFile = z.object({
  title: z.string().min(1).max(120),
  description: z.string().min(1),
  order: z.number().int().default(0),
  courses: z.array(slug).min(1),
});

export type Exercise = z.infer<typeof Exercise>;
export type ExerciseType = Exercise["type"];
export type LessonFile = z.infer<typeof LessonFile>;
export type CourseFile = z.infer<typeof CourseFile>;
export type TrackFile = z.infer<typeof TrackFile>;
export type SequentialStep = z.infer<typeof SequentialStep>;

export function exerciseXp(e: Exercise): number {
  return e.xp ?? DEFAULT_XP[e.type];
}
