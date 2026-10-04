"use client";

import { Activity, ArrowRight, BrainCircuit, Cloud, Terminal } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui";

export default function HomePage() {
  const router = useRouter();

  return (
    <section className="relative isolate flex min-h-[calc(100vh-4rem)] items-center justify-center overflow-hidden px-5 py-16 text-center">
      <div className="hero-glow absolute left-1/2 top-1/2 -z-10 size-[34rem] -translate-x-1/2 -translate-y-1/2 rounded-full" />

      <div className="mx-auto flex max-w-3xl flex-col items-center">
        <div className="hero-enter relative mb-10 grid size-32 place-items-center" aria-hidden="true">
          <div className="hero-ring absolute inset-0 rounded-full border border-emerald-200/80" />
          <div className="hero-ring-delay absolute inset-4 rounded-full border border-emerald-300/70" />
          <div className="relative grid size-16 place-items-center rounded-2xl border border-emerald-200 bg-white shadow-[0_12px_40px_rgba(16,185,129,0.18)]">
            <Activity className="size-7 text-emerald-600" />
          </div>
          <span className="hero-float absolute -left-4 top-1 grid size-9 place-items-center rounded-xl border bg-white shadow-sm">
            <Cloud className="size-4 text-neutral-500" />
          </span>
          <span className="hero-float-delay absolute -right-4 bottom-1 grid size-9 place-items-center rounded-xl border bg-white shadow-sm">
            <BrainCircuit className="size-4 text-neutral-500" />
          </span>
        </div>

        <div className="hero-enter hero-delay-1 inline-flex items-center gap-2 rounded-full border bg-white/80 px-3 py-1.5 text-xs font-medium text-neutral-600 shadow-sm backdrop-blur">
          <span className="size-2 rounded-full bg-emerald-500 motion-safe:animate-pulse" />
          AI-powered cloud operations
        </div>

        <h1 className="hero-enter hero-delay-2 mt-6 text-balance text-4xl font-semibold tracking-[-0.04em] text-neutral-950 sm:text-6xl">
          Find incidents before<br className="hidden sm:block" /> they become outages.
        </h1>
        <p className="hero-enter hero-delay-3 mt-6 max-w-xl text-pretty text-base leading-7 text-neutral-500 sm:text-lg">
          OpsPilot monitors your cloud, explains what went wrong, and sends the next best action to your team.
        </p>

        <Button
          className="hero-enter hero-delay-4 mt-9 h-12 rounded-xl px-6 text-base shadow-lg shadow-neutral-900/15 transition-all hover:-translate-y-0.5 hover:shadow-xl"
          onClick={() => router.push("/integrations")}
        >
          Get Started
          <ArrowRight className="ml-2 size-4" />
        </Button>

        <div className="hero-enter hero-delay-5 mt-12 w-full max-w-2xl overflow-hidden rounded-2xl border border-neutral-800 bg-neutral-950 text-left shadow-2xl shadow-neutral-900/10">
          <div className="flex items-center border-b border-white/10 px-4 py-3">
            <div className="flex gap-1.5" aria-hidden="true">
              <span className="size-2.5 rounded-full bg-red-400/80" />
              <span className="size-2.5 rounded-full bg-amber-400/80" />
              <span className="size-2.5 rounded-full bg-emerald-400/80" />
            </div>
            <div className="ml-4 flex items-center gap-2 text-xs font-medium text-neutral-400">
              <Terminal className="size-3.5" />
              Live infrastructure logs
            </div>
            <span className="ml-auto flex items-center gap-1.5 text-[11px] text-emerald-400">
              <span className="size-1.5 rounded-full bg-emerald-400 motion-safe:animate-pulse" />
              Monitoring
            </span>
          </div>
          <div className="space-y-2.5 px-4 py-4 font-mono text-xs sm:px-5">
            <div className="log-row log-row-1 flex gap-3 text-neutral-400">
              <span className="shrink-0 text-neutral-600">10:42:08</span>
              <span className="text-sky-400">INFO</span>
              <span className="truncate">payment-api · requests healthy</span>
            </div>
            <div className="log-row log-row-2 flex gap-3 text-neutral-400">
              <span className="shrink-0 text-neutral-600">10:42:11</span>
              <span className="text-amber-400">WARN</span>
              <span className="truncate">checkout-api · p95 latency 842ms</span>
            </div>
            <div className="log-row log-row-3 flex gap-3 text-neutral-400">
              <span className="shrink-0 text-neutral-600">10:42:14</span>
              <span className="text-emerald-400">INFO</span>
              <span className="truncate">worker-03 · CPU returned to baseline</span>
            </div>
            <div className="flex items-center gap-2 pt-1 text-neutral-600" aria-hidden="true">
              <span>$</span><span className="log-cursor h-3.5 w-1.5 bg-emerald-400" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
