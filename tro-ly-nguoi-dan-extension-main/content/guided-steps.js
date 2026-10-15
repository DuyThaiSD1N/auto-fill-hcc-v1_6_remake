// guided-steps.js — bấm hộ công dân nút "Bước tiếp theo" / "Gửi hồ sơ" của cổng tư pháp.
//
// Vì sao cần: nút điều hướng nằm CUỐI trang, dưới bảng thành phần hồ sơ dài — công dân lớn
// tuổi cuộn không tới. Trợ lý đặt nút trong khung chat rồi bấm hộ nút thật.
//
// Vì sao phải đọc lại lời cổng báo: khi thiếu dữ liệu, cổng chỉ nháy một toast ở góc màn hình
// (vd "Vui lòng đính kèm đủ Hồ sơ bắt buộc") rồi tự tắt sau vài giây. Không bắt được nó thì
// công dân chỉ thấy "bấm mà không có gì xảy ra".
//
// Xác nhận CHUYỂN BƯỚC THẬT do sidebar làm (đối chiếu wizardStep của getPageContext) — bộ đọc
// thanh bước đã có sẵn một bản duy nhất ở content.js, không nhân bản ở đây.
(() => {
  if (window.__TLND_GUIDED_STEPS__) return;
  window.__TLND_GUIDED_STEPS__ = true;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const fold = (s) => String(s || "")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/đ/gi, "d").replace(/\s+/g, " ").trim().toLowerCase();
  const isVisible = (el) => !!(el && el.offsetParent !== null);
  const plainText = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();

  // id của cổng (ổn định hơn class Tailwind đổi theo build). Bước Thành phần hồ sơ KHÔNG có
  // data-e2e nên phải khai riêng id; data-e2e="btn-next" dùng chung cho cả nút "Bước tiếp
  // theo" (bước 1) lẫn "Gửi hồ sơ" (bước 4) → luôn kiểm chữ trên nút để không bấm nhầm nộp.
  // Nhánh ủy quyền của bước chủ hồ sơ MẤT data-e2e="btn-next" và đổi id — khai tường minh
  // chứ không trông vào nhánh dự phòng button[type=submit].
  const NEXT_SELECTORS = ['button[id^="kt_buoc-tiep-theo"]', "#nop-thu-tuc-b-3",
                          "#nop-thu-tuc-b-3-uy-quyen",
                          'button[data-e2e="btn-next"]', 'button[type="submit"]'];
  const NEXT_TEXTS = ["buoc tiep theo"];
  const SUBMIT_SELECTORS = ["#kt_gui-ho-so", 'button[data-e2e="btn-next"]',
                            'button[type="submit"]'];
  const SUBMIT_TEXTS = ["gui ho so", "nop ho so"];

  function findButton(selectors, texts) {
    const matchesText = (el) => {
      const text = fold(el.textContent);
      return texts.some((wanted) => text.includes(wanted));
    };
    for (const selector of selectors) {
      const found = Array.from(document.querySelectorAll(selector))
        .find((el) => isVisible(el) && matchesText(el));
      if (found) return found;
    }
    return Array.from(document.querySelectorAll("button"))
      .find((el) => isVisible(el) && matchesText(el)) || null;
  }

  // Toast của cổng mount động (không có sẵn trong DOM) + lỗi từng ô của shadcn/ui
  // (p[id$="-form-item-message"], .text-destructive) hiện ngay dưới ô sai.
  const MESSAGE_SELECTORS = ['[role="alert"]', '[class*="toast"]', '[class*="Toast"]',
                             ".alert", 'p[id$="-form-item-message"]', ".text-destructive"];

  function messageNodes() {
    const nodes = [];
    for (const selector of MESSAGE_SELECTORS) {
      for (const el of document.querySelectorAll(selector)) {
        if (isVisible(el) && plainText(el)) nodes.push(el);
      }
    }
    return nodes;
  }

  const snapshotMessages = () => new Set(messageNodes().map((el) => fold(el.textContent)));

  function newMessage(before) {
    for (const el of messageNodes()) {
      const folded = fold(el.textContent);
      // Chỉ lấy thông báo MỚI so với trước khi bấm: trang luôn có sẵn vài node lỗi ẩn/hiện,
      // đọc bừa là báo cho công dân một lỗi cũ không liên quan.
      if (!folded || before.has(folded)) continue;
      // Cổng cũng dùng đúng khung toast đó để báo NỘP THÀNH CÔNG. Đọc nó như lời chặn thì
      // bot sẽ bảo "trang chưa cho chuyển bước" ngay lúc hồ sơ vừa nộp xong.
      if (folded.includes("thanh cong")) continue;
      return plainText(el).slice(0, 200);
    }
    return "";
  }

  // React/Radix mở theo pointerdown chứ không phải click → bấm như người thật.
  function clickLikeUser(el) {
    for (const type of ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]) {
      try {
        el.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }));
      } catch (_) { el.click(); return; }
    }
  }

  async function pressAndWatch(button) {
    const before = snapshotMessages();
    button.scrollIntoView({ block: "center" });
    clickLikeUser(button);
    // Cổng validate rồi mới hiện toast; toast tự tắt nên phải rình chứ không đọc một lần.
    let message = "";
    for (let i = 0; i < 8 && !message; i++) {
      await sleep(200);
      message = newMessage(before);
    }
    return { ok: true, clicked: true, message };
  }

  // ── Bước cuối của Kê khai (eForm tư pháp): "Xem trước" → hộp thoại "Xem tờ khai điện tử" → "Xác nhận" ──
  // Nút Xem trước dùng chung data-e2e="btn-next" với nút Bước tiếp theo → luôn kiểm chữ.
  const PREVIEW_SELECTORS = ["#xem-truoc-to-khai", 'button[data-e2e="btn-next"]'];
  const PREVIEW_TEXTS = ["xem truoc"];
  // Hộp thoại Radix là position:fixed → offsetParent luôn null, isVisible() coi là ẩn. Xét theo khung hiển thị.
  const shown = (el) => !!el && el.getClientRects().length > 0;
  // Tiêu đề thường là "Xem tờ khai điện tử"; nhận cả "Xem trước tờ khai" và alertdialog cho bản cổng khác.
  const isPreviewTitle = (text) => text.includes("xem to khai")
    || (text.includes("xem truoc") && text.includes("to khai"));
  const previewDialog = () => Array.from(document.querySelectorAll('[role="dialog"],[role="alertdialog"]'))
    .find((el) => shown(el) && isPreviewTitle(fold(el.textContent)));

  async function openPreview(button) {
    const watched = await pressAndWatch(button);
    // Cổng dựng bản xem trước (PDF) có lúc quá 10 giây → chờ tới ~20 giây. Cổng đã nháy toast chặn (còn
    // ô bắt buộc trống) thì bản xem trước sẽ không mở → chỉ chờ thêm ~3 giây rồi báo.
    const limit = watched.message ? 12 : 80;
    for (let i = 0; i < limit && !previewDialog(); i++) await sleep(250);
    return { ok: true, opened: !!previewDialog(), message: previewDialog() ? "" : watched.message };
  }

  // Bản xem trước VỪA MỞ (trợ lý bấm hay công dân tự bấm "Xem trước") → báo sidebar để trợ lý sang bước
  // Xác nhận. Chỉ báo lúc chuyển từ đóng sang mở; frame nào có hộp thoại thì frame đó báo.
  let previewWasOpen = false;
  setInterval(() => {
    const open = !!previewDialog();
    if (open && !previewWasOpen) {
      try {
        chrome.runtime.sendMessage({ action: "declarationPreviewSeen" }, () => void chrome.runtime.lastError);
      } catch (_) { /* extension vừa reload → bỏ qua */ }
    }
    previewWasOpen = open;
  }, 800);

  async function confirmPreview(dialog) {
    const button = Array.from(dialog.querySelectorAll("button"))
      .find((el) => isVisible(el) && fold(el.textContent) === "xac nhan")
      || Array.from(dialog.querySelectorAll("button")).find((el) => isVisible(el) && fold(el.textContent).includes("xac nhan"));
    if (!button) return { ok: false, message: "không thấy nút Xác nhận trong bản xem trước" };
    const watched = await pressAndWatch(button);
    return { ok: true, clicked: true, message: watched.message };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = msg?.action;
    if (!["declarationPreview", "declarationConfirm", "declarationPreviewClose"].includes(action)) return;
    const previewButton = findButton(PREVIEW_SELECTORS, PREVIEW_TEXTS);
    const dialog = previewDialog();
    // Frame không có trang Kê khai (không nút Xem trước, không bản xem trước) thì IM để frame đúng trả lời.
    if (!previewButton && !dialog) return;
    if (action === "declarationPreview") {
      if (dialog) { sendResponse({ ok: true, opened: true, message: "" }); return; }
      if (previewButton.disabled) { sendResponse({ ok: false, opened: false, message: "" }); return; }
      openPreview(previewButton).then(sendResponse)
        .catch((e) => sendResponse({ ok: false, opened: false, message: String(e?.message || e) }));
      return true;
    }
    if (action === "declarationConfirm") {
      if (!dialog) { sendResponse({ ok: false, noPreview: true, message: "" }); return; }
      confirmPreview(dialog).then(sendResponse)
        .catch((e) => sendResponse({ ok: false, message: String(e?.message || e) }));
      return true;
    }
    // Đóng bản xem trước để sửa tiếp: Radix đóng hộp thoại bằng phím Esc.
    if (dialog) {
      const close = Array.from(dialog.querySelectorAll("button"))
        .find((el) => isVisible(el) && /^(dong|huy|quay lai)$/.test(fold(el.textContent)));
      if (close) clickLikeUser(close);
      else document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    }
    sendResponse({ ok: true });
  });

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const submit = msg?.action === "guidedSubmit";
    if (msg?.action !== "guidedClickNext" && !submit) return;
    // Trang nộp một trang (Cổng DVC quốc gia) do content/tu-phap-moi.js soát ô rồi mới bấm nộp;
    // khớp chữ "nop ho so" ở đây sẽ bấm thẳng "Lưu và nộp hồ sơ" khi chưa soát.
    if (window.__TLND__?.isSurveyDossierPage?.()) return;
    const button = submit
      ? findButton(SUBMIT_SELECTORS, SUBMIT_TEXTS)
      : findButton(NEXT_SELECTORS, NEXT_TEXTS);
    // Frame không có nút thì IM để frame đúng trả lời (content script chạy ở mọi frame).
    if (!button) return;
    if (button.disabled) {
      sendResponse({ ok: false, clicked: false, message: "" });
      return true;
    }
    pressAndWatch(button)
      .then(sendResponse)
      .catch((e) => sendResponse({ ok: false, clicked: false, message: String(e?.message || e) }));
    return true; // async
  });
})();
