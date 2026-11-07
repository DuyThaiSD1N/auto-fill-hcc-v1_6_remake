import { safeJson } from "../../format";

/** ``verbatim``: in chuỗi đúng nguyên văn (output LLM thô) — không parse/format lại. */
export default function Json({ value, tall = false, empty = "Không có dữ liệu", verbatim = false }: {
  value: unknown; tall?: boolean; empty?: string; verbatim?: boolean;
}) {
  const text = verbatim && typeof value === "string" ? value : safeJson(value);
  if (!text) return <p className="faint">{empty}</p>;
  return <pre className={`code${tall ? " code--tall" : ""}`}>{text}</pre>;
}
