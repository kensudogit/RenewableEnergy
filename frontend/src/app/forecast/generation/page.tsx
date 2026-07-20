"use client";

import { useCallback } from "react";
import { ForecastPage } from "@/components/ForecastPage";
import { api } from "@/lib/api";

export default function GenerationPage() {
  const loader = useCallback((key: string) => api.generation(key), []);
  return (
    <ForecastPage
      title="発電量予測"
      subtitle="太陽光・風力などアセット別の出力予測（MW）。天候ノイズを含む合成データでデモします。"
      loader={loader}
      options={[
        { value: "solar_tokyo_1", label: "東京ソーラー1号" },
        { value: "wind_kyushu_1", label: "九州ウィンド1号" },
        { value: "battery_tokyo_1", label: "東京蓄電池1号" },
      ]}
    />
  );
}
