"use client";

import Image from "next/image";
import { useSites } from "@/hooks/useSites";
import { SiteCard } from "@/components/layout/SiteCard";
import { Button } from "@/components/ui/Button";
import Link from "next/link";
import { useTranslation } from "@/lib/i18n";

export default function DashboardPage() {
  const { t } = useTranslation();
  const { sites, isLoading, error } = useSites();

  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-navy-DEFAULT">
      <div className="absolute inset-0">
        <Image
          src="/brand/dashboard-hero.jpg"
          alt="REVEAL dashboard hero"
          fill
          priority
          className="object-cover"
        />
        <div className="absolute inset-0 bg-[linear-gradient(100deg,rgba(2,18,28,0.9),rgba(5,30,45,0.78),rgba(5,30,45,0.58))]" />
      </div>

      <div className="relative space-y-6 px-8 py-8">
        <section className="flex items-end justify-between gap-6">
          <div className="min-w-0 space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.34em] text-white/55">8p2 Advisory&apos;s REVEAL Renewable Energy Valuation, Evaluation and Analytics Lab</p>
            <h1 className="font-dolfines text-3xl font-semibold tracking-[0.08em] text-white">{t("dashboard.title")}</h1>
            <p className="max-w-full truncate text-sm text-slate-200/78">
              Solar PV and wind asset portfolios, report generation, and operational performance in one workspace.
            </p>
          </div>
          <Link href="/dashboard/site/new/edit">
            <Button variant="secondary" size="sm">+ {t("dashboard.addSite")}</Button>
          </Link>
        </section>

        <div className="flex items-center justify-between">
          <h2 className="font-dolfines text-xl font-semibold tracking-[0.06em] text-white">Sites</h2>
          <span className="text-sm text-slate-300">{sites.length} configured</span>
        </div>

        {isLoading && (
          <p className="text-sm text-slate-300">{t("common.loadingSites")}</p>
        )}

        {error && (
          <p className="text-sm text-danger">Failed to load sites: {error.message}</p>
        )}

        {!isLoading && sites.length === 0 && (
          <p className="text-sm text-slate-300">{t("dashboard.noSites")}</p>
        )}

        <div className="space-y-3">
          {sites.map((site) => (
            <SiteCard key={site.id} site={site} />
          ))}
        </div>
      </div>
    </div>
  );
}
