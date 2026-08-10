"use client";

import { CircleAlert, LoaderCircle } from "lucide-react";
import type { ToolResult, ToolResultName } from "@/entities/tool-result/model/types";
import {
  LoadingDots,
  Summary,
  ToolCardShell,
} from "@/entities/tool-result/ui/cards/tool-card-shell";

type Props = {
  result: ToolResult;
};

const toolLabels: Record<ToolResultName, string> = {
  find_kbo_game: "경기 일정",
  get_stadium_info: "구장 정보",
  get_weather_context: "구장 날씨",
  search_stadium_guide: "구장 가이드",
  search_ticketing_guide: "예매 안내",
  search_baseball_knowledge: "야구 지식",
};

export function GenericToolCard({ result }: Props) {
  const title = toolLabels[result.name];
  const Icon = result.status === "failed" ? CircleAlert : LoaderCircle;

  return (
    <ToolCardShell icon={<Icon size={18} />} title={title} status={result.status}>
      {result.status === "running" ? (
        <Summary>
          필요한 정보를 확인하고 있습니다.
          <LoadingDots aria-hidden="true">
            <span />
            <span />
            <span />
          </LoadingDots>
        </Summary>
      ) : (
        <Summary>지금은 이 정보를 확인하지 못했습니다. 잠시 후 다시 시도해주세요.</Summary>
      )}
    </ToolCardShell>
  );
}
