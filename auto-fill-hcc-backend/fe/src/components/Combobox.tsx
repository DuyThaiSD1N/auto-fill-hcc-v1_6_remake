import { useEffect, useMemo, useRef, useState } from "react";

export interface ComboOption {
  value: string;
  label: string;
}

// Bỏ dấu tiếng Việt để tìm không phân biệt dấu ("ket hon" khớp "kết hôn").
function fold(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}

// Combobox lọc-khi-gõ dùng cho filter nhiều lựa chọn tên dài (thủ tục/phường). Bề rộng CỐ ĐỊNH
// nên không phình theo option như <select> gốc. Vanilla, không thêm thư viện.
export default function Combobox({
  label,
  value,
  options,
  onChange,
  allLabel = "Tất cả",
  placeholder = "Tìm…",
  disabled = false,
}: {
  label: string;
  value: string;
  options: ComboOption[];
  onChange: (v: string) => void;
  allLabel?: string;
  placeholder?: string;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedLabel = value
    ? options.find((o) => o.value === value)?.label ?? value
    : allLabel;

  // Hàng "Tất cả" (value="") luôn đứng đầu để xóa lọc nhanh; phía dưới là option khớp query.
  const rows = useMemo(() => {
    const q = fold(query.trim());
    const matched = q ? options.filter((o) => fold(o.label).includes(q)) : options;
    return [{ value: "", label: allLabel }, ...matched];
  }, [query, options, allLabel]);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setActive(0);
    inputRef.current?.focus();
    function onDocClick(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  useEffect(() => {
    if (disabled) setOpen(false);
  }, [disabled]);

  // Đang gõ → tô sáng KẾT QUẢ KHỚP đầu tiên (bỏ qua hàng "Tất cả") để Enter chọn đúng thủ tục.
  useEffect(() => {
    setActive(query.trim() && rows.length > 1 ? 1 : 0);
  }, [query, rows.length]);

  function choose(o: ComboOption) {
    onChange(o.value);
    setOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, rows.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (rows[active]) choose(rows[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className="combobox" ref={rootRef}>
      <span className="combobox-label">{label}</span>
      <button
        type="button"
        className={`combobox-control${value ? "" : " placeholder"}`}
        onClick={() => setOpen((o) => !o)}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="combobox-value">{selectedLabel}</span>
        <svg className="combobox-caret" viewBox="0 0 20 20" width="16" height="16" aria-hidden="true">
          <path d="M5 8l5 5 5-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div className="combobox-panel">
          <input
            ref={inputRef}
            className="combobox-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={placeholder}
          />
          <ul className="combobox-list" role="listbox">
            {rows.map((o, i) => (
              <li
                key={o.value || "__all__"}
                role="option"
                aria-selected={o.value === value}
                className={`combobox-option${i === active ? " active" : ""}${
                  o.value === value ? " selected" : ""
                }`}
                onMouseEnter={() => setActive(i)}
                onMouseDown={(e) => {
                  e.preventDefault(); // giữ focus, tránh blur đóng panel trước khi chọn
                  choose(o);
                }}
              >
                {o.value === "" ? <span className="muted">{o.label}</span> : o.label}
              </li>
            ))}
            {rows.length === 1 && <li className="combobox-empty">Không tìm thấy</li>}
          </ul>
        </div>
      )}
    </div>
  );
}
