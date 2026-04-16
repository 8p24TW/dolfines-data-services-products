"use client";

import Image from "next/image";
import { BackLink } from "@/components/layout/BackLink";
import { useTranslation } from "@/lib/i18n";

type FAQItem = {
  question: string;
  answer: string;
};

export default function HelpPage() {
  const { t, lang } = useTranslation();
  const quickStart =
    lang === "fr"
      ? [
          "Ajoutez ou consultez un site depuis le tableau de bord.",
          "Ouvrez Performance pour choisir le niveau de diagnostic souhaité.",
          "Téléchargez les fichiers SCADA et confirmez les colonnes détectées.",
          "Lancez l'analyse puis téléchargez le PDF final une fois le traitement terminé.",
        ]
      : [
          "Add or review a site from the dashboard.",
          "Open Performance to choose the diagnostic depth you want.",
          "Upload SCADA files and confirm the detected columns.",
          "Run the analysis and download the final PDF when processing is complete.",
        ];
  const faqs: FAQItem[] =
    lang === "fr"
      ? [
          {
            question: "Quels formats de fichiers sont acceptés ?",
            answer:
              "REVEAL accepte actuellement les fichiers CSV pour les entrées d'analyse SCADA. Certaines zones de téléchargement acceptent aussi des formats tableur pendant les workflows de détection.",
          },
          {
            question: "Puis-je travailler en anglais et en français ?",
            answer:
              "Oui. Utilisez le sélecteur de langue dans l'en-tête pour changer la langue de l'interface à tout moment.",
          },
          {
            question: "Comment réinitialiser mon mot de passe ?",
            answer:
              "Utilisez le lien Mot de passe oublié sur la page de connexion. Si le SMTP est configuré, REVEAL enverra un lien de réinitialisation à l'adresse email enregistrée.",
          },
          {
            question: "Quelle est la différence entre Tableau de bord et Performance ?",
            answer:
              "Le tableau de bord sert à la vue d'ensemble et à la navigation entre les sites. Performance sert à lancer les diagnostics, examiner les KPI et télécharger les synthèses.",
          },
        ]
      : [
          {
            question: "Which file formats are accepted?",
            answer:
              "REVEAL currently accepts CSV files for SCADA analysis inputs. Some upload areas also allow spreadsheet formats during detection workflows.",
          },
          {
            question: "Can I work in English and French?",
            answer:
              "Yes. Use the language toggle in the header to switch the interface language at any time.",
          },
          {
            question: "How do I reset my password?",
            answer:
              "Use the Forgot password link on the login page. If SMTP is configured, REVEAL sends a reset link to the registered email account.",
          },
          {
            question: "What is the difference between Dashboard and Performance?",
            answer:
              "Dashboard is for site overview and navigation. Performance is where you run diagnostic analyses, review KPIs, and download summary outputs.",
          },
        ];

  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-navy-DEFAULT">
      <div className="absolute inset-0">
        <Image
          src="/brand/help-hero.jpg"
          alt="Help page hero"
          fill
          priority
          className="object-cover"
        />
        <div className="absolute inset-0 bg-[linear-gradient(100deg,rgba(2,18,28,0.94),rgba(5,30,45,0.74),rgba(178,99,33,0.22))]" />
      </div>
      <div className="relative space-y-6 px-8 py-8">
        <BackLink href="/dashboard" label={t("common.backToDashboard")} />

        <section className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-[0.34em] text-white/55">8p2 Advisory&apos;s REVEAL Renewable Energy Valuation, Evaluation and Analytics Lab</p>
          <h1 className="font-dolfines text-3xl font-semibold tracking-[0.08em] text-white">{t("help.title")}</h1>
          <p className="max-w-3xl text-sm text-slate-200/80">{t("help.subtitle")}</p>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
          <div className="rounded-3xl border border-navy-light bg-navy-DEFAULT/72 p-6 backdrop-blur-sm">
          <h2 className="font-dolfines text-xl font-semibold tracking-[0.06em] text-white">{t("help.quickStart")}</h2>
          <ol className="mt-4 space-y-3 text-sm text-slate-300">
            {quickStart.map((item, index) => (
              <li key={item} className="flex gap-3">
                <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-orange-DEFAULT font-semibold text-white">
                  {index + 1}
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ol>
          </div>

          <div className="rounded-3xl border border-navy-light bg-navy-DEFAULT/72 p-6 backdrop-blur-sm">
          <h2 className="font-dolfines text-xl font-semibold tracking-[0.06em] text-white">{t("help.faq")}</h2>
          <div className="mt-4 space-y-4">
            {faqs.map((item) => (
              <div key={item.question} className="rounded-2xl border border-white/8 bg-white/3 p-4">
                <h3 className="text-sm font-semibold text-white">{item.question}</h3>
                <p className="mt-2 text-sm text-slate-300">{item.answer}</p>
              </div>
            ))}
          </div>
          </div>
        </section>
      </div>
    </div>
  );
}
