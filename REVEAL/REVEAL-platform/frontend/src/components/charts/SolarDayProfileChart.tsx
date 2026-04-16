"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface SolarDayPoint {
  hour: string;
  energyMWh: number;
  irradianceWm2: number;
  prPct: number;
}

interface SolarDayProfileChartProps {
  data: SolarDayPoint[];
}

export function SolarDayProfileChart({ data }: SolarDayProfileChartProps) {
  return (
    <ResponsiveContainer width="100%" height={348}>
      <ComposedChart
        data={data}
        margin={{ top: 10, right: 28, left: 6, bottom: 4 }}
        barCategoryGap={18}
        barGap={0}
      >
        <defs>
          <linearGradient id="energyFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#7dd3fc" stopOpacity={0.95} />
            <stop offset="100%" stopColor="#2563eb" stopOpacity={0.82} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e3a50" />
        <XAxis dataKey="hour" tick={{ fill: "#94a3b8", fontSize: 11 }} />
        <YAxis
          yAxisId="energy"
          tick={{ fill: "#cbd5e1", fontSize: 11 }}
          tickFormatter={(value: number) => `${value.toFixed(1)}`}
          label={{ value: "MWh", angle: -90, position: "insideLeft", offset: 2, fill: "#cbd5e1", fontSize: 11 }}
        />
        <YAxis
          yAxisId="irradiance"
          orientation="right"
          tick={{ fill: "#cbd5e1", fontSize: 11 }}
          tickFormatter={(value: number) => `${value.toFixed(0)}`}
          label={{ value: "W/m²", angle: 90, position: "insideRight", offset: 0, fill: "#cbd5e1", fontSize: 11 }}
        />
        <YAxis yAxisId="pr" hide domain={[60, 100]} />
        <Tooltip
          contentStyle={{ background: "#0B2A3D", border: "1px solid #003366", borderRadius: 8 }}
          labelStyle={{ color: "#f8fafc" }}
          itemStyle={{ color: "#f8fafc" }}
          formatter={(value: number, name: string) => {
            if (name === "PR") return [`${value.toFixed(1)}%`, "PR"];
            if (name === "Irradiance") return [`${value.toFixed(0)} W/m²`, "Irradiance"];
            return [`${value.toFixed(2)} MWh`, "Energy"];
          }}
        />
        <Legend wrapperStyle={{ color: "#e2e8f0", fontSize: 12 }} />
        <Bar
          yAxisId="energy"
          dataKey="energyMWh"
          name="Energy"
          fill="url(#energyFill)"
          radius={[8, 8, 0, 0]}
          barSize={88}
        />
        <Line
          yAxisId="irradiance"
          type="monotone"
          dataKey="irradianceWm2"
          name="Irradiance"
          stroke="#fbbf24"
          strokeWidth={2.6}
          dot={false}
          activeDot={{ r: 4, fill: "#fbbf24", stroke: "#0B2A3D", strokeWidth: 1.5 }}
        />
        <Line
          yAxisId="pr"
          type="monotone"
          dataKey="prPct"
          name="PR"
          stroke="#f8fafc"
          strokeWidth={2.2}
          strokeDasharray="4 4"
          dot={{ r: 3, fill: "#f8fafc", stroke: "#0B2A3D", strokeWidth: 1.5 }}
          activeDot={{ r: 4 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
