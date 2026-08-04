// Các endpoint BE gói sẵn cho popup dùng.
const api = {
  // login không qua apiCall (chưa có token) — vẫn đi qua backendFetch để tránh mixed-content.
  async login(username, password) {
    const res = await backendFetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data?.message || data?.error || "Đăng nhập thất bại");
    return data; // { accessToken, refreshToken, user }
  },

  me() {
    return apiJson("/auth/me");
  },

  procedures() {
    return apiJson("/api/v1/procedures");
  },

  process(body) {
    return apiJson("/api/v1/process", { method: "POST", body: JSON.stringify(body) });
  },

  attachmentPlan(body) {
    return apiJson("/api/v1/attachments/plan", { method: "POST", body: JSON.stringify(body) });
  },

  // ===== Phiên tải ảnh qua QR (điện thoại) =====
  // Tạo phiên (có token) → trả { session_id, mobile_url, qr_png_base64, received }.
  createUploadSession() {
    return apiJson("/api/v1/upload-sessions", { method: "POST" });
  },
  // Poll/khôi phục danh sách file của phiên (fallback khi WS rớt).
  getUploadSession(sid) {
    return apiJson(`/api/v1/upload-sessions/${encodeURIComponent(sid)}`);
  },
  // Tải 1 ảnh của phiên về dataURL (qua background — nhị phân). null nếu lỗi.
  fetchUploadFileDataUrl(sid, fid) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage(
        { action: "fetchImageDataUrl",
          url: `${BACKEND_URL}/api/v1/upload-sessions/${encodeURIComponent(sid)}/files/${encodeURIComponent(fid)}` },
        (res) => resolve(res && res.ok ? res : null)
      );
    });
  },

  // Rà soát bbox: đọc lại sources (field → vùng ảnh) đã chụp lúc process. null nếu chưa có / hết hạn.
  async getReviewSources(requestId) {
    if (!requestId) return null;
    try {
      return await apiJson(`/api/v1/review/${encodeURIComponent(requestId)}/sources`);
    } catch (_) {
      return null; // 404 (thủ tục không bật review / chưa có) → ẩn card, không lỗi
    }
  },
};

if (typeof window !== "undefined") window.api = api;
