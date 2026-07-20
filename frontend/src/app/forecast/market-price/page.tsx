"use client";

import { useCallback } from "react";
import { ForecastPage } from "@/components/ForecastPage";
import { api } from "@/lib/api";

export default function MarketPricePage() {
  const loader = useCallback((key: string) => api.marketPrice(key), []);
  return (
    <ForecastPage
      title="市場価格予測"
      subtitle="JEPX スポット価格の時間前予測（JPY/kWh）。夕方ピークをモデル化しています。"
      loader={loader}
      options={[{ value: "jepx_spot", label: "JEPX Spot" }]}
    />
  );
}
