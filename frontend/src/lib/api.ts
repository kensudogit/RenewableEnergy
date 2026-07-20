const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export type Point = {
  ts: string;
  value: number;
  p10?: number;
  p90?: number;
};

export type ForecastResponse = {
  module: string;
  unit: string;
  model?: string;
  metrics?: { mae?: number | null; rmse?: number | null };
  history: Point[];
  forecast: Point[];
  [key: string]: unknown;
};

export type DashboardResponse = {
  region: string;
  asset_code: string;
  modules: {
    generation: { unit: string; next_24h_avg: number; forecast: Point[]; metrics?: object };
    demand: { unit: string; next_24h_avg: number; forecast: Point[] };
    market_price: { unit: string; next_24h_avg: number; forecast: Point[] };
    fuel_price: { unit: string; commodity: string; next_24h_avg: number; forecast: Point[] };
    risk: {
      expected_hourly_revenue_jpy: number;
      var_jpy: number;
      cvar_jpy: number;
      risk_score: number;
      volume_risk_index: number;
      price_volatility: number;
    };
    revenue: {
      total_revenue_jpy: number;
      fit_revenue_jpy: number;
      spot_revenue_jpy: number;
      avg_hourly_revenue_jpy: number;
      battery_cycles_proxy: number;
      optimizer?: string;
      battery_net_revenue_jpy?: number;
    };
    battery_optimize?: {
      total_net_revenue_jpy: number;
      avg_hourly_net_jpy: number;
      total_charge_mwh: number;
      total_discharge_mwh: number;
      final_soc_mwh: number;
    };
    vpp?: {
      peak_flexible_mw: number;
      avg_flexible_mw: number;
      flexibility_mw: number;
    };
    demand_response?: {
      event_count: number;
      total_shed_mwh: number;
      peak_reduction_mw: number;
      incentive_cost_jpy: number;
    };
  };
};

export type OptimizeResponse = {
  solver: string;
  status: string;
  summary: NonNullable<DashboardResponse["modules"]["battery_optimize"]> & {
    objective_jpy?: number;
  };
  series: Array<{
    ts: string;
    generation_mw: number;
    charge_mw: number;
    discharge_mw: number;
    battery_mw: number;
    soc_mwh: number;
    spot_yen_per_kwh: number;
    net_revenue_jpy: number;
  }>;
};

export type VppResponse = {
  summary: NonNullable<DashboardResponse["modules"]["vpp"]>;
  series: Array<{
    ts: string;
    generation_mw: number;
    battery_mw: number;
    flexible_mw: number;
  }>;
  assets: string[];
};

export type DrResponse = {
  summary: NonNullable<DashboardResponse["modules"]["demand_response"]>;
  events: Array<{ ts: string; shed_mw: number; incentive_jpy: number }>;
  series: Array<{
    ts: string;
    baseline_mw: number;
    adjusted_mw: number;
    shed_mw: number;
    spot_yen_per_kwh: number;
  }>;
};

export type RiskResponse = {
  metrics: DashboardResponse["modules"]["risk"];
  series: Array<{
    ts: string;
    revenue_jpy: number;
    generation_mw: number;
    price_yen_per_kwh: number;
  }>;
  notes: string[];
};

export type RevenueResponse = {
  summary: DashboardResponse["modules"]["revenue"];
  series: Array<{
    ts: string;
    total_revenue_jpy: number;
    fit_revenue_jpy: number;
    spot_revenue_jpy: number;
    battery_mw: number;
    generation_mw: number;
  }>;
  params: Record<string, unknown>;
};

export const api = {
  dashboard: (q = "region=tokyo&asset_code=solar_tokyo_1") =>
    getJson<DashboardResponse>(`/api/dashboard?${q}`),
  generation: (asset = "solar_tokyo_1", h = 48) =>
    getJson<ForecastResponse>(
      `/api/forecast/generation?asset_code=${asset}&horizon_hours=${h}`
    ),
  demand: (region = "tokyo", h = 48) =>
    getJson<ForecastResponse>(
      `/api/forecast/demand?region=${region}&horizon_hours=${h}`
    ),
  marketPrice: (market = "jepx_spot", h = 48) =>
    getJson<ForecastResponse>(
      `/api/forecast/market-price?market=${market}&horizon_hours=${h}`
    ),
  fuelPrice: (commodity = "lng", h = 48) =>
    getJson<ForecastResponse>(
      `/api/forecast/fuel-price?commodity=${commodity}&horizon_hours=${h}`
    ),
  risk: (asset = "solar_tokyo_1") =>
    getJson<RiskResponse>(`/api/risk?asset_code=${asset}`),
  revenue: (asset = "solar_tokyo_1", region = "tokyo") =>
    getJson<RevenueResponse>(
      `/api/simulate/revenue?asset_code=${asset}&region=${region}`
    ),
  brief: () => getJson<{ ai: { summary: string; insights: string[]; actions: string[] } }>(
    "/api/ai/brief"
  ),
  optimize: (asset = "solar_tokyo_1", h = 48) =>
    getJson<OptimizeResponse>(
      `/api/optimize/battery?asset_code=${asset}&horizon_hours=${h}`
    ),
  vpp: (region = "tokyo", h = 24) =>
    getJson<VppResponse>(`/api/vpp?region=${region}&horizon_hours=${h}`),
  dr: (region = "tokyo", h = 24) =>
    getJson<DrResponse>(`/api/dr?region=${region}&horizon_hours=${h}`),
  meta: () =>
    getJson<{
      regions: string[];
      assets: string[];
      commodities: string[];
      growth_themes: string[];
    }>("/api/meta"),
};
