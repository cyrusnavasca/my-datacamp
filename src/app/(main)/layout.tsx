import { TopNav } from "@/components/TopNav";

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <TopNav />
      <main className="mx-auto max-w-[1120px] px-4 py-8">{children}</main>
    </>
  );
}
