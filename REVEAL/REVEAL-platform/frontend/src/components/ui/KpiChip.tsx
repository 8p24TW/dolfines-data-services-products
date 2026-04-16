import clsx from "clsx";

interface KpiChipProps {
  label: string;
  value: string | number;
  unit?: string;
  status?: "good" | "warning" | "bad" | "neutral";
}

export function KpiChip({ label, value, unit, status = "neutral" }: KpiChipProps) {
  return (
    <div className="rounded-lg border border-navy-light bg-navy-dark/60 px-4 py-3">
      <p className="text-xs text-slate-400 uppercase tracking-wider">{label}</p>
      <p
        className={clsx("mt-1 text-2xl font-bold", {
          "text-success": status === "good",
          "text-warning": status === "warning",
          "text-danger": status === "bad",
          "text-white": status === "neutral",
        })}
      >
        {value}
        {unit && <span className="ml-1 text-sm font-normal text-slate-400">{unit}</span>}
      </p>
    </div>
  );
}
