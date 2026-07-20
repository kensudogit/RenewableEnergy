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
import { api, type DashboardResponse } from "@/lib/api";

function shortTs(ts: string) {
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, "0")}:00`;
}

export default function HomePage() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [themes, setThemes] = useState<string[]>([]);
  const [brief, setBrief] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.dashboard(), api.meta(), api.brief()])
      .then(([dash, meta, b]) => {
        setData(dash);
        setThemes(meta.growth_themes);
        setBrief(b.ai?.summary ?? "");
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const genSeries =
    data?.modules.generation.forecast.map((p) => ({
      ts: shortTs(p.ts),
      generation: p.value,
    })) ?? [];
  const priceSeries =
    data?.modules.market_price.forecast.map((p, i) => ({
      ts: shortTs(p.ts),
      price: p.value,
      demand: data.modules.demand.forecast[i]?.value,
    })) ?? [];

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>再エネ予測と収益の司令塔</h1>
        <p>
          発電量・電力需要・市場価格・燃料価格を一体で見通し、リスクと収益をシミュレートします。
        </p>
        {brief && <p className="muted">{brief}</p>}
        <div className="themes">
          {themes.map((t) => (
            <span key={t}>{t}</span>
          ))}
        </div>
      </section>

      {error && <p className="error">API エラー: {error}（backend 起動を確認してください）</p>}

      {data && (
        <section className="grid">
          <article className="panel">
            <h2>発電量予測</h2>
            <p className="sub">直近24時間平均（{data.modules.generation.unit}）</p>
            <div className="metrics">
              <div className="metric">
                <span className="label">Avg</span>
                <span className="value">{data.modules.generation.next_24h_avg}</span>
              </div>
            </div>
            <div style={{ width: "100%", height: 180 }}>
              <ResponsiveContainer>
                <LineChart data={genSeries}>
                  <CartesianGrid stroke="rgba(232,245,239,0.08)" />
                  <XAxis dataKey="ts" tick={{ fill: "#9bb5a8", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#9bb5a8", fontSize: 11 }} width={40} />
                  <Tooltip
                    contentStyle={{
                      background: "#0d241c",
                      border: "1px solid rgba(232,245,239,0.12)",
                    }}
                  />
                  <Line type="monotone" dataKey="generation" stroke="#3ecf8e" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="panel">
            <h2>需要 / 市場価格</h2>
            <p className="sub">需要と JEPX スポットの並走</p>
            <div className="metrics">
              <div className="metric">
                <span className="label">需要平均</span>
                <span className="value">{data.modules.demand.next_24h_avg}</span>
              </div>
              <div className="metric">
                <span className="label">価格平均</span>
                <span className="value">{data.modules.market_price.next_24h_avg}</span>
              </div>
            </div>
            <div style={{ width: "100%", height: 180 }}>
              <ResponsiveContainer>
                <LineChart data={priceSeries}>
                  <CartesianGrid stroke="rgba(232,245,239,0.08)" />
                  <XAxis dataKey="ts" tick={{ fill: "#9bb5a8", fontSize: 11 }} />
                  <YAxis yAxisId="l" tick={{ fill: "#9bb5a8", fontSize: 11 }} width={40} />
                  <YAxis
                    yAxisId="r"
                    orientation="right"
                    tick={{ fill: "#9bb5a8", fontSize: 11 }}
                    width={40}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#0d241c",
                      border: "1px solid rgba(232,245,239,0.12)",
                    }}
                  />
                  <Line
                    yAxisId="l"
                    type="monotone"
                    dataKey="demand"
                    stroke="#9bb5a8"
                    dot={false}
                  />
                  <Line
                    yAxisId="r"
                    type="monotone"
                    dataKey="price"
                    stroke="#f0b429"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="panel">
            <h2>燃料価格予測</h2>
            <p className="sub">
              {data.modules.fuel_price.commodity.toUpperCase()}（
              {data.modules.fuel_price.unit}）
            </p>
            <div className="metrics">
              <div className="metric">
                <span className="label">24h平均</span>
                <span className="value">{data.modules.fuel_price.next_24h_avg}</span>
              </div>
            </div>
          </article>

          <article className="panel">
            <h2>リスク分析</h2>
            <p className="sub">VaR / CVaR とリスクスコア</p>
            <div className="metrics">
              <div className="metric">
                <span className="label">Score</span>
                <span className="value">{data.modules.risk.risk_score}</span>
              </div>
              <div className="metric">
                <span className="label">VaR</span>
                <span className="value">
                  {Math.round(data.modules.risk.var_jpy).toLocaleString()}
                </span>
              </div>
              <div className="metric">
                <span className="label">CVaR</span>
                <span className="value">
                  {Math.round(data.modules.risk.cvar_jpy).toLocaleString()}
                </span>
              </div>
            </div>
          </article>

          <article className="panel">
            <h2>収益シミュレーション</h2>
            <p className="sub">FIT + スポット + 最適充放電</p>
            <div className="metrics">
              <div className="metric">
                <span className="label">総収益 (JPY)</span>
                <span className="value">
                  {Math.round(data.modules.revenue.total_revenue_jpy).toLocaleString()}
                </span>
              </div>
              <div className="metric">
                <span className="label">Battery cycles</span>
                <span className="value">
                  {data.modules.revenue.battery_cycles_proxy}
                </span>
              </div>
            </div>
          </article>

          <article className="panel">
            <h2>蓄電池 / VPP / DR</h2>
            <p className="sub">成長領域モジュール</p>
            <div className="metrics">
              <div className="metric">
                <span className="label">最適純収益</span>
                <span className="value">
                  {Math.round(
                    data.modules.battery_optimize?.total_net_revenue_jpy ?? 0
                  ).toLocaleString()}
                </span>
              </div>
              <div className="metric">
                <span className="label">VPP柔軟性</span>
                <span className="value">
                  {data.modules.vpp?.flexibility_mw ?? "-"}
                </span>
              </div>
              <div className="metric">
                <span className="label">DRイベント</span>
                <span className="value">
                  {data.modules.demand_response?.event_count ?? "-"}
                </span>
              </div>
              <div className="metric">
                <span className="label">ピーク削減MW</span>
                <span className="value">
                  {data.modules.demand_response?.peak_reduction_mw ?? "-"}
                </span>
              </div>
            </div>
          </article>
        </section>
      )}
    </main>
  );
}
