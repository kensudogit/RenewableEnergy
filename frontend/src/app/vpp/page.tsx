"use client";

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Nav } from "@/components/Nav";
import { api, type VppResponse } from "@/lib/api";

export default function VppPage() {
  const [data, setData] = useState<VppResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .vpp()
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  const series =
    data?.series.map((r) => ({
      ts: new Date(r.ts).getHours() + ":00",
      generation: r.generation_mw,
      flexible: r.flexible_mw,
    })) ?? [];

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>VPP（仮想発電所）</h1>
        <p>複数アセットの発電を束ね、蓄電池で柔軟性を載せた供給カーブを作ります。</p>
      </section>
      {error && <p className="error">{error}</p>}
      {data && (
        <section className="grid">
          <article className="panel wide">
            <h2>ポートフォリオ</h2>
            <p className="sub">{data.assets.join(" / ")}</p>
            <div className="metrics">
              <div className="metric">
                <span className="label">ピーク柔軟供給</span>
                <span className="value">{data.summary.peak_flexible_mw}</span>
              </div>
              <div className="metric">
                <span className="label">平均柔軟供給</span>
                <span className="value">{data.summary.avg_flexible_mw}</span>
              </div>
              <div className="metric">
                <span className="label">柔軟性</span>
                <span className="value">{data.summary.flexibility_mw}</span>
              </div>
            </div>
            <div style={{ width: "100%", height: 300 }}>
              <ResponsiveContainer>
                <AreaChart data={series}>
                  <CartesianGrid stroke="rgba(232,245,239,0.08)" />
                  <XAxis dataKey="ts" tick={{ fill: "#9bb5a8", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#9bb5a8", fontSize: 11 }} width={45} />
                  <Tooltip
                    contentStyle={{
                      background: "#0d241c",
                      border: "1px solid rgba(232,245,239,0.12)",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="generation"
                    stroke="#9bb5a8"
                    fill="rgba(155,181,168,0.25)"
                  />
                  <Area
                    type="monotone"
                    dataKey="flexible"
                    stroke="#3ecf8e"
                    fill="rgba(62,207,142,0.28)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </article>
        </section>
      )}
    </main>
  );
}
