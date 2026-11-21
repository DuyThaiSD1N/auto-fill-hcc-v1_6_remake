// Chạy trong MAIN world: content script (isolated world) không thấy XHR/fetch của trang. Cổng moj tải
// tệp qua 2 API — POST /api/File/upload (tải tệp) rồi POST /api/File/cap-nhat-tai-lieu-ca-nhan (nút
// "Thêm vào ví & Chọn"). Có ca cổng báo lỗi HTTP mà KHÔNG hiện toast → engine chỉ biết khi chờ hết hạn.
// Script này báo mã HTTP của 2 API đó sang engine để hoãn tệp ngay. Không đọc header (có token đăng nhập).

// Danh sách Ví cá nhân (GET /api/CongDan/TaiLieuCaNhan) chỉ gọi được bằng token của trang → trợ lý mở hộp thoại ví để
// TRANG tự gọi, khối này chuyển phần dữ liệu trả về (tên, mã tệp, dung lượng, ngày) sang trợ lý.
// Cờ RIÊNG, đứng trước cờ chung bên dưới: extension Auto Fill cài cùng file này (không có khối ví) với cờ chung
// __HCC_MOJ_FILE_API_WATCH__ — nó nạp trước thì khối sau cờ chung của bản này không bao giờ chạy.
(() => {
  if (!/(^|\.)moj\.gov\.vn$/i.test(location.hostname)) return;
  if (window.__TLND_MOJ_WALLET_WATCH__) return;
  window.__TLND_MOJ_WALLET_WATCH__ = true;

  const WALLET_EVENT = "__HCC_MOJ_WALLET_LIST__";
  const WALLET_LIST = /\/api\/CongDan\/TaiLieuCaNhan(?:[?#]|$)/i;

  // Chỉ tab "Tài liệu tải lên" của chính công dân; tab "Tài liệu được cấp" là bản điện tử do cơ quan cấp.
  function emitWalletList(url, body) {
    try {
      const u = new URL(String(url || ""), location.href);
      if (u.searchParams.get("filter") !== "uploaded" || u.searchParams.get("uploadBy") !== "MY") return;
      const data = (body && body.data) || {};
      const items = (Array.isArray(data.items) ? data.items : []).map((it) => ({
        id: String(it && it.id || ""),
        name: String(it && it.name || ""),
        uri: String(it && it.uri || ""),
        size: Number(it && it.size) || 0,
        type: String(it && it.type || ""),
        createdAt: String(it && it.createdAt || ""),
      }));
      document.dispatchEvent(new CustomEvent(WALLET_EVENT, { detail: JSON.stringify({
        origin: u.origin,
        page: Number(u.searchParams.get("page")) || 1,
        total: Number(data.totalItems) || 0,
        items,
      }) }));
    } catch (_) { /* không để việc nghe danh sách làm hỏng request của cổng */ }
  }

  const xhrProto = window.XMLHttpRequest && window.XMLHttpRequest.prototype;
  if (xhrProto) {
    const originalOpen = xhrProto.open;
    const originalSend = xhrProto.send;
    xhrProto.open = function (method, url, ...rest) {
      this.__tlndWalletUrl = String(url || "");
      return originalOpen.call(this, method, url, ...rest);
    };
    xhrProto.send = function (...args) {
      const url = this.__tlndWalletUrl || "";
      if (WALLET_LIST.test(url)) {
        this.addEventListener("loadend", () => {
          if (this.status < 200 || this.status >= 300) return;
          let body = null;
          try {
            body = this.responseType === "json" ? this.response : JSON.parse(this.responseText || "null");
          } catch (_) { return; }
          emitWalletList(url, body);
        });
      }
      return originalSend.apply(this, args);
    };
  }

  if (typeof window.fetch === "function") {
    const originalFetch = window.fetch;
    window.fetch = function (input, init) {
      const url = typeof input === "string" ? input : (input && input.url) || "";
      if (!WALLET_LIST.test(url)) return originalFetch.apply(this, arguments);
      return originalFetch.apply(this, arguments).then((response) => {
        if (response.ok) response.clone().json().then((body) => emitWalletList(url, body)).catch(() => {});
        return response;
      });
    };
  }
})();

(() => {
  if (!/(^|\.)moj\.gov\.vn$/i.test(location.hostname)) return;
  if (window.__HCC_MOJ_FILE_API_WATCH__) return;
  window.__HCC_MOJ_FILE_API_WATCH__ = true;

  const EVENT = "__HCC_MOJ_FILE_API__";
  const WATCHED = /\/api\/File\/(?:upload|cap-nhat-tai-lieu-ca-nhan)(?:[?#]|$)/i;
  let seq = 0;

  function pathOf(url) {
    try {
      return new URL(String(url || ""), location.href).pathname;
    } catch (_) {
      return String(url || "").split("?")[0];
    }
  }

  // detail là CHUỖI JSON: object đi qua ranh giới MAIN → isolated world có thể thành null.
  function emit(detail) {
    try {
      document.dispatchEvent(new CustomEvent(EVENT, { detail: JSON.stringify(detail) }));
    } catch (_) { /* không để lỗi theo dõi làm hỏng request của cổng */ }
  }

  function bodySnippet(text) {
    return String(text || "").replace(/\s+/g, " ").trim().slice(0, 300);
  }

  const xhrProto = window.XMLHttpRequest && window.XMLHttpRequest.prototype;
  if (xhrProto) {
    const originalOpen = xhrProto.open;
    const originalSend = xhrProto.send;
    xhrProto.open = function (method, url, ...rest) {
      this.__hccMojUrl = String(url || "");
      return originalOpen.call(this, method, url, ...rest);
    };
    xhrProto.send = function (...args) {
      const url = this.__hccMojUrl || "";
      if (WATCHED.test(url)) {
        const id = ++seq;
        const path = pathOf(url);
        emit({ phase: "start", id, path });
        this.addEventListener("loadend", () => {
          const status = Number(this.status) || 0; // 0 = lỗi mạng / bị huỷ / hết giờ
          let message = "";
          if (status < 200 || status >= 300) {
            try { message = bodySnippet(this.responseText); } catch (_) { /* responseType không phải text */ }
          }
          emit({ phase: "end", id, path, status, message });
        });
      }
      return originalSend.apply(this, args);
    };
  }

  if (typeof window.fetch === "function") {
    const originalFetch = window.fetch;
    window.fetch = function (input, init) {
      const url = typeof input === "string" ? input : (input && input.url) || "";
      if (!WATCHED.test(url)) return originalFetch.apply(this, arguments);
      const id = ++seq;
      const path = pathOf(url);
      emit({ phase: "start", id, path });
      return originalFetch.apply(this, arguments).then(
        (response) => {
          const status = Number(response.status) || 0;
          if (status >= 200 && status < 300) {
            emit({ phase: "end", id, path, status, message: "" });
          } else {
            response.clone().text()
              .then((text) => emit({ phase: "end", id, path, status, message: bodySnippet(text) }))
              .catch(() => emit({ phase: "end", id, path, status, message: "" }));
          }
          return response;
        },
        (error) => {
          emit({ phase: "end", id, path, status: 0, message: bodySnippet(error && error.message) });
          throw error;
        },
      );
    };
  }
})();
