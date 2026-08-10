"use client";

import { CalendarDays } from "lucide-react";
import type { ToolResult } from "@/entities/tool-result/model/types";
import {
  DataGrid,
  DataItem,
  Label,
  Summary,
  ToolCardShell,
  Value,
} from "@/entities/tool-result/ui/cards/tool-card-shell";
import { firstObjectItems, objectValue, stringValue } from "@/entities/tool-result/ui/cards/tool-card-utils";

type Props = {
  result: ToolResult;
};

export function FindKboGameCard({ result }: Props) {
  const payload = objectValue(result.result);
  const games = firstObjectItems(payload?.games, 2);
  const total = stringValue(payload?.total, "0");

  return (
    <ToolCardShell icon={<CalendarDays size={18} />} title="경기 일정" status={result.status}>
      <Summary>조건에 맞는 경기 {total}건을 찾았습니다.</Summary>
      {games.map((game) => (
        <DataGrid key={stringValue(game.internal_game_key, stringValue(game.id))}>
          <DataItem>
            <Label>경기</Label>
            <Value>
              {stringValue(game.away_team_name)} vs {stringValue(game.home_team_name)}
            </Value>
          </DataItem>
          <DataItem>
            <Label>구장</Label>
            <Value>{stringValue(game.stadium_name)}</Value>
          </DataItem>
          <DataItem>
            <Label>날짜</Label>
            <Value>{stringValue(game.game_date)}</Value>
          </DataItem>
          <DataItem>
            <Label>상태</Label>
            <Value>{stringValue(game.game_status)}</Value>
          </DataItem>
        </DataGrid>
      ))}
    </ToolCardShell>
  );
}
