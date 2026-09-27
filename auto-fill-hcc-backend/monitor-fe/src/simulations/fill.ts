// Output BE trả extension (T5) ở dạng dùng chung cho các mô phỏng form.

export interface UiField {
  name: string;
  comp?: string;
  value: unknown;
  default?: boolean;
  aliases?: string[];
  otherOf?: string;
}

export function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined || value === "") return true;
  if (typeof value === "object") return Object.values(value as Record<string, unknown>).every((v) => v === null || v === undefined || v === "");
  return false;
}

export function toFields(response: unknown): UiField[] {
  const fields = (response as { fields?: unknown } | null | undefined)?.fields;
  return Array.isArray(fields) ? (fields.filter((f) => f && typeof f === "object" && "name" in f) as UiField[]) : [];
}
