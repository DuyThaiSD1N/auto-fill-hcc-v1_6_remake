import { useEffect, useId, useMemo, useRef, useState } from "react";

import type { ScopeUnit } from "./api";

// Tỉnh có hơn trăm đơn vị: thả cả danh sách là cuộn mỏi tay và dễ bấm nhầm. Chỉ hiện vài kết quả
// khớp nhất, phần còn lại gõ để thu hẹp.
const MAX_RESULTS = 8;

function fold(value: string): string {
  return value
    .replace(/Đ/g, "D")
    .replace(/đ/g, "d")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim();
}

function unitLabel(unit: ScopeUnit): string {
  return unit.name || unit.xa || unit.unitId;
}

interface Props {
  units: ScopeUnit[];
  value: string; // "all" hoặc unitId
  allLabel: string;
  onChange: (value: string) => void;
}

export default function UnitPicker({ units, value, allLabel, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listId = useId();

  const selected = value === "all" ? null : units.find((u) => u.unitId === value) || null;

  const { shown, more } = useMemo(() => {
    const needle = fold(query);
    const matches = needle
      ? units.filter((u) => fold(`${u.name || ""} ${u.xa || ""}`).includes(needle))
      : units;
    return { shown: matches.slice(0, MAX_RESULTS), more: Math.max(0, matches.length - MAX_RESULTS) };
  }, [units, query]);

  // Hàng 0 = "Tất cả đơn vị" (chỉ hiện khi chưa gõ), sau đó là các đơn vị khớp.
  const showAll = !query.trim();
  const rows: { id: string; label: string; meta?: string }[] = [
    ...(showAll ? [{ id: "all", label: allLabel }] : []),
    ...shown.map((u) => ({
      id: u.unitId,
      label: unitLabel(u),
      meta: u.name && u.xa && fold(u.name) !== fold(u.xa) ? u.xa : undefined,
    })),
  ];

  useEffect(() => {
    if (!open) return;
    setActive(0);
    inputRef.current?.focus();
    const onDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  useEffect(() => setActive(0), [query]);

  function choose(id: string) {
    onChange(id);
    setOpen(false);
    setQuery("");
  }

  function onKeyDown(event: React.KeyboardEvent) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((i) => Math.min(i + 1, rows.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (rows[active]) choose(rows[active].id);
    } else if (event.key === "Escape") {
      setOpen(false);
      setQuery("");
    }
  }

  return (
    <div className="upk" ref={rootRef}>
      <button
        type="button"
        className="ctl upk-btn"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="upk-val">{selected ? unitLabel(selected) : allLabel}</span>
      </button>
      {open && (
        <div className="upk-pop">
          <input
            ref={inputRef}
            className="ctl upk-search"
            type="search"
            placeholder="Gõ tên đơn vị hoặc xã/phường…"
            value={query}
            role="combobox"
            aria-expanded="true"
            aria-controls={listId}
            aria-activedescendant={rows[active] ? `${listId}-${active}` : undefined}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <ul className="upk-list" id={listId} role="listbox">
            {rows.map((row, index) => (
              <li
                key={row.id}
                id={`${listId}-${index}`}
                role="option"
                aria-selected={row.id === value}
                className={`${index === active ? "on" : ""}${row.id === value ? " cur" : ""}`}
                onMouseEnter={() => setActive(index)}
                onMouseDown={(e) => {
                  e.preventDefault();
                  choose(row.id);
                }}
              >
                <span>{row.label}</span>
                {row.meta && <small>{row.meta}</small>}
              </li>
            ))}
            {rows.length === 0 && <li className="upk-empty">Không có đơn vị nào khớp</li>}
          </ul>
          {more > 0 && (
            <div className="upk-more">Còn {more} đơn vị khác — gõ thêm để thu hẹp</div>
          )}
        </div>
      )}
    </div>
  );
}
