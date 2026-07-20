from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

Mode = Literal["paper", "live"]
Side = Literal["buy", "sell", "hold"]
OrderStatus = Literal["submitted", "filled", "rejected", "cancelled"]
Decision = Literal["executed", "blocked", "ready", "failed", "disabled"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TradingConfig:
    enabled: bool = False
    mode: Mode = "paper"
    market: str = "jepx_spot"
    region: str = "tokyo"
    max_order_mw: float = 10.0
    max_position_mw: float = 50.0
    max_daily_trades: int = 48
    max_daily_notional_jpy: float = 50_000_000.0
    min_trade_mw: float = 0.1
    cooldown_seconds: int = 60
    scheduler_enabled: bool = False
    scheduler_interval_sec: int = 300
    use_ai: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TradingConfig":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class OrderIntent:
    side: Side
    volume_mw: float
    limit_price_yen: float
    delivery_ts: str | None = None
    rationale: str = ""
    market: str = "jepx_spot"


@dataclass
class OrderRecord:
    client_order_id: str
    mode: Mode
    market: str
    side: str
    volume_mw: float
    limit_price_yen: float
    status: OrderStatus
    broker_order_id: str | None = None
    fill_price_yen: float | None = None
    fill_volume_mw: float | None = None
    notional_jpy: float | None = None
    rationale: str = ""
    delivery_ts: str | None = None
    created_at: str = field(default_factory=lambda: utcnow().isoformat())
    filled_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def new_id() -> str:
        return f"gl-{uuid4().hex[:16]}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Position:
    market: str
    net_mw: float = 0.0
    avg_price_yen: float = 0.0
    realized_pnl_jpy: float = 0.0
    updated_at: str = field(default_factory=lambda: utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunLog:
    trigger: str
    mode: Mode
    decision: Decision
    orders_submitted: int = 0
    message: str = ""
    snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
