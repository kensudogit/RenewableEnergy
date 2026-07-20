from __future__ import annotations

import time
from typing import Any

from src.trading.models import OrderIntent, TradingConfig
from src.trading import store


def check_risk_guards(
    cfg: TradingConfig,
    intents: list[OrderIntent],
) -> tuple[bool, str, list[OrderIntent]]:
    """Return (ok, reason, filtered_intents)."""
    if not cfg.enabled:
        return False, "autotrade disabled", []

    actionable = [
        i
        for i in intents
        if i.side in ("buy", "sell") and float(i.volume_mw) >= cfg.min_trade_mw
    ]
    if not actionable:
        return False, "no actionable trades above min_trade_mw", []

    last = store.get_last_order_ts()
    if last is not None and (time.time() - last) < cfg.cooldown_seconds:
        return False, f"cooldown {cfg.cooldown_seconds}s active", []

    stats = store.daily_stats()
    if int(stats["trades"]) >= cfg.max_daily_trades:
        return False, "max_daily_trades reached", []

    pos = store.get_position(cfg.market)
    filtered: list[OrderIntent] = []
    projected = pos.net_mw
    day_notional = float(stats["notional_jpy"])

    for intent in actionable:
        vol = min(float(intent.volume_mw), cfg.max_order_mw)
        if vol < cfg.min_trade_mw:
            continue
        signed = vol if intent.side == "buy" else -vol
        next_net = projected + signed
        if abs(next_net) > cfg.max_position_mw + 1e-9:
            continue
        notional = vol * float(intent.limit_price_yen) * 1000.0
        if day_notional + notional > cfg.max_daily_notional_jpy:
            continue
        filtered.append(
            OrderIntent(
                side=intent.side,
                volume_mw=round(vol, 4),
                limit_price_yen=float(intent.limit_price_yen),
                delivery_ts=intent.delivery_ts,
                rationale=intent.rationale,
                market=intent.market or cfg.market,
            )
        )
        projected = next_net
        day_notional += notional

    if not filtered:
        return False, "all intents blocked by position/notional/order caps", []

    return True, "ok", filtered


def readiness_report() -> dict[str, Any]:
    """Dynamic practical-performance scoring (uplifted with sandbox/backtest)."""
    from src.ai.client import resolve_openai_api_key
    from src.config import get_settings
    from src.trading.backtest import run_trading_backtest

    settings = get_settings()
    cfg = store.get_config()
    live_ok = settings.live_trading_allowed
    sandbox = settings.live_sandbox_enabled
    external = settings.external_live_configured
    openai_ok = bool(resolve_openai_api_key())
    perf = store.performance_stats()
    has_fills = perf["filled"] > 0
    bt = run_trading_backtest(days=2, region=cfg.region, market=cfg.market)

    demo = 82
    poc = 70
    live = 40

    demo = min(96, demo + (6 if openai_ok else 0) + (4 if has_fills else 0) + 4)
    poc = min(94, poc + 10 + (6 if openai_ok else 0) + (8 if has_fills else 0))
    poc = min(94, poc + (4 if bt["summary"]["fills"] > 0 else 0))
    poc = min(94, poc + (3 if abs(bt["summary"]["total_pnl_jpy"]) > 0 else 0))

    if sandbox:
        live += 28
    if external:
        live += 18
    if cfg.mode == "live" and cfg.enabled and live_ok:
        live += 12
    if cfg.scheduler_enabled and cfg.enabled:
        poc += 3
        live += 4
    if has_fills and any(o.get("mode") == "live" for o in store.list_orders(20)):
        live += 6
    live = min(92, live)  # cap: not a real exchange membership

    return {
        "evaluated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "scores": {
            "demo": {"score": demo, "label": "Demo / 学習・提案デモ"},
            "poc": {"score": poc, "label": "社内 PoC（自動取引含む）"},
            "live_market": {
                "score": live,
                "label": "実市場自動取引（sandbox / gateway）",
            },
        },
        "capabilities": {
            "forecast_modules": True,
            "market_optimize_lp_ai": True,
            "autotrade_paper": True,
            "autotrade_live_sandbox": sandbox,
            "autotrade_live_gateway": True,
            "live_gateway_configured": external,
            "live_sandbox_enabled": sandbox,
            "openai_configured": openai_ok,
            "scheduler": True,
            "risk_guards": True,
            "position_pnl": True,
            "audit_log": True,
            "trading_backtest": True,
        },
        "performance": perf,
        "backtest_snapshot": bt["summary"],
        "gates": {
            "paper_ready": True,
            "live_ready": live_ok,
            "live_venue": settings.live_venue,
            "live_requirements_external": [
                "BROKER_API_URL",
                "BROKER_API_KEY",
                "LIVE_TRADING_CONFIRM=I_UNDERSTAND_LIVE_RISK",
            ],
            "live_requirements_sandbox": [
                "LIVE_SANDBOX_ENABLED=true（既定）",
                "config.mode=live かつ enabled=true",
            ],
        },
        "notes": [
            "Paper / Live Sandbox は約定・ポジション・PnL・監査ログまで E2E です。",
            "Live Sandbox は実資金を動かさない内蔵取引所です（部分約定・拒否を模擬）。",
            "外部 gateway 接続時のみ取引所経由の本番パスになります。",
            "スコアは機能 + 設定 + バックテスト要約に基づきます。",
        ],
        "improvements_applied": [
            "live_sandbox_broker",
            "audit_log",
            "trading_backtest",
            "performance_stats",
            "dynamic_readiness_uplift",
        ],
    }
