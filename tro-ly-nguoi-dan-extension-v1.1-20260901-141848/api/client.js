// api/client.js — client "1 cửa" gọi BE Trợ lý người dân (docs/03 §2.3).
// Extension CHỈ dùng: POST /assistant/chat · GET /assistant/conversations/{id}
// · GET /provinces /wards · (WS voice + upload-session ở Bước 4-5).
// Chat đòi JWT (đăng nhập quầy — api/auth.js); wards/voice/upload giữ public.
(() => {
  "use strict";

  class TlndApiClient {
    constructor() {
      this.conversationId = null;
    }

    async _base() {
      return await window.tlndBaseUrl();
    }

    // fetch có Bearer + tự refresh (401 lần 2 → auth.js bật màn đăng nhập).
    _fetch(url, init) {
      return window.tlndAuth.authFetch(url, init);
    }

    // Gọi có failover: thử backend chính → lỗi hạ tầng → backend phụ. path bắt đầu bằng "/".
    _fetchApi(path, init) {
      return window.tlndOverBases((base) => this._fetch(`${base}${path}`, init));
    }

    async _json(res) {
      const text = await res.text();
      let data = null;
      try { data = text ? JSON.parse(text) : null; } catch (_) { /* data = null */ }
      if (!res.ok) {
        const err = new Error(data?.detail || `HTTP ${res.status}`);
        err.status = res.status;
        throw err;
      }
      return data;
    }

    // POST /api/v1/assistant/chat — MỌI tương tác (gõ/nói/chip/sự kiện).
    // displayText: nhãn chip/card cho history (BE lưu nhãn, không lưu lệnh máy "__action:...").
    async ask(message, { source = "text", clientContext = null, displayText = "", preferredLang = "" } = {}) {
      const body = {
        conversation_id: this.conversationId || undefined,
        message: String(message ?? ""),
        source,
      };
      if (displayText) body.display_message = String(displayText);
      if (clientContext) body.client_context = clientContext;
      // BE chỉ dùng khi TẠO conversation mới → câu chào đầu tiên đã đúng tiếng Mông.
      if (preferredLang) body.preferred_lang = String(preferredLang);
      const res = await this._fetchApi(`/api/v1/assistant/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await this._json(res);
      if (data?.conversation_id) this.conversationId = data.conversation_id;
      return data;
    }

    // GET /api/v1/assistant/conversations/{id} — khôi phục phiên. null nếu hết hạn/không có.
    async getConversation(convId) {
      const id = convId || this.conversationId;
      if (!id) return null;
      const res = await this._fetchApi(`/api/v1/assistant/conversations/${id}`);
      if (res.status === 404) return null;
      const data = await this._json(res);
      if (data?.conversation_id) this.conversationId = data.conversation_id;
      return data;
    }

    // DELETE /api/v1/assistant/conversations/{id} — xoá phiên ngay (nút 🔄). Best-effort.
    async deleteConversation() {
      if (!this.conversationId) return;
      try {
        await this._fetchApi(`/api/v1/assistant/conversations/${this.conversationId}`, { method: "DELETE" });
      } catch (_) { /* BE tắt thì thôi — TTL 24h tự dọn */ }
      this.conversationId = null;
    }

    // GET /api/v1/wards?slug= — danh sách xã của tỉnh (đổ combobox card location).
    async getWards(slug) {
      try {
        // Public (không cần Bearer) nhưng vẫn failover qua tlndOverBases + tlndFetch (có timeout).
        const res = await window.tlndOverBases((base) =>
          window.tlndFetch(`${base}/api/v1/wards?slug=${encodeURIComponent(slug || "")}`));
        if (!res.ok) return null;
        return await res.json();
      } catch (_) {
        return null;
      }
    }
  }

  window.TlndApiClient = TlndApiClient;
})();
