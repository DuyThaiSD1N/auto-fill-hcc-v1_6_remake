// Chặng cuối trên trang nộp một trang của cổng Bộ VHTTDL (dichvucong.bvhttdl.gov.vn, form liz). BE điều phối ở
// chat/tu_phap_moi.py (registry lizFlow), extension khai supportsLizFlow:
//   - selectResultMethod: tích ô cam kết (nút "Lưu và nộp hồ sơ" của cổng chỉ mở sau khi tích), gạt ô "Đề nghị nhận
//     kết quả bản giấy tại nhà qua Bưu chính công ích (VNPost)" theo postOffice; tích thì cổng mọc khối người nhận
//     (recipient_*) → điền theo khối "Thông tin người nộp hồ sơ", báo ô đã điền / ô bắt buộc còn trống;
//   - guidedSubmit: tích lại ô cam kết, soát ô bắt buộc đang hiện, chờ nút nộp mở rồi bấm, đọc thông báo lỗi của cổng.
// Trang khác (DVCQG SurveyJS, cổng bộ iGate…) có engine riêng → ở đây im lặng.
(() => {
  if (window.__TLND_LIZ_ONE_PAGE__) return;
  window.__TLND_LIZ_ONE_PAGE__ = true;
  const H = (window.__TLND__ = window.__TLND__ || {});

  const HOST = "dichvucong.bvhttdl.gov.vn";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const textOf = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  const cleanLabel = (s) => String(s || "").replace(/\*/g, "").replace(/\s+/g, " ").trim();
  const fold = (s) => cleanLabel(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d");
  const shown = (el) => !!el && el.getClientRects().length > 0;
  const ourPage = () => location.hostname === HOST && H.detectFormKind?.() === "liz";
  H.isLizOnePage = ourPage;

  async function waitFor(fn, timeout, step = 150) {
    for (let waited = 0; waited <= timeout; waited += step) {
      const value = fn();
      if (value) return value;
      await sleep(step);
    }
    return fn();
  }

  // Ô cam kết hiện HAI lần (đầu và cuối trang), không id/name → khớp theo chữ của <label> bọc ô.
  function commitBoxes(label) {
    const want = fold(label).slice(0, 40);
    if (!want) return [];
    return Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter((input) => fold(textOf(input.closest("label"))).includes(want));
  }

  // Hai ô có thể cùng một model (tích ô này cổng tự tích ô kia) → xét lại từng ô ngay trước khi bấm.
  async function tickCommit(label) {
    const boxes = commitBoxes(label);
    if (!boxes.length) return false;
    for (const box of boxes) {
      if (box.checked || box.disabled) continue;
      box.click();
      await waitFor(() => box.checked, 1000);
      await sleep(150);
    }
    return boxes.every((box) => box.checked);
  }

  const fieldOf = (control) => control?.closest("mat-form-field") || null;
  const valueOf = (mf) => {
    if (!mf) return "";
    if (mf.querySelector("mat-select")) {
      return cleanLabel(textOf(mf.querySelector(".mat-mdc-select-value-text, .mat-select-value-text")));
    }
    return String(mf.querySelector("input, textarea")?.value || "").trim();
  };
  const labelOf = (mf) => cleanLabel(textOf(mf?.querySelector("mat-label")));

  // Ô của khối "Thông tin người nộp hồ sơ" theo đầu nhãn (nhãn đầy đủ: "Tên người nộp / Tên đơn vị"…).
  function applicantValue(prefix) {
    for (const group of document.querySelectorAll(".group")) {
      if (!fold(textOf(group.querySelector(".group-header"))).includes("thong tin nguoi nop")) continue;
      for (const mf of group.querySelectorAll("mat-form-field")) {
        if (fold(labelOf(mf)).startsWith(prefix)) return valueOf(mf);
      }
    }
    return "";
  }

  // Khối người nhận mọc khi tích VNPost: nguồn lấy từ khối người nộp; ô đã có giá trị thì giữ.
  const RECIPIENT = [
    { selector: 'input[name="recipient_name"]', from: "ten nguoi nop" },
    { selector: 'input[name="recipient_phone"]', from: "so dien thoai" },
    { selector: 'input[name="recipient_address"]', from: "dia chi chi tiet" },
    { selector: 'mat-select[name="recipient_commune_id"]', from: "dia chi hanh chinh" },
  ];

  const invalid = (mf) => {
    const input = mf.querySelector("input");
    return !!input && !!String(input.value || "").trim() && input.validity && !input.validity.valid;
  };

  // Ô bắt buộc đang hiện mà trống (hoặc sai mẫu, vd số điện thoại người nhận) — nhãn để BE đọc lên.
  function requiredEmpty(root = document) {
    const out = [];
    for (const mf of root.querySelectorAll("mat-form-field")) {
      if (!shown(mf) || mf.closest(".cdk-overlay-container")) continue;
      const control = mf.querySelector("mat-select") || mf.querySelector("input, textarea");
      if (!control || control.disabled || control.getAttribute("aria-disabled") === "true") continue;
      const required = !!mf.querySelector(".mat-mdc-form-field-required-marker, .mat-form-field-required-marker")
        || control.required || control.getAttribute("aria-required") === "true";
      if (required && (!valueOf(mf) || invalid(mf))) out.push(labelOf(mf) || cleanLabel(control.getAttribute("name")));
    }
    return out.filter(Boolean);
  }

  async function fillRecipient() {
    const filled = [];
    const fields = [];
    for (const spec of RECIPIENT) {
      const mf = fieldOf(document.querySelector(spec.selector));
      if (!mf) continue;
      fields.push(mf);
      const source = applicantValue(spec.from);
      if (valueOf(mf) || !source || typeof H.fillLizFieldElement !== "function") continue;
      try {
        if (await H.fillLizFieldElement(mf, source) === "ok" && valueOf(mf)) filled.push(labelOf(mf));
      } catch (e) {
        console.warn("[TLND] điền người nhận liz lỗi:", e);
      }
    }
    const missing = fields.filter((mf) => !valueOf(mf) || invalid(mf)).map(labelOf).filter(Boolean);
    return { filled, missing };
  }

  async function selectResultMethod(msg) {
    const commit = msg.commitLabel ? await tickCommit(msg.commitLabel) : undefined;
    if (typeof msg.postOffice !== "boolean") return { ok: true, commit, filled: [], missing: [] };
    const box = document.querySelector('input[type="checkbox"][name="post_office"]');
    if (!box) return { ok: false, commit, error: "Không thấy ô nhận kết quả qua Bưu chính công ích (VNPost)." };
    if (box.checked !== msg.postOffice) {
      box.click();
      await waitFor(() => box.checked === msg.postOffice, 1500);
    }
    if (box.checked !== msg.postOffice) return { ok: false, commit, error: "Ô VNPost không đổi trạng thái." };
    if (!msg.postOffice) return { ok: true, commit, filled: [], missing: [] };
    const appeared = await waitFor(() => document.querySelector('input[name="recipient_name"]'), 3000);
    if (!appeared) return { ok: true, commit, filled: [], missing: [] };
    await sleep(300);
    return { ok: true, commit, ...(await fillRecipient()) };
  }

  const submitButton = () => Array.from(document.querySelectorAll("button.style_btn"))
    .filter((b) => shown(b) && fold(textOf(b)).includes("luu va nop ho so"));

  // Thông báo cổng nháy lên sau khi bấm (snackbar / toast / hộp thoại) — chữ "thành công" không phải lỗi.
  function portalMessage() {
    const nodes = document.querySelectorAll("mat-snack-bar-container, .mat-mdc-snack-bar-container, simple-snack-bar, "
      + ".toast-container .toast, .toast-message, .swal2-popup, mat-dialog-container, .mat-mdc-dialog-container");
    for (const node of nodes) {
      const text = textOf(node);
      if (shown(node) && text && !fold(text).includes("thanh cong")) return text.slice(0, 300);
    }
    return "";
  }

  async function submit(msg) {
    const commit = msg.commitLabel ? await tickCommit(msg.commitLabel) : true;
    const missing = requiredEmpty();
    if (missing.length) return { ok: false, clicked: false, missing };
    const button = await waitFor(() => submitButton().find((b) => !b.disabled), 5000);
    if (!button) {
      return {
        ok: false, clicked: false,
        message: commit ? "Nút Lưu và nộp hồ sơ của cổng vẫn đang khoá."
          : "Chưa tích được ô cam kết nên nút Lưu và nộp hồ sơ của cổng còn khoá.",
      };
    }
    button.click();
    const message = await waitFor(portalMessage, 2500);
    return { ok: !message, clicked: true, message };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = String(msg?.action || "");
    if (!["selectResultMethod", "guidedSubmit"].includes(action) || !ourPage()) return;
    const run = action === "selectResultMethod" ? selectResultMethod(msg) : submit(msg);
    run.then(sendResponse).catch((e) => sendResponse({ ok: false, clicked: false, error: String(e?.message || e) }));
    return true; // async
  });
})();
