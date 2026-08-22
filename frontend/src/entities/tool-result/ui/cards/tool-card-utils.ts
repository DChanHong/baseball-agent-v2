export function objectValue(value: unknown): Record<string, unknown> | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

export function arrayValue(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export function stringValue(value: unknown, fallback = "-"): string {
  if (typeof value === "string" && value.trim()) {
    return value;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return fallback;
}

export function displayValue(value: unknown, fallback = "정보 없음"): string {
  const stringified = stringValue(value, fallback).trim();
  return stringified === "-" ? fallback : stringified;
}

export function numberValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function booleanLabel(value: unknown, trueLabel: string, falseLabel: string): string {
  if (typeof value !== "boolean") {
    return "정보 없음";
  }

  return value ? trueLabel : falseLabel;
}

export function firstObjectItems(value: unknown, limit: number): Record<string, unknown>[] {
  return arrayValue(value).flatMap((item) => {
    const objectItem = objectValue(item);
    return objectItem ? [objectItem] : [];
  }).slice(0, limit);
}

export function joinedStrings(value: unknown, fallback = "-"): string {
  const strings = arrayValue(value).filter((item): item is string => typeof item === "string");
  return strings.length > 0 ? strings.join(", ") : fallback;
}

export function gameStatusLabel(value: unknown): string {
  const status = stringValue(value, "");

  const labels: Record<string, string> = {
    scheduled: "예정",
    live: "진행 중",
    final: "종료",
    cancelled: "취소",
    postponed: "연기",
    suspended: "일시 중단",
  };

  return labels[status] ?? displayValue(value);
}

export function formatGameDate(value: unknown): string {
  const date = stringValue(value, "");
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);

  if (!match) {
    return displayValue(value);
  }

  return `${Number(match[2])}월 ${Number(match[3])}일`;
}

export function formatGameTime(value: unknown): string {
  const time = stringValue(value, "");
  const match = /^(\d{2}):(\d{2})/.exec(time);

  if (!match) {
    return displayValue(value);
  }

  return `${match[1]}:${match[2]}`;
}
