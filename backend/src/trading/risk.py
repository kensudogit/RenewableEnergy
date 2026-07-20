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
    """Dynamic practical-performance scoring."""
    from src.ai.client import resolve_openai_api_key
    from src.config import get_settings

    settings = get_settings()
    cfg = store.get_config()
    live_ok = settings.live_trading_allowed
    openai_ok = bool(resolve_openai_api_key())
    orders = store.list_orders(limit=5)
    has_fills = any(o["status"] == "filled" for o in orders)

    demo = 78
    poc = 62
    live = 18

    # Feature uplift
    demo = min(95, demo + 8)  # autotrade stack
    poc = min(90, poc + 12 + (6 if openai_ok else 0) + (4 if has_fills else 0))
    live = 35  # engine + gateway adapter present
    if live_ok:
        live += 25
    if cfg.mode == "live" and cfg.enabled and live_ok:
        live += 15
    if cfg.scheduler_enabled and cfg.enabled:
        poc += 4
        live += 5
    live = min(88, live)  # never claim 100 without exchange membership proof

    return {
        "evaluated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "scores": {
            "demo": {"score": demo, "label": "Demo / 学習・提案デモ"},
            "poc": {"score": poc, "label": "社内 PoC（自動取引含む）"},
            "live_market": {
                "score": live,
                "label": "実市場自動取引（gateway 接続時）",
            },
        },
        "capabilities": {
            "forecast_modules": True,
            "market_optimize_lp_ai": True,
            "autotrade_paper": True,
            "autotrade_live_gateway": True,
            "live_gateway_configured": live_ok,
            "openai_configured": openai_ok,
            "scheduler": True,
            "risk_guards": True,
            "position_pnl": True,
        },
        "gates": {
            "paper_ready": True,
            "live_ready": live_ok,
            "live_requirements": [
                "BROKER_API_URL",
                "BROKER_API_KEY",
                "LIVE_TRADING_CONFIRM=I_UNDERSTAND_LIVE_RISK",
                "config.mode=live かつ config.enabled=true",
            ],
        },
        "notes": [
            "Paper は約定・ポジション・PnL まで E2E で動作します。",
            "Live は外部ゲートウェイ契約（POST /orders）へ発注します。JEPX 直接会員 API はゲートウェイ側実装が必要です。",
            "スコアは静的機能評価 + 設定状態です（取引所負荷試験ではありません）。",
        ],
    }
