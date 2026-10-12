import { StatusBadge } from "@/components/CourseCard";
import { ExerciseIcon, exerciseTypeLabel } from "@/components/ExerciseIcon";
import { Markdown } from "@/components/Markdown";
import { Button, Card, EmptyState, PageHeader, ProgressBar, Stats } from "@/components/ui";
import type { ExerciseType } from "@/lib/content/schema";

// Design-system check page (replica-design step 4). Not linked from the nav.

const COLORS = [
  "bg", "surface", "surface-2", "border", "border-input", "text", "text-muted", "accent", "accent-soft", "accent-text",
  "danger", "danger-soft", "success", "success-soft", "xp", "xp-soft", "code-bg", "code-surface", "code-text",
];
const TYPES: ExerciseType[] = ["video", "coding", "mc", "order", "parsons", "classify", "sequential"];

export default function DesignPage() {
  return (
    <div className="space-y-12">
      <PageHeader title="Design system">Tokens and primitives, in the current theme.</PageHeader>

      <section>
        <h2 className="mb-3 text-lg">Colour roles</h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6">
          {COLORS.map((c) => (
            <div key={c} className="overflow-hidden rounded-md border border-border">
              <div className="h-12" style={{ background: `var(--c-${c})` }} />
              <p className="p-2 font-mono text-xs">{c}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg">Type scale</h2>
        <p className="text-display">Display 40</p>
        <p className="text-xl">Heading 28</p>
        <p className="text-lg">Title 20</p>
        <p className="text-base">Body 16. The quick brown fox jumps over the lazy dog.</p>
        <p className="text-sm text-text-muted">Small 14, muted.</p>
        <p className="text-xs">Caption 12</p>
        <p className="font-mono text-sm">mono: df.groupby(&quot;team&quot;).mean()</p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg">Buttons</h2>
        {(["sm", "md", "lg"] as const).map((size) => (
          <div key={size} className="flex flex-wrap gap-2">
            <Button size={size}>Primary</Button>
            <Button size={size} variant="secondary">
              Secondary
            </Button>
            <Button size={size} variant="ghost">
              Ghost
            </Button>
            <Button size={size} variant="danger">
              Danger
            </Button>
            <Button size={size} disabled>
              Disabled
            </Button>
            <Button size={size} loading>
              Loading
            </Button>
          </div>
        ))}
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <Card>
          <h2 className="mb-3 font-semibold">Progress and badges</h2>
          <div className="space-y-3">
            <ProgressBar value={0} max={10} label="empty" />
            <ProgressBar value={4} max={10} label="partial" />
            <ProgressBar value={10} max={10} label="done" />
            <ProgressBar value={3} max={10} label="thin" thin />
            <div className="flex flex-wrap gap-2">
              <StatusBadge state="todo" />
              <StatusBadge state="progress" />
              <StatusBadge state="done" />
              <StatusBadge state="empty" />
            </div>
          </div>
        </Card>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <Stats label="Example stats" items={[{ label: "Total XP", value: "12,450" }, { label: "Streak", value: 6 }]} />
          </div>
          <div className="col-span-2 space-y-2 rounded-lg bg-surface p-4">
            {TYPES.map((t) => (
              <p key={t} className="flex items-center gap-2 text-sm">
                <ExerciseIcon type={t} /> {exerciseTypeLabel(t)}
              </p>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div>
          <h2 className="mb-3 text-lg">Feedback</h2>
          <div className="space-y-2 text-sm">
            <div className="rounded-md bg-success-soft p-3 text-success">Correct! +100 XP</div>
            <div className="rounded-md bg-danger-soft p-3 text-danger">`result` is not quite right.</div>
            <div className="rounded-md bg-surface p-3">Hint: use `growth ** 7`.</div>
          </div>
        </div>
        <EmptyState title="No lessons in this course yet">The lesson builder writes them into content/.</EmptyState>
      </section>

      <section>
        <h2 className="mb-3 text-lg">Markdown</h2>
        <Card>
          <Markdown>{"## Slide title\n\nInline `code`, **bold**, and math $\\hat{y} = \\beta_0 + \\beta_1 x$.\n\n```python\nimport numpy as np\nnp.mean([1, 2, 3])\n```\n\n| a | b |\n|---|---|\n| 1 | 2 |"}</Markdown>
        </Card>
      </section>
    </div>
  );
}
