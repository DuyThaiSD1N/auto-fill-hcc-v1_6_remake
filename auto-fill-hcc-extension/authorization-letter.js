// Tab "Tạo giấy ủy quyền" — giấy tự soạn tại quầy, KHÔNG phải thủ tục DVC (mở từ mục vàng trên
// màn chọn thủ tục của sidebar). BE: các endpoint dưới /api/v1/assistant/authorization-letter.
//
// Ảnh vào MỘT phiên tải ảnh dùng chung (/api/v1/upload-sessions) từ ba nguồn: chọn tệp, QR điện
// thoại, máy quét tại quầy (lib/scanAgent.js). Bản xem trước là CHÍNH file PDF BE dựng để in —
// không chép mẫu giấy sang đây, nên xem trước và bản in không bao giờ lệch nhau.
(() => {
  "use strict";

  const API = "/api/v1/assistant/authorization-letter";
  const POLL_MS = 2500;
  // Tab đang soạn dở thì giữ extension không tự nạp lại trong ngần này kể từ thao tác cuối.
  const BUSY_KEEP_MS = 30 * 60 * 1000;
  const PREVIEW_DEBOUNCE_MS = 700;
  const FIELDS = [
    ["hoTen", "Họ và tên"], ["ngaySinh", "Ngày sinh"], ["soDinhDanh", "Số căn cước"],
    ["ngayCap", "Ngày cấp"], ["noiCap", "Nơi cấp"], ["noiThuongTru", "Nơi thường trú"],
  ];
  // ── Kiểm tra dữ liệu bước 2 ──
  // Ô để TRỐNG là hợp lệ (giấy in dòng chấm để viết tay) — trừ họ tên. Ô CÓ chữ thì phải đúng dạng:
  // giấy ủy quyền in ra là giấy tờ pháp lý, sai ngày/số căn cước là phải làm lại.
  const REPEAT_RE = /(.)\1{4,}/u;                       // "ttttt", "22222…": gõ nhầm/giữ phím
  const NAME_RE = /^\p{L}[\p{L} .'-]*$/u;
  const ID_RE = /^(\d{12}|\d{9}|[A-Z]\d{7,8})$/;          // CCCD/căn cước 12 số · CMND 9 số · hộ chiếu
  function parseVnDate(v) {
    const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(v || "");
    if (!m) return null;
    const d = new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]));
    return d.getDate() === Number(m[1]) && d.getMonth() === Number(m[2]) - 1 ? d : null;
  }
  function dateError(v) {
    const d = parseVnDate(v);
    if (!d) return "Nhập theo dạng ngày/tháng/năm, ví dụ 05/09/1990";
    if (d.getFullYear() < 1900) return "Năm không hợp lệ";
    if (d > new Date()) return "Ngày không được ở tương lai";
    return "";
  }
  const VALIDATORS = {
    hoTen: (v) => !v ? "Chưa có họ tên"
      : !NAME_RE.test(v) ? "Họ tên chỉ gồm chữ cái và khoảng trắng"
        : REPEAT_RE.test(v) ? "Có vẻ gõ nhầm — kiểm tra lại" : "",
    ngaySinh: (v) => v ? dateError(v) : "",
    soDinhDanh: (v) => v && !ID_RE.test(v)
      ? "Căn cước gồm 12 chữ số (CMND 9 số, hộ chiếu 1 chữ cái + 7–8 số)" : "",
    ngayCap: (v, d) => {
      if (!v) return "";
      const err = dateError(v);
      if (err) return err;
      const birth = parseVnDate(d.ngaySinh);
      return birth && parseVnDate(v) < birth ? "Ngày cấp phải sau ngày sinh" : "";
    },
    noiCap: (v) => v && REPEAT_RE.test(v) ? "Có vẻ gõ nhầm — kiểm tra lại" : "",
    noiThuongTru: (v) => v && REPEAT_RE.test(v) ? "Có vẻ gõ nhầm — kiểm tra lại" : "",
  };
  // Chuẩn hoá lúc rời ô: "5/9/1990", "05-09-1990", "05.09.1990" → "05/09/1990"; số căn cước bỏ cách/chấm.
  function normalizeField(key, v) {
    const t = String(v || "").trim().replace(/\s+/g, " ");
    if (key === "ngaySinh" || key === "ngayCap") {
      const m = /^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$/.exec(t);
      return m ? `${m[1].padStart(2, "0")}/${m[2].padStart(2, "0")}/${m[3]}` : t;
    }
    if (key === "soDinhDanh") return t.replace(/[\s.-]/g, "").toUpperCase();
    return t;
  }
  const fieldError = (key, data) => VALIDATORS[key]?.(String(data[key] || "").trim(), data) || "";

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const state = {
    step: 1, reached: 1,
    sid: "", files: [], thumbs: new Map(),
    people: [],                       // người BE đọc được từ ảnh
    assign: [],                       // assign[i] = "A" (bên ủy quyền) | "B" (bên được ủy quyền) | ""
    sides: { A: [], B: [] },          // bước 2: [{ src: chỉ số người đọc được | -1 tự nhập, data, unsure }]
    config: { suggestions: [], place: "", today: "" },
    pollTimer: null, scanConn: null, scanSeen: new Set(),
    previewTimer: null, previewUrl: "", previewSeq: 0,
    readSeq: 0,                       // tăng mỗi lần bỏ kết quả đọc → lượt đọc về muộn tự bỏ
  };

  // ── Gọi BE (Bearer + tự làm mới token + failover chính/phụ như sidebar) ──
  function api(path, init = {}) {
    return window.tlndOverBases((base) => window.tlndAuth.authFetch(`${base}${path}`, init));
  }
  async function apiJson(path, init) {
    const res = await api(path, init);
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      const err = new Error(data?.message || data?.detail || `Máy chủ báo lỗi (HTTP ${res.status})`);
      err.status = res.status;
      throw err;
    }
    return data;
  }
  const jsonInit = (method, body) => ({
    method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });

  let toastTimer = null;
  function toast(msg) {
    const el = $("toast");
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, 4200);
  }

  // ── Các bước ──
  function goStep(n) {
    if (n > state.reached) return;
    state.step = n;
    document.querySelectorAll(".step").forEach((el) => { el.hidden = Number(el.dataset.step) !== n; });
    document.querySelectorAll(".step-chip").forEach((chip) => {
      const k = Number(chip.dataset.goto);
      chip.classList.toggle("is-active", k === n);
      chip.classList.toggle("is-done", k < n);
      chip.disabled = k > state.reached;
    });
    document.querySelector(".ws-form").scrollTop = 0;
    if (n > 1) schedulePreview(0);
  }
  function reach(n) { state.reached = Math.max(state.reached, n); goStep(n); }

  // ── Phiên tải ảnh ──
  async function openSession() {
    const res = await apiJson("/api/v1/upload-sessions", { method: "POST" });
    state.sid = res.session_id;
    state.files = [];
    $("qrImg").src = `data:image/png;base64,${res.qr_png_base64}`;
    $("qrImg").hidden = false;
    renderFiles();
    startPolling();
  }
  function startPolling() {
    clearInterval(state.pollTimer);
    state.pollTimer = setInterval(() => { if (state.step === 1) void refreshFiles(); }, POLL_MS);
  }
  async function refreshFiles() {
    if (!state.sid) return;
    try {
      const res = await apiJson(`/api/v1/upload-sessions/${encodeURIComponent(state.sid)}`);
      const files = Array.isArray(res.files) ? res.files : [];
      if (files.map((f) => f.fid).join() !== state.files.map((f) => f.fid).join()) {
        state.files = files;
        renderFiles();
        // Bộ ảnh đổi sau khi đã đọc (thêm từ QR/máy quét/chọn tệp) → kết quả cũ không còn khớp.
        if (hasReadResult()) {
          resetReadResult();
          toast("Có ảnh mới — bấm Đọc giấy tờ lại.");
        }
      }
    } catch (_) { /* nhịp sau thử lại */ }
  }
  async function uploadFiles(list) {
    const files = [...(list || [])].filter((f) => f && f.size);
    if (!files.length || !state.sid) return;
    const form = new FormData();
    files.forEach((f) => form.append("files", f, f.name));
    try {
      await apiJson(`/api/v1/upload-sessions/${encodeURIComponent(state.sid)}/files`, { method: "POST", body: form });
      await refreshFiles();
    } catch (e) {
      toast(`Không tải được ảnh: ${e.message}`);
    }
  }
  async function deleteSession(sid, { keepalive = false } = {}) {
    if (!sid) return;
    if (keepalive) {
      // Đóng tab: trang sắp mất, không chờ được vòng làm mới token → gửi thẳng kèm token hiện có.
      const base = await window.tlndBaseUrl().catch(() => "");
      const token = window.tlndAuth.accessToken;
      if (base && token) {
        fetch(`${base}${API}/sessions/${encodeURIComponent(sid)}`, {
          method: "DELETE", keepalive: true, headers: { Authorization: `Bearer ${token}` },
        }).catch(() => {});
      }
      return;
    }
    await api(`${API}/sessions/${encodeURIComponent(sid)}`, { method: "DELETE" }).catch(() => {});
  }

  async function thumbUrl(fid) {
    if (state.thumbs.has(fid)) return state.thumbs.get(fid);
    const res = await api(`/api/v1/upload-sessions/${encodeURIComponent(state.sid)}/files/${encodeURIComponent(fid)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const url = URL.createObjectURL(await res.blob());
    state.thumbs.set(fid, url);
    return url;
  }
  function clearThumbs() {
    state.thumbs.forEach((url) => URL.revokeObjectURL(url));
    state.thumbs.clear();
  }

  function renderFiles() {
    const n = state.files.length;
    $("countNum").textContent = String(n);
    $("dzEmpty").hidden = n > 0;
    $("dzFiles").hidden = n === 0;
    $("dropzone").classList.toggle("has-files", n > 0);
    $("clearFiles").hidden = n === 0;
    $("extractBtn").disabled = n === 0;
    const box = $("dzFiles");
    box.innerHTML = "";
    state.files.forEach((f, i) => {
      const tile = document.createElement("div");
      const isPdf = /pdf/i.test(f.type || "") || /\.pdf$/i.test(f.name || "");
      tile.className = "thumb" + (isPdf ? " is-pdf" : "");
      tile.innerHTML = isPdf
        ? `📄<span>${esc(f.name)}</span>`
        : `<img alt=""><span class="cap">Ảnh ${i + 1}</span>`;
      if (!isPdf) {
        thumbUrl(f.fid).then((url) => { tile.querySelector("img").src = url; }).catch(() => {});
      }
      box.appendChild(tile);
    });
    const add = document.createElement("div");
    add.className = "add-tile";
    add.textContent = "+ Thêm ảnh";
    box.appendChild(add);
  }

  // ── Máy quét tại quầy: agent chỉ báo tệp MỚI quét sau khi kết nối, nên không kéo nhầm giấy cũ ──
  function connectScanner() {
    if (!window.ScanAgent || state.scanConn) return;
    const statusText = {
      da_ket_noi: "Đang theo dõi máy quét — đặt giấy vào máy và bấm quét, tệp tự đưa vào đây.",
      chua_chon_thu_muc: "Máy quét chưa chọn thư mục lưu tệp — chọn trong biểu tượng máy quét ở góc màn hình.",
    };
    state.scanConn = window.ScanAgent.connect({
      onStatus: (s) => { if (statusText[s]) $("scanStatus").textContent = statusText[s]; },
      onFile: async (evt, fetchBlob) => {
        const key = `${evt?.rel}|${evt?.size}`;
        if (!evt?.rel || state.scanSeen.has(key) || state.step !== 1) return;
        state.scanSeen.add(key);
        try {
          const blob = await fetchBlob();
          if (!blob || !blob.size) { state.scanSeen.delete(key); return; }   // máy còn đang ghi tệp
          const name = String(evt.rel).split(/[\\/]/).pop();
          await uploadFiles([new File([blob], name, { type: blob.type || "application/octet-stream" })]);
          toast(`🖨️ Đã nhận ảnh từ máy quét: ${name}`);
        } catch (_) { state.scanSeen.delete(key); }
      },
    });
  }

  // ── Đọc giấy tờ + hỏi vai ──
  let readingTimer = null;
  function showReading(on) {
    $("reading").hidden = !on;
    $("extractBtn").disabled = on || !state.files.length;
    clearInterval(readingTimer);
    const lines = [...document.querySelectorAll(".read-line")];
    lines.forEach((l) => l.classList.remove("is-on"));
    if (!on) return;
    let i = 0;
    lines[0].classList.add("is-on");
    readingTimer = setInterval(() => { i = Math.min(i + 1, lines.length - 1); lines[i].classList.add("is-on"); }, 2200);
  }

  async function extract() {
    showReading(true);
    $("rolePick").hidden = true;
    const sid = state.sid;
    const seq = ++state.readSeq;
    try {
      const res = await apiJson(`${API}/extract`, jsonInit("POST", { session_id: sid }));
      // Trong lúc đọc, cán bộ đã "Bỏ hết" / thêm ảnh → kết quả này của bộ ảnh cũ, bỏ.
      if (sid !== state.sid || seq !== state.readSeq) return;
      state.people = Array.isArray(res.people) ? res.people : [];
      if (res.ocrFailed?.length) toast(`Có ${res.ocrFailed.length} ảnh không đọc được — chụp lại rõ hơn nếu thiếu thông tin.`);
      if (!state.people.length) {
        toast("Không đọc được thông tin trên giấy tờ — cán bộ nhập tay giúp.");
        startManual();
        return;
      }
      state.assign = state.people.map(() => "");
      showRolePick();
    } catch (e) {
      if (sid === state.sid && seq === state.readSeq) toast(`Không đọc được giấy tờ: ${e.message}`);
    } finally {
      if (seq === state.readSeq) showReading(false);
    }
  }

  // ── Chọn bên cho từng người: mỗi bên MỘT hoặc NHIỀU người (đồng ủy quyền / ủy quyền cho nhiều người) ──
  const SIDE_LABEL = { A: "Bên ủy quyền", B: "Bên được ủy quyền" };
  function showRolePick() {
    $("rolePick").hidden = false;
    $("uploadActions").hidden = true;
    $("roleKicker").textContent = `Máy đọc xong — đọc được ${state.people.length} người`;
    const grid = $("roleGrid");
    grid.innerHTML = "";
    state.people.forEach((p, i) => {
      const card = document.createElement("div");
      card.className = "role-card";
      card.dataset.i = String(i);
      card.innerHTML = `<div class="noimg"></div><div class="role-name">${esc(p.hoTen || "(chưa rõ tên)")}</div>
        <div class="role-meta">${esc([p.ngaySinh && `Sinh ${p.ngaySinh}`, p.soDinhDanh && `CCCD ${p.soDinhDanh}`].filter(Boolean).join(" · "))}</div>
        <div class="seg" role="group" aria-label="Chọn bên cho ${esc(p.hoTen || "người này")}">
          <button class="seg-btn" type="button" data-side="A" aria-pressed="false">${SIDE_LABEL.A}</button>
          <button class="seg-btn" type="button" data-side="B" aria-pressed="false">${SIDE_LABEL.B}</button>
        </div>`;
      const fid = p.fids?.[0];
      if (fid) {
        thumbUrl(fid).then((url) => {
          const img = document.createElement("img");
          img.alt = "";
          img.src = url;
          card.querySelector(".noimg")?.replaceWith(img);
        }).catch(() => {});
      }
      card.querySelectorAll(".seg-btn").forEach((btn) => btn.addEventListener("click", () => pickSide(i, btn.dataset.side)));
      grid.appendChild(card);
    });
    renderRolePick();
  }
  function pickSide(i, side) {
    state.assign[i] = state.assign[i] === side ? "" : side;
    // Hai người: chọn bên cho một người là người còn lại hiển nhiên ở bên kia — đỡ một lần chạm.
    if (state.people.length === 2 && state.assign[i]) {
      const other = 1 - i;
      if (!state.assign[other]) state.assign[other] = state.assign[i] === "A" ? "B" : "A";
    }
    renderRolePick();
  }
  function renderRolePick() {
    document.querySelectorAll("#roleGrid .role-card").forEach((card) => {
      const side = state.assign[Number(card.dataset.i)] || "";
      card.classList.toggle("is-a", side === "A");
      card.classList.toggle("is-b", side === "B");
      card.querySelectorAll(".seg-btn").forEach((btn) => btn.setAttribute("aria-pressed", String(btn.dataset.side === side)));
    });
    const count = (side) => state.assign.filter((s) => s === side).length;
    const none = state.assign.filter((s) => !s).length;
    const parts = [`${SIDE_LABEL.A}: <b>${count("A")}</b> người`, `${SIDE_LABEL.B}: <b>${count("B")}</b> người`];
    if (none && none < state.assign.length) parts.push(`<span class="warn">${none} người chưa chọn sẽ không ghi vào giấy</span>`);
    $("roleSummary").innerHTML = parts.join(" · ");
    $("roleNext").disabled = !state.assign.some(Boolean);
  }

  const blankData = () => ({ hoTen: "", ngaySinh: "", soDinhDanh: "", ngayCap: "", noiCap: "", noiThuongTru: "" });
  function entryFromPerson(i) {
    const p = state.people[i];
    const data = blankData();
    for (const [key] of FIELDS) data[key] = p?.[key] || "";
    return { src: i, data, unsure: new Set(p?.chuaChac || []) };
  }
  // Áp lựa chọn bên → danh sách người ở bước 2. Giữ chỗ cán bộ đã sửa ở bước 2 (quay lại bước 1 rồi
  // bấm Tiếp tục không được xoá mất), giữ người tự thêm tay có dữ liệu; bên nào trống thì một dòng
  // trống để nhập tay (vd máy chỉ đọc được giấy của một người).
  function applyAssign() {
    const old = [...state.sides.A, ...state.sides.B];
    const next = { A: [], B: [] };
    state.assign.forEach((side, i) => {
      if (side) next[side].push(old.find((e) => e.src === i) || entryFromPerson(i));
    });
    for (const side of ["A", "B"]) {
      next[side].push(...state.sides[side].filter((e) => e.src < 0 && Object.values(e.data).some(Boolean)));
      if (!next[side].length) next[side].push({ src: -1, data: blankData(), unsure: new Set() });
    }
    state.sides = next;
    renderSides();
    reach(2);
    toast("Đã điền xong. Cán bộ đối chiếu lại ô viền vàng.");
  }
  function startManual() {
    state.people = [];
    state.assign = [];
    state.sides = { A: [{ src: -1, data: blankData(), unsure: new Set() }], B: [{ src: -1, data: blankData(), unsure: new Set() }] };
    renderSides();
    reach(2);
  }

  // ── Bước 2: danh sách người của từng bên ──
  function renderSides() {
    for (const side of ["A", "B"]) {
      const list = state.sides[side];
      const box = $(`people${side}`);
      box.innerHTML = list.map((entry, idx) => `
        <div class="person" data-side="${side}" data-idx="${idx}">
          ${list.length > 1 ? `<div class="person-hd"><b>Người ${idx + 1}</b>
            <button class="link-btn person-rm" type="button">Bỏ người này</button></div>` : ""}
          <div class="fields">${FIELDS.map(([key, label]) => {
            const read = entry.src >= 0;
            const low = read && entry.unsure.has(key);
            const badge = read ? `<span class="conf ${low ? "conf-low" : "conf-ok"}">${low ? "Cần kiểm tra" : "Đọc rõ"}</span>` : "";
            const id = `${side}_${idx}_${key}`;
            const wide = key === "hoTen" || key === "noiThuongTru" ? " wide" : "";
            const err = entry.shown?.has(key) ? fieldError(key, entry.data) : "";
            return `<div class="field${wide}${low ? " check" : ""}${err ? " invalid" : ""}"><label for="${id}">${label} ${badge}</label>
              <input id="${id}" data-key="${key}" autocomplete="off" value="${esc(entry.data[key])}"
                aria-invalid="${err ? "true" : "false"}" aria-describedby="${id}_err">
              <small class="err" id="${id}_err">${esc(err)}</small></div>`;
          }).join("")}</div>
        </div>`).join("");
      $(`count${side}`).textContent = list.length > 1 ? `${list.length} người` : "";
    }
    const names = (side) => state.sides[side].map((e) => e.data.hoTen).filter(Boolean).join(", ");
    $("rolesBar").hidden = !(names("A") && names("B"));
    $("rolesText").innerHTML = `<b>${esc(names("A"))}</b> ủy quyền cho <b>${esc(names("B"))}</b>.`;
    schedulePreview(0);
  }
  function entryOf(el) {
    const person = el.closest(".person");
    return person ? state.sides[person.dataset.side]?.[Number(person.dataset.idx)] : null;
  }
  // Hiện lỗi cho đúng ô (và ô phụ thuộc: ngày cấp so với ngày sinh) mà không vẽ lại cả form.
  function showFieldError(input, entry) {
    const key = input.dataset.key;
    const err = entry.shown?.has(key) ? fieldError(key, entry.data) : "";
    input.closest(".field").classList.toggle("invalid", !!err);
    input.setAttribute("aria-invalid", err ? "true" : "false");
    const slot = document.getElementById(`${input.id}_err`);
    if (slot) slot.textContent = err;
  }
  function onPersonBlur(e) {
    const input = e.target.closest("input[data-key]");
    const entry = input && entryOf(input);
    if (!entry) return;
    const key = input.dataset.key;
    const norm = normalizeField(key, input.value);
    if (norm !== input.value) { input.value = norm; entry.data[key] = norm; schedulePreview(); }
    (entry.shown ||= new Set()).add(key);
    showFieldError(input, entry);
    if (key === "ngaySinh") {
      const cap = input.closest(".person").querySelector('input[data-key="ngayCap"]');
      if (cap) showFieldError(cap, entry);
    }
  }
  // Kiểm cả bước 2; có lỗi thì hiện hết lỗi, cuộn tới ô đầu tiên và trả false.
  function validateSides() {
    let first = null;
    for (const side of ["A", "B"]) {
      state.sides[side].forEach((entry, idx) => {
        entry.shown = new Set(FIELDS.map(([k]) => k));
        for (const [key] of FIELDS) {
          const input = $(`${side}_${idx}_${key}`);
          if (!input) continue;
          showFieldError(input, entry);
          if (!first && fieldError(key, entry.data)) first = input;
        }
      });
    }
    if (!first) return true;
    if (state.step !== 2) goStep(2);
    first.scrollIntoView({ block: "center", behavior: "smooth" });
    first.focus({ preventScroll: true });
    toast("Còn ô nhập chưa đúng — xem dòng chữ đỏ dưới ô.");
    return false;
  }
  function onPersonInput(e) {
    const input = e.target.closest("input[data-key]");
    const person = e.target.closest(".person");
    if (!input || !person) return;
    const entry = state.sides[person.dataset.side]?.[Number(person.dataset.idx)];
    if (entry) {
      entry.data[input.dataset.key] = input.value;
      // Ô đang báo lỗi thì cập nhật lỗi theo từng phím để cán bộ thấy sửa đúng chưa.
      if (entry.shown?.has(input.dataset.key)) showFieldError(input, entry);
    }
    if (input.dataset.key === "hoTen") {
      const names = (side) => state.sides[side].map((x) => x.data.hoTen).filter(Boolean).join(", ");
      $("rolesText").innerHTML = `<b>${esc(names("A"))}</b> ủy quyền cho <b>${esc(names("B"))}</b>.`;
    }
  }
  function onPeopleClick(e) {
    const rm = e.target.closest(".person-rm");
    if (rm) {
      const person = rm.closest(".person");
      const side = person.dataset.side;
      state.sides[side].splice(Number(person.dataset.idx), 1);
      renderSides();
      return;
    }
    const add = e.target.closest("[data-add]");
    if (add) {
      state.sides[add.dataset.add].push({ src: -1, data: blankData(), unsure: new Set() });
      renderSides();
      const list = state.sides[add.dataset.add];
      $(`${add.dataset.add}_${list.length - 1}_hoTen`)?.focus();
    }
  }
  function swapSides() {
    state.sides = { A: state.sides.B, B: state.sides.A };
    state.assign = state.assign.map((s) => (s === "A" ? "B" : s === "B" ? "A" : ""));
    renderSides();
    toast("Đã đổi hai bên.");
  }

  // ── Bước 3 + dựng file ──
  function isoToday() {
    const [d, m, y] = String(state.config.today || "").split("/");
    return y ? `${y}-${m}-${d}` : new Date().toISOString().slice(0, 10);
  }
  const partyOf = (d) => ({
    hoTen: d.hoTen.trim(), ngaySinh: d.ngaySinh.trim(), diaChi: d.noiThuongTru.trim(),
    soDinhDanh: d.soDinhDanh.trim(), ngayCap: d.ngayCap.trim(), noiCap: d.noiCap.trim(),
  });
  function letterPayload(format) {
    const [y, m, d] = ($("madeDate").value || "").split("-");
    return {
      format,
      benUyQuyen: state.sides.A.map((e) => partyOf(e.data)),
      benDuocUyQuyen: state.sides.B.map((e) => partyOf(e.data)),
      ghiNgaySinhDuocUyQuyen: $("showBBirth").checked,
      noiDung: $("content").value,
      lapTai: $("place").value,
      ngayLap: y ? `${d}/${m}/${y}` : "",
      soBan: $("copies").value.trim(),
      moiBenGiu: $("copiesEach").value.trim(),
    };
  }
  async function renderFile(format) {
    const res = await api(`${API}/render`, jsonInit("POST", letterPayload(format)));
    if (!res.ok) throw new Error(`Máy chủ báo lỗi (HTTP ${res.status})`);
    const name = /filename="([^"]+)"/.exec(res.headers.get("content-disposition") || "")?.[1] || `Giay_uy_quyen.${format}`;
    return { blob: await res.blob(), name };
  }

  function schedulePreview(delay = PREVIEW_DEBOUNCE_MS) {
    clearTimeout(state.previewTimer);
    state.previewTimer = setTimeout(() => { void refreshPreview(); }, delay);
  }
  async function refreshPreview() {
    const seq = ++state.previewSeq;
    $("previewState").textContent = "Đang cập nhật…";
    try {
      const { blob } = await renderFile("pdf");
      if (seq !== state.previewSeq) return;          // đã có lượt sửa mới hơn
      if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
      state.previewUrl = URL.createObjectURL(blob);
      $("preview").src = `${state.previewUrl}#toolbar=0&navpanes=0&view=FitH`;
      $("previewState").textContent = "Khổ A4 · tự cập nhật khi sửa";
    } catch (_) {
      if (seq === state.previewSeq) $("previewState").textContent = "Chưa cập nhật được bản xem trước";
    }
  }

  function namesReady() {
    if (!state.sides.A.length || !state.sides.B.length) {
      toast("Mỗi bên phải có ít nhất một người — kiểm tra lại Bước 2.");
      goStep(2);
      return false;
    }
    if (!validateSides()) return false;
    const copies = Number($("copies").value);
    const each = Number($("copiesEach").value);
    if (!Number.isInteger(copies) || copies < 1 || copies > 20) {
      toast("Số bản lập phải từ 1 đến 20.");
      $("copies").focus();
      return false;
    }
    if (!Number.isInteger(each) || each < 1 || each > copies) {
      toast("Số bản mỗi bên giữ phải từ 1 đến số bản lập.");
      $("copiesEach").focus();
      return false;
    }
    return true;
  }
  async function downloadWord() {
    if (!namesReady()) return;
    const btn = $("downloadWord");
    btn.disabled = true;
    try {
      const { blob, name } = await renderFile("docx");
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 4000);
      toast("Đã tải file Word. Mở ra kiểm tra rồi in cho công dân ký.");
    } catch (e) {
      toast(`Không tạo được file Word: ${e.message}`);
    } finally {
      btn.disabled = false;
    }
  }
  async function printLetter() {
    if (!namesReady()) return;
    const btn = $("printBtn");
    btn.disabled = true;
    try {
      const { blob } = await renderFile("pdf");
      const url = URL.createObjectURL(blob);
      // In đúng file PDF vừa dựng (không in trang HTML này). Khung ẩn không in được thì mở tab PDF.
      const frame = document.createElement("iframe");
      frame.style.cssText = "position:fixed;width:0;height:0;border:0;right:0;bottom:0";
      frame.onload = () => {
        try { frame.contentWindow.focus(); frame.contentWindow.print(); }
        catch (_) { window.open(url, "_blank"); }
        setTimeout(() => { frame.remove(); URL.revokeObjectURL(url); }, 60000);
      };
      frame.src = url;
      document.body.appendChild(frame);
    } catch (e) {
      toast(`Không tạo được bản in: ${e.message}`);
    } finally {
      btn.disabled = false;
    }
  }

  // ── Làm lại / đóng ──
  function hasReadResult() {
    return state.people.length > 0 || !$("rolePick").hidden || state.reached > 1;
  }
  // Bỏ MỌI thứ suy ra từ lần đọc ảnh (câu hỏi vai, hai bên ở bước 2) và quay về đầu bước 1. Giữ
  // nguyên bước 3 (nội dung, nơi lập, ngày lập, số bản): cán bộ tự gõ, không lấy từ ảnh.
  function resetReadResult() {
    state.readSeq++;
    showReading(false);
    state.people = [];
    state.assign = [];
    state.sides = { A: [], B: [] };
    state.reached = 1;
    renderSides();
    $("rolePick").hidden = true;
    $("uploadActions").hidden = false;
    $("rolesBar").hidden = true;
    $("showBBirth").checked = false;
    goStep(1);
  }
  async function replaceSession() {
    const old = state.sid;
    state.sid = "";
    state.files = [];
    clearThumbs();
    renderFiles();
    await deleteSession(old);
    await openSession().catch((e) => toast(`Không mở được phiên tải ảnh: ${e.message}`));
  }
  async function resetAll() {
    if (!confirm("Xóa hết ảnh và thông tin đã nhập, làm lại từ đầu?")) return;
    resetReadResult();
    $("content").value = "";
    await replaceSession();
    schedulePreview(0);
  }

  function wire() {
    document.querySelectorAll("[data-goto]").forEach((el) => {
      el.addEventListener("click", () => {
        const n = Number(el.dataset.goto);
        // Sang bước 3 chỉ khi bước 2 đúng hết — sai ngày/số căn cước là giấy in ra phải làm lại.
        if (n === 3 && state.step === 2 && !validateSides()) return;
        if (n === 3) state.reached = Math.max(state.reached, 3);
        goStep(n);
      });
    });
    const dz = $("dropzone");
    $("fileInput").addEventListener("change", (e) => { void uploadFiles(e.target.files); e.target.value = ""; });
    dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("is-hover"); });
    dz.addEventListener("dragleave", () => dz.classList.remove("is-hover"));
    dz.addEventListener("drop", (e) => {
      e.preventDefault();
      dz.classList.remove("is-hover");
      void uploadFiles(e.dataTransfer?.files);
    });
    $("clearFiles").addEventListener("click", (e) => {
      e.preventDefault();
      resetReadResult();
      void replaceSession();
    });
    $("extractBtn").addEventListener("click", () => void extract());
    $("manualBtn").addEventListener("click", startManual);
    $("roleNext").addEventListener("click", applyAssign);
    $("swapRoles").addEventListener("click", swapSides);
    const step2 = document.querySelector(".step[data-step='2']");
    step2.addEventListener("input", onPersonInput);
    step2.addEventListener("focusout", onPersonBlur);
    step2.addEventListener("click", onPeopleClick);
    $("downloadWord").addEventListener("click", () => void downloadWord());
    $("printBtn").addEventListener("click", () => void printLetter());
    $("resetAll").addEventListener("click", () => void resetAll());
    $("closeTab").addEventListener("click", () => window.close());
    document.querySelector(".ws-form").addEventListener("input", (e) => {
      if (e.target.closest(".step[data-step='2'], .step[data-step='3']")) schedulePreview();
    });
    $("showBBirth").addEventListener("change", () => schedulePreview(0));
    $("contentChips").addEventListener("click", (e) => {
      const chip = e.target.closest(".chip");
      if (!chip) return;
      const place = $("place").value.trim();
      $("content").value = `Thay mặt tôi ${chip.textContent.trim().toLowerCase()}${place ? ` tại ${place}` : ""}.`;
      $("content").focus();
      schedulePreview(0);
    });
    // Tự cập nhật: background hỏi từng tab "có đang làm việc không" rồi mới nạp lại extension — nạp
    // lại là ĐÓNG tab này, mất giấy đang soạn. Trả lời "đang bận" khi đã có ảnh hoặc đã qua bước 1,
    // kể cả lúc tab bị ẩn (cán bộ quay sang trang cổng một lúc vẫn phải quay lại in được).
    let lastActivity = Date.now();
    ["pointerdown", "keydown", "input"].forEach((ev) =>
      document.addEventListener(ev, () => { lastActivity = Date.now(); }, { capture: true, passive: true }));
    chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
      if (msg?.action !== "hccTabDangLamViec") return;
      const busy = (state.files.length > 0 || state.reached > 1) && Date.now() - lastActivity < BUSY_KEEP_MS;
      sendResponse({ coPanel: busy, focus: busy, an: false, imLangMs: busy ? 0 : Date.now() - lastActivity });
    });
    // Đóng tab = xoá ảnh căn cước ngay, không chờ phiên hết hạn.
    window.addEventListener("pagehide", () => { void deleteSession(state.sid, { keepalive: true }); });
    window.addEventListener("tlnd-auth-required", showAuthGate);
  }

  function showAuthGate() {
    $("authGate").hidden = false;
    $("wsBody").hidden = true;
    document.querySelectorAll(".step-chip, #resetAll").forEach((el) => { el.disabled = true; });
  }

  async function init() {
    wire();
    goStep(1);
    await window.tlndAuth.load();
    if (!window.tlndAuth.accessToken) return showAuthGate();
    try {
      state.config = { ...state.config, ...(await apiJson(`${API}/config`)) };
    } catch (e) {
      if (e.status === 401) return showAuthGate();
      toast(`Không tải được cấu hình: ${e.message}`);
    }
    $("place").value = state.config.place || "";
    $("madeDate").value = isoToday();
    $("contentChips").innerHTML = (state.config.suggestions || [])
      .map((s) => `<button class="chip" type="button">${esc(s)}</button>`).join("");
    try {
      await openSession();
    } catch (e) {
      toast(`Không mở được phiên tải ảnh: ${e.message}`);
    }
    connectScanner();
    schedulePreview(0);
  }

  void init();
})();
