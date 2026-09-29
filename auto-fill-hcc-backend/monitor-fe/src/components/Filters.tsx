import { useEffect, useMemo, useState } from "react";
import { buildQuery, navigate, useLocation } from "../router";
import { isoDay } from "../format";
import { useFacets } from "../hooks";
import ComboSelect from "./ComboSelect";
import Icon from "./Icon";

/** Bộ lọc nằm trên URL: đọc từ query, ghi bằng replaceState (Back vẫn về trang trước đó). */
export function useQueryFilters<T extends Record<string, string>>(defaults: T) {
  const loc = useLocation();
  const values = { ...defaults } as T;
  for (const key of Object.keys(defaults)) {
    const v = loc.query.get(key);
    if (v !== null) (values as Record<string, string>)[key] = v;
  }
  const set = (patch: Partial<T>, { keepPage = false } = {}) => {
    const next: Record<string, string> = { ...values, ...patch } as Record<string, string>;
    if (!keepPage && !("page" in patch)) next.page = "1";
    // Giá trị bằng mặc định không ghi lên URL để link gọn.
    const clean: Record<string, string> = {};
    for (const [k, v] of Object.entries(next)) if (v !== (defaults as Record<string, string>)[k]) clean[k] = v;
    navigate(`${loc.path}${buildQuery(clean)}`, { replace: true });
  };
  const reset = () => navigate(loc.path, { replace: true });
  return { values, set, reset };
}

/** Khoảng ngày giờ VN → dateFrom/dateTo cho API. */
export function rangeToDates(range: string, from: string, to: string): { dateFrom?: string; dateTo?: string } {
  if (range === "today") return { dateFrom: isoDay(0), dateTo: isoDay(0) };
  if (range === "7d") return { dateFrom: isoDay(6), dateTo: isoDay(0) };
  if (range === "30d") return { dateFrom: isoDay(29), dateTo: isoDay(0) };
  if (range === "custom") return { dateFrom: from || undefined, dateTo: to || undefined };
  return {};
}

export function Segmented<V extends string>({
  label, value, options, onChange,
}: { label: string; value: V; options: { value: V; label: string }[]; onChange: (v: V) => void }) {
  return (
    <div className="filter" role="group" aria-label={label}>
      <span>{label}</span>
      <div className="seg">
        {options.map((o) => (
          <button key={o.value} type="button" aria-pressed={value === o.value} onClick={() => onChange(o.value)}>
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function DateRange({ range, from, to, onChange }: {
  range: string; from: string; to: string;
  onChange: (patch: { range?: string; from?: string; to?: string }) => void;
}) {
  return (
    <>
      <Segmented
        label="Thời gian"
        value={range}
        options={[
          { value: "today", label: "Hôm nay" },
          { value: "7d", label: "7 ngày" },
          { value: "30d", label: "30 ngày" },
          { value: "all", label: "Tất cả" },
          { value: "custom", label: "Tuỳ chọn" },
        ]}
        onChange={(v) => onChange({ range: v })}
      />
      {range === "custom" ? (
        <div className="filter">
          <input aria-label="Từ ngày" className="input" type="date" value={from} onChange={(e) => onChange({ from: e.target.value })} />
          <span>→</span>
          <input aria-label="Đến ngày" className="input" type="date" value={to} onChange={(e) => onChange({ to: e.target.value })} />
        </div>
      ) : null}
    </>
  );
}

export function UnitSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { facets } = useFacets();
  const options = useMemo(() => (facets?.users ?? []).map((u) => ({
    value: u.userId,
    label: u.name || u.username || u.userId,
    hint: u.name && u.username ? u.username : undefined,
  })), [facets]);
  return <ComboSelect label="Đơn vị" value={value} options={options} allLabel="Tất cả đơn vị" onChange={onChange} width={220} />;
}

export function ProcedureSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { facets } = useFacets();
  const options = useMemo(() => (facets?.procedures ?? []).map((p) => ({
    value: p.key,
    label: p.label || p.key,
    hint: p.label ? p.key : undefined,
  })), [facets]);
  return <ComboSelect label="Thủ tục" value={value} options={options} allLabel="Tất cả thủ tục" onChange={onChange} width={260} />;
}

/** Ô tìm: gõ xong 350 ms mới lọc (không gọi API mỗi phím). */
export function SearchInput({ value, onChange, placeholder }: {
  value: string; onChange: (v: string) => void; placeholder: string;
}) {
  const [text, setText] = useState(value);
  useEffect(() => setText(value), [value]);
  useEffect(() => {
    if (text === value) return undefined;
    const t = window.setTimeout(() => onChange(text.trim()), 350);
    return () => window.clearTimeout(t);
  }, [text]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <label className="filter filters__search">
      <span className="sr-only">Tìm</span>
      <input className="input" type="search" value={text} placeholder={placeholder} onChange={(e) => setText(e.target.value)} />
    </label>
  );
}

export function ResetButton({ onClick }: { onClick: () => void }) {
  return <button className="btn btn--ghost btn--sm filters__reset" type="button" onClick={onClick}><Icon name="x" size={14} /> Xoá lọc</button>;
}

export function Pager({ page, pageSize, total, onPage }: {
  page: number; pageSize: number; total: number; onPage: (p: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (total <= pageSize) return null;
  return (
    <nav className="pager" aria-label="Phân trang">
      <button className="btn btn--sm" type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        <Icon name="chevron-left" size={14} /> Trước
      </button>
      <span className="num">Trang {page.toLocaleString("vi-VN")} / {pages.toLocaleString("vi-VN")}</span>
      <button className="btn btn--sm" type="button" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        Sau <Icon name="chevron-right" size={14} />
      </button>
    </nav>
  );
}
