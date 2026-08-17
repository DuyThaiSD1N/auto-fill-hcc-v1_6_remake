import { useEffect, useRef, useState } from "react";

// Combobox tìm kiếm cho danh sách dài (34 tỉnh / cả trăm xã): gõ để lọc (không dấu vẫn
// khớp), danh sách cao ~6 dòng cuộn được — select trần sổ full rất dài và vướng mắt.
const fold = (s: string) =>
  s.replace(/Đ/g, "D").replace(/đ/g, "d").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

interface Props {
  value: string;
  options: string[];
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export default function SearchSelect({ value, options, onChange, placeholder, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const q = fold(query).trim();
  const filtered = q ? options.filter((o) => fold(o).includes(q)) : options;

  function pick(o: string) {
    onChange(o);
    setOpen(false);
    setQuery("");
  }

  return (
    <div className="sselect" ref={ref}>
      <input
        // Mở = ô đang là bộ lọc (giá trị chọn hiện ở placeholder); đóng = hiện giá trị chọn.
        value={open ? query : value}
        placeholder={value || placeholder}
        disabled={disabled}
        onFocus={() => {
          setOpen(true);
          setQuery("");
        }}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault(); // đừng submit form của modal
            if (filtered[0]) pick(filtered[0]);
          } else if (e.key === "Escape") setOpen(false);
        }}
      />
      {open && !disabled && (
        <div className="sselect-list">
          {filtered.length === 0 && <div className="sselect-empty">Không tìm thấy</div>}
          {filtered.map((o) => (
            <div
              key={o}
              className={`sselect-item${o === value ? " on" : ""}`}
              // mousedown + preventDefault: chọn trước khi input blur kịp đóng danh sách.
              onMouseDown={(e) => {
                e.preventDefault();
                pick(o);
              }}
            >
              {o}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
