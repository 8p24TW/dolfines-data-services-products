"use client";

import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from "recharts";

interface EnergyTimelineChartProps {
  data: Array<{ month: string; E_act_mwh: number; E_ref_mwh: number }>;
}

export function EnergyTimelineChart({ data }: EnergyTimelineChartProps) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e3a50" />
        <XAxis
          dataKey="month"
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickFormatter={(v: string) => v.slice(5)}
        />
        <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
        <Tooltip
          contentStyle={{ background: "#0B2A3D", border: "1px solid #003366", borderRadius: 6 }}
          formatter={(v: number, name: string) => [`${v.toFixed(1)} MWh`, name]}
        />
        <Legend wrapperStyle={{ color: "#94a3b8", fontSize: 12 }} />
        <Bar dataKey="E_act_mwh" name="Actual Energy" fill="#F39200" radius={[3, 3, 0, 0]} />
        <Line
          type="monotone"
          dataKey="E_ref_mwh"
          name="Reference Energy"
          stroke="#70AD47"
          strokeWidth={2}
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
