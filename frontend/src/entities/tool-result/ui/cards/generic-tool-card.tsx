"use client";

import { Wrench } from "lucide-react";
import type { ToolResult } from "@/entities/tool-result/model/types";
import { Summary, ToolCardShell } from "@/entities/tool-result/ui/cards/tool-card-shell";

type Props = {
  result: ToolResult;
};

export function GenericToolCard({ result }: Props) {
  const errorMessage = result.error?.message;

  return (
    <ToolCardShell icon={<Wrench size={18} />} title={result.name} status={result.status}>
      <Summary>{errorMessage ?? "도구 결과를 확인했습니다."}</Summary>
    </ToolCardShell>
  );
}
