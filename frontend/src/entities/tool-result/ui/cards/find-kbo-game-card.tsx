"use client";

import { CalendarDays } from "lucide-react";
import styled from "styled-components";
import type { ToolResult } from "@/entities/tool-result/model/types";
import {
  DataGrid,
  DataItem,
  Highlight,
  HighlightMeta,
  HighlightTitle,
  Label,
  Summary,
  ToolCardShell,
  Value,
} from "@/entities/tool-result/ui/cards/tool-card-shell";
import {
  displayValue,
  firstObjectItems,
  formatGameDate,
  formatGameTime,
  gameStatusLabel,
  objectValue,
  stringValue,
} from "@/entities/tool-result/ui/cards/tool-card-utils";

type Props = {
  result: ToolResult;
};

export function FindKboGameCard({ result }: Props) {
  const payload = objectValue(result.result);
  const games = firstObjectItems(payload?.games);
  const total = stringValue(payload?.total, "0");

  return (
    <ToolCardShell icon={<CalendarDays size={18} />} title="경기 일정" status={result.status}>
      <Summary>{Number(total) > 0 ? `조건에 맞는 경기 ${total}건입니다.` : "조건에 맞는 경기가 없습니다."}</Summary>
      {games.map((game, index) => (
        <GameBlock key={`${stringValue(game.internal_game_key, stringValue(game.id))}_${index}`}>
          <Highlight>
            <HighlightTitle>
              {displayValue(game.away_team_name)} vs {displayValue(game.home_team_name)}
            </HighlightTitle>
            <HighlightMeta>
              {formatGameDate(game.game_date)} · {formatGameTime(game.start_time)} ·{" "}
              {displayValue(game.stadium_name)}
            </HighlightMeta>
          </Highlight>
          <DataGrid>
            <DataItem>
              <Label>구장</Label>
              <Value>{displayValue(game.stadium_name)}</Value>
            </DataItem>
            <DataItem>
              <Label>상태</Label>
              <Value>{gameStatusLabel(game.game_status)}</Value>
            </DataItem>
            <DataItem>
              <Label>원정</Label>
              <Value>{displayValue(game.away_team_name)}</Value>
            </DataItem>
            <DataItem>
              <Label>홈</Label>
              <Value>{displayValue(game.home_team_name)}</Value>
            </DataItem>
          </DataGrid>
        </GameBlock>
      ))}
    </ToolCardShell>
  );
}

const GameBlock = styled.div`
  display: grid;
  gap: 10px;
`;
