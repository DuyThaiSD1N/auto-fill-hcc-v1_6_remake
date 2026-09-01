// Thủ tục ĐĂNG KÝ KINH DOANH (đăng ký hộ KD 8 trang: fill-all, ngành nghề, copy-person, cascade địa chỉ).
// Procedure-specific — tách khỏi content.js. Namespace window.__TLND__.
(() => {
  const H = window.__TLND__ || (window.__TLND__ = {});
  const { sleep, norm, fieldCandidates, setNativeValue, waitFor, readAcctContact,
    fillFormStandard, findStandardInput, findStandardSelect, isPostbackAddressField } = H;

  function foldBusinessPageText(value) {
    return norm(String(value || "")
      .replace(/Đ/g, "D")
      .replace(/đ/g, "d")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, ""));
  }

  const BUSINESS_PAGE_LABELS = {
    "hinh-thuc-dang-ky": "Hình thức đăng ký",
    "dia-chi": "Địa chỉ",
    "nganh-nghe-kinh-doanh": "Ngành nghề kinh doanh",
    "ten-ho-kinh-doanh": "Tên hộ kinh doanh",
    "chu-ho-kinh-doanh": "Thông tin về chủ hộ kinh doanh",
    "thong-tin-ve-von": "Thông tin về vốn",
    "thong-tin-ve-thue": "Thông tin về thuế",
    "cham-dut-hoat-dong": "Chấm dứt hoạt động",
    "thong-tin-de-nghi-cap-lai": "Thông tin đề nghị cấp lại GCN/GXNTĐ",
    "nguoi-nop-ho-so": "Người nộp hồ sơ",
  };
  const BUSINESS_CREATE_STEP_DELAY_MS = 2500;

  function currentBusinessPageLabel() {
    const sitemap = document.querySelector("#ctl00_LV4_SiteMapPath1")
      || document.querySelector('[id*="SiteMapPath"]');
    if (!sitemap) return "";
    const parts = Array.from(sitemap.querySelectorAll("span"))
      .map((node) => norm(node.textContent))
      .filter(Boolean);
    return parts[parts.length - 1] || norm(sitemap.textContent);
  }

  function findBusinessPageLink(label) {
    const wanted = foldBusinessPageText(label);
    if (!wanted) return null;
    const links = Array.from(document.querySelectorAll(".left-menu a, #ctl00_C_BLCtl_CtlList a"));
    return links.find((link) => foldBusinessPageText(link.textContent) === wanted) ||
      links.find((link) => {
        const text = foldBusinessPageText(link.textContent);
        return text && (text.includes(wanted) || wanted.includes(text));
      });
  }

  function detectBusinessPageKey() {
    const label = currentBusinessPageLabel();
    const wanted = foldBusinessPageText(label);
    if (!wanted) return { pageKey: null, label: "" };
    // Breadcrumb trang nghiệp vụ dùng tên "Thông báo quyết định giải thể", trong khi menu trái
    // dùng "Chấm dứt hoạt động". Đây là cùng một trang Dissolution.aspx theo HTML thực tế.
    if (wanted.includes("thong bao quyet dinh giai the") || wanted.includes("cham dut hoat dong")) {
      return { pageKey: "cham-dut-hoat-dong", label };
    }
    // Breadcrumb của DW_RE_ISSUANCEEdit.aspx rút gọn khác nhãn menu trái.
    if (wanted.includes("thong tin cap lai gcn gxn") || wanted.includes("de nghi cap lai gcn gxntd")) {
      return { pageKey: "thong-tin-de-nghi-cap-lai", label };
    }
    // So khớp theo độ trùng từ (token overlap) thay vì substring, vì breadcrumb có thể rút gọn
    // nhãn (vd "Thông tin vốn" trên breadcrumb vs "Thông tin về vốn" ở menu). Chọn trang trùng
    // nhiều từ nhất → phân biệt được vốn/thuế (đều có "thông tin").
    const wantedTokens = wanted.split(" ").filter(Boolean);
    let best = null;
    let bestScore = 0;
    for (const [key, lbl] of Object.entries(BUSINESS_PAGE_LABELS)) {
      const candSet = new Set(foldBusinessPageText(lbl).split(" ").filter(Boolean));
      const overlap = wantedTokens.filter((t) => candSet.has(t)).length;
      if (overlap > bestScore) {
        bestScore = overlap;
        best = key;
      }
    }
    const enough = bestScore >= 2 || (bestScore >= 1 && wantedTokens.length === 1);
    return { pageKey: enough ? best : null, label };
  }

  function businessNodeVisible(node) {
    if (!node) return false;
    const style = getComputedStyle(node);
    const rect = node.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  }

  function isBusinessChangeMainRoot(registrationType, page) {
    if ((!registrationType.includes("thay doi") && !registrationType.includes("cap lai")) || page.pageKey) return false;
    const pathname = String(window.location?.pathname || "");
    if (!/\/DW_DOCUMENTEdit\.aspx$/i.test(pathname)) return false;
    const currentLabel = foldBusinessPageText(currentBusinessPageLabel());
    const dataBlock = document.getElementById("ctl00_C_BLCtl_LblFilterExpand_DB");
    const leftMenu = document.getElementById("ctl00_C_BLCtl_CtlList");
    return currentLabel === "khoi du lieu"
      && !!dataBlock && foldBusinessPageText(dataBlock.textContent).includes("khoi du lieu")
      && !!leftMenu;
  }

  function isBusinessCreateMainRoot(registrationType, page) {
    if (!registrationType.includes("thanh lap moi") || page.pageKey) return false;
    const currentLabel = foldBusinessPageText(currentBusinessPageLabel());
    const dataBlock = document.getElementById("ctl00_C_BLCtl_LblFilterExpand_DB");
    const leftMenu = document.getElementById("ctl00_C_BLCtl_CtlList");
    return currentLabel === "khoi du lieu"
      && !!dataBlock && foldBusinessPageText(dataBlock.textContent).includes("khoi du lieu")
      && !!leftMenu;
  }

  // Wizard thay đổi dùng chung Registration.aspx nhưng mỗi bước có một marker riêng. Không dựa URL
  // vì URL không đổi qua bốn postback và các trang nội dung lại dùng chung với luồng thành lập mới.
  function detectBusinessChangeStage() {
    const markers = [
      ["select-registration", "ctl00_C_myWizard_LblQuestion1", "chon loai dang ky truc tuyen"],
      ["search-business", "ctl00_C_myWizard_Label2", "tim kiem ho kinh doanh de tien hanh dang ky thay doi"],
      ["select-change", "ctl00_C_myWizard_Label11", "chon loai dang ky thay doi"],
      ["confirm", "ctl00_C_myWizard_Label12", "xac nhan thong tin dang ky"],
    ];
    for (const [stage, id, phrase] of markers) {
      const node = document.getElementById(id);
      if (node && businessNodeVisible(node) && foldBusinessPageText(node.textContent).includes(phrase)) {
        return { stage, pageKey: null };
      }
    }

    // ASP.NET đôi lúc giữ heading trong DOM nhưng layout của span trả rect=0 (đặc biệt sau khi
    // extension/panel vừa mount), khiến kiểm tra visible phía trên bỏ sót. Các control dưới đây là
    // chữ ký cấu trúc riêng của từng WizardStep và ổn định hơn nội dung/khả năng hiển thị heading.
    if (document.getElementById("ctl00_C_myWizard_CtlType")
      || document.getElementById("ctl00_C_myWizard_CtlType_1")) {
      return { stage: "select-registration", pageKey: null };
    }
    if (document.getElementById("ctl00_C_myWizard_GDT_CODEFld")
      || document.getElementById("ctl00_C_myWizard_AmenHOUSEHOLDUIDFld")
      || document.getElementById("ctl00_C_myWizard_IMP_BUSINESS_REG_NUMBERFbl")
      || document.getElementById("ctl00_C_myWizard_PERS_DOC_NOFbl")) {
      return { stage: "search-business", pageKey: null };
    }
    if (document.getElementById("ctl00_C_myWizard_CtlAmendmentType")
      || document.getElementById("ctl00_C_myWizard_CtlAmendmentType_0")) {
      return { stage: "select-change", pageKey: null };
    }
    if (document.getElementById("ctl00_C_myWizard_FinishNavigationTemplateContainerID_FinishButton")) {
      return { stage: "confirm", pageKey: null };
    }
    // Trang chính REI có thể được mở trực tiếp; nhận diện từ field nghiệp vụ ngay cả khi breadcrumb
    // chưa render xong để cho phép tiếp tục từ đúng bước hiện tại.
    if (document.getElementById("ctl00_C_REI_REASONTxt")
      && (document.getElementById("ctl00_C_REI_TYPE_IDChBox")
        || document.getElementById("ctl00_C_REI_TYPE_IDChBox_0"))) {
      return { stage: "main", pageKey: "thong-tin-de-nghi-cap-lai", label: currentBusinessPageLabel() };
    }
    const page = detectBusinessPageKey();
    const registrationType = foldBusinessPageText(
      document.getElementById("ctl00_C_INFOCtl_DOCUMENT_TYPE_IDFld")?.textContent || ""
    );
    // Cùng page/menu được dùng cho thành lập mới. Chỉ nhận main khi chính hồ sơ trên cổng xác nhận
    // loại thay đổi; nếu là "Thành lập mới" phải báo sai luồng ngay, không sửa nhầm hồ sơ.
    if (page.pageKey && (registrationType.includes("thay doi") || registrationType.includes("cap lai"))) {
      return { stage: "main", pageKey: page.pageKey, label: page.label };
    }
    // DW_DOCUMENTEdit.aspx là trang tổng quan "Khối dữ liệu": chưa thuộc trang con nào nhưng đã có
    // đủ menu và metadata hồ sơ. Cho phép bắt đầu tại đây rồi state machine tự mở pageOrder[0].
    if (isBusinessChangeMainRoot(registrationType, page)) {
      return { stage: "main-root", pageKey: null, label: page.label };
    }
    console.warn("[ChangeHKD] không nhận diện được bước", {
      pathname: String(window.location?.pathname || ""),
      breadcrumb: currentBusinessPageLabel(),
      registrationType,
      hasWizard: !!document.querySelector('[id^="ctl00_C_myWizard_"]'),
    });
    return { stage: "unknown", pageKey: null };
  }

  // Thành lập mới có ba màn bootstrap trước 8 khối dữ liệu. Nhận diện bằng control/metadata
  // nghiệp vụ thật của WebForms; URL Registration.aspx không đổi qua các full postback.
  function detectBusinessCreateStage() {
    const host = String(window.location?.hostname || "").toLowerCase();
    if (host !== "hokinhdoanh.dkkd.gov.vn") return { stage: "unknown", pageKey: null };

    const pathname = String(window.location?.pathname || "");
    if (/\/HkdOnline\/?$/i.test(pathname) || /\/HkdOnline\/Default\.aspx$/i.test(pathname)) {
      const link = Array.from(document.querySelectorAll("a.AspNet-Menu-Link, .PrettyMenu a"))
        .find((node) => foldBusinessPageText(node.textContent) === "dang ky ho kinh doanh");
      if (link) return { stage: "home", pageKey: null };
    }

    const typeTable = document.getElementById("ctl00_C_myWizard_CtlType");
    const newRadio = document.querySelector('input[name="ctl00$C$myWizard$CtlType"][value="NEW"]');
    if (typeTable || newRadio) return { stage: "select-registration", pageKey: null };

    const finish = document.getElementById("ctl00_C_myWizard_FinishNavigationTemplateContainerID_FinishButton");
    const confirmedType = foldBusinessPageText(
      document.getElementById("ctl00_C_myWizard_InfoChnType")?.textContent || ""
    );
    if (finish) return { stage: "confirm", pageKey: null, confirmedType };

    const page = detectBusinessPageKey();
    const registrationType = foldBusinessPageText(
      document.getElementById("ctl00_C_INFOCtl_DOCUMENT_TYPE_IDFld")?.textContent || ""
    );
    if (page.pageKey && registrationType.includes("thanh lap moi")) {
      return { stage: "main", pageKey: page.pageKey, label: page.label };
    }
    if (isBusinessCreateMainRoot(registrationType, page)) {
      return { stage: "main-root", pageKey: null, label: page.label };
    }
    return { stage: "unknown", pageKey: null };
  }

  function detectBusinessProcedureHint() {
    const registrationType = foldBusinessPageText(
      document.getElementById("ctl00_C_INFOCtl_DOCUMENT_TYPE_IDFld")?.textContent || ""
    );
    // Metadata hồ sơ là bằng chứng mạnh nhất. Ở trang tổng quan "Khối dữ liệu" chưa có pageKey;
    // nếu đợi breadcrumb trang con, popup sẽ giữ nhầm workflow thay đổi từ session trước.
    if (registrationType.includes("thanh lap moi")) return "create";

    const detected = detectBusinessChangeStage();
    if (detected.stage === "main" && detected.pageKey === "cham-dut-hoat-dong") {
      return "dissolution";
    }
    if (detected.stage === "main" && detected.pageKey === "thong-tin-de-nghi-cap-lai") {
      return "reissue";
    }
    // Trang Người nộp/Đính kèm không còn breadcrumb cấp lại, nhưng metadata hồ sơ vẫn mang loại REI.
    if (["main", "main-root"].includes(detected.stage) && registrationType.includes("cap lai")) {
      return "reissue";
    }
    if (["main", "main-root"].includes(detected.stage) && registrationType.includes("thay doi")) {
      if (findBusinessPageLink("Chấm dứt hoạt động")) return "dissolution";
      return "change-exact";
    }
    if (detected.stage === "confirm") {
      const confirmedType = foldBusinessPageText(
        document.getElementById("ctl00_C_myWizard_InfoChnType")?.textContent || ""
      );
      if (confirmedType.includes("thanh lap moi")) return "create";
      if (confirmedType.includes("cap lai")) return "reissue";
      if (confirmedType.includes("thay doi")) return "change";
    }
    // Bước tìm kiếm dùng chung cho CHN và REI, HTML không mang loại đăng ký đã chọn. Không được
    // tự khóa về thủ tục thay đổi; popup sẽ giữ lựa chọn tay hiện tại hoặc yêu cầu người dùng chọn.
    if (detected.stage === "search-business") return "shared-business-search";
    if (["select-change", "confirm", "main", "main-root"].includes(detected.stage)) {
      return "change";
    }
    // Đây chỉ là màn chọn chung có nhiều loại đăng ký. Sự xuất hiện của label "Đăng ký thay đổi"
    // trong danh sách option KHÔNG có nghĩa người dùng đã chọn thủ tục thay đổi.
    if (detected.stage === "select-registration") return "choice";

    const page = detectBusinessPageKey();
    // Ở trang Người nộp/Văn bản đính kèm breadcrumb không còn chữ "giải thể"; menu dữ liệu
    // của chính hồ sơ vẫn có mục Chấm dứt hoạt động nên đủ để nhận diện nhánh dissolution.
    if (registrationType.includes("thay doi") && findBusinessPageLink("Chấm dứt hoạt động")) {
      return "dissolution";
    }
    if (registrationType.includes("cap lai")) return "reissue";
    if (page.pageKey && registrationType.includes("thay doi")) return "change";
    if (page.pageKey && registrationType.includes("cap lai")) return "reissue";
    return "";
  }

  async function navigateBusinessRegistrationPage(pageKey, labelFromPopup) {
    const label = labelFromPopup || BUSINESS_PAGE_LABELS[pageKey] || "";
    if (!label) return { error: "Thiếu tên trang đăng ký kinh doanh." };

    const current = currentBusinessPageLabel();
    if (current && foldBusinessPageText(current).includes(foldBusinessPageText(label))) {
      return { ok: true, already: true, label };
    }

    const link = findBusinessPageLink(label);
    if (!link) {
      return { error: `Không tìm thấy menu trang "${label}". Hãy mở đúng hồ sơ đăng ký kinh doanh.` };
    }

    try {
      if (typeof link.scrollIntoView === "function") link.scrollIntoView({ block: "center" });
      link.click();
      await sleep(250);
      return { ok: true, navigating: true, label };
    } catch (e) {
      return { error: `Không mở được trang "${label}": ${e?.message || e}` };
    }
  }

  const FILLALL_KEY = "autofill_fillall_state";
  const FILLALL_SESSION_MIRROR_KEY = FILLALL_KEY + "_mirror";

  function readFillAllSessionMirror() {
    try {
      const raw = window.sessionStorage.getItem(FILLALL_SESSION_MIRROR_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }

  function newestFillAllState(stored, mirror) {
    if (!stored) return mirror || null;
    if (!mirror) return stored;
    return Number(mirror.__stateUpdatedAt || 0) > Number(stored.__stateUpdatedAt || 0) ? mirror : stored;
  }

  function getFillAllState() {
    return new Promise((resolve) => {
      let done = false;
      const finish = (stored) => {
        if (done) return;
        done = true;
        clearTimeout(timer);
        resolve(newestFillAllState(stored, readFillAllSessionMirror()));
      };
      const timer = setTimeout(() => {
        console.warn("[FillAll] storage.get timeout — dùng session mirror");
        finish(null);
      }, 1500);
      try {
        chrome.storage.local.get(FILLALL_KEY, (res) => {
          if (chrome.runtime.lastError) {
            console.warn("[FillAll] storage.get lỗi:", chrome.runtime.lastError.message);
            return finish(null);
          }
          finish((res && res[FILLALL_KEY]) || null);
        });
      } catch (e) {
        console.warn("[FillAll] storage.get exception:", e?.message || e);
        finish(null);
      }
    });
  }

  function setFillAllState(st) {
    return new Promise((resolve) => {
      st.__stateUpdatedAt = Date.now();
      try { window.sessionStorage.setItem(FILLALL_SESSION_MIRROR_KEY, JSON.stringify(st)); }
      catch (e) { /* chrome.storage vẫn là nguồn chính */ }
      let done = false;
      const finish = () => { if (!done) { done = true; clearTimeout(timer); resolve(); } };
      // Sau full postback, Chrome đôi lúc không gọi callback storage dù request đã được nhận. Không để
      // state machine treo vô hạn; state đã được clone vào lệnh set trước khi chờ callback.
      const timer = setTimeout(() => {
        console.warn("[FillAll] storage.set timeout — tiếp tục state machine");
        finish();
      }, 1500);
      try {
        chrome.storage.local.set({ [FILLALL_KEY]: st }, () => {
          if (chrome.runtime.lastError) {
            console.warn("[FillAll] storage.set lỗi:", chrome.runtime.lastError.message);
          }
          finish();
        });
      } catch (e) {
        console.warn("[FillAll] storage.set exception:", e?.message || e);
        finish();
      }
    });
  }

  function clearFillAllState() {
    return new Promise((resolve) => {
      try { window.sessionStorage.removeItem(FILLALL_SESSION_MIRROR_KEY); } catch (e) { /* ignore */ }
      let done = false;
      const finish = () => { if (!done) { done = true; clearTimeout(timer); resolve(); } };
      const timer = setTimeout(() => {
        console.warn("[FillAll] storage.remove timeout — tiếp tục kết thúc phiên");
        finish();
      }, 1500);
      try {
        chrome.storage.local.remove(FILLALL_KEY, () => {
          if (chrome.runtime.lastError) {
            console.warn("[FillAll] storage.remove lỗi:", chrome.runtime.lastError.message);
          }
          finish();
        });
      } catch (e) {
        console.warn("[FillAll] storage.remove exception:", e?.message || e);
        finish();
      }
    });
  }

  function findBusinessSaveButton() {
    const luu = Array.from(document.querySelectorAll('input[type="submit"]'))
      .filter((b) => norm(b.value) === "lưu");
    return luu.find((b) => /save/i.test(b.id) || /save/i.test(b.name || "") ||
      /\b(save-btn|default)\b/.test(b.className)) || luu[0] || null;
  }

  function injectMainWorld(code) {
    try {
      const s = document.createElement("script");
      s.textContent = code;
      (document.documentElement || document.head).appendChild(s);
      s.remove();
      return true;
    } catch (e) { return false; }
  }

  function ensureConfirmOverride() {
    if (window.__AF_CONFIRM_OVERRIDE__) return;
    window.__AF_CONFIRM_OVERRIDE__ = true;
    // Cổng cấm inline script bằng CSP. Các xác nhận nghiệp vụ được xử lý bằng DOM thật ở từng nhánh;
    // không chèn script main-world vì vừa bị chặn vừa tạo log lỗi gây hiểu nhầm.
  }

  function doAspPostback(target, arg) {
    if (H.isBusinessRunCancelled?.()) return false;
    const et = document.getElementById("__EVENTTARGET");
    const ea = document.getElementById("__EVENTARGUMENT");
    const form = (et && et.form) || document.forms.namedItem("aspnetForm") || document.querySelector("form");
    if (form && et) {
      et.value = target;
      if (ea) ea.value = arg || "";
      console.log("[FillAll] submit postback ->", target);
      try { form.submit(); return true; } catch (e) { /* thử cách khác */ }
    }
    return injectMainWorld("try{__doPostBack(" + JSON.stringify(target) + "," + JSON.stringify(arg || "") + ");}catch(e){}");
  }

  function goToBusinessPageByKey(pageKey) {
    if (H.isBusinessRunCancelled?.()) return false;
    const label = BUSINESS_PAGE_LABELS[pageKey] || "";
    const link = findBusinessPageLink(label);
    if (!link) {
      console.warn("[FillAll] Không tìm thấy menu trang:", label);
      return false;
    }
    const href = link.getAttribute("href") || "";
    const m = href.match(/__doPostBack\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]\s*\)/);
    if (m) return doAspPostback(m[1], m[2]);
    try { link.click(); return true; } catch (e) { return false; }
  }

  function clickSaveDetectReload(btn) {
    return new Promise((resolve) => {
      if (H.isBusinessRunCancelled?.()) { resolve(false); return; }
      let done = false;
      const onLeave = () => { if (!done) { done = true; resolve(true); } };
      window.addEventListener("beforeunload", onLeave, { once: true });
      window.addEventListener("pagehide", onLeave, { once: true });
      try { btn.click(); } catch (e) { /* ignore */ }
      setTimeout(() => {
        if (done) return;
        done = true;
        window.removeEventListener("beforeunload", onLeave);
        window.removeEventListener("pagehide", onLeave);
        resolve(false);
      }, 2600);
    });
  }

  function selectNativeRadio(node) {
    if (!node || H.isBusinessRunCancelled?.()) return false;
    node.checked = true;
    node.dispatchEvent(new Event("input", { bubbles: true }));
    node.dispatchEvent(new Event("click", { bubbles: true }));
    node.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  function clickBusinessWizardButton(node) {
    if (!node || node.disabled || H.isBusinessRunCancelled?.()) return false;
    // click() không yêu cầu control nằm trong viewport. Không scroll trước khi click để màn hình
    // công dân không nhảy xuống giữa trang ngay trước full postback.
    node.click();
    return true;
  }

  function readBusinessResult() {
    const read = (id) => norm((document.getElementById(id)?.textContent || ""));
    return {
      name: read("ctl00_C_myWizard_AMEN_HOUSEHOLD_NAME"),
      type: read("ctl00_C_myWizard_AMEN_HOUSEHOLD_TYPE_ID"),
      businessNumber: read("ctl00_C_myWizard_AMEN_HOUSEHOLD_GDT_CODE"),
      registrationNumber: read("ctl00_C_myWizard_AMEN_IMP_BUSINESS_REG_NUMBER"),
      internalNumber: read("ctl00_C_myWizard_AMEN_HOUSEHOLD_CODE"),
    };
  }

  function businessResultMatches(flow) {
    const result = readBusinessResult();
    if (!result.name && !result.businessNumber && !result.registrationNumber && !result.internalNumber) return false;
    const search = (flow && flow.search) || {};
    const expectedCode = String(search.expectedBusinessNumber
      || (search.method === "businessNumber" ? search.value : "") || "").replace(/\D/g, "");
    const actualCodes = [result.businessNumber, result.registrationNumber, result.internalNumber]
      .map((value) => String(value || "").replace(/\D/g, "")).filter(Boolean);
    if (expectedCode && actualCodes.length && !actualCodes.includes(expectedCode)) return false;
    const expectedName = foldBusinessPageText(search.expectedName || "");
    if (expectedName && result.name && !foldBusinessPageText(result.name).includes(expectedName)
      && !expectedName.includes(foldBusinessPageText(result.name))) return false;
    return true;
  }

  const BUSINESS_SEARCH_CONTROL = {
    businessNumber: ["ctl00$C$myWizard$GDT_CODEFld", "ctl00$C$myWizard$btnAmendGDTUID"],
    internalNumber: ["ctl00$C$myWizard$AmenHOUSEHOLDUIDFld", "ctl00$C$myWizard$Button1"],
    registrationNumber: ["ctl00$C$myWizard$IMP_BUSINESS_REG_NUMBERFbl", "ctl00$C$myWizard$Button3"],
    identityNumber: ["ctl00$C$myWizard$PERS_DOC_NOFbl", "ctl00$C$myWizard$Button4"],
  };

  async function failChangeWorkflow(message) {
    console.error("[ChangeHKD] dừng có kiểm soát:", message);
    await clearFillAllState();
    H.endFillAllUI("⚠ " + message);
  }

  async function failCreateWorkflow(message) {
    console.error("[CreateHKD] dừng có kiểm soát:", message);
    await clearFillAllState();
    H.endFillAllUI("⚠ " + message);
  }

  async function waitCreateBootstrapStep(expectedStage) {
    await sleep(BUSINESS_CREATE_STEP_DELAY_MS);
    const active = await getFillAllState();
    if (!active || active.workflow !== "create") return false;
    const currentStage = detectBusinessCreateStage().stage;
    if (currentStage !== expectedStage) {
      // Trang đã đổi trong lúc chờ (người dùng/cổng thao tác trước) → nhận diện lại ngay,
      // không thực hiện click dành cho DOM của bước cũ.
      setTimeout(stepFillAll, 0);
      return false;
    }
    return true;
  }

  async function stepCreateBootstrap(st) {
    const detected = detectBusinessCreateStage();
    H.setRunProgressText(`Thành lập mới hộ kinh doanh — ${detected.stage}\n(đừng thao tác tới khi xong)`);
    console.log("[CreateHKD] bootstrap", detected.stage);

    if (detected.stage === "unknown") {
      st.bootstrapTries = Number(st.bootstrapTries || 0) + 1;
      await setFillAllState(st);
      if (st.bootstrapTries <= 6) return void setTimeout(stepFillAll, 700);
      return void failCreateWorkflow("Không nhận diện được màn Thành lập mới hộ kinh doanh hiện tại.");
    }
    st.bootstrapTries = 0;
    ensureConfirmOverride();

    if (detected.stage === "main" || detected.stage === "main-root") {
      if (st.bootstrapOnly) {
        await clearFillAllState();
        H.businessDraftReady?.();
        return;
      }
      st.bootstrapDone = true;
      st.phase = "fill";
      await setFillAllState(st);
      return void stepFillAll();
    }

    if (detected.stage === "home") {
      const link = Array.from(document.querySelectorAll("a.AspNet-Menu-Link, .PrettyMenu a"))
        .find((node) => foldBusinessPageText(node.textContent) === "dang ky ho kinh doanh");
      if (!link) return void failCreateWorkflow("Không tìm thấy menu Đăng ký Hộ kinh doanh.");

      st.homeTries = Number(st.homeTries || 0) + 1;
      if (st.homeTries > 3) {
        return void failCreateWorkflow(
          "Đã chọn Đăng ký Hộ kinh doanh nhưng cổng vẫn chưa mở trang chọn loại đăng ký."
        );
      }
      await setFillAllState(st);
      if (!await waitCreateBootstrapStep("home")) return;

      // Menu này là javascript:__doPostBack của ASP.NET, không phải link điều hướng thường.
      // Bóc đúng target/argument rồi submit form để không phụ thuộc javascript URL chạy từ
      // isolated world của content script.
      const href = link.getAttribute("href") || "";
      const postback = href.match(
        /__doPostBack\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]\s*\)/
      );
      const submitted = postback
        ? doAspPostback(postback[1], postback[2])
        : doAspPostback("ctl00$LV3$mCon", "bĐăng ký Hộ kinh doanh");
      if (!submitted) return void failCreateWorkflow("Không gửi được lệnh mở Đăng ký Hộ kinh doanh.");

      // Postback thành công sẽ hủy timer khi reload. Nếu trang không đổi, detector chạy lại
      // có giới hạn và báo lỗi thay vì im lặng đứng ở trạng thái `home`.
      setTimeout(stepFillAll, 1600);
      return;
    }

    if (detected.stage === "select-registration") {
      const radio = document.querySelector('input[name="ctl00$C$myWizard$CtlType"][value="NEW"]');
      const next = document.getElementById("ctl00_C_myWizard_StepNavigationTemplateContainerID_StepNextButton");
      if (!radio || !next) {
        return void failCreateWorkflow("Không tìm thấy lựa chọn Thành lập mới hoặc nút Tiếp theo.");
      }
      await setFillAllState(st);
      if (!await waitCreateBootstrapStep("select-registration")) return;
      selectNativeRadio(radio);
      await setFillAllState(st);
      clickBusinessWizardButton(next);
      return;
    }

    if (detected.stage === "confirm") {
      if (!String(detected.confirmedType || "").includes("thanh lap moi")) {
        return void failCreateWorkflow(
          "Bước xác nhận không hiển thị Thành lập mới hộ kinh doanh nên em không bấm Bắt đầu."
        );
      }
      const begin = document.getElementById("ctl00_C_myWizard_FinishNavigationTemplateContainerID_FinishButton");
      if (!begin) return void failCreateWorkflow("Không tìm thấy nút Bắt đầu ở bước xác nhận.");
      await setFillAllState(st);
      if (!await waitCreateBootstrapStep("confirm")) return;
      clickBusinessWizardButton(begin);
    }
  }

  async function stepChangeBootstrap(st) {
    const detected = detectBusinessChangeStage();
    const flow = st.businessFlow || {};
    const search = st.businessSearch || flow.search || {};
    const effectiveFlow = { ...flow, search };
    console.log("[ChangeHKD] bootstrap", detected.stage, search);
    const workflowLabel = flow.wizardType === "reissue" ? "Cấp lại/cấp đổi GCN HKD" : "Đăng ký thay đổi HKD";
    H.setRunProgressText(`${workflowLabel} — ${detected.stage}\n(đừng thao tác tới khi xong)`);

    if (detected.stage === "unknown") {
      return void failChangeWorkflow(`Trang hiện tại không thuộc luồng ${workflowLabel}. Hãy mở đúng hồ sơ rồi chạy lại.`);
    }
    if (detected.stage === "main" || detected.stage === "main-root") {
      st.bootstrapDone = true;
      st.phase = "fill";
      await setFillAllState(st);
      return void stepFillAll();
    }

    ensureConfirmOverride();
    if (detected.stage === "select-registration") {
      const registrationOption = flow.registrationOption || (flow.wizardType === "reissue" ? "REI" : "CHN");
      const radio = document.querySelector(
        `input[name="ctl00$C$myWizard$CtlType"][value="${registrationOption}"]`
      );
      const next = document.getElementById("ctl00_C_myWizard_StepNavigationTemplateContainerID_StepNextButton");
      if (!radio || !next) return void failChangeWorkflow(`Không tìm thấy lựa chọn ${registrationOption} hoặc nút Tiếp theo ở bước 1.`);
      selectNativeRadio(radio);
      await setFillAllState(st);
      clickBusinessWizardButton(next);
      return;
    }

    if (detected.stage === "search-business") {
      if (businessResultMatches(effectiveFlow)) {
        const next = document.getElementById("ctl00_C_myWizard_StepNavigationTemplateContainerID_StepNextButton");
        if (!next) return void failChangeWorkflow("Đã tìm thấy hộ kinh doanh nhưng không thấy nút Tiếp theo.");
        clickBusinessWizardButton(next);
        return;
      }
      const control = BUSINESS_SEARCH_CONTROL[search.method];
      if (!control || !search.value) {
        return void failChangeWorkflow("Không trích xuất được mã hộ kinh doanh hoặc số định danh để tìm kiếm.");
      }
      const input = document.querySelector(`[name="${control[0]}"]`);
      const button = document.querySelector(`[name="${control[1]}"]`);
      if (!input || !button) return void failChangeWorkflow("Không tìm thấy ô/nút Tìm kiếm tương ứng trên bước 2.");
      st.searchTries = (st.searchTries || 0) + 1;
      if (st.searchTries > 3) return void failChangeWorkflow("Tìm hộ kinh doanh quá 3 lần nhưng chưa có kết quả khớp hồ sơ.");
      setNativeValue(input, search.value, { typing: true, commit: true });
      await setFillAllState(st);
      clickBusinessWizardButton(button);
      return;
    }

    if (detected.stage === "select-change") {
      if (flow.wizardType === "reissue") {
        return void failChangeWorkflow("Cổng đang ở nhánh Đăng ký thay đổi (CHN), không phải nhánh Cấp lại GCN (REI). Hãy quay lại màn chọn loại đăng ký.");
      }
      const amendmentValue = flow.amendmentType || "CHAPAR";
      const amendment = document.querySelector(
        `input[name="ctl00$C$myWizard$CtlAmendmentType"][value="${amendmentValue}"]`
      ) || (amendmentValue === "CHAPAR" ? document.getElementById("ctl00_C_myWizard_CtlAmendmentType_0") : null);
      const next = document.getElementById("ctl00_C_myWizard_StepNavigationTemplateContainerID_StepNextButton");
      if (!amendment || !next) return void failChangeWorkflow("Thiếu lựa chọn loại đăng ký thay đổi hoặc nút Tiếp theo ở bước 3.");

      // DISSOLU có AutoPostBack ngay khi chọn. Persist trước rồi chờ reload; nếu cổng không reload
      // thì nhịp hẹn giờ kế tiếp sẽ thấy radio đã checked và bấm Tiếp theo.
      if (amendmentValue === "DISSOLU" && !amendment.checked) {
        await setFillAllState(st);
        selectNativeRadio(amendment);
        return void setTimeout(stepFillAll, 1200);
      }
      if (amendmentValue !== "DISSOLU") selectNativeRadio(amendment);
      if (amendmentValue === "CHAPAR") {
        const nameValue = flow.nameChange ? "Y" : "N";
        const nameRadio = document.querySelector(`input[name="ctl00$C$myWizard$NAME_CHANGE_YN_IDFld"][value="${nameValue}"]`);
        if (!nameRadio) return void failChangeWorkflow("Thiếu lựa chọn Có/Không thay đổi tên hộ kinh doanh ở bước 3.");
        selectNativeRadio(nameRadio);
      }
      await setFillAllState(st);
      clickBusinessWizardButton(next);
      return;
    }

    if (detected.stage === "confirm") {
      const begin = document.getElementById("ctl00_C_myWizard_FinishNavigationTemplateContainerID_FinishButton");
      if (!begin) return void failChangeWorkflow("Không tìm thấy nút Bắt đầu ở bước xác nhận.");
      if (flow.wizardType === "reissue") {
        const confirmedType = foldBusinessPageText(
          document.getElementById("ctl00_C_myWizard_InfoChnType")?.textContent || ""
        );
        if (!confirmedType.includes("cap lai")) {
          return void failChangeWorkflow("Bước xác nhận không hiển thị loại Cấp lại Giấy chứng nhận; không bấm Bắt đầu để tránh mở nhầm hồ sơ.");
        }
      }
      st.bootstrapDone = true;
      await setFillAllState(st);
      clickBusinessWizardButton(begin);
    }
  }

  function reissueCheckboxLabel(node) {
    if (!node) return "";
    const explicit = node.id ? document.querySelector(`label[for="${node.id}"]`) : null;
    if (explicit) return norm(explicit.textContent);
    const cell = node.closest("td, li, div");
    return norm(cell?.textContent || node.parentElement?.textContent || "");
  }

  async function handleReissuePage(st) {
    const fields = (st.pages && st.pages["thong-tin-de-nghi-cap-lai"]) || [];
    const request = fields.find((field) => field.name === "__reissueRequest")?.value || {};
    const kind = String(request.kind || "");
    const reason = String(request.reason || "").replace(/\s+/g, " ").trim();
    if (!reason) return void failChangeWorkflow("Không trích xuất được lý do cấp lại/cấp đổi nên chưa thể lưu trang đề nghị.");
    if (kind !== "cap_lai" && kind !== "cap_doi") {
      return void failChangeWorkflow("Không xác định được hồ sơ yêu cầu cấp lại hay cấp đổi; không tự chọn thay người dùng.");
    }

    const checkboxes = Array.from(document.querySelectorAll(
      'input[type="checkbox"][name^="ctl00$C$REI_TYPE_IDChBox"], #ctl00_C_REI_TYPE_IDChBox input[type="checkbox"]'
    ));
    const target = checkboxes.find((node) => {
      const label = foldBusinessPageText(reissueCheckboxLabel(node));
      return kind === "cap_doi" ? label.includes("cap doi") : label.includes("cap lai") && !label.includes("cap doi");
    });
    if (!target) {
      const wanted = kind === "cap_doi" ? "Cấp đổi" : "Cấp lại";
      return void failChangeWorkflow(`Cổng không có lựa chọn ${wanted} tương ứng với hồ sơ; không chọn loại khác thay thế.`);
    }
    if (!target.checked) target.click();
    if (!target.checked) {
      target.checked = true;
      target.dispatchEvent(new Event("input", { bubbles: true }));
      target.dispatchEvent(new Event("change", { bubbles: true }));
    }

    const reasonInput = document.querySelector('[name="ctl00$C$REI_REASONTxt"]')
      || document.getElementById("ctl00_C_REI_REASONTxt");
    if (!reasonInput) return void failChangeWorkflow("Không tìm thấy ô Lý do cấp lại/cấp đổi trên trang đề nghị.");
    setNativeValue(reasonInput, reason, { typing: true, commit: true });

    const save = document.getElementById("ctl00_C_BtnSaveRei") || findBusinessSaveButton();
    if (!save) return void failChangeWorkflow("Không tìm thấy nút Lưu của trang cấp lại/cấp đổi.");
    await waitFor(() => !save.disabled, 5000, 200);
    if (save.disabled) {
      return void failChangeWorkflow("Đã chọn loại và nhập lý do nhưng nút Lưu vẫn bị khóa; hãy kiểm tra validation của cổng.");
    }
    st.phase = "saving";
    await setFillAllState(st);
    const reloaded = await clickSaveDetectReload(save);
    if (reloaded) return;
    return void failChangeWorkflow("Cổng không chuyển trang sau khi bấm Lưu thông tin cấp lại/cấp đổi.");
  }

  function getNnCodes(st) {
    const f = ((st.pages && st.pages["nganh-nghe-kinh-doanh"]) || []).find((x) => x.name === "__businessLines");
    return f ? f.value : null; // {codes:[...], main:"...", items:[{code,name,main}]}
  }

  function foldBusinessLineName(value) {
    return foldBusinessPageText(String(value || "")
      .replace(/[()]/g, " ")
      .replace(/\b\d{3,6}\b/g, " "));
  }

  // Chuẩn hóa ngay tại điểm ghi vào form để không phụ thuộc dữ liệu backend/cache cũ đã viết hoa
  // hay chưa. Chỉ viết hoa chữ cái đầu tiên, vẫn giữ nguyên phần còn lại của tên ngành nghề.
  function capitalizeBusinessLineName(value) {
    const text = String(value || "").trim().replace(/\s+/g, " ");
    const match = text.match(/[^\W\d_]/);
    if (!match) return text;
    const i = match.index;
    return text.slice(0, i) + text[i].toUpperCase() + text.slice(i + 1);
  }

  function getBusinessLineNameByCode(nn) {
    const byCode = {};
    const rows = Array.isArray(nn && nn.items) ? nn.items : [];
    for (const row of rows) {
      const code = String(row && (row.code || row.ma || "") || "").trim();
      // norm() chỉ dùng để so sánh vì nó hạ toàn bộ chữ thường; không được dùng giá trị norm để ghi
      // vào textarea mô tả ngành nghề.
      const name = capitalizeBusinessLineName(row && (row.name || row.ten || "") || "");
      if (code && name && !byCode[code]) byCode[code] = name;
    }
    return byCode;
  }

  function getAddedBusinessCodes() {
    const codes = [];
    const rows = Array.from(document.querySelectorAll("#ctl00_C_CtlList tr"));
    for (const r of rows) {
      for (const td of r.querySelectorAll("td")) {
        const t = (td.textContent || "").trim();
        if (/^\d{3,6}$/.test(t)) { codes.push(t); break; }
      }
    }
    return codes;
  }

  function findBusinessRowByCode(code) {
    const wanted = String(code).trim();
    const rows = Array.from(document.querySelectorAll("#ctl00_C_CtlList tr"));
    return rows.find((r) => Array.from(r.querySelectorAll("td")).some((td) => (td.textContent || "").trim() === wanted)) || null;
  }

  function getBusinessRowDescription(row) {
    return row && row.querySelector(
      'textarea[name$="DW_HH_BUSINESS_LINE_DESCRIPTIONFld"], textarea[id$="DW_HH_BUSINESS_LINE_DESCRIPTIONFld"], textarea[name*="BUSINESS_LINE_DESCRIPTION"], textarea[id*="BUSINESS_LINE_DESCRIPTION"]'
    );
  }

  function getBusinessRowOfficialName(row, code) {
    if (!row) return "";
    const nameNode = row.querySelector('[id$="CL_BUSINESS_LINE__NAMEFld"], [id*="CL_BUSINESS_LINE__NAMEFld"]');
    if (nameNode && norm(nameNode.textContent)) return norm(nameNode.textContent);

    const wanted = String(code || "").trim();
    const cells = Array.from(row.querySelectorAll("td"));
    const candidates = [];
    for (const td of cells) {
      if (td.querySelector('input[type="checkbox"], input[type="radio"], input[type="submit"], input[type="button"], button, a')) {
        continue;
      }
      const clone = td.cloneNode(true);
      clone.querySelectorAll("textarea, input, button, a").forEach((node) => node.remove());
      let text = norm(clone.textContent);
      if (!text) continue;
      text = norm(text.replace(new RegExp(`\\b${wanted.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "g"), " "));
      if (!text || /^\d{3,6}$/.test(text)) continue;
      if (/^(stt|mã ngành|ma nganh|tên ngành|ten nganh)$/i.test(text)) continue;
      candidates.push(text);
    }
    return candidates.find((text) => foldBusinessLineName(text)) || "";
  }

  function shouldFillBusinessDescription(officialName, extractedName) {
    const official = foldBusinessLineName(officialName);
    const extracted = foldBusinessLineName(extractedName);
    return !!official && !!extracted && official !== extracted;
  }

  function fillBusinessLineDescriptions(nn) {
    const nameByCode = getBusinessLineNameByCode(nn);
    let changed = 0;
    for (const code of Object.keys(nameByCode)) {
      const extractedName = nameByCode[code];
      const row = findBusinessRowByCode(code);
      const desc = getBusinessRowDescription(row);
      const officialName = getBusinessRowOfficialName(row, code);
      if (!row || !desc || !shouldFillBusinessDescription(officialName, extractedName)) continue;

      const current = String(desc.value || "").trim();
      const currentFold = foldBusinessLineName(current);
      const extractedFold = foldBusinessLineName(extractedName);
      if (currentFold && (currentFold === extractedFold || currentFold.includes(extractedFold))) continue;

      const next = current ? `${current}\n${extractedName}` : extractedName;
      setNativeValue(desc, next, { typing: false, commit: true });
      changed += 1;
      console.log("[FillAll] mô tả ngành nghề:", { code, officialName, extractedName });
    }
    return changed;
  }

  function findBusinessLineUpdateButton() {
    const byId = document.querySelector(
      'input[name="ctl00$C$btnUpdateBusinessLine"], #ctl00_C_btnUpdateBusinessLine, input[name*="btnUpdateBusinessLine"], input[id*="btnUpdateBusinessLine"]'
    );
    if (byId && !byId.disabled) return byId;
    const main = document.querySelector('input[name="ctl00$C$btnUpdateMain"], #ctl00_C_btnUpdateMain');
    if (main && !main.disabled) return main;
    const save = findBusinessSaveButton();
    return save && !save.disabled ? save : null;
  }

  function findBusinessActTextarea() {
    return document.querySelector(
      '#ctl00_C_BUSINESS_ACT_TEXTFld, textarea[name="ctl00$C$BUSINESS_ACT_TEXTFld"], textarea[name$="BUSINESS_ACT_TEXTFld"], textarea[id$="BUSINESS_ACT_TEXTFld"]'
    );
  }

  function findBusinessActSaveButton() {
    return document.querySelector(
      'input[name="ctl00$C$BtnSaveNotVSIC"], #ctl00_C_BtnSaveNotVSIC, input[name*="BtnSaveNotVSIC"], input[id*="BtnSaveNotVSIC"]'
    );
  }

  function enableBusinessActSaveButton(btn) {
    if (!btn) return null;
    // Cổng chỉ bật nút này qua handler onkeyup/onchange của textarea. Khi extension set value trực tiếp,
    // có trang vẫn giữ disabled nên phải mở nút trước khi click để postback lưu nội dung BUSINESS_ACT_TEXTFld.
    if (btn.disabled) {
      try {
        btn.disabled = false;
        btn.removeAttribute("disabled");
      } catch (e) { /* ignore */ }
    }
    return btn;
  }

  function fillBusinessActDefault(defaults) {
    const text = norm(defaults && defaults.businessActText);
    if (!text) return 0;
    const textarea = findBusinessActTextarea();
    if (!textarea) return 0;

    const current = norm(textarea.value);
    const currentFold = foldBusinessPageText(current);
    const textFold = foldBusinessPageText(text);
    if (currentFold && (currentFold === textFold || currentFold.includes(textFold))) return 0;
    // Ô này là ghi chú pháp lý theo phường; không ghi đè nội dung cán bộ/cổng đã nhập sẵn.
    if (current) {
      console.log("[FillAll] ngành nghề: bỏ qua ghi chú mặc định vì ô đã có nội dung.");
      return 0;
    }

    setNativeValue(textarea, text, { typing: true, commit: true });
    console.log("[FillAll] ngành nghề: điền ghi chú mặc định theo tài khoản/phường.");
    return 1;
  }

  async function saveBusinessActDefaultIfChanged(changed) {
    if (!changed) return false;
    const save = enableBusinessActSaveButton(findBusinessActSaveButton());
    if (!save) {
      console.warn("[FillAll] ngành nghề: đã điền ghi chú mặc định nhưng không thấy nút Lưu BtnSaveNotVSIC.");
      return false;
    }
    console.log("[FillAll] ngành nghề: lưu ghi chú mặc định.");
    return clickSaveDetectReload(save);
  }

  function isBusinessMainSet(code) {
    const row = findBusinessRowByCode(code);
    const radio = row && row.querySelector('input[name="ismain"]');
    return !!(radio && radio.checked);
  }

  function addOneBusinessCode(code) {
    const input = findStandardInput(["ctl00$C$newBusinessLineCode"]);
    const hidden = findStandardInput(["ctl00$C$newBusinessLineCodeVal"]);
    const addBtn = document.querySelector('input[name="ctl00$C$BtnAddBl"], #ctl00_C_BtnAddBl');
    if (!input || !addBtn) {
      console.warn("[FillAll] Ngành nghề: không thấy ô mã / nút Thêm");
      return Promise.resolve(false);
    }
    setNativeValue(input, code, { typing: true, commit: true });
    if (hidden) setNativeValue(hidden, code, { typing: false, commit: true });
    console.log("[FillAll] thêm mã ngành:", code);
    return clickSaveDetectReload(addBtn);
  }

  function setBusinessMainAndUpdate(code) {
    const row = findBusinessRowByCode(code);
    const radio = row && row.querySelector('input[name="ismain"]');
    const upd = document.querySelector('input[name="ctl00$C$btnUpdateMain"], #ctl00_C_btnUpdateMain');
    if (!radio || !upd) {
      console.warn("[FillAll] Ngành nghề: không thấy radio chính / nút Cập nhật chính cho mã", code);
      return Promise.resolve(false);
    }
    radio.checked = true;
    radio.dispatchEvent(new Event("click", { bubbles: true }));
    radio.dispatchEvent(new Event("change", { bubbles: true }));
    console.log("[FillAll] cập nhật ngành chính:", code);
    return clickSaveDetectReload(upd);
  }

  async function handleNganhNghePage(st) {
    const nn = getNnCodes(st);

    // Không có mã VSIC → điền ô ngành nghề dạng text tự do (nếu có) rồi sang trang kế.
    if (!nn || !Array.isArray(nn.codes) || !nn.codes.length) {
      const fields = ((st.pages && st.pages["nganh-nghe-kinh-doanh"]) || []).filter((f) => f.name !== "__businessLines");
      if (fields.length) { try { await fillFormStandard(fields); } catch (e) { /* ignore */ } }
      let changed = 0;
      if (!st.nnBusinessActDefaultDone) {
        st.nnBusinessActDefaultDone = true;
        changed = fillBusinessActDefault(st.businessDefaults);
        await setFillAllState(st);
      }
      if (await saveBusinessActDefaultIfChanged(changed)) return;
      await sleep(400);
      return void advanceFillAll(st);
    }

    const skip = st.nnSkip || [];
    const added = getAddedBusinessCodes();
    const remaining = nn.codes.filter((c) => !added.includes(c) && !skip.includes(c));
    console.log("[FillAll] ngành nghề — đã có:", added, "| còn cần:", remaining);

    // Chặn lặp vô hạn: quá nhiều lần thêm thì dừng.
    if ((st.nnAdds || 0) > nn.codes.length + 5) {
      console.warn("[FillAll] Ngành nghề: quá số lần thêm cho phép, chuyển sang cập nhật chính.");
    } else if (remaining.length) {
      const code = remaining[0];
      st.nnAdds = (st.nnAdds || 0) + 1;
      await setFillAllState(st);
      const reloaded = await addOneBusinessCode(code);
      if (reloaded) return;           // postback → resume xử lý mã kế
      st.nnSkip = [...skip, code];    // không thêm được → bỏ qua mã này
      await setFillAllState(st);
      return void stepFillAll();      // thử mã tiếp theo ngay
    }

    // Đã thêm hết → set ngành chính (1 lần). Postback này cũng là điểm ổn định để portal render đủ row.
    if (nn.main && !st.nnMainDone && !isBusinessMainSet(nn.main)) {
      st.nnMainDone = true;
      await setFillAllState(st);
      const reloaded = await setBusinessMainAndUpdate(nn.main);
      if (reloaded) return;
    }

    // Đã thêm hết mã → nếu tên OCR cụ thể hơn/khác tên chính thức portal thì ghi vào ô mô tả của dòng đó.
    if (!st.nnDescriptionsDone) {
      st.nnDescriptionsDone = true;
      const changed = fillBusinessLineDescriptions(nn);
      await setFillAllState(st);
      if (changed) {
        const upd = findBusinessLineUpdateButton();
        if (upd) {
          const reloaded = await clickSaveDetectReload(upd);
          if (reloaded) return;
        }
      }
    }

    if (!st.nnBusinessActDefaultDone) {
      st.nnBusinessActDefaultDone = true;
      const changed = fillBusinessActDefault(st.businessDefaults);
      await setFillAllState(st);
      if (await saveBusinessActDefaultIfChanged(changed)) return;
    }
    return void advanceFillAll(st);
  }

  function getBusinessLineChanges(st) {
    const direct = st.businessFlow && st.businessFlow.industryChanges;
    if (direct) return direct;
    const raw = ((st.pages && st.pages["nganh-nghe-kinh-doanh"]) || [])
      .find((field) => field.name === "__businessLineChanges");
    return (raw && raw.value) || { add: [], remove: [] };
  }

  function findBusinessDeleteControl(row) {
    if (!row) return null;
    return row.querySelector('a[id$="LnkDelete"], a[name$="LnkDelete"], input[id$="LnkDelete"], input[name$="LnkDelete"]');
  }

  function findBusinessRestoreControl(row) {
    if (!row) return null;
    const exact = row.querySelector(
      'a[id*="Restore"], a[name*="Restore"], input[id*="Restore"], input[name*="Restore"],'
      + ' a[id*="Recover"], a[name*="Recover"], input[id*="Recover"], input[name*="Recover"]'
    );
    if (exact) return exact;
    return Array.from(row.querySelectorAll('a, button, input[type="submit"], input[type="button"]'))
      .find((node) => {
        const label = foldBusinessPageText(
          node.value || node.textContent || node.getAttribute?.("title") || node.getAttribute?.("aria-label") || ""
        );
        return label === "khoi phuc";
      }) || null;
  }

  function isBusinessRowMarkedDeleted(row) {
    return !!findBusinessRestoreControl(row);
  }

  function parseBusinessDeletePostback(control) {
    if (!control) return null;
    const script = [control.getAttribute?.("href"), control.getAttribute?.("onclick")]
      .filter(Boolean).join(" ");
    const direct = script.match(/__doPostBack\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]\s*\)/);
    if (direct) return { target: direct[1], arg: direct[2] || "" };
    const options = script.match(/WebForm_PostBackOptions\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]/);
    if (options) return { target: options[1], arg: options[2] || "" };
    return null;
  }

  function submitBusinessDeleteWithoutNativeConfirm(control) {
    const postback = parseBusinessDeletePostback(control);
    if (postback) return doAspPostback(postback.target, postback.arg);

    // Fallback cho ASP <input type=submit>: gửi đúng name/value bằng form.submit(), không gọi click()
    // nên onclick="return confirm(...)" không chạy. Server vẫn nhận button đã submit.
    const form = control?.form || control?.closest?.("form") || document.forms.namedItem("aspnetForm");
    const name = control?.getAttribute?.("name") || "";
    if (!form || !name) return false;
    const marker = document.createElement("input");
    marker.type = "hidden";
    marker.name = name;
    marker.value = control.value || "Xóa";
    form.appendChild(marker);
    try { form.submit(); return true; } catch (e) { marker.remove(); return false; }
  }

  function confirmBusinessDeleteDetectReload(control) {
    return new Promise((resolve) => {
      let done = false;
      const finish = (result) => { if (!done) { done = true; resolve(result); } };
      const onLeave = () => finish({ started: true, reloaded: true });
      // Chỉ pagehide xác nhận document thực sự rời trang. beforeunload có thể chạy dù navigation
      // bị cổng hủy; resolve sớm ở đó sẽ khiến state machine đứng mà không có document mới để resume.
      window.addEventListener("pagehide", onLeave, { once: true });

      // Đây là nhánh "OK" tất định: bypass native confirm và gửi postback của đúng row đã đối chiếu mã.
      const started = submitBusinessDeleteWithoutNativeConfirm(control);
      if (!started) {
        window.removeEventListener("pagehide", onLeave);
        finish({ started: false, reloaded: false });
        return;
      }
      setTimeout(() => {
        window.removeEventListener("pagehide", onLeave);
        finish({ started: true, reloaded: false });
      }, 2600);
    });
  }

  async function handleChangeBusinessLines(st) {
    const changes = getBusinessLineChanges(st);
    const removals = Array.isArray(changes.remove) ? changes.remove : [];
    const additions = Array.isArray(changes.add) ? changes.add : [];
    const removeCodes = removals.map((item) => String(item && (item.code || item.ma) || "").replace(/\D/g, ""))
      .filter((code) => code.length === 4);

    // Sau postback xóa, xử lý state này TRƯỚC vòng tìm/xóa chung. Một số bản HkdOnline phục hồi
    // document từ cache và không chạy lại đúng nhịp UI; đối chiếu row thật giúp tiếp tục an toàn.
    if (st.phase === "deleting-industry") {
      const deletedCode = String(st.pendingIndustryDelete || "").replace(/\D/g, "");
      const remainingRow = deletedCode ? findBusinessRowByCode(deletedCode) : null;
      const remainingDelete = remainingRow ? findBusinessDeleteControl(remainingRow) : null;
      const markedDeleted = isBusinessRowMarkedDeleted(remainingRow);
      console.log(
        `[ChangeHKD] reconcile xóa ngành code=${deletedCode}`
        + ` rowStillExists=${!!remainingRow} markedDeleted=${markedDeleted}`
        + ` deleteControlStillExists=${!!remainingDelete}`
      );
      if (remainingRow && !markedDeleted && !remainingDelete) {
        return void failChangeWorkflow(`Mã ngành ${deletedCode} vẫn còn nhưng không thấy trạng thái Khôi phục hoặc nút Xóa của đúng dòng.`);
      }
      st.phase = "fill";
      delete st.pendingIndustryDelete;
      await setFillAllState(st);
      console.log("[ChangeHKD] đã lưu phase fill sau reconcile");
      if (!remainingRow || markedDeleted) {
        console.log("[ChangeHKD] đã xóa mềm mã ngành, tiếp tục state machine:", deletedCode);
      } else {
        console.warn("[ChangeHKD] postback chưa xóa mã ngành, retry đúng dòng:", deletedCode);
      }
    }

    // Xóa từng mã đang tồn tại và CHƯA ở trạng thái "Khôi phục". Portal xóa mềm nên row vẫn còn;
    // nút Khôi phục mới là dấu hiệu server đã ghi nhận xóa.
    const pendingRemove = removeCodes.find((code) => {
      const row = findBusinessRowByCode(code);
      return row && !isBusinessRowMarkedDeleted(row);
    });
    if (pendingRemove) {
      st.nnRemoveTries = (st.nnRemoveTries || 0) + 1;
      if (st.nnRemoveTries > removeCodes.length + 4) {
        return void failChangeWorkflow("Không xóa được đúng mã ngành " + pendingRemove + " sau nhiều lần thử.");
      }
      const row = findBusinessRowByCode(pendingRemove);
      const control = findBusinessDeleteControl(row);
      if (!control) return void failChangeWorkflow(`Đã thấy dòng mã ${pendingRemove} nhưng không thấy nút Xóa của dòng.`);
      console.log("[ChangeHKD] xóa mã ngành chính xác:", pendingRemove);
      st.phase = "deleting-industry";
      st.pendingIndustryDelete = pendingRemove;
      await setFillAllState(st);
      const confirmed = await confirmBusinessDeleteDetectReload(control);
      if (!confirmed.started) {
        st.phase = "fill";
        delete st.pendingIndustryDelete;
        await setFillAllState(st);
        return void failChangeWorkflow(`Không đọc được postback để xác nhận xóa mã ngành ${pendingRemove}.`);
      }
      if (confirmed.reloaded) return;
      // Không có navigation thực sự (postback bị cổng chặn): trả phase về fill và kiểm tra DOM lại,
      // thay vì dừng ở trạng thái đang xóa.
      st.phase = "fill";
      delete st.pendingIndustryDelete;
      await setFillAllState(st);
      return void stepFillAll();
    }

    const coded = additions.filter((item) => String(item && (item.code || item.ma) || "").replace(/\D/g, "").length === 4);
    const addedCodes = getAddedBusinessCodes();
    const skippedAddCodes = new Set(Array.isArray(st.nnSkippedAddCodes) ? st.nnSkippedAddCodes : []);
    const pendingAdd = coded.find((item) => {
      const code = String(item.code || item.ma).replace(/\D/g, "");
      return !addedCodes.includes(code) && !skippedAddCodes.has(code);
    });
    if (pendingAdd) {
      const code = String(pendingAdd.code || pendingAdd.ma).replace(/\D/g, "");
      st.nnAddTries = (st.nnAddTries && typeof st.nnAddTries === "object") ? st.nnAddTries : {};
      st.nnAddTries[code] = Number(st.nnAddTries[code] || st.nnAdds || 0) + 1;
      st.nnAdds = 0; // bỏ counter global cũ; retry phải độc lập theo từng mã.
      if (st.nnAddTries[code] > 4) {
        st.nnSkippedAddCodes = Array.from(new Set([...(st.nnSkippedAddCodes || []), code]));
        st.warnings = Array.from(new Set([
          ...(st.warnings || []),
          `Không tự bổ sung được mã ngành ${code}; đã bỏ qua để tiếp tục các bước còn lại.`,
        ]));
        console.warn("[ChangeHKD] bỏ qua mã ngành bổ sung sau 4 lần thử, tiếp tục luồng:", code);
        await setFillAllState(st);
        return void stepFillAll();
      }
      await setFillAllState(st);
      const reloaded = await addOneBusinessCode(code);
      if (reloaded) return;
      return void stepFillAll();
    }

    const availableCodes = new Set(getAddedBusinessCodes());
    const availableCoded = coded.filter((item) => {
      const code = String(item.code || item.ma).replace(/\D/g, "");
      return availableCodes.has(code) && !skippedAddCodes.has(code);
    });

    // Tên ngành không có mã được lưu ở ô nội dung ngoài VSIC; nối thêm, không ghi đè dữ liệu đang có.
    const textOnly = additions.map((item) => String(item && (item.name || item.ten) || "").replace(/\s+/g, " ").trim())
      .filter((name, index, all) => name
        && all.findIndex((candidate) => foldBusinessPageText(candidate) === foldBusinessPageText(name)) === index
        && !coded.some((item) => foldBusinessPageText(item.name || item.ten) === foldBusinessPageText(name)));
    if (textOnly.length && !st.nnTextDone) {
      const textarea = findBusinessActTextarea();
      const save = enableBusinessActSaveButton(findBusinessActSaveButton());
      st.nnTextDone = true;
      if (!textarea || !save) {
        st.warnings = Array.from(new Set([
          ...(st.warnings || []),
          "Không tự bổ sung được ngành nghề chưa có mã; đã bỏ qua để tiếp tục các bước còn lại.",
        ]));
        console.warn("[ChangeHKD] không thấy ô/nút lưu ngành không mã, bỏ qua và tiếp tục luồng");
        await setFillAllState(st);
      } else {
        const current = String(textarea.value || "").trim();
        const currentFold = foldBusinessPageText(current);
        const missing = textOnly.filter((name) => !currentFold.includes(foldBusinessPageText(name)));
        await setFillAllState(st);
        if (missing.length) {
          setNativeValue(textarea, [current, ...missing].filter(Boolean).join("\n"), { typing: true, commit: true });
          console.log("[ChangeHKD] bổ sung ngành không mã:", missing);
          const reloaded = await clickSaveDetectReload(save);
          if (reloaded) return;
        }
      }
    }

    // Chỉ đổi ngành chính khi Thông báo đánh dấu rõ một ngành bổ sung là chính.
    const requestedMain = availableCoded.find((item) => item && item.main);
    if (requestedMain && !st.nnMainDone) {
      const code = String(requestedMain.code || requestedMain.ma).replace(/\D/g, "");
      if (!isBusinessMainSet(code)) {
        st.nnMainDone = true;
        await setFillAllState(st);
        const reloaded = await setBusinessMainAndUpdate(code);
        if (reloaded) return;
      }
    }

    if (!st.nnDescriptionsDone && availableCoded.length) {
      st.nnDescriptionsDone = true;
      const changed = fillBusinessLineDescriptions({ items: availableCoded });
      await setFillAllState(st);
      if (changed) {
        const update = findBusinessLineUpdateButton();
        if (update && await clickSaveDetectReload(update)) return;
      }
    }

    return void advanceFillAll(st);
  }

  // Ô mặc định theo địa bàn do backend dùng chung trả trong businessDefaults. Extension chỉ ánh xạ
  // khóa nghiệp vụ vào control HkdOnline, đồng thời ghi đè field cũ nếu backend đã trả cùng control.
  const LOCAL_DEFAULT_FIELDS = {
    "nguoi-nop-ho-so": [
      { key: "postalServiceAddress", name: "ctl00$C$POSTAL_SERVICEFld", comp: "dom-input" },
    ],
  };

  function applyBusinessLocalDefaults(fields, defaults, pageKey) {
    const out = Array.isArray(fields) ? fields.slice() : [];
    const specs = LOCAL_DEFAULT_FIELDS[pageKey] || [];
    for (const spec of specs) {
      const value = defaults && defaults[spec.key];
      if (!value) continue;
      const idx = out.findIndex((f) => f && f.name === spec.name);
      if (idx >= 0) out[idx] = { ...out[idx], value };
      else out.push({ name: spec.name, comp: spec.comp, value });
      console.log("[FillAll] default theo địa bàn:", spec.name, "=", value);
    }
    return out;
  }

  function localDefaultFieldsFor(defaults, pageKey) {
    return applyBusinessLocalDefaults([], defaults, pageKey);
  }

  // Chỉ trang NGƯỜI NỘP mới dùng nút "Sao chép thông tin đăng ký tài khoản": khối đó phải mang
  // nhân thân của chính người đang đăng nhập. Trang chủ hộ KHÔNG copy (xem handleOwnerPage).
  const COPY_PERSON_CFG = {
    "nguoi-nop-ho-so": {
      copyBtn: 'input[name="ctl00$C$btnIS_SIGNER"], #ctl00_C_btnIS_SIGNER',
      nameFilled: () => !!((document.getElementById("ctl00_C_PERSCtl_FULL_NAMEFld_Vw") || {}).textContent || "").trim(),
      addrMatch: /\$C\$PERSCtl\$ADDRCCtl/,
      requireCopiedContact: true,
      readPhone: () => readAcctContact("ctl00_C_PERSCtl_PHONEFld"),
      readEmail: () => readAcctContact("ctl00_C_PERSCtl_EMAILFld"),
    },
  };

  // Trang chủ hộ chỉ cần biết ô nào thuộc khối địa chỉ (điền bằng cascade riêng).
  const OWNER_PAGE_CFG = { addrMatch: /OWN_PCtl\$PERSCtl\$ADDRCCtl/ };

  // Ô nhân thân + liên hệ của một người: điền bằng hàm riêng, KHÔNG đi qua fillFormStandard chung.
  const PERSON_CONTROL_RE = /FULL_NAME|GENDER|DATE_OF_BIRTH|PERS_DOC_NO|PHONE|FAX|EMAIL|URL/i;

  // Nhân thân + liên hệ CHỦ HỘ lấy nguyên từ GIẤY ĐỀ NGHỊ. Cổng không có nguồn nào đúng hơn cho
  // khối này, nên ô nào đơn không kê khai thì XÓA — không giữ lại giá trị lạ của lần chạy trước.
  const OWNER_PERSON_FIELDS = [
    { pattern: /FULL_NAMEFld$/i, id: "ctl00_C_OWN_PCtl_PERSCtl_FULL_NAMEFld" },
    { pattern: /GENDER_IDFld$/i, radioName: "ctl00$C$OWN_PCtl$PERSCtl$GENDER_IDFld" },
    { pattern: /DATE_OF_BIRTHFld$/i, id: "ctl00_C_OWN_PCtl_PERSCtl_DATE_OF_BIRTHFld" },
    { pattern: /PERS_DOC_NOFld$/i, id: "ctl00_C_OWN_PCtl_PERSCtl_PERS_DOC_NOFld" },
    { pattern: /PHONEFld$/i, id: "ctl00_C_OWN_PCtl_PERSCtl_PHONEFld" },
    { pattern: /FAXFld$/i, id: "ctl00_C_OWN_PCtl_PERSCtl_FAXFld" },
    { pattern: /EMAILFld$/i, id: "ctl00_C_OWN_PCtl_PERSCtl_EMAILFld" },
    { pattern: /URLFld$/i, id: "ctl00_C_OWN_PCtl_PERSCtl_URLFld" },
  ];

  function applyOwnerFromDossier(fields) {
    for (const { pattern, id, radioName } of OWNER_PERSON_FIELDS) {
      const source = fields.find((f) => pattern.test(f.name || ""));
      const value = source ? String(source.value ?? "") : "";
      if (radioName) { setGenderRadio(radioName, value); continue; }
      const el = document.getElementById(id);
      if (!el) continue;
      // Input disabled/readonly KHÔNG được trình duyệt submit → giá trị vừa ghi sẽ mất sau postback
      // kế tiếp. Trước đây nút "Sao chép" lo việc mở khóa này; bỏ nút thì phải tự mở.
      if (el.disabled) el.disabled = false;
      if (el.readOnly) el.readOnly = false;
      if (norm(el.value) === norm(value)) continue;
      setNativeValue(el, value, { typing: false, commit: true });
    }
  }

  /**
   * Trang "Thông tin về chủ hộ kinh doanh" — điền THẲNG từ giấy đề nghị, KHÔNG bấm
   * "Sao chép thông tin đăng ký tài khoản".
   *
   * Chủ hộ là người trên GIẤY ĐỀ NGHỊ, không phải người đang đăng nhập cổng. Nút sao chép đổ nhân
   * thân + liên hệ của tài khoản vào khối này rồi lại phải ghi đè ngược: thừa một vòng AJAX, và
   * ghi đè hụt ô nào là hồ sơ mang dữ liệu sai người ở ô đó.
   */
  async function handleOwnerPage(st) {
    ensureConfirmOverride();
    const cfg = OWNER_PAGE_CFG;
    const fields = (st.pages && st.pages["chu-ho-kinh-doanh"]) || [];
    if (st.workflow === "change") return void handleChangeOwnerPage(st, fields, cfg);

    // 1. Radio cấu trúc (OWNER_TYPE = cá nhân) trước: cổng render lại khối nhân thân theo ô này.
    if (st.filledStep !== st.step) {
      st.filledStep = st.step;
      await setFillAllState(st); // persist TRƯỚC khi fill để postback giữa chừng không fill lại
      const structural = fields.filter((f) => !/^__/.test(f.name || "")
        && !cfg.addrMatch.test(f.name || "")
        && !PERSON_CONTROL_RE.test(f.name || ""));
      if (structural.length) { try { await fillFormStandard(structural); } catch (e) { /* ignore */ } }
      await sleep(300);
    }

    // 2. Nhân thân + liên hệ chủ hộ theo đơn.
    applyOwnerFromDossier(fields);

    // 3. Địa chỉ cá nhân của chủ hộ: cascade quốc gia → tỉnh → xã → số nhà.
    const address = fields.filter((f) => cfg.addrMatch.test(f.name || ""));
    try { await fillAddressCascade(address); } catch (e) { /* ignore */ }

    // 4. Mỗi postback của cascade địa chỉ đều render lại khối nhân thân → ghi lại ngay trước khi Lưu.
    applyOwnerFromDossier(fields);

    const saveBtn = findBusinessSaveButton();
    if (!saveBtn || saveBtn.disabled) return void advanceFillAll(st);
    st.phase = "saving";
    await setFillAllState(st);
    const reloaded = await clickSaveDetectReload(saveBtn);
    if (reloaded) return;
    return void advanceFillAll(st);
  }

  /** Trang NGƯỜI NỘP HỒ SƠ: khối này phải mang nhân thân của chính người đang đăng nhập nên vẫn
   *  phải bấm "Sao chép thông tin đăng ký tài khoản". Trang chủ hộ dùng handleOwnerPage. */
  async function handleCopyPersonPage(st, targetKey) {
    ensureConfirmOverride();
    const cfg = COPY_PERSON_CFG[targetKey];
    const fields = applyBusinessLocalDefaults(
      (st.pages && st.pages[targetKey]) || [], st.businessDefaults, targetKey);

    if (targetKey === "nguoi-nop-ho-so") {
      // Vì sao vai trò lại ra như vậy — in ngay đầu mỗi lượt để soi được khi cổng tick sai.
      console.log("[FillAll] vai trò người nộp — businessDefaults:",
        JSON.stringify(st.businessDefaults || null),
        "| workflow:", st.workflow || "create",
        "| ép Người có thẩm quyền ký:", forceSelfSubmitter(st));
    }

    // Nhân thân người nộp = CCCD của CHÍNH NGƯỜI ĐANG ĐĂNG NHẬP trong hồ sơ. Chỉ xác định được sau
    // bước "Sao chép thông tin đăng ký tài khoản" (lúc đó form mới có tên/số định danh của tài khoản).
    let submitterOverride = null;
    // Chỉ dùng để lấy ĐỊA CHỈ (không ghi đè nhân thân) ở nhánh ép vai trò Đà Nẵng.
    let submitterAddressCard = null;
    // null = chưa đối chiếu → bước 3 cứ bám radio thật như cũ.
    let submitterIsOwnerAccount = null;

    // 1. Điền trường CẤU TRÚC (không phải địa chỉ, không phải thông tin cá nhân/liên hệ do copy điền),
    //    vd radio loại chủ thể (OWNER_TYPE) / loại người nộp (PERS_SUBGroup) — 1 lần.
    if (st.filledStep !== st.step) {
      st.filledStep = st.step;
      await setFillAllState(st);
      const structural = fields.filter((f) =>
        !/^__/.test(f.name || "") && // field metadata (__applicantAddress...) không phải control trên DOM
        !cfg.addrMatch.test(f.name || "") &&
        // Tài khoản Đà Nẵng: vai trò người nộp do bước 2c chốt cứng, KHÔNG điền radio vai trò theo
        // backend (backend không biết ai đăng nhập; tick "Người được ủy quyền" ở đây là thừa một
        // postback rồi lại phải tick ngược về).
        !(forceSelfSubmitter(st) && /PERS_SUBGroup/.test(f.name || "")) &&
        !PERSON_CONTROL_RE.test(f.name || "")
      );
      if (structural.length) { try { await fillFormStandard(structural); } catch (e) { /* ignore */ } }
      await sleep(300);
    }

    // "Person đã sẵn": có HỌ TÊN; với trang cần bắt liên hệ thì PHẢI có sđt HOẶC email (cổng có thể tự
    // nạp tên nhưng sđt/email chỉ có SAU khi bấm Sao chép → không được chỉ xét tên).
    const personReady = () => cfg.nameFilled()
      && (!cfg.requireCopiedContact || cfg.readPhone() || cfg.readEmail());

    // 2. Bấm "Sao chép thông tin đăng ký tài khoản" cho tới khi person sẵn (nút trong UpdatePanel → AJAX → CHỜ).
    if (!personReady() && (st.copyTries || 0) < 3) {
      const copyBtn = document.querySelector(cfg.copyBtn);
      if (copyBtn) {
        st.copyTries = (st.copyTries || 0) + 1;
        await setFillAllState(st);
        console.log("[FillAll]", targetKey, "— bấm Sao chép thông tin đăng ký tài khoản");
        try { copyBtn.click(); } catch (e) { /* ignore */ }
        const ok = await waitFor(personReady, 7000, 250);
        if (!ok) return; // đang reload / copy chưa xong → xử lý lần kế
      }
    }

    // 2c. Chốt vai trò người nộp:
    //  - So sánh tài khoản với chủ hộ theo số định danh VÀ họ tên
    //  - Chủ hộ: Nếu số HOẶC tên KHỚP (chỉ cần 1 trong 2)
    //  - Người được ủy quyền: Nếu CẢ số VÀ tên đều KHÁC
    //  - Ngoại lệ Đà Nẵng: bỏ qua hết phần đối chiếu, luôn giữ "Người có thẩm quyền ký".
    if (targetKey === "nguoi-nop-ho-so" && forceSelfSubmitter(st)) {
      await tickSubmitterSelfRadio();
      // Ép vai trò CHỈ ép cái radio. NGƯỜI NỘP vẫn là người đang đăng nhập, nên khi tài khoản KHÔNG
      // phải chủ hộ thì tuyệt đối không được kéo nhân thân/địa chỉ chủ hộ sang khối người nộp:
      //  - Nhân thân: giữ nguyên dữ liệu nút "Sao chép tài khoản" vừa đổ vào (submitterOverride để
      //    null nên bước 2d/4 không ghi đè).
      //  - Địa chỉ: lấy trên CCCD của chính người đăng nhập; không khớp thẻ nào thì để TRỐNG.
      const ownerMatch = matchAccountWithOwner(st);
      submitterIsOwnerAccount = ownerMatch.isOwner || ownerMatch.ownerUnknown;
      if (!submitterIsOwnerAccount) {
        submitterAddressCard = matchSubmitterIdentityCandidate(st, fields);
        console.log("[FillAll] tài khoản Đà Nẵng nhưng KHÁC chủ hộ → giữ tick Người có thẩm quyền ký,",
          submitterAddressCard
            ? `địa chỉ lấy trên CCCD của ${submitterAddressCard.hoTen}`
            : "không có CCCD nào khớp tài khoản → để trống địa chỉ");
      }
    } else if (targetKey === "nguoi-nop-ho-so") {
      const { isOwner, ownerUnknown, idMatches } = matchAccountWithOwner(st);

      const authRadio = findSubmitterRoleRadio(true);
      const selfRadio = findSubmitterRoleRadio(false);

      if (isOwner) {
        console.log("[FillAll] tài khoản khớp chủ hộ",
          idMatches ? "(số định danh)" : "(họ tên)", "→ Người có thẩm quyền ký");
        // Hồ sơ mở lại (hoặc lần chạy trước tick nhầm) có thể đang ở "Người được ủy quyền" → tick lại
        // "Người có thẩm quyền ký Giấy đề nghị đăng ký Hộ kinh doanh" để cổng render khối chủ hộ.
        if (selfRadio && !selfRadio.checked) {
          (document.querySelector(`label[for="${CSS.escape(selfRadio.id)}"]`) || selfRadio).click();
          await waitForPanelSettle("ctl00_C_PERSCtl_FULL_NAMEFld");
        }
      } else if (ownerUnknown) {
        console.warn("[FillAll] hồ sơ không có nhân thân chủ hộ để đối chiếu → giữ nguyên vai trò đang tick");
      } else if (authRadio && !authRadio.checked) {
        // CẢ số VÀ tên đều khác → chọn Người được ủy quyền
        console.log("[FillAll] tài khoản khác chủ hộ (cả số và tên) → chọn Người được ủy quyền");
        (document.querySelector(`label[for="${CSS.escape(authRadio.id)}"]`) || authRadio).click();
        // Radio này AutoPostBack: phải CHỜ cổng render lại khối người nộp xong
        await waitForPanelSettle("ctl00_C_PERSCtl_FULL_NAMEFld");
      }

      // 2d. Người đăng nhập KHÔNG phải chủ hộ ⇒ chính họ là người nộp. Tìm đúng CCCD của họ trong hồ
      // sơ (khớp số định danh HOẶC họ tên với dữ liệu vừa sao chép) rồi ghi nhân thân + địa chỉ của
      // thẻ đó vào khối người nộp. Không khớp thẻ nào → giữ nguyên dữ liệu tài khoản, không đoán bừa.
      // Xét theo radio THẬT đang tick (đã chốt ở 2c) để không ghi đè khi form đang ở nhánh chủ hộ.
      if (submitterIsAuthorized()) {
        submitterOverride = buildSubmitterOverride(st, fields);
        if (submitterOverride && submitterNeedsRewrite(submitterOverride)) {
          if (await enableSubmitterEdit(st)) return; // cổng reload → lần chạy kế điền tiếp
          applySubmitterOverride(submitterOverride);
        }
      }
    }

    // 3. Điền ĐỊA CHỈ từ backend — cascade inline (quốc gia→tỉnh→xã→số nhà).
    let addrFields = fields.filter((f) => cfg.addrMatch.test(f.name || ""));
    if (targetKey === "nguoi-nop-ho-so") {
      addrFields = submitterAddressFields(st, fields, addrFields,
        submitterOverride || submitterAddressCard, submitterIsOwnerAccount);
    }
    try { await fillAddressCascade(addrFields); } catch (e) { /* ignore */ }

    // 4. Lưu. Ghi lại nhân thân người nộp ngay trước khi Lưu: mỗi postback của cascade địa chỉ đều
    // render lại khối người nộp theo dữ liệu tài khoản nên bản ghi ở bước 2d có thể đã bị đè.
    if (submitterOverride && submitterNeedsRewrite(submitterOverride)) {
      if (await enableSubmitterEdit(st)) return;
      applySubmitterOverride(submitterOverride);
    }
    // Cascade địa chỉ có thể render lại cả form; default địa bàn phải được ghi lại ngay trước Lưu.
    const localDefaults = localDefaultFieldsFor(st.businessDefaults, targetKey);
    if (localDefaults.length) {
      try { await fillFormStandard(localDefaults); } catch (e) { /* ignore */ }
    }
    const saveBtn = findBusinessSaveButton();
    if (!saveBtn) return void advanceFillAll(st);
    if (saveBtn.disabled) {
      // HkdOnline đôi khi không bật cờ dirty khi extension phát input/change bằng script. Nếu trang
      // thực sự có dữ liệu cần lưu thì vẫn phải mở nút và postback, không được lặng lẽ bỏ qua trang.
      const hadChanges = fields.length > 0 || !!submitterOverride;
      if (!hadChanges) return void advanceFillAll(st);
      try { saveBtn.removeAttribute("disabled"); } catch (e) { /* ignore */ }
    }
    st.phase = "saving";
    await setFillAllState(st);
    const reloaded = await clickSaveDetectReload(saveBtn);
    if (reloaded) return;
    return void advanceFillAll(st);
  }

  async function handleChangeOwnerPage(st, fields, cfg) {
    // Chủ hộ mới là dữ liệu của hồ sơ, không mặc định là tài khoản đang nộp. Bật Sửa đổi dữ liệu
    // trước (AutoPostBack), sau đó mới điền nhân thân/địa chỉ và lưu.
    const personChange = document.querySelector(
      'input[name="ctl00$C$OWN_PCtl$PERSCtl$PERSONChange"], #ctl00_C_OWN_PCtl_PERSCtl_PERSONChange'
    );
    if (personChange && !personChange.checked) {
      st.ownerEnableTries = (st.ownerEnableTries || 0) + 1;
      if (st.ownerEnableTries > 3) return void failChangeWorkflow("Không bật được Sửa đổi dữ liệu chủ hộ kinh doanh.");
      await setFillAllState(st);
      const reloaded = await clickSaveDetectReload(personChange);
      if (reloaded) return;
    }

    const address = fields.filter((field) => cfg.addrMatch.test(field.name || ""));
    const stable = fields.filter((field) => !cfg.addrMatch.test(field.name || "")
      && !/PERSONChange/.test(field.name || ""));
    try { await fillFormStandard(stable); } catch (e) { /* ignore */ }
    try { await fillAddressCascade(address); } catch (e) { /* ignore */ }

    const save = findBusinessSaveButton();
    if (!save || save.disabled) return void advanceFillAll(st);
    st.phase = "saving";
    await setFillAllState(st);
    const reloaded = await clickSaveDetectReload(save);
    if (reloaded) return;
    return void advanceFillAll(st);
  }

  function readPersonControl(baseId) {
    const input = document.getElementById(baseId);
    const view = document.getElementById(baseId + "_Vw");
    return norm((input && input.value) || (view && view.textContent) || "");
  }

  /** Giá trị THÔ của control nhân thân — readPersonControl() hạ chữ thường nên chỉ hợp để SO SÁNH,
   *  ghi ngược lên form phải dùng bản thô này (giữ nguyên hoa/thường và dấu tiếng Việt). */
  function readPersonControlRaw(baseId) {
    const input = document.getElementById(baseId);
    const view = document.getElementById(baseId + "_Vw");
    return String((input && input.value) || (view && view.textContent) || "").replace(/\s+/g, " ").trim();
  }

  /** Tick radio giới tính: thử value backend ("M"/"F"), rồi value cổng ("1"=Nam/"0"=Nữ), rồi theo label. */
  function setGenderRadio(radioName, wantedValue) {
    const wanted = String(wantedValue || "");
    let radio = document.querySelector(`input[type="radio"][name="${radioName}"][value="${wanted}"]`);
    if (!radio && wanted) {
      const gender = foldBusinessPageText(wanted);
      const mappedValue = (gender === "m" || gender === "nam" || gender === "1") ? "1"
        : (gender === "f" || gender === "nu" || gender === "nữ" || gender === "0") ? "0" : null;
      if (mappedValue) {
        radio = document.querySelector(`input[type="radio"][name="${radioName}"][value="${mappedValue}"]`);
      }
      if (!radio) {
        const allRadios = Array.from(document.querySelectorAll(`input[type="radio"][name="${radioName}"]`));
        radio = allRadios.find((r) => {
          const label = document.querySelector(`label[for="${r.id}"]`) || r.closest("label") || r.parentElement;
          return foldBusinessPageText(label ? label.textContent : "").includes(gender);
        });
      }
    }
    if (!radio || radio.checked) return !!radio;
    radio.checked = true;
    radio.dispatchEvent(new Event("click", { bubbles: true }));
    radio.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  // Nhân thân người nộp lấy từ GIẤY ỦY QUYỀN, ghi đè lên dữ liệu tài khoản mà nút "Sao chép thông tin
  // đăng ký tài khoản" vừa đổ vào. KHÔNG đụng tới sđt/email: hồ sơ vẫn nhận thông báo qua liên hệ
  // của tài khoản đang nộp.
  const SUBMITTER_OVERRIDE_FIELDS = [
    { key: "hoTen", id: "ctl00_C_PERSCtl_FULL_NAMEFld" },
    { key: "gioiTinh", radioName: "ctl00$C$PERSCtl$GENDER_IDFld" },
    { key: "ngaySinh", id: "ctl00_C_PERSCtl_DATE_OF_BIRTHFld" },
    { key: "soDinhDanh", id: "ctl00_C_PERSCtl_PERS_DOC_NOFld" },
  ];

  function findCheckboxByLabel(folded) {
    return Array.from(document.querySelectorAll('input[type="checkbox"]')).find((box) => {
      const label = (box.id && document.querySelector(`label[for="${box.id}"]`))
        || box.closest("label") || box.parentElement;
      return foldBusinessPageText(label ? label.textContent : "").includes(folded);
    }) || null;
  }

  /**
   * Bật "Sửa đổi dữ liệu" ở khối người nộp — điều kiện để nhập được người được ủy quyền.
   * Cổng khóa nhân thân đã "Khớp với CSDLQG về dân cư"; BỎ tích thì cổng nạp lại ngay dữ liệu tài
   * khoản (đã xem trực tiếp trên cổng) nên tích xong phải GIỮ NGUYÊN tới lúc Lưu.
   * Trả true nếu cổng reload cả trang → lần chạy kế của state machine điền tiếp.
   */
  async function enableSubmitterEdit(st) {
    const box = document.querySelector(
      'input[name="ctl00$C$PERSCtl$PERSONChange"], #ctl00_C_PERSCtl_PERSONChange'
    ) || findCheckboxByLabel("sua doi du lieu");
    if (!box) {
      console.warn("[FillAll] không thấy ô 'Sửa đổi dữ liệu' ở khối người nộp");
      return false;
    }
    if (box.checked) return false;
    if ((st.submitterEditTries || 0) >= 3) return false;
    st.submitterEditTries = (st.submitterEditTries || 0) + 1;
    await setFillAllState(st); // persist TRƯỚC: ô này AutoPostBack, có thể reload cả trang
    console.log("[FillAll] bật 'Sửa đổi dữ liệu' để nhập người được ủy quyền");
    if (await clickSaveDetectReload(box)) return true;
    await waitForPanelSettle("ctl00_C_PERSCtl_FULL_NAMEFld");
    return false;
  }

  /**
   * Chờ UpdatePanel của cổng render xong sau một postback AJAX.
   * Dấu hiệu: node đích bị thay bằng node mới (ASP.NET dựng lại DOM của panel) rồi đứng yên. Không đọc
   * được Sys.WebForms từ content script (isolated world) nên bám theo chính DOM.
   */
  async function waitForPanelSettle(id, timeout = 4000) {
    const before = document.getElementById(id);
    await waitFor(() => document.getElementById(id) !== before, timeout, 150);
    let last = document.getElementById(id);
    for (let i = 0; i < 6; i += 1) {
      await sleep(200);
      const now = document.getElementById(id);
      if (now === last) return; // hai nhịp liền không đổi node → panel đã ổn định
      last = now;
    }
  }

  /**
   * Ghi nhân thân người ĐƯỢC ủy quyền đè lên dữ liệu tài khoản ở khối người nộp hồ sơ.
   * Giống cách trang chủ hộ ghi đè: set thẳng value (KHÔNG bấm "Xóa"), sau khi enableSubmitterEdit()
   * đã bật "Sửa đổi dữ liệu". Ô của trang này có thể là input (kể cả đang disabled) hoặc span hiển
   * thị `..._Vw` — ghi cả hai nếu có để giá trị vừa hiện đúng vừa được submit.
   */
  function applySubmitterOverride(override) {
    if (!override || override.role !== "authorized") return;
    const missing = [];
    for (const { key, id, radioName } of SUBMITTER_OVERRIDE_FIELDS) {
      const value = String(override[key] || "").trim(); // norm() hạ chữ thường → chỉ dùng để SO SÁNH
      if (!value) continue;
      if (radioName) {
        if (!setGenderRadio(radioName, value)) missing.push(key);
        continue;
      }
      const el = document.getElementById(id);
      const view = document.getElementById(`${id}_Vw`);
      if (!el && !view) { missing.push(key); continue; }
      const state = el ? `input disabled=${!!el.disabled} readonly=${!!el.readOnly}` : "chỉ có span _Vw";
      if (el) {
        // Input bị disable KHÔNG được trình duyệt submit → giá trị vừa gõ mất sau postback kế tiếp.
        // Bỏ disable/readonly ngay trước khi ghi để giá trị đi cùng form (không đụng "Sửa đổi dữ liệu").
        if (el.disabled) el.disabled = false;
        if (el.readOnly) el.readOnly = false;
        if (norm(el.value) !== norm(value)) setNativeValue(el, value, { typing: false, commit: true });
      }
      if (view) view.textContent = value;
      console.log("[FillAll] người được ủy quyền:", key, "=", value, `(${state})`);
    }
    if (missing.length) {
      console.warn("[FillAll] người được ủy quyền — không thấy ô:", missing.join(", "));
    }
  }

  function matchCopiedApplicant(candidates) {
    const rows = Array.isArray(candidates) ? candidates.filter((item) => item && typeof item === "object") : [];
    const uiName = foldBusinessPageText(readPersonControl("ctl00_C_PERSCtl_FULL_NAMEFld"));
    const uiId = readPersonControl("ctl00_C_PERSCtl_PERS_DOC_NOFld").replace(/\D/g, "");
    if (!uiName && !uiId) return null;
    return rows.find((item) => {
      const name = foldBusinessPageText(item.hoTen || "");
      const id = String(item.soDinhDanh || "").replace(/\D/g, "");
      return !!uiName && !!uiId && name === uiName && id === uiId;
    }) || rows.find((item) => {
      const name = foldBusinessPageText(item.hoTen || "");
      const id = String(item.soDinhDanh || "").replace(/\D/g, "");
      return !!uiId && id === uiId && (!uiName || !name || name === uiName);
    });
  }

  function applicantAddressFields(address) {
    if (!address || typeof address !== "object") return [];
    const base = "ctl00$C$PERSCtl$ADDRCCtl";
    const out = [
      { name: `${base}$COUNTRY_IDFld`, comp: "dom-select", value: address.quocGia || "Việt Nam" },
      { name: `${base}$CITY_IDFld`, comp: "dom-select", value: address.tinh || "" },
      { name: `${base}$WARD_IDFld`, comp: "dom-select", value: address.xa || "" },
      { name: `${base}$STREET_NUMBERFld`, comp: "dom-input", value: address.diaChi || "" },
    ].filter((field) => field.value);
    // Chỉ có mỗi "Việt Nam" thì coi như không có địa chỉ → để nguồn kế tiếp trong chuỗi ưu tiên lo.
    return out.some((field) => !/COUNTRY_IDFld$/.test(field.name)) ? out : [];
  }

  // Hai thủ tục áp ngoại lệ Đà Nẵng: "Đăng ký hộ kinh doanh" (luồng 8 trang, state không gắn
  // workflow) và "Chấm dứt hoạt động hộ kinh doanh" (workflow "dissolution"). Thay đổi nội dung /
  // cấp lại GCN vẫn tự chốt vai trò bằng cách đối chiếu tài khoản với chủ hộ.
  const FORCE_SELF_SUBMITTER_WORKFLOWS = new Set(["create", "dissolution"]);

  /**
   * Tài khoản đăng nhập gắn tỉnh Đà Nẵng (popup đọc `tinh` từ /auth/me rồi gắn cờ vào
   * businessDefaults) ⇒ vai trò người nộp LUÔN là "Người có thẩm quyền ký Giấy đề nghị đăng ký Hộ
   * kinh doanh", KHÔNG bao giờ chuyển sang "Người được ủy quyền" dù nhân thân tài khoản khác chủ hộ.
   */
  function forceSelfSubmitter(st) {
    if (!st || !st.businessDefaults || !st.businessDefaults.forceSelfSubmitter) return false;
    return FORCE_SELF_SUBMITTER_WORKFLOWS.has(st.workflow || "create");
  }

  /**
   * Đối chiếu tài khoản ĐANG ĐĂNG NHẬP (dữ liệu nút "Sao chép thông tin đăng ký tài khoản" vừa đổ vào
   * khối người nộp) với nhân thân chủ hộ trong hồ sơ. Gom chủ hộ từ MỌI nguồn có:
   *  - pages["chu-ho-kinh-doanh"]: luồng đăng ký mới, và luồng thay đổi CÓ đổi chủ hộ (chủ hộ MỚI)
   *  - businessFlow.owner: chủ hộ HIỆN TẠI backend gửi kèm cho luồng thay đổi/chấm dứt (không có
   *    trang chủ hộ để đọc)
   *  - search.value khi tra cứu bằng số định danh chủ hộ
   * Khớp BẤT KỲ nguồn nào cũng là chủ hộ tự nộp: hồ sơ đổi chủ hộ có thể do chủ cũ hoặc chủ mới ký.
   * KHÔNG fallback về search.expectedName: đó là TÊN HỘ KINH DOANH, không phải tên chủ hộ — so với
   * tên tài khoản thì luôn lệch.
   */
  function matchAccountWithOwner(st) {
    const copiedId = readPersonControl("ctl00_C_PERSCtl_PERS_DOC_NOFld").replace(/\D/g, "");
    const copiedName = foldBusinessPageText(readPersonControl("ctl00_C_PERSCtl_FULL_NAMEFld"));

    const ownerIdentities = [];
    const addOwnerIdentity = (hoTen, soDinhDanh) => {
      const id = String(soDinhDanh || "").replace(/\D/g, "");
      const name = foldBusinessPageText(hoTen || "");
      if (id || name) ownerIdentities.push({ id, name });
    };

    const ownerFields = (st.pages && st.pages["chu-ho-kinh-doanh"]) || [];
    if (ownerFields.length) {
      const ownerIdField = ownerFields.find((f) => /PERS_DOC_NOFld$/i.test(f.name || ""));
      const ownerNameField = ownerFields.find((f) => /FULL_NAMEFld$/i.test(f.name || ""));
      addOwnerIdentity((ownerNameField && ownerNameField.value) || "",
        (ownerIdField && ownerIdField.value) || "");
    }
    const flowOwner = st.businessFlow?.owner || {};
    addOwnerIdentity(flowOwner.hoTen, flowOwner.soDinhDanh);
    if (st.businessFlow?.search?.method === "identityNumber") {
      addOwnerIdentity("", st.businessFlow.search.value);
    }

    // Chỉ kết luận "không phải chủ hộ" khi CẢ số VÀ tên đều KHÁC MỌI chủ hộ trong hồ sơ.
    const idMatches = ownerIdentities.some((o) => copiedId && o.id && copiedId === o.id);
    const nameMatches = ownerIdentities.some((o) => copiedName && o.name && copiedName === o.name);
    // Hồ sơ không cho biết chủ hộ là ai (cả số lẫn tên đều trống) → KHÔNG kết luận gì.
    return { isOwner: idMatches || nameMatches, ownerUnknown: !ownerIdentities.length, idMatches, nameMatches };
  }

  // Tên/value chính xác dùng được trên trang đăng ký mới; một số biến thể của trang thay đổi dùng
  // control khác nhưng giữ nguyên nhãn. Ưu tiên hợp đồng chính xác, rồi mới fallback theo nhãn hiện.
  function findSubmitterRoleRadio(authorized) {
    const value = authorized ? "IS_AUTHORIZED_BUTTON" : "IS_SIGNER_BUTTON";
    const byName = document.querySelector(`input[type="radio"][name="ctl00$C$PERS_SUBGroup"][value="${value}"]`);
    if (byName) return byName;
    const folded = authorized ? "nguoi duoc uy quyen" : "nguoi co tham quyen ky";
    return Array.from(document.querySelectorAll('input[type="radio"]')).find((radio) => {
      const label = (radio.id && document.querySelector(`label[for="${radio.id}"]`))
        || radio.closest("label") || radio.parentElement;
      return foldBusinessPageText(label ? label.textContent : "").includes(folded);
    }) || null;
  }

  /** Tick "Người có thẩm quyền ký Giấy đề nghị đăng ký Hộ kinh doanh" (radio AutoPostBack → phải chờ). */
  async function tickSubmitterSelfRadio() {
    const selfRadio = findSubmitterRoleRadio(false);
    if (!selfRadio) {
      console.warn("[FillAll] tài khoản Đà Nẵng: không thấy radio Người có thẩm quyền ký trên trang");
      return;
    }
    if (selfRadio.checked) {
      console.log("[FillAll] tài khoản Đà Nẵng → giữ nguyên Người có thẩm quyền ký");
      return;
    }
    // Hồ sơ mở lại (hoặc lần chạy trước tick nhầm) có thể đang ở "Người được ủy quyền" → tick lại.
    console.log("[FillAll] tài khoản Đà Nẵng → tick lại Người có thẩm quyền ký");
    (document.querySelector(`label[for="${CSS.escape(selfRadio.id)}"]`) || selfRadio).click();
    await waitForPanelSettle("ctl00_C_PERSCtl_FULL_NAMEFld");
  }

  /** Vai trò người nộp đang tick THẬT trên cổng (sau bước "Sao chép thông tin đăng ký tài khoản"). */
  function submitterIsAuthorized() {
    const authRadio = findSubmitterRoleRadio(true);
    if (authRadio) return !!authRadio.checked;
    const selfRadio = findSubmitterRoleRadio(false);
    return !!(selfRadio && !selfRadio.checked);
  }

  function readSubmitterPageField(st, fields, name) {
    const inPage = (fields || []).find((f) => f && f.name === name);
    if (inPage && inPage.value) return inPage.value;
    const nopFields = Array.isArray(st.pages && st.pages["nguoi-nop-ho-so"])
      ? st.pages["nguoi-nop-ho-so"] : [];
    const stored = nopFields.find((f) => f && f.name === name);
    return (stored && stored.value) || null;
  }

  /**
   * Nhân thân trong hồ sơ (thẻ căn cước HOẶC bên được ủy quyền đọc từ Giấy ủy quyền) thuộc về CHÍNH
   * NGƯỜI ĐANG ĐĂNG NHẬP — đối chiếu với dữ liệu nút "Sao chép thông tin đăng ký tài khoản".
   *
   * Khối người nộp trên cổng CHỈ nhận nhân thân của tài khoản đang đăng nhập: ghi nhân thân người
   * khác vào thì sau khi Lưu cổng đẩy ngược về dữ liệu tài khoản. Vì vậy phép khớp phải chặt:
   *  - Khớp SỐ ĐỊNH DANH là chắc nhất.
   *  - Chỉ khớp HỌ TÊN khi KHÔNG có số định danh nào phản chứng. Trùng tên mà số định danh khác thì
   *    đó là NGƯỜI KHÁC (hoặc OCR sai số) — ghi vào là chắc chắn sai.
   *  - Không khớp ai → trả null, KHÔNG lấy đại người đầu tiên (rất dễ vớ phải nhân thân chủ hộ).
   */
  function matchSubmitterIdentityCandidate(st, fields) {
    const fromPage = readSubmitterPageField(st, fields, "__identityCandidates");
    const fromFlow = st.businessFlow?.identityCandidates;
    const candidates = (Array.isArray(fromPage) && fromPage.length ? fromPage : fromFlow) || [];
    if (!Array.isArray(candidates) || !candidates.length) return null;

    const copiedName = foldBusinessPageText(readPersonControl("ctl00_C_PERSCtl_FULL_NAMEFld"));
    const copiedId = readPersonControl("ctl00_C_PERSCtl_PERS_DOC_NOFld").replace(/\D/g, "");
    if (!copiedName && !copiedId) return null;

    const idOf = (item) => String((item && item.soDinhDanh) || "").replace(/\D/g, "");
    const nameOf = (item) => foldBusinessPageText((item && item.hoTen) || "");

    // Khớp SỐ ĐỊNH DANH là chắc nhất, NHƯNG hồ sơ có thể chứa NHIỀU bản nhân thân của cùng một người
    // (bản đọc từ Giấy ủy quyền + bản đọc từ thẻ căn cước) và OCR có thể sai họ tên ở một trong hai.
    // Tài khoản đang đăng nhập là căn cứ đúng nhất → trong các bản cùng số định danh, chọn bản có
    // HỌ TÊN khớp luôn tên tài khoản; không bản nào khớp tên thì mới đành lấy bản đầu tiên.
    const idMatches = candidates.filter((item) => idOf(item) && copiedId && idOf(item) === copiedId);
    if (idMatches.length) {
      const exact = idMatches.find((item) => copiedName && nameOf(item) === copiedName);
      if (exact) return exact;
      if (copiedName && idMatches.length) {
        console.warn("[FillAll] nhân thân khớp số định danh nhưng LỆCH TÊN tài khoản:",
          idMatches.map((item) => item.hoTen).join(" / "), "≠", `"${copiedName}"`,
          "→ nhiều khả năng OCR sai tên, sẽ ghi tên theo tài khoản");
      }
      // Cùng số định danh = cùng người. Không bản nào khớp tên thì GỘP thay vì chọn bừa một bản, để
      // không mất ngày sinh / giới tính / địa chỉ mà chỉ một trong hai bản đọc được. Bản đứng trước
      // (giấy ủy quyền) vẫn thắng ở những field cả hai cùng có.
      return idMatches.reduce((acc, item) => {
        for (const key of Object.keys(item || {})) {
          const current = acc[key];
          if (current === undefined || current === null || current === "") acc[key] = item[key];
        }
        return acc;
      }, {});
    }

    const byName = candidates.find((item) => {
      if (!copiedName || nameOf(item) !== copiedName) return false;
      const id = idOf(item);
      // Cùng tên nhưng số định danh mâu thuẫn với tài khoản ⇒ KHÔNG phải người đang đăng nhập.
      if (id && copiedId && id !== copiedId) return false;
      return true;
    });
    if (byName) return byName;

    const conflicting = candidates.find((item) => copiedName && nameOf(item) === copiedName);
    if (conflicting) {
      console.warn("[FillAll] hồ sơ có người TRÙNG TÊN tài khoản nhưng số định danh khác",
        `(hồ sơ ${idOf(conflicting)} ≠ tài khoản ${copiedId})`,
        "→ coi là người khác, giữ nguyên dữ liệu tài khoản");
    }
    return null;
  }

  /** Nhân thân người nộp lấy từ CCCD của chính người đăng nhập; không khớp thẻ nào thì trả null. */
  function buildSubmitterOverride(st, fields) {
    const person = matchSubmitterIdentityCandidate(st, fields);
    if (!person) {
      console.warn("[FillAll] hồ sơ không có CCCD nào khớp người đăng nhập → giữ nguyên dữ liệu tài khoản");
      return null;
    }
    console.log("[FillAll] người nộp = CCCD khớp tài khoản:", person.hoTen, person.soDinhDanh);
    // HỌ TÊN luôn lấy theo TÀI KHOẢN đang đăng nhập, không lấy tên OCR được từ hồ sơ. Khối người nộp
    // trên cổng chỉ nhận nhân thân của chính tài khoản; tên lệch một dấu (giấy ủy quyền viết tay rất
    // hay sai dấu) là sau khi Lưu bị đẩy ngược về dữ liệu tài khoản. Lưu ý phép so tên ở trên BỎ DẤU
    // nên "Thiệt" vẫn khớp "Thiết" — không thể dựa vào nó để phát hiện sai dấu. Hồ sơ chỉ còn nhiệm vụ
    // cấp ngày sinh / giới tính / địa chỉ, những thứ nút "Sao chép tài khoản" không đổ vào.
    const accountName = readPersonControlRaw("ctl00_C_PERSCtl_FULL_NAMEFld");
    if (!accountName) return { role: "authorized", ...person };
    if (foldBusinessPageText(person.hoTen || "") !== foldBusinessPageText(accountName)) {
      console.warn("[FillAll] tên trong hồ sơ khác hẳn tên tài khoản:",
        `"${person.hoTen}"`, "≠", `"${accountName}"`, "→ ghi theo tài khoản");
    }
    return { role: "authorized", ...person, hoTen: accountName };
  }

  /** Nhân thân trên form đã đúng người nộp chưa — đỡ phải bật "Sửa đổi dữ liệu" một cách vô ích. */
  function submitterNeedsRewrite(override) {
    const currentId = readPersonControl("ctl00_C_PERSCtl_PERS_DOC_NOFld").replace(/\D/g, "");
    const currentName = foldBusinessPageText(readPersonControl("ctl00_C_PERSCtl_FULL_NAMEFld"));
    const wantedId = String(override.soDinhDanh || "").replace(/\D/g, "");
    const wantedName = foldBusinessPageText(override.hoTen || "");
    return (!!wantedId && wantedId !== currentId) || (!!wantedName && wantedName !== currentName);
  }

  /**
   * Địa chỉ người nộp hồ sơ theo ĐÚNG người đang nộp:
   *  - Tài khoản CHÍNH LÀ chủ hộ → địa chỉ cá nhân ghi trong ĐƠN (Giấy đề nghị), backend gửi sẵn
   *    trong __applicantAddress.self.
   *  - Tài khoản KHÁC chủ hộ → địa chỉ trên CCCD của chính người đăng nhập (identityCard). Không
   *    khớp được thẻ nào thì KHÔNG điền gì (thà để trống còn hơn ghi địa chỉ chủ hộ vào người nộp).
   *
   * `isOwnerAccount` là kết quả đối chiếu tài khoản ↔ chủ hộ do caller truyền xuống. Bỏ trống thì
   * suy từ radio thật trên cổng như cũ — CHỈ đúng khi vai trò được chốt bằng chính phép đối chiếu
   * đó. Nhánh ép vai trò (tài khoản Đà Nẵng) luôn tick "Người có thẩm quyền ký" kể cả khi tài khoản
   * không phải chủ hộ, nên ở đó radio KHÔNG còn nói lên ai là người nộp và caller phải truyền cờ.
   */
  function submitterAddressFields(st, fields, backendAddrFields, identityCard, isOwnerAccount) {
    const plan = readSubmitterPageField(st, fields, "__applicantAddress") || {};
    const isOwner = typeof isOwnerAccount === "boolean" ? isOwnerAccount : !submitterIsAuthorized();

    if (isOwner) {
      const own = applicantAddressFields(plan.self);
      if (own.length) {
        console.log("[FillAll] người nộp là chủ hộ → địa chỉ trong đơn:", JSON.stringify(plan.self));
        return own;
      }
      return backendAddrFields;
    }

    const fromIdentity = applicantAddressFields(identityCard && identityCard.diaChi);
    if (fromIdentity.length) {
      console.log("[FillAll] người nộp khác chủ hộ → địa chỉ trên CCCD:", JSON.stringify(identityCard.diaChi));
      return fromIdentity;
    }
    console.log("[FillAll] người nộp khác chủ hộ, không có CCCD khớp tài khoản → không điền địa chỉ");
    return [];
  }

  function areaFold(s) {
    return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/gi, "d")
      .toLowerCase().replace(/\s+/g, " ").trim()
      .replace(/^(phuong|xa|thi tran|tinh|thanh pho|tp)\s+/, "");
  }

  function areaSelectedText(sel) {
    const opt = sel && sel.selectedOptions && sel.selectedOptions[0];
    return opt ? opt.textContent : "";
  }

  function areaFindOption(sel, target) {
    const t = areaFold(target);
    if (!t) return null;
    const opts = Array.from(sel.options).filter((o) => o.value);
    return opts.find((o) => areaFold(o.textContent) === t)
      || (t.length > 2 ? opts.find((o) => areaFold(o.textContent).includes(t)) : null);
  }

  function areaIsAt(sel, target) {
    return !!target && areaFold(areaSelectedText(sel)) === areaFold(target);
  }

  function areaChoose(sel, target) {
    const opt = areaFindOption(sel, target);
    if (!opt) return false;
    sel.value = opt.value;
    sel.dispatchEvent(new Event("input", { bubbles: true }));
    sel.dispatchEvent(new Event("change", { bubbles: true })); // → onchange __doPostBack
    return true;
  }

  async function fillAddressCascade(fields) {
    const selInfo = (key) => {
      const f = fields.find((x) => new RegExp(key).test(x.name || ""));
      return f && f.value ? { f, target: String(f.value) } : null;
    };
    const chooseAndWait = async (info, waitReady) => {
      if (!info) return;
      const el = findStandardSelect(fieldCandidates(info.f));
      if (!el || areaIsAt(el, info.target)) return;
      if (!areaFindOption(el, info.target)) { console.warn("[FillAll] địa chỉ: chưa có option", info.target); return; }
      areaChoose(el, info.target); // dispatch change → onchange __doPostBack (AJAX partial)
      console.log("[FillAll] địa chỉ chọn:", info.target);
      if (waitReady) await waitFor(waitReady, 8000, 250);
      else await sleep(900);
    };

    const country = selInfo("COUNTRY_IDFld");
    const city = selInfo("CITY_IDFld");
    const ward = selInfo("WARD_IDFld");

    await chooseAndWait(country);
    // Chọn tỉnh xong → CHỜ danh sách xã nạp lại đến khi có option đích.
    await chooseAndWait(city, () => {
      if (!ward) return true;
      const w = findStandardSelect(fieldCandidates(ward.f));
      return w && !!areaFindOption(w, ward.target);
    });
    await chooseAndWait(ward);

    // Số nhà: set value KHÔNG kích onchange (tránh thêm 1 postback thừa); nút Lưu sẽ submit giá trị này.
    const sf = fields.find((x) => /STREET_NUMBER/.test(x.name || ""));
    if (sf && sf.value) {
      const el = findStandardInput(fieldCandidates(sf));
      if (el && norm(el.value) !== norm(String(sf.value))) {
        setNativeValue(el, sf.value, { typing: false, change: false, commit: false });
        console.log("[FillAll] địa chỉ số nhà:", sf.value);
      }
    }
  }

  async function handleAddressCascadePage(st, targetKey) {
    ensureConfirmOverride();
    const fields = (st.pages && st.pages[targetKey]) || [];

    // 1. Điền các trường KHÔNG postback (phone/email/fax/website/radio...) 1 lần.
    if (st.filledStep !== st.step) {
      st.filledStep = st.step;
      await setFillAllState(st);
      const nonAddr = fields.filter((f) => !isPostbackAddressField(f));
      if (nonAddr.length) { try { await fillFormStandard(nonAddr); } catch (e) { /* ignore */ } }
    }

    // 2. Cascade địa chỉ (inline). Nếu là full-postback thì reload sẽ cắt ngang → resume chạy tiếp phần còn lại.
    try { await fillAddressCascade(fields.filter((f) => isPostbackAddressField(f))); } catch (e) { /* ignore */ }

    // 3. Lưu.
    const saveBtn = findBusinessSaveButton();
    if (!saveBtn || saveBtn.disabled) return void advanceFillAll(st);
    st.phase = "saving";
    await setFillAllState(st);
    const reloaded = await clickSaveDetectReload(saveBtn);
    if (reloaded) return;
    return void advanceFillAll(st);
  }

  function isTaxAddressModeField(f) {
    return /REP_RECV_ADDR_TYPEFld/.test(f?.name || "");
  }

  async function handleTaxPage(st) {
    ensureConfirmOverride();
    const fields = (st.pages && st.pages["thong-tin-ve-thue"]) || [];
    const stableFields = fields.filter((f) => !isTaxAddressModeField(f) && !isPostbackAddressField(f));
    const modeFields = fields.filter(isTaxAddressModeField);
    const addressFields = fields.filter((f) => isPostbackAddressField(f));

    // Trang thuế có radio "Địa chỉ nhận thông báo thuế" gây __doPostBack.
    // Xử lý như state machine nhỏ:
    // 1) stable: điền field không postback để người dùng thấy ngay.
    // 2) mode: đổi radio/cascade địa chỉ thuế (có thể postback làm mất DOM vừa điền).
    // 3) stable_again: LUÔN điền lại stable fields sau mọi postback trước khi Lưu.
    // Không dùng filledStep cho trang này vì đánh dấu sớm sẽ làm miss field sau reload.
    const phase = st.taxPhase || "stable";
    if (phase === "stable") {
      if (stableFields.length) { try { await fillFormStandard(stableFields); } catch (e) { /* ignore */ } }
      st.taxPhase = "mode";
      await setFillAllState(st);
    }

    if (st.taxPhase === "mode") {
      if (modeFields.length) { try { await fillFormStandard(modeFields); } catch (e) { /* ignore */ } }
      try { await fillAddressCascade(addressFields); } catch (e) { /* ignore */ }
      st.taxPhase = "stable_again";
      await setFillAllState(st);
    }

    if (stableFields.length) { try { await fillFormStandard(stableFields); } catch (e) { /* ignore */ } }

    const saveBtn = findBusinessSaveButton();
    if (!saveBtn || saveBtn.disabled) return void advanceFillAll(st);
    st.phase = "saving";
    await setFillAllState(st);
    const reloaded = await clickSaveDetectReload(saveBtn);
    if (reloaded) return;
    return void advanceFillAll(st);
  }

  async function handleChangeCapitalPage(st) {
    const fields = (st.pages && st.pages["thong-tin-ve-von"]) || [];
    // Loại tăng/giảm có thể AutoPostBack. Không dùng filledStep: sau reload phải điền lại số tiền
    // và thời điểm; select đã đúng sẽ không gây postback lần hai.
    try { await fillFormStandard(fields); } catch (e) { /* ignore */ }
    await sleep(500);
    const save = findBusinessSaveButton();
    if (!save || save.disabled) return void advanceFillAll(st);
    st.phase = "saving";
    await setFillAllState(st);
    const reloaded = await clickSaveDetectReload(save);
    if (reloaded) return;
    return void advanceFillAll(st);
  }

  // Điền xong 8 trang → nếu popup gửi kèm kế hoạch đính kèm (nút "Quét nhập thông tin và đính kèm")
  // thì TỰ CHẠY TIẾP state machine đính kèm; không thì kết thúc.
  async function finishFillAllThenAttach(st) {
    const payload = st && st.attachPayload;
    await clearFillAllState();
    if (payload && Array.isArray(payload.files) && payload.files.length
      && Array.isArray(payload.attachments) && payload.attachments.length
      && typeof H.startAttachAllBusiness === "function") {
      H.setRunProgressText(`✓ Đã điền xong ${st.order.length} trang. Bắt đầu đính kèm hồ sơ…\n(đừng thao tác tới khi xong)`);
      await H.startAttachAllBusiness(payload.files, payload.attachments);
      setTimeout(H.stepAttachAll, 400);
      return;
    }
    H.endFillAllUI(`✓ Đã điền xong ${st.order.length} trang. Vui lòng rà soát rồi bấm Nộp.`);
  }

  async function advanceFillAll(st) {
    if (H.isBusinessRunCancelled?.()) return;
    st.step += 1;
    st.retries = 0; st.phase = "fill"; st.filledStep = -1; st.navCount = 0;
    st.nnAdds = 0; st.nnAddTries = {}; st.nnSkippedAddCodes = []; st.nnSkip = [];
    st.nnMainDone = false; st.nnDescriptionsDone = false; st.nnBusinessActDefaultDone = false;
    st.nnRemoveTries = 0; st.nnTextDone = false; st.taxPhase = ""; st.copyTries = 0;
    await setFillAllState(st);
    if (st.step >= st.order.length) {
      return void finishFillAllThenAttach(st);
    }
    goToBusinessPageByKey(st.order[st.step]);
  }

  async function stepFillAll() {
    if (H.isBusinessRunCancelled?.()) return;
    const st = await getFillAllState();
    if (!st || !Array.isArray(st.order)) return;
    if (st.workflow === "create" && !st.bootstrapDone) {
      return void stepCreateBootstrap(st);
    }
    if ((["change", "reissue"].includes(st.businessFlow?.wizardType) || ["change", "reissue", "dissolution"].includes(st.workflow)) && !st.bootstrapDone) {
      return void stepChangeBootstrap(st);
    }
    const order = st.order;

    const finish = async () => { await finishFillAllThenAttach(st); };

    if (st.step >= order.length) return finish();
    const targetKey = order[st.step];
    const _det = detectBusinessPageKey();
    console.log("[FillAll] step", st.step, "phase", st.phase, "target", targetKey, "onPage", _det.pageKey, `(${_det.label})`);

    // Ưu tiên hoàn tất nhịp xóa trước cả thao tác banner/UI. Đây là phase đã được persist ngay
    // trước postback, nên sau reload chỉ cần đối chiếu row rồi tiếp tục luồng ngành nghề.
    if (st.workflow === "change" && st.phase === "deleting-industry"
      && targetKey === "nganh-nghe-kinh-doanh" && _det.pageKey === targetKey) {
      return void handleChangeBusinessLines(st);
    }
    H.setFillAllProgress(st.step + 1, order.length, BUSINESS_PAGE_LABELS[targetKey] || targetKey);

    // Vừa reload sau khi bấm Lưu → coi như đã lưu → sang trang kế.
    if (st.phase === "saving") {
      return void advanceFillAll(st);
    }

    // Chưa đúng trang mục tiêu → điều hướng tới (postback reload). Có chặn vòng lặp: quá 3 lần không
    // tới được trang thì bỏ qua trang đó (tránh kẹt vô hạn khi breadcrumb không nhận diện được).
    const { pageKey } = detectBusinessPageKey();
    if (pageKey !== targetKey) {
      st.navCount = (st.navStep === st.step ? (st.navCount || 0) : 0) + 1;
      st.navStep = st.step;
      if (st.navCount > 3) return void advanceFillAll(st); // không tới được → bỏ qua trang này
      await setFillAllState(st);
      return void goToBusinessPageByKey(targetKey);
    }

    // Trang NGÀNH NGHỀ: xử lý riêng (thêm lần lượt mọi mã + set ngành chính), KHÔNG dùng fill/save chung.
    if (targetKey === "nganh-nghe-kinh-doanh") {
      if (st.workflow === "change") return void handleChangeBusinessLines(st);
      return void handleNganhNghePage(st);
    }

    ensureConfirmOverride();

    if (targetKey === "thong-tin-de-nghi-cap-lai") {
      return void handleReissuePage(st);
    }

    // Trang CHỦ HỘ: điền thẳng từ giấy đề nghị, không bấm "Sao chép thông tin đăng ký tài khoản".
    if (targetKey === "chu-ho-kinh-doanh") {
      return void handleOwnerPage(st);
    }

    // Trang NGƯỜI NỘP có nút "Sao chép thông tin đăng ký tài khoản": khối này giữ nhân thân +
    // contact của chính tài khoản đang đăng nhập.
    if (targetKey === "nguoi-nop-ho-so") {
      return void handleCopyPersonPage(st, targetKey);
    }

    // Trang Địa chỉ trụ sở: cascade địa chỉ (quốc gia→tỉnh→xã→số nhà) + phone/email/website.
    if (targetKey === "dia-chi") {
      return void handleAddressCascadePage(st, targetKey);
    }

    // Trang thuế có radio địa chỉ nhận thông báo thuế gây postback; xử lý riêng để không hụt
    // "Số lượng lao động" và "Phương pháp tính thuế".
    if (targetKey === "thong-tin-ve-thue") {
      return void handleTaxPage(st);
    }

    if (targetKey === "thong-tin-ve-von" && st.workflow === "change") {
      return void handleChangeCapitalPage(st);
    }

    const pageFields = applyBusinessLocalDefaults(
      (st.pages && st.pages[targetKey]) || [], st.businessDefaults, targetKey);

    // Điền field trang này (chỉ 1 lần/step: mid-fill có thể postback như trang ngành nghề).
    if (st.filledStep !== st.step) {
      st.filledStep = st.step;
      await setFillAllState(st); // persist TRƯỚC khi fill để postback giữa chừng không fill lại
      if (pageFields.length) {
        try { await fillFormStandard(pageFields); } catch (e) { /* ignore */ }
      }
      await sleep(800); // để form "dirty" + cascade địa danh xong → nút Lưu bật
    }

    if (H.isBusinessRunCancelled?.()) return;

    const saveBtn = findBusinessSaveButton();
    if (!saveBtn) return void advanceFillAll(st);
    if (saveBtn.disabled) {
      if (!pageFields.length) return void advanceFillAll(st);
      try { saveBtn.removeAttribute("disabled"); } catch (e) { /* ignore */ }
    }

    st.phase = "saving";
    await setFillAllState(st);
    const reloaded = await clickSaveDetectReload(saveBtn);
    if (reloaded) return; // đang reload → bước "saving" xử lý ở lần load kế

    // Không reload = bị validation chặn → retry tối đa 2 lần rồi sang trang kế.
    st.retries = (st.retries || 0) + 1;
    st.phase = "fill";
    if (st.retries < 2) {
      st.filledStep = -1; // cho phép fill lại
      await setFillAllState(st);
      return void stepFillAll();
    }
    return void advanceFillAll(st);
  }

  // ===================== ĐÍNH KÈM HỘ KINH DOANH (cổng HkdOnline, nhiều postback) =====================
  // Luồng: (declare) mở modal cài đặt → khai báo loại tài liệu → đóng modal → click mục đầu (postback)
  //        (upload) trang tải: nhét TẤT CẢ file vào 1 input → "Tải lên" (postback)
  //        (classify) gán "Loại đính kèm" cho từng dòng theo phân loại BE → "Lưu" (postback) → xong.
  // State resume qua chrome.storage (autofill_attachall_state), giữ dataUrl file để nhét ở pha upload.
  const ATTACH_KEY = "autofill_attachall_state";

  // category cổng → giá trị option ở modal (#attId) và ở "Loại đính kèm" (droptypleAttach) + nhãn hiển thị.
  const ATTACH_TYPE = {
    BUSREGFRM: { attId: "1_BUSREGFRM", droptyple: "BUSREGFRM", label: "Giấy đề nghị đăng ký hộ kinh doanh" },
    // Giá trị option của cổng có thể thay đổi theo cấu hình địa phương; label exact là hợp đồng ổn định.
    BUSCHANGEFRM: { attId: "", droptyple: "", label: "Thông báo thay đổi nội dung đăng ký hộ kinh doanh" },
    BUSREISSUEFRM: { attId: "", droptyple: "", label: "Giấy đề nghị cấp lại Giấy chứng nhận đăng ký hộ kinh doanh" },
    DISSOLUTION_FAMILY_MINUTES: { attId: "", droptyple: "", label: "Bản sao biên bản họp thành viên hộ gia đình" },
    TAX_TERMINATION_NOTICE: { attId: "", droptyple: "", label: "Thông báo về việc chấm dứt hiệu lực mã số thuế của Cơ quan thuế" },
    DISSOLUTION_NOTICE: { attId: "", droptyple: "", label: "Thông báo về việc chấm dứt hoạt động hộ kinh doanh" },
    BUSINESS_REG_CERT_ORIGINAL: { attId: "", droptyple: "", label: "Bản gốc Giấy chứng nhận đăng ký hộ kinh doanh" },
    CPID: { attId: "2_CPID", droptyple: "CPID", label: "Bản sao giấy tờ pháp lý của cá nhân" },
    TRANSFER: { attId: "", droptyple: "", label: "Hợp đồng mua bán hoặc các giấy tờ chứng minh hoàn tất việc mua bán; hợp đồng tặng cho; bản sao văn bản xác nhận quyền thừa kế hợp pháp" },
    FAMILYMINUTES: { attId: "", droptyple: "", label: "Bản sao biên bản họp thành viên hộ gia đình" },
    FAMILYAUTH: { attId: "", droptyple: "", label: "Bản sao văn bản ủy quyền của thành viên hộ gia đình cho một thành viên làm chủ hộ kinh doanh" },
    OTHERS: { attId: "20_OTHERS", droptyple: "OTHERS", label: "Khác" },
  };
  // Cổng chỉ dựng lại danh sách loại ở sidebar sau một full postback. Giới hạn cả reload lẫn
  // vòng khai lại để lỗi phía cổng không biến thành vòng lặp vô hạn.
  const ATTACH_LIST_RELOAD_LIMIT = 2;
  const ATTACH_DECLARE_RECOVERY_LIMIT = 2;

  function getAttachAllState() {
    return new Promise((resolve) => {
      try {
        chrome.storage.local.get(ATTACH_KEY, (res) => {
          if (chrome.runtime.lastError) return resolve(null);
          resolve((res && res[ATTACH_KEY]) || null);
        });
      } catch (e) { resolve(null); }
    });
  }
  function setAttachAllState(st) {
    return new Promise((resolve) => {
      try { chrome.storage.local.set({ [ATTACH_KEY]: st }, () => resolve()); }
      catch (e) { resolve(); }
    });
  }
  function clearAttachAllState() {
    return new Promise((resolve) => {
      try { chrome.storage.local.remove(ATTACH_KEY, () => resolve()); }
      catch (e) { resolve(); }
    });
  }

  function foldName(name) {
    return foldBusinessPageText(String(name || "").replace(/\.[^.]+$/, ""));
  }

  function attachProgressText(st) {
    const label = {
      declare: "khai báo loại tài liệu",
      upload: "tải file lên",
      classify: "gán loại & lưu",
      done: "hoàn tất",
    }[st.phase] || "xử lý";
    return `Đang đính kèm hồ sơ — ${label}\n(đừng thao tác tới khi xong)`;
  }

  // Khởi tạo phiên (gọi từ content handler). plan[i] khớp files[i] theo attachment.fileIndex.
  async function startAttachAllBusiness(files, attachments) {
    const plan = files.map((f, i) => {
      const a = (attachments || []).find((x) => x && x.fileIndex === i) || {};
      const category = ATTACH_TYPE[a.category] ? a.category : "OTHERS"; // BUSREGFRM | CPID | OTHERS
      return { fileName: f.name, category, documentName: a.documentName || f.name };
    });
    // Các loại PHÂN BIỆT cần khai báo trong modal (giữ thứ tự xuất hiện) + số tài liệu mỗi loại.
    const declareTypes = [];
    const declareCounts = {};
    for (const p of plan) {
      if (!declareTypes.includes(p.category)) declareTypes.push(p.category);
      declareCounts[p.category] = (declareCounts[p.category] || 0) + 1;
    }
    const st = { files, plan, declareTypes, declareCounts, declared: [], phase: "declare", uploadTries: 0 };
    await setAttachAllState(st);
    return { ok: true, started: true };
  }

  // ---- helpers DOM ----
  function onUploadPage() {
    return !!document.getElementById("ctl00_C_FileUploadCtl");
  }
  // Danh sách LOẠI đã khai, hiện dưới "Văn bản đính kèm" trong container #ctl00_C_BLCtl_CtlAttList
  // (KHÁC #ctl00_C_BLCtl_CtlList = menu 8 trang). Bấm 1 item bất kỳ → điều hướng tới trang tải file.
  function attachTypeLinks() {
    const scoped = Array.from(document.querySelectorAll(
      '#ctl00_C_BLCtl_CtlAttList a[id*="LnkEdit"], #C_BLCtl_CtlAttList a[id*="LnkEdit"]'))
      .filter((a) => /__doPostBack/.test(a.getAttribute("href") || ""));
    if (scoped.length) return scoped;
    // ID container thay đổi giữa các giao diện; fallback theo đúng nhãn loại tài liệu để tránh bấm
    // nhầm các mục điều hướng HkdOnline khác cùng nằm trong sidebar.
    const labels = Object.values(ATTACH_TYPE).map((type) => foldBusinessPageText(type.label));
    return Array.from(document.querySelectorAll(".left-menu a"))
      .filter((link) => labels.includes(foldBusinessPageText(link.textContent)));
  }
  function clickAttachTypeLink(link) {
    if (H.isBusinessRunCancelled?.()) return false;
    const href = link.getAttribute("href") || "";
    const m = href.match(/__doPostBack\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]\s*\)/);
    if (m) return doAspPostback(m[1], m[2]);
    try { link.click(); return true; } catch (e) { return false; }
  }
  function uploadedRows() {
    return Array.from(document.querySelectorAll("#ctl00_C_CtlList tr"))
      .filter((tr) => tr.querySelector('select[id*="droptypleAttach"]'));
  }
  function declaredLabelsFold() {
    // CHỈ đọc bảng loại đã khai trong modal (#tblAtt). KHÔNG đọc a[id*="LnkEdit"] — đó là MENU 8 trang
    // bên trái (Hình thức đăng ký, Địa chỉ...), không phải loại tài liệu đã khai → tránh nhận nhầm.
    const out = [];
    document.querySelectorAll('#tblAtt tbody tr').forEach((el) => {
      const t = foldBusinessPageText(el.textContent);
      if (t) out.push(t);
    });
    return out;
  }
  // Đặt "Số tài liệu" trong modal khai loại (validateItemCount của cổng yêu cầu số ≥ 1).
  function setAttachItemCount(n) {
    const inp = document.getElementById("itemCount")?.querySelector("input");
    if (inp) setNativeValue(inp, String(n || 1), { typing: false, commit: true });
  }
  function hasDeclared(labelFold) {
    return declaredLabelsFold().some((x) => x.includes(labelFold));
  }
  function findAttachTypeOption(sel, type) {
    if (!sel || !type) return null;
    const labelFold = foldBusinessPageText(type.label);
    const opts = Array.from(sel.options || []);
    return (type.attId ? opts.find((o) => o.value === type.attId) : null)
      || opts.find((o) => foldBusinessPageText(o.textContent) === labelFold)
      || opts.find((o) => foldBusinessPageText(o.textContent).includes(labelFold))
      || null;
  }
  function attachmentModalHasCategory(sel, cat) {
    const type = ATTACH_TYPE[cat];
    return !!type && (hasDeclared(foldBusinessPageText(type.label)) || !!findAttachTypeOption(sel, type));
  }
  async function waitForAttachModalData(sel, st) {
    // Modal hiện trước, sau đó GetAttachment mới nạp option + bảng loại bằng AJAX. Chờ đủ dữ liệu
    // của mọi loại cần khai để không bỏ qua loại chỉ vì thao tác sớm hơn phản hồi AJAX.
    return waitFor(() => (st.declareTypes || []).every((cat) => attachmentModalHasCategory(sel, cat)), 7000, 250);
  }
  function syncDeclaredFromModal(st) {
    st.declared = (st.declareTypes || []).filter((cat) => {
      const type = ATTACH_TYPE[cat];
      return type && hasDeclared(foldBusinessPageText(type.label));
    });
  }
  function chooseOption(sel, value, labelFold) {
    const opts = Array.from(sel.options);
    const opt = (value ? opts.find((o) => o.value === value) : null)
      || (labelFold ? opts.find((o) => foldBusinessPageText(o.textContent) === labelFold) : null)
      || (labelFold ? opts.find((o) => foldBusinessPageText(o.textContent).includes(labelFold)) : null);
    if (!opt) return false;
    sel.value = opt.value;
    sel.dispatchEvent(new Event("input", { bubbles: true }));
    sel.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }
  async function ensureAttachModalOpen() {
    let sel = document.getElementById("attId");
    if (sel && H.isVisible(sel)) return sel;
    // Icon ⚙ mở modal qua handler jQuery của cổng. click() của content-script LÀ event DOM thật nên
    // handler jQuery vẫn nhận (CSP chỉ chặn INLINE script — không chặn dispatch event; KHÔNG inject nữa).
    const icon = document.getElementById("ctl00_C_BLCtl_ImgAttachmentSettings")
      || document.querySelector("img.settings, .right.settings, .settings");
    if (icon) { try { icon.click(); } catch (e) { /* ignore */ } }
    const ok = await waitFor(() => { const s = document.getElementById("attId"); return s && H.isVisible(s); }, 6000, 250);
    return ok ? document.getElementById("attId") : null; // null = không mở được (để caller xử lý)
  }
  function closeAttachModal({ refreshList = false } = {}) {
    if (refreshList) {
      // Handler close của chính cổng chỉ submit form khi cờ này = 1. Chủ động đặt lại cờ cả ở
      // nhánh recovery để sidebar CtlAttList được dựng từ dữ liệu đã lưu trên server.
      const refresh = document.getElementById("ctl00_C_BLCtl_RefreshAttachment");
      if (refresh) refresh.value = "1";
    }
    const dlg = document.getElementById("attachment")?.closest(".ui-dialog");
    const x = dlg?.querySelector(".ui-dialog-titlebar-close");
    if (x) { try { x.click(); return true; } catch (e) { /* fallthrough */ } }
    const closeButton = Array.from(dlg?.querySelectorAll(".ui-dialog-buttonpane button") || [])
      .find((button) => foldBusinessPageText(button.textContent).includes("dong"));
    if (closeButton) { try { closeButton.click(); return true; } catch (e) { /* fallthrough */ } }
    // Không phụ thuộc inject inline (CSP của HkdOnline chặn). Nếu cần refresh mà nút đóng không
    // tồn tại, submit form thật là fallback tương đương handler close của cổng.
    if (refreshList) {
      const form = document.forms?.namedItem?.("aspnetForm") || document.forms?.[0];
      if (form && typeof form.submit === "function") {
        try { form.submit(); return true; } catch (e) { /* fallthrough */ }
      }
    }
    return false;
  }

  // ---- các pha ----
  function isTypeDeclared(st, cat) {
    return (st.declared || []).includes(cat) || hasDeclared(foldBusinessPageText(ATTACH_TYPE[cat].label));
  }

  async function handleDeclarePhase(st) {
    if (H.isBusinessRunCancelled?.()) return;
    st.declared = st.declared || [];
    const missingFromState = st.declareTypes.filter((c) => !isTypeDeclared(st, c));
    if (missingFromState.length || st.forceDeclareRecovery) {
      const sel = await ensureAttachModalOpen();
      if (!sel) {
        st.declareTries = (st.declareTries || 0) + 1;
        await setAttachAllState(st);
        if (st.declareTries > 3) {
          return void failAttachAll("Không mở được cửa sổ khai báo loại tài liệu (icon ⚙ cạnh 'Văn bản đính kèm').");
        }
        return void setTimeout(stepAttachAll, 800);
      }
      const modalReady = await waitForAttachModalData(sel, st);
      if (!modalReady) {
        st.declareTries = (st.declareTries || 0) + 1;
        await setAttachAllState(st);
        closeAttachModal();
        if (st.declareTries > 3) {
          return void failAttachAll("Cổng không tải được danh sách loại tài liệu trong cửa sổ Văn bản đính kèm.");
        }
        return void setTimeout(stepAttachAll, 800);
      }

      // Trong recovery, state local có thể nói "đã khai" nhưng sidebar lại rỗng. Lấy bảng #tblAtt
      // vừa tải từ server làm nguồn sự thật; loại đã có thì không AddAtt lần nữa để tránh trùng.
      syncDeclaredFromModal(st);
      let savedAny = false;
      const missing = st.declareTypes.filter((cat) => !isTypeDeclared(st, cat));
      for (const cat of missing) {
        if (H.isBusinessRunCancelled?.()) return;
        const t = ATTACH_TYPE[cat];
        // AJAX có thể cập nhật bảng trong lúc vòng lặp đang chạy.
        if (hasDeclared(foldBusinessPageText(t.label))) {
          if (!st.declared.includes(cat)) st.declared.push(cat);
          continue;
        }
        const optionReady = await waitFor(() => !!findAttachTypeOption(sel, t), 3000, 200);
        if (!optionReady) continue;
        if (!chooseOption(sel, t.attId, foldBusinessPageText(t.label))) continue;
        // "Số tài liệu" phải là số ≥ 1 (validateItemCount của cổng) → set = số file thuộc loại này.
        setAttachItemCount((st.declareCounts && st.declareCounts[cat]) || 1);
        await waitFor(() => { const b = document.getElementById("AddAtt"); return b && !b.disabled; }, 5000, 200);
        const addBtn = document.getElementById("AddAtt");
        if (!addBtn) continue;
        if (addBtn.disabled) { try { addBtn.removeAttribute("disabled"); } catch (e) { /* ignore */ } }
        try { addBtn.click(); } catch (e) { /* ignore */ }
        // Khai báo lưu SERVER (AJAX SaveAttachment) → nhớ vào state (không đọc DOM #tblAtt sau khi
        // đóng modal / đổi trang được nữa).
        const ok = await waitFor(() => hasDeclared(foldBusinessPageText(t.label)), 6000, 300);
        if (ok) {
          savedAny = true;
          if (!st.declared.includes(cat)) st.declared.push(cat);
        }
        await sleep(300);
      }

      syncDeclaredFromModal(st);
      const unresolved = st.declareTypes.filter((cat) => !st.declared.includes(cat));
      if (unresolved.length) {
        st.phase = "declare";
        st.forceDeclareRecovery = true;
        st.declareTries = (st.declareTries || 0) + 1;
        if (st.declareTries > 3) {
          closeAttachModal();
          return void failAttachAll("Không khai đủ loại tài liệu đính kèm sau nhiều lần thử.");
        }
        await setAttachAllState(st);
        closeAttachModal({ refreshList: savedAny });
        H.setRunProgressText("Chưa khai đủ loại tài liệu, em đang thử lại…\n(đừng thao tác tới khi xong)");
        return void setTimeout(stepAttachAll, 1000);
      }

      st.phase = "upload";
      st.forceDeclareRecovery = false;
      st.declareTries = 0;
      await setAttachAllState(st);
      // Luôn yêu cầu full postback sau khi đối chiếu/lưu modal. Đây là bước khiến danh sách loại
      // xuất hiện ở sidebar; chỉ location.reload() không bảo đảm cổng nhận cờ RefreshAttachment.
      closeAttachModal({ refreshList: true });
      await sleep(600);
      // Sau khi khai, danh sách loại (CtlAttList) hiện dưới "Văn bản đính kèm" → chờ render để điều hướng.
      await waitFor(() => attachTypeLinks().length > 0 || onUploadPage(), 5000, 300);
    }

    // Đã khai loại xong → sang pha tải file. stepAttachAll tự điều hướng (bấm 1 item CtlAttList) sang
    // trang có ô Tải lên rồi upload/gán loại.
    st.phase = "upload";
    await setAttachAllState(st);
    return void setTimeout(stepAttachAll, 300);
  }

  async function handleUploadPhase(st) {
    if (H.isBusinessRunCancelled?.()) return;
    // Đã có dòng file (postback "Tải lên" xong) → chuyển sang gán loại.
    const existing = uploadedRows();
    if (existing.length) return void handleClassifyPhase(st, existing);

    const input = document.getElementById("ctl00_C_FileUploadCtl");
    const btn = document.getElementById("ctl00_C_BtnSaveNoTyple");
    if (!input || !btn) return; // trang chưa sẵn
    st.uploadTries = (st.uploadTries || 0) + 1;
    if (st.uploadTries > 3) return void failAttachAll("Tải file lên thất bại (thử lại quá số lần).");
    st.uploaded = true; // sau postback "Tải lên" → dòng file hiện ra → pha classify
    await setAttachAllState(st);
    const files = (st.files || []).map((f) => H.dataUrlToFile(f, ""));
    H.setFilesOnInput(input, files, { allowMultiple: true, assumeConsumed: true });
    await sleep(500);
    const reloaded = await clickSaveDetectReload(btn); // "Tải lên" → postback
    if (reloaded) return; // reload xong → dòng file hiện ra → pha classify
    return void stepAttachAll();
  }

  function categoryForFileName(st, folded) {
    if (!folded) return null;
    const p = (st.plan || []).find((x) => foldName(x.fileName) === folded);
    if (p) return p.category;
    const p2 = (st.plan || []).find((x) => folded.includes(foldName(x.fileName)) || foldName(x.fileName).includes(folded));
    return p2 ? p2.category : null;
  }

  async function handleClassifyPhase(st, rows) {
    if (H.isBusinessRunCancelled?.()) return;
    if (st.phase !== "classify") { st.phase = "classify"; await setAttachAllState(st); H.setRunProgressText(attachProgressText(st)); }
    const plan = st.plan || [];
    const sameCount = rows.length === plan.length; // dòng cùng thứ tự file đã tải
    rows.forEach((row, i) => {
      const sel = row.querySelector('select[id*="droptypleAttach"]');
      if (!sel) return;
      // Ưu tiên map theo THỨ TỰ (tên file cổng hiển thị có thể lệch khoảng trắng "đa ng ky..." → khớp tên
      // dễ sai). Chỉ dùng tên làm fallback khi số dòng ≠ số file.
      const nameEl = row.querySelector('span[id*="Label22"]') || row.querySelector("td:nth-child(2)");
      const byName = categoryForFileName(st, foldName(nameEl?.textContent || ""));
      const category = sameCount ? (plan[i] && plan[i].category) || byName : byName;
      const t = ATTACH_TYPE[category] || ATTACH_TYPE.OTHERS;
      console.log("[Attach] classify row", i, nameEl?.textContent?.trim(), "→", t.droptyple);
      chooseOption(sel, t.droptyple, foldBusinessPageText(t.label));
    });
    await sleep(400);
    const saveBtn = document.getElementById("ctl00_C_BtnSave");
    if (!saveBtn) return void finishAttachAll();
    // Nút "Lưu" mặc định disabled → bật lại sau khi đã gán loại (đổi droptyple làm form "dirty").
    if (saveBtn.disabled) { try { saveBtn.removeAttribute("disabled"); } catch (e) { /* ignore */ } }
    st.phase = "done";
    await setAttachAllState(st);
    const reloaded = await clickSaveDetectReload(saveBtn); // "Lưu" → postback
    if (reloaded) return; // done xử lý ở lần load kế
    return void finishAttachAll();
  }

  async function finishAttachAll() {
    if (H.isBusinessRunCancelled?.()) return;
    await clearAttachAllState();
    H.endFillAllUI("✓ Đã đính kèm xong hồ sơ. Vui lòng rà soát rồi bấm Nộp.");
  }
  async function failAttachAll(msg) {
    if (H.isBusinessRunCancelled?.()) return;
    await clearAttachAllState();
    H.endFillAllUI("⚠ " + msg);
  }

  async function stepAttachAll() {
    if (H.isBusinessRunCancelled?.()) return;
    const st = await getAttachAllState();
    if (!st) return;
    H.setRunProgressText(attachProgressText(st));
    ensureConfirmOverride();

    if (st.phase === "done") return void finishAttachAll();

    st.declared = st.declared || [];
    const declaredAll = st.declareTypes.every((c) => isTypeDeclared(st, c));
    console.log("[Attach] phase", st.phase, "| declared", st.declared, "declaredAll", declaredAll,
      "| hasGear", !!document.getElementById("ctl00_C_BLCtl_ImgAttachmentSettings"),
      "| onUploadPage", onUploadPage(), "| rows", uploadedRows().length);

    // B1 — KHAI LOẠI (modal ⚙): icon `.settings` là sidebar, có ở MỌI trang → khai được ở bất cứ đâu.
    // Chưa khai đủ + trang có icon ⚙ → mở modal khai luôn (KHÔNG cần ở trang có ô tải file).
    if ((st.forceDeclareRecovery || !declaredAll) && (document.getElementById("ctl00_C_BLCtl_ImgAttachmentSettings")
      || document.querySelector(".settings"))) {
      return void handleDeclarePhase(st);
    }

    // B2 — ĐIỀU HƯỚNG tới trang có ô tải file (#ctl00_C_FileUploadCtl). Sau khi khai loại, cổng hiện
    // danh sách loại trong #ctl00_C_BLCtl_CtlAttList → bấm 1 item bất kỳ sẽ ra trang tải file.
    if (!onUploadPage()) {
      const links = attachTypeLinks();
      if (links.length) {
        st.attListReloads = 0;
        st.declareRecoveryRounds = 0;
        st.forceDeclareRecovery = false;
        st.navTries = (st.navTries || 0) + 1;
        await setAttachAllState(st);
        if (st.navTries > 5) {
          return void failAttachAll("Không mở được trang tải file sau khi khai loại. Hãy bấm 1 mục trong danh sách 'Văn bản đính kèm'.");
        }
        H.setRunProgressText("Mở trang tải văn bản đính kèm…\n(đừng thao tác tới khi xong)");
        clickAttachTypeLink(links[0]); // postback → trang tải file (ATTACHMENTS.aspx)
        return;
      }
      // Chưa thấy danh sách loại: nếu đã khai (state) thì reload để cổng dựng CtlAttList (khai đã lưu server).
      if (declaredAll) {
        st.attListReloads = (st.attListReloads || 0) + 1;
        await setAttachAllState(st);
        if (st.attListReloads <= ATTACH_LIST_RELOAD_LIMIT) { location.reload(); return; }

        const recoveryRound = (st.declareRecoveryRounds || 0) + 1;
        if (recoveryRound > ATTACH_DECLARE_RECOVERY_LIMIT) {
          return void failAttachAll("Cổng chưa hiển thị danh sách loại tài liệu sau khi đã tự khai lại 2 lần.");
        }
        // State local không còn được tin ở đây: mở lại modal, lấy dữ liệu server, thêm loại thật sự
        // còn thiếu và submit lại cờ RefreshAttachment để cổng dựng CtlAttList.
        st.declareRecoveryRounds = recoveryRound;
        st.attListReloads = 0;
        st.navTries = 0;
        st.declared = [];
        st.phase = "declare";
        st.forceDeclareRecovery = true;
        st.declareTries = 0;
        await setAttachAllState(st);
        H.setRunProgressText(`Sidebar chưa hiển thị loại tài liệu. Em đang kiểm tra và khai lại (lần ${recoveryRound}/${ATTACH_DECLARE_RECOVERY_LIMIT})…\n(đừng thao tác tới khi xong)`);
        return void setTimeout(stepAttachAll, 700);
      }
      await setAttachAllState(st);
      H.setRunProgressText("Đang khai loại tài liệu…");
      return;
    }
    st.navTries = 0;
    st.attListReloads = 0;
    await setAttachAllState(st);

    const rows = uploadedRows();
    // Đã có dòng file (đã tải lên) → gán loại & lưu.
    if (rows.length && (st.phase === "classify" || st.uploaded)) {
      return void handleClassifyPhase(st, rows);
    }
    // Đã khai xong, đang ở trang có ô file → tải file lên.
    return void handleUploadPhase(st);
  }

  H.detectBusinessPageKey = detectBusinessPageKey;
  H.detectBusinessChangeStage = detectBusinessChangeStage;
  H.detectBusinessCreateStage = detectBusinessCreateStage;
  H.detectBusinessProcedureHint = detectBusinessProcedureHint;
  H.parseBusinessDeletePostback = parseBusinessDeletePostback;
  H.isBusinessRowMarkedDeleted = isBusinessRowMarkedDeleted;
  H.fillBusinessActDefault = fillBusinessActDefault;
  H.applyBusinessLocalDefaults = applyBusinessLocalDefaults;
  // Vai trò/địa chỉ người nộp hồ sơ — export để test được không cần cả state machine.
  H.applySubmitterOverride = applySubmitterOverride;
  H.submitterAddressFields = submitterAddressFields;
  H.buildSubmitterOverride = buildSubmitterOverride;
  H.matchSubmitterIdentityCandidate = matchSubmitterIdentityCandidate;
  H.forceSelfSubmitter = forceSelfSubmitter;
  H.matchAccountWithOwner = matchAccountWithOwner;
  H.tickSubmitterSelfRadio = tickSubmitterSelfRadio;
  H.getFillAllState = getFillAllState;
  H.clearFillAllState = clearFillAllState;
  H.navigateBusinessRegistrationPage = navigateBusinessRegistrationPage;
  H.setFillAllState = setFillAllState;
  H.stepFillAll = stepFillAll;
  H.startAttachAllBusiness = startAttachAllBusiness;
  H.stepAttachAll = stepAttachAll;
  H.getAttachAllState = getAttachAllState;
  H.clearAttachAllState = clearAttachAllState;
})();
 
