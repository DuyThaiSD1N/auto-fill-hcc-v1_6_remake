// portal-quangninh.js — chặng CỔNG TỈNH, nối tiếp content/agency-select.js.
//
// Thủ tục đặc thù của tỉnh: bấm "Nộp trực tuyến" trên cổng quốc gia xong, cổng KHÔNG mở biểu mẫu
// mà ném sang cổng tỉnh, ví dụ:
//   https://dichvucong.quangninh.gov.vn/nop-ho-so?...&MaTTHC=1.115835&MaCoQuanThucHien=H49.22
// Ở đó còn ba việc nữa mới tới bước kê khai:
//   1. Bảng "Danh sách thủ tục hành chính" -> bấm "Nộp hồ sơ" ĐÚNG DÒNG (một mã TTHC ra nhiều
//      biến thể: đồng bằng / "Miền núi, hải đảo"...).
//   2. Cổng tỉnh có phiên đăng nhập RIÊNG -> hay chặn bằng dialog "Đăng nhập bằng VNeID". Đăng
//      nhập xong quay lại đúng trang này và phải bấm "Nộp hồ sơ" lần nữa.
//   3. Modal "Thông tin chung" -> chọn Cơ quan thực hiện (chi nhánh VPĐK đất đai theo địa bàn)
//      rồi bấm "Xác nhận".
//
// Cùng dùng CỜ autofill_agency_autoselect với agency-select.js: cờ nằm ở chrome.storage nên sống
// qua cú nhảy cross-origin từ cổng quốc gia sang cổng tỉnh. agency-select.js khoá host
// dichvucong.gov.vn nên hai bên không giẫm chân nhau.
//
// Điều khiển theo TRẠNG THÁI TRANG chứ không theo tên chặng: mỗi nhịp nhìn DOM rồi làm việc đang
// tới lượt. Cổng tỉnh chạy chuỗi login/redirect không đoán trước được, bám tên chặng là sai nhịp.
//
// Cấu hình lấy từ `provincePortalFlow` của thủ tục trong ke_khai_links.json (backend) — không
// hard-code thủ tục/địa bàn vào engine.
(() => {
  if (window.top !== window) return;          // bảng + modal chỉ có ở top frame
  if (window.__HCC_QN_FLOW__) return;         // chống inject trùng
  window.__HCC_QN_FLOW__ = true;

  const ARM_KEY = "autofill_agency_autoselect";
  // Dài bằng chặng đăng nhập bên agency-select.js: đoạn này gần như luôn phải chờ công dân xác thực.
  const ARM_TTL_MS = 30 * 60 * 1000;
  const SUBMIT_LABEL = "nop ho so";
  const CONFIRM_LABEL = "xac nhan";
  const INFO_MODAL_TITLE = "thong tin chung";
  const FORM_MARKERS = ["ke khai thong tin", "thong tin ke khai"];
  // Bấm xong cổng cần vài giây để điều hướng/dựng modal. Không có khoảng nghỉ này thì nhịp watcher
  // kế tiếp thấy nút vẫn còn đó và bấm lần hai -> mở nhầm hai hồ sơ.
  const CLICK_COOLDOWN_MS = 6000;
  // Modal "Thông tin chung" là chuỗi select PHỤ THUỘC: chọn xong Cơ quan thực hiện cổng mới gọi API
  // nạp "Đơn vị tiếp nhận" tương ứng. Thao tác liền tay là bấm vào danh sách cũ/rỗng, nên mỗi bước
  // nghỉ một nhịp cho cổng render xong.
  const STEP_PAUSE_MS = 500;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function fold(value) {
    return String(value || "")
      .replace(/đ/g, "d").replace(/Đ/g, "D")
      .normalize("NFD").replace(/[̀-ͯ]/g, "")
      .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
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

  /** Bấm "như người thật": Radix/React chốt lựa chọn ở mousedown, .click() đơn thuần không ăn. */
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

  function toast(message, kind) {
    try { window.__HCC__?.showPageToast?.(message, kind); } catch (_) { /* panel chưa sẵn */ }
  }

  function notifyPopup() {
    try { chrome.runtime?.sendMessage?.({ action: "portalFlowChanged" }); } catch (_) { /* ignore */ }
  }

  const log = (...args) => console.log("[QuangNinh]", ...args);

  // ---------- cờ dùng chung với agency-select.js ----------
  /** Trả undefined khi ĐỌC LỖI, null khi thật sự KHÔNG có cờ — hai chuyện phải xử khác nhau. */
  async function readArm() {
    try {
      const res = await chrome.storage.local.get(ARM_KEY);
      return res?.[ARM_KEY] || null;
    } catch (error) {
      console.warn("[QuangNinh] không đọc được cờ:", error);
      return undefined;
    }
  }

  async function setArm(value) {
    try { await chrome.storage.local.set({ [ARM_KEY]: value }); } catch (_) { /* ignore */ }
  }

  async function clearArm() {
    try { await chrome.storage.local.remove(ARM_KEY); } catch (_) { /* ignore */ }
  }

  // ---------- đọc trạng thái trang ----------
  function loginState() {
    try {
      return window.__HCC_LOGIN__?.detectLoginState?.(undefined, { maxAgeMs: 0 }) || null;
    } catch (_) { return null; }
  }

  function loginBlocked() {
    return !!loginState()?.loginRequired;
  }

  function textNodes() {
    return Array.from(document.querySelectorAll("div, span, h1, h2, h3, p, label, li, button"))
      .filter(visible);
  }

  /** Đã tới bước kê khai chưa. */
  function formReady() {
    if (document.querySelector('iframe[src*="eform"], iframe[src*="ke-khai"]')) return true;
    return textNodes().some((node) => {
      const text = fold(node.textContent);
      return text.length < 60 && FORM_MARKERS.some((marker) => text.includes(marker));
    });
  }

  /**
   * Modal "Thông tin chung" (chọn cơ quan thực hiện). Lấy dialog NHỎ NHẤT có tiêu đề đó — cổng
   * lồng nhiều lớp overlay, lấy lớp ngoài là quét trúng cả nội dung trang phía sau.
   */
  function findInfoModal() {
    return Array.from(document.querySelectorAll('[role="dialog"], .ant-modal-content'))
      .filter(visible)
      .filter((node) => fold(node.textContent).includes(INFO_MODAL_TITLE))
      .sort((a, b) => fold(a.textContent).length - fold(b.textContent).length)[0] || null;
  }

  // ---------- bước 1: bấm "Nộp hồ sơ" đúng dòng ----------
  function submitButtons() {
    return Array.from(document.querySelectorAll("button, a"))
      .filter(visible)
      .filter((node) => fold(node.textContent) === SUBMIT_LABEL);
  }

  function rowOf(button) {
    return button?.closest?.("tr") || button?.parentElement || null;
  }

  /**
   * Một mã TTHC ra NHIỀU dòng (đồng bằng / "Miền núi, hải đảo"...). Ưu tiên khớp theo CHỮ trong
   * dòng (`rowIncludes`) vì thứ tự bảng đổi theo dữ liệu cổng; không khớp mới rơi về vị trí
   * (`rowIndex`, mặc định dòng đầu — cùng quy ước "lấy mục đầu" của agency-select.js).
   */
  function pickSubmitButton(flow) {
    const all = submitButtons();
    if (!all.length) return null;
    const wanted = fold(flow.rowIncludes || "");
    if (wanted) {
      const matched = all.find((button) => fold(rowOf(button)?.textContent).includes(wanted));
      if (matched) {
        log("chọn dòng khớp chữ:", flow.rowIncludes);
        return matched;
      }
      console.warn(`[QuangNinh] không thấy dòng chứa "${flow.rowIncludes}" — rơi về vị trí`);
    }
    const index = rowIndexOf(flow);
    if (index > all.length) {
      // Cấu hình đòi dòng thứ N mà bảng không có đủ. Rơi về dòng đầu là mở NHẦM biến thể thủ tục
      // (đồng bằng thay vì miền núi, "không phải nộp" thay vì "phải nộp nghĩa vụ tài chính") —
      // thà không bấm gì để cán bộ tự chọn.
      console.warn(`[QuangNinh] bảng mới có ${all.length} dòng, cấu hình đòi dòng ${index}`);
      return null;
    }
    log(`chọn dòng theo vị trí: ${index}/${all.length}`);
    return all[index - 1];
  }

  function rowIndexOf(flow) {
    return Math.max(1, Number(flow.rowIndex) || 1);
  }

  let lastSubmitClickAt = 0;

  async function submitStage(flow) {
    if (Date.now() - lastSubmitClickAt < CLICK_COOLDOWN_MS) return;
    if (!await waitFor(() => submitButtons().length, 12000, 300)) return;  // bảng chưa dựng xong
    // Bảng render DẦN: chờ số nút đứng yên rồi mới chốt, bấm sớm là trúng dòng khác.
    let count = submitButtons().length;
    for (let round = 0; round < 5; round += 1) {
      await sleep(400);
      const now = submitButtons().length;
      if (now === count) break;
      count = now;
    }

    const button = pickSubmitButton(flow);
    if (!button) {
      const index = rowIndexOf(flow);
      // Bảng đã vẽ xong mà vẫn thiếu dòng -> dừng hẳn, đừng lặng lẽ thử lại mãi.
      if (index > count) {
        await stop();
        return void toast(
          `Bảng chỉ có ${count} dòng "Nộp hồ sơ" nhưng cấu hình đòi dòng ${index} — mời bấm tay.`,
          "warning",
        );
      }
      return;
    }
    lastSubmitClickAt = Date.now();
    log("bấm \"Nộp hồ sơ\"");
    realClick(button);
  }

  // ---------- bước 3: chọn cơ quan trong modal "Thông tin chung" ----------
  function comboboxes(modal) {
    return Array.from(modal.querySelectorAll(
      'button[role="combobox"], button[aria-haspopup="listbox"], button[aria-haspopup="dialog"]'
    )).filter(visible);
  }

  /** Panel dropdown là PORTAL gắn cuối <body> (Radix popper), KHÔNG nằm trong modal. */
  function dropdownPanel() {
    const poppers = Array.from(document.querySelectorAll("[data-radix-popper-content-wrapper]"))
      .filter(visible);
    if (poppers.length) return poppers[poppers.length - 1];
    const lists = Array.from(document.querySelectorAll('[role="listbox"], [cmdk-list]')).filter(visible);
    return lists.length ? lists[lists.length - 1].parentElement : null;
  }

  function optionNodes(panel) {
    const tagged = Array.from(panel.querySelectorAll('[role="option"], [cmdk-item], li')).filter(visible);
    if (tagged.length) return tagged;
    // Bản shadcn/cmdk không phải build nào cũng gắn role -> lấy node LÁ có chữ.
    return Array.from(panel.querySelectorAll("div, span"))
      .filter((node) => !node.children.length && fold(node.textContent) && visible(node));
  }

  function matchOption(options, wanted) {
    const target = fold(wanted);
    return options.find((node) => fold(node.textContent) === target)
      || options.find((node) => fold(node.textContent).includes(target))
      || null;
  }

  /** Gõ vào ô tìm kiếm của panel — danh sách chi nhánh dài, bị cắt max-height nên phải lọc mới thấy. */
  function typeIntoSearch(panel, wanted) {
    const input = Array.from(panel.querySelectorAll("input")).filter(visible)[0];
    if (!input) return false;
    // React kiểm soát value -> phải qua native setter, gán thẳng .value sẽ bị bỏ qua.
    const proto = window.HTMLInputElement?.prototype;
    const native = proto && Object.getOwnPropertyDescriptor(proto, "value")?.set;
    if (native) native.call(input, wanted); else input.value = wanted;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  }

  function comboValue(control) {
    return String(control?.textContent || "").replace(/\s+/g, " ").trim();
  }

  /** Ô còn "Tìm kiếm" / "-- Chọn … --" / rỗng = chưa chọn gì. */
  function isPlaceholder(control) {
    const label = fold(comboValue(control));
    return !label || label.startsWith("chon") || label.startsWith("tim kiem");
  }

  /**
   * Dò TỪNG ô chọn trong modal cho tới ô nào có lựa chọn cần tìm.
   *
   * Cố ý KHÔNG khoá theo vị trí ô: modal có mấy ô (Cấp thực hiện / Tỉnh-Thành / Cơ quan thực hiện /
   * …) và thứ tự đổi theo thủ tục. Tìm theo TÊN chi nhánh thì chỉ đúng một ô chứa nó, không thể
   * đặt nhầm giá trị vào ô khác.
   */
  async function pickAgency(modal, wanted) {
    const target = fold(wanted);
    const controls = comboboxes(modal);
    log(`modal có ${controls.length} ô chọn — tìm "${wanted}"`);

    for (let index = 0; index < controls.length; index += 1) {
      const control = () => comboboxes(modal)[index];
      if (fold(comboValue(control())).includes(target)) {
        log(`ô ${index} đã sẵn giá trị cần chọn`);
        return true;
      }

      realClick(control());
      const panel = await waitFor(dropdownPanel, 2500, 120);
      if (!panel) continue;
      await sleep(STEP_PAUSE_MS);   // chờ cổng nạp xong danh sách rồi mới đọc

      let option = matchOption(optionNodes(panel), wanted);
      if (!option && typeIntoSearch(panel, wanted)) {
        option = await waitFor(() => matchOption(optionNodes(dropdownPanel() || panel), wanted), 3000, 150);
      }
      if (!option) {
        realClick(control());   // đóng lại, trả modal về nguyên trạng rồi thử ô kế
        await sleep(STEP_PAUSE_MS);
        continue;
      }

      // Bấm đúng node nhận sự kiện: node lá có thể chỉ là <span> chữ bên trong item.
      realClick(option.closest('[role="option"], [cmdk-item], li') || option);
      const ok = await waitFor(() => fold(comboValue(control())).includes(target), 3000, 150);
      log(ok ? `đã chọn ở ô ${index}: ${wanted}` : `bấm xong nhưng ô ${index} chưa đổi`);
      if (ok) {
        await sleep(STEP_PAUSE_MS);   // nhường nhịp cho cổng gọi API nạp ô phụ thuộc
        return true;
      }
    }
    return false;
  }

  /**
   * Điền nốt các ô CÒN TRỐNG sau khi đã chọn Cơ quan thực hiện — điển hình là "Đơn vị tiếp nhận",
   * chỉ được cổng nạp SAU khi biết cơ quan.
   *
   * Đi lần lượt từng ô, mỗi ô mở ra chờ danh sách nạp xong rồi lấy lựa chọn ĐẦU (cùng quy ước "mục
   * đầu như default"). Bấm Xác nhận khi ô này còn trống là gửi hồ sơ thiếu đơn vị tiếp nhận.
   *
   * Ô đã có giá trị thì KHÔNG đụng: cổng tự điền sẵn theo mã trên URL, ghi đè là đổi ý người khác.
   */
  async function fillDependentCombos(modal) {
    const chosen = [];
    let failed = 0;
    for (let index = 0; index < comboboxes(modal).length; index += 1) {
      const control = () => comboboxes(modal)[index];
      if (!control() || !isPlaceholder(control())) continue;

      await sleep(STEP_PAUSE_MS);
      realClick(control());
      const panel = await waitFor(dropdownPanel, 3000, 150);
      if (!panel) {
        // Không mở nổi thì không thể biết ô này bắt buộc hay không -> tính là hỏng, để cán bộ xem.
        log(`ô ${index} không mở được danh sách`);
        failed += 1;
        continue;
      }
      // Danh sách phụ thuộc nạp bằng API: chờ tới lúc CÓ lựa chọn, đừng đọc vào lúc còn rỗng.
      const option = await waitFor(() => optionNodes(dropdownPanel() || panel)[0], 4000, 200);
      if (!option) {
        // Rỗng hẳn = ô không áp dụng cho hồ sơ này (cổng vẫn render). KHÔNG tính là hỏng, nếu không
        // mọi hồ sơ có ô tuỳ chọn đều bị chặn lại bắt cán bộ bấm tay.
        log(`ô ${index} không có lựa chọn nào — coi như không áp dụng`);
        realClick(control());
        await sleep(STEP_PAUSE_MS);
        continue;
      }
      const label = comboValue(option);
      realClick(option.closest('[role="option"], [cmdk-item], li') || option);
      const ok = await waitFor(() => !isPlaceholder(control()), 3000, 150);
      log(ok ? `ô ${index} đã chọn: ${label}` : `ô ${index} bấm xong nhưng chưa đổi`);
      if (ok) chosen.push(label); else failed += 1;
    }
    return { chosen, failed };
  }

  function confirmButton(modal) {
    return Array.from(modal.querySelectorAll("button"))
      .filter(visible)
      .find((node) => fold(node.textContent) === CONFIRM_LABEL) || null;
  }

  let lastAgencyAt = 0;

  async function agencyStage(arm, flow, modal) {
    if (Date.now() - lastAgencyAt < CLICK_COOLDOWN_MS) return;
    lastAgencyAt = Date.now();

    const wanted = String(flow.agency || "").trim();
    if (wanted && !await pickAgency(modal, wanted)) {
      // Không tự chọn được thì DỪNG HẲN: bấm "Xác nhận" lúc này là nộp vào cơ quan cổng đang để
      // sẵn, sai cơ quan tiếp nhận thì hồ sơ đi lạc mà không ai kê khai điều đó.
      await stop();
      return void toast(`Không tự chọn được "${wanted}" — mời chọn cơ quan rồi bấm Xác nhận.`, "warning");
    }

    // Cơ quan thực hiện xong -> cổng mới nạp "Đơn vị tiếp nhận" tương ứng. Điền nốt rồi mới xác nhận.
    const { chosen, failed } = await fillDependentCombos(modal);

    const confirm = confirmButton(modal);
    if (!confirm || confirm.disabled) {
      lastAgencyAt = Date.now();
      await stop();
      return void toast("Đã chọn cơ quan thực hiện. Mời bấm Xác nhận.", "success");
    }
    // Có ô CÓ lựa chọn mà đặt không được -> DỪNG, nhường cán bộ chọn tay. Bấm Xác nhận lúc này là
    // gửi hồ sơ thiếu thông tin tiếp nhận.
    if (failed) {
      lastAgencyAt = Date.now();
      await stop();
      return void toast(
        `Còn ${failed} ô chưa chọn được ở "Thông tin chung" — mời chọn nốt rồi bấm Xác nhận.`,
        "warning",
      );
    }
    const picked = [wanted, ...chosen].filter(Boolean);
    if (picked.length) toast(`Đã chọn: ${picked.join("; ")}.`, "success");
    await sleep(STEP_PAUSE_MS);
    log("bấm Xác nhận");
    realClick(confirm);
    await waitFor(() => formReady() || !findInfoModal(), 8000, 300);
    // Cooldown tính từ lúc XONG: cả lượt này mất hàng chục giây, tính từ lúc bắt đầu thì nhịp
    // watcher kế tiếp đã hết hạn nghỉ và làm lại từ đầu.
    lastAgencyAt = Date.now();
  }

  // ---------- điều phối ----------
  let loginNotified = false;

  async function park(arm) {
    await setArm({ ...arm, at: Date.now() });   // gia hạn: công dân xác thực bao lâu cũng được
    if (loginNotified) return;
    loginNotified = true;
    notifyPopup();
    const hint = window.__HCC_LOGIN__?.loginHint?.(loginState()) || "Cổng tỉnh yêu cầu đăng nhập.";
    toast(`${hint} Xong là trợ lý bấm "Nộp hồ sơ" tiếp.`, "info");
  }

  async function stop() {
    await clearArm();
    ensureWatcher(false);
    notifyPopup();
  }

  let lastSeen = "";

  async function step(arm, flow) {
    // Mỗi nhịp in ĐANG THẤY GÌ (chỉ khi đổi): lúc trợ lý không bấm, đây là chỗ duy nhất cho biết
    // nó đang kẹt ở màn đăng nhập, chưa thấy nút, hay đang mở modal.
    const seen = [
      loginBlocked() ? "chan-dang-nhap" : "",
      formReady() ? "da-vao-form" : "",
      findInfoModal() ? "modal-thong-tin-chung" : "",
      `nut-nop-ho-so:${submitButtons().length}`,
    ].filter(Boolean).join(" ");
    if (seen !== lastSeen) {
      lastSeen = seen;
      log("trạng thái trang:", seen);
    }

    // 1. Cổng tỉnh có phiên đăng nhập riêng: chưa qua thì mọi thao tác dưới đều bấm vào khoảng không.
    if (loginBlocked()) return void await park(arm);
    loginNotified = false;

    // 2. Đã vào bước kê khai -> xong việc của chặng này.
    if (formReady()) {
      await stop();
      return void toast("Đã vào bước kê khai. Mời quét và nhập dữ liệu.", "success");
    }

    // 3. Modal "Thông tin chung" đang mở -> chọn cơ quan rồi Xác nhận.
    const modal = findInfoModal();
    if (modal) return void await agencyStage(arm, flow, modal);

    // 4. Còn ở bảng danh sách -> bấm "Nộp hồ sơ" đúng dòng.
    await submitStage(flow);
  }

  let lastStandDownReason = "";

  /**
   * Cờ có thuộc về cổng tỉnh đang mở không. Không phải thì script này đứng ngoài hoàn toàn.
   *
   * In LÝ DO đứng ngoài (mỗi lý do một lần) — bản đầu im lặng nên lúc trợ lý không bấm gì, không
   * có cách nào biết là thiếu cờ, sai host hay cờ hết hạn.
   */
  async function armForThisHost() {
    const arm = await readArm();
    if (arm === undefined) return undefined;          // đọc lỗi -> chưa kết luận gì
    const standDown = (reason) => {
      if (reason !== lastStandDownReason) {
        lastStandDownReason = reason;
        log("đứng ngoài —", reason);
      }
      return null;
    };
    if (!arm) {
      return standDown('chưa có cờ "Đi đến thủ tục". Mở panel, chọn thủ tục rồi bấm nút đi tới.');
    }
    const flow = arm.provincePortalFlow;
    if (!flow) {
      return standDown(
        `thủ tục "${arm.procedureKey || "?"}" không khai provincePortalFlow trong ke_khai_links.json`
        + " (hoặc cờ được ghi trước khi nạp lại extension — bấm 'Đi đến thủ tục' lại một lượt).",
      );
    }
    if (String(flow.host || "") !== location.hostname) {
      return standDown(`cờ dành cho host "${flow.host}", trang này là "${location.hostname}"`);
    }
    if (Date.now() - Number(arm.at || 0) > ARM_TTL_MS) {
      await clearArm();
      return standDown("cờ đã quá hạn 30 phút — bấm 'Đi đến thủ tục' lại");
    }
    lastStandDownReason = "";
    return { arm, flow };
  }

  let timer = null;
  let busy = false;

  function ensureWatcher(active) {
    if (active && !timer) timer = setInterval(() => void tick(), 1000);
    if (!active && timer) { clearInterval(timer); timer = null; }
  }

  async function tick() {
    if (busy) return;
    const ctx = await armForThisHost();
    if (ctx === undefined) return;      // đọc cờ lỗi một nhịp -> thử lại nhịp sau, đừng tự tắt
    if (!ctx) return void ensureWatcher(false);
    busy = true;
    try {
      await step(ctx.arm, ctx.flow);
    } catch (error) {
      console.warn("[QuangNinh] lỗi giữa chừng:", error);
    } finally {
      busy = false;
    }
  }

  /** Đúng trang nộp hồ sơ của một mã TTHC — chỗ cán bộ TRÔNG ĐỢI trợ lý làm việc. */
  function onDossierPage() {
    try {
      const url = new URL(location.href);
      return url.pathname.startsWith("/nop-ho-so") && !!url.searchParams.get("MaTTHC");
    } catch (_) { return false; }
  }

  let toldOnPage = false;

  async function boot() {
    if (await armForThisHost()) {
      log("cờ thuộc cổng tỉnh này — bắt đầu theo dõi");
      ensureWatcher(true);
      return void tick();
    }
    // Đứng ngoài NGAY TRÊN trang nộp hồ sơ thì phải nói ra màn hình: bản trước chỉ im lặng nên
    // cán bộ chỉ thấy "trợ lý không bấm gì" mà không biết là thiếu cờ.
    if (!toldOnPage && onDossierPage() && lastStandDownReason) {
      toldOnPage = true;
      toast(`Trợ lý chưa nhận việc ở trang này: ${lastStandDownReason}`, "warning");
    }
  }

  // Cờ có thể được ghi SAU khi trang đã tải (mở panel rồi bấm "Đi đến thủ tục" ở tab khác).
  try {
    chrome.storage?.onChanged?.addListener((changes, area) => {
      if (area === "local" && changes[ARM_KEY]) void boot();
    });
  } catch (_) { /* ngữ cảnh không có storage thì thôi */ }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => void boot(), { once: true });
  } else {
    void boot();
  }
})();
