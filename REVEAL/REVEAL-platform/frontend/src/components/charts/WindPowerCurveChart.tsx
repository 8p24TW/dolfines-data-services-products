"use client";

import {
  ComposedChart,
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface WindPowerCurveChartProps {
  manufacturer: string;
  ratedMw: number;
}

function buildCurve(manufacturer: string, ratedMw: number) {
  const maxKw = ratedMw * 1000;
  const points = [
    { windSpeed: 0, powerKw: 0 },
    { windSpeed: 1.5, powerKw: 0 },
    { windSpeed: 2.5, powerKw: maxKw * 0.02 },
    { windSpeed: 4, powerKw: maxKw * 0.12 },
    { windSpeed: 5.5, powerKw: maxKw * 0.28 },
    { windSpeed: 7, powerKw: maxKw * 0.5 },
    { windSpeed: 8.5, powerKw: maxKw * 0.74 },
    { windSpeed: 10, powerKw: maxKw * 0.95 },
    { windSpeed: 11, powerKw: maxKw },
    { windSpeed: 13, powerKw: maxKw },
    { windSpeed: 20, powerKw: maxKw },
    { windSpeed: 21.5, powerKw: maxKw * 0.98 },
  ];

  const manufacturerFactor =
    manufacturer.includes("Vestas") ? 1 :
    manufacturer.includes("Siemens") ? 0.98 :
    manufacturer.includes("GE") ? 1.02 :
    manufacturer.includes("Nordex") ? 0.97 :
    1;

  return points.map((point) => ({
    ...point,
    manufacturerKw: Math.max(0, Math.min(maxKw, point.powerKw * manufacturerFactor)),
  }));
}

function buildDemoCurves(ratedMw: number) {
  const maxKw = ratedMw * 1000;
  const refCurve = buildCurve("reference", ratedMw);
  const refAt = (speed: number) => {
    for (let i = 0; i < refCurve.length - 1; i += 1) {
      const a = refCurve[i];
      const b = refCurve[i + 1];
      if (speed >= a.windSpeed && speed <= b.windSpeed) {
        const ratio = (speed - a.windSpeed) / (b.windSpeed - a.windSpeed);
        return a.manufacturerKw + ratio * (b.manufacturerKw - a.manufacturerKw);
      }
    }
    return speed > 20 ? maxKw : 0;
  };

  const actualProduction = Array.from({ length: 140 }, (_, index) => {
    const windSpeed = Number((0.4 + index * 0.14).toFixed(2));
    const baseline = refAt(windSpeed);
    const lowWindLoss = windSpeed < 5 ? (5 - windSpeed) * 55 : 0;
    const highWindSoftening = windSpeed > 10.5 ? (windSpeed - 10.5) * 22 : 0;
    const smoothDrift = Math.sin(index / 8) * 45;
    const actualKw = Math.max(0, baseline - lowWindLoss - highWindSoftening + smoothDrift);
    return { windSpeed, actualKw: Math.min(maxKw * 0.995, actualKw) };
  });

  return { actualProduction };
}

export function WindPowerCurveChart({ manufacturer, ratedMw }: WindPowerCurveChartProps) {
  const data = buildCurve(manufacturer, ratedMw);
  const curves = buildDemoCurves(ratedMw);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 10, right: 20, left: 6, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e3a50" />
        <XAxis
          dataKey="windSpeed"
          type="number"
          domain={[0, 21]}
          ticks={[0, 2.5, 5, 7.5, 10, 12.5, 15, 17.5, 20]}
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickFormatter={(value: number) => value.toFixed(1)}
          unit=" m/s"
        />
        <YAxis
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickFormatter={(v: number) => `${v.toFixed(0)}`}
          label={{ value: "kW", angle: -90, position: "insideLeft", offset: 0, fill: "#cbd5e1", fontSize: 11 }}
        />
        <Tooltip
          contentStyle={{ background: "#0B2A3D", border: "1px solid #003366", borderRadius: 6 }}
          formatter={(value: number, name: string) => [
            `${value.toFixed(0)} kW`,
            name === "manufacturerKw" ? "Reference curve" : "Actual production",
          ]}
          labelFormatter={(value) => `${value} m/s`}
        />
        <Legend wrapperStyle={{ color: "#e2e8f0", fontSize: 12 }} />
        <Line
          type="monotone"
          dataKey="manufacturerKw"
          stroke="#1d4f7a"
          strokeWidth={3}
          dot={false}
          name="Reference curve"
        />
        <Line
          data={curves.actualProduction}
          dataKey="actualKw"
          type="monotone"
          stroke="#dbe7f3"
          strokeWidth={2.8}
          dot={false}
          connectNulls
          name="Actual production"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
