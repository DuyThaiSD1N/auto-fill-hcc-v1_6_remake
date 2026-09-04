// Engine fill cho cổng dịch vụ công tỉnh BẮC NINH (Liferay portlet + select2 + jQuery).
// Nền tảng RIÊNG, khác hẳn 3 engine cũ (legacy moj / Angular / standard):
//   - Field đơn là `_org_bn_hoso_noptructuyen_element_<id>`, id đổi theo eform → KHÔNG khớp
//     theo name/id mà khớp theo NHÃN (thuộc tính `title` của chính input, = <label>).
//   - Dropdown dùng select2 (cần set option + trigger change; cascade tự nạp con).
//   - Đính kèm: mỗi thành phần hồ sơ có checkbox `thanhPhanHoSo<id>` + input file
//     `filethanhPhanHoSobanChinh<id>KhongKySo` (bản chính, không ký số).
// Tách riêng theo yêu cầu: mọi thứ Bắc Ninh gói gọn ở file này, giao tiếp qua window.__HCC__.
(() => {
  const H = window.__HCC__ || (window.__HCC__ = {});

  const PFX = "_org_bn_hoso_noptructuyen_";
  // Portlet KHÁC: trang hoàn thiện tài khoản VNeID SSO (/vneidsso) — ô là input/select portlet THƯỜNG
  // (`_org_bn_taikhoan_sso_vneid_INSTANCE_<rnd>_<key>`), KHÔNG có eform-element/element_ → khớp NAME suffix.
  const BN_ACCOUNT_MARK = "_taikhoan_sso_vneid_";

  // Fold dấu + hạ chữ thường + gộp khoảng trắng (tự chứa, không phụ thuộc helper chưa export).
  const fold = (s) =>
    String(s || "")
      .replace(/Đ/g, "D")
      .replace(/đ/g, "d")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      // Đồng nhất mọi dấu gạch (–—‐‑-) → space: tên xã sáp nhập "Phường X – Đà Lạt" (OCR
      // ra en-dash) vs option "… - …" (hyphen) mới khớp được ở select cascade Tỉnh/Xã.
      .replace(/\s*[-–—‐‑]+\s*/g, " ")
      .trim()
      .toLowerCase()
      .replace(/\s+/g, " ");

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // Nhận diện form Bắc Ninh: có field portlet đặc trưng (chỉ cổng này dùng prefix đó).
  function isBacNinhForm() {
    return document.querySelectorAll(`[name^="${PFX}"]`).length >= 3;
  }

  // Nhãn của 1 ô đơn: ưu tiên title của chính input, fallback sang <label for=...>.
  function elementLabel(el) {
    let t = (el.getAttribute("title") || "").trim();
    if (!t && el.id) {
      try {
        const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
        if (lbl) t = (lbl.getAttribute("title") || lbl.textContent || "").trim();
      } catch { /* id lạ ký tự → bỏ qua */ }
    }
    return t;
  }

  // Tất cả ô đơn có thể điền (input text/number + textarea), bỏ file/checkbox/radio/hidden.
  function collectFormElements() {
    const nodes = document.querySelectorAll(
      `input[name^="${PFX}element_"], textarea[name^="${PFX}element_"]`,
    );
    const out = [];
    for (const el of nodes) {
      const type = (el.getAttribute("type") || "text").toLowerCase();
      if (["file", "checkbox", "radio", "hidden"].includes(type)) continue;
      out.push({ el, labelFold: fold(elementLabel(el)) });
    }
    return out;
  }

  // Khớp ô eForm theo CLASS NGỮ NGHĨA ỔN ĐỊNH `eform-element-<Key>` (vd KinhGui, 211ThuaDatSo,
  // CoQuanCapNYC). Bền hơn khớp NHÃN vì nhiều ô trùng title ("Cơ quan cấp"/"cấp ngày"/"Số"). Dùng
  // attribute selector [class~="..."] để né vấn đề escape với key bắt đầu bằng số (211…, 11…).
  function findElementByClass(name) {
    const key = String(name || "").trim();
    if (!key) return null;
    let el = null;
    try {
      el = document.querySelector(
        `input[class~="eform-element-${key}"], textarea[class~="eform-element-${key}"]`,
      );
    } catch { el = null; }
    if (el && /^(input|textarea)$/i.test(el.tagName)) {
      const type = (el.getAttribute("type") || "text").toLowerCase();
      if (!["file", "checkbox", "radio", "hidden"].includes(type)) return el;
    }
    return null;
  }

  // Khớp ô theo NAME cố định (chấp nhận name có hoặc chưa có prefix portlet). Trả input/textarea.
  function findElementByName(name) {
    const raw = String(name || "").trim();
    if (!raw) return null;
    const full = raw.startsWith(PFX) ? raw : PFX + raw;
    for (const sel of [`[name="${full}"]`, `#${CSS.escape(full)}`]) {
      let el = null;
      try { el = document.querySelector(sel); } catch { el = null; }
      if (el && /^(input|textarea)$/i.test(el.tagName)) {
        const type = (el.getAttribute("type") || "text").toLowerCase();
        if (!["file", "checkbox", "radio", "hidden"].includes(type)) return el;
      }
    }
    return null;
  }

  // Khớp ô theo NHÃN, ưu tiên giảm dần:
  //  (1) TRÙNG KHỚP CHÍNH XÁC fold(label) === fold(name) — cho nhãn ngắn/mơ hồ như "(2)"/"(3)".
  //  (2) label BẮT ĐẦU bằng name — chọn nhãn NGẮN NHẤT (khớp sát nhất): vd "c) diện tích" ưu tiên
  //      "c) diện tích (6)" hơn "c) diện tích sàn xây dựng... (13)".
  //  (3) label CHỨA name — cũng chọn ngắn nhất.
  function findElementByLabel(elements, name) {
    const want = fold(name);
    if (!want) return null;
    let exact = null;
    let starts = null, startsLen = Infinity;
    let inc = null, incLen = Infinity;
    for (const item of elements) {
      const lbl = item.labelFold;
      if (!lbl) continue;
      if (lbl === want) { exact = item; break; }
      if (lbl.startsWith(want) && lbl.length < startsLen) { starts = item; startsLen = lbl.length; }
      if (lbl.includes(want) && lbl.length < incLen) { inc = item; incLen = lbl.length; }
    }
    const chosen = exact || starts || inc;
    return chosen ? chosen.el : null;
  }

  // ---- select2 (chỉ dùng nếu BE phát field bn-select; hiện đơn đính chính không cần) ----
  // Set option theo TEXT (fold) trên <select> gốc rồi báo select2/jQuery cập nhật + nạp cascade.
  function fillSelect2ByText(selectEl, value) {
    if (!selectEl) return false;
    const want = fold(value);
    if (!want) return false;
    let picked = null;
    for (const opt of selectEl.options) {
      const t = fold(opt.textContent);
      if (!t) continue;
      if (t === want || t.includes(want) || want.includes(t)) {
        picked = opt;
        if (t === want) break;
      }
    }
    if (!picked) return false;
    selectEl.value = picked.value;
    // select2 lắng nghe change của <select> gốc qua jQuery → phát cả native lẫn jQuery.
    selectEl.dispatchEvent(new Event("change", { bubbles: true }));
    try {
      const jq = window.jQuery || window.$;
      if (jq && jq.fn && jq(selectEl).data("select2")) jq(selectEl).trigger("change");
    } catch { /* không có jQuery thì thôi */ }
    return true;
  }

  // Điền select CÓ CASCADE (vd Xã phụ thuộc Tỉnh): option con nạp qua AJAX sau khi đổi Tỉnh nên
  // có thể CHƯA có ngay. Thử ngay; nếu chưa khớp → chờ và thử lại tới ~2.4s cho tới khi option xuất hiện.
  async function fillSelect2ByTextAsync(selectEl, value, tries = 12, delay = 200) {
    if (!selectEl) return false;
    if (fillSelect2ByText(selectEl, value)) return true;
    for (let i = 0; i < tries; i++) {
      await sleep(delay);
      if (fillSelect2ByText(selectEl, value)) return true;
    }
    return false;
  }

  // Chuẩn hóa giá trị theo KIỂU ô: input type=number chỉ nhận chữ số → bỏ dấu chấm/khoảng trắng
  // (vd SĐT "0395.792.788" → "0395792788"; nếu để nguyên, number input từ chối thành rỗng).
  function coerceForInput(el, value) {
    const type = (el.getAttribute("type") || "").toLowerCase();
    if (type === "number") return String(value == null ? "" : value).replace(/[^\d]/g, "");
    return value;
  }

  // ---- Điền đơn ----
  async function fillFormBacNinh(fields) {
    // Trang hoàn thiện tài khoản VNeID (/vneidsso) dùng portlet khác → engine khớp NAME suffix riêng.
    if (isBacNinhAccountForm()) return fillAccountBacNinh(fields);
    const list = Array.isArray(fields) ? fields : [];
    if (!list.length) return { error: "Không có trường nào để điền." };
    // Nạp CSS đánh dấu (xanh = đã điền) — engine bacninh cũng cần, nếu không markFilled vô hình.
    H.injectAutofillStyles && H.injectAutofillStyles();
    const elements = collectFormElements();
    const filled = [];
    const unmatched = [];

    for (const f of list) {
      const name = f && f.name;
      const value = f && f.value;
      if (!name || value === "" || value == null) continue;
      const comp = String(f.comp || "");

      if (comp === "bn-select") {
        // Địa chỉ Tỉnh/Xã: tìm <select> theo class eform-element-* (ổn định) hoặc cốt name, rồi
        // lái select2. Xã cascade theo Tỉnh → điền BẤT ĐỒNG BỘ (chờ option con nạp xong).
        const target = findSelectForField(name);
        if (target && (await fillSelect2ByTextAsync(target, value))) filled.push(name);
        else unmatched.push(name);
        continue;
      }

      if (comp === "bn-radio") {
        // value = danh sách CỤM NHÃN cần tick; khớp radio theo nhãn kề (không phụ thuộc id/value).
        const wants = Array.isArray(value) ? value : [value];
        if (tickRadiosByLabel(wants)) filled.push(name);
        else unmatched.push(name);
        continue;
      }

      // Thứ tự khớp: (1) CLASS eform-element-<Key> (ổn định, phân biệt được title trùng) →
      // (2) NAME cố định của cổng (vd `nhanTaiNhahoTen`) → (3) NHÃN (title) cho ô thân đơn nhãn duy nhất.
      const el = findElementByClass(name) || findElementByName(name) || findElementByLabel(elements, name);
      if (!el) {
        unmatched.push(name);
        continue;
      }
      try {
        H.setNativeValue(el, coerceForInput(el, value), { typing: true, commit: true });
        H.markFilled && H.markFilled(el);
        filled.push(name);
      } catch (e) {
        unmatched.push(name);
      }
    }

    console.log("[AutoFill-BN] điền đơn:", { filled, unmatched });
    return {
      ok: true,
      method: "bacninh",
      filled: filled.length,
      unmatched,
      total: list.length,
    };
  }

  // ===== [Bắc Ninh] Điền thông tin tài khoản (portlet _taikhoan_sso_vneid_, khớp NAME suffix) =====
  function isBacNinhAccountForm() {
    return document.querySelectorAll(`[name*="${BN_ACCOUNT_MARK}"]`).length >= 3;
  }

  // Khớp ô form tài khoản theo NAME kết thúc bằng `_<key>` (vd hoTen, soCCCD, thuongTrutinhThanhId).
  // Bỏ ô hidden/file/checkbox/radio (có 1 ô hidden trùng tên soDinhDanh). Suffix là DUY NHẤT —
  // `_ngayCap` KHÔNG dính `_ngayCapCCCD`, `_thuongTru` KHÔNG dính `_thuongTrutinhThanhId` (endsWith).
  function findAccountField(key) {
    const k = String(key || "").trim();
    if (!k) return null;
    let nodes;
    try { nodes = document.querySelectorAll(`[name$="_${k}"]`); }
    catch { return null; }
    for (const el of nodes) {
      if (!(el.getAttribute("name") || "").includes(BN_ACCOUNT_MARK)) continue;
      const tag = el.tagName.toLowerCase();
      if (tag === "select") return el;
      if (tag !== "input" && tag !== "textarea") continue;
      const type = (el.getAttribute("type") || "text").toLowerCase();
      if (["hidden", "file", "checkbox", "radio"].includes(type)) continue;
      return el;
    }
    return null;
  }

  async function fillAccountBacNinh(fields) {
    const list = Array.isArray(fields) ? fields : [];
    if (!list.length) return { error: "Không có trường nào để điền." };
    H.injectAutofillStyles && H.injectAutofillStyles();
    const filled = [];
    const unmatched = [];
    // Điền TUẦN TỰ: Tỉnh trước Xã (BE phát đúng thứ tự) để select2 cascade nạp option con kịp.
    for (const f of list) {
      const name = f && f.name;
      const value = f && f.value;
      if (!name || value === "" || value == null) continue;
      const el = findAccountField(name);
      if (!el) { unmatched.push(name); continue; }
      if (String(f.comp || "") === "bn-select" || el.tagName.toLowerCase() === "select") {
        if (await fillSelect2ByTextAsync(el, value)) { H.markFilled && H.markFilled(el); filled.push(name); }
        else unmatched.push(name);
        continue;
      }
      try {
        H.setNativeValue(el, coerceForInput(el, value), { typing: true, commit: true });
        H.markFilled && H.markFilled(el);
        filled.push(name);
      } catch { unmatched.push(name); }
    }
    console.log("[AutoFill-BN] điền tài khoản:", { filled, unmatched });
    return { ok: true, method: "bacninh-account", filled: filled.length, unmatched, total: list.length };
  }

  async function activateBacNinhTab(tabName) {
    const name = String(tabName || "").trim();
    if (!name) return { error: "Thiếu tên phần biểu mẫu Bắc Ninh." };
    const tab = document.querySelector(`li[data-tab-name="${CSS.escape(name)}"]`);
    const link = tab && tab.querySelector("a");
    if (!tab || !link) return { error: `Không thấy phần "${name}" trên biểu mẫu Bắc Ninh.` };
    if (!link.classList.contains("active")) {
      link.click();
      await sleep(250);
    }
    return { ok: true, tabName: name };
  }

  async function fillAuthorizedPersonBacNinh(fields, subjectOption) {
    const optionText = String(subjectOption || "").trim();
    if (!optionText) return { error: "Thiếu loại đối tượng ủy quyền cần chọn." };
    const checkbox = document.querySelector(
      `input[type="checkbox"][name="${PFX}boSungDoituongKhac"]`,
    );
    if (!checkbox) return { error: "Không thấy khối Thông tin trong trường hợp được ủy quyền." };
    setChecked(checkbox);
    const typeSelect = document.querySelector(`select[name="${PFX}loaiDoiTuongKhac"]`);
    if (!typeSelect || !(await fillSelect2ByTextAsync(typeSelect, optionText))) {
      return { error: `Không chọn được đối tượng ủy quyền "${optionText}".` };
    }
    // Đổi loại đối tượng khiến Liferay nạp khối chi tiết bằng AJAX. Chờ ô đầu tiên xuất hiện trước
    // khi fill để tránh trạng thái nút đã bấm nhưng toàn bộ field bị unmatched.
    for (let i = 0; i < 15; i++) {
      if (document.querySelector(`[name="${PFX}doiTuongKhachoTen"]`)) break;
      await sleep(200);
    }
    if (!document.querySelector(`[name="${PFX}doiTuongKhachoTen"]`)) {
      return { error: "Cổng chưa tải xong khối thông tin người được ủy quyền. Vui lòng bấm lại." };
    }
    return fillFormBacNinh(fields);
  }

  const fillAuthorizedElderlyBacNinh = (fields) =>
    fillAuthorizedPersonBacNinh(fields, "Người cao tuổi");

  // Nhãn của 1 radio/checkbox: label[for], hoặc text trong .form-check, hoặc text kề ngay sau input.
  function radioLabelText(input) {
    if (input.id) {
      try {
        const lbl = document.querySelector(`label[for="${CSS.escape(input.id)}"]`);
        if (lbl && lbl.textContent.trim()) return lbl.textContent;
      } catch { /* id lạ → bỏ qua */ }
    }
    const box = input.closest(".form-check, .form-check-inline, label, div");
    if (box && box.textContent.trim()) return box.textContent;
    let sib = input.nextSibling, acc = "";
    while (sib && acc.length < 120) {
      acc += sib.textContent || sib.nodeValue || "";
      sib = sib.nextSibling;
    }
    return acc;
  }

  // Tick các radio/checkbox trên form Bắc Ninh mà NHÃN kề khớp cụm mong muốn. Xét TỪNG want:
  //   - Nếu có ô nhãn TRÙNG KHỚP CHÍNH XÁC (fold(label) === fold(want)) → chỉ tick ô đó. Tránh tick
  //     nhầm option DÀI chứa cụm này, vd "Bên thế chấp" ⊂ "Người đại diện của bên thế chấp, bên nhận…".
  //   - Không có exact → giữ hành vi cũ: tick MỌI ô có nhãn CHỨA cụm (cho phép 1 want tick nhiều checkbox).
  function tickRadiosByLabel(wants) {
    const wantList = (Array.isArray(wants) ? wants : [wants]).map(fold).filter(Boolean);
    if (!wantList.length) return false;
    const inputs = document.querySelectorAll(
      `input[type="radio"][name^="${PFX}"], input[type="checkbox"][name^="${PFX}element_"]`,
    );
    const labeled = [];
    for (const el of inputs) {
      const lbl = fold(radioLabelText(el));
      if (lbl) labeled.push({ el, lbl });
    }
    let hit = 0;
    for (const w of wantList) {
      const exact = labeled.filter((x) => x.lbl === w);
      const targets = exact.length ? exact : labeled.filter((x) => x.lbl.includes(w));
      for (const t of targets) {
        try {
          setChecked(t.el);
          H.markFilled && H.markFilled(t.el.closest(".form-check, label, div") || t.el);
          hit++;
        } catch { /* bỏ qua ô lỗi */ }
      }
    }
    return hit > 0;
  }

  // Tìm <select> Bắc Ninh theo:
  //   (1) class ngữ nghĩa `eform-element-<name>` (vd TinhThuongTru/XaThuongTru) — ỔN ĐỊNH, không
  //       đổi theo eform (khác id/name element_<số>);
  //   (2) fallback: cốt name / title chứa key (dùng cho field tên cố định như nhanTaiNhatinhThanhId).
  function findSelectForField(name) {
    try {
      const byClass = document.querySelector(`select.eform-element-${CSS.escape(name)}`);
      if (byClass) return byClass;
    } catch { /* name có ký tự lạ → bỏ, dùng fallback */ }
    const key = fold(name);
    const selects = document.querySelectorAll(`select[name^="${PFX}"]`);
    for (const s of selects) {
      const shortName = (s.getAttribute("name") || "").replace(PFX, "");
      const title = fold(s.getAttribute("title") || "");
      if (fold(shortName).includes(key) || title.includes(key)) return s;
    }
    return null;
  }

  // ---- Đính kèm theo kế hoạch BE ----
  // Mỗi item: { fileIndex, componentName, slotKey("banChinh"|"banSao"), documentName }.
  // FE khớp NHÓM thành phần theo componentName (substring nhãn đã fold), tick checkbox nhóm,
  // rồi gán file vào ô Bản chính/Bản sao (không ký số) của nhóm.

  // Map id thành phần → text nhóm (để khớp componentName). Lấy từ checkbox `thanhPhanHoSo<id>`.
  function buildComponentIndex() {
    const index = [];
    const checks = document.querySelectorAll(`input[type="checkbox"][name^="${PFX}thanhPhanHoSo"]`);
    for (const cb of checks) {
      const m = (cb.getAttribute("name") || "").match(/thanhPhanHoSo(\d+)$/);
      if (!m) continue;
      const id = m[1];
      // 4 thành phần nằm CHUNG 1 bảng (#thanhPhanHoSoTbl) → KHÔNG đi lên tổ tiên (sẽ trùm cả
      // bảng, dính tên nhóm khác). Mỗi checkbox nằm ở DÒNG TIÊU ĐỀ riêng chứa TÊN thành phần
      // → dùng đúng <tr> gần nhất của checkbox để khớp tên (đã kiểm chứng: text = tên nhóm đó).
      const group = cb.closest("tr") || cb.closest(".form-group, li, div") || cb.parentElement;
      index.push({ id, checkbox: cb, group, textFold: fold(group ? group.textContent : "") });
    }
    return index;
  }

  function findComponentId(index, componentName) {
    const want = fold(componentName);
    if (!want) return null;
    for (const c of index) {
      if (c.textFold.includes(want)) return c;
    }
    return null;
  }

  function fileInputForSlot(id, slotKey) {
    const slot = slotKey === "banSao" ? "banSao" : "banChinh";
    // Ưu tiên ô KHÔNG ký số (upload thường); fallback ô còn lại nếu không có.
    return (
      document.querySelector(`input[type="file"][name="${PFX}filethanhPhanHoSo${slot}${id}KhongKySo"]`) ||
      document.querySelector(`input[type="file"][name*="filethanhPhanHoSo${slot}${id}KhongKySo"]`) ||
      document.querySelector(`input[type="file"][name*="filethanhPhanHoSo${slot}${id}"]`)
    );
  }

  // Tên file đã tải (vd "Giấy chứng nhận QSDĐ.pdf"); loại trừ dòng gợi ý "cho phép .pdf,.docx…".
  const FILENAME_RE = /[^\s,\/\\]{2,}\.(pdf|docx?|xlsx?|pptx?|jpe?g|png|gif)\b/i;

  // Ô (Bản chính/Bản sao) đã có file đính kèm chưa → để BỎ QUA, không đính lại (giống hộ tịch).
  function slotHasFile(input) {
    if (input && input.files && input.files.length) return true;
    const scope = input && (input.closest("tr") || input.closest(".form-group, li, div"));
    if (!scope) return false;
    for (const el of scope.querySelectorAll("a, span, div, td, li, p")) {
      const txt = (el.textContent || "").trim();
      if (!txt) continue;
      const low = fold(txt);
      if (low.includes("dinh dang tep tin") || low.includes("cho phep") || low.includes("kich thuoc toi da")) continue;
      if (FILENAME_RE.test(txt)) return true;
    }
    return false;
  }

  // Đặt 1 checkbox/radio về CHECKED an toàn: ưu tiên native click() (chạy đủ handler + default),
  // CHỈ khi đang unchecked (tránh click lại toggle off); fallback set .checked + change.
  function setChecked(el) {
    if (!el || el.checked) return;
    try { el.click(); } catch { /* bỏ qua */ }
    if (!el.checked) {
      try {
        el.checked = true;
        el.dispatchEvent(new Event("input", { bubbles: true }));
      } catch { /* bỏ qua */ }
    }
    try { el.dispatchEvent(new Event("change", { bubbles: true })); } catch { /* bỏ qua */ }
  }

  function ensureChecked(cb) {
    setChecked(cb);
  }

  async function attachBacNinhByPlan(payloadFiles, attachments, opts = {}) {
    if (window.__AUTOFILL_HCC_ATTACH_BUSY__) {
      return { error: "Đang có lượt đính kèm khác đang chạy, vui lòng đợi hoàn tất." };
    }
    window.__AUTOFILL_HCC_ATTACH_BUSY__ = true;
    try {
      const items = (Array.isArray(attachments) ? attachments : []).filter(Boolean);
      const index = buildComponentIndex();
      if (!index.length) return { error: "Không thấy thành phần hồ sơ trên trang Bắc Ninh." };

      // Gom file theo componentName + slot (nhiều file có thể vào cùng ô Bản chính multiple).
      // Item target="supplementary" (CCCD/ủy quyền/khác — không có slot riêng) gom vào ô đính kèm bổ sung.
      const groups = new Map(); // key = componentName||slot → { comp, slot, files[] }
      const suppEntries = [];
      const errors = [];
      const attachedNames = [];
      const skippedNames = [];

      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        const payload = H.payloadForPlanItem
          ? H.payloadForPlanItem(payloadFiles, item, i)
          : payloadFiles[Number.isInteger(item.fileIndex) ? item.fileIndex : i];
        if (!payload) {
          errors.push(`Không tìm thấy file ${item.fileName || i + 1} trong payload.`);
          continue;
        }
        if (item.target === "supplementary" || !item.componentName) {
          suppEntries.push({ item, payload });
          continue;
        }
        const slot = item.slotKey === "banSao" ? "banSao" : "banChinh";
        const key = `${fold(item.componentName)}||${slot}`;
        if (!groups.has(key)) groups.set(key, { componentName: item.componentName, slot, entries: [] });
        groups.get(key).entries.push({ item, payload });
      }

      for (const g of groups.values()) {
        const comp = findComponentId(index, g.componentName);
        if (!comp) {
          errors.push(`Không khớp thành phần "${g.componentName}".`);
          continue;
        }
        const input = fileInputForSlot(comp.id, g.slot);
        if (!input) {
          errors.push(`Không thấy ô ${g.slot} của thành phần "${g.componentName}".`);
          continue;
        }
        // Đã có file ở ô này rồi → BỎ QUA, không đính lại (tránh trùng khi chạy lại).
        if (slotHasFile(input)) {
          skippedNames.push(...g.entries.map((e) => e.item.documentName || e.item.fileName).filter(Boolean));
          continue;
        }
        ensureChecked(comp.checkbox);
        const files = [];
        for (const e of g.entries) {
          const file = H.dataUrlToFile
            ? H.dataUrlToFile(e.payload, e.item.documentName || "")
            : e.payload;
          if (file) files.push(file);
        }
        if (!files.length) continue;
        const multiple = !!(input.multiple || input.hasAttribute("multiple"));
        const ok = H.setFilesOnInput(input, files, {
          allowMultiple: multiple,
          assumeConsumed: true,
        });
        if (ok) attachedNames.push(...files.map((f) => f.name));
        else errors.push(`Gán file thất bại cho "${g.componentName}".`);
        await H.sleep(150);
      }

      // Ô ĐÍNH KÈM BỔ SUNG (ngoài danh mục) — CCCD/ủy quyền/đơn... vào input fsfile...fileDinhKem.
      if (suppEntries.length) {
        const suppInput = document.querySelector(`input[type="file"][name*="fsfilethanhPhanHoSofileDinhKem"]`)
          || document.querySelector(`input[type="file"][name*="fileDinhKem"]`);
        if (!suppInput) {
          errors.push("Không thấy ô đính kèm bổ sung (fileDinhKem).");
        } else if (slotHasFile(suppInput)) {
          skippedNames.push(...suppEntries.map((e) => e.item.documentName || e.item.fileName).filter(Boolean));
        } else {
          const files = [];
          for (const e of suppEntries) {
            const file = H.dataUrlToFile ? H.dataUrlToFile(e.payload, e.item.documentName || "") : e.payload;
            if (file) files.push(file);
          }
          if (files.length) {
            const ok = H.setFilesOnInput(suppInput, files, { allowMultiple: true, assumeConsumed: true });
            if (ok) attachedNames.push(...files.map((f) => f.name));
            else errors.push("Gán file thất bại cho ô đính kèm bổ sung.");
            await H.sleep(150);
          }
        }
      }

      if (errors.length && !attachedNames.length && !skippedNames.length) {
        return { error: errors.join("; ") };
      }
      return {
        ok: true,
        method: "bacninh",
        attached: attachedNames.length,
        fileNames: attachedNames,
        skipped: skippedNames.length,
        skippedNames,
        errors,
      };
    } catch (e) {
      return { error: `Lỗi đính kèm Bắc Ninh: ${e && e.message ? e.message : e}` };
    } finally {
      window.__AUTOFILL_HCC_ATTACH_BUSY__ = false;
    }
  }

  Object.assign(H, {
    isBacNinhForm,
    isBacNinhAccountForm,
    fillFormBacNinh,
    fillAccountBacNinh,
    activateBacNinhTab,
    fillAuthorizedPersonBacNinh,
    fillAuthorizedElderlyBacNinh,
    attachBacNinhByPlan,
  });
})();
