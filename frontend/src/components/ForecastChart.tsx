"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Point } from "@/lib/api";

function shortTs(ts: string) {
  const d = new Date(ts);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}`;
}

export function ForecastChart({
  history,
  forecast,
  unit,
}: {
  history: Point[];
  forecast: Point[];
  unit: string;
}) {
  const data = [
    ...history.slice(-36).map((p) => ({
      ts: shortTs(p.ts),
      history: p.value,
    })),
    ...forecast.map((p) => ({
      ts: shortTs(p.ts),
      forecast: p.value,
      p10: p.p10,
      p90: p.p90,
    })),
  ];

  return (
    <div style={{ width: "100%", height: 260 }}>
      <ResponsiveContainer>
        <ComposedChart data={data}>
          <CartesianGrid stroke="rgba(232,245,239,0.08)" />
          <XAxis dataKey="ts" tick={{ fill: "#9bb5a8", fontSize: 11 }} minTickGap={24} />
          <YAxis
            tick={{ fill: "#9bb5a8", fontSize: 11 }}
            width={48}
            label={{ value: unit, angle: -90, position: "insideLeft", fill: "#9bb5a8" }}
          />
          <Tooltip
            contentStyle={{
              background: "#0d241c",
              border: "1px solid rgba(232,245,239,0.12)",
              borderRadius: 12,
            }}
          />
          <Legend />
          <Area
            type="monotone"
            dataKey="p90"
            stroke="none"
            fill="rgba(62,207,142,0.12)"
            name="P90"
          />
          <Area
            type="monotone"
            dataKey="p10"
            stroke="none"
            fill="rgba(7,21,16,0.35)"
            name="P10"
          />
          <Line
            type="monotone"
            dataKey="history"
            stroke="#9bb5a8"
            dot={false}
            strokeWidth={1.5}
            name="実績"
          />
          <Line
            type="monotone"
            dataKey="forecast"
            stroke="#3ecf8e"
            dot={false}
            strokeWidth={2.2}
            name="予測"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
