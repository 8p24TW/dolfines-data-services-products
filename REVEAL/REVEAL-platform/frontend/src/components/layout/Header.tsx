"use client";

import Link from "next/link";
import { useSession, signOut } from "next-auth/react";
import { LanguageToggle } from "./LanguageToggle";
import { Button } from "@/components/ui/Button";
import { useTranslation } from "@/lib/i18n";
import { BrandLockup } from "./BrandLockup";

export function Header() {
  const { data: session } = useSession();
  const { t } = useTranslation();

  return (
    <header className="flex h-16 items-center justify-between border-b border-navy-light bg-navy-DEFAULT px-6">
      <div className="flex items-center gap-6">
        <BrandLockup compact />
        {session && (
          <nav className="flex gap-4 text-sm">
            <Link href="/dashboard" className="text-slate-300 hover:text-white transition-colors">
              {t("nav.dashboard")}
            </Link>
            <Link href="/dashboard/charting" className="text-slate-300 hover:text-white transition-colors">
              {t("nav.charting")}
            </Link>
            <Link href="/dashboard/performance" className="text-slate-300 hover:text-white transition-colors">
              {t("nav.reporting")}
            </Link>
            <Link href="/dashboard/long-term-modelling" className="text-slate-300 hover:text-white transition-colors">
              {t("nav.longTerm")}
            </Link>
            <Link href="/dashboard/price-forecast" className="text-slate-300 hover:text-white transition-colors">
              {t("nav.priceForecast")}
            </Link>
            <Link href="/dashboard/retrofit-bess" className="text-slate-300 hover:text-white transition-colors">
              {t("nav.retrofitBess")}
            </Link>
            <Link href="/dashboard/knowledge-base" className="text-slate-300 hover:text-white transition-colors">
              {t("nav.knowledgeBase")}
            </Link>
            <Link href="/dashboard/contact" className="text-slate-300 hover:text-white transition-colors">
              {t("nav.contact")}
            </Link>
          </nav>
        )}
      </div>
      <div className="flex items-center gap-4">
        <LanguageToggle />
        {session && (
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400">{session.user?.email}</span>
            <Button variant="ghost" size="sm" onClick={() => signOut({ callbackUrl: "/login" })}>
              {t("nav.logout")}
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
