"use client";

import { FileSearch, Ticket } from "lucide-react";
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
          <GuideEvidenceItem key={stringValue(item.chunk_id, stringValue(item.document_id))} item={item} />
        ))}
      </EvidenceList>
    </ToolCardShell>
  );
}

type GuideEvidenceItemProps = {
  item: Record<string, unknown>;
};

function GuideEvidenceItem({ item }: GuideEvidenceItemProps) {
  const sources = arrayValue(item.source_urls).filter(
    (source): source is string => typeof source === "string" && Boolean(source.trim()),
  );

  return (
    <EvidenceItem>
      <EvidenceTitle>{displayValue(item.title, "관련 안내")}</EvidenceTitle>
      <EvidenceText>{displayValue(item.content)}</EvidenceText>
      {sources.length > 0 ? (
        <EvidenceMeta>
          <SourceDisclosure sources={sources} />
        </EvidenceMeta>
      ) : null}
    </EvidenceItem>
  );
}
