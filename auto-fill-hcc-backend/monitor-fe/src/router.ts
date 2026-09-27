import { useEffect, useState } from "react";

// Router tối giản bằng History API: đủ cho 6 route và giữ bộ lọc trên URL (gửi link cho nhau
// mở đúng màn; Back khôi phục bộ lọc) mà không thêm thư viện.

export interface Location {
  path: string;
  query: URLSearchParams;
}

const EVENT = "hcc-monitor:navigate";

function read(): Location {
  return { path: window.location.pathname, query: new URLSearchParams(window.location.search) };
}

export function navigate(to: string, { replace = false } = {}) {
  if (to === `${window.location.pathname}${window.location.search}`) return;
  if (replace) window.history.replaceState({}, "", to);
  else window.history.pushState({}, "", to);
  window.dispatchEvent(new Event(EVENT));
  if (!replace) window.scrollTo({ top: 0 });
}

export function useLocation(): Location {
  const [loc, setLoc] = useState<Location>(read);
  useEffect(() => {
    const update = () => setLoc(read());
    window.addEventListener("popstate", update);
    window.addEventListener(EVENT, update);
    return () => {
      window.removeEventListener("popstate", update);
      window.removeEventListener(EVENT, update);
    };
  }, []);
  return loc;
}

export function match(pattern: string, path: string): Record<string, string> | null {
  const a = pattern.split("/").filter(Boolean);
  const b = path.split("/").filter(Boolean);
  if (a.length !== b.length) return null;
  const params: Record<string, string> = {};
  for (let i = 0; i < a.length; i += 1) {
    if (a[i].startsWith(":")) params[a[i].slice(1)] = decodeURIComponent(b[i]);
    else if (a[i] !== b[i]) return null;
  }
  return params;
}

/** Dựng chuỗi query, bỏ giá trị rỗng/mặc định để URL gọn. */
export function buildQuery(values: Record<string, string | number | null | undefined>): string {
  const q = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value === null || value === undefined || value === "" || value === "all") continue;
    q.set(key, String(value));
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

/** Link nội bộ: giữ Ctrl/⌘-click mở tab mới, click thường đi bằng History API. */
export function onLinkClick(event: React.MouseEvent, to: string) {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey) return;
  event.preventDefault();
  navigate(to);
}
