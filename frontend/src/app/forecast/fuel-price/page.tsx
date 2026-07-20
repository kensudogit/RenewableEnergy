"use client";

import { useCallback } from "react";
import { ForecastPage } from "@/components/ForecastPage";
import { api } from "@/lib/api";

export default function FuelPricePage() {
  const loader = useCallback((key: string) => api.fuelPrice(key), []);
  return (
    <ForecastPage
      title="燃料価格予測"
      subtitle="LNG / 石炭 / 原油の価格パス。火力限界費用と市場連動の前提になります。"
      loader={loader}
      options={[
        { value: "lng", label: "LNG" },
        { value: "coal", label: "石炭" },
        { value: "oil", label: "原油" },
      ]}
    />
  );
}
