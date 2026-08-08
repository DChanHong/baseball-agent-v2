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

export function numberValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function booleanLabel(value: unknown, trueLabel: string, falseLabel: string): string {
  if (typeof value !== "boolean") {
    return "-";
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
