"use client";

import { FileSearch, Ticket } from "lucide-react";
import type { ToolResult } from "@/entities/tool-result/model/types";
import {
  EvidenceItem,
  EvidenceList,
  EvidenceText,
  EvidenceTitle,
  Summary,
  ToolCardShell,
} from "@/entities/tool-result/ui/cards/tool-card-shell";
import {
  firstObjectItems,
  joinedStrings,
  objectValue,
  stringValue,
} from "@/entities/tool-result/ui/cards/tool-card-utils";

type Props = {
  result: ToolResult;
};

export function SearchGuideCard({ result }: Props) {
  const payload = objectValue(result.result);
  const items = firstObjectItems(payload?.items, 3);
  const isTicketing = result.name === "search_ticketing_guide";
  const title = isTicketing ? "예매 안내" : "구장 가이드";
  const Icon = isTicketing ? Ticket : FileSearch;

  return (
    <ToolCardShell icon={<Icon size={18} />} title={title} status={result.status}>
      <Summary>
        {stringValue(payload?.stadium_id, "구장")} 기준 문서 {items.length}건을 확인했습니다.
      </Summary>
      <EvidenceList>
        {items.map((item) => (
          <EvidenceItem key={stringValue(item.chunk_id, stringValue(item.document_id))}>
            <EvidenceTitle>{stringValue(item.title)}</EvidenceTitle>
            <EvidenceText>{stringValue(item.content)}</EvidenceText>
            <EvidenceText>{joinedStrings(item.source_urls)}</EvidenceText>
          </EvidenceItem>
        ))}
      </EvidenceList>
    </ToolCardShell>
  );
}
