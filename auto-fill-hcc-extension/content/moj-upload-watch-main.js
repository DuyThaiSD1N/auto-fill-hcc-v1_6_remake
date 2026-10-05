// Chạy trong MAIN world: content script (isolated world) không thấy XHR/fetch của trang. Cổng moj tải
// tệp qua 2 API — POST /api/File/upload (tải tệp) rồi POST /api/File/cap-nhat-tai-lieu-ca-nhan (nút
// "Thêm vào ví & Chọn"). Có ca cổng báo lỗi HTTP mà KHÔNG hiện toast → engine chỉ biết khi chờ hết hạn.
// Script này báo mã HTTP của 2 API đó sang engine để hoãn tệp ngay. Không đọc header (có token đăng nhập).
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
