import type { Metadata } from "next";
import "katex/dist/katex.min.css";
import "./globals.css";
import { getSetting } from "@/lib/progress";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "my-datacamp",
  description: "A personal, local learning app for data science and AI engineering.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const theme = getSetting("theme", "system");
  return (
    <html lang="en" data-theme={theme === "system" ? undefined : theme}>
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
