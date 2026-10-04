"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserRound } from "lucide-react";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <>
      <header className="sticky top-0 z-40 border-b bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center px-5 sm:px-8">
          <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
            <span className="grid size-7 place-items-center rounded-lg bg-neutral-900 text-xs font-bold text-white">O</span>
            OpsPilot AI
          </Link>
          <button aria-label="Open user menu" className="ml-auto grid size-8 place-items-center rounded-full bg-neutral-900 text-white hover:bg-neutral-700">
            <UserRound className="size-4" />
          </button>
        </div>
      </header>
      <main className={pathname === "/" ? "" : "mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-14"}>{children}</main>
    </>
  );
}
