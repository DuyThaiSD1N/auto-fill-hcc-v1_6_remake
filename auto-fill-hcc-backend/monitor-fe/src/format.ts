export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const value = new Date(iso);
  if (Number.isNaN(value.getTime())) return iso;
  return value.toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms.toLocaleString("vi-VN")} ms`;
  return `${(ms / 1000).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} giây`;
}

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toLocaleString("vi-VN", { maximumFractionDigits: 0 })} KB`;
  return `${(kb / 1024).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} MB`;
}

export function traceSourceLabel(experience: string | null | undefined): string {
  return experience === "handfree" ? "Handfree" : "No handfree";
}

export function traceActionLabel(kind: string | null | undefined): string {
  return kind === "attach" ? "Đính kèm" : "Auto-fill";
}

export function traceUnit(name: string | null | undefined, username: string | null | undefined): string {
  return name?.trim() || username?.trim() || "—";
}

export function safeJson(value: unknown): string {
  if (value == null) return "";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
