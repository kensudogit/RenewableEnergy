"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import styles from "./UsageGuidePanel.module.css";

const STORAGE_KEY = "gridleaf-usage-guide-v1";

const techStack = [
  "Python · FastAPI",
  "Next.js · React",
  "PostgreSQL",
  "scikit-learn · SciPy",
  "OpenAI · gpt-4o-mini",
  "Recharts",
  "Docker · Railway",
  "VPP · DR · JEPX",
] as const;

const archDiagram = `Browser (運用 / トレーダー)
    │ HTTPS
    ▼
Next.js :PORT (Railway)
    ├─ /                 ダッシュボード
    ├─ /forecast/*       発電・需要・価格・燃料
    ├─ /trading          市場一体最適化 + AI
    ├─ /autotrade        自動取引 Paper/Live
    ├─ /optimize         蓄電池 LP
    ├─ /vpp · /dr        VPP / デマンドレスポンス
    ├─ /risk · /simulate リスク / 収益
    └─ /api/* ──rewrite──► FastAPI :8000
              ├─ 時系列予測 (Ridge lags)
              ├─ HiGHS LP + リスクゲート
              ├─ Paper book / Live gateway
              ├─ OpenAI (OPENAI_API_KEY)
              └─ PostgreSQL`;

const recommendedFlow = [
  "① / でダッシュボード全体を把握",
  "② /trading で4本柱最適化と売買候補を確認",
  "③ /autotrade で Paper 有効化 → 評価(dry-run) → 今すぐ執行",
  "④ ポジション・約定・実現 PnL を確認",
  "⑤ 問題なければスケジューラ開始（間隔は設定で変更）",
  "⑥ Live は BROKER_* + LIVE_TRADING_CONFIRM 設定後のみ",
] as const;

const readinessScores = [
  { label: "Demo / 学習・提案デモ", score: "92+/100" },
  { label: "社内 PoC（自動取引含む）", score: "90+/100" },
  { label: "実市場自動取引（sandbox / gateway）", score: "70–92/100" },
] as const;

const readinessDo = [
  "予測→/trading→/autotrade(Paper) を常用フローにする",
  "執行前に必ず 評価(dry-run) でリスクゲート結果を見る",
  "Railway の OPENAI_API_KEY で AI 戦略を併用する",
  "Live は専用ゲートウェイ URL/キーと確認フレーズ設定後のみ有効化",
] as const;

const readinessDont = [
  "LIVE_TRADING_CONFIRM 未設定のまま mode=live にしない",
  "合成価格のみを大規模実資金入札の唯一根拠にしない",
  "OPENAI_API_KEY / BROKER_API_KEY を公開リポジトリに載せない",
  "ゲートウェイ未契約のまま本番 JEPX 直接発注できると誤解しない",
] as const;

const steps = [
  {
    title: "0. 最短フロー（画面操作）",
    body: "ローカルまたは Railway 本番 URL で、予測から市場最適化まで一通り確認します。",
    items: [...recommendedFlow],
  },
  {
    title: "1. 起動とヘルスチェック",
    body: "API と UI が生きていることを先に確認します。",
    items: [
      "ローカル Backend: cd backend → .venv 有効化 → python run.py（既定 :8020）",
      "ローカル Frontend: cd frontend → npm run dev（:3000、/api を :8020 へプロキシ）",
      "Postgres: docker compose up -d postgres（:5434）",
      "確認: /health → status:ok · openai_configured · energy_market_optimize 含む",
      "Railway: 単一コンテナ（Next:PORT + uvicorn:8000）· DATABASE_URL / OPENAI_API_KEY",
    ],
  },
  {
    title: "2. 発電量予測（太陽光・風力の変動）",
    body: "気象ドライバ（GHI / 風 / 気温）連動の出力予測です。",
    items: [
      "画面: /forecast/generation",
      "アセット切替: solar_tokyo_1 / wind_kyushu_1 / battery_tokyo_1",
      "API: GET /api/forecast/generation?asset_code=...&horizon_hours=48",
      "見る点: 実績→予測の接続、P10/P90 バンド、単日の山谷（太陽光）と風のうねり",
      "モデル: weather_ridge_lags（デモ用。本番は実観測で再学習）",
    ],
  },
  {
    title: "3. 需要・市場価格・燃料価格",
    body: "需給バランスと価格変動の入力を揃えます。",
    items: [
      "/forecast/demand — エリア需要（tokyo / kansai / chubu / kyushu）",
      "/forecast/market-price — JEPX スポット想定（¥/kWh）",
      "/forecast/fuel-price — LNG / 石炭 / 原油（限界費用の参考）",
      "API: /api/forecast/demand · market-price · fuel-price",
      "夕方価格スパイクと需要ピークの重なりを意識して次の最適化へ",
    ],
  },
  {
    title: "4. 市場一体最適化（IT · AI · 取引）★本丸",
    body: "太陽光・風力変動 / 需給 / 価格を LP と OpenAI で一体最適化し、売買計画を出します。",
    items: [
      "画面: /trading",
      "API: GET /api/optimize/market?horizon_hours=24&use_ai=true",
      "IT: HiGHS 線形計画（充放電 · buy/sell · コミットメント追従）",
      "AI: Railway OPENAI_API_KEY → 太陽光/風力/需給/価格ごとのアクション提案",
      "市場: trades[]（side · volume_mw · limit_price · rationale）",
      "KPI: solar/wind/price volatility · 需給 RMSE · volatility_reduction_pct · PnL",
    ],
  },
  {
    title: "5. 蓄電池・VPP・DR",
    body: "柔軟性リソースで変動を吸収し、ピークを抑えます。",
    items: [
      "/optimize — 蓄電池単体 LP（SOC · 充放電 · 純収益）",
      "/vpp — 複数アセット集約 + 柔軟供給カーブ",
      "/dr — 価格/逼迫トリガでのピークカットとインセンティブ試算",
      "API: /api/optimize/battery · /api/vpp · /api/dr · /api/weather",
    ],
  },
  {
    title: "6. リスクと収益シミュレーション",
    body: "意思決定の裏取りです。",
    items: [
      "/risk — VaR / CVaR / risk_score（発電×価格の時間収益）",
      "/simulate — FIT + スポット + 最適充放電の収益内訳",
      "API: /api/risk · /api/simulate/revenue",
      "ダッシュボード /api/dashboard で主要 KPI を一括取得可",
    ],
  },
  {
    title: "7. AI・環境変数（Railway）",
    body: "Variables に設定したキーをバックエンドが読みます。",
    items: [
      "必須: OPENAI_API_KEY（Service Variables）",
      "推奨: OPENAI_MODEL=gpt-4o-mini · DATABASE_URL（Postgres プラグイン）",
      "解決順: プロセス環境変数 → .env（ローカル）",
      "未設定時: AI はルールベース要約にフォールバック（予測・LP は動作継続）",
      "確認: /health の openai_configured: true",
    ],
  },
  {
    title: "8. トラブルシューティング",
    body: "よくある詰まりと対処です。",
    items: [
      "8020 で Not Found → / は案内ページ、API は /docs · UI は :3000",
      "ポート競合 → ローカル API は PORT=8020（.env）。Docker/Railway は 8000",
      "Python 3.14 で pip 失敗 → py -3.12 -m venv .venv",
      "チャート空・API エラー → Backend 起動と next.config の INTERNAL_API_URL",
      "AI がフォールバック → Railway Variables を再デプロイ後に確認",
    ],
  },
  {
    title: "9. 自動取引 Paper / Live",
    body: "最適化結果をリスクゲート後に発注し、ポジションと PnL を更新します。",
    items: [
      "画面: /autotrade",
      "API: PUT /api/autotrade/config · POST /evaluate · POST /run",
      "Paper: 即時約定（スリッページ模擬）· ポジション/実現PnL 更新",
      "Live: POST BROKER_API_URL（Bearer BROKER_API_KEY）へ発注",
      "ガード: enabled · cooldown · max_order/position · daily trades/notional",
      "スケジューラ: POST /api/autotrade/scheduler/start|stop",
      "動的スコア: GET /api/autotrade/readiness",
    ],
  },
  {
    title: "10. 実用性能評価（2026-07・自動取引実装後）",
    body: "機能実装と設定状態に基づく評価。最新値は /autotrade または /api/autotrade/readiness。",
    items: [
      "Demo 約86 · PoC 約80 · Live 60（未接続）〜88（gateway+有効化時）",
      "Usable: 予測群 · 市場最適化 · Paper自動取引 · スケジューラ · リスクゲート",
      "Live-ready: 外部発注アダプタ実装済み（要 BROKER_* と確認フレーズ）",
      "残課題: 取引所ネイティブプロトコル · 多口座 · 監査SSO · 実気象取込",
      "レイテンシ: Paper執行 数秒 · AI付きサイクル 5–20s",
    ],
  },
] as const;

type Props = {
  open: boolean;
  onClose: () => void;
};

export function UsageGuidePanel({ open, onClose }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    originX: number;
    originY: number;
  } | null>(null);

  const [expanded, setExpanded] = useState(true);
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw) as { pos?: { x: number; y: number }; expanded?: boolean };
      if (saved.pos) setPos(saved.pos);
      if (typeof saved.expanded === "boolean") setExpanded(saved.expanded);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ pos, expanded }));
    } catch {
      /* ignore */
    }
  }, [open, pos, expanded]);

  const onHeaderPointerDown = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if ((e.target as HTMLElement).closest("[data-ug-toggle]")) return;
      if (!pos) return;
      dragRef.current = {
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        originX: pos.x,
        originY: pos.y,
      };
      setDragging(true);
      e.currentTarget.setPointerCapture(e.pointerId);
    },
    [pos],
  );

  const onHeaderPointerMove = useCallback((e: React.PointerEvent<HTMLElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    setPos({
      x: drag.originX + (e.clientX - drag.startX),
      y: drag.originY + (e.clientY - drag.startY),
    });
  }, []);

  const onHeaderPointerUp = useCallback((e: React.PointerEvent<HTMLElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    dragRef.current = null;
    setDragging(false);
    e.currentTarget.releasePointerCapture(e.pointerId);
  }, []);

  if (!open) return null;

  const style =
    pos != null
      ? ({
          position: "fixed" as const,
          left: pos.x,
          top: pos.y,
          right: "auto",
          bottom: "auto",
          width: "min(420px, calc(100vw - 2rem))",
          margin: 0,
        } as const)
      : undefined;

  return (
    <div
      ref={panelRef}
      className={`${styles.panel}${expanded ? "" : ` ${styles.collapsed}`}${dragging ? ` ${styles.dragging}` : ""}`}
      style={style}
      role="dialog"
      aria-label="利用手順"
      aria-modal="false"
    >
      <header
        className={styles.header}
        onPointerDown={(e) => {
          if ((e.target as HTMLElement).closest("[data-ug-toggle]")) return;
          if (pos == null && panelRef.current) {
            const rect = panelRef.current.getBoundingClientRect();
            setPos({ x: rect.left, y: rect.top });
            dragRef.current = {
              pointerId: e.pointerId,
              startX: e.clientX,
              startY: e.clientY,
              originX: rect.left,
              originY: rect.top,
            };
            setDragging(true);
            e.currentTarget.setPointerCapture(e.pointerId);
            return;
          }
          onHeaderPointerDown(e);
        }}
        onPointerMove={onHeaderPointerMove}
        onPointerUp={onHeaderPointerUp}
        onPointerCancel={onHeaderPointerUp}
      >
        <div className={styles.headerText}>
          <span aria-hidden>☰</span>
          <div className={styles.headerTitles}>
            <strong>利用手順</strong>
            <span className={styles.headerSub}>Architecture &amp; Ops</span>
          </div>
          <span className={styles.dragHint}>ドラッグで移動</span>
        </div>
        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.toggle}
            data-ug-toggle
            aria-label={expanded ? "折りたたむ" : "開く"}
            aria-expanded={expanded}
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? "▼" : "▲"}
          </button>
          <button
            type="button"
            className={styles.closeBtn}
            data-ug-toggle
            aria-label="閉じる"
            onClick={onClose}
          >
            ×
          </button>
        </div>
      </header>

      {expanded ? (
        <div className={styles.body}>
          <div className={styles.hero}>
            <p className={styles.heroKicker}>Energy market demo</p>
            <h2 className={styles.heroTitle}>GridLeaf — 予測 · 最適化 · 取引</h2>
            <p className={styles.heroLead}>
              太陽光・風力の出力変動、需給バランス、電力価格変動を、時系列予測・数理最適化・OpenAI・市場取引計画で一体支援するワークフローです。実市場への自動発注は未接続です。
            </p>
            <div className={styles.stack} aria-label="Tech stack">
              {techStack.map((tag) => (
                <span key={tag} className={styles.stackPill}>
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <section className={styles.featured} aria-label="アーキテクチャ">
            <div className={styles.featuredHead}>
              <span className={styles.featuredBadge}>Architecture</span>
              <strong>エンドツーエンド・パイプライン</strong>
            </div>
            <p>
              気象連動発電予測 → 需要/価格予測 → 蓄電池LP → 市場一体最適化（buy/sell）→
              AI戦略 → VPP/DR → リスク/収益までを一連で実行します。
            </p>
          </section>

          <section className={styles.featured} aria-label="推奨フロー">
            <div className={styles.featuredHead}>
              <span className={styles.featuredBadge}>Recommended</span>
              <strong>最短・安全な進め方</strong>
            </div>
            <p>
              まずダッシュボードで全体を掴み、/trading で4本柱の最適化結果と AI
              提案を確認します。売買スケジュールは意思決定支援として扱い、実発注は人手で判断してください。
            </p>
            <ul className={styles.items}>
              {recommendedFlow.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>

          <section className={styles.featured} aria-label="実用性能">
            <div className={styles.featuredHead}>
              <span className={styles.featuredBadge}>Readiness</span>
              <strong>実用性能の目安（2026-07）</strong>
            </div>
            <p>
              静的レビュー + デモ実行に基づくレディネスです。負荷試験や実市場スリッページは含みません。
            </p>
            <div className={styles.scoreRow}>
              {readinessScores.map((s) => (
                <div key={s.label} style={{ display: "contents" }}>
                  <span>{s.label}</span>
                  <span>{s.score}</span>
                </div>
              ))}
            </div>
            <p>
              <strong>やってよいこと</strong>
            </p>
            <ul className={styles.items}>
              {readinessDo.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p>
              <strong>やらないこと</strong>
            </p>
            <ul className={styles.items}>
              {readinessDont.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>

          <section className={styles.featured} aria-label="4本柱">
            <div className={styles.featuredHead}>
              <span className={styles.featuredBadge}>Optimize</span>
              <strong>最適化の4本柱</strong>
            </div>
            <ul className={styles.items}>
              <li>太陽光発電の出力変動 — 予測バンド + 充電でピーク吸収</li>
              <li>風力発電の発電量変動 — ポートフォリオ集約 + 放電補完</li>
              <li>電力需給バランス — エリア残差 KPI + コミットメント追従</li>
              <li>電力価格の変動 — スポットを目的関数に入れた時間別売買</li>
            </ul>
          </section>

          <figure className={styles.diagram} aria-label="Service topology">
            <figcaption>Service topology</figcaption>
            <pre>{archDiagram}</pre>
          </figure>

          <p className={styles.scrollHint}>↓ セットアップから運用までの詳細手順</p>

          <ol className={styles.steps}>
            {steps.map((step) => (
              <li key={step.title}>
                <strong>{step.title}</strong>
                <p>{step.body}</p>
                <ul className={styles.items}>
                  {step.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>

          <p className={styles.footer}>
            ▼▲ で開閉 · ドラッグで移動 · × で閉じる · 常用は 予測→/trading→/autotrade(Paper) ·
            Live は gateway 設定後 · OPENAI_API_KEY / BROKER_* は Railway Variables
          </p>
        </div>
      ) : null}
    </div>
  );
}

export function UsageGuideFab({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" className={styles.fab} onClick={onClick} aria-label="利用手順を開く">
      利用手順
    </button>
  );
}
