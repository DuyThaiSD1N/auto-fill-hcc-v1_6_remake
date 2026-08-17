export function fmtDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

// Thời gian xử lý: < 1s hiển thị ms, còn lại đổi ra giây (2 số lẻ).
export function fmtMs(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} s`;
}

// Dung lượng payload: tự chọn B / KB / MB.
export function fmtBytes(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  const kb = n / 1024;
  if (kb < 1024) return `${kb.toLocaleString("vi-VN", { maximumFractionDigits: 0 })} KB`;
  return `${(kb / 1024).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} MB`;
}
