import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-16 text-center">
      <h1 className="text-xl">Nothing here</h1>
      <p className="mt-2 text-text-muted">That page, course or exercise does not exist (yet).</p>
      <Link className="mt-6 inline-block rounded-md bg-accent px-4 py-2 text-sm font-semibold text-on-accent" href="/">
        Back to the dashboard
      </Link>
    </main>
  );
}
