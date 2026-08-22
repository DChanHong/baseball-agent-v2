"use client";

import { CloudSun } from "lucide-react";
import type { ToolResult } from "@/entities/tool-result/model/types";
import {
  DataGrid,
  DataItem,
  Label,
  Summary,
  ToolCardShell,
  Value,
} from "@/entities/tool-result/ui/cards/tool-card-shell";
import {
  displayValue,
  joinedStrings,
  numberValue,
  objectValue,
  stringValue,
} from "@/entities/tool-result/ui/cards/tool-card-utils";

type Props = {
  result: ToolResult;
};

const conditionLabel: Record<string, string> = {
  good: "좋음",
  caution: "주의",
  bad: "나쁨",
  unsupported: "미지원",
};

export function WeatherContextCard({ result }: Props) {
  const payload = objectValue(result.result);
  const weather = objectValue(payload?.weather);
  const visitCondition = objectValue(payload?.visit_condition);
  const source = objectValue(payload?.source);
  const level = stringValue(visitCondition?.level);
  const temperature = numberValue(weather?.temperature_c);
  const rainProbability = numberValue(weather?.precipitation_probability);

  return (
    <ToolCardShell
      icon={<CloudSun size={18} />}
      title="구장 날씨"
      status={result.status}
      meta={source ? `출처 ${stringValue(source.provider)} · ${stringValue(source.api)}` : undefined}
    >
      <Summary>
        {stringValue(payload?.stadium_name, stringValue(payload?.stadium_id, "구장"))} 기준 직관
        컨디션은 {conditionLabel[level] ?? level} 수준입니다.
      </Summary>
      <DataGrid>
        <DataItem>
          <Label>기온</Label>
          <Value>{temperature === null ? "정보 없음" : `${temperature}°C`}</Value>
        </DataItem>
        <DataItem>
          <Label>강수 확률</Label>
          <Value>{rainProbability === null ? "정보 없음" : `${rainProbability}%`}</Value>
        </DataItem>
        <DataItem>
          <Label>강수량</Label>
          <Value>
            {weather?.precipitation_mm === null || weather?.precipitation_mm === undefined
              ? "정보 없음"
              : `${displayValue(weather.precipitation_mm)}mm`}
          </Value>
        </DataItem>
        <DataItem>
          <Label>습도</Label>
          <Value>
            {weather?.humidity_percent === null || weather?.humidity_percent === undefined
              ? "정보 없음"
              : `${displayValue(weather.humidity_percent)}%`}
          </Value>
        </DataItem>
      </DataGrid>
      <Summary>{joinedStrings(visitCondition?.tips, "준비 팁은 추가 확인이 필요합니다.")}</Summary>
    </ToolCardShell>
  );
}
