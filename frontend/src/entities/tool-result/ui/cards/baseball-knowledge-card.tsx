"use client";

import { BookOpenText } from "lucide-react";
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

export function BaseballKnowledgeCard({ result }: Props) {
  const payload = objectValue(result.result);
  const items = firstObjectItems(payload?.items, 3);

  return (
    <ToolCardShell icon={<BookOpenText size={18} />} title="야구 지식" status={result.status}>
      <Summary>{stringValue(payload?.query, "질문")} 관련 근거를 확인했습니다.</Summary>
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
