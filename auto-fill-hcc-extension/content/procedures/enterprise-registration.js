// Tự tiến tới thủ tục ĐĂNG KÝ THÀNH LẬP DOANH NGHIỆP trên Cổng đăng ký doanh nghiệp qua mạng
// (dangkyquamang.dkkd.gov.vn — ASP.NET WebForms, wizard `ctl00$C$myWizard`).
//
// Cùng mô hình "lên đạn bằng cờ storage" với content/agency-select.js: popup ghi cờ khi bấm
// "Đi đến thủ tục", script này đọc cờ rồi bấm hộ TRỌN BA BƯỚC để vào thẳng khối dữ liệu hồ sơ:
//   B1 Registration.aspx  "Chọn loại đăng ký"  -> radio $CtlType    = NEW (Thành lập mới) -> Tiếp theo
//   B2 Registration.aspx  "Chọn loại hình"     -> radio $CtlEntType = loại hình của THỦ TỤC ĐANG CHỌN
//                                                  (SC = công ty cổ phần, LLC2 = TNHH hai thành viên
//                                                  trở lên...) -> Tiếp theo
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
    // Loại hình do CỜ mang sang (panel ghi từ registry: enterpriseEntityLabel/Value). Wizard này
    // dùng chung cho MỌI loại hình nên tuyệt đối không mặc định về công ty cổ phần: thiếu nhãn mà
    // đoán bừa là mở nhầm loại hình, hồ sơ phải bỏ đi làm lại.
    const entityLabel = arm.entityLabel || "";
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
      if (!entityLabel && !arm.entityValue) {
        return void await stop("Chưa biết loại hình doanh nghiệp cần chọn — mời chọn tay rồi bấm Tiếp theo.");
      }
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
   *
   * THỨ TỰ KHAI Ở ĐÂY = THỨ TỰ ĐIỀN (state.order lọc theo đúng thứ tự này), nên phải bám đúng thứ
   * tự mục trong menu "KHỐI DỮ LIỆU" bên trái. Trang nào backend không trả field thì tự rụng khỏi
   * order — nhờ vậy CTCP và TNHH hai thành viên dùng chung một bảng: bên nào có trang nấy.
   *
   * Ba khoá phụ chỉ dùng cho các trang mới của loại hình TNHH:
   *  - `detailPath`: trang danh sách + form chi tiết là HAI file .aspx khác nhau (thành viên).
   *  - `notProbe`: control mà nếu CÓ thì trang KHÔNG phải trang này (chống nhận nhầm giữa hai form
   *    cùng dùng khối REPCtl$PERSCtl: người đại diện theo pháp luật vs người đại diện của tổ chức).
   *  - `addLabels`: chữ trên nút mở form thêm một dòng của trang danh sách.
   */
  // Nút "Tạo mới" của các trang DANH SÁCH. Đọc từ DOM thật của cổng:
  //   <input type="submit" name="ctl00$C$btnNew" value="Tạo mới" id="C_btnNew">
  // Khớp theo NAME/ID trước rồi mới tới chữ trên nút — chữ có thể đổi ("Thêm mới"), name thì không.
  const ADD_BUTTON_SELECTORS = ['input[name$="$btnNew"]', "#C_btnNew", '[id$="_btnNew"]'];
  // Nút "Trở về" của form chi tiết. DOM thật của cổng:
  //   <input type="submit" name="ctl00$C$btnBack" value="Trở về" id="C_btnBack">
  // Bấm Lưu xong cổng GIỮ NGUYÊN form chi tiết chứ không tự quay ra danh sách, nên phải tự bấm nút
  // này. Không bấm thì nhịp sau vẫn thấy form chi tiết đang mở và điền người kế tiếp ĐÈ LÊN form
  // của người vừa lưu — đúng lỗi "lặp lại 2 người" trên cổng thật.
  const BACK_BUTTON_SELECTORS = ['input[name$="$btnBack"]', "#C_btnBack", '[id$="_btnBack"]'];
  const BACK_BUTTON_LABELS = ["tro ve", "quay lai"];

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
      // Trang này LUÔN chạm trần số lượt điền, và đó là chuyện BÌNH THƯỜNG chứ không phải hỏng:
      // ô "tiền tố loại hình" (ctl00$C$DROP_NAME_TYPE) là dropdown AutoPostBack — cứ đặt giá trị
      // là cổng tải lại trang ngay, lệnh đánh dấu "đã xong" chạy sau đó chết theo trang. Mỗi lượt
      // tải lại vẫn điền đủ tên nên kết quả đúng, chỉ là phải đi hết trần mới thoát ra được.
      // Vì vậy KHÔNG bắn toast đỏ ở trang này — cảnh báo sai làm cán bộ tưởng hồ sơ điền hụt.
      // Vẫn giữ console.warn để khi cần còn lần được.
      quietFillCap: true,
    },
    "thong-tin-ve-von": {
      label: "Thông tin về vốn",
      path: "dw_capitaledit.aspx",
      probe: '[name^="ctl00$C$UC_DW_CAPITALEditCtl"]',
      save: "ctl00$C$btnSave",
    },
    "thong-tin-thanh-vien": {
      // Mục menu trỏ tới trang DANH SÁCH; mỗi thành viên là một lượt "Tạo mới" → form chi tiết →
      // Lưu → quay lại danh sách. Vòng lặp này nằm ở stepMemberListing/stepMemberDetail bên dưới.
      label: "Thông tin về thành viên",
      path: "dw_member_vwlisting.aspx",
      detailPath: "informationofmembers.aspx",
      probe: '[name^="ctl00$C$MEM_PCtl"]',
      save: "ctl00$C$btnSave",
      addSelectors: ADD_BUTTON_SELECTORS,
      addLabels: ["tao moi", "them moi", "them"],
    },
    "nguoi-dai-dien-phap-luat": {
      // Mục menu trỏ tới trang DANH SÁCH người đại diện, phải bấm "Tạo mới" mới mở được form nhập
      // (Information_of_Legal_representative.aspx) — giống mục thành viên. Chưa có tên file của
      // trang danh sách nên KHÔNG khai `path` cho nó: engine nhận theo ngữ cảnh, xem nhánh
      // "vừa mở mục menu xong mà chưa nhận ra trang" trong stepFillOnce.
      //
      // Khối REPCtl$PERSCtl dùng CHUNG với trang "người đại diện của tổ chức" nên probe một mình
      // không đủ: notProbe loại trừ bằng ô "Tên thành viên là tổ chức" vốn CHỈ trang tổ chức có.
      label: "Người đại diện theo pháp luật",
      path: "information_of_legal_representative.aspx",
      probe: '[name$="$REPCtl$PERSCtl$FULL_NAMEFld"]',
      notProbe: '[name$="$REPCtl$NameMemberdrFld"]',
      save: "ctl00$C$btnSave",
      addSelectors: ADD_BUTTON_SELECTORS,
      addLabels: ["tao moi", "them moi", "them"],
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
    "thong-tin-bao-hiem-xa-hoi": {
      // Trang này mới chỉ có ẢNH CHỤP MÀN HÌNH, chưa có HTML: không biết tên file .aspx lẫn tên
      // control. Nên nhận trang bằng chính ba lựa chọn in trên đó — bộ ba nhãn này không trang
      // nào khác của hồ sơ có, mà cổng đổi id/tên control cũng không đổi được chữ hiển thị.
      label: "Thông tin về bảo hiểm xã hội",
      probeLabels: ["hang thang", "03 thang mot lan", "06 thang mot lan"],
      save: "ctl00$C$btnSave",
    },
    "nguoi-dai-dien-to-chuc": {
      // Backend KHÔNG trả field cho trang này (chỉ dùng khi thành viên là TỔ CHỨC, bảng đặc tả ghi
      // "không áp dụng") nên nó không bao giờ vào order. Khai ở đây để currentFillPage() nhận đúng
      // trang — nếu không, probe của trang "người đại diện theo pháp luật" sẽ vơ nhầm nó.
      label: "Thông tin về đại diện của tổ chức",
      path: "dw_authorized_rep_p_vwlisting.aspx",
      detailPath: "infoauthorizedrepforforeignfoundere.aspx",
      probe: '[name$="$REPCtl$NameMemberdrFld"]',
      save: "ctl00$C$btnSave",
      addSelectors: ADD_BUTTON_SELECTORS,
      addLabels: ["tao moi", "them moi", "them"],
    },
    "nguoi-nop-ho-so": {
      label: "Người nộp hồ sơ",
      path: "contactperson.aspx",
      probe: 'input[name="ctl00$C$PERSCtl$FULL_NAMEFld"]',
      save: "ctl00$C$btnSave",
    },
  };

  const MAX_PAGE_RETRIES = 3;
  // Trần số lần ĐIỀN cho MỘT trang. Xem chú thích ở stepFillOnce: control AutoPostBack có thể làm
  // cổng tải lại trang ngay giữa lúc đang điền, nên một trang được điền lại vài lượt là BÌNH THƯỜNG
  // — nhưng quá số này là đang quay vòng, phải bỏ qua để cả luồng còn chạy tiếp.
  const MAX_FILL_TRIES = 3;
  // Trần TỔNG số nhịp của cả phiên điền. Tối đa 9 trang × (điều hướng + điền + lưu), cộng mỗi thành
  // viên một vòng (mở form + điền + lưu), cộng MỖI MÃ NGÀNH một postback riêng — hồ sơ thật đã gặp
  // bảng 11 dòng, mà trần cũ (90) không hề tính khoản này; vượt là đang lặp -> dừng có kiểm soát.
  const MAX_TOTAL_STEPS = 140;

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
      // Trang chỉ khai `probeLabels`: nhận theo CHỮ của các lựa chọn radio — dùng cho trang
      // chưa biết tên file .aspx lẫn tên control. Đòi CÓ ĐỦ mọi nhãn khai ở spec mới nhận, để
      // không vơ nhầm một trang khác tình cờ có một lựa chọn trùng chữ.
      if (spec.probeLabels) {
        if (spec.probeLabels.every((wanted) => !!findRadioByLabel(wanted))) return key;
        continue;
      }
      if (!spec.probe || !document.querySelector(spec.probe)) continue;
      // notProbe = "control này có mặt thì KHÔNG phải trang này". Không có nó thì hai form dùng
      // chung khối REPCtl$PERSCtl sẽ nhận nhầm nhau và điền dữ liệu người đại diện pháp luật vào
      // form người đại diện của tổ chức.
      if (spec.notProbe && document.querySelector(spec.notProbe)) continue;
      return key;
    }
    return null;
  }

  /** Đang đứng ở FORM CHI TIẾT của một trang danh sách (thành viên / đại diện tổ chức)? */
  function currentDetailPage() {
    const path = String(location.pathname || "").toLowerCase();
    for (const [key, spec] of Object.entries(PAGE_SPEC)) {
      if (spec.detailPath && path.endsWith(spec.detailPath)) return key;
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

  // ---------- TRANG "THÔNG TIN VỀ THÀNH VIÊN" (danh sách + form từng người) ----------
  /**
   * Nút theo CHỮ trên nút (cổng không đặt id ổn định cho nút "Tạo mới" của các trang danh sách).
   * Khớp ĐÚNG HỆT trước, rồi mới tới "chứa cụm chữ" — cổng có nơi ghi "Tạo mới", nơi ghi
   * "Thêm mới thành viên", nên đòi trùng tuyệt đối là hụt nút và bỏ qua cả mục.
   */
  /**
   * Bấm "Tạo mới" của một mục kiểu danh sách. Trả TRUE = đã bấm (nhịp này dừng tại đây).
   * Có trần thử để không bấm mãi khi cổng không chuyển trang.
   */
  async function openAddForm(state, key, spec) {
    const tryKey = `${key}#add`;
    const tries = Number(state.fillTries[tryKey] || 0) + 1;
    if (tries > MAX_FILL_TRIES) return false;
    const addButton = findAddButton(spec);
    console.log("[EnterpriseFill] trang danh sách:", {
      muc: spec.label, luot: tries, thayNutThem: !!addButton,
      chuTrenNut: addButton ? buttonText(addButton).trim() : null,
    });
    if (!addButton) return false;
    progress(state, spec.label);
    state.fillTries[tryKey] = tries;
    await setFillState(state);
    const reloaded = await clickSaveDetectReload(addButton);
    if (!reloaded) scheduleStepFill(800);
    return true;
  }

  /** Nút "Tạo mới" của một trang danh sách: NAME/ID trước (chắc), chữ trên nút sau (lưới đỡ). */
  function findAddButton(spec) {
    for (const selector of (spec && spec.addSelectors) || []) {
      const node = Array.from(document.querySelectorAll(selector))
        .find((el) => visible(el) && !el.disabled);
      if (node) return node;
    }
    return findButtonByTexts(spec && spec.addLabels);
  }

  /**
   * Radio theo NHÃN hiển thị, không cần biết cổng đặt tên control là gì.
   *
   * Dùng cho trang mà ta chỉ có ảnh màn hình chứ chưa có HTML. Khớp ĐÚNG HỆT trước rồi mới tới
   * "chứa cụm chữ": ba lựa chọn BHXH có chữ lồng nhau ("03 tháng một lần" / "06 tháng một lần")
   * nên khớp lỏng trước là tick nhầm kỳ đóng.
   */
  function findRadioByLabel(wanted) {
    const want = fold(wanted);
    if (!want) return null;
    const radios = Array.from(document.querySelectorAll('input[type="radio"]')).filter(visible);
    return radios.find((radio) => fold(radioLabel(radio)) === want)
      || radios.find((radio) => {
        const text = fold(radioLabel(radio));
        return !!text && text.includes(want);
      })
      || null;
  }

  /** Nút "Trở về" của form chi tiết: NAME/ID trước (chắc), chữ trên nút sau (lưới đỡ). */
  function findBackButton() {
    for (const selector of BACK_BUTTON_SELECTORS) {
      const node = Array.from(document.querySelectorAll(selector))
        .find((el) => visible(el) && !el.disabled);
      if (node) return node;
    }
    return findButtonByTexts(BACK_BUTTON_LABELS);
  }

  function findButtonByTexts(labels) {
    const wanted = (labels || []).map(fold).filter(Boolean);
    if (!wanted.length) return null;
    const nodes = Array.from(document.querySelectorAll(
      'input[type="submit"], input[type="button"], button, a'
    )).filter((node) => visible(node) && !node.disabled);
    return nodes.find((node) => wanted.includes(fold(buttonText(node))))
      || nodes.find((node) => {
        const text = fold(buttonText(node));
        return text && wanted.some((want) => text.includes(want));
      })
      || null;
  }

  // ---------- TRANG "NGÀNH NGHỀ KINH DOANH" (thêm từng mã bằng postback) ----------
  /**
   * Bảng ngành nghề là GridView dựng bằng postback: KHÔNG có control tĩnh nào để điền cả danh sách.
   * Mỗi mã là một lượt "gõ mã → bấm Thêm → cổng tải lại trang", nên trang này phải có state machine
   * riêng thay vì đi nhánh "điền hết field rồi Lưu" như các trang khác — nhánh chung chỉ gõ được ô
   * mã rồi bấm Lưu, tức là hồ sơ ra đời với đúng 0 ngành nghề.
   *
   * Cổng này dùng CHUNG component ngành nghề với HkdOnline nên thao tác DOM lấy nguyên bộ đã chạy
   * ổn định bên đó (H.businessLineOps), ở đây chỉ lo trình tự và state.
   */
  function businessLinePlan(state) {
    const raw = (state.pages && state.pages["nganh-nghe-kinh-doanh"]) || [];
    const value = (raw.find((f) => f.name === "__businessLines") || {}).value;
    return value && Array.isArray(value.codes) && value.codes.length ? value : null;
  }

  /** Field tĩnh của trang: BỎ ô mã ngành — ô đó là ô nhập tạm do vòng lặp thêm mã sở hữu. */
  function businessLineStaticFields(state) {
    return (state.pages["nganh-nghe-kinh-doanh"] || []).filter((f) => {
      const name = String(f.name || "");
      return !name.startsWith("__") && name !== "ctl00$C$newBusinessLineCode";
    });
  }

  /** Điền nốt phần tĩnh (ghi chú ngành ngoài Hệ thống VSIC) rồi Lưu, đóng trang ngành nghề. */
  async function saveBusinessLinePage(state) {
    const key = "nganh-nghe-kinh-doanh";
    const spec = PAGE_SPEC[key];
    const fields = businessLineStaticFields(state);
    if (fields.length) {
      try {
        await H.fillFormStandard?.(fields);
      } catch (error) {
        console.warn("[EnterpriseFill] điền ghi chú ngành nghề lỗi:", error);
      }
      await sleep(500);
    }
    state.done = [...state.done, key];
    await setFillState(state);
    const save = await waitForSaveButton(spec);
    if (!save) return void scheduleStepFill();
    const reloaded = await clickSaveDetectReload(save);
    if (!reloaded) scheduleStepFill();
  }

  async function stepBusinessLines(state) {
    const key = "nganh-nghe-kinh-doanh";
    const spec = PAGE_SPEC[key];
    progress(state, spec.label);
    const ops = H.businessLineOps;
    const plan = businessLinePlan(state);
    // Không có mã VSIC nào (hoặc engine hộ kinh doanh chưa nạp) → trang này chỉ còn phần ghi chú.
    if (!ops || !plan) {
      if (!ops) console.warn("[EnterpriseFill] thiếu H.businessLineOps — bỏ vòng lặp thêm mã ngành.");
      return void await saveBusinessLinePage(state);
    }

    const added = ops.getAddedCodes();
    const skipped = Array.isArray(state.blSkip) ? state.blSkip : [];
    const remaining = plan.codes.filter((code) => !added.includes(code) && !skipped.includes(code));
    console.log("[EnterpriseFill] ngành nghề:", {
      canThem: plan.codes, daDocDuocTrenBang: added, conLai: remaining,
      daBoQua: skipped, chinh: plan.main,
    });

    if (remaining.length) {
      const code = remaining[0];
      // Đếm lượt theo TỪNG MÃ, không dùng một biến đếm chung cho cả trang. Biến đếm chung có một
      // kiểu chết rất khó thấy: nếu vì lý do gì mà không đọc được mã vừa thêm trong bảng (cổng đổi
      // id bảng chẳng hạn), mã đó mãi nằm đầu `remaining` nên engine tiêu hết lượt vào ĐÚNG NÓ và
      // các mã sau không bao giờ được thử. Đếm theo mã thì mã hỏng bị bỏ lại sau vài lượt và vòng
      // lặp luôn tiến tới mã kế.
      state.blTries = (state.blTries && typeof state.blTries === "object") ? state.blTries : {};
      const tries = Number(state.blTries[code] || 0) + 1;
      state.blTries[code] = tries;
      if (tries > 2) {
        state.blSkip = [...skipped, code];
        console.warn("[EnterpriseFill] bỏ mã ngành không thêm được sau 2 lượt:", code);
        await setFillState(state);
        return void scheduleStepFill();
      }
      await setFillState(state);
      const reloaded = await ops.addOneCode(code);
      if (reloaded) return;                       // postback → nhịp sau xử lý mã kế
      await setFillState(state);
      return void scheduleStepFill();
    }
    const missed = Array.isArray(state.blSkip) ? state.blSkip : [];
    if (missed.length) {
      console.warn("[EnterpriseFill] các mã ngành không thêm được:", missed);
      toast(`Chưa thêm được ${missed.length} mã ngành (${missed.join(", ")}) — mời thêm tay trên trang Ngành nghề kinh doanh.`, "warn");
    }

    // Ngành chính: một lượt duy nhất, đánh dấu TRƯỚC vì nút Cập nhật chính cũng là postback.
    if (plan.main && !state.blMainDone && !ops.isMainSet(plan.main)) {
      state.blMainDone = true;
      await setFillState(state);
      if (await ops.setMainAndUpdate(plan.main)) return;
    }

    // Tên ngành trên hồ sơ chi tiết hơn tên chính thức theo mã VSIC ("Chi tiết: Kinh doanh vận tải
    // hàng bằng ôtô") → ghi vào ô mô tả của đúng dòng đó.
    if (!state.blDescDone) {
      state.blDescDone = true;
      let changed = 0;
      try {
        changed = ops.fillDescriptions(plan, null);
      } catch (error) {
        console.warn("[EnterpriseFill] điền mô tả ngành nghề lỗi:", error);
      }
      await setFillState(state);
      if (changed) {
        const update = ops.findUpdateButton();
        if (update && await clickSaveDetectReload(update)) return;
      }
    }

    return void await saveBusinessLinePage(state);
  }

  /** Danh sách thành viên backend gửi kèm — mỗi người MỘT bộ field đã dựng sẵn. */
  function memberList(state) {
    const raw = (state.pages && state.pages["thong-tin-thanh-vien"]) || [];
    const value = (raw.find((f) => f.name === "__members") || {}).value;
    return Array.isArray(value) ? value : [];
  }

  /**
   * Trang này có DỮ LIỆU THẬT để nhập không (khác "backend có trả khoá cho trang này").
   *
   * enrich_all() của backend trả ĐỦ khoá cho MỌI trang, kể cả trang mà lượt đọc hồ sơ không rút được
   * field nào — mảng rỗng. Với trang thường thì vô hại (không điền gì, nút Lưu không bật). Nhưng với
   * trang kiểu DANH SÁCH (thành viên, người đại diện theo pháp luật) engine sẽ bấm "Tạo mới" rồi mở
   * một form TRỐNG, đánh dấu xong và đi tiếp — cán bộ nhận về một bản ghi rỗng mà KHÔNG có lời cảnh
   * báo nào. Đó đúng là cảnh "Danh sách trống!" ở mục Người đại diện theo pháp luật trên hồ sơ thật.
   */
  function pageHasData(pages, key) {
    const fields = (pages && pages[key]) || [];
    if (!Array.isArray(fields) || !fields.length) return false;
    if (key === "thong-tin-thanh-vien") {
      const members = (fields.find((f) => f && f.name === "__members") || {}).value;
      return Array.isArray(members) && members.length > 0;
    }
    return fields.some((f) => f && !String(f.name || "").startsWith("__"));
  }

  /**
   * Những gì lượt đọc hồ sơ THỰC SỰ rút được, tính theo trang — in ra đầu mỗi phiên điền.
   * Thiếu thành viên hay thiếu người đại diện là chuyện của khâu ĐỌC HỒ SƠ, không phải của engine;
   * không nói ra thì cán bộ chỉ phát hiện sau khi hồ sơ đã lưu thiếu.
   */
  function runSummary(pages) {
    const all = pages || {};
    const members = (((all["thong-tin-thanh-vien"] || [])
      .find((f) => f && f.name === "__members") || {}).value) || [];
    const lines = (((all["nganh-nghe-kinh-doanh"] || [])
      .find((f) => f && f.name === "__businessLines") || {}).value) || {};
    return {
      businessLines: Array.isArray(lines.codes) ? lines.codes.length : 0,
      members: Array.isArray(members) ? members.length : 0,
      hasLegalRep: pageHasData(all, "nguoi-dai-dien-phap-luat"),
      emptyPages: Object.keys(PAGE_SPEC)
        .filter((key) => Array.isArray(all[key]) && !pageHasData(all, key)),
    };
  }

  /** Trang danh sách mà hồ sơ không có dữ liệu: BÁO cho cán bộ rồi bỏ qua, đừng tạo bản ghi rỗng. */
  async function skipEmptyListPage(state, key, spec) {
    console.warn("[EnterpriseFill] không có dữ liệu cho trang danh sách:", spec.label);
    toast(`Hồ sơ không đọc được dữ liệu cho mục "${spec.label}" — mời nhập tay mục này.`, "warn");
    if (!state.done.includes(key)) state.done = [...state.done, key];
    await setFillState(state);
    scheduleStepFill();
  }

  async function skipMemberPage(state) {
    if (!state.done.includes("thong-tin-thanh-vien")) {
      state.done = [...state.done, "thong-tin-thanh-vien"];
    }
    await setFillState(state);
    scheduleStepFill();
  }

  /** Trang DANH SÁCH: còn người chưa nhập thì bấm "Tạo mới", hết người thì chuyển trang kế. */
  async function stepMemberListing(state) {
    const spec = PAGE_SPEC["thong-tin-thanh-vien"];
    const members = memberList(state);
    const index = Number(state.memberIndex || 0);
    // Đã ra tới danh sách thì nhịp "bấm Trở về" coi như xong, dù nó tự về hay do engine bấm.
    if (state.memberPhase === "back") {
      state.memberPhase = "fill";
      await setFillState(state);
    }
    // Hồ sơ KHÔNG có thành viên nào (lượt đọc hồ sơ không rút được dòng nào của Danh sách thành
    // viên): phải BÁO, không lẳng lặng bỏ qua như trường hợp đã nhập xong hết.
    if (!members.length) return void await skipEmptyListPage(state, "thong-tin-thanh-vien", spec);
    if (index >= members.length) return void await skipMemberPage(state);

    progress(state, spec.label);
    const addButton = findAddButton(spec);
    console.log("[EnterpriseFill] danh sách thành viên:", {
      daNhap: index, tong: members.length, thayNutThem: !!addButton,
      chuTrenNut: addButton ? buttonText(addButton).trim() : null,
    });
    if (!addButton) {
      console.warn("[EnterpriseFill] không thấy nút thêm thành viên trên trang danh sách.");
      toast("Không mở được form thêm thành viên — mời nhập tay mục Thông tin về thành viên.", "warn");
      return void await skipMemberPage(state);
    }
    await setFillState(state);
    const reloaded = await clickSaveDetectReload(addButton);
    if (!reloaded) scheduleStepFill(800);
  }

  /**
   * Rời form chi tiết bằng nút "Trở về" để quay ra trang danh sách.
   *
   * Đây là bước BẮT BUỘC sau mỗi lần Lưu, không phải cho đẹp: cổng giữ nguyên form chi tiết sau khi
   * lưu, mà nhánh 0 của stepFillOnce hễ thấy form chi tiết là gọi stepMemberDetail — còn form đang
   * mở thì người kế tiếp bị điền đè lên form của người vừa lưu.
   */
  async function leaveMemberDetail(state, spec) {
    const back = findBackButton();
    state.memberPhase = "fill";
    await setFillState(state);
    console.log("[EnterpriseFill] rời form thành viên:", { thayNutTroVe: !!back });
    if (back) {
      const reloaded = await clickSaveDetectReload(back);
      if (!reloaded) scheduleStepFill(800);
      return;
    }
    // Không thấy nút Trở về: quay ra danh sách bằng chính mục menu, KHÔNG điền tiếp trên form này.
    const link = findMenuLink(spec.label);
    if (!link) {
      console.warn("[EnterpriseFill] không rời được form thành viên (thiếu cả nút Trở về lẫn mục menu).");
      toast("Không quay lại được danh sách thành viên — mời kiểm tra tay mục Thông tin về thành viên.", "warn");
      return void await skipMemberPage(state);
    }
    openMenuLink(link);
    scheduleStepFill(3000);
  }

  /**
   * FORM CHI TIẾT: điền ĐÚNG MỘT LƯỢT cho người thứ `memberIndex`, Lưu, rồi Trở về danh sách.
   *
   * Mỗi người CHỈ được điền một lượt — không còn vòng thử lại như các trang thường. Trang thường
   * điền lại thì cùng lắm ghi đè chính nó, còn ở đây mỗi lượt điền là một BẢN GHI trong danh sách:
   * điền lại là đẻ thêm người trùng, không có cách nào tự dọn.
   */
  async function stepMemberDetail(state) {
    const spec = PAGE_SPEC["thong-tin-thanh-vien"];
    const members = memberList(state);
    const index = Number(state.memberIndex || 0);
    // Vừa Lưu xong người trước → việc duy nhất còn lại ở form này là bấm "Trở về".
    if (state.memberPhase === "back") return void await leaveMemberDetail(state, spec);

    const member = members[index];
    // Lạc vào form chi tiết mà không còn ai để nhập: đóng trang này lại, đừng điền đè người cũ.
    if (!member) return void await leaveMemberDetail(state, spec);

    // Tiến độ để NGUYÊN dạng chung "Đang điền trang X/Y — <tên trang>" như thủ tục công ty cổ
    // phần: tên từng người chỉ là nhiễu giữa luồng, cán bộ cần biết đang ở trang nào là đủ.
    progress(state, spec.label);
    console.log("[EnterpriseFill] điền thành viên:", {
      thu: index + 1, tong: members.length, hoTen: member.fullName || null,
    });

    const fields = Array.isArray(member.fields) ? member.fields : [];
    if (fields.length) {
      try {
        await H.fillFormStandard?.(fields);
      } catch (error) {
        console.warn("[EnterpriseFill] điền thành viên lỗi:", member.fullName, error);
      }
      await sleep(500);
    }
    const save = await waitForSaveButton(spec);
    if (!save) {
      console.warn("[EnterpriseFill] không thấy nút Lưu ở form thành viên:", member.fullName);
      toast(`Không lưu được thành viên "${member.fullName || index + 1}" — mời nhập tay người này.`, "warn");
      // Vẫn tính là đã xử lý người này rồi Trở về: điền lại chỉ đẻ thêm bản ghi trùng.
      state.memberIndex = index + 1;
      return void await leaveMemberDetail(state, spec);
    }
    // Chốt chỉ số VÀ chuyển sang nhịp "Trở về" TRƯỚC khi bấm Lưu: bấm xong là postback, không còn
    // cơ hội ghi state. Nhờ ghi trước mà dù cổng tải lại trang ngay, nhịp sau vẫn biết người này đã
    // xong và chỉ còn phải bấm Trở về.
    state.memberIndex = index + 1;
    state.memberPhase = "back";
    await setFillState(state);
    const reloaded = await clickSaveDetectReload(save);
    if (!reloaded) {
      // Cổng không tải lại = validation chặn, người này CHƯA được lưu. Không điền lại (sẽ trùng),
      // chỉ báo để cán bộ nhập tay đúng một người.
      console.warn("[EnterpriseFill] bấm Lưu nhưng cổng không chuyển trang:", member.fullName);
      toast(`Thành viên "${member.fullName || index + 1}" chưa lưu được — mời kiểm tra tay người này.`, "warn");
      scheduleStepFill(800);
    }
  }

  // ---------- TRANG "THÔNG TIN VỀ BẢO HIỂM XÃ HỘI" ----------
  /**
   * Trang chỉ có một nhóm radio "Phương thức đóng bảo hiểm xã hội" (GĐN mục 10).
   *
   * Không đi nhánh điền chung vì nhánh đó cần TÊN CONTROL, mà tên control của trang này chưa
   * biết. Ở đây dò radio theo đúng chữ hiển thị — backend gửi sẵn nhãn chuẩn hoá qua __bhxhMethod.
   */
  async function stepSocialInsurance(state) {
    const key = "thong-tin-bao-hiem-xa-hoi";
    const spec = PAGE_SPEC[key];
    const fields = (state.pages && state.pages[key]) || [];
    const wanted = ((fields.find((f) => f && f.name === "__bhxhMethod") || {}).value || "").trim();
    progress(state, spec.label);

    // Đánh dấu đã xử lý TRƯỚC mọi thao tác: bấm Lưu là postback, không còn cơ hội ghi state.
    state.done = [...state.done, key];
    await setFillState(state);

    if (!wanted) {
      // Mục 10 là chọn 1 trong 3, hồ sơ không kê khai thì TUYỆT ĐỐI không chọn hộ.
      console.warn("[EnterpriseFill] hồ sơ không kê khai phương thức đóng BHXH — để trống.");
      toast("Hồ sơ không ghi phương thức đóng bảo hiểm xã hội — mời chọn tay mục này.", "warn");
      return void scheduleStepFill();
    }
    const radio = findRadioByLabel(wanted);
    console.log("[EnterpriseFill] bảo hiểm xã hội:", { canChon: wanted, thayO: !!radio });
    if (!radio) {
      console.warn("[EnterpriseFill] không thấy ô BHXH mang nhãn:", wanted);
      toast(`Không thấy lựa chọn "${wanted}" ở trang bảo hiểm xã hội — mời chọn tay.`, "warn");
      return void scheduleStepFill();
    }
    if (!radio.checked) {
      const label = radio.id ? document.querySelector(`label[for="${CSS.escape(radio.id)}"]`) : null;
      (label || radio).click();
      radio.dispatchEvent(new Event("change", { bubbles: true }));
      await sleep(300);
    }
    const save = await waitForSaveButton(spec);
    if (!save) {
      console.warn("[EnterpriseFill] trang BHXH: không bấm được Lưu.");
      return void scheduleStepFill();
    }
    const reloaded = await clickSaveDetectReload(save);
    if (!reloaded) scheduleStepFill(800);
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
    state.fillTries = state.fillTries && typeof state.fillTries === "object" ? state.fillTries : {};
    state.steps = Number(state.steps || 0) + 1;
    if (state.steps > MAX_TOTAL_STEPS) {
      console.warn("[EnterpriseFill] vượt trần số nhịp — dừng để không lặp vô hạn.");
      await clearFillState();
      H.endFillAllUI?.("⚠ Dừng vì lặp quá nhiều bước. Mời kiểm tra lại hồ sơ và điền tay phần còn thiếu.");
      return;
    }

    const onPage = currentFillPage();
    const onDetail = currentDetailPage();
    console.log("[EnterpriseFill] nhịp:", {
      onPage,
      onDetail,
      thanhVienThu: Number(state.memberIndex || 0) + 1,
      daXong: state.done,
      conLai: state.order.filter((key) => !state.done.includes(key)),
    });

    // 0) Form chi tiết của một trang danh sách: KHÔNG nằm trong `order` nên phải xử lý trước nhánh
    //    chung, nếu không currentFillPage() sẽ coi nó là trang danh sách và điền nhầm chỗ.
    //
    //    PHẢI có chốt `!done`: nhập xong người cuối mà cổng vẫn đứng ở form chi tiết thì nhánh này
    //    cứ nhận trang → stepMemberDetail thấy hết người → đánh dấu xong → hẹn nhịp → nhánh này lại
    //    nhận trang... quay vòng mãi ở mục thành viên và KHÔNG BAO GIỜ sang mục kế. Nhánh chung bên
    //    dưới có chốt này từ đầu, nhánh 0 thì thiếu — đúng lỗi "đã lưu nhưng không chuyển mục".
    if (onDetail === "thong-tin-thanh-vien"
      && !state.done.includes(onDetail)
      && Array.isArray(state.pages && state.pages[onDetail])) {
      return void await stepMemberDetail(state);
    }

    // 1) Đang đứng ở trang có dữ liệu và chưa xử lý → điền + Lưu ngay, bất kể thứ tự.
    if (onPage && !state.done.includes(onPage) && Array.isArray(state.pages && state.pages[onPage])) {
      const spec = PAGE_SPEC[onPage];
      // Trang danh sách thành viên không có ô nào để điền: việc của nó là mở form cho từng người.
      if (onPage === "thong-tin-thanh-vien") return void await stepMemberListing(state);
      // Ngành nghề cũng không điền một lượt được: mỗi mã là một postback riêng (xem stepBusinessLines).
      // Trang BHXH cũng không điền theo tên control được (xem stepSocialInsurance).
      if (onPage === "thong-tin-bao-hiem-xa-hoi") return void await stepSocialInsurance(state);
      if (onPage === "nganh-nghe-kinh-doanh") return void await stepBusinessLines(state);
      // Vài mục dùng CHUNG một .aspx cho cả DANH SÁCH lẫn form nhập: vào mục là thấy danh sách,
      // phải bấm "Tạo mới" mới hiện form. Nhận ra bằng: ĐÚNG trang (theo đường dẫn) nhưng control
      // của form CHƯA có, mà nút Tạo mới thì có. Không xử lý ở đây thì engine điền vào hư không rồi
      // đánh dấu xong, bỏ luôn cả mục.
      if (spec.addSelectors && !document.querySelector(spec.probe)) {
        if (!pageHasData(state.pages, onPage)) return void await skipEmptyListPage(state, onPage, spec);
        if (await openAddForm(state, onPage, spec)) return;
      }
      progress(state, spec.label);
      const fields = state.pages[onPage].filter((f) => !String(f.name || "").startsWith("__"));
      if (onPage === "nguoi-nop-ho-so") {
        // Trang này phải "hỏi cổng trước, điền sau": vai trò người nộp chỉ chốt được sau khi biết
        // tài khoản đang đăng nhập là ai. Trả true = đang chờ postback, dừng nhịp này.
        if (await prepareSubmitterPage(state, fields)) return;
      }
      // GHI SỐ LẦN THỬ TRƯỚC KHI ĐỤNG VÀO FORM. Vài control của cổng có AutoPostBack — rõ nhất là
      // dropdown tiền tố loại hình ở EnterpriseName.aspx: vừa đổi giá trị là cổng tải lại trang
      // NGAY, lệnh ghi state chạy sau đó chết theo trang, trang không bao giờ được đánh dấu xong →
      // lượt tải trang sau lại điền → lại postback → LẶP VÔ HẠN (đúng lỗi gặp trên cổng thật).
      // Ghi trước thì lượt sau ô đã mang đúng giá trị nên không đổi gì nữa, không còn postback, và
      // trần bên dưới bảo đảm không bao giờ quay vòng mãi.
      const fillTries = Number(state.fillTries[onPage] || 0) + 1;
      state.fillTries[onPage] = fillTries;
      await setFillState(state);
      if (fillTries > MAX_FILL_TRIES) {
        console.warn("[EnterpriseFill] hết lượt điền, chuyển trang:", spec.label,
          spec.quietFillCap ? "(trang có control AutoPostBack — chạm trần là bình thường)" : "");
        if (!spec.quietFillCap) {
          toast(`Trang "${spec.label}" điền mãi không xong — mời kiểm tra và điền tay trang này.`, "warn");
        }
        state.done = [...state.done, onPage];
        await setFillState(state);
        return void scheduleStepFill();
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

    // 1b) Vừa bấm mục menu xong mà KHÔNG nhận ra trang đang đứng: mục menu của vài trang trỏ tới
    //     DANH SÁCH (người đại diện theo pháp luật, thành viên...), phải bấm "Tạo mới" mới ra form
    //     nhập. Tên file trang danh sách không đoán được nên nhận theo NGỮ CẢNH: mục vừa mở là mục
    //     nào (state.navTarget), mục đó có khai nút thêm, và trang này có đúng nút đó.
    if (!onPage && !onDetail) {
      // Mục vừa bấm là mốc chính; nhưng lệnh ghi state có thể thua cuộc với lúc cổng chuyển trang,
      // nên thiếu nó thì lấy MỤC CHƯA XONG ĐẦU TIÊN — đằng nào cũng chính là mục đang mở dở.
      const target = (state.navTarget && !state.done.includes(state.navTarget))
        ? state.navTarget
        : state.order.find((key) => !state.done.includes(key));
      const targetSpec = target ? PAGE_SPEC[target] : null;
      // Đòi có DỮ LIỆU THẬT, không chỉ "backend có trả khoá cho trang" — xem pageHasData().
      const canAdd = !!(targetSpec && (targetSpec.addSelectors || targetSpec.addLabels)
        && pageHasData(state.pages, target));
      // Log KỂ CẢ khi không làm gì: đây là chỗ khó lần nhất (trang lạ, không biết vì sao đứng im).
      console.log("[EnterpriseFill] trang chưa nhận diện được:", {
        duongDan: String(location.pathname || ""),
        mucDangMo: target || null, coNutThemKhaiSan: canAdd,
        navTarget: state.navTarget || null,
      });
      // Đang đứng ở trang danh sách của một mục mà hồ sơ KHÔNG có dữ liệu: đánh dấu xong kèm cảnh
      // báo ngay tại đây. Để rơi xuống nhánh mở trang bên dưới thì engine cứ mở lại đúng mục này ba
      // lượt rồi mới bỏ qua bằng thông báo chung chung "không mở được trang".
      if (targetSpec && (targetSpec.addSelectors || targetSpec.addLabels)
        && Array.isArray(state.pages && state.pages[target]) && !pageHasData(state.pages, target)) {
        return void await skipEmptyListPage(state, target, targetSpec);
      }
      if (canAdd && await openAddForm(state, target, targetSpec)) return;
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
    // Nhớ mục vừa mở: trang danh sách của vài mục không đoán được tên file, nên nhánh bên trên
    // dựa vào đây để biết "trang lạ này chính là danh sách của mục vừa bấm".
    state.navTarget = next;
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

    // Chặng 2: đối chiếu tài khoản đang đăng nhập với hồ sơ để chốt vai trò.
    // Đọc từ page fields GỐC: tham số `fields` đã bị lọc bỏ mọi field "__" trước khi truyền vào.
    const rawFields = (state.pages && state.pages["nguoi-nop-ho-so"]) || [];
    const legalRep = (rawFields.find((f) => f.name === "__legalRep") || {}).value || null;
    const candidates = (rawFields.find((f) => f.name === "__identityCandidates") || {}).value || [];
    const accountId = digitsOf(byName(SUBMITTER.docNo) && byName(SUBMITTER.docNo).value);
    const accountName = fold(byName(SUBMITTER.fullName) && byName(SUBMITTER.fullName).value);
    const matched = (Array.isArray(candidates) ? candidates : []).find((card) =>
      (card.docNo && accountId && digitsOf(card.docNo) === accountId)
      || (accountName && fold(card.fullName) === accountName));

    /**
     * Vai trò người nộp, theo ĐÚNG luật của thủ tục hộ kinh doanh (business-registration.js):
     * đối chiếu TÀI KHOẢN ĐANG ĐĂNG NHẬP với người có thẩm quyền ký của hồ sơ — bên HKD là CHỦ HỘ,
     * bên này là NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT. Chỉ cần TRÙNG SỐ ĐỊNH DANH **HOẶC** HỌ TÊN là coi
     * như chính chủ (OCR hay rơi dấu nên không đòi trùng cả hai).
     *
     * Mốc này quan trọng hơn lối đối chiếu theo ảnh CCCD bên dưới: nhân thân người đại diện đọc
     * được từ Giấy đề nghị/Điều lệ nên LUÔN CÓ, còn ảnh CCCD thì cán bộ có thể không kèm — đúng
     * trường hợp làm bước chốt vai trò bị bỏ qua im lặng trước đây.
     *
     * Trả null = không đủ căn cứ → GIỮ mặc định của cổng, không đoán bừa (tick nhầm "ủy quyền" là
     * bắt cán bộ phải kê khai thêm cả khối Thông tin Ủy quyền).
     */
    function decideAuthorized() {
      const hasAccount = !!(accountId || accountName);
      if (hasAccount && legalRep && (legalRep.docNo || legalRep.fullName)) {
        const idMatch = !!(legalRep.docNo && accountId && digitsOf(legalRep.docNo) === accountId);
        const nameMatch = !!(accountName && fold(legalRep.fullName) === accountName);
        console.log("[EnterpriseFill] đối chiếu tài khoản với người đại diện theo pháp luật:",
          { accountId, accountName, legalRep, idMatch, nameMatch });
        return !(idMatch || nameMatch);
      }
      // Lưới đỡ: hồ sơ không đọc được người đại diện (vd thủ tục chưa khai trang đó) thì quay về
      // đối chiếu với các CCCD có trong hồ sơ như trước.
      if (Array.isArray(candidates) && candidates.length) return !matched;
      return null;
    }

    const authorized = decideAuthorized();
    if (authorized !== null) {
      const radio = document.querySelector(
        `input[type="radio"][name="${SUBMITTER.role}"][value="${authorized ? SUBMITTER.roleAuthorized : SUBMITTER.roleSelf}"]`
      );
      console.log("[EnterpriseFill] vai trò người nộp:", authorized ? "được ủy quyền" : "có thẩm quyền ký",
        { soCccdTrongHoSo: (candidates || []).length, coNguoiDaiDien: !!legalRep });
      if (radio && selectNativeRadio(radio)) await sleep(400);
    } else {
      console.log("[EnterpriseFill] không đủ căn cứ đối chiếu tài khoản → giữ nguyên vai trò cổng đang tick");
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
    // In NGAY những gì lượt đọc hồ sơ rút được. Hồ sơ thật đã gặp cảnh chỉ ra 1/2 thành viên và
    // không ra người đại diện theo pháp luật: engine chạy đúng hết nhưng hồ sơ vẫn thiếu, mà không
    // có dòng nào nói ra nên chỉ phát hiện được sau khi đã lưu lên cổng.
    const summary = runSummary(pages);
    console.log("[EnterpriseFill] hồ sơ đọc được:", {
      maNganhNghe: summary.businessLines,
      thanhVien: summary.members,
      coNguoiDaiDienPhapLuat: summary.hasLegalRep,
      trangKhongCoDuLieu: summary.emptyPages,
      trangSeDien: order,
    });
    if (summary.emptyPages.length) {
      toast(`Hồ sơ không đọc được dữ liệu cho ${summary.emptyPages.length} mục — trợ lý sẽ báo từng mục khi đi tới.`, "warn");
    }

    // Giữ kế hoạch đính kèm do backend phân loại để dùng ở chặng cuối (khối "VĂN BẢN ĐÍNH KÈM").
    const attachPayload = (message && message.attachPayload) || null;
    await setFillState({
      order, pages, done: [], navTries: {}, fillTries: {}, navTarget: "", memberIndex: 0,
      // "fill" = đang cần điền người thứ memberIndex; "back" = vừa Lưu xong, chỉ còn bấm Trở về.
      memberPhase: "fill",
      attachPayload,
    });
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
  H.enterprisePageHasData = pageHasData;
  H.enterpriseRunSummary = runSummary;
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
  // Bản engine cũ từng dựng banner "chờ xác nhận captcha". Cơ chế đó đã bỏ hẳn; dọn nốt phần tử
  // còn sót của bản cũ để cán bộ không nhìn thấy banner ma sau khi nạp lại extension (cổng có lúc
  // chỉ postback một phần nên trang không tải lại và không xoá hộ).
  try { document.getElementById("af-enterprise-captcha-gate")?.remove(); } catch (_) { /* ignore */ }

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
