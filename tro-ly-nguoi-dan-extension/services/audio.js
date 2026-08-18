// audio.js — Nền tảng thu âm micro cho voice push-to-talk (Phase 1, voice-extension-plan.md).
//
// MicCapture: mở mic → AudioContext 16k → cắt thành chunk PCM S16LE → gọi onPcm(ArrayBuffer).
// KHÔNG đụng WebSocket ở đây (Phase 2 services/asr.js sẽ nối mic ↔ /ws/asr). Tách để test riêng.
//
// Bối cảnh MV3: popup chạy trong iframe origin chrome-extension://…; content.js đã set
// iframe.allow = "camera; microphone" để parent delegate quyền. getUserMedia bật prompt 1 lần.
//
// Port từ voice-mode-hcc/src/hooks/useSpeechToText.ts (đã chạy production), giữ nguyên thuật toán
// downsample + mẹo "silent gain node" tránh trình duyệt GC ScriptProcessor.
//
// Dùng (không phải ES module để khớp cách load <script> của popup.html):
//   const mic = new MicCapture({ rate: 16000, onPcm, onState, onError });
//   await mic.start();   // -> state "requesting" -> "active", phát onPcm liên tục
//   mic.stop();          // -> state "stopped"
(function () {
  const DEFAULT_RATE = 16000;

  // Float32 [-1,1] → Int16 S16LE. Nếu inputRate ≠ outputRate thì lấy mẫu thưa (nearest).
  // Thực tế AudioContext đã mở ở outputRate nên nhánh đầu (no-op resample) chạy là chính.
  function downsampleBuffer(buffer, inputRate, outputRate) {
    if (outputRate === inputRate) {
      const result = new Int16Array(buffer.length);
      for (let i = 0; i < buffer.length; i++) {
        const s = Math.max(-1, Math.min(1, buffer[i]));
        result[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      return result;
    }
    const compression = inputRate / outputRate;
    const length = Math.floor(buffer.length / compression);
    const result = new Int16Array(length);
    for (let i = 0; i < length; i++) {
      const s = Math.max(-1, Math.min(1, buffer[Math.floor(i * compression)]));
      result[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return result;
  }

  function isSupported() {
    return !!(
      navigator.mediaDevices &&
      typeof navigator.mediaDevices.getUserMedia === "function" &&
      (window.AudioContext || window.webkitAudioContext)
    );
  }

  // Suy ra base WebSocket từ base HTTP của backend (dùng cho Phase 2).
  //   https://host  -> wss://host      http://host:11007 -> ws://host:11007
  function wsBaseFrom(httpBase) {
    const base = (httpBase || window.HCC_BASE_URL || "").replace(/\/+$/, "");
    if (base.startsWith("https://")) return "wss://" + base.slice("https://".length);
    if (base.startsWith("http://")) return "ws://" + base.slice("http://".length);
    return base;
  }

  class MicCapture {
    // opts: { rate?, onPcm(ArrayBuffer), onState(state), onError({name,message}) }
    constructor(opts = {}) {
      this.rate = opts.rate || DEFAULT_RATE;
      this.onPcm = opts.onPcm || function () {};
      this.onState = opts.onState || function () {};
      this.onError = opts.onError || function () {};
      this._gen = 0;
      this._ctx = null;
      this._stream = null;
      this._source = null;
      this._processor = null;
      this._gain = null;
    }

    get active() {
      return !!this._processor;
    }

    _setState(s) {
      try {
        this.onState(s);
      } catch (_) {
        /* nuốt lỗi callback để không vỡ pipeline audio */
      }
    }

    async start() {
      const gen = ++this._gen;
      this._cleanup();

      if (!isSupported()) {
        this.onError({ name: "NotSupportedError", message: "Trình duyệt không hỗ trợ thu âm." });
        this._setState("error");
        return false;
      }

      this._setState("requesting");
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            channelCount: 1,
          },
        });
        // Người dùng bấm dừng / start lại trong lúc chờ cấp quyền → bỏ stream cũ.
        if (this._gen !== gen) {
          stream.getTracks().forEach((t) => t.stop());
          return false;
        }
        this._stream = stream;

        let ctx;
        try {
          const Ctx = window.AudioContext || window.webkitAudioContext;
          ctx = new Ctx({ sampleRate: this.rate });
        } catch (_) {
          const Ctx = window.AudioContext || window.webkitAudioContext;
          ctx = new Ctx();
        }
        this._ctx = ctx;

        // Trong offscreen document (không có user-gesture), AudioContext thường khởi tạo ở trạng
        // thái "suspended" từ lần thứ 2 trở đi → onaudioprocess KHÔNG chạy (mic sáng đèn nhưng
        // không có audio). resume() để ép context chạy. Đồ thị chỉ thu (output gain 0) nên Chrome
        // cho resume không cần gesture.
        if (ctx.state === "suspended") {
          try {
            await ctx.resume();
          } catch (_) {
            /* nếu không resume được sẽ báo lỗi ở nhánh kiểm tra dưới */
          }
        }
        if (this._gen !== gen) {
          // start lại / stop trong lúc await resume → bỏ.
          stream.getTracks().forEach((t) => t.stop());
          ctx.close().catch(() => {});
          return false;
        }

        const source = ctx.createMediaStreamSource(stream);
        this._source = source;

        const processor = ctx.createScriptProcessor(4096, 1, 1);
        this._processor = processor;

        // Gain 0 nối tới destination: giữ ScriptProcessor sống (tránh GC) mà không phát ra loa.
        const silentGain = ctx.createGain();
        silentGain.gain.value = 0;
        this._gain = silentGain;

        source.connect(processor);
        processor.connect(silentGain);
        silentGain.connect(ctx.destination);

        processor.onaudioprocess = (e) => {
          if (this._gen !== gen) return;
          const input = e.inputBuffer.getChannelData(0);
          const pcm = downsampleBuffer(input, ctx.sampleRate, this.rate);
          // slice(0) → ArrayBuffer độc lập (an toàn khi gửi qua WS ở Phase 2).
          this.onPcm(pcm.buffer.slice(0));
        };

        this._setState("active");
        return true;
      } catch (err) {
        if (this._gen !== gen) return false;
        const name = (err && err.name) || "Error";
        const message =
          name === "NotAllowedError"
            ? "not-allowed"
            : (err && err.message) || "Không truy cập được micro.";
        this.onError({ name, message });
        this._setState("error");
        this._cleanup();
        return false;
      }
    }

    stop() {
      this._gen++;
      this._cleanup();
      this._setState("stopped");
    }

    _cleanup() {
      if (this._processor) {
        this._processor.onaudioprocess = null;
        try {
          this._processor.disconnect();
        } catch (_) {}
        this._processor = null;
      }
      if (this._source) {
        try {
          this._source.disconnect();
        } catch (_) {}
        this._source = null;
      }
      if (this._gain) {
        try {
          this._gain.disconnect();
        } catch (_) {}
        this._gain = null;
      }
      if (this._ctx && this._ctx.state !== "closed") {
        this._ctx.close().catch(() => {});
      }
      this._ctx = null;
      if (this._stream) {
        this._stream.getTracks().forEach((t) => t.stop());
        this._stream = null;
      }
    }
  }

  // Expose toàn cục (khớp cách popup.html load bằng <script>, không dùng import).
  window.MicCapture = MicCapture;
  window.micSupported = isSupported;
  window.hccWsBase = wsBaseFrom;
})();
