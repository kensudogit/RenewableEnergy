"use client";

import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Nav } from "@/components/Nav";

type MarketOpt = {
  solver: string;
  status: string;
  description: string;
  openai: { configured: boolean; model: string | null; source: string };
  pillars: {
    solar_volatility: number;
    wind_volatility: number;
    supply_demand_balance_rmse_mw: number;
    price_volatility: number;
    volatility_reduction_pct: number;
  };
  summary: {
    total_net_pnl_jpy: number;
    total_sell_mwh: number;
    total_buy_mwh: number;
    total_deficit_mwh: number;
  };
  series: Array<{
    ts: string;
    solar_mw: number;
    wind_mw: number;
    spot_yen_per_kwh: number;
    sell_mw: number;
    buy_mw: number;
    soc_mwh: number;
    area_residual_mw: number;
  }>;
  trades: Array<{
    ts: string;
    side: string;
    volume_mw: number;
    limit_price_yen_per_kwh: number;
    rationale: string;
  }>;
  ai: {
    summary?: string;
    strategy?: string;
    solar_actions?: string[];
    wind_actions?: string[];
    balance_actions?: string[];
    price_actions?: string[];
    trade_rules?: string[];
    risks?: string[];
    confidence?: number;
    openai_configured?: boolean;
    model?: string | null;
    error?: string;
  };
};

export default function TradingPage() {
  const [data, setData] = useState<MarketOpt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch("/api/optimize/market?horizon_hours=24&use_ai=true", { cache: "no-store" })
      .then(async (r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        return r.json() as Promise<MarketOpt>;
      })
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const chart =
    data?.series.map((r) => ({
      ts: new Date(r.ts).getHours() + ":00",
      solar: r.solar_mw,
      wind: r.wind_mw,
      price: r.spot_yen_per_kwh,
      sell: r.sell_mw,
      buy: r.buy_mw,
      residual: r.area_residual_mw,
    })) ?? [];

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>市場一体最適化</h1>
        <p>
          太陽光・風力の出力変動、需給バランス、価格変動を予測・数理最適化・AI・市場取引で最適化します。
          Railway の <code>OPENAI_API_KEY</code> を利用します。
        </p>
      </section>

      {loading && <p className="muted">最適化と AI 戦略を計算中…</p>}
      {error && <p className="error">エラー: {error}</p>}

      {data && (
        <section className="grid">
          <article className="panel">
            <h2>4本柱（変動指標）</h2>
            <p className="sub">
              solver: {data.solver} / OpenAI:{" "}
              {data.openai.configured ? data.openai.model ?? "on" : "未設定"}
            </p>
            <div className="metrics">
              <div className="metric">
                <span className="label">太陽光 vol</span>
                <span className="value">{data.pillars.solar_volatility}</span>
              </div>
              <div className="metric">
                <span className="label">風力 vol</span>
                <span className="value">{data.pillars.wind_volatility}</span>
              </div>
              <div className="metric">
                <span className="label">需給 RMSE</span>
                <span className="value">
                  {data.pillars.supply_demand_balance_rmse_mw}
                </span>
              </div>
              <div className="metric">
                <span className="label">価格 vol</span>
                <span className="value">{data.pillars.price_volatility}</span>
              </div>
              <div className="metric">
                <span className="label">変動低減%</span>
                <span className="value">{data.pillars.volatility_reduction_pct}</span>
              </div>
            </div>
          </article>

          <article className="panel">
            <h2>市場取引サマリー</h2>
            <div className="metrics">
              <div className="metric">
                <span className="label">純 PnL</span>
                <span className="value">
                  {Math.round(data.summary.total_net_pnl_jpy).toLocaleString()}
                </span>
              </div>
              <div className="metric">
                <span className="label">売電 MWh</span>
                <span className="value">{data.summary.total_sell_mwh}</span>
              </div>
              <div className="metric">
                <span className="label">買電 MWh</span>
                <span className="value">{data.summary.total_buy_mwh}</span>
              </div>
              <div className="metric">
                <span className="label">不足 MWh</span>
                <span className="value">{data.summary.total_deficit_mwh}</span>
              </div>
            </div>
          </article>

          <article className="panel wide">
            <h2>AI 戦略（OPENAI_API_KEY）</h2>
            <p className="sub">{data.ai.summary ?? "—"}</p>
            {data.ai.strategy && <p>{data.ai.strategy}</p>}
            {data.ai.error && <p className="error">{data.ai.error}</p>}
            <div className="grid" style={{ display: "grid", gap: "0.75rem" }}>
              {[
                ["太陽光", data.ai.solar_actions],
                ["風力", data.ai.wind_actions],
                ["需給", data.ai.balance_actions],
                ["価格取引", data.ai.price_actions],
              ].map(([title, items]) => (
                <div key={title as string}>
                  <strong>{title as string}</strong>
                  <ul className="muted">
                    {((items as string[]) ?? []).map((x) => (
                      <li key={x}>{x}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </article>

          <article className="panel wide">
            <h2>発電・価格・売買</h2>
            <div style={{ width: "100%", height: 300 }}>
              <ResponsiveContainer>
                <LineChart data={chart}>
                  <CartesianGrid stroke="rgba(232,245,239,0.08)" />
                  <XAxis dataKey="ts" tick={{ fill: "#9bb5a8", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#9bb5a8", fontSize: 11 }} width={45} />
                  <Tooltip
                    contentStyle={{
                      background: "#0d241c",
                      border: "1px solid rgba(232,245,239,0.12)",
                    }}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="solar" stroke="#f0b429" dot={false} />
                  <Line type="monotone" dataKey="wind" stroke="#3ecf8e" dot={false} />
                  <Line type="monotone" dataKey="price" stroke="#ff7a59" dot={false} />
                  <Line type="monotone" dataKey="sell" stroke="#9bb5a8" dot={false} />
                  <Line type="monotone" dataKey="buy" stroke="#6ec6ff" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="panel wide">
            <h2>取引スケジュール</h2>
            <ul className="muted">
              {data.trades
                .filter((t) => t.side !== "hold")
                .slice(0, 12)
                .map((t) => (
                  <li key={t.ts + t.side}>
                    {new Date(t.ts).toLocaleString("ja-JP")} — {t.side.toUpperCase()}{" "}
                    {t.volume_mw} MW @ {t.limit_price_yen_per_kwh} ¥/kWh（{t.rationale}）
                  </li>
                ))}
            </ul>
          </article>
        </section>
      )}
    </main>
  );
}
