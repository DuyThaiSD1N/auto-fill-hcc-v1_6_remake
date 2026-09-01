// offscreen.js — chạy AsrSession (mic + WS /ws/asr) trong offscreen document.
//
// Nhận lệnh từ service worker: { target:"offscreen", cmd:"start"|"stop", lang, baseUrl }.
// Phát transcript/trạng thái cho popup: chrome.runtime.sendMessage({ type:"asr-event", event, ... }).
//
// Lý do dùng offscreen: getUserMedia bị Chrome chặn trong iframe popup (nhúng vào trang web).
// Offscreen là ngữ cảnh top-level của origin extension → dùng được quyền micro đã cấp 1 lần
// (qua permission.html), không bị khóa theo trang chủ.
let session = null;

function emit(event, payload) {
  // Callback form + đọc lastError → nuốt lỗi "no receiver" khi popup đã đóng (tránh reject).
  try {
    chrome.runtime.sendMessage(
      Object.assign({ type: "asr-event", event }, payload || {}),
      () => void chrome.runtime.lastError,
    );
  } catch (_) {
    /* bỏ qua */
  }
}

chrome.runtime.onMessage.addListener((msg) => {
  if (!msg || msg.target !== "offscreen") return;

  if (msg.cmd === "start") {
    if (session) session.stop();
    session = new window.AsrSession({
      baseUrl: msg.baseUrl,
      lang: msg.lang || "vi",
      accessToken: msg.accessToken || "",
      onState: (s) => emit("state", { state: s }),
      onPartial: (t) => emit("partial", { text: t }),
      onFinal: (t) => emit("final", { text: t }),
      onError: (e) => emit("error", { error: e && e.message, name: e && e.name }),
    });
    session.start();
  } else if (msg.cmd === "stop") {
    if (session) {
      session.stop();
      session = null;
    }
  } else if (msg.cmd === "tts-speak") {
    ttsEnqueue({ url: msg.url, protocols: msg.protocols || [], text: msg.text, id: msg.id });
  } else if (msg.cmd === "tts-stop") {
    ttsStopAll();
  }
});

// ───────────── TTS phát loa tại offscreen ─────────────
// Loa phải nằm ĐÂY chứ không trong iframe sidebar: (1) trang điều hướng là iframe chết
// → câu đang đọc bị nuốt giữa chừng; (2) sidebar tự mở lại không có cú click nào →
// AudioContext trong iframe bị autoplay policy treo. Offscreen sống xuyên chuyển trang
// và được miễn autoplay. Hàng đợi đặt ở đây luôn để sidebar chết cũng không mất câu chờ.
const ttsQueue = [];
let ttsPlaying = false;
let ttsCurrent = null; // { ws, ctx, sources, id } — để tts-stop cắt được ngay

function ttsEmit(event, id) {
  try {
    chrome.runtime.sendMessage({ type: "tts-event", event, id }, () => void chrome.runtime.lastError);
  } catch (_) { /* bỏ qua */ }
}

function ttsEnqueue(item) {
  if (!item || !item.url || !item.text) return;
  ttsQueue.push(item);
  if (!ttsPlaying) ttsNext();
}

function ttsStopAll() {
  ttsQueue.length = 0;
  if (ttsCurrent) {
    const cur = ttsCurrent;
    ttsCurrent = null;
    try { cur.ws.onmessage = null; cur.ws.onclose = null; cur.ws.close(); } catch (_) { /* noop */ }
    for (const s of cur.sources) { try { s.stop(); } catch (_) { /* noop */ } }
    try { cur.ctx.close(); } catch (_) { /* noop */ }
  }
  ttsPlaying = false;
}

function ttsNext() {
  const item = ttsQueue.shift();
  if (!item) { ttsPlaying = false; return; }
  ttsPlaying = true;
  ttsPlayOne(item);
}

function ttsPlayOne(item) {
  // AudioContext MỚI mỗi câu — tái dùng context trong document này từng dính lỗi
  // khởi tạo "suspended" (xem ghi chú ASR ở background.js).
  let ws;
  try {
    ws = new WebSocket(item.url, item.protocols || []);
  } catch (_) {
    ttsEmit("error", item.id);
    ttsNext();
    return;
  }
  const ctx = new AudioContext({ sampleRate: 16000 });
  const cur = { ws, ctx, sources: [], id: item.id };
  ttsCurrent = cur;
  let nextStartTime = 0;
  let wsClosed = false;

  const finish = (event) => {
    if (ttsCurrent !== cur) return; // đã bị tts-stop cắt → không báo done
    ttsCurrent = null;
    try { ctx.close(); } catch (_) { /* noop */ }
    ttsEmit(event, item.id);
    ttsNext();
  };

  const maybeDone = () => {
    if (wsClosed && cur.sources.length === 0) finish("done");
  };

  ws.onmessage = (evt) => {
    if (ttsCurrent !== cur) return;
    try {
      const data = JSON.parse(evt.data);
      if (data.ready) {
        ws.send(JSON.stringify({ text: item.text }));
        ws.send(JSON.stringify({ text: "" }));
        return;
      }
      if (data.audio && typeof data.audio === "string") {
        if (ctx.state === "suspended") ctx.resume();
        const binary = atob(data.audio);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        const sampleCount = Math.floor(bytes.length / 2);
        if (!sampleCount) return;
        const float32 = new Float32Array(sampleCount);
        const view = new DataView(bytes.buffer);
        for (let i = 0; i < sampleCount; i++) float32[i] = view.getInt16(i * 2, true) / 32768;
        const buffer = ctx.createBuffer(1, float32.length, 16000);
        buffer.getChannelData(0).set(float32);
        const source = ctx.createBufferSource();
        source.buffer = buffer;
        source.connect(ctx.destination);
        cur.sources.push(source);
        const startAt = Math.max(ctx.currentTime, nextStartTime);
        source.start(startAt);
        nextStartTime = startAt + buffer.duration;
        source.onended = () => {
          cur.sources = cur.sources.filter((s) => s !== source);
          maybeDone();
        };
      }
      if (data.isFinal === true) ws.close();
    } catch (_) { /* non-JSON */ }
  };
  ws.onerror = () => { /* onclose sẽ chốt lượt */ };
  ws.onclose = () => {
    wsClosed = true;
    maybeDone();
  };
}
