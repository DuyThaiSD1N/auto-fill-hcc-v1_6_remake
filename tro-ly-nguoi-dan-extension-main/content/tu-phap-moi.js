// tu-phap-moi.js — phần trang của luồng "tư pháp mới": trang nộp MỘT TRANG của Cổng DVC quốc gia
// (dichvucong.gov.vn/nop-ho-so) chứa cả form SurveyJS, bảng thành phần hồ sơ, ô "Hình thức nhận kết
// quả" và nút "Lưu và nộp hồ sơ". Trả lời ba lệnh sidebar đã có sẵn khi đứng trên trang này:
//   - attachFilesByPlan  → engine "Tải lên file" (content/fill-surveyjs.js)
//   - selectResultMethod → chọn option của dropdown cc-select (không phải công tắc như cổng tư pháp)
//   - guidedSubmit       → soát ô bắt buộc (form + khối bưu điện), đủ mới bấm "Lưu và nộp hồ sơ"
// Các engine cũ (attach-core / portal-dvc / guided-steps) tự im trên trang này.
(() => {
  if (window.__TLND_TU_PHAP_MOI__) return;
  window.__TLND_TU_PHAP_MOI__ = true;

  const H = (window.__TLND__ = window.__TLND__ || {});
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const isVisible = (el) => (typeof H.isVisible === "function" ? H.isVisible(el) : !!el?.offsetParent);
  const fold = (s) => String(s ?? "")
    .replace(/Đ/g, "D").replace(/đ/g, "d")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().replace(/\s+/g, " ").trim();
  const plainText = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  const onPage = () => typeof H.isSurveyDossierPage === "function" && H.isSurveyDossierPage();

  // React mở dropdown theo mousedown/pointerdown chứ không chỉ click → bấm như người thật.
  function clickLikeUser(el) {
    for (const type of ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]) {
      try {
        el.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }));
      } catch (_) { el.click(); return; }
    }
  }

  // ── Ô "Hình thức nhận kết quả" (cc-select tự viết, không id/name, nằm ngoài form SurveyJS) ──
  // Khối nhận kết quả qua bưu điện còn một cc-select khác ("Thanh toán lệ phí") → neo theo nhãn.
  function resultSelectWrapper() {
    const title = Array.from(document.querySelectorAll("span, label, div, p"))
      .find((el) => !el.children.length && isVisible(el) && fold(el.textContent) === "hinh thuc nhan ket qua");
    let node = title;
    for (let i = 0; node && i < 5; i++) {
      node = node.parentElement;
      const wrapper = node?.querySelector(".cc-select-wrapper");
      if (wrapper) return wrapper;
    }
    return null;
  }

  function selectedLabel(wrapper) {
    const el = wrapper?.querySelector(".cc-select-selected-label");
    return String(el?.getAttribute("title") || el?.textContent || "").trim();
  }

  // Danh sách option chỉ dựng khi mở; markup option không có trong snapshot → khớp phần tử đang hiện
  // có chữ ĐÚNG nhãn, sâu nhất, ngoài ô đang chọn (ô đó cũng hiện đúng chữ của option đang chọn).
  function findOption(label) {
    const want = fold(label);
    return Array.from(document.querySelectorAll('[role="option"], li, div, span'))
      .filter((el) => isVisible(el) && fold(el.textContent) === want && !el.closest(".cc-select-selector"))
      .find((el) => !Array.from(el.children).some((child) => fold(child.textContent) === want)) || null;
  }

  async function chooseResultMethod(label) {
    const wrapper = resultSelectWrapper();
    if (!wrapper) return { ok: false, error: "Không thấy ô Hình thức nhận kết quả trên trang." };
    const want = fold(label);
    for (let round = 0; round < 2; round++) {
      if (fold(selectedLabel(wrapper)) === want) return { ok: true };
      clickLikeUser(wrapper.querySelector(".cc-select-selector") || wrapper.querySelector(".cc-select") || wrapper);
      let option = null;
      for (let i = 0; i < 10 && !option; i++) {
        await sleep(150);
        option = findOption(label);
      }
      if (option) {
        clickLikeUser(option);
        await sleep(300);
      } else {
        document.activeElement?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      }
    }
    return fold(selectedLabel(wrapper)) === want
      ? { ok: true }
      : { ok: false, error: "Chọn option mà ô Hình thức nhận kết quả không đổi." };
  }

  // ── Khối "THÔNG TIN NHẬN KẾT QUẢ" (chỉ hiện khi chọn bưu điện) — trợ lý chỉ kiểm, không điền hộ ──
  // id lấy từ DOM thật của cổng; ô chọn (đơn vị vận chuyển, tỉnh, xã) là nút listbox, còn trống thì
  // hiện chữ mờ "Chọn … *".
  const POSTAL_FIELDS = [
    "id-recipientName", "id-recipientPhone", "partnerCode",
    "recipientProvinceCode", "recipientComuneCode", "id-recipientAddress",
  ];

  function postalFieldState(el) {
    if (el.tagName === "INPUT") {
      const label = plainText(document.querySelector(`label[for="${CSS.escape(el.id)}"]`));
      return { empty: !String(el.value || "").trim(), label, box: el.parentElement };
    }
    const shown = el.querySelector("span");
    const text = plainText(shown);
    const tooltip = plainText(el.closest(".input-with-tooltip")?.querySelector(".tooltip-text"));
    const empty = !text || /\*\s*$/.test(text) || !!shown?.classList?.contains("text-gray-400");
    const label = (tooltip || text).replace(/^chọn\s+/i, "");
    return { empty, label: label.charAt(0).toUpperCase() + label.slice(1), box: el.parentElement };
  }

  function postalMissing({ mark = false } = {}) {
    const missing = [];
    let first = null;
    for (const id of POSTAL_FIELDS) {
      const el = document.getElementById(id);
      if (!el || !isVisible(el)) continue;
      const state = postalFieldState(el);
      if (!state.empty) {
        if (mark) state.box?.removeAttribute("data-tlnd-mark");
        continue;
      }
      missing.push(state.label.replace(/\s*\*\s*$/, "").trim() || id);
      first = first || el;
      if (mark && typeof H.setSurveyJsMark === "function") {
        H.injectSurveyJsMarkStyles?.();
        H.setSurveyJsMark(state.box, "not-filled");
      }
    }
    return { missing, first };
  }

  async function selectResultMethodOnPage({ label, needsInput }) {
    const res = await chooseResultMethod(label);
    if (!res.ok || !needsInput) return { ...res, missing: [] };
    await sleep(600); // React dựng khối nhận kết quả của cách vừa chọn
    return { ok: true, missing: postalMissing({ mark: true }).missing };
  }

  // ── Nộp: soát trước, đủ mới bấm "Lưu và nộp hồ sơ" ──
  function submitButton() {
    return Array.from(document.querySelectorAll("button"))
      .find((el) => isVisible(el) && fold(el.textContent) === "luu va nop ho so") || null;
  }

  function toastTexts() {
    return Array.from(document.querySelectorAll('.Toastify__toast, [role="alert"]'))
      .filter((el) => isVisible(el))
      .map((el) => plainText(el))
      .filter(Boolean);
  }

  async function submitDossier() {
    const required = typeof H.markEmptyRequired === "function"
      ? await H.markEmptyRequired({ force: true })
      : { names: [], labels: [], firstEl: null };
    const missing = [...required.labels];
    let first = required.firstEl;
    if (fold(selectedLabel(resultSelectWrapper())).includes("buu dien")) {
      const postal = postalMissing({ mark: true });
      missing.push(...postal.missing);
      first = first || postal.first;
    }
    if (missing.length) {
      first?.scrollIntoView?.({ block: "center" });
      return { ok: false, clicked: false, missing, message: "" };
    }
    const button = submitButton();
    if (!button || button.disabled) return { ok: false, clicked: false, message: "" };
    const before = new Set(toastTexts());
    button.scrollIntoView({ block: "center" });
    button.click();
    // Cổng báo lỗi bằng toast tự tắt sau vài giây → rình một lúc chứ không đọc một lần.
    let message = "";
    for (let i = 0; i < 15 && !message; i++) {
      await sleep(200);
      const fresh = toastTexts().find((text) => !before.has(text)) || "";
      if (fresh && !fold(fresh).includes("thanh cong")) message = fresh.slice(0, 200);
      else if (fresh) break;
    }
    return { ok: !message, clicked: true, message };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = msg?.action;
    if (!["attachFilesByPlan", "selectResultMethod", "guidedSubmit"].includes(action)) return;
    // Frame/trang khác IM để engine cũ của trang đó trả lời (content script chạy ở mọi frame).
    if (!onPage()) return;
    let job;
    if (action === "attachFilesByPlan") {
      const files = Array.isArray(msg.files) ? msg.files : [];
      const attachments = Array.isArray(msg.attachments) ? msg.attachments : [];
      if (!files.length) { sendResponse({ error: "Không có file nào để đính kèm." }); return; }
      if (!attachments.length) { sendResponse({ error: "Không có kế hoạch đính kèm từ backend." }); return; }
      job = H.attachSurveyJsByPlan(files, attachments);
    } else if (action === "selectResultMethod") {
      job = selectResultMethodOnPage(msg);
    } else {
      job = submitDossier();
    }
    Promise.resolve(job)
      .then(sendResponse)
      .catch((e) => sendResponse({ ok: false, clicked: false, error: String(e?.message || e) }));
    return true; // async
  });
})();
