// Tự tiến tới thủ tục ĐĂNG KÝ THÀNH LẬP DOANH NGHIỆP trên Cổng đăng ký doanh nghiệp qua mạng
// (dangkyquamang.dkkd.gov.vn — ASP.NET WebForms, wizard `ctl00$C$myWizard`).
//
// Cùng mô hình "lên đạn bằng cờ storage" với content/agency-select.js: popup ghi cờ khi bấm
// "Đi đến thủ tục", script này đọc cờ rồi bấm hộ TRỌN BA BƯỚC để vào thẳng khối dữ liệu hồ sơ:
//   B1 Registration.aspx  "Chọn loại đăng ký"  -> radio $CtlType    = NEW (Thành lập mới) -> Tiếp theo
//   B2 Registration.aspx  "Chọn loại hình"     -> radio $CtlEntType = SC  (Công ty cổ phần) -> Tiếp theo
//   B3 Registration.aspx  màn xác nhận         -> nút "Bắt đầu"
//   => DW_DOCUMENTEdit.aspx "Khối dữ liệu" (menu trái: Hình thức đăng ký, Địa chỉ, Ngành nghề...) = XONG.
//
// BỐN ĐIỂM KHÁC HkdOnline (hokinhdoanh.dkkd.gov.vn) BẮT BUỘC PHẢI CHIỀU:
// 1. ClientID NGẮN: cổng này render id "C_myWizard_CtlType_0", KHÔNG có tiền tố "ctl00_" như
//    HkdOnline -> mọi tra cứu radio đều theo NAME (`name$="$CtlType"`) vì NAME là UniqueID đầy đủ.
// 2. Mỗi bước là một POSTBACK tải lại trang: không giữ được state trong biến, nên cờ storage vừa là
//    "lệnh" vừa là "đang tới đâu"; script chạy lại từ đầu sau mỗi lần tải trang và tự nhận ra bước.
// 3. Nút bấm ("Tiếp theo"/"Bắt đầu") dò theo CHỮ, không theo id: id của FinishButton dài và khác
//    nhau giữa các bản wizard, còn nhãn thì cố định trên giao diện tiếng Việt.
// 4. Loại hình khớp NHÃN (<label for>) trước, value chỉ là lưới đỡ: chọn nhầm nhãn là mở nhầm loại
//    hình doanh nghiệp. Không khớp được nhãn lẫn value thì DỪNG và mời chọn tay.
(() => {
  if (location.hostname !== "dangkyquamang.dkkd.gov.vn") return;

  const H = window.__HCC__ || (window.__HCC__ = {});

  const ARM_KEY = "autofill_enterprise_autostart";
  const ARM_TTL_MS = 15 * 60 * 1000;   // cờ quá cũ = cán bộ đã bỏ giữa chừng
  const MAX_TRIES = 8;                 // trần lượt bấm cho CẢ ba bước, chặn vòng lặp
  const NEXT_LABEL = "tiep theo";
  const START_LABEL = "bat dau";
  // Menu trái của khối dữ liệu hồ sơ (ảnh màn hình cuối). Đủ đặc trưng để biết đã vào tới nơi.
  const DOSSIER_MARKERS = ["khoi du lieu", "hinh thuc dang ky"];

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

  // ---------- DOM của wizard ----------
  /** Radio theo NAME hậu tố (UniqueID "ctl00$C$myWizard$CtlType"); id ở cổng này ngắn nên không dùng. */
  function wizardRadios(nameSuffix) {
    return Array.from(
      document.querySelectorAll(`input[type="radio"][name$="$${nameSuffix}"]`)
    );
  }

  function buttonText(node) {
    return node.tagName === "INPUT" ? (node.value || "") : (node.textContent || "");
  }

  function findButtonByLabel(label) {
    return Array.from(document.querySelectorAll(
      'input[type="submit"], input[type="button"], input[type="image"], button, a'
    ))
      .filter(visible)
      .find((node) => !node.disabled && fold(buttonText(node)) === label) || null;
  }

  function onDossierPage() {
    if (!/DW_DOCUMENTEdit\.aspx$/i.test(String(location.pathname || ""))) return false;
    const body = fold(document.body?.innerText || "");
    return DOSSIER_MARKERS.every((marker) => body.includes(marker));
  }

  /**
   * Bước hiện tại của wizard. Dùng chung cho state machine LẪN tín hiệu nhận diện thủ tục gửi lên
   * popup — nên phải trả lời được cả khi KHÔNG có cờ "lên đạn".
   */
  function detectStage() {
    if (onDossierPage()) return "dossier";
    if (wizardRadios("CtlEntType").length) return "select-entity-type";
    if (wizardRadios("CtlType").length) return "select-registration-type";
    // Màn xác nhận đứng CUỐI wizard: hết radio chọn loại, chỉ còn nút "Bắt đầu".
    if (/\/Registration\.aspx$/i.test(String(location.pathname || "")) && findButtonByLabel(START_LABEL)) {
      return "confirm";
    }
    return "unknown";
  }

  // Cổng ĐKKD qua mạng dùng CHUNG domain cho mọi loại hình doanh nghiệp nên popup không suy được
  // thủ tục từ URL. Hint này nói "đang ở cổng doanh nghiệp, bước nào" để popup ĐỪNG giữ nhầm thủ tục
  // hộ kinh doanh của phiên trước; loại hình cụ thể do detectEnterpriseEntityLabel() bên dưới chốt.
  H.detectEnterpriseProcedureHint = () => {
    if (location.hostname !== "dangkyquamang.dkkd.gov.vn") return "";
    const stage = detectStage();
    return stage === "unknown" ? "portal" : stage;
  };

  const ENTITY_LABEL_MARKER = "loai hinh doanh nghiep";

  /**
   * Loại hình doanh nghiệp CỦA HỒ SƠ ĐANG MỞ, đọc từ khối "Thông tin về hồ sơ" trên
   * DW_DOCUMENTEdit.aspx (dòng "Loại hình doanh nghiệp: Công ty cổ phần").
   *
   * CHỈ đọc ở trang hồ sơ. Ở bước 2 của wizard cũng có nhãn loại hình nhưng cổng TICK SẴN dòng đầu
   * (Công ty TNHH một thành viên) — đọc radio đang checked ở đó sẽ nhận diện nhầm khi cán bộ chưa
   * chọn gì. Trang hồ sơ là nơi DUY NHẤT giá trị này đã được chốt.
   */
  H.detectEnterpriseEntityLabel = () => {
    if (location.hostname !== "dangkyquamang.dkkd.gov.vn") return "";
    if (detectStage() !== "dossier") return "";
    const lines = String(document.body?.innerText || "").split(/\r?\n/);
    for (let i = 0; i < lines.length; i += 1) {
      if (!fold(lines[i]).startsWith(ENTITY_LABEL_MARKER)) continue;
      // Bảng render "nhãn<TAB>giá trị" trên một dòng; vài bản tách nhãn và giá trị thành hai dòng.
      const inline = lines[i].split(":").slice(1).join(":").replace(/\s+/g, " ").trim();
      if (inline) return inline;
      const next = lines.slice(i + 1).find((line) => line.trim());
      return next ? next.replace(/\s+/g, " ").trim() : "";
    }
    return "";
  };

  if (window.top !== window) return;   // wizard nằm ở top frame; hint ở trên thì frame nào cũng trả được

  // KHÔNG trả lời getPortalFlowState ở cổng này: để content.js trả `unsupported` như mọi cổng
  // chuyên ngành khác. Nhờ vậy panel giữ nguyên màn quen thuộc (Loại thủ tục + Giấy tờ + Quét) với
  // thủ tục do detect tự nhận diện, thay vì hiện khối "Đi đến thủ tục" (Tỉnh/Xã + nút mở trang) —
  // khối đó chỉ hợp ở Cổng DVC quốc gia, nơi thật sự phải chọn cơ quan trước khi vào biểu mẫu.

  // ---------- cờ "lên đạn" ----------
  async function readArm() {
    try {
      const res = await chrome.storage.local.get(ARM_KEY);
      return res?.[ARM_KEY] || null;
    } catch (_) { return null; }
  }
  async function setArm(value) {
    try { await chrome.storage.local.set({ [ARM_KEY]: value }); } catch (_) { /* ignore */ }
  }
  async function clearArm() {
    try { await chrome.storage.local.remove(ARM_KEY); } catch (_) { /* ignore */ }
  }

  function toast(message, kind) {
    try { H.showPageToast?.(message, kind); } catch (_) { /* panel chưa sẵn */ }
  }

  async function stop(message) {
    await clearArm();
    if (message) {
      console.warn("[EnterpriseReg] dừng có kiểm soát:", message);
      toast(message, "warn");
    }
  }

  function radioLabel(radio) {
    if (radio.id) {
      let selector = radio.id;
      try { selector = CSS.escape(radio.id); } catch (_) { /* id của cổng không có ký tự lạ */ }
      const explicit = document.querySelector(`label[for="${selector}"]`);
      if (explicit) return explicit.textContent;
    }
    const cell = radio.closest("td, li, p, div");
    return cell?.textContent || radio.parentElement?.textContent || "";
  }

  /**
   * Khớp NHÃN trước (đúng hệt, rồi bắt đầu bằng), value là lưới đỡ cuối. Nhãn là thứ cán bộ nhìn
   * thấy nên sai nhãn là sai thủ tục; value ("NEW"/"SC") chỉ cứu khi OCR/nhãn cổng đổi chữ.
   */
  function pickRadio(radios, spec) {
    const wanted = fold(spec.labelMatch || "");
    if (wanted) {
      const exact = radios.find((node) => fold(radioLabel(node)) === wanted);
      if (exact) return exact;
      const prefixed = radios.find((node) => fold(radioLabel(node)).startsWith(wanted));
      if (prefixed) return prefixed;
    }
    if (spec.value) {
      const byValue = radios.find((node) => node.value === spec.value);
      if (byValue) return byValue;
    }
    return null;
  }

  function selectNativeRadio(node) {
    if (!node) return false;
    node.checked = true;
    node.dispatchEvent(new Event("input", { bubbles: true }));
    node.dispatchEvent(new Event("click", { bubbles: true }));
    node.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  // ---------- chạy từng bước ----------
  /**
   * Chọn radio rồi TRẢ VỀ nút "Tiếp theo" cho người gọi bấm. Radio ở cổng này có thể AutoPostBack:
   * vừa tick xong thì nhường một nhịp cho cổng tải lại; lượt sau thấy radio đã checked mới bấm.
   * Trả null = đã dừng có kiểm soát (đã báo cho cán bộ) hoặc đang chờ postback.
   */
  async function chooseThenFindNext(arm, radios, spec, stepName) {
    const target = pickRadio(radios, spec);
    if (!target) {
      await stop(`Không thấy lựa chọn "${spec.labelMatch}" ở bước ${stepName} — mời chọn tay rồi bấm Tiếp theo.`);
      return null;
    }
    if (!target.checked) {
      selectNativeRadio(target);
      await setArm({ ...arm, at: Date.now() });
      // AutoPostBack (nếu có) sẽ tải lại trang trong khoảng này; không reload thì bấm tiếp bên dưới.
      await sleep(1200);
      if (!target.isConnected) return null;   // trang đã đổi -> lượt chạy sau xử lý tiếp
    }
    const next = findButtonByLabel(NEXT_LABEL);
    if (!next) {
      await stop(`Đã chọn "${spec.labelMatch}" nhưng không thấy nút Tiếp theo ở bước ${stepName}.`);
      return null;
    }
    return next;
  }

  async function run() {
    const arm = await readArm();
    if (!arm) return;
    if (Date.now() - Number(arm.at || 0) > ARM_TTL_MS) return void await clearArm();

    const stage = detectStage();

    // Đã vào tới khối dữ liệu hồ sơ = xong phần điều hướng, nhường lại cho cán bộ/bước điền.
    if (stage === "dossier") {
      await clearArm();
      return void toast(`Đã mở hồ sơ ${arm.procedureLabel || "đăng ký thành lập doanh nghiệp"}. Mời quét và nhập dữ liệu.`, "success");
    }
    // Chưa tới wizard (màn đăng nhập ĐKKD, trang chủ cổng, trang trung gian): GIỮ cờ để lượt điều
    // hướng sau chạy tiếp — cán bộ không phải bấm "Đi đến thủ tục" lần nữa.
    if (stage === "unknown") return;

    const tries = Number(arm.tries || 0) + 1;
    if (tries > MAX_TRIES) {
      return void await stop("Trợ lý đã thử mở thủ tục nhiều lần nhưng cổng chưa chuyển bước — mời thao tác tay.");
    }
    const entityLabel = arm.entityLabel || "Công ty cổ phần";
    const nextArm = { ...arm, tries, at: Date.now() };

    if (stage === "select-registration-type") {
      toast(`Đang mở thủ tục ${arm.procedureLabel || "đăng ký thành lập " + entityLabel.toLowerCase()}…`, "success");
      const next = await chooseThenFindNext(
        nextArm,
        wizardRadios("CtlType"),
        { value: arm.registrationType || "NEW", labelMatch: arm.registrationLabel || "Thành lập mới" },
        "Chọn loại đăng ký",
      );
      if (!next) return;
      await setArm(nextArm);
      next.click();
      return;
    }

    if (stage === "select-entity-type") {
      const next = await chooseThenFindNext(
        nextArm,
        wizardRadios("CtlEntType"),
        { value: arm.entityValue || "", labelMatch: entityLabel },
        "Chọn loại hình",
      );
      if (!next) return;
      await setArm(nextArm);
      next.click();
      return;
    }

    // stage === "confirm": bấm "Bắt đầu" để cổng tạo hồ sơ và chuyển sang DW_DOCUMENTEdit.aspx.
    // KHÔNG xóa cờ ở đây: lượt chạy trên trang khối dữ liệu mới là nơi chốt "xong" và báo cho cán bộ.
    const start = findButtonByLabel(START_LABEL);
    if (!start) {
      return void await stop("Không thấy nút Bắt đầu ở bước xác nhận — mời bấm tay để vào hồ sơ.");
    }
    await setArm(nextArm);
    start.click();
  }

  // Postback có thể chỉ thay UpdatePanel (không tải lại cả trang) -> rà thêm theo nhịp. Khoá chống
  // chạy chồng vì mỗi lượt có thể đang chờ AutoPostBack.
  let running = false;
  const start = () => {
    if (running) return;
    running = true;
    void run().finally(() => { running = false; });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }

  let lastStage = detectStage();
  setInterval(() => {
    const stage = detectStage();
    if (stage === lastStage) return;
    lastStage = stage;
    if (stage !== "unknown") start();
  }, 1000);
})();
