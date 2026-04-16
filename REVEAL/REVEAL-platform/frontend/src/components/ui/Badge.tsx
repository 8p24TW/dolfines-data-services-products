import clsx from "clsx";

interface BadgeProps {
  label: string;
  color?: "green" | "amber" | "red" | "blue" | "gray";
}

export function Badge({ label, color = "gray" }: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        {
          "bg-success/20 text-success": color === "green",
          "bg-warning/20 text-warning": color === "amber",
          "bg-danger/20 text-danger": color === "red",
          "bg-blue-500/20 text-blue-300": color === "blue",
          "bg-slate-500/20 text-slate-300": color === "gray",
        }
      )}
    >
      {label}
    </span>
  );
}
