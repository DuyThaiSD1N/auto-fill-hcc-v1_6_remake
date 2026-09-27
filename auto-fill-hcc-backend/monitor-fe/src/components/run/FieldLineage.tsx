import { DROP_REASONS } from "../../stages";
import type { RunDetail } from "../../types";
import { EmptyState } from "../Status";
import { fieldMap, parseMaybeJson, show } from "./model";

/** Dòng đời từng field: LLM trả → sau lọc → trả FE (sau mapper + chuẩn hoá ngày). */
export default function FieldLineage({ run }: { run: RunDetail }) {
  const steps = run.steps;
  if (!steps) return <EmptyState title="Lượt cũ chưa có dữ liệu từng tầng" />;
  const extract = [...(steps.llm ?? [])].reverse().find((c) => c.purpose === "extract");
  const parsed = parseMaybeJson(extract?.parsed) as { fields?: unknown } | undefined;
  const llm = fieldMap(parsed?.fields);
  const valid = fieldMap(parseMaybeJson(steps.outputs?.fields_after_validate));
  const final = fieldMap((steps.outputs?.response as { fields?: unknown } | undefined)?.fields);
  const dropped = new Map(
    (Array.isArray(steps.outputs?.validate_dropped) ? steps.outputs.validate_dropped as { name: string; reason: string }[] : [])
      .map((d) => [d.name, d.reason]),
  );
  const names = Array.from(new Set([...llm.keys(), ...valid.keys(), ...final.keys()]));
  if (!names.length) return <EmptyState title="Lượt này không có field" />;

  return (
    <div className="table-wrap">
      <table className="mini-table">
        <thead><tr><th>Field</th><th>LLM trả</th><th>Sau lọc</th><th>Trả FE</th><th>Ghi chú</th></tr></thead>
        <tbody>
          {names.map((name) => {
            const a = llm.get(name), b = valid.get(name), c = final.get(name);
            const changed = valid.has(name) && final.has(name) && show(b) !== show(c);
            const reason = dropped.get(name);
            const note = reason ? `bị loại: ${DROP_REASONS[reason] ?? reason}`
              : !llm.has(name) && final.has(name) ? "mapper thêm / đổi tên"
              : llm.has(name) && !final.has(name) ? "mapper bỏ / đổi tên"
              : changed ? "đổi sau lọc (mapper / chuẩn hoá ngày)" : "";
            return (
              <tr key={name} className={dropped.has(name) ? "dropped" : changed ? "changed" : undefined}>
                <td className="mono">{name}</td><td>{show(a)}</td><td>{show(b)}</td><td>{show(c)}</td><td>{note}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
