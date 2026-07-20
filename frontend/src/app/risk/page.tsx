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
import { api, type RiskResponse } from "@/lib/api";

export default function RiskPage() {
  const [data, setData] = useState<RiskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .risk()
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  const series =
    data?.series.map((r) => ({
      ts: new Date(r.ts).getHours() + ":00",
      revenue: r.revenue_jpy,
    })) ?? [];

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>リスク分析</h1>
        <p>発電量帯と価格ボラティリティから VaR / CVaR・リスクスコアを算出します。</p>
      </section>
      {error && <p className="error">{error}</p>}
      {data && (
        <section className="grid">
          <article className="panel">
            <h2>指標</h2>
            <div className="metrics">
              <div className="metric">
                <span className="label">Risk score</span>
                <span className="value">{data.metrics.risk_score}</span>
              </div>
              <div className="metric">
                <span className="label">VaR</span>
                <span className="value">
                  {Math.round(data.metrics.var_jpy).toLocaleString()}
                </span>
              </div>
              <div className="metric">
                <span className="label">CVaR</span>
                <span className="value">
                  {Math.round(data.metrics.cvar_jpy).toLocaleString()}
                </span>
              </div>
              <div className="metric">
                <span className="label">Volume risk</span>
                <span className="value">{data.metrics.volume_risk_index}</span>
              </div>
            </div>
            <ul className="muted">
              {data.notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          </article>
          <article className="panel">
            <h2>時間収益パス</h2>
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <LineChart data={series}>
                  <CartesianGrid stroke="rgba(232,245,239,0.08)" />
                  <XAxis dataKey="ts" tick={{ fill: "#9bb5a8", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#9bb5a8", fontSize: 11 }} width={50} />
                  <Tooltip
                    contentStyle={{
                      background: "#0d241c",
                      border: "1px solid rgba(232,245,239,0.12)",
                    }}
                  />
                  <Line type="monotone" dataKey="revenue" stroke="#ff7a59" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </article>
        </section>
      )}
    </main>
  );
}
