(() => {
  "use strict";

  const H = (window.__TLND__ = window.__TLND__ || {});

  const fold = (value) => String(value || "")
    .replace(/Đ/g, "D").replace(/đ/g, "d")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ").trim().toLowerCase();

  function defaultVisible(element) {
    if (!element) return false;
    try {
      const style = element.ownerDocument?.defaultView?.getComputedStyle(element);
      return style?.display !== "none" && style?.visibility !== "hidden" && style?.opacity !== "0"
        && element.getClientRects().length > 0;
    } catch (_) {
      return false;
    }
  }

  function visibleTextElement(doc, isVisible, matches) {
    return Array.from(doc.querySelectorAll("h1,h2,h3,h4,p,span,div,label"))
      .filter((element) => {
        if (!isVisible(element)) return false;
        const text = fold(element.textContent);
        return text && text.length <= 600 && matches(text);
      })
      .sort((a, b) => fold(a.textContent).length - fold(b.textContent).length)[0] || null;
  }

  function modalScope(marker, isVisible) {
    const scope = marker?.closest?.(".ant-modal-content, [role='dialog'], .ant-modal")
      || marker?.closest?.(".ant-modal-body")
      || marker?.parentElement;
    return scope && isVisible(scope) ? scope : null;
  }

  function hasVisibleButton(scope, isVisible, labels) {
    return Array.from(scope?.querySelectorAll?.("button") || [])
      .some((button) => isVisible(button) && labels.includes(fold(button.textContent)));
  }

  /** Màn OTP khi công dân đăng nhập bằng thông tin tài khoản thay vì quét QR. */
  function detectVneidLoginCodePrompt(doc = document, isVisible = defaultVisible) {
    const marker = visibleTextElement(doc, isVisible, (text) =>
      text.includes("ma xac nhan dang nhap") || text.includes("nhap ma xac nhan"));
    const scope = modalScope(marker, isVisible);
    if (!scope) return false;
    const input = scope.querySelector?.(
      'input[inputmode="numeric"], input[type="number"], input[autocomplete="one-time-code"]'
    );
    return !!input && hasVisibleButton(scope, isVisible, ["xac nhan", "dang nhap", "tiep tuc"]);
  }

  /** Màn xin công dân đồng ý chia sẻ dữ liệu sau khi xác thực đăng nhập. */
  function detectVneidDataSharingPrompt(doc = document, isVisible = defaultVisible) {
    const marker = visibleTextElement(doc, isVisible, (text) =>
      text.includes("toi da doc va hieu ro noi dung muc dich")
      && text.includes("quyen, nghia vu cua chu the du lieu"));
    const scope = modalScope(marker, isVisible);
    if (!scope) return false;
    const checkbox = scope.querySelector?.(
      'input[type="checkbox"], [role="checkbox"], .ant-checkbox-input'
    );
    return !!checkbox && hasVisibleButton(scope, isVisible, ["xac nhan chia se"]);
  }

  /**
   * Nhận diện riêng modal nhập passcode VNeID. Không dựa class Tailwind động và không
   * nhận nhầm modal xin chia sẻ dữ liệu đứng ngay trước nó.
   */
  function detectVneidPasscodePrompt(doc = document, isVisible = defaultVisible) {
    const title = visibleTextElement(doc, isVisible, (text) => text === "nhap passcode");
    if (!title) return false;

    const scope = modalScope(title, isVisible);
    if (!scope) return false;

    const input = scope.querySelector(
      'input[type="number"][inputmode="numeric"][autocomplete="off"]'
    );
    if (!input) return false;

    return hasVisibleButton(scope, isVisible, ["xac nhan"]);
  }

  H.detectVneidLoginCodePrompt = detectVneidLoginCodePrompt;
  H.detectVneidDataSharingPrompt = detectVneidDataSharingPrompt;
  H.detectVneidPasscodePrompt = detectVneidPasscodePrompt;
})();
