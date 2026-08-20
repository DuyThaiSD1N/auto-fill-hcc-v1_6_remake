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
    if (!res.ok) {
      const err = new Error(data?.message || data?.error || "Đăng nhập thất bại");
      err.status = res.status;
      err.data = data;
      throw err;
    }
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
  // Tải 1 file của phiên về dataURL, STREAM theo chunk qua Port (fetch vẫn ở background vì
  // CORS/mixed-content). Gửi 1 message cả cục sẽ hụt với file lớn (PDF 65MB → base64 ~87MB >
  // trần ~64MB) → đây là lý do extension "không nhận được". null nếu lỗi.
  fetchUploadFileDataUrl(sid, fid) {
    return new Promise((resolve) => {
      const url = `${BACKEND_URL}/api/v1/upload-sessions/${encodeURIComponent(sid)}/files/${encodeURIComponent(fid)}`;
      let port;
      try { port = chrome.runtime.connect({ name: "filePull" }); }
      catch (_) { return resolve(null); }
      const parts = [];
      let type = "", settled = false;
      const finish = (val) => { if (settled) return; settled = true; try { port.disconnect(); } catch (_) {} resolve(val); };
      port.onMessage.addListener((m) => {
        if (!m) return;
        if (m.error) return finish(null);
        if (m.meta) { type = m.type || ""; return; }
        if (m.chunk != null) { parts.push(m.chunk); return; }
        if (m.done) return finish({ ok: true, dataUrl: parts.join(""), type });
      });
      // SW bị kill giữa chừng / lỗi kênh → coi như thất bại (pull lại lượt sau).
      port.onDisconnect.addListener(() => finish(null));
      try { port.postMessage({ url }); }
      catch (_) { finish(null); }
    });
  },

  // Ghi nhận chấp thuận xử lý dữ liệu (PDPL). BE tự sinh PDF bằng chứng + lưu. Trả {ok, id}.
  // Chỉ khi trả 200 mới coi phiên là ĐÃ đồng ý (bằng chứng chắc chắn đã lưu).
  saveConsent(body) {
    return apiJson("/api/v1/consent", { method: "POST", body: JSON.stringify(body) });
  },

  // ===== Danh mục dùng chung (BE là nguồn duy nhất, extension KHÔNG đóng gói bản sao) =====
  // Cả hai endpoint đều MỞ (không cần token): panel dựng ô địa chỉ + "Đi đến thủ tục" ngay lúc mở,
  // trước khi cán bộ đăng nhập. Dùng backendFetch thẳng để khỏi kéo theo luồng refresh token.
  async locationsCatalog() {
    const res = await backendFetch("/api/v1/locations/catalog");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json(); // { provinces: [{text, slug, name}], wardsBySlug: {slug: {slug, province, communes}} }
  },

  async keKhaiLinks() {
    const res = await backendFetch("/api/v1/procedures/ke-khai-links");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json(); // { links: [{key, label, url, needsAgencySelect, autoConfirm}] }
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
