// Tự chọn "Chọn cơ quan thực hiện" (Tỉnh/Thành phố + Phường/Xã) trên cổng DVC quốc gia
// (dichvucong.gov.vn, React). Tương ứng action `select_agency` của tro-ly-nguoi-dan-backend
// (app/chat/flow.py) — bên đó chỉ phát {province, ward}, phần thao tác DOM nằm ở client.
//
// Kích hoạt MỘT LẦN: popup ghi cờ autofill_agency_autoselect khi bấm "Mở trang kê khai"; script
// đọc cờ, điền hộ rồi XÓA cờ. Người dùng tự duyệt cổng bằng tay sẽ không bị can thiệp.
//
// BA ĐẶC ĐIỂM CỦA CỔNG BẮT BUỘC PHẢI CHIỀU:
// 1. Ô chọn ĐỔI DẠNG theo trạng thái: chưa chọn là <button aria-haspopup="listbox"><span>…</span>,
//    chọn rồi thì React thay bằng <input value="…"> kèm nút x. Giữ tham chiếu node cũ = cầm rác,
//    nên mọi thao tác đều PHẢI dò lại ô theo THỨ TỰ trong thẻ, không cache node.
// 2. Panel dropdown là PORTAL gắn cuối <body> (position:fixed), KHÔNG nằm trong thẻ; ô tìm kiếm là
//    ANH EM của <ul role="listbox">, không nằm trong listbox.
// 3. Option chốt lựa chọn ở MOUSEDOWN (chạy trước blur) -> .click() đơn thuần KHÔNG ăn, phải bắn
//    đủ chuỗi pointerdown -> mousedown -> mouseup -> click.
(() => {
  if (location.hostname !== "dichvucong.gov.vn") return;
  if (window.top !== window) return;  // khối cơ quan chỉ có ở top frame

  // Cho content.js biết có script này -> nó khỏi trả lời thay ở action getPortalFlowState.
  window.__HCC_AGENCY_FLOW__ = true;

  const ARM_KEY = "autofill_agency_autoselect";
  const ARM_TTL_MS = 10 * 60 * 1000;   // cờ quá cũ = người dùng đã bỏ giữa chừng
  const CARD_TITLE = "chon co quan thuc hien";
  const CONFIRM_LABELS = ["nop ho so", "dong y"];
  const SUBMIT_LABEL = "nop truc tuyen";
  const COMBO_SELECTOR =
    'button[aria-haspopup="listbox"], input:not([type="radio"]):not([type="checkbox"])';

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function fold(value) {
    return String(value || "")
      .replace(/đ/g, "d").replace(/Đ/g, "D")
      .normalize("NFD").replace(/[̀-ͯ]/g, "")
      .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  }

  /** Bỏ tiền tố cấp hành chính để "Tỉnh Lâm Đồng" khớp "Lâm Đồng" và ngược lại. */
  function foldArea(value) {
    return fold(value).replace(/^(tinh|thanh pho|tp|quan|huyen|thi xa|phuong|xa|thi tran|dac khu)\s+/, "").trim();
  }

  function visible(node) {
    if (!node || !node.getBoundingClientRect) return false;
    const rect = node.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return false;
    const style = getComputedStyle(node);
    return style.display !== "none" && style.visibility !== "hidden";
  }

  async function waitFor(fn, timeout = 8000, step = 200) {
    const deadline = Date.now() + timeout;
    for (;;) {
      let value;
      try { value = fn(); } catch (_) { value = null; }
      if (value) return value;
      if (Date.now() > deadline) return null;
      await sleep(step);
    }
  }

  /**
   * Bấm "như người thật": nhiều dropdown tự dựng chốt lựa chọn ở mousedown để chạy TRƯỚC blur,
   * nên riêng .click() sẽ mở được dropdown mà KHÔNG chọn được option.
   */
  function realClick(node) {
    if (!node) return false;
    try { node.scrollIntoView?.({ block: "nearest" }); } catch (_) { /* ignore */ }
    const init = { bubbles: true, cancelable: true, view: window, button: 0 };
    const fire = (Ctor, type) => {
      if (typeof Ctor !== "function") return;
      try { node.dispatchEvent(new Ctor(type, init)); } catch (_) { /* ignore */ }
    };
    fire(window.PointerEvent, "pointerdown");
    fire(window.MouseEvent, "mousedown");
    fire(window.PointerEvent, "pointerup");
    fire(window.MouseEvent, "mouseup");
    try { node.click(); } catch (_) { /* ignore */ }
    return true;
  }

  /** Thẻ "Chọn cơ quan thực hiện": tìm theo TIÊU ĐỀ rồi lấy container có combobox bên trong. */
  function findAgencyCard() {
    const heads = Array.from(document.querySelectorAll("div, h1, h2, h3, span"))
      .filter((node) => fold(node.textContent) === CARD_TITLE && visible(node));
    for (const head of heads) {
      let node = head;
      for (let depth = 0; node && depth < 5; depth += 1) {
        if (node.querySelector('button[aria-haspopup="listbox"]')) return node;
        node = node.parentElement;
      }
    }
    return null;
  }

  /** Hai ô chọn theo THỨ TỰ tài liệu: [0] Tỉnh/Thành phố, [1] Phường/Xã. Dò LẠI mỗi lần dùng. */
  function comboControls(card) {
    return Array.from(card.querySelectorAll(COMBO_SELECTOR)).filter(visible);
  }

  function controlValue(control) {
    if (!control) return "";
    if (control.tagName === "INPUT") return String(control.value || "").trim();
    // Nhãn nằm ở <span> đầu tiên; icon mũi tên nằm ở div sau nên không lẫn vào.
    return (control.querySelector("span")?.textContent || control.textContent || "").trim();
  }

  /** Ô còn "-- Chọn … --" (hoặc rỗng) = chưa chọn gì. */
  function isPlaceholder(control) {
    const label = fold(controlValue(control));
    return !label || label.startsWith("chon");
  }

  /**
   * Panel dropdown của cổng là PORTAL gắn cuối <body> (position: fixed), KHÔNG nằm trong thẻ
   * "Chọn cơ quan thực hiện":
   *   <div style="position:fixed" class="bg-white border shadow-lg">
   *     <div class="p-2 border-b"><input type="text"></div>   ← ô tìm kiếm, ANH EM của ul
   *     <ul role="listbox" class="max-h-56 overflow-auto">…</ul>
   *   </div>
   * nên phải dò từ document rồi leo lên từ <ul> để lấy panel, không tìm input BÊN TRONG listbox.
   */
  function openListbox() {
    const lists = Array.from(document.querySelectorAll('[role="listbox"]')).filter(visible);
    return lists.length ? lists[lists.length - 1] : null;
  }

  function dropdownPanel() {
    let node = openListbox()?.parentElement || null;
    for (let depth = 0; node && depth < 3; depth += 1) {
      if (node.querySelector("input")) return node;
      node = node.parentElement;
    }
    return null;
  }

  /**
   * Từng dòng lựa chọn. Cổng KHÔNG gắn role="option" nên sau khi thử role, lấy thẳng CON TRỰC TIẾP
   * của listbox — <li> hay <div> gì cũng đúng, khỏi phải đoán class.
   */
  function optionNodes() {
    const list = openListbox();
    if (!list) return null;
    const tagged = Array.from(list.querySelectorAll('[role="option"]')).filter(visible);
    if (tagged.length) return tagged;
    const direct = Array.from(list.children).filter(visible);
    return direct.length ? direct : null;
  }

  function matchOption(options, wanted) {
    const exact = fold(wanted);
    const loose = foldArea(wanted);
    return options.find((node) => fold(node.textContent) === exact)
      || options.find((node) => foldArea(node.textContent) === loose)
      || null;
  }

  /** Gõ vào ô tìm kiếm của panel — danh sách 34 tỉnh/3321 xã bị cắt max-h-56 nên phải lọc mới thấy. */
  function typeIntoSearch(wanted) {
    const panel = dropdownPanel();
    const input = panel && Array.from(panel.querySelectorAll("input")).filter(visible)[0];
    if (!input) return false;
    const setter = window.__HCC__?.setNativeValue;
    if (setter) {
      setter(input, wanted, { typing: true, commit: false });
    } else {
      // React kiểm soát value -> phải qua native setter, gán thẳng .value sẽ bị bỏ qua.
      const proto = window.HTMLInputElement?.prototype;
      const native = proto && Object.getOwnPropertyDescriptor(proto, "value")?.set;
      if (native) native.call(input, wanted); else input.value = wanted;
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
    return true;
  }

  async function pickCombo(card, index, wanted, label) {
    if (!wanted) return false;
    // Dò LẠI ô mỗi lần: React thay <button> bằng <input> sau khi chọn nên node cũ thành rác.
    const control = () => comboControls(card)[index] || null;
    const done = () => foldArea(controlValue(control())) === foldArea(wanted);

    if (!control()) {
      console.warn("[AgencySelect] không thấy ô", label);
      return false;
    }
    if (done()) {
      console.log("[AgencySelect]", label, "đã đúng sẵn:", wanted);
      return true;
    }

    realClick(control());
    if (!await waitFor(openListbox, 4000, 150)) {
      console.warn("[AgencySelect] không mở được danh sách", label);
      return false;
    }

    const findTarget = () => {
      const options = optionNodes();
      return options ? matchOption(options, wanted) : null;
    };
    let target = await waitFor(findTarget, 1200, 150);
    if (!target && typeIntoSearch(wanted)) {
      target = await waitFor(findTarget, 3000, 150);   // danh sách lọc lại sau khi gõ
    }
    if (!target) {
      console.warn("[AgencySelect] không thấy lựa chọn", label, "=", wanted);
      realClick(control());   // đóng dropdown, trả trang về nguyên trạng
      return false;
    }

    realClick(target);
    const ok = await waitFor(done, 3000, 150);
    console.log("[AgencySelect]", label, ok ? "đã chọn:" : "click xong nhưng ô chưa đổi:", wanted);
    return !!ok;
  }

  function findConfirmButton(card) {
    return Array.from(card.querySelectorAll("button"))
      .filter(visible)
      .find((node) => CONFIRM_LABELS.includes(fold(node.textContent))) || null;
  }

  function toast(message, kind) {
    try { window.__HCC__?.showPageToast?.(message, kind); } catch (_) { /* panel chưa sẵn */ }
  }

  async function readArm() {
    try {
      const res = await chrome.storage.local.get(ARM_KEY);
      return res?.[ARM_KEY] || null;
    } catch (_) { return null; }
  }

  async function clearArm() {
    try { await chrome.storage.local.remove(ARM_KEY); } catch (_) { /* ignore */ }
  }

  async function setArm(value) {
    try { await chrome.storage.local.set({ [ARM_KEY]: value }); } catch (_) { /* ignore */ }
  }

  /**
   * Nút "Nộp trực tuyến" ở thẻ kết quả (trang "Danh sách dịch vụ công"):
   *   <button class="… bg-primary …"><div><span>Nộp trực tuyến</span></div></button>
   */
  function submitButtons(scope) {
    return Array.from((scope || document).querySelectorAll("button, a"))
      .filter(visible)
      .filter((node) => fold(node.textContent) === SUBMIT_LABEL);
  }

  /** Nhiều dịch vụ cùng hiện thì phải chọn ĐÚNG thẻ mang tên thủ tục; không chắc thì trả null. */
  function pickSubmitButton(procedureLabel) {
    const all = submitButtons();
    if (all.length <= 1) return all[0] || null;

    const wanted = fold(procedureLabel);
    if (!wanted) return null;
    const narrowed = all.filter((button) => {
      let node = button.parentElement;
      for (let depth = 0; node && depth < 6; depth += 1) {
        // Thẻ kết quả nhỏ nhất có chứa tên thủ tục, và chỉ chứa ĐÚNG 1 nút nộp.
        if (fold(node.textContent).includes(wanted)) return submitButtons(node).length === 1;
        node = node.parentElement;
      }
      return false;
    });
    return narrowed.length === 1 ? narrowed[0] : null;
  }

  /**
   * Giai đoạn 2: trang kết quả đã hiện -> bấm "Nộp trực tuyến" để vào biểu mẫu kê khai.
   * Chạy được cả khi trang KHÔNG reload (gọi thẳng sau khi bấm xác nhận) lẫn khi cổng tải lại trang
   * (instance mới đọc cờ stage="submit").
   */
  async function submitStage(arm) {
    const button = await waitFor(() => pickSubmitButton(arm.procedureLabel), 15000, 300);
    if (!button) {
      await clearArm();
      return void toast(`Đã chọn ${arm.ward}, ${arm.province}. Mời bấm "Nộp trực tuyến".`, "success");
    }
    // Đổi cờ TRƯỚC khi bấm: bấm xong là cổng điều hướng, không được bấm "Nộp trực tuyến" lần hai.
    const next = arm.autoConfirm ? { ...arm, stage: "confirm", at: Date.now() } : null;
    if (next) await setArm(next); else await clearArm();
    // Đã vào được hồ sơ -> panel tự đổi về màn giấy tờ nhờ atPortalHome, chỉ cần báo cho nó biết.
    notifyPopup();
    realClick(button);
    if (!next) {
      toast(`Đã chọn ${arm.ward}, ${arm.province} và mở biểu mẫu kê khai.`, "success");
      return;
    }
    await confirmStage(next);
  }

  /**
   * Giai đoạn 3 (chỉ thủ tục có autoConfirm): cổng chặn modal "Thông tin chung" trước wizard hồ sơ
   * -> bấm "Xác nhận" hộ. Tương ứng action `confirm_info_modal` bên tro-ly-nguoi-dan-backend.
   *
   * Modal CHỈ hiện khi đã đăng nhập. Chưa đăng nhập thì chờ hết giờ rồi nhường lại cho người dùng —
   * nút "Quét và nhập dữ liệu" vẫn bấm hộ modal ở lượt sau (popup.passInfoModalIfAny).
   */
  async function confirmStage(arm) {
    for (let round = 0; round < 3; round += 1) {
      const seen = await waitFor(
        () => (formReady() ? "form" : (findInfoModal() ? "modal" : null)),
        round === 0 ? 8000 : 4000, 300,
      );
      if (seen === "form") {
        await clearArm();
        return void toast("Đã vào bước kê khai. Mời quét và nhập dữ liệu.", "success");
      }
      if (seen !== "modal") {
        // Chưa thấy gì = gần như chắc đang ở trang đăng nhập VNeID. GIỮ NGUYÊN cờ: đăng nhập xong
        // cổng điều hướng, watcher dưới gọi lại run() và vào đúng chặng này — người dùng KHÔNG
        // phải bấm "Đi đến thủ tục" lần nữa. Cờ tự hết hạn theo ARM_TTL_MS nếu bỏ giữa chừng.
        console.log("[AgencySelect] chưa thấy modal Thông tin chung — chờ lần điều hướng kế");
        return;
      }
      const modal = findInfoModal();
      realClick(modal.button);
      // Cổng có thể render lại modal một nhịp nữa -> chờ nó đóng hẳn rồi mới xét vòng sau.
      await waitFor(() => !findInfoModal(), 4000, 250);
    }

    await clearArm();
    if (formReady()) return void toast("Đã vào bước kê khai. Mời quét và nhập dữ liệu.", "success");
    if (ownerInfoStep()) return void toast("Đã xác nhận Thông tin chung. " + OWNER_STEP_HINT, "success");
    toast("Đã xác nhận Thông tin chung.", "success");
  }

  async function run() {
    const arm = await readArm();
    if (!arm) return;
    if (Date.now() - Number(arm.at || 0) > ARM_TTL_MS) return void clearArm();
    if (arm.stage === "submit") return void await submitStage(arm);
    if (arm.stage === "confirm") return void await confirmStage(arm);
    if (!arm.province || !arm.ward) return;

    // Trang thủ tục render bằng React → chờ khối cơ quan xuất hiện; không có thì thôi, giữ nguyên cờ
    // cho lần điều hướng kế (cổng hay chuyển trang trung gian trước khi tới trang chi tiết).
    const card = await waitFor(findAgencyCard, 15000, 300);
    if (!card) return;

    if (comboControls(card).length < 2) {
      console.warn("[AgencySelect] khối cơ quan chưa đủ 2 ô chọn");
      return;
    }

    if (!await pickCombo(card, 0, arm.province, "Tỉnh/Thành phố")) {
      await clearArm();
      return void toast("Không tự chọn được Tỉnh/Thành phố — mời chọn tay.", "warning");
    }
    // Chọn tỉnh xong cổng mới nạp danh sách phường/xã.
    await waitFor(() => !isPlaceholder(comboControls(card)[0]), 3000, 150);
    if (!await pickCombo(card, 1, arm.ward, "Phường/Xã")) {
      await clearArm();
      return void toast("Không tự chọn được Phường/Xã — mời chọn tay.", "warning");
    }

    // Sang GIAI ĐOẠN 2 trước khi bấm: trang kết quả cũng có khối cơ quan, giữ cờ giai đoạn 1 là
    // chạy lại thành vòng lặp; đổi stage vừa chặn lặp vừa sống sót nếu cổng tải lại trang.
    const next = { ...arm, stage: "submit", at: Date.now() };
    await setArm(next);
    const confirm = findConfirmButton(card);
    if (!confirm || confirm.disabled) {
      await clearArm();
      return void toast(`Đã chọn ${arm.ward}, ${arm.province}. Mời bấm nút xác nhận.`, "success");
    }
    realClick(confirm);
    await submitStage(next);
  }

  // Vòng theo dõi SPA có thể gọi run() trong lúc lượt trước còn đang chờ nút -> khoá lại, nếu không
  // hai lượt cùng thấy nút và bấm hai lần.
  let running = false;
  // ---------- bước sau khi đăng nhập: modal "Thông tin chung" -> wizard "Kê khai thông tin" ----------
  // Theo luồng của tro-ly-nguoi-dan-backend (app/chat/flow.py): thấy infoModal thì bấm Xác nhận,
  // tới wizardStep 2 / có form kê khai thì mới đến lượt quét & điền.
  const INFO_MODAL_TITLE = "thong tin chung";
  const CONFIRM_MODAL_LABELS = ["xac nhan", "dong y", "tiep tuc"];
  const FORM_MARKERS = ["ke khai thong tin", "thong tin ke khai"];
  // Wizard hồ sơ bước 1: người dân TỰ điền rồi TỰ bấm "Xác nhận" (bot bên tro-ly cũng chỉ dặn,
  // xem app/chat/flow.py nhánh wizardStep == 1). Quét/điền chỉ chạy được từ bước 2 trở đi.
  const OWNER_STEP_MARKER = "thong tin chu ho so";
  const OWNER_STEP_HINT =
    'Đang ở bước "Thông tin chủ hồ sơ" — mời điền rồi bấm "Xác nhận" ở bước này, xong mới quét được.';

  function textNodes() {
    return Array.from(document.querySelectorAll("div, span, h1, h2, h3, p, label, li, button"))
      .filter(visible);
  }

  function confirmButtonIn(scope) {
    return Array.from(scope.querySelectorAll("button"))
      .filter(visible)
      .find((node) => CONFIRM_MODAL_LABELS.includes(fold(node.textContent))) || null;
  }

  /**
   * Chỗ "Thông tin chung" + nút xác nhận của nó. Cổng dựng theo HAI dạng tuỳ thủ tục:
   *  - modal nổi ([role="dialog"] / .modal)
   *  - MỤC trong wizard: chỉ là tiêu đề "Thông tin chung" nằm cùng khối với nút "Xác nhận"
   * nên dò dialog trước, không có thì bám theo tiêu đề rồi leo lên tìm khối chứa nút.
   */
  function findInfoModal() {
    const dialogs = Array.from(document.querySelectorAll('[role="dialog"], .modal, [class*="modal"]'))
      .filter(visible);
    for (const scope of dialogs) {
      if (!fold(scope.textContent).includes(INFO_MODAL_TITLE)) continue;
      const button = confirmButtonIn(scope);
      if (button) return { scope, button };
    }

    // Dạng mục trong wizard: lấy TIÊU ĐỀ (text ngắn, đúng "Thông tin chung") rồi leo lên tối đa 5
    // cấp. Khối hợp lệ phải chứa ĐÚNG 1 nút xác nhận — nhiều hơn nghĩa là đã leo quá tay ra ngoài,
    // bấm bừa sẽ nhầm nút của bước khác.
    const headings = textNodes().filter((node) => {
      const text = fold(node.textContent);
      return text.length < 40 && text.includes(INFO_MODAL_TITLE);
    });
    for (const heading of headings) {
      let scope = heading.parentElement;
      for (let depth = 0; scope && depth < 5; depth += 1) {
        const buttons = Array.from(scope.querySelectorAll("button"))
          .filter(visible)
          .filter((node) => CONFIRM_MODAL_LABELS.includes(fold(node.textContent)));
        if (buttons.length === 1) return { scope, button: buttons[0] };
        if (buttons.length > 1) break;
        scope = scope.parentElement;
      }
    }
    return null;
  }

  /** Đã tới bước kê khai chưa: có heading "Kê khai thông tin" hoặc eform trong iframe. */
  function formReady() {
    if (document.querySelector('iframe[src*="eform"], iframe[src*="ke-khai"]')) return true;
    return textNodes().some((node) => {
      const text = fold(node.textContent);
      return text.length < 60 && FORM_MARKERS.some((marker) => text.includes(marker));
    });
  }

  /** Đang ở bước "Thông tin chủ hồ sơ" của wizard (chưa tới bước kê khai). */
  function ownerInfoStep() {
    if (formReady()) return false;
    return textNodes().some((node) => {
      const text = fold(node.textContent);
      return text.length < 60 && text.includes(OWNER_STEP_MARKER);
    });
  }

  // Trang chi tiết DVCQG đã định danh thủ tục ngay trong route. Không chờ thẻ "Chọn cơ quan
  // thực hiện" render mới kết luận, vì trong nhịp tải đầu popup sẽ hiểu nhầm đây là trang chủ và
  // hiện lại màn tìm/chọn thủ tục dù URL đã đủ để auto-detect.
  function isProcedureDetailPage(rawUrl = location.href) {
    try {
      const url = new URL(rawUrl);
      return url.hostname === "dichvucong.gov.vn"
        && /^\/thu-tuc-hanh-chinh\/[^/]+\/?$/.test(url.pathname);
    } catch (_) {
      return false;
    }
  }

  function flowState() {
    const onProcedurePage = isProcedureDetailPage() || !!findAgencyCard();
    const infoModal = !!findInfoModal();
    const ownerInfo = ownerInfoStep();
    const ready = formReady();
    return {
      onProcedurePage,
      infoModal,
      ownerInfo,
      formReady: ready,
      // Chưa dính gì tới một thủ tục cụ thể (trang chủ, tra cứu, danh mục…) -> panel hiện khối
      // chọn điểm đến; vào tới trang thủ tục/hồ sơ rồi thì trả màn về giấy tờ + quét.
      atPortalHome: !(onProcedurePage || infoModal || ownerInfo || ready),
      ownerStepHint: OWNER_STEP_HINT,
    };
  }

  // Popup hỏi trạng thái / nhờ bấm hộ modal. Chỉ top frame trả lời.
  chrome.runtime?.onMessage?.addListener((msg, _sender, sendResponse) => {
    if (window.top !== window) return;
    if (msg?.action === "getPortalFlowState") {
      sendResponse({ ok: true, ...flowState() });
      return;
    }
    if (msg?.action === "confirmInfoModal") {
      const modal = findInfoModal();
      if (!modal) { sendResponse({ ok: false, reason: "no-modal" }); return; }
      realClick(modal.button);
      waitFor(formReady, 8000, 250).then((ready) => sendResponse({ ok: true, formReady: !!ready }));
      return true;   // trả lời bất đồng bộ
    }
  });

  const start = () => {
    if (running) return;
    running = true;
    void run().finally(() => { running = false; });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();

  // SPA: cổng đổi route mà không tải lại trang → chạy lại khi URL đổi (cờ hết thì run() tự thoát).
  // Đăng nhập VNeID xong có khi chỉ render lại DOM mà giữ nguyên URL, nên còn rà thêm: đang có cờ
  // dở dang mà trang xuất hiện modal "Thông tin chung" thì vào tiếp luôn.
  function notifyPopup() {
    // Panel là iframe riêng, không thấy được DOM cổng -> phải bắn tin để nó đổi màn kịp thời.
    try { chrome.runtime?.sendMessage?.({ action: "portalFlowChanged" }); } catch (_) { /* ignore */ }
  }

  let lastUrl = location.href;
  let lastHome = null;
  setInterval(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      notifyPopup();
      return void start();
    }
    // SPA đổi màn mà giữ URL: bám theo chính trạng thái luồng.
    const home = flowState().atPortalHome;
    if (home !== lastHome) {
      lastHome = home;
      notifyPopup();
    }
    if (!running && findInfoModal()) start();
  }, 1000);
})();
