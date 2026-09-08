// dataUrl -> Blob: tách binary khỏi JSON để gửi multipart (BE mới base64 hóa lại → payload
// không phình). Chỉ dùng cho luồng /api/v2/process.
function dataUrlToBlob(dataUrl, fallbackType) {
  const fallback = fallbackType || "application/octet-stream";
  if (!dataUrl || typeof dataUrl !== "string") return new Blob([], { type: fallback });
  const comma = dataUrl.indexOf(",");
  if (comma < 0) return new Blob([], { type: fallback });
  const header = dataUrl.slice(0, comma);
  const dataPart = dataUrl.slice(comma + 1);
  const mimeMatch = header.match(/^data:([^;,]+)/i);
  const type = (mimeMatch && mimeMatch[1]) || fallback;
  let bytes;
  if (/;base64/i.test(header)) {
    const binary = atob(dataPart);
    bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  } else {
    const text = decodeURIComponent(dataPart);
    bytes = new Uint8Array(text.length);
    for (let i = 0; i < text.length; i++) bytes[i] = text.charCodeAt(i);
  }
  return new Blob([bytes], { type });
}

// Dựng multipart cho /api/v2/process — DÙNG CHUNG cho fill (điền) và attach (đính kèm).
// Field khớp app/v2/router.py: action, procedure, options(JSON), fileMetadata(JSON), files[] (binary).
// Metadata per-file phải có name/type/role để BE dựng lại FileItem lõi v1.
function buildV2ProcessForm(action, body) {
  const form = new FormData();
  form.append("action", action);
  form.append("procedure", (body && body.procedure) || "");
  form.append("options", JSON.stringify((body && body.options) || {}));
  const files = body && Array.isArray(body.files) ? body.files : [];
  const fileMetadata = files.map((f) => ({
    name: (f && f.name) || "file",
    type: (f && f.type) || "application/octet-stream",
    role: (f && f.role) || "doc",
  }));
  form.append("fileMetadata", JSON.stringify(fileMetadata));
  for (const f of files) {
    form.append("files", dataUrlToBlob(f && f.dataUrl, f && f.type), (f && f.name) || "file");
  }
  return form;
}

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
    // v2 multipart (action=fill): binary đi thẳng, không base64-JSON phình payload. Dùng chung
    // endpoint với attach; BE tái dùng lõi v1 nên kết quả (fields/extracted/...) giữ nguyên.
    return apiJson("/api/v2/process", { method: "POST", body: buildV2ProcessForm("fill", body) });
  },

  attachmentPlan(body) {
    // Báo NĂNG LỰC đính kèm của extension để BE phát plan tương thích ngược: chỉ bản này (mới) mới xử lý
    // được luồng "Thêm giấy tờ" (add-document-dialog) trộn với ô cố định. Bản CŨ không gửi cờ → BE giữ
    // hành vi cũ (không phát add-document-dialog) nên không lỗi "target chưa hỗ trợ".
    let extVersion = "";
    try { extVersion = (chrome.runtime.getManifest() || {}).version || ""; } catch (_) { /* ignore */ }
    const merged = {
      ...body,
      options: {
        ...(body?.options || {}),
        extVersion,
        attachSupports: ["attp-row", "fixed-slot", "add-document-dialog", "fixed-slot+add-document-dialog"],
      },
    };
    return apiJson("/api/v2/process", {
      method: "POST",
      body: buildV2ProcessForm("attach", merged),
    });
  },

  // Case FE tự đính file: chỉ gửi JSON metadata để BE tạo trace/mã hỗ trợ.
  // Tuyệt đối không đưa dataUrl/Blob/file binary vào request này.
  clientAttachmentTrace(body) {
    return apiJson("/api/v1/attachments/client-trace", {
      method: "POST",
      body: JSON.stringify(body),
    });
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
  async fetchUploadFileDataUrl(sid, fid) {
    // GET /files/{fid} yêu cầu Bearer của tài khoản sở hữu phiên (require_upload_session_access).
    // Background fetch KHÔNG tự có token → phải truyền Authorization qua Port, nếu không sẽ 401
    // → file rớt âm thầm ("gửi được mà extension không nhận"). Token hết hạn thì lượt poll sau
    // (getUploadSession qua apiCall) tự refresh rồi lần kéo kế lấy token mới.
    const tokens = await AuthStore.getTokens();
    const headers = tokens?.accessToken ? { Authorization: `Bearer ${tokens.accessToken}` } : {};
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
      try { port.postMessage({ url, headers }); }
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
    return res.json(); // { links: [{key, label, url, needsAgencySelect, provinceOnlyAgency, selectSo, selectSoProvinces, submitCardIncludes, provincePortalFlow, autoConfirm}] }
  },

  // Rà soát bbox: đọc lại sources (field → vùng ảnh) đã chụp lúc process. null nếu chưa có / hết hạn.
  async getReviewSources(requestId, reviewToken) {
    if (!requestId || !reviewToken) return null;
    try {
      return await apiJson(
        `/api/v1/review/${encodeURIComponent(requestId)}/sources?token=${encodeURIComponent(reviewToken)}`,
      );
    } catch (_) {
      return null; // 404 (thủ tục không bật review / chưa có) → ẩn card, không lỗi
    }
  },
};

if (typeof window !== "undefined") window.api = api;
