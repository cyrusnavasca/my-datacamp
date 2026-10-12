# Components: my-datacamp

All colours via tokens (`bg-surface`, `text-muted`, `bg-code-bg` ...), never raw hex.
Icons: Lucide (`lucide-react`, ISC). Fonts: Inter + JetBrains Mono (OFL). No DataCamp
assets, mascot or copy. Focus ring everywhere: 2px `accent` ring, 2px offset.

```
Button
  variants  primary, secondary, ghost, danger
  sizes     sm 32px, md 40px, lg 48px
  states    default, hover, active, focus-visible, disabled, loading (spinner, label kept for SR)
  tokens    primary: bg accent / on-accent; secondary: bg surface-2 / text; ghost: transparent / text; danger: bg danger / white
            radius md, text sm/600
  a11y      real <button>, or <a> when it navigates
  used on   all

ProgressBar
  variants  thin (4px), labelled (8px + "n of m")
  states    0, partial, 100 (success colour)
  tokens    track surface-2, fill accent, done success
  a11y      role=progressbar, aria-valuenow/min/max, aria-label
  used on   S01, S02, S03, S04, S12

Stats (replaces StatTile after the unslop-ui pass)
  one row of numbers, no boxes or icons; label sm text-muted, value xl/600; thin rules above, below and between
  used on   S01, S11, S12

TrackCard / CourseCard
  states    not started, in progress (progress bar), done (check badge)
  tokens    bg bg, border border, radius lg, no shadow, hover border-input
  a11y      whole card is one link; title is the link text
  used on   S01, S02, S03

CourseStep (numbered course in a track)
  states    todo, current (accent ring on number), done (success check), empty (no content yet: muted, "Content coming")
  used on   S03

ChapterAccordion + LessonRow
  states    collapsed, expanded; row: todo, current, done
  tokens    row icon by exercise type (Lucide: PlayCircle video, Code2 coding, ListChecks mc, GripVertical drag)
  a11y      <details>/<summary> or button with aria-expanded
  used on   S04, S13

StatusBadge
  variants  todo, in-progress (accent-soft), done (success-soft), empty (surface-2)
  tokens    text xs/500, radius pill

XPCounter (player header, plain text)
  states    default, gain ("+100" float, 700ms, respects prefers-reduced-motion)
  tokens    text, icon in xp colour; no pill background

ExerciseDots (player header)
  one dot per exercise in the lesson: todo (border), current (accent), done (success)
  a11y      nav with links, aria-current on current

PlayerLayout
  header 52px: back link, course/lesson title, ExerciseDots, XPCounter, outline button
  body: left pane 38% (context, instructions, hint/solution) on bg; right pane (editor + console) on code-bg
  < 900px: stacked
  used on   S05-S09

SlideViewer (video exercise)
  markdown slides split by "---", prev/next, slide n of m, keyboard arrows
  tokens    slide bg surface, radius lg, prose base
  used on   S05

CodeEditor
  CodeMirror 6, python mode, theme from code-* tokens, line numbers, ____ placeholders highlighted (xp-soft)
  states    editable, read-only (solution view), running (dim + spinner on Run)
  keys      Ctrl/Cmd+Enter run, Ctrl/Cmd+Shift+Enter submit
  used on   S06, S07 (console), S09

Console
  tabs      Output, Plots (when images)
  states    empty ("Run your code to see output"), running, stdout, error (code-error), timeout
  tokens    bg code-bg, text code-text mono sm
  a11y      aria-live=polite on result region

Instructions
  numbered list, xp shown top right ("100 XP")
  HintPanel below: "Take hint (-30 XP)" ghost button -> reveals hint box (xp-soft bg)
                   "Show answer (-70 XP)" ghost button -> loads solution into editor read-only diff
  used on   S06, S07, S09

FeedbackToast (inline banner under the editor, not floating)
  variants  success (success-soft, CheckCircle2), incorrect (danger-soft, XCircle), error (danger-soft, AlertTriangle)
  success shows "+n XP" and Continue button (autofocus)
  a11y      role=status (success) / role=alert (incorrect)

OptionList (multiple choice)
  radio group; states: unselected, selected (accent border), wrong (danger border + feedback under it), correct (success)
  a11y      fieldset/legend, real radios, arrow keys

DragList (order / parsons) and ClassifyBoard
  @dnd-kit sortable; keyboard sorting (space to lift, arrows to move)
  parsons: indent buttons (← →) per line, mono text
  states    idle, dragging (shadow pop), checked-wrong (danger border on misplaced), correct
  used on   S08

StepTabs (sequential)
  step 1..n, done steps get check, only current is editable
  used on   S09

Modal
  chapter complete (S10): XP earned, exercises done, Next chapter primary
  confirm reset (S14): danger
  a11y      dialog element, focus trap, Esc closes, returns focus

Drawer (course outline S13)
  right side, 360px, overlay < 900px; Esc closes

TopNav
  logo text "my-datacamp" (no mascot), links Dashboard / Tracks / Progress, XP pill, streak flame, settings icon
  active link: text accent-text + 2px underline

EmptyState
  icon + one line + action; e.g. "No lessons in this course yet. Run the lesson builder to add some."
```

## Restraint rules (unslop-ui pass, 2026-10-06)

- Shadows only for real elevation: dialogs, drawer, the item being dragged. Cards use a border, not border plus shadow.
- No tinted box per stat, no icon in front of every label. Numbers and type size carry the hierarchy.
- Amber (`xp`) is for the XP icon and success-adjacent numbers only, never a background fill.
- Lists of courses, progress rows and classify items are rows with dividers, not stacks of cards.
- No uppercase tracked eyebrows; small muted sentence-case labels instead.
- Opaque header, no backdrop blur. No decorative icons (confetti and the like).
