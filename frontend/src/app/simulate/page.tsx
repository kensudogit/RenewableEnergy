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
import { api, type RevenueResponse } from "@/lib/api";

export default function SimulatePage() {
  const [data, setData] = useState<RevenueResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .revenue()
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  const series =
    data?.series.map((r) => ({
      ts: new Date(r.ts).getHours() + ":00",
      total: r.total_revenue_jpy,
      fit: r.fit_revenue_jpy,
      spot: r.spot_revenue_jpy,
    })) ?? [];

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>収益シミュレーション</h1>
        <p>
          FIT 比率・スポット販売・蓄電池アービトラージを組み合わせた時間別収益を試算します。
        </p>
      </section>
      {error && <p className="error">{error}</p>}
      {data && (
        <section className="grid">
          <article className="panel wide">
            <h2>サマリー</h2>
            <div className="metrics">
              <div className="metric">
                <span className="label">総収益</span>
                <span className="value">
                  {Math.round(data.summary.total_revenue_jpy).toLocaleString()}
                </span>
              </div>
              <div className="metric">
                <span className="label">FIT</span>
                <span className="value">
                  {Math.round(data.summary.fit_revenue_jpy).toLocaleString()}
                </span>
              </div>
              <div className="metric">
                <span className="label">Spot</span>
                <span className="value">
                  {Math.round(data.summary.spot_revenue_jpy).toLocaleString()}
                </span>
              </div>
              <div className="metric">
                <span className="label">Battery cycles</span>
                <span className="value">{data.summary.battery_cycles_proxy}</span>
              </div>
            </div>
            <div style={{ width: "100%", height: 300 }}>
              <ResponsiveContainer>
                <AreaChart data={series}>
                  <CartesianGrid stroke="rgba(232,245,239,0.08)" />
                  <XAxis dataKey="ts" tick={{ fill: "#9bb5a8", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#9bb5a8", fontSize: 11 }} width={55} />
                  <Tooltip
                    contentStyle={{
                      background: "#0d241c",
                      border: "1px solid rgba(232,245,239,0.12)",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="fit"
                    stackId="1"
                    stroke="#3ecf8e"
                    fill="rgba(62,207,142,0.35)"
                  />
                  <Area
                    type="monotone"
                    dataKey="spot"
                    stackId="1"
                    stroke="#f0b429"
                    fill="rgba(240,180,41,0.3)"
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
