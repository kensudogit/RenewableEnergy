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
import { api, type DrResponse } from "@/lib/api";

export default function DrPage() {
  const [data, setData] = useState<DrResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .dr()
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  const series =
    data?.series.map((r) => ({
      ts: new Date(r.ts).getHours() + ":00",
      baseline: r.baseline_mw,
      adjusted: r.adjusted_mw,
    })) ?? [];

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>デマンドレスポンス（DR）</h1>
        <p>
          価格スパイクや需給逼迫時にピークカットイベントを計画し、削減量とインセンティブを試算します。
        </p>
      </section>
      {error && <p className="error">{error}</p>}
      {data && (
        <section className="grid">
          <article className="panel">
            <h2>サマリー</h2>
            <div className="metrics">
              <div className="metric">
                <span className="label">イベント数</span>
                <span className="value">{data.summary.event_count}</span>
              </div>
              <div className="metric">
                <span className="label">削減 MWh</span>
                <span className="value">{data.summary.total_shed_mwh}</span>
              </div>
              <div className="metric">
                <span className="label">ピーク削減 MW</span>
                <span className="value">{data.summary.peak_reduction_mw}</span>
              </div>
              <div className="metric">
                <span className="label">インセンティブ</span>
                <span className="value">
                  {Math.round(data.summary.incentive_cost_jpy).toLocaleString()}
                </span>
              </div>
            </div>
            <ul className="muted">
              {data.events.slice(0, 6).map((e) => (
                <li key={e.ts}>
                  {new Date(e.ts).toLocaleString("ja-JP")} — {e.shed_mw} MW / ¥
                  {Math.round(e.incentive_jpy).toLocaleString()}
                </li>
              ))}
            </ul>
          </article>
          <article className="panel">
            <h2>需要カーブ</h2>
            <div style={{ width: "100%", height: 280 }}>
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
                  <Line type="monotone" dataKey="baseline" stroke="#9bb5a8" dot={false} />
                  <Line type="monotone" dataKey="adjusted" stroke="#ff7a59" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </article>
        </section>
      )}
    </main>
  );
}
