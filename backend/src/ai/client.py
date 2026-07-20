from __future__ import annotations

import json
import os
from typing import Any

from src.config import get_settings


def resolve_openai_api_key() -> str:
    """Prefer process env (Railway Variables), then Settings/.env."""
    return (
        os.getenv("OPENAI_API_KEY", "").strip()
        or get_settings().openai_api_key.strip()
    )


def chat_json(system: str, user: str) -> dict[str, Any]:
    """Call OpenAI for structured JSON guidance. Falls back if key missing."""
    settings = get_settings()
    api_key = resolve_openai_api_key()
    if not api_key:
        return {
            "summary": "OPENAI_API_KEY 未設定のためローカル要約を返しています。",
            "insights": [
                "再エネ出力変動と需要ピークのギャップを蓄電池で緩和できます。",
                "JEPX スポット価格の夕方スパイクは収益機会になります。",
                "燃料価格上昇局面では市場価格ボラティリティに注意してください。",
            ],
            "actions": ["発電・需要・価格の予測レンジをダッシュボードで確認する"],
            "openai_configured": False,
        }

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system + " Always respond in Japanese JSON."},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        if isinstance(data, dict):
            data["openai_configured"] = True
        return data
    except Exception as exc:  # noqa: BLE001
        return {
            "summary": "AI 呼び出しに失敗したためフォールバック要約です。",
            "error": str(exc),
            "insights": [],
            "actions": [],
            "openai_configured": True,
        }
