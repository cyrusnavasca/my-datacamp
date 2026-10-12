"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui";

/** Makes a monster the partner (adopting it first if it is an open starter). */
export function PartnerButton({ id, children, size = "sm" }: { id: string; children: React.ReactNode; size?: "sm" | "md" }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <div className="flex flex-col items-center gap-1">
      <Button
        size={size}
        loading={busy}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            const r = await fetch("/api/partner", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ id }) });
            if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error ?? "Could not choose this monster");
            router.refresh();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {children}
      </Button>
      {error && (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
