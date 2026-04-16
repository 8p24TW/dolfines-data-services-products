"use client";

import Link from "next/link";
import { useTranslation } from "@/lib/i18n";

interface BackLinkProps {
  href: string;
  label?: string;
}

export function BackLink({ href, label }: BackLinkProps) {
  const { t } = useTranslation();

  return (
    <Link
      href={href}
      className="inline-flex items-center gap-2 text-sm font-semibold text-slate-300 transition-colors hover:text-white"
    >
      <span aria-hidden="true">←</span>
      <span>{label ?? t("common.back")}</span>
    </Link>
  );
}
