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
// Metadata per-file phải có name/type/role để BE dựng lại FileItem lõi v1. Tệp có trong `stored`
// chỉ gửi mã sha256 (metadata.stored), không kèm binary.
function buildV2ProcessForm(action, body, blobs, stored) {
  const form = new FormData();
  form.append("action", action);
  form.append("procedure", (body && body.procedure) || "");
  form.append("options", JSON.stringify((body && body.options) || {}));
  const files = body && Array.isArray(body.files) ? body.files : [];
  const fileMetadata = files.map((f, i) => ({
    name: (f && f.name) || "file",
    type: (f && f.type) || "application/octet-stream",
    role: (f && f.role) || "doc",
    ...(stored && stored[i] ? { stored: stored[i] } : {}),
  }));
  form.append("fileMetadata", JSON.stringify(fileMetadata));
  files.forEach((f, i) => {
    if (stored && stored[i]) return;
    const blob = blobs ? blobs[i] : dataUrlToBlob(f && f.dataUrl, f && f.type);
    form.append("files", blob, (f && f.name) || "file");
  });
  return form;
}

// sha256 các tệp máy chủ đã lưu ở lượt điền/đính trước (BE trả fileRefs): lượt sau chỉ gửi mã thay
// vì đẩy lại cả tệp — mạng chậm mất cả phút cho tệp vài chục MB ở bước đính kèm.
const serverFileHashes = new Set();

async function sha256Hex(blob) {
  if (!globalThis.crypto || !globalThis.crypto.subtle) return "";
  try {
    const digest = await globalThis.crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
    return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
  } catch (_) {
    return "";
  }
}

// Bước điền gửi bản nén (lib/nenTep.js) cho tệp rất nặng. Bước đính gửi bản gốc: planner đính kèm kiểm
// trần dung lượng cổng theo đúng tệp BE nhận, trong khi tệp đính lên cổng là bản gốc. Nhớ bản nén theo tệp
// gốc: lượt điền lại (vd nút người ủy quyền) gửi đúng bản cũ → BE nhận ra tệp đã lưu, trúng cache OCR.
const shrunkUploads = new Map();

async function blobForUpload(action, f) {
  const blob = dataUrlToBlob(f && f.dataUrl, f && f.type);
  if (action !== "fill" || typeof NenTep === "undefined" || blob.size <= NenTep.MIN_BYTES) return blob;
  if (!shrunkUploads.has(f.dataUrl)) {
    shrunkUploads.set(f.dataUrl, NenTep.forUpload(blob));
    if (shrunkUploads.size > 8) shrunkUploads.delete(shrunkUploads.keys().next().value);
  }
  return shrunkUploads.get(f.dataUrl);
}

async function postV2Process(action, body) {
  const files = body && Array.isArray(body.files) ? body.files : [];
  const blobs = await Promise.all(files.map((f) => blobForUpload(action, f)));
  const hashes = await Promise.all(blobs.map(sha256Hex));
  const stored = hashes.map((h) => (h && serverFileHashes.has(h) ? h : ""));
  const send = (refs) => apiJson("/api/v2/process", {
    method: "POST",
    body: buildV2ProcessForm(action, body, blobs, refs),
  });
  let res;
  try {
    res = await send(stored.some(Boolean) ? stored : null);
  } catch (err) {
    // Máy chủ không còn tệp (đã chuyển kho / backend dự phòng bản cũ) → gửi lại đầy đủ.
    const code = err && err.data && err.data.error;
    if (!stored.some(Boolean) || !["STORED_FILE_MISSING", "BAD_FILE_METADATA"].includes(code)) throw err;
    serverFileHashes.clear();
    res = await send(null);
  }
  if (res && res.fileRefs) hashes.forEach((h) => h && serverFileHashes.add(h));
  return res;
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

  // Phiếu đánh giá trải nghiệm. Gọi được NHIỀU lần cho cùng hồ sơ, lần sau ghi đè: bước 1 gửi
  // mỗi mức (ghi ngay khi công dân chạm, để bỏ dở vẫn còn số), bước 2 gửi kèm lý do/ý kiến.
  dossierRating(body) {
    return apiJson("/api/v1/dossiers/rating", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },

  process(body) {
    // v2 multipart (action=fill): binary đi thẳng, không base64-JSON phình payload. Dùng chung
    // endpoint với attach; BE tái dùng lõi v1 nên kết quả (fields/extracted/...) giữ nguyên.
    return postV2Process("fill", body);
  },

  // Ảnh HEIC → JPG (BE đổi; Chrome không giải mã được HEIC). BE trả JSON có dataUrl vì backendFetch đọc mọi
  // phản hồi dạng chữ (không lấy được nhị phân). Trả Blob JPG, lỗi thì ném.
  async convertHeic(file) {
    const form = new FormData();
    form.append("file", file, file.name || "anh.heic");
    const data = await apiJson("/api/v1/files/convert-image", { method: "POST", body: form });
    if (!data?.dataUrl) throw new Error("BE không trả ảnh JPG");
    return dataUrlToBlob(data.dataUrl, "image/jpeg");
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
    return postV2Process("attach", merged);
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
      // Phải dùng base ĐANG ACTIVE: getUploadSession đi qua apiJson (có failover) nên khi chạy
      // backend phụ, hardcode BACKEND_URL sẽ kéo file ở server KHÔNG có phiên → 404 im lặng,
      // poll thử lại vô hạn mà cán bộ không thấy gì.
      const base = (typeof activeBackendBase === "function") ? activeBackendBase() : BACKEND_URL;
      const url = `${base}/api/v1/upload-sessions/${encodeURIComponent(sid)}/files/${encodeURIComponent(fid)}`;
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
    // `text` = tên khớp option trên cổng DVC (dùng để điền hộ); `label` = nhãn hiển thị cho cán bộ.
    return res.json(); // { provinces: [{text, slug, name, label}], wardsBySlug: {slug: {slug, province, communes}} }
  },

  // Kèm token khi đã đăng nhập: BE bỏ thủ tục riêng của tỉnh khác (provinceOnly) theo tỉnh tài
  // khoản. Chưa đăng nhập thì gọi trơn, BE trả đủ danh mục.
  keKhaiLinks() {
    return apiJson("/api/v1/procedures/ke-khai-links"); // { links: [{key, label, url, needsAgencySelect, provinceOnlyAgency, selectSo, selectSoProvinces, submitCardIncludes, submitCardIndex, provincePortalFlow, autoConfirm, provinceOnly}] }
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
