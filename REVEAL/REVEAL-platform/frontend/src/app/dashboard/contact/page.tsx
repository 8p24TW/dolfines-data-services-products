"use client";

import Image from "next/image";
import { BackLink } from "@/components/layout/BackLink";
import { Button } from "@/components/ui/Button";
import { useTranslation } from "@/lib/i18n";

export default function ContactPage() {
  const { t, lang } = useTranslation();
  const supportItems =
    lang === "fr"
      ? [
          "Toutes les demandes : consulting@8p2.fr",
          "Support plateforme, support performance et demandes générales via une seule adresse.",
          "Pour les urgences liées aux analyses, indiquez le nom du site et le type d'analyse dans votre message.",
        ]
      : [
          "All enquiries: consulting@8p2.fr",
          "Platform support, performance-analysis support, and general business enquiries now go through one address.",
          "For urgent workflow issues, include the site name and analysis type in your message.",
        ];
  const officeItems =
    lang === "fr"
      ? [
          "Le nom de votre entreprise",
          "Le site ou portefeuille concerné",
          "La page ou l'action où le problème s'est produit",
          "Une capture d'écran ou une courte description du problème",
        ]
      : [
          "Your company name",
          "The site or portfolio concerned",
          "The page or action where the issue happened",
          "A screenshot or short description of the problem",
        ];

  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-navy-DEFAULT">
      <div className="absolute inset-0">
        <Image
          src="/brand/contact-hero.jpg"
          alt="Contact page hero"
          fill
          priority
          className="object-cover"
        />
        <div className="absolute inset-0 bg-[linear-gradient(100deg,rgba(2,18,28,0.95),rgba(5,30,45,0.72),rgba(235,132,53,0.18))]" />
      </div>
      <div className="relative space-y-6 px-8 py-8">
        <BackLink href="/dashboard" label={t("common.backToDashboard")} />

        <section className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-[0.34em] text-white/55">8p2 Advisory&apos;s REVEAL Renewable Energy Valuation, Evaluation and Analytics Lab</p>
          <h1 className="font-dolfines text-3xl font-semibold tracking-[0.08em] text-white">{t("contact.title")}</h1>
          <p className="max-w-3xl text-sm text-slate-200/80">{t("contact.subtitle")}</p>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-3xl border border-navy-light bg-navy-DEFAULT/72 p-6 backdrop-blur-sm">
          <h2 className="font-dolfines text-xl font-semibold tracking-[0.06em] text-white">{t("contact.supportTitle")}</h2>
          <div className="mt-4 space-y-3 text-sm text-slate-300">
            {supportItems.map((item) => (
              <p key={item}>{item}</p>
            ))}
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <a href="mailto:consulting@8p2.fr">
              <Button variant="primary">{t("contact.emailSupport")}</Button>
            </a>
            <a href="mailto:consulting@8p2.fr">
              <Button variant="secondary">{t("contact.emailSales")}</Button>
            </a>
          </div>
        </div>

        <div className="rounded-3xl border border-navy-light bg-navy-DEFAULT/72 p-6 backdrop-blur-sm">
          <h2 className="font-dolfines text-xl font-semibold tracking-[0.06em] text-white">{t("contact.officeTitle")}</h2>
          <ul className="mt-4 space-y-3 text-sm text-slate-300">
            {officeItems.map((item) => (
              <li key={item} className="flex gap-3">
                <span className="mt-[7px] h-2 w-2 rounded-full bg-orange-DEFAULT" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
          <p className="mt-6 rounded-2xl border border-white/8 bg-white/3 p-4 text-sm text-slate-300">
            {t("contact.responseNote")}
          </p>
        </div>
      </section>
      </div>
    </div>
  );
}
