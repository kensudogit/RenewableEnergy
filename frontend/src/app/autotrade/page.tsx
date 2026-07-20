"use client";

import { useCallback, useEffect, useState } from "react";
import { Nav } from "@/components/Nav";

type Status = {
  config: {
    enabled: boolean;
    mode: "paper" | "live";
    market: string;
    max_order_mw: number;
    max_position_mw: number;
    scheduler_enabled: boolean;
    scheduler_interval_sec: number;
    use_ai: boolean;
  };
  scheduler: { running: boolean; interval_sec: number };
  position: {
    market: string;
    net_mw: number;
    avg_price_yen: number;
    realized_pnl_jpy: number;
  };
  recent_orders: Array<{
    client_order_id: string;
    side: string;
    volume_mw: number;
    status: string;
    fill_price_yen?: number;
    mode: string;
    created_at: string;
  }>;
  recent_runs: Array<{
    trigger: string;
    decision: string;
    message: string;
    created_at: string;
  }>;
  daily: { trades: number; notional_jpy: number };
  live_trading_allowed: boolean;
};

type Readiness = {
  scores: {
    demo: { score: number; label: string };
    poc: { score: number; label: string };
    live_market: { score: number; label: string };
  };
  gates: { live_ready: boolean; live_requirements: string[] };
  notes: string[];
};

export default function AutotradePage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [log, setLog] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [s, r] = await Promise.all([
      fetch("/api/autotrade/status", { cache: "no-store" }).then((x) => x.json()),
      fetch("/api/autotrade/readiness", { cache: "no-store" }).then((x) => x.json()),
    ]);
    setStatus(s);
    setReadiness(r);
  }, []);

  useEffect(() => {
    refresh().catch((e: Error) => setError(e.message));
  }, [refresh]);

  async function patchConfig(body: Record<string, unknown>) {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/autotrade/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || res.statusText);
      }
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function post(path: string) {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(path, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      setLog(JSON.stringify(data, null, 2));
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>自動取引（Paper / Live）</h1>
        <p>
          市場一体最適化の結果をリスクゲート通過後に発注します。既定は Paper
          約定。Live は Railway のゲートウェイ変数設定後に有効化できます。
        </p>
      </section>

      {error && <p className="error">{error}</p>}

      {readiness && (
        <section className="grid">
          <article className="panel wide">
            <h2>実用性能スコア（動的）</h2>
            <div className="metrics">
              <div className="metric">
                <span className="label">{readiness.scores.demo.label}</span>
                <span className="value">{readiness.scores.demo.score}</span>
              </div>
              <div className="metric">
                <span className="label">{readiness.scores.poc.label}</span>
                <span className="value">{readiness.scores.poc.score}</span>
              </div>
              <div className="metric">
                <span className="label">{readiness.scores.live_market.label}</span>
                <span className="value">{readiness.scores.live_market.score}</span>
              </div>
            </div>
            <p className="sub">
              Live ready: {readiness.gates.live_ready ? "YES" : "NO"} —{" "}
              {readiness.notes[0]}
            </p>
          </article>
        </section>
      )}

      {status && (
        <section className="grid">
          <article className="panel">
            <h2>設定</h2>
            <p className="sub">
              mode={status.config.mode} / enabled={String(status.config.enabled)} /
              live_allowed={String(status.live_trading_allowed)}
            </p>
            <div className="controls">
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  patchConfig({ enabled: !status.config.enabled, mode: "paper" })
                }
              >
                {status.config.enabled ? "停止 (disable)" : "Paper 有効化"}
              </button>
              <button
                type="button"
                disabled={busy || !status.live_trading_allowed}
                onClick={() => patchConfig({ mode: "live", enabled: true })}
              >
                Live 有効化
              </button>
              <button type="button" disabled={busy} onClick={() => post("/api/autotrade/evaluate")}>
                評価 (dry-run)
              </button>
              <button type="button" disabled={busy} onClick={() => post("/api/autotrade/run")}>
                今すぐ執行
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => post("/api/autotrade/scheduler/start")}
              >
                スケジューラ開始
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => post("/api/autotrade/scheduler/stop")}
              >
                スケジューラ停止
              </button>
            </div>
            <div className="metrics">
              <div className="metric">
                <span className="label">Scheduler</span>
                <span className="value">
                  {status.scheduler.running ? "RUN" : "OFF"}
                </span>
              </div>
              <div className="metric">
                <span className="label">本日約定</span>
                <span className="value">{status.daily.trades}</span>
              </div>
              <div className="metric">
                <span className="label">本日想定額</span>
                <span className="value">
                  {Math.round(status.daily.notional_jpy).toLocaleString()}
                </span>
              </div>
            </div>
          </article>

          <article className="panel">
            <h2>ポジション</h2>
            <div className="metrics">
              <div className="metric">
                <span className="label">Net MW</span>
                <span className="value">{status.position.net_mw}</span>
              </div>
              <div className="metric">
                <span className="label">Avg ¥/kWh</span>
                <span className="value">{status.position.avg_price_yen}</span>
              </div>
              <div className="metric">
                <span className="label">実現 PnL</span>
                <span className="value">
                  {Math.round(status.position.realized_pnl_jpy).toLocaleString()}
                </span>
              </div>
            </div>
          </article>

          <article className="panel wide">
            <h2>直近オーダー</h2>
            <ul className="muted">
              {status.recent_orders.slice(0, 10).map((o) => (
                <li key={o.client_order_id}>
                  {new Date(o.created_at).toLocaleString("ja-JP")} [{o.mode}]{" "}
                  {o.side.toUpperCase()} {o.volume_mw} MW — {o.status}
                  {o.fill_price_yen != null ? ` @ ${o.fill_price_yen}` : ""}
                </li>
              ))}
              {status.recent_orders.length === 0 && <li>まだ注文はありません</li>}
            </ul>
          </article>

          <article className="panel wide">
            <h2>実行ログ</h2>
            <ul className="muted">
              {status.recent_runs.slice(0, 8).map((r, i) => (
                <li key={r.created_at + i}>
                  {new Date(r.created_at).toLocaleString("ja-JP")} {r.trigger} →{" "}
                  <strong>{r.decision}</strong> — {r.message}
                </li>
              ))}
            </ul>
            {log && (
              <pre
                style={{
                  marginTop: "0.75rem",
                  padding: "0.75rem",
                  borderRadius: 12,
                  background: "rgba(0,0,0,0.25)",
                  overflow: "auto",
                  fontSize: 12,
                }}
              >
                {log}
              </pre>
            )}
          </article>
        </section>
      )}
    </main>
  );
}
