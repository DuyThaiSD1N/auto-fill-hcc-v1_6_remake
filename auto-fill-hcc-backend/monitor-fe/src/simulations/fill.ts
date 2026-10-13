// Output BE trả extension (T5) ở dạng dùng chung cho các mô phỏng form.

export interface UiField {
  name: string;
  comp?: string;
  value: unknown;
  default?: boolean;
  aliases?: string[];
  otherOf?: string;
  /** Biểu mẫu SurveyJS (Cổng DVC quốc gia mới): mã option, cờ tra cứu CSDL dân cư, radio của cụm địa chỉ. */
  code?: string;
  lookup?: boolean;
  radio?: string;
  /** Chỉ ghi khi ô còn trống — ô cổng đã đổ sẵn thì extension giữ nguyên. */
  onlyIfEmpty?: boolean;
}

export function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined || value === "") return true;
  if (typeof value === "object") return Object.values(value as Record<string, unknown>).every((v) => v === null || v === undefined || v === "");
  return false;
}

/** Output của biểu mẫu SurveyJS (Cổng DVC quốc gia mới): mapper gắn comp "sjs-*" (bản đầu 05/10: "sv-*"). Lượt cũ
 *  cùng mã thủ tục (trước khi chuyển cổng) mang comp của eForm moj → phải dựng bằng mẫu cũ. */
export function isSurveyJsOutput(fields: UiField[]): boolean {
  return fields.some((f) => /^(sjs|sv)-/.test(String(f.comp ?? "")));
}

export function toFields(response: unknown): UiField[] {
  const fields = (response as { fields?: unknown } | null | undefined)?.fields;
  return Array.isArray(fields) ? (fields.filter((f) => f && typeof f === "object" && "name" in f) as UiField[]) : [];
}
