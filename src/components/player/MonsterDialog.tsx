"use client";

import { useEffect, useRef } from "react";
import { ArrowRight } from "lucide-react";
import { Sprite } from "@/components/monsters/Sprite";
import { Button } from "@/components/ui";
import type { MonsterEvent } from "@/lib/monsters";
import { getLine } from "@/lib/monsters/roster";

const nameOf = (id: string, form: number) => getLine(id)?.forms[form].name ?? id;

/** The big moments: an evolution or a catch. Opens itself when given one. */
export function MonsterDialog({ event, onClose }: { event: MonsterEvent | null; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const p = event?.partner;
  const evolved = p && p.to.form > p.from.form ? p : null;
  const caught = event?.caught ?? [];
  const open = Boolean(evolved || caught.length);

  useEffect(() => {
    if (open && !ref.current?.open) ref.current?.showModal();
  }, [open, event]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      aria-labelledby="monster-dialog-h"
      className="m-auto w-[min(28rem,calc(100vw-2rem))] rounded-lg bg-bg p-6 text-center text-text shadow-pop backdrop:bg-text/40"
    >
      {evolved && (
        <div>
          <h2 id="monster-dialog-h" className="text-lg">
            {nameOf(evolved.id, evolved.from.form)} evolved into {nameOf(evolved.id, evolved.to.form)}!
          </h2>
          <div className="mt-4 flex items-center justify-center gap-3">
            <Sprite id={evolved.id} form={evolved.from.form} size={80} />
            <ArrowRight className="size-5 text-text-muted" aria-hidden />
            <Sprite id={evolved.id} form={evolved.to.form} size={128} label={nameOf(evolved.id, evolved.to.form)} className="monster-pop" />
          </div>
          <p className="mt-3 text-sm text-text-muted">{getLine(evolved.id)?.forms[evolved.to.form].dex}</p>
        </div>
      )}
      {caught.map((c, i) => (
        <div key={c.id} className={evolved || i > 0 ? "mt-6 border-t border-border pt-6" : undefined}>
          <h2 id={evolved || i > 0 ? undefined : "monster-dialog-h"} className="text-lg">
            You caught {nameOf(c.id, c.form)}!
          </h2>
          <Sprite id={c.id} form={c.form} size={112} label={nameOf(c.id, c.form)} className="monster-pop mx-auto mt-3" />
          <p className="mt-3 text-sm text-text-muted">
            Joins at Lv {c.level}. Make it your partner from the Dex.
          </p>
        </div>
      ))}
      <Button className="mt-6" autoFocus onClick={() => ref.current?.close()}>
        Nice
      </Button>
    </dialog>
  );
}
