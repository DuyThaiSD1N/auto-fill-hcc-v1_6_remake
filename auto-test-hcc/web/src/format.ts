const VN = "vi-VN";

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const value = new Date(iso);
  if (Number.isNaN(value.getTime())) return iso;
  return value.toLocaleString(VN, {
    day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

/** Giờ ngắn cho bảng: hôm nay chỉ giờ, ngày khác thêm ngày/tháng. */
export function formatWhen(iso: string | null | undefined): { main: string; sub: string } {
  if (!iso) return { main: "—", sub: "" };
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return { main: iso, sub: "" };
  const time = d.toLocaleTimeString(VN, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const date = d.toLocaleDateString(VN, { day: "2-digit", month: "2-digit" });
  const today = new Date().toDateString() === d.toDateString();
  return { main: time, sub: today ? "hôm nay" : date };
}

export function formatClock(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleTimeString(VN, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

/** ms → "850 ms" / "14,2 s" / "2 ph 05 s". */
export function formatMs(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || Number.isNaN(ms)) return "—";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  if (ms < 60_000) return `${(ms / 1000).toLocaleString(VN, { maximumFractionDigits: ms < 10_000 ? 2 : 1 })} s`;
  const m = Math.floor(ms / 60_000);
  const s = Math.round((ms % 60_000) / 1000);
  return `${m} ph ${String(s).padStart(2, "0")} s`;
}

/** Số giây gọn cho ô số lớn: trả [số, đơn vị]. */
export function splitMs(ms: number | null | undefined): [string, string] {
  if (ms === null || ms === undefined) return ["—", ""];
  if (ms < 1000) return [String(Math.round(ms)), "ms"];
  return [(ms / 1000).toLocaleString(VN, { maximumFractionDigits: 1 }), "s"];
}

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toLocaleString(VN, { maximumFractionDigits: 0 })} KB`;
  return `${(kb / 1024).toLocaleString(VN, { maximumFractionDigits: 1 })} MB`;
}

export function formatInt(n: number | null | undefined): string {
  return n === null || n === undefined ? "—" : n.toLocaleString(VN);
}

export function pct(part: number, total: number): string {
  if (!total) return "—";
  return `${((part / total) * 100).toLocaleString(VN, { maximumFractionDigits: 1 })}%`;
}

export function safeJson(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") {
    try {
      return JSON.stringify(JSON.parse(value), null, 2);
    } catch {
      return value;
    }
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

/** Ngày (giờ VN) dạng YYYY-MM-DD cho bộ lọc, lùi `days` ngày từ hôm nay. */
export function isoDay(daysAgo = 0): string {
  const d = new Date(Date.now() - daysAgo * 86_400_000);
  const vn = new Date(d.getTime() + (7 * 60 + d.getTimezoneOffset()) * 60_000);
  return `${vn.getFullYear()}-${String(vn.getMonth() + 1).padStart(2, "0")}-${String(vn.getDate()).padStart(2, "0")}`;
}
