"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/tracks", label: "Tracks" },
  { href: "/progress", label: "Progress" },
  { href: "/dex", label: "Dex" },
];

export function NavLinks() {
  const path = usePathname();
  return (
    <nav aria-label="Main" className="flex items-center gap-1 text-sm">
      {LINKS.map((l) => {
        const active = l.href === "/" ? path === "/" : path.startsWith(l.href) || (l.href === "/tracks" && path.startsWith("/courses"));
        return (
          <Link
            key={l.href}
            href={l.href}
            aria-current={active ? "page" : undefined}
            className={`rounded-md px-2 py-1.5 ${active ? "font-semibold text-accent-text underline decoration-2 underline-offset-[10px] sm:underline-offset-[18px]" : "text-text-muted hover:text-text"}`}
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
