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
  // State machine điền 7 trang khối dữ liệu. Khóa RIÊNG, KHÔNG dùng chung autofill_fillall_state của
  // HkdOnline: state machine bên đó sẽ tự resume theo khóa ấy và lôi menu/id của HKD vào cổng này.
  const FILL_KEY = "autofill_enterprise_fillall";
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
    // Mỗi trang con là một file .aspx riêng và tên KHÔNG theo quy tắc nào: Address_of_head_office.aspx,
    // EnterpriseName.aspx, DW_ENT_BUSINESS_LINE_VWListingInsUpd.aspx... Đoán theo tên file là sai.
    // Menu trái "KHỐI DỮ LIỆU" có mặt ở MỌI trang trong hồ sơ và không có ở wizard -> dùng làm mốc.
    const path = String(location.pathname || "");
    if (!/\/online\/Forms\/APP\//i.test(path)) return false;
    // Registration.aspx là WIZARD (chọn loại đăng ký/loại hình), không phải trang trong hồ sơ.
    // Loại trừ tường minh để không bao giờ nhầm hai chặng với nhau.
    if (/\/Registration\.aspx$/i.test(path)) return false;
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

    // Đã vào tới khối dữ liệu hồ sơ = xong phần điều hướng. KHÔNG toast: panel tự chạy tiếp chặng
    // quét + điền nên thông báo ở đây chỉ là nhiễu giữa luồng.
    if (stage === "dossier") {
      await clearArm();
      return;
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
      // Trợ lý tự chạy (không cần cán bộ bấm gì) nên phải TÔN TRỌNG lựa chọn tay: cổng tick sẵn
      // "Thành lập mới"; nếu ô đang tick là loại khác thì chính cán bộ đã đổi — đứng im, không ghi đè
      // để khỏi kéo họ sang nhánh thành lập mới khi họ đang định làm thay đổi/cấp lại.
      const registrationRadios = wizardRadios("CtlType");
      const spec = {
        value: arm.registrationType || "NEW",
        labelMatch: arm.registrationLabel || "Thành lập mới",
      };
      const checked = registrationRadios.find((node) => node.checked);
      const wanted = pickRadio(registrationRadios, spec);
      if (checked && wanted && checked !== wanted) {
        return void await stop(
          `Cán bộ đang chọn "${String(radioLabel(checked)).replace(/\s+/g, " ").trim()}" ở bước Chọn loại đăng ký nên trợ lý không tự đi tiếp.`,
        );
      }
      const next = await chooseThenFindNext(
        nextArm,
        registrationRadios,
        spec,
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

  // ======================================================================================
  // ENGINE ĐIỀN 7 TRANG KHỐI DỮ LIỆU
  // Mỗi trang: mở menu trái → điền → bấm Lưu (postback tải lại trang) → trang kế. State nằm ở
  // chrome.storage nên sống qua từng lần tải lại; mỗi lần script chạy lại chỉ làm ĐÚNG một bước.
  // ======================================================================================

  /**
   * Đặc tả từng trang. `probe` là control CHỈ trang đó có — nhận diện trang bằng control thay vì
   * breadcrumb vì breadcrumb cổng này rút gọn khác nhãn menu. `save` là name nút Lưu: cổng KHÔNG
   * đặt tên đồng nhất (btnSave / BtnSave / BtnSaveNotVSIC) nên phải khai riêng từng trang.
   */
  const PAGE_SPEC = {
    "hinh-thuc-dang-ky": {
      label: "Hình thức đăng ký",
      path: "dw_reorganizationedit.aspx",
      probe: '[name^="ctl00$C$REORGCtl"]',
      save: "ctl00$C$btnSave",
    },
    "dia-chi": {
      label: "Địa chỉ",
      path: "address_of_head_office.aspx",
      probe: 'input[name="ctl00$C$ADDRCtl$STREET_NUMBERFld"]',
      save: "ctl00$C$btnSave",
    },
    "nganh-nghe-kinh-doanh": {
      label: "Ngành nghề kinh doanh",
      path: "dw_ent_business_line_vwlistinginsupd.aspx",
      probe: 'input[name="ctl00$C$newBusinessLineCode"]',
      save: "ctl00$C$BtnSaveNotVSIC",
    },
    "ten-doanh-nghiep": {
      label: "Tên doanh nghiệp",
      path: "enterprisename.aspx",
      probe: 'input[name="ctl00$C$NAMEFld"]',
      save: "ctl00$C$BtnSave",
    },
    "thong-tin-ve-von": {
      label: "Thông tin về vốn",
      path: "dw_capitaledit.aspx",
      probe: '[name^="ctl00$C$UC_DW_CAPITALEditCtl"]',
      save: "ctl00$C$btnSave",
    },
    "thong-tin-ve-co-phan": {
      label: "Thông tin về cổ phần",
      path: "informationofshare.aspx",
      probe: '[name^="ctl00$C$UC_DW_OTHEREditCtl"]',
      save: "ctl00$C$btnSave",
    },
    "thong-tin-ve-thue": {
      label: "Thông tin về thuế",
      path: "taxinformation.aspx",
      probe: '[name^="ctl00$C$UC_DW_TAXEditCtl"]',
      save: "ctl00$C$btnSave",
    },
    "nguoi-nop-ho-so": {
      label: "Người nộp hồ sơ",
      path: "contactperson.aspx",
      probe: 'input[name="ctl00$C$PERSCtl$FULL_NAMEFld"]',
      save: "ctl00$C$btnSave",
    },
  };

  const MAX_PAGE_RETRIES = 3;
  // Trần TỔNG số nhịp của cả phiên điền. 7 trang × (điều hướng + điền + lưu) không thể quá con số
  // này; vượt là đang lặp -> dừng có kiểm soát thay vì quay vòng mãi.
  const MAX_TOTAL_STEPS = 60;

  async function readFillState() {
    try {
      const res = await chrome.storage.local.get(FILL_KEY);
      return res?.[FILL_KEY] || null;
    } catch (_) { return null; }
  }
  async function setFillState(state) {
    try { await chrome.storage.local.set({ [FILL_KEY]: state }); } catch (_) { /* ignore */ }
  }
  async function clearFillState() {
    try { await chrome.storage.local.remove(FILL_KEY); } catch (_) { /* ignore */ }
  }

  /** Trang đang mở là trang nào trong 7 trang khối dữ liệu (null nếu không phải trang nào). */
  /** Đã vào trong hồ sơ chưa (kể cả đang đứng ở trang GỐC khối dữ liệu, chưa mở trang con nào). */
  function inDossier() {
    return detectStage() === "dossier" || !!currentFillPage();
  }

  function currentFillPage() {
    // ĐƯỜNG DẪN là bằng chứng chắc nhất (mỗi trang con một file .aspx riêng); control chỉ dùng cho
    // các trang chưa biết tên file.
    const path = String(location.pathname || "").toLowerCase();
    for (const [key, spec] of Object.entries(PAGE_SPEC)) {
      if (spec.path && path.endsWith(spec.path)) return key;
    }
    for (const [key, spec] of Object.entries(PAGE_SPEC)) {
      if (document.querySelector(spec.probe)) return key;
    }
    return null;
  }

  /** Link menu trái theo NHÃN — cổng không đặt id ổn định cho từng mục nên khớp theo chữ. */
  function findMenuLink(label) {
    const wanted = fold(label);
    if (!wanted) return null;
    const links = Array.from(document.querySelectorAll("a")).filter(visible);
    return links.find((link) => fold(link.textContent) === wanted)
      || links.find((link) => {
        const text = fold(link.textContent);
        return text && (text.startsWith(wanted) || wanted.startsWith(text));
      })
      || null;
  }

  /**
   * Gọi postback của WebForms mà KHÔNG đi qua `javascript:` URL.
   *
   * Menu trái render href="javascript:__doPostBack('ctl00$C$...','')" — CSP của cổng
   * ("script-src 'self'") CHẶN thẳng loại URL này nên link.click() im lặng không làm gì, engine cứ
   * đứng mãi ở onPage:null rồi bỏ qua trang. Tự điền __EVENTTARGET rồi submit form là đường duy
   * nhất còn lại (engine hộ kinh doanh cũng làm đúng vậy).
   */
  function doAspPostback(target, arg) {
    const et = document.getElementById("__EVENTTARGET");
    const ea = document.getElementById("__EVENTARGUMENT");
    const form = (et && et.form) || document.forms?.namedItem?.("aspnetForm") || document.querySelector("form");
    if (!form || !et) return false;
    et.value = target;
    if (ea) ea.value = arg || "";
    try {
      form.submit();
      return true;
    } catch (error) {
      console.warn("[EnterpriseFill] submit form lỗi:", error);
      return false;
    }
  }

  /** Mở một mục menu trái; ưu tiên postback trực tiếp, click chỉ là lưới đỡ. */
  function openMenuLink(link) {
    const href = link.getAttribute ? String(link.getAttribute("href") || "") : "";
    const match = href.match(/__doPostBack\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]\s*\)/);
    if (match && doAspPostback(match[1], match[2])) return true;
    try { link.click(); return true; } catch (_) { return false; }
  }

  /** Nút Lưu ĐANG BẬT (bỏ qua nút đang disabled). */
  function findEnabledSaveButton(spec) {
    const byName = document.querySelector(`[name="${spec.save}"]`);
    if (byName && visible(byName) && !byName.disabled) return byName;
    // Lưới đỡ khi cổng đổi tên control: bắt theo chữ trên nút.
    return Array.from(document.querySelectorAll('input[type="submit"], button'))
      .filter(visible)
      .find((node) => !node.disabled && fold(buttonText(node)) === "luu") || null;
  }

  /** Nút Lưu có tồn tại trên trang không, kể cả đang disabled — để phân biệt "không có" với "chưa bật". */
  function saveButtonExists(spec) {
    const byName = document.querySelector(`[name="${spec.save}"]`);
    if (byName) return true;
    return Array.from(document.querySelectorAll('input[type="submit"], button'))
      .some((node) => fold(buttonText(node)) === "luu");
  }

  /**
   * Cổng để nút Lưu DISABLED cho tới khi form có thay đổi hợp lệ; validator chạy sau sự kiện change
   * nên ngay sau khi điền nút vẫn còn mờ. Kiểm một phát rồi bỏ qua là mất luôn bước lưu (đúng lỗi
   * "không thấy nút Lưu ở trang: Ngành nghề kinh doanh" trong log). Chờ tối đa ~3s cho nút bật.
   */
  async function waitForSaveButton(spec) {
    for (let i = 0; i < 12; i += 1) {
      const button = findEnabledSaveButton(spec);
      if (button) return button;
      await sleep(250);
    }
    return null;
  }

  /** Bấm Lưu rồi chờ xem cổng có tải lại trang không (postback). */
  function clickSaveDetectReload(button) {
    return new Promise((resolve) => {
      let done = false;
      const onLeave = () => { if (!done) { done = true; resolve(true); } };
      window.addEventListener("beforeunload", onLeave, { once: true });
      window.addEventListener("pagehide", onLeave, { once: true });
      try { button.click(); } catch (_) { /* ignore */ }
      setTimeout(() => {
        if (done) return;
        done = true;
        window.removeEventListener("beforeunload", onLeave);
        window.removeEventListener("pagehide", onLeave);
        resolve(false);
      }, 2600);
    });
  }

  function progress(state, text) {
    const step = Math.min((state.done || []).length + 1, state.order.length);
    H.setRunProgressText?.(`Đang điền trang ${step}/${state.order.length} — ${text}\n(đừng thao tác tới khi xong)`);
  }

  async function finishFill(state) {
    await clearFillState();
    const filled = (state.done || []).length;
    const payload = state.attachPayload;
    const files = payload && payload.files;
    const attachments = payload && payload.attachments;

    // Chặng cuối: đính kèm. Cổng này DÙNG CHUNG component đính kèm với HkdOnline (cùng icon ⚙
    // BLCtl_ImgAttachmentSettings, cùng modal #attId/#tblAtt, cùng ô #FileUploadCtl) nên tái sử dụng
    // luôn state machine đã chạy ổn định ở business-registration.js thay vì viết lại.
    if (Array.isArray(files) && files.length && Array.isArray(attachments) && attachments.length
      && typeof H.startAttachAllBusiness === "function") {
      H.setRunProgressText?.(`✓ Đã điền xong ${filled}/${state.order.length} trang. Bắt đầu đính kèm hồ sơ…\n(đừng thao tác tới khi xong)`);
      await H.startAttachAllBusiness(files, attachments);
      setTimeout(() => H.stepAttachAll && H.stepAttachAll(), 400);
      return;
    }
    H.endFillAllUI?.(`✓ Đã điền xong ${filled}/${state.order.length} trang. Vui lòng rà soát rồi bấm Nộp.`);
  }

  /**
   * Một nhịp của state machine: chạy lại từ đầu sau MỖI lần cổng tải lại trang.
   *
   * Điều khiển theo TRANG ĐANG ĐỨNG, không theo "trang mục tiêu": đang ở trang nào mà còn dữ liệu
   * chưa điền thì điền ngay trang đó, xong mới mở trang kế theo thứ tự. Bản trước bắt trang hiện tại
   * phải KHỚP trang mục tiêu — cổng nhảy sang trang khác một nhịp là kẹt, đếm đủ số lần thử rồi bỏ
   * qua cả trang dù trang đó đang mở sẵn trước mắt.
   */
  // Hai nguồn cùng gọi state machine: resume() ở mỗi lần tải trang, và lệnh bấm nút từ popup. Không
  // khoá thì cả hai cùng vào nhánh "điền trang này" trước khi lượt đầu kịp ghi state -> điền và bấm
  // Lưu HAI lần trên cùng một trang.
  let filling = false;
  async function stepFill() {
    if (filling) return;
    filling = true;
    try { await stepFillOnce(); } finally { filling = false; }
  }

  /** Nhịp kế tiếp phải chờ khoá nhả — gọi thẳng stepFill() trong thân sẽ bị chính khoá chặn. */
  function scheduleStepFill(delay = 0) {
    setTimeout(stepFill, delay);
  }

  async function stepFillOnce() {
    const state = await readFillState();
    if (!state || !Array.isArray(state.order)) return;
    state.done = Array.isArray(state.done) ? state.done : [];
    state.navTries = state.navTries && typeof state.navTries === "object" ? state.navTries : {};
    state.steps = Number(state.steps || 0) + 1;
    if (state.steps > MAX_TOTAL_STEPS) {
      console.warn("[EnterpriseFill] vượt trần số nhịp — dừng để không lặp vô hạn.");
      await clearFillState();
      H.endFillAllUI?.("⚠ Dừng vì lặp quá nhiều bước. Mời kiểm tra lại hồ sơ và điền tay phần còn thiếu.");
      return;
    }

    const onPage = currentFillPage();
    console.log("[EnterpriseFill] nhịp:", {
      onPage,
      daXong: state.done,
      conLai: state.order.filter((key) => !state.done.includes(key)),
    });

    // 1) Đang đứng ở trang có dữ liệu và chưa xử lý → điền + Lưu ngay, bất kể thứ tự.
    if (onPage && !state.done.includes(onPage) && Array.isArray(state.pages && state.pages[onPage])) {
      const spec = PAGE_SPEC[onPage];
      progress(state, spec.label);
      const fields = state.pages[onPage].filter((f) => !String(f.name || "").startsWith("__"));
      if (onPage === "nguoi-nop-ho-so") {
        // Trang này phải "hỏi cổng trước, điền sau": vai trò người nộp chỉ chốt được sau khi biết
        // tài khoản đang đăng nhập là ai. Trả true = đang chờ postback, dừng nhịp này.
        if (await prepareSubmitterPage(state, fields)) return;
      }
      if (fields.length) {
        try {
          await H.fillFormStandard?.(fields);
        } catch (error) {
          console.warn("[EnterpriseFill] điền trang lỗi:", spec.label, error);
        }
        await sleep(500);
      }
      // Đánh dấu đã xử lý TRƯỚC khi bấm Lưu: bấm xong là postback, không còn cơ hội ghi state.
      state.done = [...state.done, onPage];
      await setFillState(state);
      const save = await waitForSaveButton(spec);
      if (!save) {
        // Nút có mà không bật = form không có gì thay đổi (backend không trả field cho trang này,
        // hoặc trang cần thao tác riêng như thêm ngành nghề bằng mã số) -> bỏ qua là ĐÚNG.
        console.warn("[EnterpriseFill] bỏ qua lưu ở trang:", spec.label,
          saveButtonExists(spec) ? "(nút Lưu có nhưng không bật - form chưa đổi gì)" : "(không thấy nút Lưu)");
        return void scheduleStepFill();
      }
      const reloaded = await clickSaveDetectReload(save);
      if (!reloaded) return void scheduleStepFill();   // cổng không tải lại → đi tiếp ngay
      return;
    }

    // 2) Trang này không có gì để điền → mở trang KẾ TIẾP chưa xử lý theo đúng thứ tự menu.
    const next = state.order.find((key) => !state.done.includes(key));
    if (!next) return void finishFill(state);

    const spec = PAGE_SPEC[next];
    progress(state, spec.label);
    const tries = Number(state.navTries[next] || 0) + 1;
    state.navTries[next] = tries;
    if (tries > MAX_PAGE_RETRIES) {
      // Không mở được thì BỎ QUA trang này, đừng để kẹt cả luồng; trang sau vẫn được điền.
      console.warn("[EnterpriseFill] bỏ qua trang không mở được:", spec.label);
      state.done = [...state.done, next];
      await setFillState(state);
      return void scheduleStepFill();
    }
    await setFillState(state);

    const link = findMenuLink(spec.label);
    if (!link) {
      console.warn("[EnterpriseFill] không thấy mục menu:", spec.label);
      return void scheduleStepFill(800);
    }
    try { link.scrollIntoView && link.scrollIntoView({ block: "center" }); } catch (_) { /* ignore */ }
    openMenuLink(link);
    // Bình thường cổng postback -> lượt tải trang sau tự gọi lại stepFill. Nhưng nếu link KHÔNG
    // điều hướng (không phải __doPostBack, hoặc bị chặn) thì sẽ không còn nhịp nào đánh thức state
    // machine -> kẹt cứng. Hẹn nhịp dự phòng để navTries còn đếm được và bỏ qua trang nếu cần.
    scheduleStepFill(3000);
  }

  // ---------- TRANG "NGƯỜI NỘP HỒ SƠ" (ContactPerson.aspx) ----------
  // Port cơ chế của thủ tục hộ kinh doanh (content/procedures/business-registration.js): KHÔNG tự
  // đoán vai trò từ giấy tờ, mà nhờ cổng đổ nhân thân TÀI KHOẢN ĐANG ĐĂNG NHẬP xuống trước, rồi đối
  // chiếu với các CCCD có trong hồ sơ để chốt "người có thẩm quyền ký" hay "người được ủy quyền".
  //
  // Giá trị radio ở cổng NÀY khác HkdOnline: tự ký là IS_REPRESENTATIVE_BUTTON (HKD dùng
  // IS_SIGNER_BUTTON), ủy quyền vẫn là IS_AUTHORIZED_BUTTON.
  const SUBMITTER = {
    role: "ctl00$C$PERS_SUBGroup",
    roleSelf: "IS_REPRESENTATIVE_BUTTON",
    roleAuthorized: "IS_AUTHORIZED_BUTTON",
    copy: "ctl00$C$btnIS_SIGNER",          // nút "Sao chép thông tin đăng ký tài khoản"
    editable: "ctl00$C$PERSCtl$PERSONChange", // checkbox "Sửa đổi dữ liệu" (mở khoá ô readonly)
    fullName: "ctl00$C$PERSCtl$FULL_NAMEFld",
    docNo: "ctl00$C$PERSCtl$PERS_DOC_NOFld",
    addressPrefix: "ctl00$C$PERSCtl$ADDRCCtl",
  };

  const byName = (name) => document.querySelector(`[name="${name}"]`);
  const digitsOf = (value) => String(value || "").replace(/\D/g, "");

  /**
   * Trả TRUE nghĩa là đã tiêu thụ nhịp này (đang chờ postback) — người gọi phải dừng.
   * Trả FALSE nghĩa là đã xong phần đặc thù, nhánh điền chung chạy tiếp bình thường.
   */
  async function prepareSubmitterPage(state, fields) {
    // Chặng 1: nhờ cổng điền nhân thân tài khoản. Chỉ bấm khi ô họ tên còn trống — bấm lại khi đã
    // có dữ liệu là ghi đè mất thứ vừa điền.
    const nameInput = byName(SUBMITTER.fullName);
    const alreadyHasName = String(nameInput && nameInput.value || "").trim();
    if (!state.submitterCopied && !alreadyHasName) {
      const copyBtn = byName(SUBMITTER.copy);
      if (copyBtn && !copyBtn.disabled) {
        state.submitterCopied = true;
        await setFillState(state);
        console.log("[EnterpriseFill] bấm 'Sao chép thông tin đăng ký tài khoản'");
        const reloaded = await clickSaveDetectReload(copyBtn);
        if (reloaded) return true;          // postback -> lượt tải trang sau đi tiếp
      }
    }
    state.submitterCopied = true;

    // Mở khoá các ô readonly để còn ghi đè được địa chỉ/liên hệ.
    const editable = byName(SUBMITTER.editable);
    if (editable && !editable.checked) {
      editable.click();
      if (!editable.checked) {
        editable.checked = true;
        editable.dispatchEvent(new Event("change", { bubbles: true }));
      }
      await sleep(300);
    }

    // Chặng 2: đối chiếu tài khoản đang đăng nhập với các CCCD trong hồ sơ để chốt vai trò.
    // Đọc từ page fields GỐC: tham số `fields` đã bị lọc bỏ mọi field "__" trước khi truyền vào.
    const rawFields = (state.pages && state.pages["nguoi-nop-ho-so"]) || [];
    const candidates = (rawFields.find((f) => f.name === "__identityCandidates") || {}).value || [];
    const accountId = digitsOf(byName(SUBMITTER.docNo) && byName(SUBMITTER.docNo).value);
    const accountName = fold(byName(SUBMITTER.fullName) && byName(SUBMITTER.fullName).value);
    const matched = (Array.isArray(candidates) ? candidates : []).find((card) =>
      (card.docNo && accountId && digitsOf(card.docNo) === accountId)
      || (accountName && fold(card.fullName) === accountName));

    // Không có CCCD nào trong hồ sơ để đối chiếu -> GIỮ mặc định của cổng, không đoán bừa vai trò
    // (chọn nhầm "ủy quyền" là bắt cán bộ phải kê khai thêm cả khối Thông tin Ủy quyền).
    if (Array.isArray(candidates) && candidates.length) {
      const authorized = !matched;
      const radio = document.querySelector(
        `input[type="radio"][name="${SUBMITTER.role}"][value="${authorized ? SUBMITTER.roleAuthorized : SUBMITTER.roleSelf}"]`
      );
      console.log("[EnterpriseFill] vai trò người nộp:", authorized ? "được ủy quyền" : "có thẩm quyền ký",
        { accountId, accountName, soCccdTrongHoSo: candidates.length });
      if (radio && selectNativeRadio(radio)) await sleep(400);
    }

    // Vai trò do ĐÂY quyết định (dựa trên tài khoản thật), KHÔNG để nhánh điền chung quyết định lại.
    // Mapper luôn phát sẵn PERS_SUBGroup = "người có thẩm quyền ký" làm mặc định; nếu để nguyên trong
    // danh sách điền thì fillFormStandard sẽ tick đè NGƯỢC lại ngay sau khi ta vừa chọn "được ủy
    // quyền" — đúng hiện tượng "tích người được ủy quyền rồi chỉnh lại".
    for (let i = fields.length - 1; i >= 0; i -= 1) {
      if (String(fields[i].name || "").includes("PERS_SUBGroup")) fields.splice(i, 1);
    }

    // Người đăng nhập KHÔNG phải người trong hồ sơ -> KHÔNG điền gì cả.
    // Khối nhân thân/địa chỉ ở đây là của CHÍNH TÀI KHOẢN đang đăng nhập: cổng ghi đè lại theo tài
    // khoản khi lưu, nên cố điền dữ liệu của người khác vừa vô ích vừa làm sai hồ sơ.
    if (!matched) {
      console.log("[EnterpriseFill] tài khoản không phải người trong hồ sơ — giữ nguyên khối người nộp.");
      fields.length = 0;
      await setFillState(state);
      return false;
    }

    // Khớp rồi thì chỉ còn thiếu ĐỊA CHỈ: nút "Sao chép tài khoản" của cổng không đổ phần này.
    const address = matched.address;
    if (address && !fields.some((f) => String(f.name || "").includes("ADDRCCtl$CITY_IDFld"))) {
      fields.push(
        { name: `${SUBMITTER.addressPrefix}$COUNTRY_IDFld`, comp: "dom-select", value: address.quocGia || "Việt Nam" },
        { name: `${SUBMITTER.addressPrefix}$CITY_IDFld`, comp: "dom-select", value: address.tinh },
        { name: `${SUBMITTER.addressPrefix}$WARD_IDFld`, comp: "dom-select", value: address.xa },
        { name: `${SUBMITTER.addressPrefix}$STREET_NUMBERFld`, comp: "dom-input", value: address.diaChi },
      );
    }
    await setFillState(state);
    return false;
  }

  /** Popup gọi khi cán bộ bấm nút quét: nhận field 7 trang rồi chạy state machine. */
  async function startEnterpriseFillAll(message) {
    const pages = (message && message.pages) || {};
    const order = Object.keys(PAGE_SPEC).filter((key) => Array.isArray(pages[key]));
    if (!order.length) return { error: "Backend không trả field nào cho các trang khối dữ liệu." };
    if (!inDossier()) {
      // Còn ở wizard: TỰ MỞ HỒ SƠ luôn thay vì báo lỗi rồi bắt bấm lại. Popup đã có bước tiền kiểm
      // (getEnterpriseStage) nhưng nếu vì lý do gì bước đó không chạy thì lượt bấm vẫn phải có tác
      // dụng — cán bộ bấm nút là để trợ lý đi tiếp, không phải để nhận thông báo.
      const armed = await armFromFlow(message && message.enterpriseFlow);
      if (!armed) {
        return { error: "Chưa ở trong khối dữ liệu hồ sơ và không mở được hồ sơ. Vui lòng thử lại." };
      }
      start();
      return { ok: true, openingDossier: true };
    }
    // Giữ kế hoạch đính kèm do backend phân loại để dùng ở chặng cuối (khối "VĂN BẢN ĐÍNH KÈM").
    const attachPayload = (message && message.attachPayload) || null;
    await setFillState({ order, pages, done: [], navTries: {}, attachPayload });
    H.beginFillAllUI?.();
    setTimeout(stepFill, 60);
    return { ok: true, started: true, pages: order.length };
  }

  /** Đặt cờ chạy wizard từ dữ liệu popup gửi kèm (hoặc giữ cờ sẵn có nếu popup không gửi). */
  async function armFromFlow(flow) {
    const existing = await readArm();
    if (existing) return true;
    if (!flow || !flow.entityLabel) return false;
    await setArm({ ...flow, at: Date.now() });
    return true;
  }

  chrome.runtime?.onMessage?.addListener((msg, _sender, sendResponse) => {
    if (window.top !== window) return;
    // Popup hỏi đang ở bước nào. KHÔNG dùng lại tín hiệu detectProcedure của content.js vì đường đó
    // đi qua collectProcedureSignals và có thể thiếu hint nếu file này chưa kịp gắn vào namespace.
    if (msg?.action === "getEnterpriseStage") {
      sendResponse({ ok: true, stage: detectStage(), inDossier: inDossier() });
      return;
    }
    if (msg?.action !== "startEnterpriseFillAll") return;
    startEnterpriseFillAll(msg).then(sendResponse);
    return true;   // trả lời bất đồng bộ
  });

  // Mở ra namespace để soi/chạy tay từ console khi hỗ trợ cán bộ, và để test dựng được state machine.
  H.enterpriseFillPageSpec = PAGE_SPEC;
  H.startEnterpriseFillAll = startEnterpriseFillAll;
  H.stepEnterpriseFill = stepFill;
  H.currentEnterpriseFillPage = currentFillPage;
  H.isInEnterpriseDossier = inDossier;

  // Postback có thể chỉ thay UpdatePanel (không tải lại cả trang) -> rà thêm theo nhịp. Khoá chống
  // chạy chồng vì mỗi lượt có thể đang chờ AutoPostBack.
  let running = false;
  const start = () => {
    if (running) return;
    running = true;
    void run().finally(() => { running = false; });
  };

  // Mỗi lần cổng tải lại trang (sau khi bấm Lưu / mở menu) script chạy lại từ đầu: nối tiếp cả luồng
  // wizard (cờ ARM_KEY) lẫn luồng điền 7 trang (FILL_KEY).
  const resume = () => { start(); setTimeout(() => void stepFill(), 400); };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", resume, { once: true });
  } else {
    resume();
  }

  // Panel đặt cờ SAU khi trang đã tải xong (nhận diện thủ tục chạy trong iframe popup), lúc đó lượt
  // run() ở DOMContentLoaded đã kết thúc vì chưa thấy cờ. Không nghe storage thì cán bộ đang đứng
  // sẵn ở Registration.aspx sẽ chẳng thấy gì xảy ra cho tới lần tải trang kế.
  try {
    chrome.storage?.onChanged?.addListener((changes, area) => {
      if (area !== "local" || !changes[ARM_KEY]?.newValue) return;
      start();
    });
  } catch (_) { /* ignore */ }

  let lastStage = detectStage();
  setInterval(() => {
    const stage = detectStage();
    if (stage === lastStage) return;
    lastStage = stage;
    if (stage !== "unknown") start();
  }, 1000);
})();
