"use client";

import { MapPinned } from "lucide-react";
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
  booleanLabel,
  displayValue,
  joinedStrings,
  objectValue,
  stringValue,
} from "@/entities/tool-result/ui/cards/tool-card-utils";

type Props = {
  result: ToolResult;
};

export function StadiumInfoCard({ result }: Props) {
  const payload = objectValue(result.result);
  const stadium = objectValue(payload?.stadium);

  if (!stadium) {
    return (
      <ToolCardShell icon={<MapPinned size={18} />} title="구장 정보" status={result.status}>
        <Summary>구장 정보를 찾지 못했습니다.</Summary>
      </ToolCardShell>
    );
  }

  return (
    <ToolCardShell icon={<MapPinned size={18} />} title="구장 정보" status={result.status}>
      <Highlight>
        <HighlightTitle>{displayValue(stadium.name_ko, "구장 정보")}</HighlightTitle>
        <HighlightMeta>
          {displayValue(stadium.city)} · {booleanLabel(stadium.is_dome, "돔구장", "야외 구장")}
        </HighlightMeta>
      </Highlight>
      <Summary>
        주소와 홈팀 등 기본 정보를 확인했습니다. 비어 있는 항목은 아직 데이터 보강이 필요합니다.
      </Summary>
      <DataGrid>
        <DataItem>
          <Label>주소</Label>
          <Value>{displayValue(stadium.address)}</Value>
        </DataItem>
        <DataItem>
          <Label>돔 여부</Label>
          <Value>{booleanLabel(stadium.is_dome, "돔구장", "야외 구장")}</Value>
        </DataItem>
        <DataItem>
          <Label>홈팀</Label>
          <Value>{joinedStrings(stadium.home_team_ids, "정보 없음")}</Value>
        </DataItem>
        <DataItem>
          <Label>지역</Label>
          <Value>
            {displayValue(stadium.city)} {stringValue(stadium.region, "")}
          </Value>
        </DataItem>
      </DataGrid>
    </ToolCardShell>
  );
}
