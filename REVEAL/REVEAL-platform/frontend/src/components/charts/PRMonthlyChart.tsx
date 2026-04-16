"use client";

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Cell
} from "recharts";
import type { MonthlyPR } from "@/types/analysis";

interface PRMonthlyChartProps {
  data: MonthlyPR[];
  targetPR?: number; // e.g. 0.79
}

export function PRMonthlyChart({ data, targetPR = 0.79 }: PRMonthlyChartProps) {
  const target = targetPR * 100;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e3a50" />
        <XAxis
          dataKey="month"
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickFormatter={(v: string) => v.slice(5)} // "2024-03" → "03"
        />
        <YAxis
          domain={[0, 100]}
          tickFormatter={(v: number) => `${v}%`}
          tick={{ fill: "#94a3b8", fontSize: 11 }}
        />
        <Tooltip
          formatter={(v: number) => [`${v.toFixed(1)}%`, "PR"]}
          contentStyle={{ background: "#0B2A3D", border: "1px solid #003366", borderRadius: 6, color: "#f8fafc" }}
          labelStyle={{ color: "#e2e8f0" }}
          itemStyle={{ color: "#f8fafc" }}
          cursor={{ fill: "rgba(12, 37, 56, 0.42)" }}
        />
        <ReferenceLine
          y={target}
          stroke="#F39200"
          strokeDasharray="6 3"
          label={{ value: `Target ${target}%`, position: "insideTopRight", fill: "#F39200", fontSize: 11 }}
        />
        <Bar dataKey="PR_pct" radius={[3, 3, 0, 0]}>
          {data.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.PR_pct >= target ? "#70AD47" : entry.PR_pct >= target * 0.95 ? "#C98A00" : "#C62828"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
