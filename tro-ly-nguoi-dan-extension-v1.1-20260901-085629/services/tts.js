// TTS cho extension — plan_tuyenquang/13. Port từ chatbot-hcc-base-ts/voice-mode-hcc/src/lib/tts.ts.
// Đọc 1 câu qua WebSocket /ws/tts (backend tự chọn giọng: vi → phuongnhi-north).
// Khác bản gốc: WS host lấy từ baseUrl (window.HCC_BASE_URL), KHÔNG dùng window.location.host
// (panel chạy trong iframe trang DVC). Expose window.__hccTTS = { speak, stop, setMuted }.
(() => {
  "use strict";

  // ── Chuẩn hoá text cho TTS (số/ngày/điện thoại → chữ tiếng Việt) ──
  const DIGIT_WORDS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"];

  function numberToVietnamese(n) {
    if (n === 0) return "không";
    if (n < 0) return "âm " + numberToVietnamese(-n);
    const parts = [];
    if (n >= 1_000_000_000) { parts.push(numberToVietnamese(Math.floor(n / 1_000_000_000)) + " tỷ"); n %= 1_000_000_000; }
    if (n >= 1_000_000) { parts.push(numberToVietnamese(Math.floor(n / 1_000_000)) + " triệu"); n %= 1_000_000; }
    if (n >= 1_000) { parts.push(numberToVietnamese(Math.floor(n / 1_000)) + " nghìn"); n %= 1_000; }
    if (n >= 100) { parts.push(DIGIT_WORDS[Math.floor(n / 100)] + " trăm"); n %= 100; }
    if (n >= 20) {
      parts.push(DIGIT_WORDS[Math.floor(n / 10)] + " mươi");
      n %= 10;
      if (n === 1) { parts.push("mốt"); n = 0; }
      else if (n === 5) { parts.push("lăm"); n = 0; }
    } else if (n >= 10) {
      parts.push("mười");
      n %= 10;
      if (n === 5) { parts.push("lăm"); n = 0; }
    }
    if (n > 0) parts.push(DIGIT_WORDS[n]);
    return parts.join(" ");
  }

  function normalizeTTSText(text, lang) {
    let out = String(text || "");
    out = out.replace(/\*\*/g, "");
    out = out.replace(/\*/g, "");
    out = out.replace(/^#{1,6}\s+/gm, "");
    out = out.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");
    out = out.replace(/```[\s\S]*?```/g, "");
    out = out.replace(/`([^`]+)`/g, "$1");
    if (lang && lang !== "vi") {
      // Tiếng Mông (hoặc ngôn ngữ khác): CHỈ bỏ markdown — không đổi số/ngày/sđt thành
      // chữ tiếng Việt (voice Mông tự đọc số theo cách của nó).
      out = out.replace(/^[-•]\s+/gm, "");
      out = out.replace(/\n{3,}/g, "\n\n");
      out = out.replace(/ {2,}/g, " ");
      return out.trim();
    }
    out = out.replace(/(\d{1,3}(?:\.\d{3})+)/g, (m) => m.replace(/\./g, ""));
    out = out.replace(/(\d{1,3}(?:,\d{3})+)/g, (m) => m.replace(/,/g, ""));
    out = out.replace(/(\d+)\s*(đồng|vnđ|VNĐ|đ)\b/gi, (_, num) => numberToVietnamese(parseInt(num)) + " đồng");
    out = out.replace(/(ngày\s+)?(\d{1,2})\/(\d{1,2})\/(\d{4})/g, (_, prefix, dd, mm, yyyy) =>
      `${prefix || "ngày "}${numberToVietnamese(parseInt(dd))} tháng ${numberToVietnamese(parseInt(mm))} năm ${numberToVietnamese(parseInt(yyyy))}`,
    );
    out = out.replace(/(?<!\d)(0\d(?:[\s.\-]?\d){8,9})(?!\d)/g, (_, raw) => {
      const digits = raw.replace(/\D/g, "");
      const words = digits.split("").map((d) => DIGIT_WORDS[parseInt(d)]);
      const groups = [];
      for (let i = 0; i < words.length; i += 3) groups.push(words.slice(i, i + 3).join(" "));
      if (groups.length >= 2 && !groups[groups.length - 1].includes(" ")) {
        const last = groups.pop();
        groups[groups.length - 1] = `${groups[groups.length - 1]} ${last}`;
      }
      return groups.join(", ");
    });
    out = out.replace(/\b(\d{2,})\b/g, (_, num) => numberToVietnamese(parseInt(num)));
    out = out.replace(/(\p{L})\s*\/\s*(\p{L})/gu, "$1 $2");
    out = out.replace(/\//g, " trên ");
    out = out.replace(/%/g, " phần trăm");
    out = out.replace(/&/g, " và ");
    out = out.replace(/^[-•]\s+/gm, "");
    out = out.replace(/\n{3,}/g, "\n\n");
    out = out.replace(/ {2,}/g, " ");
    return out.trim();
  }

  // ── Proxy sang offscreen ──
  // Loa KHÔNG phát trong iframe sidebar nữa: trang điều hướng là iframe chết → câu đang
  // đọc bị nuốt; sidebar tự mở lại không có cú click → AudioContext bị autoplay policy
  // treo. Offscreen (background tạo) sống xuyên chuyển trang và miễn autoplay — sidebar
  // chỉ gửi lệnh {tts-speak, url, text, id} và chờ {tts-event, done, id} để bắn onDone.
  let _muted = false;
  let _idSeq = 0;
  let _generation = 0;
  const _idPrefix = Math.random().toString(36).slice(2, 8); // nhiều tab không giẫm id nhau
  const _pending = {}; // id → onDone (vòng rảnh tay: đọc xong → mở mic)

  function ttsWsUrl(lang) {
    const base = window.HCC_BASE_URL || "https://demo-trolyao-hcc.vnekyc.vn";
    const u = new URL(base);
    u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
    u.pathname = "/ws/tts";
    u.search = `?lang=${lang || "vi"}`;
    return u.toString();
  }

  function speak(text, lang = "vi", onDone) {
    if (_muted || !text || typeof window === "undefined") {
      // Không đọc (mute/rỗng) vẫn phải báo xong để vòng rảnh tay đi tiếp.
      if (onDone) setTimeout(onDone, 0);
      return;
    }
    const id = `${_idPrefix}-${++_idSeq}`;
    const generation = _generation;
    void (async () => {
      const accessToken = await window.tlndAuth?.getAccessToken?.();
      // Người dùng đã barge-in/mute trong lúc refresh token: không được phát câu cũ hoặc
      // gọi onDone để tự mở micro trở lại.
      if (generation !== _generation) return;
      if (!accessToken) {
        if (onDone) setTimeout(onDone, 0);
        return;
      }
      if (onDone) _pending[id] = onDone;
      try {
        chrome.runtime.sendMessage(
          {
            type: "tts-speak",
            url: ttsWsUrl(lang),
            protocols: ["tlnd-voice", `tlnd-auth.${accessToken}`],
            text: normalizeTTSText(text, lang),
            id,
          },
          () => void chrome.runtime.lastError,
        );
      } catch (_) {
        delete _pending[id];
        if (onDone) setTimeout(onDone, 0);
      }
    })();
  }

  function stop() {
    // barge-in/mute: xóa callback (KHÔNG bắn onDone) — người ngắt lời tự quyết bước kế.
    _generation++;
    for (const k of Object.keys(_pending)) delete _pending[k];
    try {
      chrome.runtime.sendMessage({ type: "tts-stop" }, () => void chrome.runtime.lastError);
    } catch (_) { /* bỏ qua */ }
  }

  function setMuted(v) {
    _muted = !!v;
    if (_muted) stop();
  }

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg?.type !== "tts-event") return;
    const cb = _pending[msg.id];
    if (!cb) return; // của tab khác / đã stop / sidebar đời trước
    delete _pending[msg.id];
    try { cb(); } catch (_) { /* nuốt lỗi callback */ }
  });

  window.__hccTTS = { speak, stop, setMuted };
})();
