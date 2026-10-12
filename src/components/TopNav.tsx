import Link from "next/link";
import { Flame, GraduationCap, Settings, Zap } from "lucide-react";
import { getPartner } from "@/lib/monsters";
import { streak, totalXp } from "@/lib/progress";
import { Sprite } from "./monsters/Sprite";
import { NavLinks } from "./NavLinks";

export function TopNav() {
  const xp = totalXp();
  const days = streak();
  const partner = getPartner();
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-bg">
      <div className="mx-auto flex max-w-[1120px] flex-wrap items-center gap-x-4 px-4 py-2 sm:h-14 sm:flex-nowrap sm:py-0">
        <Link href="/" className="flex items-center gap-2 font-bold">
          <GraduationCap className="size-5 text-accent" aria-hidden />
          <span className="whitespace-nowrap">my-datacamp</span>
        </Link>
        <div className="order-last -mx-2 w-full sm:order-none sm:mx-0 sm:w-auto">
          <NavLinks />
        </div>
        <div className="ml-auto flex items-center gap-4 text-sm">
          <span className="hidden items-center gap-1 text-text-muted sm:inline-flex" title="Day streak">
            <Flame className="size-4" aria-hidden />
            <span className="tabular-nums">{days}</span>
            <span className="sr-only">day streak</span>
          </span>
          <span className="inline-flex items-center gap-1 font-semibold" title="Total XP">
            <Zap className="size-4 text-xp" aria-hidden />
            <span className="tabular-nums">{xp.toLocaleString()}</span>
            <span className="font-normal text-text-muted">XP</span>
          </span>
          <Link
            href="/dex"
            className="inline-flex items-center gap-1 rounded-md py-1 pr-2 pl-1 hover:bg-surface-2"
            title={partner ? `Partner: ${partner.line.forms[partner.form].name}` : "Choose a partner"}
          >
            {partner ? (
              <>
                <Sprite id={partner.line.id} form={partner.form} size={28} />
                <span className="tabular-nums">Lv {partner.level}</span>
                <span className="sr-only">{partner.line.forms[partner.form].name}, your partner</span>
              </>
            ) : (
              <span className="text-accent-text">Choose a partner</span>
            )}
          </Link>
          <Link href="/settings" className="rounded-md p-2 text-text-muted hover:bg-surface-2" aria-label="Settings">
            <Settings className="size-4" aria-hidden />
          </Link>
        </div>
      </div>
    </header>
  );
}
