"use client";

import type { ToolResult } from "@/entities/tool-result/model/types";
import { BaseballKnowledgeCard } from "@/entities/tool-result/ui/cards/baseball-knowledge-card";
import { FindKboGameCard } from "@/entities/tool-result/ui/cards/find-kbo-game-card";
import { GenericToolCard } from "@/entities/tool-result/ui/cards/generic-tool-card";
import { SearchGuideCard } from "@/entities/tool-result/ui/cards/search-guide-card";
import { StadiumInfoCard } from "@/entities/tool-result/ui/cards/stadium-info-card";
import { WeatherContextCard } from "@/entities/tool-result/ui/cards/weather-context-card";

type ToolResultCardProps = {
  result: ToolResult;
};

export function ToolResultCard({ result }: ToolResultCardProps) {
  if (result.status === "failed") {
    return <GenericToolCard result={result} />;
  }

  switch (result.name) {
    case "find_kbo_game":
      return <FindKboGameCard result={result} />;
    case "get_stadium_info":
      return <StadiumInfoCard result={result} />;
    case "get_weather_context":
      return <WeatherContextCard result={result} />;
    case "search_stadium_guide":
    case "search_ticketing_guide":
      return <SearchGuideCard result={result} />;
    case "search_baseball_knowledge":
      return <BaseballKnowledgeCard result={result} />;
    default:
      return <GenericToolCard result={result} />;
  }
}
