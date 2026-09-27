import { groupOf } from "../../stages";
import type { LlmCall, SpanDoc, StepsDoc } from "../../types";

export interface FlatSpan extends SpanDoc { depth: number; ownMs: number; hasChildren: boolean }

/** Cây span → danh sách phẳng theo thứ tự thời gian, giữ độ sâu để thụt lề. */
export function flattenSpans(spans: SpanDoc[]): FlatSpan[] {
  const byParent = new Map<number | null, SpanDoc[]>();
  const ids = new Set(spans.map((s) => s.i));
  for (const s of spans) {
    const parent = s.p !== null && ids.has(s.p) ? s.p : null;
    const list = byParent.get(parent) ?? [];
    list.push(s);
    byParent.set(parent, list);
  }
  for (const list of byParent.values()) list.sort((a, b) => a.t0 - b.t0 || a.i - b.i);
  const out: FlatSpan[] = [];
  const walk = (parent: number | null, depth: number) => {
    for (const s of byParent.get(parent) ?? []) {
      const kids = byParent.get(s.i) ?? [];
      out.push({ ...s, depth, ownMs: ownTime(s, kids), hasChildren: kids.length > 0 });
      walk(s.i, depth + 1);
    }
  };
  walk(null, 0);
  return out;
}

/** Thời gian riêng = span trừ phần các span con phủ (con chạy song song chỉ trừ một lần). */
function ownTime(s: SpanDoc, kids: SpanDoc[]): number {
  const ivs = kids.map((k) => [Math.max(k.t0, s.t0), Math.min(k.t0 + k.ms, s.t0 + s.ms)] as [number, number])
    .filter(([a, b]) => b > a).sort((x, y) => x[0] - y[0]);
  let covered = 0, end = -Infinity;
  for (const [a, b] of ivs) {
    if (b <= end) continue;
    covered += b - Math.max(a, end);
    end = b;
  }
  return Math.max(0, s.ms - covered);
}

export function barClass(name: string): string {
  const g = groupOf(name);
  return g ? `st-${g}` : "";
}

export function callForSpan(steps: StepsDoc | null, span: SpanDoc): LlmCall | undefined {
  if (!steps) return undefined;
  const byId = steps.llm.find((c) => c.span === span.i);
  if (byId) return byId;
  const n = typeof span.a?.n === "number" ? span.a.n : null;
  return n ? steps.llm.find((c) => c.n === n) : undefined;
}

/** Bước đáng xem nhất khi mở: bước lá tốn thời gian nhất (thường là một lần gọi LLM). */
export function defaultSpan(flat: FlatSpan[]): number | null {
  const leaves = flat.filter((s) => !flat.some((c) => c.p === s.i) && s.n !== "pre.request");
  const pick = leaves.sort((a, b) => b.ms - a.ms)[0] ?? flat[0];
  return pick ? pick.i : null;
}

/** Field dạng {name: value} hoặc [{name, value}] → Map. */
export function fieldMap(value: unknown): Map<string, unknown> {
  const out = new Map<string, unknown>();
  if (Array.isArray(value)) {
    for (const f of value) if (f && typeof f === "object" && "name" in f) out.set(String((f as { name: unknown }).name), (f as { value?: unknown }).value);
  } else if (value && typeof value === "object") {
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) out.set(k, v);
  }
  return out;
}

export function parseMaybeJson(value: unknown): unknown {
  if (typeof value !== "string") return value;
  try { return JSON.parse(value); } catch { return value; }
}

export function show(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string") return value;
  try { return JSON.stringify(value); } catch { return String(value); }
}
