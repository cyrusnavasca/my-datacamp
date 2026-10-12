"use client";

import Link from "next/link";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const isContent = error.message.includes(".yaml");
  return (
    <main className="mx-auto max-w-2xl px-4 py-16">
      <h1 className="text-xl">{isContent ? "A lesson file has a problem" : "Something broke"}</h1>
      <pre className="mt-4 overflow-x-auto whitespace-pre-wrap rounded-md bg-danger-soft p-4 font-mono text-sm text-danger">
        {error.message || `Error ${error.digest ?? ""}`}
      </pre>
      {isContent && (
        <p className="mt-4 text-sm text-text-muted">
          Fix the file, or run <code className="font-mono">npm run content:check</code> to see every problem at once.
        </p>
      )}
      <div className="mt-6 flex gap-3">
        <button className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-on-accent" onClick={reset}>
          Try again
        </button>
        <Link className="rounded-md bg-surface-2 px-4 py-2 text-sm font-semibold" href="/">
          Dashboard
        </Link>
      </div>
    </main>
  );
}
