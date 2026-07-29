// Điều hướng tối giản bằng hash (không kéo react-router vào). Trang chi tiết trace có URL
// riêng #/trace/<id> để share/F5/nút Back trình duyệt đều hoạt động.
export interface TraceRoute {
  name: "trace";
  id: string;
}

export function parseRoute(): TraceRoute | null {
  const m = window.location.hash.match(/^#\/trace\/(.+)$/);
  return m ? { name: "trace", id: decodeURIComponent(m[1]) } : null;
}

export function goToTrace(id: string): void {
  window.location.hash = `#/trace/${encodeURIComponent(id)}`;
}

export function goToList(): void {
  // Xóa hash → App quay về view danh sách. Dùng pushState để không để lại "#" thừa trên URL.
  if (window.location.hash) {
    history.pushState("", document.title, window.location.pathname + window.location.search);
    window.dispatchEvent(new Event("hashchange"));
  }
}
