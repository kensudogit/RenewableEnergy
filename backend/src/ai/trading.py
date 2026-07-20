"""AI market-trading advisor — uses Railway OPENAI_API_KEY via Settings."""
from __future__ import annotations

from typing import Any

from src.ai.client import chat_json, resolve_openai_api_key
from src.config import get_settings


def advise_market_trading(context: dict[str, Any]) -> dict[str, Any]:
    """
    Ask OpenAI for Japanese trading / balancing strategy.
    Uses OPENAI_API_KEY from Railway Variables (or local .env).
    """
    settings = get_settings()
    key = resolve_openai_api_key()
    system = (
        "あなたは日本の電力市場（JEPXスポット・需給調整）のトレーディングAIです。"
        "太陽光・風力の出力変動、需給バランス、価格変動を踏まえ、"
        "蓄電池充放電と市場売買で収益と安定供給を両立する戦略を提案してください。"
        "必ず次のJSONだけを返すこと: "
        '{"summary": str, '
        '"strategy": str, '
        '"solar_actions": [str], '
        '"wind_actions": [str], '
        '"balance_actions": [str], '
        '"price_actions": [str], '
        '"trade_rules": [str], '
        '"risks": [str], '
        '"confidence": number}'
    )
    user = (
        "次の定量コンテキストに基づき、今後の市場取引・運用方針を最適化提案してください。\n"
        f"{context}"
    )
    ai = chat_json(system=system, user=user)
    ai["openai_configured"] = bool(key)
    ai["model"] = (settings.openai_model if key else None)
    return ai
