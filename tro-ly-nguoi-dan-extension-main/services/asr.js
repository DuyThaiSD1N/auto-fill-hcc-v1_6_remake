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
      this.accessToken = opts.accessToken || "";
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
      if (!this.accessToken) {
        this.onError({ name: "AuthError", message: "Phiên đăng nhập giọng nói không hợp lệ." });
        this._setState("error");
        return false;
      }
      let ws;
      try {
        ws = new WebSocket(wsUrl, ["tlnd-voice", `tlnd-auth.${this.accessToken}`]);
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
            // Chốt RỖNG (tiếng ồn, tiếng loa) cũng phải báo dừng — không thì bên gọi vẫn tưởng mic
            // đang nghe ("Đang nghe…" treo, vòng rảnh tay không mở lại mic).
            if (finalText) this.onFinal(finalText);
            else this._setState("stopped");
          }
        } else if (msg.type === "error") {
          // KHÔNG hiện nguyên văn lỗi máy chủ: chi tiết dịch vụ ASR có thể chứa địa chỉ nội bộ.
          this.onError({ name: "AsrError", message: "Dịch vụ nhận giọng nói đang gặp sự cố, thử lại sau hoặc gõ chữ." });
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

  // ── Giữ sẵn phiên (BE báo voice/config.asrWarm) ──
  // Mic + WS /ws/asr mở suốt phiên làm việc; bấm mic chỉ còn gửi {"type":"start","turn":n} rồi cho âm thanh đi —
  // không dựng offscreen / bắt tay WS / xác thực / xin mic lại mỗi lượt (mất mấy giây). Âm thanh CHỈ rời máy khi
  // đang có lượt (armed); ngoài lượt mic vẫn thu nhưng khung bị bỏ ngay. Mỗi lượt một số "turn": transcript của lượt
  // cũ (lượt bị huỷ còn trả về muộn) không lọt sang lượt mới.
  const WARM_PING_MS = 20000; // proxy cắt WS im lặng ~60 giây → ping, BE đáp pong
  const WARM_RECONNECT_MS = [1000, 2000, 5000, 10000];
  const ARM_OPEN_WAIT_MS = 4000; // bấm mic mà WS chưa nối lại kịp → báo lỗi như lượt cũ, không treo "Đang nghe…"
  const ARM_PCM_WATCH_MS = 1500; // đã vào lượt mà chưa có khung âm thanh nào → AudioContext treo, dựng lại mic

  class AsrWarmSession {
    // opts: như AsrSession.
    constructor(opts = {}) {
      this.baseUrl = opts.baseUrl || window.HCC_BASE_URL || "";
      this.lang = opts.lang || "vi";
      this.rate = opts.rate || 16000;
      this.accessToken = opts.accessToken || "";
      this.onPartial = opts.onPartial || function () {};
      this.onFinal = opts.onFinal || function () {};
      this.onState = opts.onState || function () {};
      this.onError = opts.onError || function () {};
      this._ws = null;
      this._mic = null;
      this._micStarting = null;
      this._cooled = false;
      this._turn = 0;
      this._armed = false;
      this._sentStart = false;
      this._lastText = "";
      this._lastPcmAt = 0;
      this._retry = 0;
      this._retryTimer = null;
      this._pingTimer = null;
      this._armTimer = null;
      this._watchTimer = null;
    }

    _setState(s) {
      try {
        this.onState(s);
      } catch (_) {}
    }

    // Sidebar báo sống kèm token mới (token cũ hết hạn thì lần nối lại sau dùng token này).
    update({ baseUrl, accessToken, lang } = {}) {
      if (baseUrl) this.baseUrl = baseUrl;
      if (accessToken) this.accessToken = accessToken;
      if (lang) this.lang = lang;
    }

    async warm() {
      this._cooled = false;
      this._connect();
      await this._ensureMic();
    }

    _ensureMic() {
      if (this._mic && this._mic.active) return Promise.resolve(true);
      if (this._micStarting) return this._micStarting;
      if (!window.MicCapture || !window.micSupported || !window.micSupported()) {
        if (this._armed) {
          this.onError({ name: "NotSupportedError", message: "Trình duyệt không hỗ trợ thu âm." });
          this._disarm("error");
        }
        return Promise.resolve(false);
      }
      const mic = new window.MicCapture({
        rate: this.rate,
        onPcm: (ab) => {
          this._lastPcmAt = Date.now();
          const ws = this._ws;
          if (this._armed && this._sentStart && ws && ws.readyState === WebSocket.OPEN) ws.send(ab);
        },
        onError: (err) => {
          if (this._mic === mic) this._mic = null;
          // Lúc giữ sẵn (chưa ai bấm mic) thì im: báo lỗi quyền micro ở đây là tự mở trang cấp quyền khi chưa ai bấm.
          if (!this._armed) return;
          this.onError(err);
          this._disarm("error");
        },
      });
      this._mic = mic;
      this._micStarting = mic.start().finally(() => { this._micStarting = null; });
      return this._micStarting;
    }

    _connect() {
      if (this._cooled || !this.accessToken) return;
      const cur = this._ws;
      if (cur && (cur.readyState === WebSocket.OPEN || cur.readyState === WebSocket.CONNECTING)) return;
      clearTimeout(this._retryTimer);
      let ws;
      try {
        ws = new WebSocket((window.hccWsBase(this.baseUrl) || "") + "/ws/asr",
          ["tlnd-voice", `tlnd-auth.${this.accessToken}`]);
      } catch (_) {
        this._scheduleReconnect();
        return;
      }
      ws.binaryType = "arraybuffer";
      this._ws = ws;
      ws.onopen = () => {
        if (this._ws !== ws) return;
        this._retry = 0;
        ws.send(JSON.stringify({ type: "warm", lang: this.lang }));
        clearInterval(this._pingTimer);
        this._pingTimer = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "ping" }));
        }, WARM_PING_MS);
        if (this._armed && !this._sentStart) this._sendStart();
      };
      ws.onmessage = (evt) => {
        if (this._ws === ws) this._onMessage(evt);
      };
      ws.onerror = () => { /* onclose chốt */ };
      ws.onclose = () => {
        if (this._ws !== ws) return;
        this._ws = null;
        clearInterval(this._pingTimer);
        if (this._armed) {
          this.onError({ name: "WsError", message: "Mất kết nối dịch vụ nhận giọng nói." });
          this._disarm("error");
        }
        this._scheduleReconnect();
      };
    }

    _scheduleReconnect() {
      if (this._cooled) return;
      clearTimeout(this._retryTimer);
      const delay = WARM_RECONNECT_MS[Math.min(this._retry, WARM_RECONNECT_MS.length - 1)];
      this._retry += 1;
      this._retryTimer = setTimeout(() => this._connect(), delay);
    }

    // Bấm mic (hoặc trợ lý tự mở mic): mở lượt nói mới.
    async arm(lang) {
      if (lang) this.lang = lang;
      this._cooled = false;
      this._turn += 1;
      const turn = this._turn;
      this._armed = true;
      this._sentStart = false;
      this._lastText = "";
      this._setState("connecting");
      this._connect();
      clearTimeout(this._armTimer);
      this._armTimer = setTimeout(() => {
        if (this._armed && this._turn === turn && !this._sentStart) {
          this.onError({ name: "WsError", message: "Không kết nối được dịch vụ nhận giọng nói." });
          this._disarm("error");
        }
      }, ARM_OPEN_WAIT_MS);
      let micOk = await this._ensureMic();
      // Mic hỏng lúc giữ sẵn (lỗi bị nuốt vì chưa ai bấm, vd chưa cấp quyền) → mở lại lúc đã có lượt để báo đúng lỗi.
      if (!micOk && this._armed && this._turn === turn) micOk = await this._ensureMic();
      if (!this._armed || this._turn !== turn || !micOk) return;
      await this._mic?.ensureRunning?.();
      if (!this._armed || this._turn !== turn) return;
      if (this._ws && this._ws.readyState === WebSocket.OPEN && !this._sentStart) this._sendStart();
    }

    _sendStart() {
      const turn = this._turn;
      this._ws.send(JSON.stringify({ type: "start", lang: this.lang, rate: this.rate, turn }));
      this._sentStart = true;
      clearTimeout(this._armTimer);
      this._setState("listening");
      const startedAt = Date.now();
      clearTimeout(this._watchTimer);
      this._watchTimer = setTimeout(() => {
        if (!this._armed || this._turn !== turn || this._lastPcmAt >= startedAt) return;
        console.warn("[TLND-ASR] mic giữ sẵn không có âm thanh → dựng lại mic");
        if (this._mic) this._mic.stop();
        this._mic = null;
        void this._ensureMic();
      }, ARM_PCM_WATCH_MS);
    }

    _onMessage(evt) {
      let msg;
      try {
        msg = JSON.parse(evt.data);
      } catch (_) {
        return;
      }
      if (!this._armed || msg.turn !== this._turn) return; // pong / lượt cũ trả về muộn
      if (msg.type === "transcript") {
        const t = (msg.data && msg.data.transcript) || "";
        if (t) {
          this._lastText = t;
          this.onPartial(t);
        }
        if (msg.data && msg.data.isFinal) {
          const finalText = (this._lastText || "").trim();
          this._disarm("final");
          // Chốt RỖNG (tiếng ồn, tiếng loa) cũng phải báo dừng như AsrSession.
          if (finalText) this.onFinal(finalText);
          else this._setState("stopped");
        }
      } else if (msg.type === "error") {
        this.onError({ name: "AsrError", message: "Dịch vụ nhận giọng nói đang gặp sự cố, thử lại sau hoặc gõ chữ." });
        this._disarm("error");
      } else if (msg.type === "end") {
        const t = (this._lastText || "").trim();
        this._disarm(null);
        if (t) this.onFinal(t);
        else this._setState("stopped");
      }
    }

    _disarm(state) {
      clearTimeout(this._armTimer);
      clearTimeout(this._watchTimer);
      this._armed = false;
      this._sentStart = false;
      if (state) this._setState(state);
    }

    // Người dùng / trợ lý dừng giữa lượt: bỏ lượt, GIỮ mic + WS cho lượt sau.
    disarm() {
      if (!this._armed) return;
      const ws = this._ws;
      if (this._sentStart && ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "cancel" }));
      this._disarm("stopped");
    }

    // Nhả hẳn: đóng WS, tắt mic (hết biểu tượng micro).
    cool() {
      this._cooled = true;
      this._disarm(null);
      clearTimeout(this._retryTimer);
      clearInterval(this._pingTimer);
      if (this._mic) {
        this._mic.stop();
        this._mic = null;
      }
      const ws = this._ws;
      this._ws = null;
      if (ws) {
        ws.onopen = ws.onmessage = ws.onerror = ws.onclose = null;
        try {
          if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "stop" }));
          ws.close();
        } catch (_) {}
      }
    }
  }

  window.AsrSession = AsrSession;
  window.AsrWarmSession = AsrWarmSession;
})();
