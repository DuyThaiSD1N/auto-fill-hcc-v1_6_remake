// Tab "Tờ khai đăng ký hộ kinh doanh": cán bộ Auto Fill điền, xem trước, tải Word/PDF và in. Chỉ mở từ thủ tục
// dang-ky-kinh-doanh trong panel. BE: /api/v1/ho-kinh-doanh/giay-de-nghi.
//
// Bản xem trước là CHÍNH file PDF BE dựng để in, không chép mẫu giấy sang đây nên xem trước và bản in không lệch.
// Gõ không cập nhật gì: cán bộ điền hết rồi bấm "Lưu" (đầu trang, hoặc Ctrl+S) — kiểm ô, dựng bản xem trước MỘT lần
// và chuyển tờ khai cho Auto Fill qua chrome.storage.session (chỉ trong RAM, không ghi đĩa vì có số định danh); popup
// đọc khi bấm điền, Auto Fill điền cổng thẳng theo bản đã lưu, không quét. Đóng tab / làm lại là xoá.
(() => {
  "use strict";

  const API = "/api/v1/ho-kinh-doanh/giay-de-nghi";
  const BUSY_KEEP_MS = 30 * 60 * 1000;
  const MAX_NGANH = 50;
  const MAX_THANH_VIEN = 20;
  const lib = window.HccGiayDeNghiHkd;

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const state = {
    config: { kinhGui: "", diaDanh: "", today: "", nganh: [] },
    nganhTheoMa: new Map(),
    previewUrl: "", previewSeq: 0,
    vonChuTuDoc: true, // ô bằng chữ còn theo số; cán bộ sửa tay thì thôi tự đọc đè lên
    dirty: false, // đã gõ gì trong tab (báo bận khi extension tự cập nhật, hỏi lại khi đóng tab)
    unsaved: false, // có sửa sau lần bấm Lưu gần nhất
    savedAt: 0, // lúc Lưu gần nhất có chuyển tờ khai cho Auto Fill
    gateShown: false,
    tabId: null,
  };
  const sessionStore = chrome.storage?.session || null;

  let toastTimer = null;
  function toast(msg) {
    const el = $("toast");
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, 4200);
  }

  function showAuthGate() {
    state.gateShown = true;
    $("authGate").hidden = false;
    $("wsBody").hidden = true;
    ["saveBtn", "blankWord", "resetAll"].forEach((id) => { $(id).disabled = true; });
  }

  // ── Kiểm tra ô ──
  const CHECK = {
    ngay: (v) => lib.loiNgay(v),
    ngayQuaKhu: (v) => lib.loiNgay(v, { quaKhu: true }),
    hoa: (v) => lib.loiChu(v),
    dinhDanh: (v) => lib.loiSoDinhDanh(v),
    dienThoai: (v) => lib.loiDienThoai(v),
    email: (v) => lib.loiEmail(v),
    laoDong: (v) => lib.loiLaoDong(v),
    maNganh: (v) => lib.loiMaNganh(v),
  };
  const NORMALIZE = {
    ngay: lib.chuanHoaNgay,
    ngayQuaKhu: lib.chuanHoaNgay,
    dinhDanh: lib.chuanHoaSoDinhDanh,
    hoa: (v) => v.toLocaleUpperCase("vi"),
  };

  function normalizeInput(input) {
    const fix = NORMALIZE[input.dataset.kind];
    const text = input.value.trim().replace(/\s+/g, " ");
    const next = fix ? fix(text) : text;
    if (next !== input.value) input.value = next;
  }
  function showError(input) {
    const check = CHECK[input.dataset.kind];
    const error = check ? check(input.value.trim()) : "";
    const field = input.closest(".field");
    field?.classList.toggle("invalid", !!error);
    input.setAttribute("aria-invalid", error ? "true" : "false");
    const slot = field?.querySelector(".err");
    if (slot) slot.textContent = error;
    return error;
  }
  // Có ô sai thì mở khối thu gọn chứa nó, cuộn tới ô đầu và trả false: sai ngày/số định danh là in ra phải làm lại.
  function validateAll() {
    let first = null;
    document.querySelectorAll("#form input[data-kind]").forEach((input) => {
      if (input.closest("[hidden]")) return; // bảng thành viên đang ẩn thì không gửi, không được chặn nút In
      normalizeInput(input);
      if (showError(input) && !first) first = input;
    });
    if (!first) return true;
    const details = first.closest("details");
    if (details) details.open = true;
    first.scrollIntoView({ block: "center", behavior: "smooth" });
    first.focus({ preventScroll: true });
    toast("Còn ô nhập chưa đúng, xem dòng chữ đỏ dưới ô.");
    return false;
  }

  // ── Bảng ngành nghề ──
  function renderNganhRow(data = {}) {
    const row = document.createElement("div");
    row.className = "row-card";
    row.innerHTML = `
      <div class="row-hd">
        <label class="row-main"><input type="radio" name="nganhChinh"> Ngành, nghề kinh doanh chính</label>
        <button class="link-btn row-rm" type="button">Bỏ dòng này</button>
      </div>
      <div class="fields nganh-grid">
        <div class="field ma-search"><label>Mã ngành</label>
          <input data-col="ma" data-kind="maNganh" inputmode="numeric" maxlength="10" autocomplete="off" placeholder="Gõ mã, vd 4721"
            role="combobox" aria-autocomplete="list" aria-expanded="false" value="${esc(data.ma)}">
          <ul class="ma-goi-y" role="listbox" hidden></ul><small class="err"></small></div>
        <div class="field"><label>Tên ngành (tự điền theo mã, sửa thêm được)</label><input data-col="ten" maxlength="300" value="${esc(data.ten)}"></div>
      </div>`;
    $("nganhRows").appendChild(row);
    return row;
  }
  function addNganh(data) {
    if ($("nganhRows").children.length >= MAX_NGANH) return toast(`Tối đa ${MAX_NGANH} ngành, nghề.`);
    const row = renderNganhRow(data);
    if (!document.querySelector('input[name="nganhChinh"]:checked')) row.querySelector('input[name="nganhChinh"]').checked = true;
    return row;
  }
  // ── Tìm ngành theo mã: danh sách thả xuống dưới ô Mã ngành ──
  function goiYCua(input) {
    return input.closest(".ma-search")?.querySelector(".ma-goi-y");
  }
  function anGoiY(input) {
    const list = goiYCua(input);
    if (!list) return;
    list.hidden = true;
    list.innerHTML = "";
    input.setAttribute("aria-expanded", "false");
  }
  function hienGoiY(input) {
    const list = goiYCua(input);
    const items = lib.timTheoMa(state.config.nganh, input.value);
    if (!list || !items.length) return anGoiY(input);
    list.innerHTML = items.map((item, i) => `
      <li role="option" data-ma="${esc(item.ma)}" aria-selected="${i === 0}" class="${i === 0 ? "on" : ""}">
        <b>${esc(item.ma)}</b><span>${esc(item.ten)}</span></li>`).join("");
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
  }
  function chonMa(input, ma) {
    const row = input.closest(".row-card");
    const ten = row.querySelector('[data-col="ten"]');
    // Tên còn trống hoặc vẫn là tên chuẩn của mã cũ thì thay theo mã mới; cán bộ đã sửa tay (thêm "Chi tiết") thì giữ.
    const tenCu = state.nganhTheoMa.get(input.value.trim());
    if (!ten.value.trim() || ten.value.trim() === tenCu) ten.value = state.nganhTheoMa.get(ma) || ten.value;
    input.value = ma;
    anGoiY(input);
    showError(input);
    markUnsaved();
  }
  function onMaKeydown(e) {
    const input = e.target;
    if (input.dataset?.col !== "ma") return;
    const list = goiYCua(input);
    if (!list || list.hidden) return;
    const options = [...list.children];
    const cur = options.findIndex((li) => li.classList.contains("on"));
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const next = (cur + (e.key === "ArrowDown" ? 1 : -1) + options.length) % options.length;
      options.forEach((li, i) => { li.classList.toggle("on", i === next); li.setAttribute("aria-selected", String(i === next)); });
      options[next].scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (options[cur]) chonMa(input, options[cur].dataset.ma);
    } else if (e.key === "Escape") {
      anGoiY(input);
    }
  }
  function onNganhInput(e) {
    const input = e.target;
    const row = input.closest(".row-card");
    if (!row || input.dataset.col !== "ma") return;
    hienGoiY(input);
    // Gõ đủ 4 số mà không chọn trong danh sách: tên trống thì vẫn tự điền theo mã.
    const ten = row.querySelector('[data-col="ten"]');
    const known = state.nganhTheoMa.get(input.value.trim());
    if (known && !ten.value.trim()) ten.value = known;
  }
  const nganhRows = () => [...$("nganhRows").children].map((row) => ({
    ten: row.querySelector('[data-col="ten"]').value.trim(),
    ma: row.querySelector('[data-col="ma"]').value.trim(),
    chinh: row.querySelector('input[name="nganhChinh"]').checked,
  }));

  // ── Bảng thành viên ──
  const THANH_VIEN_COT = [
    ["hoTen", "Họ tên", "wide", "maxlength=120"],
    ["ngaySinh", "Ngày, tháng, năm sinh", "", 'data-kind="ngayQuaKhu" placeholder="ngày/tháng/năm" maxlength=10'],
    ["soDinhDanh", "Số định danh cá nhân", "", 'data-kind="dinhDanh" inputmode="numeric" maxlength=20'],
    ["gioiTinh", "Giới tính", "", "maxlength=10"],
    ["quocTich", "Quốc tịch", "", "maxlength=60"],
    ["danToc", "Dân tộc", "", "maxlength=60"],
    ["noiThuongTru", "Nơi thường trú", "wide", "maxlength=300"],
    ["noiOHienTai", "Nơi ở hiện tại", "wide", "maxlength=300"],
  ];
  function renumberThanhVien() {
    [...$("thanhVienRows").children].forEach((row, i) => { row.querySelector(".row-no").textContent = `Thành viên ${i + 1}`; });
  }
  function addThanhVien(data = {}) {
    if ($("thanhVienRows").children.length >= MAX_THANH_VIEN) return toast(`Tối đa ${MAX_THANH_VIEN} thành viên.`);
    const row = document.createElement("div");
    row.className = "row-card";
    row.innerHTML = `
      <div class="row-hd"><span class="row-no"></span><button class="link-btn row-rm" type="button">Bỏ dòng này</button></div>
      <div class="fields two">${THANH_VIEN_COT.map(([key, label, wide, attrs]) => `
        <div class="field ${wide}"><label>${label}</label><input data-col="${key}" ${attrs} value="${esc(data[key])}"><small class="err"></small></div>`).join("")}
      </div>`;
    $("thanhVienRows").appendChild(row);
    renumberThanhVien();
    return row;
  }
  const thanhVienRows = () => [...$("thanhVienRows").children].map((row) => Object.fromEntries(
    THANH_VIEN_COT.map(([key]) => [key, row.querySelector(`[data-col="${key}"]`).value.trim()])));

  // Gán value bằng code không bị maxlength của ô chặn, mà ghép ba phần có thể vượt giới hạn 300 của BE.
  const diaChiChuHo = (addr) => [addr.chiTiet, addr.xa, addr.tinh].filter(Boolean).join(", ").slice(0, 300);
  function addChuHoRow() {
    const d = readForm();
    if (!d.hoTen) {
      toast("Chưa có họ tên chủ hộ.");
      return $("hoTen").focus();
    }
    addThanhVien({
      hoTen: d.hoTen, ngaySinh: d.ngaySinh, soDinhDanh: d.soDinhDanh, gioiTinh: d.gioiTinh, quocTich: d.quocTich,
      danToc: d.danToc, noiThuongTru: diaChiChuHo(d.thuongTru), noiOHienTai: diaChiChuHo(d.noiO),
    });
    markUnsaved();
  }

  // ── Đọc form thành dữ liệu gửi BE ──
  function setPath(target, path, value) {
    const [head, tail] = path.split(".");
    if (tail) (target[head] ||= {})[tail] = value;
    else target[head] = value;
  }
  function readForm() {
    const data = {};
    document.querySelectorAll("#form [data-f]").forEach((el) => {
      setPath(data, el.dataset.f, el.type === "checkbox" ? el.checked : el.value.trim());
    });
    data.nganh = nganhRows();
    data.vonKinhDoanh = lib.dongVon($("vonSo").value, $("vonChu").value);
    data.phuongPhapThue = document.querySelector('input[name="phuongPhapThue"]:checked')?.value || "";
    data.chuThe = document.querySelector('input[name="chuThe"]:checked')?.value || "";
    data.thanhVien = data.chuThe === "ho_gia_dinh" ? thanhVienRows() : [];
    return data;
  }

  // ── Gọi BE ──
  // backendFetch đọc phản hồi bằng res.text(): file nhị phân qua đó là hỏng, nên render fetch thẳng. Hết hạn token
  // thì gọi /auth/me để apiCall tự làm mới rồi gửi lại.
  async function renderFile(format, data) {
    const body = JSON.stringify({ format, ...data });
    const send = async () => {
      const tokens = await AuthStore.getTokens();
      return fetch(`${activeBackendBase()}${API}/render`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${tokens?.accessToken || ""}` },
        body,
      });
    };
    let res = await send();
    if (res.status === 401) {
      await apiJson("/auth/me");
      res = await send();
    }
    if (res.status === 404) throw new Error("Máy chủ chưa có tính năng này, cần cập nhật máy chủ");
    if (!res.ok) throw new Error(`Máy chủ báo lỗi (HTTP ${res.status})`);
    const name = /filename="([^"]+)"/.exec(res.headers.get("content-disposition") || "")?.[1] || `To_khai_ho_kinh_doanh.${format}`;
    return { blob: await res.blob(), name };
  }
  function handleError(prefix, error) {
    if (error?.unauthorized) return showAuthGate();
    toast(`${prefix}: ${error?.message || error}`);
  }

  // Trả true khi đã hiện bản mới. Lượt gọi cũ hơn về sau (bấm Lưu liên tiếp) thì bỏ, không đè bản mới.
  async function refreshPreview(data) {
    const seq = ++state.previewSeq;
    $("previewState").textContent = "Đang cập nhật…";
    try {
      const { blob } = await renderFile("pdf", data);
      if (seq !== state.previewSeq) return false;
      if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
      state.previewUrl = URL.createObjectURL(blob);
      $("preview").src = `${state.previewUrl}#toolbar=0&navpanes=0&view=FitH`;
      return true;
    } catch (error) {
      if (seq !== state.previewSeq) return false;
      if (error?.unauthorized) showAuthGate();
      else toast(`Chưa cập nhật được bản xem trước: ${error?.message || error}`);
      $("previewState").textContent = "Chưa cập nhật được bản xem trước, bấm Lưu để thử lại";
      return false;
    }
  }

  // ── Lưu: kiểm ô → Auto Fill → bản xem trước, một lần ──
  function markUnsaved() {
    state.dirty = true;
    if (state.unsaved) return;
    state.unsaved = true;
    $("saveBtn").dataset.unsaved = "true";
    $("previewState").textContent = "Có thay đổi chưa lưu, bấm Lưu để cập nhật";
    showAutoFillState();
  }
  async function saveAll(button, { quiet = false } = {}) {
    if (!validateAll()) return false;
    const data = readForm();
    let ok = false;
    await withButton(button, async () => {
      // Ghi cho Auto Fill trước: bản xem trước lỗi mạng thì Auto Fill vẫn có đúng bản cán bộ vừa lưu.
      await saveForAutoFill(data);
      ok = await refreshPreview(data);
    });
    if (!ok) return false;
    state.unsaved = false;
    delete $("saveBtn").dataset.unsaved;
    $("previewState").textContent = `Đã lưu lúc ${lib.gioPhut(Date.now())}`;
    showAutoFillState();
    if (!quiet) toast(state.savedAt ? "Đã lưu. Bản xem trước và Auto Fill dùng thông tin này." : "Đã lưu bản xem trước.");
    return true;
  }

  function saveBlob({ blob, name }) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }
  async function withButton(button, job) {
    button.disabled = true;
    try {
      await job();
    } finally {
      button.disabled = false;
    }
  }
  async function download(format, button) {
    if (!validateAll()) return;
    if (state.unsaved && !(await saveAll($("saveBtn"), { quiet: true }))) return;
    await withButton(button, async () => {
      try {
        saveBlob(await renderFile(format, readForm()));
        toast(format === "docx" ? "Đã tải file Word. Mở ra kiểm tra rồi in cho công dân ký." : "Đã tải file PDF.");
      } catch (error) {
        handleError(`Không tạo được file ${format === "docx" ? "Word" : "PDF"}`, error);
      }
    });
  }
  async function downloadBlank(button) {
    await withButton(button, async () => {
      try {
        saveBlob(await renderFile("docx", {}));
        toast("Đã tải mẫu trống.");
      } catch (error) {
        handleError("Không tải được mẫu trống", error);
      }
    });
  }
  async function printForm(button) {
    if (!validateAll()) return;
    if (state.unsaved && !(await saveAll($("saveBtn"), { quiet: true }))) return;
    await withButton(button, async () => {
      try {
        const { blob } = await renderFile("pdf", readForm());
        const url = URL.createObjectURL(blob);
        // In đúng file PDF vừa dựng (không in trang HTML này). Khung ẩn không in được thì mở tab PDF.
        const frame = document.createElement("iframe");
        frame.style.cssText = "position:fixed;width:0;height:0;border:0;right:0;bottom:0";
        frame.onload = () => {
          try {
            frame.contentWindow.focus();
            frame.contentWindow.print();
          } catch (_) {
            window.open(url, "_blank");
          }
          setTimeout(() => { frame.remove(); URL.revokeObjectURL(url); }, 60000);
        };
        frame.src = url;
        document.body.appendChild(frame);
      } catch (error) {
        handleError("Không tạo được bản in", error);
      }
    });
  }

  // ── Chuyển cho Auto Fill (chỉ khi bấm Lưu; data đã qua validateAll nên BE không trả 400) ──
  async function saveForAutoFill(data) {
    if (!sessionStore || state.gateShown) return;
    try {
      if (!lib.coNoiDung(data)) {
        await sessionStore.remove(lib.KHOA_AUTO_FILL);
        state.savedAt = 0;
        return;
      }
      const savedAt = Date.now();
      await sessionStore.set({ [lib.KHOA_AUTO_FILL]: {
        data, ten: lib.tenToKhai(data), tabId: state.tabId, savedAt,
      } });
      state.savedAt = savedAt;
    } catch (error) {
      console.warn("[Tờ khai HKD] Không chuyển được cho Auto Fill:", error);
      toast("Không chuyển được tờ khai cho Auto Fill, bấm Lưu lại.");
    }
  }
  function forgetForAutoFill() {
    state.savedAt = 0;
    try { void sessionStore?.remove(lib.KHOA_AUTO_FILL); } catch (_) { /* tab đang đóng */ }
  }
  function showAutoFillState() {
    const el = $("autoFillState");
    if (!el) return;
    if (!sessionStore) {
      el.textContent = "Trình duyệt này chưa hỗ trợ chuyển tờ khai cho Auto Fill, Auto Fill sẽ quét giấy như thường.";
      el.dataset.ready = "false";
      return;
    }
    const ready = !!state.savedAt && !state.unsaved;
    el.dataset.ready = ready ? "true" : "false";
    if (ready) {
      el.textContent = "✓ Đã chuyển cho Auto Fill. Trên trang hokinhdoanh.dkkd.gov.vn bấm \"⚡ Quét nhập thông tin và đính kèm\": Auto Fill điền 8 trang theo tờ khai này, không cần quét tờ khai.";
    } else if (state.savedAt) {
      el.textContent = `Có thay đổi chưa lưu. Auto Fill đang giữ bản lưu lúc ${lib.gioPhut(state.savedAt)}; bấm Lưu để Auto Fill điền theo thông tin mới.`;
    } else {
      el.textContent = "Điền hết thông tin rồi bấm Lưu ở đầu trang: bản xem trước cập nhật và Auto Fill dùng luôn để điền cổng, không cần quét tờ khai.";
    }
  }

  // ── Làm lại ──
  function applyDefaults() {
    $("diaDanh").value = state.config.diaDanh || "";
    $("ngayLap").value = state.config.today || "";
    $("kinhGui").value = state.config.kinhGui || "";
  }
  function resetAll() {
    if (!confirm("Xóa hết thông tin đã nhập, làm lại từ đầu?")) return;
    $("form").reset();
    $("nganhRows").innerHTML = "";
    $("thanhVienRows").innerHTML = "";
    document.querySelectorAll("#form .invalid").forEach((el) => el.classList.remove("invalid"));
    document.querySelectorAll("#form details").forEach((el) => { el.open = false; });
    addNganh();
    syncThanhVienBox();
    state.vonChuTuDoc = true;
    state.dirty = false;
    state.unsaved = false;
    delete $("saveBtn").dataset.unsaved;
    applyDefaults();
    forgetForAutoFill();
    showAutoFillState();
    void showBlankPreview();
  }
  // Mở tab / làm lại: bản xem trước là mẫu với mấy ô điền sẵn theo tài khoản (địa danh, ngày lập, kính gửi).
  async function showBlankPreview() {
    if (await refreshPreview(readForm())) $("previewState").textContent = "Điền hết thông tin rồi bấm Lưu để cập nhật";
  }
  function syncThanhVienBox() {
    const family = document.querySelector('input[name="chuThe"]:checked')?.value === "ho_gia_dinh";
    $("thanhVienBox").hidden = !family;
  }

  function wire() {
    const form = $("form");
    form.addEventListener("submit", (e) => e.preventDefault());
    form.addEventListener("input", (e) => {
      const input = e.target;
      if (input.closest("#nganhRows")) onNganhInput(e);
      if (input.dataset.kind && input.closest(".field")?.classList.contains("invalid")) showError(input);
      markUnsaved();
    });
    form.addEventListener("change", (e) => {
      if (e.target.name === "chuThe") {
        syncThanhVienBox();
        if (e.target.value === "ho_gia_dinh" && !$("thanhVienRows").children.length) addThanhVien();
      }
      markUnsaved();
    });
    form.addEventListener("focusout", (e) => {
      const input = e.target;
      if (!(input instanceof HTMLInputElement) || !input.dataset.kind) return;
      const before = input.value;
      normalizeInput(input);
      showError(input);
      if (before !== input.value) markUnsaved();
    });
    form.addEventListener("click", (e) => {
      const clear = e.target.closest("[data-clear]");
      if (clear) {
        document.querySelectorAll(`input[name="${clear.dataset.clear}"]`).forEach((el) => { el.checked = false; });
        syncThanhVienBox();
        markUnsaved();
        return;
      }
      const copy = e.target.closest("[data-copy]");
      if (copy) {
        const [from, to] = copy.dataset.copy.split(">");
        ["chiTiet", "xa", "tinh"].forEach((part) => {
          document.querySelector(`[data-f="${to}.${part}"]`).value = document.querySelector(`[data-f="${from}.${part}"]`).value;
        });
        markUnsaved();
        return;
      }
      const remove = e.target.closest(".row-rm");
      if (remove) {
        const row = remove.closest(".row-card");
        const wasMain = row.querySelector('input[name="nganhChinh"]')?.checked;
        const box = row.parentElement;
        row.remove();
        if (box.id === "thanhVienRows") renumberThanhVien();
        if (box.id === "nganhRows") {
          if (!box.children.length) addNganh();
          if (wasMain) box.querySelector('input[name="nganhChinh"]').checked = true;
        }
        markUnsaved();
      }
    });
    $("addNganh").addEventListener("click", () => { addNganh()?.querySelector('[data-col="ma"]').focus(); });
    $("nganhRows").addEventListener("keydown", onMaKeydown);
    // mousedown (không phải click): chọn trước khi ô mã mất focus làm danh sách đóng.
    $("nganhRows").addEventListener("mousedown", (e) => {
      const li = e.target.closest(".ma-goi-y li");
      if (!li) return;
      e.preventDefault();
      chonMa(li.closest(".ma-search").querySelector('[data-col="ma"]'), li.dataset.ma);
    });
    $("nganhRows").addEventListener("focusin", (e) => { if (e.target.dataset?.col === "ma") hienGoiY(e.target); });
    $("nganhRows").addEventListener("focusout", (e) => { if (e.target.dataset?.col === "ma") anGoiY(e.target); });
    $("addThanhVien").addEventListener("click", () => { addThanhVien()?.querySelector('[data-col="hoTen"]').focus(); });
    $("addChuHo").addEventListener("click", addChuHoRow);

    $("vonSo").addEventListener("input", (e) => {
      e.target.value = lib.dinhDangTien(e.target.value);
      if (state.vonChuTuDoc) $("vonChu").value = lib.docTienBangChu(e.target.value);
    });
    $("vonChu").addEventListener("input", (e) => { state.vonChuTuDoc = !e.target.value.trim(); });

    $("saveBtn").addEventListener("click", (e) => void saveAll(e.currentTarget));
    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && !e.altKey && e.key.toLowerCase() === "s") {
        e.preventDefault(); // Ctrl+S quen tay: lưu tờ khai thay vì hộp thoại lưu trang của trình duyệt
        if (!$("saveBtn").disabled && !state.gateShown) void saveAll($("saveBtn"));
      }
    });
    $("printBtn").addEventListener("click", (e) => void printForm(e.currentTarget));
    $("downloadWord").addEventListener("click", (e) => void download("docx", e.currentTarget));
    $("downloadPdf").addEventListener("click", (e) => void download("pdf", e.currentTarget));
    $("blankWord").addEventListener("click", (e) => void downloadBlank(e.currentTarget));
    $("resetAll").addEventListener("click", resetAll);
    $("closeTab").addEventListener("click", () => window.close());

    // Tự cập nhật: background hỏi từng tab có đang làm việc không rồi mới nạp lại extension. Nạp lại là ĐÓNG tab này,
    // mất tờ khai đang soạn, nên báo bận khi đã gõ, kể cả lúc cán bộ quay sang trang cổng một lúc.
    let lastActivity = Date.now();
    ["pointerdown", "keydown", "input"].forEach((ev) =>
      document.addEventListener(ev, () => { lastActivity = Date.now(); }, { capture: true, passive: true }));
    chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
      if (msg?.action !== "hccTabDangLamViec") return;
      const busy = state.dirty && Date.now() - lastActivity < BUSY_KEEP_MS;
      sendResponse({ coPanel: busy, focus: busy, an: false, imLangMs: busy ? 0 : Date.now() - lastActivity });
    });
    window.addEventListener("beforeunload", (e) => {
      if (state.dirty) e.preventDefault();
    });
    // Đóng tab là hết tờ khai: không để Auto Fill điền nhầm tờ khai cũ cho hồ sơ sau. Popup còn kiểm tab sống.
    window.addEventListener("pagehide", forgetForAutoFill);
  }

  async function init() {
    wire();
    addNganh();
    syncThanhVienBox();
    showAutoFillState();
    try { state.tabId = (await chrome.tabs.getCurrent())?.id ?? null; } catch (_) { state.tabId = null; }
    const tokens = await AuthStore.getTokens();
    if (!tokens?.accessToken) return showAuthGate();
    try {
      state.config = { ...state.config, ...(await apiJson(`${API}/config`)) };
    } catch (error) {
      if (error?.unauthorized) return showAuthGate();
      toast(error?.status === 404 ? "Máy chủ chưa có tính năng này, cần cập nhật máy chủ." : `Không tải được cấu hình: ${error?.message || error}`);
    }
    applyDefaults();
    const nganh = state.config.nganh || [];
    state.nganhTheoMa = new Map(nganh.map((item) => [item.ma, item.ten]));
    void showBlankPreview();
  }

  void init();
})();
