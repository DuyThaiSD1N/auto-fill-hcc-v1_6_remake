// portal-login.js — nhận diện TRẠNG THÁI ĐĂNG NHẬP của cổng DVC quốc gia + ba màn VNeID/SSO.
//
// Port từ tro-ly-nguoi-dan-extension: content/vneid-sso.js (ba modal VNeID) + khối `getPageContext`
// của content.js (loggedIn/loginPage). Khác biệt: bên đó backend chat cầm nhịp và hỏi trạng thái
// qua message; bên này agency-select.js tự cầm nhịp bằng máy trạng thái stage, nên module chỉ ĐỌC
// DOM và trả tín hiệu, KHÔNG tự thao tác gì.
//
// VÌ SAO PHẢI CÓ: bấm "Nộp trực tuyến" xong cổng chỉ mở modal "Thông tin chung" khi ĐÃ đăng nhập.
// Chưa đăng nhập thì cổng đá sang màn VNeID — chuỗi tự động cũ chờ hết giờ rồi im lặng bỏ cuộc,
// cán bộ không biết vì sao trợ lý dừng. Có tín hiệu này thì agency-select.js đứng đợi ở stage
// "login" rồi tự đi tiếp vào form ngay khi công dân đăng nhập xong.
//
// KHÔNG dựa class Tailwind (đổi theo build) — mọi thứ khớp theo TEXT đã fold dấu.
(() => {
  const H = (window.__HCC_LOGIN__ = window.__HCC_LOGIN__ || {});
  if (H.detectLoginState) return;

  const fold = (value) => String(value || "")
    .replace(/Đ/g, "D").replace(/đ/g, "d")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/\s+/g, " ").trim().toLowerCase();

  function visible(element) {
    if (!element) return false;
    try {
      const style = element.ownerDocument?.defaultView?.getComputedStyle(element);
      if (!style) return false;
      return style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0"
        && element.getClientRects().length > 0;
    } catch (_) {
      return false;
    }
  }

  /**
   * Chữ đang HIỂN THỊ trên màn. Bỏ qua node dài (>300 ký tự) vì đó là wrapper bọc cả phần đăng
   * nhập ẩn lẫn nội dung kê khai — tin nó là nhận nhầm trang đã vào hồ sơ thành trang đăng nhập.
   */
  function hasVisibleText(doc, needle) {
    const nodes = doc.querySelectorAll("h1,h2,h3,h4,p,span,label,button,a,div");
    for (const element of nodes) {
      // Lọc theo CHỮ trước rồi mới đo hiển thị: getClientRects() ép trình duyệt tính layout, gọi
      // cho vài nghìn node mỗi nhịp watcher là đủ làm giật trang cổng.
      const raw = String(element.textContent || "").replace(/\s+/g, " ").trim();
      if (!raw || raw.length > 300) continue;
      if (!fold(raw).includes(needle)) continue;
      if (visible(element)) return true;
    }
    return false;
  }

  /** Node chữ NGẮN NHẤT khớp điều kiện — node ngắn nhất là chính dòng chữ đó, không phải wrapper. */
  function visibleTextElement(doc, matches) {
    return Array.from(doc.querySelectorAll("h1,h2,h3,h4,p,span,div,label"))
      .filter((element) => {
        const text = fold(element.textContent);
        if (!text || text.length > 600 || !matches(text)) return false;
        return visible(element);   // đo layout sau cùng, chỉ cho vài node đã khớp chữ
      })
      .sort((a, b) => fold(a.textContent).length - fold(b.textContent).length)[0] || null;
  }

  function modalScope(marker) {
    const scope = marker?.closest?.(".ant-modal-content, [role='dialog'], .ant-modal")
      || marker?.closest?.(".ant-modal-body")
      || marker?.parentElement;
    return scope && visible(scope) ? scope : null;
  }

  /**
   * Như modalScope nhưng KHÔNG có nhánh lùi về parentElement — dùng cho chỗ bắt buộc phải thật sự
   * nằm trong dialog. modalScope lỏng là cố ý (ba modal kia còn soi thêm input/checkbox bên trong
   * nên container lỏng vẫn đúng), riêng nút "Đăng nhập bằng VNeID" chỉ có mỗi cái nhãn.
   */
  function strictModalScope(marker) {
    const scope = marker?.closest?.(
      ".ant-modal-content, [role='dialog'], .ant-modal, .ant-modal-body"
    );
    return scope && visible(scope) ? scope : null;
  }

  function hasVisibleButton(scope, labels) {
    return Array.from(scope?.querySelectorAll?.("button") || [])
      .some((button) => visible(button) && labels.includes(fold(button.textContent)));
  }

  /** Màn OTP khi công dân đăng nhập bằng tài khoản thay vì quét QR. */
  function detectVneidLoginCodePrompt(doc) {
    const marker = visibleTextElement(doc, (text) =>
      text.includes("ma xac nhan dang nhap") || text.includes("nhap ma xac nhan"));
    const scope = modalScope(marker);
    if (!scope) return false;
    const input = scope.querySelector?.(
      'input[inputmode="numeric"], input[type="number"], input[autocomplete="one-time-code"]'
    );
    return !!input && hasVisibleButton(scope, ["xac nhan", "dang nhap", "tiep tuc"]);
  }

  /** Màn xin công dân đồng ý chia sẻ dữ liệu, hiện NGAY SAU khi xác thực xong. */
  function detectVneidDataSharingPrompt(doc) {
    const marker = visibleTextElement(doc, (text) =>
      text.includes("toi da doc va hieu ro noi dung muc dich")
      && text.includes("quyen, nghia vu cua chu the du lieu"));
    const scope = modalScope(marker);
    if (!scope) return false;
    const checkbox = scope.querySelector?.(
      'input[type="checkbox"], [role="checkbox"], .ant-checkbox-input'
    );
    return !!checkbox && hasVisibleButton(scope, ["xac nhan chia se"]);
  }

  /** Modal nhập passcode VNeID — khớp ĐÚNG tiêu đề để không nuốt modal chia sẻ dữ liệu đứng trước. */
  function detectVneidPasscodePrompt(doc) {
    const title = visibleTextElement(doc, (text) => text === "nhap passcode");
    const scope = modalScope(title);
    if (!scope) return false;
    const input = scope.querySelector('input[type="number"][inputmode="numeric"][autocomplete="off"]');
    return !!input && hasVisibleButton(scope, ["xac nhan"]);
  }

  /**
   * Cổng TỈNH (dichvucong.quangninh.gov.vn) chặn bằng một dialog chỉ có nút "Đăng nhập bằng VNeID"
   * — KHÔNG có chữ "quét mã QR" như cổng quốc gia, nên cặp marker kia bắt hụt. Nhãn này đủ đặc
   * trưng để không đụng nút "Đăng nhập" trống ở header.
   */
  function detectVneidLoginButton(scope) {
    const button = Array.from(scope.querySelectorAll("button, a")).find((node) => {
      const text = fold(node.textContent);
      return text.startsWith("dang nhap bang vneid") && visible(node);
    });
    // BẮT BUỘC nằm trong dialog đang mở, giống ba màn VNeID kia. Nút "Đăng nhập bằng VNeID" còn
    // nằm sẵn ở khu vực tài khoản của nhiều cổng tỉnh kể cả khi đã đăng nhập — nhận nó là chặn thì
    // trợ lý đứng chờ đăng nhập vĩnh viễn trên một trang vốn đã vào được.
    return !!strictModalScope(button);
  }

  let cached = null;
  let cachedAt = 0;

  /**
   * Trạng thái đăng nhập của trang đang mở.
   *
   * `loggedIn`: cổng React hiện tên tài khoản (.user-dropdown) / Angular (#account_name), hoặc có
   * nút "Đăng xuất". Phải xét node có HIỂN THỊ: cổng hay giữ lại component cũ trong DOM.
   *
   * `loginRequired`: đang đứng ở màn đăng nhập. Chỉ nhận khi thấy ĐỦ "đăng nhập" + "quét mã QR" —
   * nút "Đăng nhập" ở header trang chủ luôn có nên một mình nó không đủ làm bằng chứng. Ba modal
   * VNeID thì thắng cả `loggedIn`: sau OTP cổng đã hiện tên tài khoản nhưng vẫn chặn bằng modal
   * chia sẻ dữ liệu/passcode, đi tiếp lúc này là bấm vào khoảng không.
   */
  function detectLoginState(doc, { maxAgeMs = 600 } = {}) {
    // Chỉ TRANG THẬT mới được cache. Gọi kèm doc (test, iframe) là hỏi một cây DOM khác — trả bản
    // nhớ của trang chính thì sai, mà ghi đè bản nhớ đó thì làm hỏng nhịp watcher.
    const live = doc === undefined;
    const scope = live ? document : doc;
    // Watcher gọi mỗi giây, popup hỏi thêm mỗi lần đổi màn -> dùng chung một lượt quét trong
    // khoảng 600ms. Chỗ nào vừa bấm xong cần số liệu tươi thì truyền maxAgeMs: 0.
    if (live && cached && maxAgeMs > 0 && Date.now() - cachedAt < maxAgeMs) return cached;
    const account = scope.querySelector("#account_name") || scope.querySelector(".user-dropdown");
    const loggedIn = visible(account) || hasVisibleText(scope, "dang xuat");
    const vneidLoginCodePrompt = detectVneidLoginCodePrompt(scope);
    const vneidDataSharingPrompt = detectVneidDataSharingPrompt(scope);
    const vneidPasscodePrompt = detectVneidPasscodePrompt(scope);
    const vneidLoginButton = detectVneidLoginButton(scope);
    const onAuthHost = /xacthuc|vneid|sso|dancuquocgia/.test(location.hostname);
    const loginRequired = vneidLoginCodePrompt || vneidDataSharingPrompt || vneidPasscodePrompt
      || vneidLoginButton
      || (!loggedIn && (onAuthHost
        || (hasVisibleText(scope, "dang nhap") && hasVisibleText(scope, "quet ma qr"))));
    const state = {
      loggedIn,
      loginRequired,
      vneidLoginCodePrompt,
      vneidDataSharingPrompt,
      vneidPasscodePrompt,
      vneidLoginButton,
    };
    if (live) { cached = state; cachedAt = Date.now(); }
    return state;
  }

  /** Câu nhắc đúng việc đang chặn — để toast/panel nói rõ cán bộ phải làm gì tiếp. */
  function loginHint(state) {
    if (!state || !state.loginRequired) return "";
    if (state.vneidPasscodePrompt) return "Mời nhập passcode VNeID để hoàn tất đăng nhập.";
    if (state.vneidDataSharingPrompt) return "Mời tích đồng ý và bấm \"Xác nhận chia sẻ\" trên VNeID.";
    if (state.vneidLoginCodePrompt) return "Mời nhập mã xác nhận đăng nhập VNeID.";
    if (state.vneidLoginButton) return "Mời bấm \"Đăng nhập bằng VNeID\" rồi hoàn tất đăng nhập.";
    return "Mời đăng nhập VNeID (quét mã QR hoặc nhập tài khoản) để vào hồ sơ.";
  }

  H.detectLoginState = detectLoginState;
  H.loginHint = loginHint;
})();
