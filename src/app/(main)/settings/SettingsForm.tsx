"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { Button } from "@/components/ui";

async function save(body: object) {
  const r = await fetch("/api/settings", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error("Could not save");
}

export function SettingsForm({ goal, theme, courses }: { goal: number; theme: string; courses: { slug: string; title: string }[] }) {
  const router = useRouter();
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [resetTarget, setResetTarget] = useState("all");
  const dialog = useRef<HTMLDialogElement>(null);

  const run = async (body: object, done: string) => {
    setBusy(true);
    try {
      await save(body);
      setMsg(done);
      router.refresh();
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-xl space-y-10">
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          run({ dailyGoal: Number(f.get("goal")), theme: f.get("theme") }, "Saved.");
        }}
      >
        <div>
          <label htmlFor="goal" className="block text-sm font-semibold">
            Daily XP goal
          </label>
          <select id="goal" name="goal" defaultValue={goal} className="mt-1 h-10 w-full rounded-md border border-border-input bg-bg px-3">
            {[100, 200, 300, 500, 800, 1200].map((g) => (
              <option key={g} value={g}>
                {g} XP a day
              </option>
            ))}
          </select>
        </div>
        <fieldset>
          <legend className="text-sm font-semibold">Theme</legend>
          <div className="mt-2 flex gap-4">
            {["system", "light", "dark"].map((t) => (
              <label key={t} className="flex items-center gap-2 text-sm capitalize">
                <input type="radio" name="theme" value={t} defaultChecked={theme === t} className="accent-accent" /> {t}
              </label>
            ))}
          </div>
        </fieldset>
        <Button type="submit" loading={busy}>
          Save
        </Button>
        <p role="status" className="text-sm text-text-muted">
          {msg}
        </p>
      </form>

      <section className="rounded-lg border border-danger/40 p-5">
        <h2 className="font-semibold text-danger">Reset progress</h2>
        <p className="mt-1 text-sm text-text-muted">Clears completed exercises and XP. Lesson files are not touched.</p>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <label htmlFor="reset" className="sr-only">
            What to reset
          </label>
          <select id="reset" value={resetTarget} onChange={(e) => setResetTarget(e.target.value)} className="h-10 flex-1 rounded-md border border-border-input bg-bg px-3">
            <option value="all">Everything (all courses, streak, history, monsters)</option>
            {courses.map((c) => (
              <option key={c.slug} value={c.slug}>
                Only: {c.title}
              </option>
            ))}
          </select>
          <Button variant="danger" onClick={() => dialog.current?.showModal()}>
            Reset…
          </Button>
        </div>
      </section>

      <dialog ref={dialog} className="m-auto max-w-sm rounded-lg bg-bg p-6 text-text shadow-pop backdrop:bg-text/40">
        <h2 className="font-semibold">Reset progress?</h2>
        <p className="mt-2 text-sm text-text-muted">This cannot be undone.</p>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => dialog.current?.close()} autoFocus>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={() => {
              dialog.current?.close();
              run({ reset: resetTarget }, "Progress reset.");
            }}
          >
            Reset
          </Button>
        </div>
      </dialog>
    </div>
  );
}
