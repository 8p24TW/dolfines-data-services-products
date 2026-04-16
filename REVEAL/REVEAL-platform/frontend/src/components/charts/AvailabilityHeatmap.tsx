"use client";

// Availability heatmap: months (X) × inverters (Y), coloured by availability %
interface HeatmapProps {
  data: Array<{ month: string; inv_id: string; avail_pct: number }>;
}

function colorFor(pct: number): string {
  if (pct >= 98) return "#70AD47";
  if (pct >= 95) return "#C98A00";
  if (pct >= 85) return "#E07820";
  return "#C62828";
}

export function AvailabilityHeatmap({ data }: HeatmapProps) {
  const months = [...new Set(data.map((d) => d.month))].sort();
  const inverters = [...new Set(data.map((d) => d.inv_id))].sort();

  const lookup = new Map(data.map((d) => [`${d.inv_id}|${d.month}`, d.avail_pct]));

  const cellW = 40;
  const cellH = 20;
  const labelW = 80;
  const headerH = 40;
  const totalW = labelW + months.length * cellW;
  const totalH = headerH + inverters.length * cellH;

  return (
    <div className="overflow-x-auto">
      <svg width={totalW} height={totalH} style={{ fontFamily: "inherit" }}>
        {/* Month headers */}
        {months.map((m, mi) => (
          <text
            key={m}
            x={labelW + mi * cellW + cellW / 2}
            y={headerH - 6}
            textAnchor="middle"
            fontSize={9}
            fill="#94a3b8"
          >
            {m.slice(5)}
          </text>
        ))}

        {/* Rows */}
        {inverters.map((inv, ii) => (
          <g key={inv}>
            <text
              x={labelW - 4}
              y={headerH + ii * cellH + cellH / 2 + 4}
              textAnchor="end"
              fontSize={9}
              fill="#94a3b8"
            >
              {inv}
            </text>
            {months.map((m, mi) => {
              const val = lookup.get(`${inv}|${m}`) ?? 0;
              return (
                <g key={m}>
                  <rect
                    x={labelW + mi * cellW + 1}
                    y={headerH + ii * cellH + 1}
                    width={cellW - 2}
                    height={cellH - 2}
                    fill={colorFor(val)}
                    rx={2}
                    opacity={0.85}
                  />
                  <title>{`${inv} · ${m}: ${val.toFixed(1)}%`}</title>
                </g>
              );
            })}
          </g>
        ))}
      </svg>

      {/* Legend */}
      <div className="mt-2 flex gap-4 text-xs text-slate-400">
        {[
          { label: "≥98%", color: "#70AD47" },
          { label: "≥95%", color: "#C98A00" },
          { label: "≥85%", color: "#E07820" },
          { label: "<85%", color: "#C62828" },
        ].map((l) => (
          <div key={l.label} className="flex items-center gap-1">
            <span className="inline-block h-3 w-3 rounded" style={{ background: l.color }} />
            {l.label}
          </div>
        ))}
      </div>
    </div>
  );
}
