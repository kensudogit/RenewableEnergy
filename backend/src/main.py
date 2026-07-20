from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.api.analysis import router as analysis_router
from src.api.dashboard import router as dashboard_router
from src.api.forecast import router as forecast_router
from src.api.grid import router as grid_router
from src.ai.client import resolve_openai_api_key
from src.config import get_settings
from src.db import init_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(
    title="Renewable Energy Platform",
    description=(
        "発電量・需要・市場価格・燃料価格の予測、リスク分析、収益シミュレーション、"
        "蓄電池最適化、VPP、デマンドレスポンス"
    ),
    version="0.3.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecast_router)
app.include_router(analysis_router)
app.include_router(dashboard_router)
app.include_router(grid_router)


@app.get("/", response_class=HTMLResponse)
def root():
    """Browser-friendly landing (avoids bare {"detail":"Not Found"} on /)."""
    return """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GridLeaf API</title>
  <style>
    body { font-family: "IBM Plex Sans", system-ui, sans-serif; margin: 0;
      background: linear-gradient(160deg,#071510,#123528); color: #e8f5ef;
      min-height: 100vh; display: grid; place-items: center; }
    main { width: min(560px, calc(100% - 2rem)); }
    h1 { font-family: Georgia, serif; font-weight: 560; margin: 0 0 .5rem; }
    h1 span { color: #3ecf8e; }
    p { color: #9bb5a8; line-height: 1.5; }
    a { color: #3ecf8e; }
    ul { padding-left: 1.1rem; line-height: 1.8; }
  </style>
</head>
<body>
  <main>
    <h1>Grid<span>Leaf</span> API</h1>
    <p>バックエンドは稼働中です。UI または API ドキュメントへ進んでください。</p>
    <ul>
      <li><a href="http://localhost:3000">フロントエンド UI</a> — http://localhost:3000</li>
      <li><a href="/docs">Swagger API Docs</a></li>
      <li><a href="/health">Health check</a></li>
      <li><a href="/api/dashboard">Dashboard JSON</a></li>
    </ul>
  </main>
</body>
</html>"""


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": "renewable-energy",
        "modules": [
            "generation",
            "demand",
            "market_price",
            "fuel_price",
            "risk",
            "revenue_simulation",
            "battery_optimize",
            "vpp",
            "demand_response",
            "weather",
            "energy_market_optimize",
        ],
        "openai_configured": bool(resolve_openai_api_key()),
    }


@app.get("/api/meta")
def meta():
    return {
        "regions": ["tokyo", "kansai", "chubu", "kyushu"],
        "assets": ["solar_tokyo_1", "wind_kyushu_1", "battery_tokyo_1"],
        "markets": ["jepx_spot"],
        "commodities": ["lng", "coal", "oil"],
        "growth_themes": [
            "再エネ導入拡大",
            "蓄電池導入",
            "VPP",
            "デマンドレスポンス（DR）",
            "スマートグリッド",
            "2050カーボンニュートラル",
        ],
    }
