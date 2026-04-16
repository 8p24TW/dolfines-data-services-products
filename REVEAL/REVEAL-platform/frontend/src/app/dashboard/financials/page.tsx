"use client";

import Image from "next/image";
import Link from "next/link";
import { BackLink } from "@/components/layout/BackLink";
import { Button } from "@/components/ui/Button";

export default function FinancialsPage() {
  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-navy-DEFAULT">
      <div className="absolute inset-0">
        <Image src="/brand/long-term-hero.jpg" alt="Financials hero" fill priority className="object-cover" />
        <div className="absolute inset-0 bg-[linear-gradient(100deg,rgba(2,18,28,0.92),rgba(5,30,45,0.78),rgba(8,40,54,0.6))]" />
      </div>

      <div className="relative space-y-6 px-8 py-8">
        <BackLink href="/dashboard" label="Back to dashboard" />

        <section className="rounded-[30px] border border-white/12 bg-[rgba(3,16,26,0.82)] p-6 backdrop-blur-sm">
          <div className="max-w-4xl space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.34em] text-white/55">8p2 Advisory&apos;s REVEAL Renewable Energy Valuation, Evaluation and Analytics Lab</p>
            <h1 className="font-dolfines text-3xl font-semibold tracking-[0.08em] text-white">Financials</h1>
            <p className="text-sm leading-7 text-slate-200/84">
              This page will bring together the performance diagnosis and long-term normalization outputs to evaluate retrofit economics for asset owners, with a specific focus on BESS for underperforming operational solar PV and wind assets.
            </p>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-[28px] border border-white/12 bg-[rgba(3,16,26,0.82)] p-5 backdrop-blur-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-white/55">Planned workflow</p>
            <ol className="mt-4 space-y-3 text-sm leading-7 text-slate-200/84">
              <li>1. Pull recoverable losses and improvement points from the Performance workflow.</li>
              <li>2. Pull normalized production and yield expectations from the Long-Term workflow.</li>
              <li>3. Overlay long-term electricity prices and battery operating assumptions.</li>
              <li>4. Quantify recoverable MWh, avoided curtailment, and the retrofit ROI for the asset owner.</li>
            </ol>
          </div>
          <div className="rounded-[28px] border border-violet-300/18 bg-[linear-gradient(180deg,rgba(196,181,253,0.1),rgba(46,16,101,0.16))] p-5 backdrop-blur-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-violet-100/80">Current status</p>
            <p className="mt-4 text-sm leading-7 text-slate-100/88">
              Placeholder page for the next REVEAL module. The intention is to make this the asset-owner view that converts technical underperformance and curtailment diagnostics into an actionable battery-retrofit business case.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link href="/dashboard/performance">
                <Button variant="secondary">Open Performance</Button>
              </Link>
              <Link href="/dashboard/long-term-modelling">
                <Button variant="ghost">Open Long-Term</Button>
              </Link>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
