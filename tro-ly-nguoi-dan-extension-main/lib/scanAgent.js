// Cầu nối tới scan-bridge agent (Go) chạy trên máy cán bộ — dò cổng cục bộ,
// mint token AES-GCM, nghe SSE /v1/events, báo về file MỚI quét ra.
// Hợp đồng đầy đủ: docs/local-api.md trong repo scan-bridge.
//
// Module này KHÔNG biết gì về files[]/form của popup — chỉ báo sự kiện qua
// callback. Phần gắn file vào danh sách đính kèm nằm ở popup.js, y hệt cách
// "Thêm ảnh từ điện thoại (QR)" đã làm (ảnh ngoài kéo về files[] như ảnh chọn tay).
const ScanAgent = (() => {
  // Khoá DÙNG CHUNG với MỌI agent đã cài (config.ini: token_key=...) — đổi
  // khoá này thì phải đổi lại token_key trên toàn bộ máy đã triển khai, không
  // thì agent trả 401 với mọi request. Nằm trong bundle extension là THIẾT KẾ
  // có chủ đích (xem docs/local-api.md §6), không phải sơ suất lộ khoá.
  const TOKEN_KEY_HEX = "3cd6e98cc6170654834e1dd00d25fcf3ba3326aa1e7e0fed0ba57f329fe85218";

  // Cổng mặc định 28147, agent thử lần lượt tới 28151 nếu bận (docs §1).
  const PORTS = [28147, 28148, 28149, 28150, 28151];
  const PING_TIMEOUT_MS = 800;
  const DISCOVER_BACKOFF_START_MS = 3000;
  const DISCOVER_BACKOFF_MAX_MS = 30000;

  function hexToBytes(hex) {
    const out = new Uint8Array(hex.length / 2);
    for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.substr(i * 2, 2), 16);
    return out;
  }

  let keyPromise = null;
  function cryptoKey() {
    if (!keyPromise) {
      keyPromise = crypto.subtle.importKey("raw", hexToBytes(TOKEN_KEY_HEX), "AES-GCM", false, ["encrypt"]);
    }
    return keyPromise;
  }

  // Ký MỘT token mỗi request (docs §2) — jti dùng lại bị agent từ chối 401.
  async function mintToken() {
    const key = await cryptoKey();
    const nonce = crypto.getRandomValues(new Uint8Array(12));
    const jti = [...crypto.getRandomValues(new Uint8Array(8))]
      .map((b) => b.toString(16).padStart(2, "0")).join("");
    const payload = new TextEncoder().encode(
      JSON.stringify({ ts: Math.floor(Date.now() / 1000), jti })
    );
    const sealed = new Uint8Array(
      await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce }, key, payload)
    );
    const raw = new Uint8Array(nonce.length + sealed.length);
    raw.set(nonce, 0);
    raw.set(sealed, nonce.length);
    return btoa(String.fromCharCode(...raw))
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  // ID của extension autofill. Cần đúng MỘT chỗ và chỉ dùng cho việc đọc trường
  // `ext_version` CŨ (số ít) của agent bản cũ — hồi đó agent chỉ quản một
  // extension, và đó là autofill. Không có phép kiểm này thì extension thứ hai
  // cắm vào agent cũ sẽ đọc version của autofill, tưởng mình lạc hậu, rồi nạp
  // lại vô ích cho tới khi chạm trần số lần thử.
  const ID_AUTOFILL = "jggkfcelfkeljnfnelmfmglcjanhmiem";

  function idCuaMinh() {
    try { return chrome.runtime.id || ""; } catch (_) { return ""; }
  }

  // Version của CHÍNH extension này theo lời agent.
  //
  // Agent bản mới trả `ext_versions` = {extension ID: version} cho MỌI extension
  // nó đang giữ — tra bằng chrome.runtime.id là ra đúng của mình, không cần biết
  // slug. `ext_versions` CÓ mà không có ID của mình nghĩa là agent không quản
  // extension này → "" → bỏ qua hẳn luồng tự cập nhật, KHÔNG được lùi về
  // `ext_version` (đó là version của extension KHÁC).
  function versionCuaChinhMinh(data) {
    const theoID = data && data.ext_versions;
    if (theoID && typeof theoID === "object") {
      const v = theoID[idCuaMinh()];
      return typeof v === "string" ? v : "";
    }
    // Agent bản CŨ: chỉ có `ext_version` số ít, và nó luôn là của autofill.
    if (idCuaMinh() !== ID_AUTOFILL) return "";
    return typeof data?.ext_version === "string" ? data.ext_version : "";
  }

  async function pingPort(port) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), PING_TIMEOUT_MS);
    try {
      const res = await fetch(`http://127.0.0.1:${port}/v1/ping`, { signal: ctrl.signal });
      if (!res.ok) return null;
      const data = await res.json();
      if (data?.app !== "scan-bridge-agent") return null;
      // caps: danh sách khả năng agent tự khai (agent bản CŨ không có trường này
      // → mảng rỗng → bên gọi tự ẩn chức năng đi thay vì bấm rồi mới ăn 404).
      return {
        port,
        folderSelected: !!data.folder_selected,
        caps: Array.isArray(data.caps) ? data.caps : [],
        // extVersion: version CỦA CHÍNH EXTENSION NÀY đang nằm trên đĩa (agent
        // giữ đồng bộ với bản CMS phát hành). Lệch với version đang chạy nghĩa
        // là đĩa đã có bản mới, chỉ còn chờ chrome.runtime.reload().
        extVersion: versionCuaChinhMinh(data),
      };
    } catch (_) {
      return null; // khong bat may/timeout - coi nhu khong co agent o cong nay
    } finally {
      clearTimeout(timer);
    }
  }

  // Dò TUẦN TỰ (không song song): mở 5 kết nối cùng lúc tới các cổng không ai
  // lắng nghe chỉ tổ chờ timeout cùng lúc, không nhanh hơn được bao nhiêu.
  async function discoverOnce() {
    for (const port of PORTS) {
      const found = await pingPort(port);
      if (found) return found;
    }
    return null;
  }

  async function authedGet(baseUrl, path) {
    const token = await mintToken();
    return fetch(`${baseUrl}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  }

  async function authedPost(baseUrl, path) {
    const token = await mintToken();
    return fetch(`${baseUrl}${path}`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
  }

  async function fetchFileBlob(baseUrl, rel) {
    const res = await authedGet(baseUrl, `/v1/files/content?rel=${encodeURIComponent(rel)}`);
    if (!res.ok) throw new Error(`khong tai duoc file tu may quet (${res.status})`);
    return res.blob();
  }

  /**
   * Dò agent rồi mở SSE. Tự dò lại + mint token MỚI khi kết nối hỏng hẳn (agent
   * chưa bật, token sai/hết hạn, agent đổi cổng sau khi khởi động lại...) - xem
   * "CLOSED" bên dưới. Mất mạng NGẮN thì để EventSource tự nối lại lấy
   * (readyState CONNECTING, trình duyệt tự gửi kèm Last-Event-ID), không tự
   * đóng/dò lại phá mất chuỗi đó.
   *
   * callbacks:
   *   onStatus(state) - "dang_do" | "chua_chon_thu_muc" | "da_ket_noi" | "mat_ket_noi"
   *   onFile({rel, size, at}, fetchBlob) - bắn cho MỌI `file.added` nhận được
   *     sau khi đã kết nối - gồm cả file thật sự mới LẪN file đã có `rel`
   *     nhưng vừa bị ghi đè nội dung khác (agent dùng lại đúng event này cho
   *     cả hai trường hợp, không có event "file.changed" riêng - xem
   *     apps/agent/internal/watcher/watcher.go hàm Tick()). Bên gọi PHẢI tự
   *     kiểm `rel` đã có trong danh sách của mình chưa để quyết định thêm mới
   *     hay cập nhật lại, không được coi `rel` đã thấy là "bỏ qua". File có
   *     sẵn, KHÔNG đổi gì từ trước lúc kết nối thì sẽ không bao giờ bắn ra
   *     event nào ở đây - agent chỉ phát khi Tick() thấy size/mtime khác.
   *   onFileRemoved({rel, at}) - file bị xoá khỏi thư mục quét (thủ công hoặc
   *     do thao tác khác) SAU khi đã kết nối.
   *   onConnected({listFiles, fetchBlob, renameFile, caps}) - bắn mỗi khi handshake SSE thành
   *     công (kể cả lần trình duyệt tự nối lại). listFiles() trả `/v1/files`
   *     hiện tại — dùng để đối soát lại files đã kéo về trước đó (rel còn
   *     không, hash có đổi không) khi popup mở lại; scanAgent.js không tự giữ
   *     danh sách đó (xem đầu file), việc đối soát thuộc về bên gọi.
   *     renameFile(rel, name) đổi tên file trên đĩa (cần agent có caps
   *     "rename"); caps là mảng khả năng agent tự khai, agent bản cũ trả mảng
   *     rỗng → bên gọi phải tự ẩn chức năng tương ứng.
   *     extVersion là version extension đang nằm trên đĩa ("" nếu agent không
   *     quản thư mục extension).
   *   onExtensionVersion(version) - version extension ĐANG NẰM TRÊN ĐĨA, theo
   *     lời agent. Bắn ở MỌI lượt dò thấy agent (kể cả khi chưa chọn thư mục
   *     scan) và mỗi khi agent tráo xong bản mới. Lệch với version đang chạy
   *     nghĩa là chỉ còn chờ một lần chrome.runtime.reload(); bên gọi quyết
   *     định lúc nào nạp lại (đừng cắt ngang lúc cán bộ đang nộp hồ sơ).
   *
   * Trả về { stop() } để đóng hẳn kết nối.
   */
  function connect(callbacks) {
    let stopped = false;
    let es = null;
    // Backoff SỐNG SUỐT PHIÊN connect() này — dùng chung cho MỌI lý do phải thử
    // lại (chưa thấy agent, chưa chọn thư mục, mở SSE hỏng vì token sai/hết
    // hạn...). Đặt biến này CỤC BỘ trong một lượt thử là bug: mỗi lượt lại bắt
    // đầu lại từ 0, nên trường hợp "thấy agent nhưng SSE hỏng ngay" (token sai)
    // hoá ra KHÔNG BAO GIỜ chờ, retry hàng trăm lần/giây.
    let backoff = DISCOVER_BACKOFF_START_MS;

    function scheduleRetry() {
      if (stopped) return;
      const wait = backoff;
      backoff = Math.min(backoff * 2, DISCOVER_BACKOFF_MAX_MS);
      setTimeout(() => { if (!stopped) void attempt(); }, wait);
    }

    async function attempt() {
      if (stopped) return;
      callbacks.onStatus("dang_do");
      const found = await discoverOnce();
      if (stopped) return;
      if (!found) return scheduleRetry();
      // Báo version trên đĩa NGAY, TRƯỚC cửa kiểm thư mục scan. Để sau cửa đó
      // thì máy chưa chọn thư mục sẽ không bao giờ biết có bản extension mới —
      // kẹt vĩnh viễn ở bản cũ dù agent đã tải bản mới về từ lâu.
      if (callbacks.onExtensionVersion && found.extVersion) callbacks.onExtensionVersion(found.extVersion);
      if (!found.folderSelected) {
        callbacks.onStatus("chua_chon_thu_muc");
        return scheduleRetry(); // can bo co the dang chon thu muc - do lai, khong bo cuoc
      }

      const baseUrl = `http://127.0.0.1:${found.port}`;
      const listFiles = async () => {
        const res = await authedGet(baseUrl, "/v1/files");
        if (!res.ok) return { files: [] };
        return res.json();
      };

      // Đổi tên file NGAY TRÊN ĐĨA. Trả {rel} mới. Ném Error có .status/.code để
      // bên gọi phân biệt được "trùng tên" (409 NAME_EXISTS) với "tên không hợp
      // lệ" (400 BAD_NAME) mà báo cho đúng — xem docs/api-agent.md.
      const renameFile = async (rel, name) => {
        const res = await authedPost(
          baseUrl,
          `/v1/files/rename?rel=${encodeURIComponent(rel)}&name=${encodeURIComponent(name)}`
        );
        if (!res.ok) {
          let code = "";
          try { code = (await res.json())?.error?.code || ""; } catch (_) { /* body rong */ }
          const err = new Error(`doi ten that bai (${res.status} ${code})`);
          err.status = res.status;
          err.code = code;
          throw err;
        }
        return res.json();
      };

      // Dedup theo ID DÒNG SSE (`ev.lastEventId`, dòng "id: N" trên dây),
      // KHÔNG theo `rel`: agent dùng lại đúng event "file.added" cho cả file
      // MỚI lẫn file ĐÃ CÓ nhưng vừa bị ghi đè nội dung khác (size/mtime khác
      // - xem watcher.go Tick(), agent không có event "file.changed" riêng).
      // Chặn theo `rel` (bản trước) làm lần "file.added" thứ hai của cùng một
      // rel - tức nội dung MỚI - bị coi là trùng và bỏ qua vĩnh viễn: cán bộ
      // quét đè lên đúng tên file cũ thì extension vẫn giữ nguyên bản CŨ đã
      // kéo về trước đó, không kiểm lại checksum. Dedup theo ID chỉ chặn đúng
      // một trường hợp cần chặn: SSE gửi trùng lặp CÙNG MỘT dòng (native
      // reconnect chồng lấn Last-Event-ID).
      //
      // KHÔNG cần đọc `/v1/files` làm baseline để "loại trừ file có sẵn" như
      // bản trước: agent chỉ bắn `file.added` khi Tick() thấy size/mtime khác
      // với lần quét trước ĐÓ CỦA CHÍNH NÓ - một file có sẵn, không ai đụng
      // tới từ trước lúc kết nối, sẽ không bao giờ tự nhiên bắn event cho một
      // client mới kết nối (không có Last-Event-ID thì không có replay, xem
      // docs/local-api.md mục SSE). Baseline vì vậy không chặn được rủi ro
      // "hồ sơ cũ để lại" nào cả trên thực tế, mà lại vô tình chặn nhầm đúng
      // ca cần xử lý (nội dung mới trên rel cũ).
      const seenEventId = new Set();

      function xuLyAdded(d, id) {
        if (!d?.rel) return;
        if (id != null) {
          if (seenEventId.has(id)) return;
          seenEventId.add(id);
        }
        callbacks.onFile(d, () => fetchFileBlob(baseUrl, d.rel));
      }
      function xuLyRemoved(d, id) {
        if (!d?.rel) return;
        if (id != null) {
          if (seenEventId.has(id)) return;
          seenEventId.add(id);
        }
        if (callbacks.onFileRemoved) callbacks.onFileRemoved(d);
      }

      const token = await mintToken();
      if (stopped) return;
      es = new EventSource(`${baseUrl}/v1/events?token=${encodeURIComponent(token)}`);
      es.onopen = () => {
        backoff = DISCOVER_BACKOFF_START_MS; // ket noi that su thanh cong -> reset
        callbacks.onStatus("da_ket_noi");
        if (callbacks.onConnected) {
          callbacks.onConnected({
            listFiles,
            fetchBlob: (rel) => fetchFileBlob(baseUrl, rel),
            renameFile,
            caps: found.caps,
            extVersion: found.extVersion || "",
          });

        }
      };
      es.addEventListener("file.added", (ev) => {
        let d;
        try { d = JSON.parse(ev.data); } catch (_) { return; }
        xuLyAdded(d, ev.lastEventId);
      });
      es.addEventListener("file.removed", (ev) => {
        let d;
        try { d = JSON.parse(ev.data); } catch (_) { return; }
        xuLyRemoved(d, ev.lastEventId);
      });
      // Agent bản cũ không bao giờ phát event này; EventSource chỉ gọi listener
      // đã đăng ký nên hai chiều đều an toàn.
      es.addEventListener("extension.updated", (ev) => {
        if (!callbacks.onExtensionVersion) return;
        let d;
        try { d = JSON.parse(ev.data); } catch (_) { return; }
        if (!d || typeof d.version !== "string" || !d.version) return;
        // Hai extension cùng nghe một kênh SSE. Agent kèm `id` để mỗi bên biết
        // tin này có phải của mình không; agent bản cũ không gửi `id` thì tin đó
        // chỉ có thể là của autofill.
        const cuaAi = typeof d.id === "string" && d.id ? d.id : ID_AUTOFILL;
        if (cuaAi !== idCuaMinh()) return;
        callbacks.onExtensionVersion(d.version);
      });

      es.onerror = () => {
        if (stopped || !es) return;
        callbacks.onStatus("mat_ket_noi");
        // CONNECTING: trinh duyet dang TU nap lai (kem Last-Event-ID, khong mat
        // event lo dung luc dut) - de yen. CLOSED: trinh duyet bo cuoc han (handshake
        // loi ngay tu dau - vd 401 do token sai/het han sau 60s - hoac cong da doi
        // sau khi agent khoi dong lai) - phai tu do lai tu dau (co backoff), khong
        // thi ket noi nam chet mai, phai bam reload/tat-bat lai extension moi song
        // lai duoc.
        if (es.readyState === EventSource.CLOSED) {
          es = null;
          scheduleRetry();
        }
      };
    }

    void attempt();

    return {
      stop() {
        stopped = true;
        if (es) {
          try { es.close(); } catch (_) { /* ignore */ }
          es = null;
        }
      },
    };
  }

  return { connect };
})();

if (typeof window !== "undefined") window.ScanAgent = ScanAgent;
