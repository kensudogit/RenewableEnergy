-- Renewable Energy Platform schema

CREATE TABLE IF NOT EXISTS regions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Tokyo'
);

CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    code VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128) NOT NULL,
    asset_type VARCHAR(32) NOT NULL, -- solar, wind, hydro, battery
    region_id INTEGER REFERENCES regions(id),
    capacity_mw NUMERIC(12, 3) NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS generation_ts (
    id BIGSERIAL PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(id),
    ts TIMESTAMPTZ NOT NULL,
    mw NUMERIC(14, 4) NOT NULL,
    UNIQUE (asset_id, ts)
);

CREATE TABLE IF NOT EXISTS demand_ts (
    id BIGSERIAL PRIMARY KEY,
    region_id INTEGER REFERENCES regions(id),
    ts TIMESTAMPTZ NOT NULL,
    mw NUMERIC(14, 4) NOT NULL,
    UNIQUE (region_id, ts)
);

CREATE TABLE IF NOT EXISTS market_price_ts (
    id BIGSERIAL PRIMARY KEY,
    market_code VARCHAR(32) NOT NULL, -- jepx_spot, etc.
    ts TIMESTAMPTZ NOT NULL,
    yen_per_kwh NUMERIC(12, 4) NOT NULL,
    UNIQUE (market_code, ts)
);

CREATE TABLE IF NOT EXISTS fuel_price_ts (
    id BIGSERIAL PRIMARY KEY,
    commodity VARCHAR(32) NOT NULL, -- lng, coal, oil
    ts TIMESTAMPTZ NOT NULL,
    usd_per_unit NUMERIC(12, 4) NOT NULL,
    unit VARCHAR(16) NOT NULL DEFAULT 'mmbtu',
    UNIQUE (commodity, ts)
);

CREATE TABLE IF NOT EXISTS forecast_runs (
    id BIGSERIAL PRIMARY KEY,
    module VARCHAR(64) NOT NULL,
    target_code VARCHAR(64) NOT NULL,
    horizon_hours INTEGER NOT NULL,
    model_name VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metrics JSONB,
    payload JSONB
);

CREATE TABLE IF NOT EXISTS simulation_runs (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    params JSONB NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed regions
INSERT INTO regions (code, name) VALUES
    ('tokyo', '東京電力エリア'),
    ('kansai', '関西電力エリア'),
    ('chubu', '中部電力エリア'),
    ('kyushu', '九州電力エリア')
ON CONFLICT (code) DO NOTHING;

-- Seed assets
INSERT INTO assets (code, name, asset_type, region_id, capacity_mw)
SELECT 'solar_tokyo_1', '東京ソーラー1号', 'solar', r.id, 50
FROM regions r WHERE r.code = 'tokyo'
ON CONFLICT (code) DO NOTHING;

INSERT INTO assets (code, name, asset_type, region_id, capacity_mw)
SELECT 'wind_kyushu_1', '九州ウィンド1号', 'wind', r.id, 80
FROM regions r WHERE r.code = 'kyushu'
ON CONFLICT (code) DO NOTHING;

INSERT INTO assets (code, name, asset_type, region_id, capacity_mw)
SELECT 'battery_tokyo_1', '東京蓄電池1号', 'battery', r.id, 20
FROM regions r WHERE r.code = 'tokyo'
ON CONFLICT (code) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_generation_ts_asset_ts ON generation_ts(asset_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_demand_ts_region_ts ON demand_ts(region_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_market_price_ts ON market_price_ts(market_code, ts DESC);
CREATE INDEX IF NOT EXISTS idx_fuel_price_ts ON fuel_price_ts(commodity, ts DESC);
