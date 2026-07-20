"use client";

import { useEffect, useState } from "react";
import { Nav } from "@/components/Nav";
import { ForecastChart } from "@/components/ForecastChart";
import type { ForecastResponse } from "@/lib/api";

export function ForecastPage({
  title,
  subtitle,
  loader,
  options,
}: {
  title: string;
  subtitle: string;
  loader: (key: string) => Promise<ForecastResponse>;
  options: { value: string; label: string }[];
}) {
  const [key, setKey] = useState(options[0]?.value ?? "");
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    loader(key)
      .then((d) => {
        if (alive) {
          setData(d);
          setError(null);
        }
      })
      .catch((e: Error) => {
        if (alive) setError(e.message);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [key, loader]);

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </section>
      <div className="controls">
        <select value={key} onChange={(e) => setKey(e.target.value)}>
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>
      <section className="panel wide">
        {loading && <p className="muted">読み込み中…</p>}
        {error && <p className="error">エラー: {error}</p>}
        {data && (
          <>
            <div className="metrics">
              <div className="metric">
                <span className="label">モデル</span>
                <span className="value">{data.model ?? "-"}</span>
              </div>
              <div className="metric">
                <span className="label">MAE</span>
                <span className="value">{data.metrics?.mae ?? "-"}</span>
              </div>
              <div className="metric">
                <span className="label">RMSE</span>
                <span className="value">{data.metrics?.rmse ?? "-"}</span>
              </div>
            </div>
            <ForecastChart
              history={data.history}
              forecast={data.forecast}
              unit={data.unit}
            />
          </>
        )}
      </section>
    </main>
  );
}
