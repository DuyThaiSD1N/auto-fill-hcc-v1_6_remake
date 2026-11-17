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
// Cổng DVC Bộ Công an (dichvucong.bocongan.gov.vn — đăng ký xe) cùng nền eForm Nth: BE chỉ dùng trang 1 và gửi nhóm ô
// "*" = tự dò MỌI ô chọn đang hiện trong khung chứa nút "Đồng ý và tiếp tục" (Loại xe, rồi các ô cổng hiện thêm sau khi
// chọn); nhãn lấy ở #_lbl_<name> .label-content, dấu (*) (.mandatory) = bắt buộc. Ô bị bootstrap-select / select2 che
// (thẻ <select> gốc ẩn) vẫn tính là đang hiện.
(() => {
  if (window.__TLND_LAICHAU_PORTAL__) return;
  window.__TLND_LAICHAU_PORTAL__ = true;
  const H = (window.__TLND__ = window.__TLND__ || {});

  const HOSTS = ["dichvucong.laichau.gov.vn", "dichvucong.bocongan.gov.vn"];
  const AUTO = "*";
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
  const ourPage = () => HOSTS.includes(location.hostname) && location.pathname.includes("/tiep-nhan-online/");
  // Ô chọn bị bootstrap-select / select2 che: thẻ <select> gốc ẩn, khung công dân thấy nằm ở wrapper / ngay sau.
  const controlShown = (el) => shown(el) || shown(el?.closest?.(".bootstrap-select"))
    || (el?.nextElementSibling?.classList?.contains("select2") && shown(el.nextElementSibling));
  // Nhóm radio (Bộ Công an: "Loại biển số"): radio tự vẽ có ô gốc ẩn, nhãn hiện.
  const isRadio = (el) => el?.tagName === "INPUT" && el.type === "radio";
  const radioShown = (r) => shown(r) || shown(r.closest("label")) || shown(r.parentElement);
  const radiosOf = (name) => Array.from(document.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`))
    .filter(radioShown);
  // Khối riêng của MỘT lựa chọn radio (cổng Bộ Công an: div.form-group.radio#cachThucHien1 chứa ô + nhãn
  // #_lbl_cachThucHien1) — chỉ tính khi khối đó chứa đúng một ô radio (khối chứa cả nhóm thì nhãn trong đó là nhãn ô).
  function optionBox(radio) {
    const box = radio.closest(".radio, .form-group");
    return box && box.querySelectorAll("input[type='radio']").length === 1 ? box : null;
  }

  function radioText(radio) {
    const own = radio.id ? document.querySelector(`label[for="${CSS.escape(radio.id)}"]`) : null;
    const box = optionBox(radio);
    const text = textOf(own) || textOf(radio.closest("label"))
      || textOf(box && Array.from(box.querySelectorAll("label")).find((l) => !l.contains(radio)));
    if (text) return text;
    let node = radio.nextSibling;
    while (node && node.nodeType === 3 && !node.textContent.trim()) node = node.nextSibling;
    return (node?.nodeType === 3 ? node.textContent.replace(/\s+/g, " ").trim() : textOf(node)) || String(radio.value || "");
  }

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

  // ── select2 nạp danh sách khi mở (ô "Điểm đăng ký"): mở một nhịp để đọc / chọn rồi đóng ──
  const lazyOptions = new Map();
  const select2Of = (select) => (select?.nextElementSibling?.classList?.contains("select2") ? select.nextElementSibling : null);
  const openResults = () => Array.from(document.querySelectorAll(".select2-container--open .select2-results__option"))
    .filter((li) => !li.classList.contains("loading-results") && !li.classList.contains("select2-results__message")
      && li.getAttribute("aria-disabled") !== "true" && textOf(li));

  async function openSelect2(select) {
    const box = select2Of(select);
    const handle = box?.querySelector(".select2-selection") || box;
    if (!handle || select.disabled) return false;
    handle.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    for (let waited = 0; waited < 2500 && !openResults().length; waited += 150) await sleep(150);
    return openResults().length > 0;
  }

  function closeSelect2() {
    const search = document.querySelector(".select2-container--open .select2-search__field");
    (search || document.activeElement || document.body)
      .dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", keyCode: 27, which: 27, bubbles: true }));
    if (document.querySelector(".select2-container--open")) {
      document.body.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    }
  }

  async function loadLazy(groups) {
    for (const group of resolve(groups)) {
      const select = control(group.name);
      if (!select || select.tagName !== "SELECT" || select.disabled || realOptions(select).length || !select2Of(select)
        || !controlShown(select)) continue;
      try {
        if (await openSelect2(select)) lazyOptions.set(group.name, [...new Set(openResults().map(textOf))].slice(0, 400));
      } finally {
        closeSelect2();
      }
      await sleep(150);
    }
  }

  async function pickSelect2(select, text) {
    try {
      if (!(await openSelect2(select))) return false;
      const item = openResults().find((li) => sameText(textOf(li), text));
      if (!item) return false;
      item.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
      await sleep(150);
      if (document.querySelector(".select2-container--open")) item.click();
      await sleep(300);
      return sameText(selectedText(select) || textOf(select2Of(select)?.querySelector(".select2-selection__rendered")), text);
    } finally {
      closeSelect2();
    }
  }

  // Ô chọn (kể cả select2 nạp khi mở) hoặc nhóm radio: chọn đúng lựa chọn có chữ `text`.
  async function setControl(name, text) {
    const el = control(name);
    if (!el) return false;
    if (isRadio(el)) {
      const radio = radiosOf(name).find((r) => sameText(radioText(r), text));
      if (!radio || radio.disabled) return false;
      // iCheck (cổng Bộ Công an): ô gốc trong suốt, lớp ins.iCheck-helper phủ trên — iCheck CHẶN click thẳng vào ô gốc,
      // phải bấm lớp phủ (iCheck tự tích, đổi giao diện, bắn sự kiện cho cổng). Không có thì bấm nhãn, rồi tới ô.
      const helper = radio.parentElement?.querySelector("ins.iCheck-helper");
      const label = radio.id ? document.querySelector(`label[for="${CSS.escape(radio.id)}"]`) : null;
      for (const target of [helper, label, radio]) {
        if (radio.checked || !target) continue;
        target.click();
        await sleep(150);
      }
      if (!radio.checked) {
        radio.checked = true;
        fire(radio);
      }
      return radio.checked;
    }
    if (setSelect(el, text)) return true;
    return select2Of(el) ? pickSelect2(el, text) : false;
  }

  function readGroup(group) {
    const select = control(group.name);
    if (select && isRadio(select)) {
      const radios = radiosOf(group.name);
      if (!radios.length) return { name: group.name, present: false };
      const locked = radios.every((r) => r.disabled);
      const checked = radios.find((r) => r.checked);
      const options = locked ? [] : radios.map(radioText).filter(Boolean);
      return { name: group.name, present: true, value: checked ? radioText(checked) : "", options,
        fixed: locked || !options.length };
    }
    if (!select || !controlShown(select)) return { name: group.name, present: false };
    if (select.tagName !== "SELECT") return { name: group.name, present: true, value: String(select.value || ""), fixed: true };
    const locked = select.disabled || select.hasAttribute("readonly");
    const native = realOptions(select).map(textOf);
    // select2 nạp khi mở: chọn xong thẻ <select> gốc chỉ còn đúng mục vừa chọn → giữ danh sách đã đọc lúc mở.
    const lazy = lazyOptions.get(group.name) || [];
    const options = locked ? [] : (native.length > 1 || !lazy.length ? native : lazy);
    const value = selectedText(select)
      || (select2Of(select) && !native.length ? lazyValue(select) : "");
    return { name: group.name, present: true, value, options, fixed: locked || !options.length };
  }

  // ── Tự dò ô (nhóm "*") ──

  const nextButton = () => document.getElementById("btn-next")
    || Array.from(document.querySelectorAll("button, a.btn")).find((b) => fold(textOf(b)) === "dong y va tiep tuc");

  // Khung chọn trường hợp: tổ tiên gần nhất của nút "Đồng ý và tiếp tục" có ô chọn (bỏ ô chọn ngôn ngữ đầu trang).
  function caseRoot() {
    for (let node = nextButton()?.parentElement; node && node !== document.body; node = node.parentElement) {
      if (node.querySelector("select[name], input[type='radio'][name]")) return node;
    }
    return document.querySelector("form") || document.body;
  }

  const cleanLabel = (s) => String(s || "").replace(/\(\s*\*\s*\)|\*/g, "").replace(/[:\s]+$/, "").trim();

  // Nhãn của MỘT lựa chọn radio (bọc ô / for= ô radio) không phải nhãn của ô.
  const optionLabel = (label) => !!label.querySelector("input")
    || isRadio(label.htmlFor ? document.getElementById(label.htmlFor) : null);

  // Nhãn của nhóm radio mà mỗi lựa chọn nằm một khối riêng: nhãn gần nhất phía trước khối lựa chọn đầu, không nằm
  // trong khối lựa chọn nào, giữa nhãn và nhóm không có ô khác (ảnh 17/11: "Loại biển số (*)" ở cột trước hai cột lựa chọn).
  function radioGroupLabel(radio) {
    const group = radiosOf(radio.getAttribute("name") || "");
    const boxes = group.map(optionBox).filter(Boolean);
    const first = boxes[0] || radio;
    let level = 0;
    for (let node = first.parentElement; node && level < 4; node = node.parentElement, level += 1) {
      const labels = Array.from(node.querySelectorAll("label, .control-label")).filter((l) => textOf(l)
        && !boxes.some((b) => b.contains(l)) && !optionLabel(l) && (l.compareDocumentPosition(first) & 4));
      const label = labels[labels.length - 1];
      if (!label) continue;
      const between = Array.from(node.querySelectorAll("select, input:not([type='hidden'])")).some((c) => !group.includes(c)
        && (label.compareDocumentPosition(c) & 4) && (c.compareDocumentPosition(first) & 4));
      return between ? null : label;
    }
    return null;
  }

  function labelFor(select) {
    const name = select.getAttribute("name") || "";
    if (isRadio(select) && !document.getElementById(`_lbl_${name}`) && optionBox(select)) {
      const own = radioGroupLabel(select);
      const required = !!own && (!!own.querySelector(".mandatory") || /\*/.test(textOf(own)));
      return { label: cleanLabel(textOf(own?.querySelector(".label-content") || own)) || name, required };
    }
    const own = document.getElementById(`_lbl_${name}`)
      || (select.id && !isRadio(select) ? document.querySelector(`label[for="${CSS.escape(select.id)}"]`) : null)
      || Array.from(select.closest(".form-group")?.querySelectorAll("label") || []).find((l) => !optionLabel(l));
    const text = cleanLabel(textOf(own?.querySelector(".label-content") || own));
    const required = select.required || (!!own && (!!own.querySelector(".mandatory") || /\*/.test(textOf(own))));
    return { label: text || name, required };
  }

  function discover() {
    const seen = new Set();
    const out = [];
    for (const el of caseRoot().querySelectorAll("select[name], input[type='radio'][name]")) {
      const name = el.getAttribute("name");
      if (seen.has(name) || !(isRadio(el) ? radiosOf(name).length : controlShown(el))) continue;
      seen.add(name);
      out.push({ name, ...labelFor(el) });
    }
    return out;
  }

  // Chữ đang hiện của select2 nạp khi mở (thẻ <select> gốc chưa có option nào): bỏ dòng gợi ý "-- Chưa chọn --".
  function lazyValue(select) {
    const text = textOf(select2Of(select)?.querySelector(".select2-selection__rendered")).replace(/^×\s*/, "");
    return !text || /^-+\s*chua chon|^-+\s*chon|^chon\b/.test(fold(text)) ? "" : text;
  }

  // Chọn một ô, cổng tải thêm ô / nạp lại danh sách qua AJAX (ảnh 17/11: ~1,5 giây sau mới hiện Loại biển số, Điểm
  // đăng ký…) → chờ tới khi khung chọn trường hợp không đổi DOM 1 giây (tối thiểu 2 giây, tối đa 6 giây); cổng chậm hơn
  // nữa thì lưới đỡ watchCase báo đọc lại.
  async function settle() {
    const root = caseRoot();
    let lastChange = Date.now();
    const observer = new MutationObserver(() => { lastChange = Date.now(); });
    observer.observe(root, { subtree: true, childList: true, attributes: true, characterData: true });
    const start = Date.now();
    try {
      while (Date.now() - start < 6000) {
        await sleep(200);
        if (Date.now() - start >= 2000 && Date.now() - lastChange >= 1000) break;
      }
    } finally {
      observer.disconnect();
    }
  }

  // Lưới đỡ trang chọn trường hợp tự dò: ô đổi SAU lượt đọc (cổng tải chậm hơn mốc chờ, công dân tự chọn trên trang) →
  // báo sidebar để trợ lý đọc lại, hiện thẻ đúng các ô đang có. Chỉ bật sau khi BE đã xin đọc tự dò.
  let caseWatching = false;
  let caseBusy = 0;
  let caseReported = "";
  const caseSig = () => JSON.stringify(readGroups([{ name: AUTO }]).map((g) => [g.name, g.present, g.value]));
  function watchCase() {
    if (caseWatching || !location.pathname.includes(CASE_PAGE)) return;
    caseWatching = true;
    let timer = null;
    const changed = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        if (caseBusy) return;
        const sig = caseSig();
        if (sig === caseReported) return;
        caseReported = sig;
        try {
          chrome.runtime.sendMessage({ __tlnd: "lcCaseChanged" }, () => void chrome.runtime.lastError);
        } catch (_) { /* extension vừa reload */ }
      }, 1500);
    };
    new MutationObserver(changed).observe(caseRoot(), { subtree: true, childList: true, attributes: true });
    document.addEventListener("change", changed, true);
  }

  // Lượt đọc / chọn của trợ lý: tạm dừng lưới đỡ, xong thì ghi lại các ô vừa báo.
  async function caseTurn(groups, run) {
    const auto = (groups || []).some((g) => g?.name === AUTO);
    caseBusy += 1;
    try {
      return await run();
    } finally {
      caseBusy -= 1;
      if (auto) {
        caseReported = caseSig();
        watchCase();
      }
    }
  }

  const resolve = (groups) => ((groups || []).some((g) => g?.name === AUTO) ? discover() : (groups || []));

  const readGroups = (groups) => resolve(groups).map((group) => ({
    ...readGroup(group),
    ...(group.label ? { label: group.label, required: !!group.required } : {}),
  }));

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
    for (const group of resolve(groups)) {
      const select = control(group.name);
      if (!select || select.tagName !== "SELECT" || !controlShown(select) || select.value) continue;
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
    if (prepared.some((x) => x.startsWith("auto:"))) await settle();
    await loadLazy(msg.groups);
    return { groups: readGroups(msg.groups), missing: missingAddress(), prepared };
  }

  async function setGroup(msg) {
    let ok = false;
    const prepared = [];
    try {
      ok = await setControl(msg.name, msg.value);
      // Cổng hiện / ẩn khối địa chỉ theo cách nhận; chọn trường hợp thì nạp lại ô nơi nộp phụ thuộc (AJAX) — chờ đứng yên.
      if (ok) await settle();
      if (ok && msg.name === RESULT && addressShown() && addressEmpty() && await pullApplicantAddress()) {
        prepared.push("address");
      }
      // Ô chỉ một lựa chọn chọn luôn; chọn xong cổng có thể hiện thêm ô → lặp vài vòng.
      for (let round = 0; ok && round < 3; round += 1) {
        const picked = autoPickSingle(msg.groups);
        if (!picked.length) break;
        prepared.push(...picked);
        await settle();
      }
      if (ok) await loadLazy(msg.groups);
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
  const fieldErrors = () => [...document.querySelectorAll("p.form-error"),
    // Cổng Bộ Công an: jQuery validate / toastr / sweetalert.
    ...document.querySelectorAll("label.error, span.error, .help-block.error, .has-error .help-block, .toast-message, "
      + ".swal2-html-container, .jconfirm-content")].filter(shown).map(textOf).filter(Boolean).join("; ");

  // Trang chọn trường hợp tự dò: ô bắt buộc (dấu (*)) đang hiện mà còn trống.
  const emptyRequired = () => discover().filter((g) => g.required)
    .filter((g) => { const got = readGroup(g); return got.present && !got.value; }).map((g) => g.label);

  async function moveNext() {
    const button = nextButton();
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
    // Trang vẫn đứng yên, cổng không nói gì: trang chọn trường hợp còn ô bắt buộc trống thì báo đúng các ô đó.
    const missing = location.pathname.includes(CASE_PAGE) ? emptyRequired() : [];
    if (missing.length) return { clicked: true, message: `Còn trống: ${missing.join(", ")}`, missing };
    return { clicked: true, message: "" };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = String(msg?.action || "");
    if (!action.startsWith("lc") || !ourPage()) return;
    const run = {
      lcResultScan: () => caseTurn(msg.groups, () => scan(msg)),
      lcResultSet: () => caseTurn(msg.groups, () => setGroup(msg)),
      lcNext: moveNext,
    }[action];
    if (!run) return;
    run().then(sendResponse).catch((e) => sendResponse({ ok: false, clicked: false, error: String(e?.message || e) }));
    return true;
  });
})();
