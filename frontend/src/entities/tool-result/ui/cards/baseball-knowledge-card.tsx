"use client";

import { BookOpenText } from "lucide-react";
import type { ToolResult } from "@/entities/tool-result/model/types";
import {
  EvidenceItem,
  EvidenceList,
  EvidenceMeta,
  EvidenceText,
  EvidenceTitle,
  Summary,
  ToolCardShell,
} from "@/entities/tool-result/ui/cards/tool-card-shell";
import { SourceDisclosure } from "@/entities/tool-result/ui/cards/source-disclosure";
import {
  arrayValue,
  displayValue,
  firstObjectItems,
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
          <KnowledgeEvidenceItem key={stringValue(item.chunk_id, stringValue(item.document_id))} item={item} />
        ))}
      </EvidenceList>
    </ToolCardShell>
  );
}

type KnowledgeEvidenceItemProps = {
  item: Record<string, unknown>;
};

function KnowledgeEvidenceItem({ item }: KnowledgeEvidenceItemProps) {
  const sources = arrayValue(item.source_urls).filter(
    (source): source is string => typeof source === "string" && Boolean(source.trim()),
  );

  return (
    <EvidenceItem>
      <EvidenceTitle>{displayValue(item.title, "야구 지식")}</EvidenceTitle>
      <EvidenceText>{formatKnowledgeContent(item.content)}</EvidenceText>
      {sources.length > 0 ? (
        <EvidenceMeta>
          <SourceDisclosure sources={sources} />
        </EvidenceMeta>
      ) : null}
    </EvidenceItem>
  );
}

function formatKnowledgeContent(value: unknown): string {
  const content = displayValue(value);
  const summaryMatch = /요약:\s*([\s\S]*?)(?:\s*출처\s*발췌:|$)/.exec(content);

  if (summaryMatch?.[1]?.trim()) {
    return summaryMatch[1].replace(/\s+/g, " ").trim();
  }

  return content.replace(/\s*출처\s*발췌:\s*/g, "\n").replace(/\s+/g, " ").trim();
}
