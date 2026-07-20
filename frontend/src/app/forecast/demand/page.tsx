"use client";

import { useCallback } from "react";
import { ForecastPage } from "@/components/ForecastPage";
import { api } from "@/lib/api";

export default function DemandPage() {
  const loader = useCallback((key: string) => api.demand(key), []);
  return (
    <ForecastPage
      title="電力需要予測"
      subtitle="エリア別の需要カーブ。曜日・時間帯プロファイルを反映します。"
      loader={loader}
      options={[
        { value: "tokyo", label: "東京" },
        { value: "kansai", label: "関西" },
        { value: "chubu", label: "中部" },
        { value: "kyushu", label: "九州" },
      ]}
    />
  );
}
