// asr.js — Phiên nhận giọng nói (Phase 2, voice-extension-plan.md).
//
// AsrSession nối MicCapture (services/audio.js) ↔ WebSocket /ws/asr của backend.
//   mic PCM S16LE ──► ws.send(binary) ──gRPC──► dịch vụ ASR (.env ASR_GRPC_URI)
//   ws ◄── { type:"transcript", data:{ transcript, isFinal } }  ◄── ASR
//
// Push-to-talk: gọi start() khi bấm nút 🎤. Server tự phát hiện im lặng (ASR_SPEECH_TIMEOUT)
// → trả isFinal → onFinal(text) + TỰ DỪNG mic (1 lượt = 1 câu). Bấm lại để nói câu kế.
//
// KHÔNG phải ES module (khớp <script> của popup.html). Expose window.AsrSession.
// Protocol giống voice-mode-hcc (đã chạy production) — xem src/routes/voice/ws-asr.ts.
(function () {
  // opts: { baseUrl, lang?, rate?, onPartial(text), onFinal(text), onState(state), onError({name,message}) }
  //   state: "connecting" | "listening" | "final" | "stopped" | "error"
  class AsrSession {
    constructor(opts = {}) {
      this.baseUrl = opts.baseUrl || window.HCC_BASE_URL || "";
      this.lang = opts.lang || "vi";
      this.rate = opts.rate || 16000;
      this.onPartial = opts.onPartial || function () {};
      this.onFinal = opts.onFinal || function () {};
      this.onState = opts.onState || function () {};
      this.onError = opts.onError || function () {};
      this._ws = null;
      this._mic = null;
      this._gen = 0;
      this._lastText = "";
    }

    get active() {
      return !!this._ws;
    }

    _setState(s) {
      try {
        this.onState(s);
      } catch (_) {}
    }

    async start() {
      const gen = ++this._gen;
      this._teardown();
      this._lastText = "";
      this._setState("connecting");

      if (!window.MicCapture || !window.micSupported || !window.micSupported()) {
        this.onError({ name: "NotSupportedError", message: "Trình duyệt không hỗ trợ thu âm." });
        this._setState("error");
        return false;
      }

      const wsUrl = (window.hccWsBase(this.baseUrl) || "") + "/ws/asr";
      let ws;
      try {
        ws = new WebSocket(wsUrl);
      } catch (e) {
        this.onError({ name: "WsError", message: "Không kết nối được dịch vụ nhận giọng nói." });
        this._setState("error");
        return false;
      }
      ws.binaryType = "arraybuffer";
      this._ws = ws;

      ws.onopen = async () => {
        if (this._gen !== gen) {
          try { ws.close(); } catch (_) {}
          return;
        }
        ws.send(JSON.stringify({ type: "start", lang: this.lang, rate: this.rate }));

        // Mic mở SAU khi WS open + gửi control "start" → đảm bảo thứ tự frame đúng.
        this._mic = new window.MicCapture({
          rate: this.rate,
          onPcm: (ab) => {
            if (this._gen === gen && ws.readyState === WebSocket.OPEN) ws.send(ab);
          },
          onState: (ms) => {
            if (this._gen === gen && ms === "active") this._setState("listening");
          },
          onError: (err) => {
            if (this._gen !== gen) return;
            this.onError(err); // name "NotAllowedError" → caller hiện hint bật mic
            this._setState("error");
            this._teardown();
          },
        });
        await this._mic.start();
      };

      ws.onmessage = (evt) => {
        if (this._gen !== gen) return;
        let msg;
        try {
          msg = JSON.parse(evt.data);
        } catch (_) {
          return;
        }
        if (msg.type === "transcript") {
          const t = (msg.data && msg.data.transcript) || "";
          if (t) {
            this._lastText = t;
            this.onPartial(t);
          }
          if (msg.data && msg.data.isFinal) {
            const finalText = (this._lastText || "").trim();
            this._setState("final");
            // Push-to-talk: chốt 1 câu → dừng mic, đóng WS, báo caller.
            this._teardown();
            if (finalText) this.onFinal(finalText);
          }
        } else if (msg.type === "error") {
          this.onError({ name: "AsrError", message: msg.message || "Lỗi nhận giọng nói." });
          this._setState("error");
          this._teardown();
        } else if (msg.type === "end") {
          // Server đóng stream mà chưa final → coi như kết thúc, gửi text đang có (nếu có).
          const t = (this._lastText || "").trim();
          this._teardown();
          if (t) this.onFinal(t);
          else this._setState("stopped");
        }
      };

      ws.onerror = () => {
        if (this._gen !== gen) return;
        this.onError({ name: "WsError", message: "Mất kết nối dịch vụ nhận giọng nói." });
        this._setState("error");
        this._teardown();
      };

      ws.onclose = () => {
        if (this._gen === gen && this._ws) {
          // Đóng ngoài ý muốn (chưa teardown) → dọn + báo dừng.
          this._teardown();
          this._setState("stopped");
        }
      };

      return true;
    }

    // Người dùng bấm dừng giữa chừng (hủy lượt nói).
    stop() {
      this._gen++;
      this._teardown();
      this._setState("stopped");
    }

    _teardown() {
      if (this._mic) {
        this._mic.stop();
        this._mic = null;
      }
      if (this._ws) {
        const ws = this._ws;
        this._ws = null;
        ws.onopen = ws.onmessage = ws.onerror = ws.onclose = null;
        try {
          if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
            if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "stop" }));
            ws.close();
          }
        } catch (_) {}
      }
    }
  }

  window.AsrSession = AsrSession;
})();
