import { useEffect, useId, useMemo, useRef, useState } from "react";
import Icon from "./Icon";

export interface ComboOption {
  value: string;
  label: string;
  /** Chữ phụ (mã, tài khoản) — hiện mờ bên phải, cũng tìm được. */
  hint?: string;
}

const fold = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/gi, "d").toLowerCase();

// Danh sách dài (hàng trăm đơn vị / thủ tục) → chỉ dựng một phần, gõ để thu hẹp.
const MAX_RENDER = 200;

/** Ô chọn có tìm kiếm: danh sách thấp (~8 dòng) và cuộn, không bung hết một lượt như <select>. */
export default function ComboSelect({ label, value, options, allLabel, onChange, width = 240 }: {
  label: string;
  value: string;
  options: ComboOption[];
  /** Nhãn của lựa chọn rỗng (bỏ lọc), vd "Tất cả đơn vị". */
  allLabel: string;
  onChange: (value: string) => void;
  width?: number;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const id = useId();

  const current = options.find((o) => o.value === value);
  const items = useMemo(() => {
    const needle = fold(q.trim());
    const hits = needle ? options.filter((o) => fold(`${o.label} ${o.hint ?? ""}`).includes(needle)) : options;
    return [{ value: "", label: allLabel }, ...hits];
  }, [options, q, allLabel]);
  const shown = items.slice(0, MAX_RENDER + 1);

  useEffect(() => {
    if (!open) return undefined;
    const away = (e: MouseEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    setQ("");
    const i = Math.max(0, items.findIndex((o) => o.value === value));
    setActive(i);
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    list.current?.querySelector<HTMLElement>(`[data-i="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [active, open]);

  const pick = (v: string) => {
    onChange(v);
    setOpen(false);
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, shown.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); if (shown[active]) pick(shown[active].value); }
    else if (e.key === "Escape") { e.preventDefault(); setOpen(false); }
  };

  return (
    <div className="filter combo" ref={root}>
      <span>{label}</span>
      <button
        type="button"
        className={`select combo__btn${value ? " is-set" : ""}`}
        style={{ width }}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        title={current?.label ?? allLabel}
      >
        <span className="combo__value">{current?.label ?? (value || allLabel)}</span>
        <Icon name="chevron-right" size={14} />
      </button>
      {open ? (
        <div className="combo__pop" style={{ width: Math.max(width, 300) }}>
          <label className="combo__search">
            <Icon name="search" size={14} />
            <input
              autoFocus
              role="combobox"
              aria-expanded
              aria-controls={`${id}-list`}
              aria-activedescendant={`${id}-${active}`}
              aria-label={`Tìm ${label.toLowerCase()}`}
              placeholder={`Tìm ${label.toLowerCase()}…`}
              value={q}
              onChange={(e) => { setQ(e.target.value); setActive(0); }}
              onKeyDown={onKey}
            />
          </label>
          <ul className="combo__list" role="listbox" id={`${id}-list`} ref={list} aria-label={label}>
            {shown.map((o, i) => (
              <li
                key={o.value || "__all"}
                id={`${id}-${i}`}
                data-i={i}
                role="option"
                aria-selected={o.value === value}
                className={`combo__opt${i === active ? " is-active" : ""}${o.value ? "" : " combo__opt--all"}`}
                onMouseEnter={() => setActive(i)}
                onMouseDown={(e) => { e.preventDefault(); pick(o.value); }}
              >
                <span className="combo__label">{o.label}</span>
                {o.hint ? <span className="combo__hint">{o.hint}</span> : null}
                {o.value === value ? <Icon name="check" size={14} /> : null}
              </li>
            ))}
            {items.length === 1 ? <li className="combo__empty">Không có kết quả</li> : null}
            {items.length > shown.length ? <li className="combo__empty">… còn {items.length - shown.length} mục, gõ để thu hẹp</li> : null}
          </ul>
          <div className="combo__foot">{(items.length - 1).toLocaleString("vi-VN")} / {options.length.toLocaleString("vi-VN")} mục</div>
        </div>
      ) : null}
    </div>
  );
}
