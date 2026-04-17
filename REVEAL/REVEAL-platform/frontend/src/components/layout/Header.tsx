"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import { LanguageToggle } from "./LanguageToggle";
import { Button } from "@/components/ui/Button";
import { useTranslation } from "@/lib/i18n";
import { BrandLockup } from "./BrandLockup";

export function Header() {
  const { data: session } = useSession();
  const { t } = useTranslation();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  const navLinks = session
    ? [
        { href: "/dashboard", label: t("nav.dashboard") },
        { href: "/dashboard/charting", label: t("nav.charting") },
        { href: "/dashboard/performance", label: t("nav.reporting") },
        { href: "/dashboard/long-term-modelling", label: t("nav.longTerm") },
        { href: "/dashboard/price-forecast", label: t("nav.priceForecast") },
        { href: "/dashboard/retrofit-bess", label: t("nav.retrofitBess") },
        { href: "/dashboard/knowledge-base", label: t("nav.knowledgeBase") },
        { href: "/dashboard/contact", label: t("nav.contact") },
      ]
    : [];

  return (
    <header className="border-b border-navy-light bg-navy-DEFAULT">
      {/* Main bar */}
      <div className="flex h-14 items-center justify-between px-4 lg:px-6">
        <div className="flex items-center gap-3 lg:gap-5 min-w-0">
          <BrandLockup compact />

          {/* Desktop nav — hidden below lg */}
          {session && (
            <nav className="hidden lg:flex items-center gap-0.5 text-xs">
              {navLinks.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className={`whitespace-nowrap px-2.5 py-1.5 transition-colors border-b-2 ${
                    pathname === href
                      ? "text-white font-semibold border-orange-DEFAULT"
                      : "text-slate-300 hover:text-white border-transparent hover:border-white/20"
                  }`}
                >
                  {label}
                </Link>
              ))}
            </nav>
          )}
        </div>

        <div className="flex items-center gap-2 lg:gap-3 shrink-0">
          <LanguageToggle />
          {session && (
            <>
              <span className="hidden xl:block text-xs text-slate-400 truncate max-w-[180px]">
                {session.user?.email}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="hidden lg:inline-flex"
                onClick={() => signOut({ callbackUrl: "/login" })}
              >
                {t("nav.logout")}
              </Button>
            </>
          )}

          {/* Hamburger — visible below lg */}
          {session && (
            <button
              type="button"
              aria-label="Toggle menu"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((prev) => !prev)}
              className="lg:hidden flex flex-col justify-center gap-[5px] p-1.5 rounded"
            >
              <span
                className={`block w-5 h-0.5 bg-slate-300 origin-center transition-transform duration-200 ${
                  menuOpen ? "translate-y-[7px] rotate-45" : ""
                }`}
              />
              <span
                className={`block w-5 h-0.5 bg-slate-300 transition-opacity duration-200 ${
                  menuOpen ? "opacity-0" : ""
                }`}
              />
              <span
                className={`block w-5 h-0.5 bg-slate-300 origin-center transition-transform duration-200 ${
                  menuOpen ? "-translate-y-[7px] -rotate-45" : ""
                }`}
              />
            </button>
          )}
        </div>
      </div>

      {/* Mobile / tablet dropdown */}
      {session && menuOpen && (
        <div className="lg:hidden border-t border-navy-light bg-navy-DEFAULT px-4 py-3">
          <nav className="flex flex-col gap-0.5">
            {navLinks.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                onClick={() => setMenuOpen(false)}
                className={`rounded px-3 py-2.5 text-sm transition-colors border-l-2 ${
                  pathname === href
                    ? "border-orange-DEFAULT text-white font-semibold bg-white/5"
                    : "border-transparent text-slate-300 hover:text-white hover:bg-white/5"
                }`}
              >
                {label}
              </Link>
            ))}
          </nav>
          <div className="mt-3 pt-3 border-t border-white/10 flex items-center justify-between">
            <span className="text-xs text-slate-400 truncate">{session.user?.email}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => signOut({ callbackUrl: "/login" })}
            >
              {t("nav.logout")}
            </Button>
          </div>
        </div>
      )}
    </header>
  );
}
