import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

// Primitives from replica/design/components.md. Tokens only, no raw colours.

const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

const buttonBase =
  "inline-flex items-center justify-center gap-2 rounded-md font-semibold text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap";
const buttonVariants = {
  primary: "bg-accent text-on-accent hover:opacity-90",
  secondary: "bg-surface-2 text-text hover:bg-border",
  ghost: "text-text hover:bg-surface-2",
  danger: "bg-danger text-bg hover:opacity-90",
} as const;
const buttonSizes = { sm: "h-8 px-3", md: "h-10 px-4", lg: "h-12 px-5 text-base" } as const;

type ButtonStyle = { variant?: keyof typeof buttonVariants; size?: keyof typeof buttonSizes };

export function buttonClass({ variant = "primary", size = "md" }: ButtonStyle = {}, extra?: string) {
  return cx(buttonBase, buttonVariants[variant], buttonSizes[size], extra);
}

export function Button({
  variant,
  size,
  loading,
  className,
  children,
  disabled,
  ...rest
}: ComponentProps<"button"> & ButtonStyle & { loading?: boolean }) {
  return (
    <button className={buttonClass({ variant, size }, className)} disabled={disabled || loading} aria-busy={loading} {...rest}>
      {loading && <span className="size-3 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />}
      {children}
    </button>
  );
}

export function ButtonLink({ variant, size, className, ...rest }: ComponentProps<typeof Link> & ButtonStyle) {
  return <Link className={buttonClass({ variant, size }, className)} {...rest} />;
}

export function ProgressBar({ value, max, label, thin }: { value: number; max: number; label: string; thin?: boolean }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <div
        role="progressbar"
        aria-label={label}
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        className={cx("w-full overflow-hidden rounded-pill bg-surface-2", thin ? "h-1" : "h-2")}
      >
        <div className={cx("h-full rounded-pill", pct >= 100 ? "bg-success" : "bg-accent")} style={{ width: `${pct}%` }} />
      </div>
      {!thin && <span className="text-xs text-text-muted tabular-nums">{pct}%</span>}
    </div>
  );
}

/** A row of numbers. No boxes: size and weight carry the hierarchy, a thin rule separates. */
export function Stats({ items, label }: { items: { label: string; value: ReactNode; sub?: ReactNode }[]; label: string }) {
  return (
    <dl aria-label={label} className="grid grid-cols-2 gap-y-6 border-y border-border py-5 sm:flex sm:divide-x sm:divide-border">
      {items.map((it) => (
        <div key={it.label} className="sm:flex-1 sm:px-6 sm:first:pl-0">
          <dt className="text-sm text-text-muted">{it.label}</dt>
          <dd className="mt-1 text-xl font-semibold tabular-nums">{it.value}</dd>
          {it.sub && <dd className="mt-2">{it.sub}</dd>}
        </div>
      ))}
    </dl>
  );
}

const badgeTones = {
  todo: "bg-surface-2 text-text-muted",
  progress: "bg-accent-soft text-accent-text",
  done: "bg-success-soft text-success",
  empty: "bg-surface-2 text-text-muted",
} as const;

export function Badge({ tone, children }: { tone: keyof typeof badgeTones; children: ReactNode }) {
  return <span className={cx("inline-flex items-center gap-1 rounded-pill px-2 py-0.5 text-xs font-medium", badgeTones[tone])}>{children}</span>;
}

export function Card({ className, ...rest }: ComponentProps<"div">) {
  return <div className={cx("rounded-lg border border-border bg-bg p-5", className)} {...rest} />;
}

export function EmptyState({ icon, title, children }: { icon?: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg bg-surface px-6 py-10 text-center">
      {icon && <div className="text-text-muted">{icon}</div>}
      <p className="font-semibold">{title}</p>
      {children && <div className="text-sm text-text-muted">{children}</div>}
    </div>
  );
}

export function PageHeader({ title, children, eyebrow }: { title: string; eyebrow?: ReactNode; children?: ReactNode }) {
  return (
    <header className="mb-8">
      {eyebrow && <div className="mb-2 text-sm text-text-muted">{eyebrow}</div>}
      <h1 className="text-xl break-words">{title}</h1>
      {children && <div className="mt-2 max-w-2xl text-text-muted">{children}</div>}
    </header>
  );
}

export { cx };
