// Cổng Lai Châu (dichvucong.laichau.gov.vn, eForm Nth đời cũ): MỖI BƯỚC là một trang riêng (bấm "Đồng ý và tiếp tục"
// là tải hẳn trang mới), tiêu đề trang ghi "Bước N - <tên bước>". Phần trang của luồng do BE điều phối (chat/lai_chau):
//   - lcStep: số bước đọc từ tiêu đề (2 Thông tin người nộp, 3 Thành phần hồ sơ, 4 Lệ phí hồ sơ…); trang "Trường hợp nộp
//     hồ sơ" (chon-truong-hop-ho-so, tiêu đề không ghi bước) = 1; 0 = không phải trang nộp hồ sơ của cổng này;
//   - đọc / chọn ô chọn theo name BE gửi: trang 1 "Cơ quan giải quyết hồ sơ" (maCoQuan) + "Trường hợp giải quyết"
//     (maQttt, select2); bước 4 "Hình thức nhận kết quả" (maHinhThucNhanKetQua) + "Mức lệ phí" (loaiLePhi_<mã loại>).
//     Ô chưa chọn mà chỉ có một lựa chọn thì chọn luôn; bước 4 nhận kết quả tại nhà mà ô địa chỉ trống thì bấm "Lấy
//     địa chỉ của Người nộp" (cổng chép Tỉnh / Phường-Xã / Số nhà của bước 2), ô "Số lượng" trống thì để 1;
//   - bấm "Đồng ý và tiếp tục" (#btn-next) rồi đọc lời cổng báo nếu bị chặn (hộp thoại Nth.Alert hoặc lỗi dưới ô
//     p.form-error).
// Ô chọn là <select> thường: đặt value + bắn change là đủ (handler jQuery của cổng nhận sự kiện gốc).
(() => {
  if (window.__TLND_LAICHAU_PORTAL__) return;
  window.__TLND_LAICHAU_PORTAL__ = true;
  const H = (window.__TLND__ = window.__TLND__ || {});

  const HOST = "dichvucong.laichau.gov.vn";
  const RESULT = "maHinhThucNhanKetQua";
  const FEE = "loaiLePhi";
  // Ô địa chỉ nhận kết quả (cổng chỉ hiện khi nhận kết quả về địa chỉ, ẩn khi "Đến cơ quan giải quyết").
  const ADDRESS = ["phuongXaNhanKetQua_quanHuyen_maTinhThanh", "maPhuongXaNhanKetQua", "diaChiNhanKetQua"];
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const fold = (s) => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/gi, "d").replace(/\s+/g, " ").trim().toLowerCase();
  const textOf = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  const shown = (el) => !!el && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== "hidden";
  const sameText = (a, b) => fold(a).replace(/[.\s]+$/, "") === fold(b).replace(/[.\s]+$/, "");
  const ourPage = () => location.hostname === HOST && location.pathname.includes("/tiep-nhan-online/");

  const CASE_PAGE = "/chon-truong-hop-ho-so";

  function step() {
    if (!ourPage()) return 0;
    if (location.pathname.includes(CASE_PAGE)) return 1;
    const match = /^buoc\s+(\d+)\s*-/.exec(fold(document.title));
    return match ? Number(match[1]) : 0;
  }
  H.laiChauStep = step;

  function control(name) {
    if (name === FEE) {
      const fees = Array.from(document.querySelectorAll(`select[name^="${FEE}_"]`));
      return fees.find(shown) || fees[0] || null;
    }
    return document.querySelector(`[name="${CSS.escape(name)}"]`);
  }

  const realOptions = (select) => Array.from(select?.options || []).filter((o) => o.value !== "" && textOf(o));
  const selectedText = (select) => {
    const option = select?.selectedOptions?.[0];
    return option && option.value !== "" ? textOf(option) : "";
  };

  function fire(el) {
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function setSelect(select, text) {
    const option = realOptions(select).find((o) => sameText(textOf(o), text));
    if (!option) return false;
    if (select.value !== option.value) {
      select.value = option.value;
      option.selected = true;
      fire(select);
    }
    return select.value === option.value;
  }

  function readGroup(group) {
    const select = control(group.name);
    if (!select || !shown(select)) return { name: group.name, present: false };
    if (select.tagName !== "SELECT") return { name: group.name, present: true, value: String(select.value || ""), fixed: true };
    const locked = select.disabled || select.hasAttribute("readonly");
    const options = locked ? [] : realOptions(select).map(textOf);
    return { name: group.name, present: true, value: selectedText(select), options, fixed: locked || !options.length };
  }

  const readGroups = (groups) => (groups || []).map(readGroup);

  // ── Địa chỉ nhận kết quả + số lượng ──

  const addressShown = () => shown(control("diaChiNhanKetQua"));
  const addressEmpty = () => !String(control("diaChiNhanKetQua")?.value || "").trim();

  async function pullApplicantAddress() {
    const button = document.querySelector('button[data-action="get-address-from-user"]');
    if (!button || !shown(button)) return false;
    button.click();
    for (let waited = 0; waited < 3000 && addressEmpty(); waited += 150) await sleep(150);
    await sleep(600); // cổng nạp lại danh sách phường/xã theo tỉnh rồi mới chọn xã
    return !addressEmpty();
  }

  // Ô bắt buộc (dấu (*) cạnh nhãn) của khối địa chỉ đang hiện mà còn trống → nhãn để trợ lý nhắc.
  function missingAddress() {
    const out = [];
    for (const name of ADDRESS) {
      const el = control(name);
      if (!el || !shown(el) || String(el.value || "").trim()) continue;
      const label = document.getElementById(`_lbl_${name}`);
      if (label && !label.querySelector(".mandatory")) continue;
      out.push(textOf(label?.querySelector(".label-content")) || name);
    }
    return out;
  }

  function fixQuantity() {
    const box = Array.from(document.querySelectorAll('input[name^="soLuong_"]')).find(shown);
    if (!box || box.readOnly || box.disabled || Number(String(box.value).replace(/\D/g, "")) >= 1) return false;
    box.value = "1";
    fire(box);
    return true;
  }

  // Ô chọn chưa có giá trị mà cổng chỉ cho đúng một lựa chọn → chọn luôn ("auto:<name>").
  function autoPickSingle(groups) {
    const prepared = [];
    for (const group of groups || []) {
      const select = control(group.name);
      if (!select || select.tagName !== "SELECT" || !shown(select) || select.value) continue;
      const options = realOptions(select);
      if (options.length === 1 && setSelect(select, textOf(options[0]))) prepared.push(`auto:${group.name}`);
    }
    return prepared;
  }

  // Lần đọc đầu: làm sẵn những việc không cần hỏi công dân.
  async function prepare(groups) {
    const prepared = [];
    if (fixQuantity()) prepared.push("quantity");
    const result = control(RESULT);
    if (result && result.value !== "0" && addressShown() && addressEmpty() && await pullApplicantAddress()) {
      prepared.push("address");
    }
    prepared.push(...autoPickSingle(groups));
    return prepared;
  }

  async function scan(msg) {
    const prepared = msg.prepare === false ? [] : await prepare(msg.groups);
    return { groups: readGroups(msg.groups), missing: missingAddress(), prepared };
  }

  async function setGroup(msg) {
    let ok = false;
    const prepared = [];
    try {
      ok = setSelect(control(msg.name), msg.value);
      // Cổng hiện / ẩn khối địa chỉ theo cách nhận; chọn trường hợp thì nạp lại ô nơi nộp phụ thuộc (AJAX).
      if (ok) await sleep(800);
      if (ok && msg.name === RESULT && addressShown() && addressEmpty() && await pullApplicantAddress()) {
        prepared.push("address");
      }
      if (ok) prepared.push(...autoPickSingle(msg.groups));
    } catch (e) {
      console.warn("[TLND] Lai Châu: đổi ô chọn lỗi:", e);
    }
    return { ok, groups: readGroups(msg.groups), missing: missingAddress(), prepared };
  }

  // ── Đồng ý và tiếp tục ──

  const DIALOGS = ".modal.in, .modal.show, .bootbox, [role=dialog]";
  const dialogText = () => Array.from(document.querySelectorAll(DIALOGS)).filter(shown)
    .map((box) => textOf(box.querySelector(".modal-body, .bootbox-body") || box)).find(Boolean) || "";
  // Ô chặn hiện lời ngay dưới ô (Nth Component.showMessage → p.form-error).
  const fieldErrors = () => Array.from(document.querySelectorAll("p.form-error")).filter(shown)
    .map(textOf).filter(Boolean).join("; ");

  async function moveNext() {
    const button = document.getElementById("btn-next")
      || Array.from(document.querySelectorAll("button, a.btn")).find((b) => fold(textOf(b)) === "dong y va tiep tuc");
    if (!button || !shown(button) || button.disabled) return { clicked: false, message: "" };
    const before = dialogText();
    const beforeErrors = fieldErrors();
    button.click();
    // Hợp lệ thì cổng tải trang mới (script này mất theo trang); bị chặn thì hiện hộp thoại hoặc lời dưới ô.
    for (let waited = 0; waited < 5000; waited += 200) {
      await sleep(200);
      const text = dialogText();
      if (text && text !== before) return { clicked: true, message: text.slice(0, 200) };
      const errors = fieldErrors();
      if (errors && errors !== beforeErrors) return { clicked: true, message: errors.slice(0, 200) };
    }
    return { clicked: true, message: "" };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = String(msg?.action || "");
    if (!action.startsWith("lc") || !ourPage()) return;
    const run = { lcResultScan: () => scan(msg), lcResultSet: () => setGroup(msg), lcNext: moveNext }[action];
    if (!run) return;
    run().then(sendResponse).catch((e) => sendResponse({ ok: false, clicked: false, error: String(e?.message || e) }));
    return true;
  });
})();
