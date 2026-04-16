import Link from "next/link";
import type { JSX } from "react";
import type { ReportType } from "@/types/report";

interface ReportTypeCardProps {
  type: ReportType;
  title: string;
  description: string;
  href: string;
}

const icons: Record<ReportType, JSX.Element> = {
  comprehensive: (
    <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 19h16" />
      <path d="M7 16V9" />
      <path d="M12 16V5" />
      <path d="M17 16v-3" />
    </svg>
  ),
  daily: (
    <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M8 3v4M16 3v4M3 10h18" />
      <path d="M8 14h3" />
    </svg>
  ),
  monthly: (
    <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="4" width="18" height="17" rx="2" />
      <path d="M8 2v4M16 2v4M3 10h18" />
      <path d="M8 14h8M8 17h5" />
    </svg>
  ),
};

export function ReportTypeCard({ type, title, description, href }: ReportTypeCardProps) {
  const disabled = href === "#";

  return (
    <Link
      href={href}
      aria-disabled={disabled}
      className={`group block rounded-[24px] border border-white/12 bg-[rgba(3,16,26,0.82)] p-6 shadow-[0_16px_40px_rgba(0,0,0,0.24)] backdrop-blur-sm transition-colors ${
        disabled ? "cursor-not-allowed opacity-60" : "hover:border-orange-DEFAULT/60"
      }`}
      onClick={(event) => {
        if (disabled) event.preventDefault();
      }}
    >
      <div className="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl border border-orange-DEFAULT/30 bg-orange-DEFAULT/14 text-orange-DEFAULT">
        {icons[type]}
      </div>
      <h3 className="font-dolfines text-xl font-semibold tracking-[0.04em] text-white group-hover:text-orange-DEFAULT transition-colors">
        {title}
      </h3>
      <p className="mt-2 text-sm leading-relaxed text-slate-300">{description}</p>
    </Link>
  );
}
