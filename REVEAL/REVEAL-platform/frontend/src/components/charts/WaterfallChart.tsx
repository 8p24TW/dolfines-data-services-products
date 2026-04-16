"use client";

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from "recharts";
import type { WaterfallItem } from "@/types/analysis";

interface WaterfallChartProps {
  data: WaterfallItem[];
}

function wrapWords(label: string, maxLineLength = 16) {
  const words = label.split(" ");
  const lines: string[] = [];
  let currentLine = "";
  for (const word of words) {
    if (!currentLine.length) {
      currentLine = word;
      continue;
    }
    if (`${currentLine} ${word}`.length <= maxLineLength) {
      currentLine = `${currentLine} ${word}`;
    } else {
      lines.push(currentLine);
      currentLine = word;
    }
  }
  if (currentLine.length) lines.push(currentLine);
  return lines;
}

function WrappedAxisTick(props: { x?: number; y?: number; payload?: { value?: string } }) {
  const { x = 0, y = 0, payload } = props;
  const lines = wrapWords(String(payload?.value ?? ""));
  return (
    <g transform={`translate(${x},${y})`}>
      <text textAnchor="middle" fill="#cbd5e1" fontSize={12}>
        {lines.map((line, index) => (
          <tspan key={`${line}-${index}`} x={0} dy={index === 0 ? 12 : 14}>
            {line}
          </tspan>
        ))}
      </text>
    </g>
  );
}

// Transform waterfall items into floating bar format for Recharts
function toWaterfallBars(items: WaterfallItem[]) {
  let cumulative = 0;
  return items.map((item) => {
    const start = item.type === "base" ? 0 : cumulative;
    const end = item.type === "loss" ? cumulative - Math.abs(item.value_mwh)
      : item.type === "gain" ? cumulative + item.value_mwh
      : item.value_mwh;
    cumulative = end;
    return { ...item, start: Math.min(start, end), height: Math.abs(item.value_mwh), end };
  });
}

export function WaterfallChart({ data }: WaterfallChartProps) {
  const bars = toWaterfallBars(data);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={bars} margin={{ top: 12, right: 12, left: 16, bottom: 56 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" />
        <XAxis
          dataKey="label"
          tick={<WrappedAxisTick />}
          interval={0}
          tickLine={false}
          axisLine={{ stroke: "rgba(255,255,255,0.16)" }}
        />
        <YAxis
          tickFormatter={(v: number) => `${v.toFixed(0)}`}
          tick={{ fill: "#cbd5e1", fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: "rgba(255,255,255,0.16)" }}
          label={{ value: "Yield (MWh)", angle: -90, position: "insideLeft", dy: 52, fill: "#cbd5e1", fontSize: 11 }}
        />
        <Tooltip
          formatter={(v: number) => [`${v.toFixed(1)} MWh`]}
          contentStyle={{ background: "rgba(5,20,32,0.94)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 16, color: "#f8fafc" }}
          labelStyle={{ color: "#e2e8f0", fontWeight: 600 }}
          itemStyle={{ color: "#f8fafc" }}
          cursor={false}
        />
        {/* Invisible spacer bar to float the visible bar */}
        <Bar dataKey="start" stackId="w" fill="transparent" />
        <Bar dataKey="height" stackId="w" radius={[3, 3, 0, 0]}>
          {bars.map((b, i) => (
            <Cell
              key={i}
              fill={b.type === "base" ? "#003366" : b.type === "loss" ? "#C62828" : "#70AD47"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
