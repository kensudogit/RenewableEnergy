"""In-memory trading store (Postgres optional via init.sql for future sync)."""
from __future__ import annotations

from threading import Lock
from typing import Any

from src.config import get_settings
from src.trading.models import OrderRecord, Position, RunLog, TradingConfig

_lock = Lock()
_config = TradingConfig(mode=get_settings().trading_default_mode)  # type: ignore[arg-type]
_orders: list[OrderRecord] = []
_runs: list[RunLog] = []
_positions: dict[str, Position] = {}
_audit: list[dict] = []
_last_order_ts: float | None = None


def get_config() -> TradingConfig:
    with _lock:
        return TradingConfig(**_config.to_dict())


def update_config(patch: dict[str, Any]) -> TradingConfig:
    global _config
    with _lock:
        data = _config.to_dict()
        data.update({k: v for k, v in patch.items() if v is not None})
        # Safety: cannot enable live without gateway confirmation
        settings = get_settings()
        if data.get("mode") == "live" and not settings.live_trading_allowed:
            data["mode"] = "paper"
            data["enabled"] = False if patch.get("mode") == "live" else data.get("enabled", False)
        _config = TradingConfig.from_dict(data)
        return TradingConfig(**_config.to_dict())


def add_order(order: OrderRecord) -> OrderRecord:
    with _lock:
        _orders.insert(0, order)
        if len(_orders) > 500:
            del _orders[500:]
        return order


def list_orders(limit: int = 50) -> list[dict[str, Any]]:
    with _lock:
        return [o.to_dict() for o in _orders[:limit]]


def add_run(run: RunLog) -> RunLog:
    with _lock:
        _runs.insert(0, run)
        if len(_runs) > 200:
            del _runs[200:]
        return run


def list_runs(limit: int = 30) -> list[dict[str, Any]]:
    with _lock:
        return [r.to_dict() for r in _runs[:limit]]


def get_position(market: str) -> Position:
    with _lock:
        if market not in _positions:
            _positions[market] = Position(market=market)
        return Position(**_positions[market].to_dict())


def apply_fill(order: OrderRecord) -> Position:
    """Update net position and realized PnL on fill."""
    with _lock:
        pos = _positions.get(order.market) or Position(market=order.market)
        fill_mw = float(order.fill_volume_mw or order.volume_mw)
        fill_px = float(order.fill_price_yen or order.limit_price_yen)
        signed = fill_mw if order.side == "buy" else -fill_mw

        # Realize PnL when reducing / flipping
        if pos.net_mw != 0 and ((pos.net_mw > 0 and signed < 0) or (pos.net_mw < 0 and signed > 0)):
            close_mw = min(abs(pos.net_mw), abs(signed))
            direction = 1 if pos.net_mw > 0 else -1
            # Long closed by sell: (fill - avg) * mw * 1000
            # Short closed by buy: (avg - fill) * mw * 1000
            if direction > 0:
                pos.realized_pnl_jpy += (fill_px - pos.avg_price_yen) * close_mw * 1000.0
            else:
                pos.realized_pnl_jpy += (pos.avg_price_yen - fill_px) * close_mw * 1000.0

        new_net = pos.net_mw + signed
        if abs(new_net) < 1e-9:
            pos.net_mw = 0.0
            pos.avg_price_yen = 0.0
        elif pos.net_mw == 0 or (pos.net_mw > 0) != (new_net > 0):
            # open or flip residual
            residual = new_net
            pos.net_mw = residual
            pos.avg_price_yen = fill_px
        else:
            # add to same side
            total = abs(pos.net_mw) + abs(signed)
            pos.avg_price_yen = (
                (abs(pos.net_mw) * pos.avg_price_yen + abs(signed) * fill_px) / total
            )
            pos.net_mw = new_net

        from src.trading.models import utcnow

        pos.updated_at = utcnow().isoformat()
        _positions[order.market] = pos
        return Position(**pos.to_dict())


def list_positions() -> list[dict[str, Any]]:
    with _lock:
        return [p.to_dict() for p in _positions.values()]


def daily_stats() -> dict[str, float | int]:
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).date().isoformat()
    with _lock:
        todays = [o for o in _orders if o.created_at.startswith(today) and o.status == "filled"]
        notional = sum(float(o.notional_jpy or 0) for o in todays)
        return {"trades": len(todays), "notional_jpy": notional}


def get_last_order_ts() -> float | None:
    with _lock:
        return _last_order_ts


def set_last_order_ts(ts: float) -> None:
    global _last_order_ts
    with _lock:
        _last_order_ts = ts


def add_audit(event: str, payload: dict[str, Any] | None = None) -> None:
    from src.trading.models import utcnow

    with _lock:
        _audit.insert(
            0,
            {
                "ts": utcnow().isoformat(),
                "event": event,
                "payload": payload or {},
            },
        )
        if len(_audit) > 500:
            del _audit[500:]


def list_audit(limit: int = 50) -> list[dict[str, Any]]:
    with _lock:
        return list(_audit[:limit])


def performance_stats() -> dict[str, Any]:
    with _lock:
        filled = [o for o in _orders if o.status == "filled"]
        rejected = [o for o in _orders if o.status == "rejected"]
        buys = sum(1 for o in filled if o.side == "buy")
        sells = sum(1 for o in filled if o.side == "sell")
        notional = sum(float(o.notional_jpy or 0) for o in filled)
        realized = sum(p.realized_pnl_jpy for p in _positions.values())
        fill_rate = (len(filled) / max(len(_orders), 1)) * 100.0
        return {
            "total_orders": len(_orders),
            "filled": len(filled),
            "rejected": len(rejected),
            "buy_fills": buys,
            "sell_fills": sells,
            "fill_rate_pct": round(fill_rate, 1),
            "total_notional_jpy": round(notional, 2),
            "realized_pnl_jpy": round(realized, 2),
            "open_positions": len([p for p in _positions.values() if abs(p.net_mw) > 1e-9]),
        }
