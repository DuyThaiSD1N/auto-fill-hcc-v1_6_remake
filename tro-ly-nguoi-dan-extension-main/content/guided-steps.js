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

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const submit = msg?.action === "guidedSubmit";
    if (msg?.action !== "guidedClickNext" && !submit) return;
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
