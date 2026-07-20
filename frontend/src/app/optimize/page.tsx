"use client";

import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Nav } from "@/components/Nav";
import { api, type OptimizeResponse } from "@/lib/api";

export default function OptimizePage() {
  const [data, setData] = useState<OptimizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .optimize()
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  const series =
    data?.series.map((r) => ({
      ts: new Date(r.ts).getHours() + ":00",
      soc: r.soc_mwh,
      net: r.net_revenue_jpy,
      batt: r.battery_mw,
    })) ?? [];

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>蓄電池最適化</h1>
        <p>
          市場価格と発電予測を入力に、線形計画（HiGHS）で充放電スケジュールを最適化します。
        </p>
      </section>
      {error && <p className="error">{error}</p>}
      {data && (
        <section className="grid">
          <article className="panel">
            <h2>結果</h2>
            <p className="sub">
              solver: {data.solver} / {data.status}
            </p>
            <div className="metrics">
              <div className="metric">
                <span className="label">純収益</span>
                <span className="value">
                  {Math.round(data.summary.total_net_revenue_jpy).toLocaleString()}
                </span>
              </div>
              <div className="metric">
                <span className="label">充電 MWh</span>
                <span className="value">{data.summary.total_charge_mwh}</span>
              </div>
              <div className="metric">
                <span className="label">放電 MWh</span>
                <span className="value">{data.summary.total_discharge_mwh}</span>
              </div>
              <div className="metric">
                <span className="label">最終 SOC</span>
                <span className="value">{data.summary.final_soc_mwh}</span>
              </div>
            </div>
          </article>
          <article className="panel">
            <h2>SOC / 充放電</h2>
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <LineChart data={series}>
                  <CartesianGrid stroke="rgba(232,245,239,0.08)" />
                  <XAxis dataKey="ts" tick={{ fill: "#9bb5a8", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#9bb5a8", fontSize: 11 }} width={45} />
                  <Tooltip
                    contentStyle={{
                      background: "#0d241c",
                      border: "1px solid rgba(232,245,239,0.12)",
                    }}
                  />
                  <Line type="monotone" dataKey="soc" stroke="#3ecf8e" dot={false} />
                  <Line type="monotone" dataKey="batt" stroke="#f0b429" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </article>
        </section>
      )}
    </main>
  );
}
