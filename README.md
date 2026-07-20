# Renewable Energy Platform (GridLeaf)

再エネ向けの予測・リスク・収益シミュレーション開発環境です。

## モジュール

| モジュール | API | 説明 |
|---|---|---|
| 発電量予測 | `GET /api/forecast/generation` | 気象連動の太陽光・風力出力予測 |
| 電力需要予測 | `GET /api/forecast/demand` | エリア需要予測 |
| 市場価格予測 | `GET /api/forecast/market-price` | JEPX スポット等 |
| 燃料価格予測 | `GET /api/forecast/fuel-price` | LNG / 石炭 / 原油 |
| リスク分析 | `GET /api/risk` | VaR / CVaR / リスクスコア |
| 収益シミュレーション | `GET /api/simulate/revenue` | FIT + スポット + 最適充放電 |
| 蓄電池最適化 | `GET /api/optimize/battery` | HiGHS 線形計画で充放電計画 |
| VPP | `GET /api/vpp` | 複数アセット集約 + 柔軟性 |
| DR | `GET /api/dr` | ピークカットイベント計画 |
| 気象 | `GET /api/weather` | GHI / 風速 / 気温ドライバ |
| **市場一体最適化** | `GET /api/optimize/market` | 太陽光・風力変動 / 需給 / 価格を LP+AI+市場取引で最適化 |

### 市場一体最適化（IT・AI・市場取引）

`GET /api/optimize/market` は次を一体で扱います。

1. 太陽光発電の出力変動  
2. 風力発電の発電量変動  
3. 電力需給バランス  
4. 電力価格の変動  

- **IT**: 予測 + HiGHS 線形計画（充放電・売買・コミットメント追従）  
- **AI**: Railway Variables の `OPENAI_API_KEY` で取引戦略を生成  
- **市場取引**: 時間別 buy/sell スケジュール（JEPX スポット想定）  

UI: `/trading`

### 自動取引（Paper / Live）

| API | 説明 |
|---|---|
| `PUT /api/autotrade/config` | `enabled` / `mode=paper\|live` など |
| `POST /api/autotrade/evaluate` | 発注せずリスク判定 |
| `POST /api/autotrade/run` | 最適化→ガード→発注 |
| `POST /api/autotrade/scheduler/start\|stop` | 定期執行 |
| `GET /api/autotrade/readiness` | 実用性能スコア（動的） |

**Live に必要な Railway Variables**

- `BROKER_API_URL` — 発注ゲートウェイ POST 先
- `BROKER_API_KEY` — Bearer トークン
- `LIVE_TRADING_CONFIRM=I_UNDERSTAND_LIVE_RISK`
- （任意）`BROKER_ACCOUNT_ID`

UI: `/autotrade`

## 技術スタック

- **Backend**: Python 3.12 / FastAPI / scikit-learn / SQLAlchemy
- **Frontend**: Next.js 15 / React 19 / Recharts
- **DB**: PostgreSQL 16
- **Infra**: Docker Compose（ローカル） / Railway（本番単一コンテナ）

## ローカル起動

前提: Docker Desktop, **Python 3.12**（推奨。`py -3.12`）、Node.js 20+

```bat
setup.bat
```

別ターミナルで:

```bat
cd backend
.venv\Scripts\activate
python run.py
```

```bat
cd frontend
npm run dev
```

- UI: http://localhost:3000
- API: http://localhost:8020/docs （ローカル既定。Docker / Railway では 8000）
- Health: http://localhost:8020/health

Docker 一括起動:

```bat
docker compose up --build
```

## 環境変数

`.env.example` をコピーして `.env` を作成します。

| 変数 | 用途 |
|---|---|
| `DATABASE_URL` | PostgreSQL 接続 |
| `OPENAI_API_KEY` | AI 市場ブリーフ |
| `OPENAI_MODEL` | 既定 `gpt-4o-mini` |

## Railway

1. `railway login`
2. プロジェクトを `railway link`
3. Postgres プラグインを追加し `DATABASE_URL` を接続
4. OpenAI キーを Variables に追加:

```powershell
.\scripts\set-railway-openai.ps1
```

または:

```bash
railway variables set OPENAI_API_KEY=...
railway variables set OPENAI_MODEL=gpt-4o-mini
```

ルートの `Dockerfile` + `railway.toml` で Next.js と FastAPI を同一サービス起動します。

## 今後の拡張（成長テーマ）

- 再エネ導入拡大 / 蓄電池 / VPP / DR / スマートグリッド
- 実市場 API（JEPX・気象・IoT）連携
- 数理最適化（充放電計画・入札）
- ビッグデータパイプライン（AWS / Azure）

現状は合成時系列 + Ridge ラグ特徴量で、API・UI・DB・デプロイの骨格を先に固めています。
# RenewableEnergy
