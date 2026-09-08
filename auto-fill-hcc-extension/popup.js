// Popup = client thuần: đăng nhập, chọn thủ tục + file, gửi BE xử lý, nhận fields →
// nhờ content.js điền DOM. Toàn bộ OCR/LLM/mapping nằm ở backend.

// ===== DOM refs =====
const loginScreen = document.getElementById("loginScreen");
const mainScreen = document.getElementById("mainScreen");
const loginUsername = document.getElementById("loginUsername");
const loginPassword = document.getElementById("loginPassword");
const rememberLogin = document.getElementById("rememberLogin");
const forgetLoginBtn = document.getElementById("forgetLoginBtn");
const loginBtn = document.getElementById("loginBtn");
const loginStatus = document.getElementById("loginStatus");
const userLabel = document.getElementById("userLabel");
const logoutBtn = document.getElementById("logoutBtn");
const newSessionBtn = document.getElementById("newSessionBtn");

const procedureSelect = document.getElementById("procedureSelect");
const procedureCombo = document.getElementById("procedureCombo");
const procedureTrigger = document.getElementById("procedureTrigger");
const procedureDropdown = document.getElementById("procedureDropdown");
const procedureSearchInput = document.getElementById("procedureSearchInput");
const procedureResults = document.getElementById("procedureResults");
const selectedProcedureLabel = document.getElementById("selectedProcedureLabel");
const uploadHintEl = document.getElementById("uploadHint");
const uploadHintToggle = document.getElementById("uploadHintToggle");
const uploadHintBox = document.getElementById("uploadHintBox");
const uploadHintClose = document.getElementById("uploadHintClose");
const businessPagePanel = document.getElementById("businessPagePanel");
const businessPageButtons = document.getElementById("businessPageButtons");
const fillAllBtn = document.getElementById("fillAllBtn");
const fileInput = document.getElementById("fileInput");
const fileList = document.getElementById("fileList");
const splitModeToggle = document.getElementById("splitModeToggle");
const splitModeRow = document.getElementById("splitModeRow");
const settingsBtn = document.getElementById("settingsBtn");
// Nút ⚙ (footer) mở trang cài đặt extension (settings.html) trong tab mới.
// Handler này từng bị NUỐT khi merge nhánh → nút thành mồ côi (bấm không phản ứng); thêm lại.
settingsBtn?.addEventListener("click", () => {
  chrome.tabs.create({ url: chrome.runtime.getURL("settings.html") });
});
const reportBtn = document.getElementById("reportBtn");
// Nút "Xem báo cáo" (footer) mở trang thống kê của đơn vị và ĐĂNG NHẬP SẴN bằng tài khoản đang
// dùng ở extension: token đi qua FRAGMENT (#hcc=...) — fragment không gửi lên server nên không lọt
// log, và trang báo cáo tự xoá khỏi thanh địa chỉ ngay khi nhận.
// CHỈ trao access token (TTL 1h), KHÔNG trao refresh: /auth/refresh xoay vòng sẽ thu hồi refresh
// token của extension và đá cán bộ ra đăng nhập lại giữa lúc đang làm hồ sơ.
// Dùng chrome.tabs.create thay vì target="_blank": popup thường chạy NHÚNG trong iframe trên trang
// cổng, mở tab bằng link trong iframe không chắc ăn.
reportBtn?.addEventListener("click", async (e) => {
  e.preventDefault();
  if (reportBtn.getAttribute("aria-busy") === "true") return;
  reportBtn.setAttribute("aria-busy", "true");
  try {
    // Gọi /auth/me trước để apiCall tự refresh nếu access token đã hết hạn → token trao đi luôn còn sống.
    await api.me();
    const tokens = await AuthStore.getTokens();
    const accessToken = tokens?.accessToken;
    if (!accessToken) {
      setStatus("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", "err");
      return;
    }
    const base = (typeof activeBackendBase === "function") ? activeBackendBase() : BACKEND_URL;
    const url = (window.REPORT_URL_BY_BACKEND || {})[base];
    if (!url) {
      setStatus("Chưa cấu hình trang báo cáo cho máy chủ đang dùng.", "err");
      return;
    }
    await chrome.tabs.create({ url: url + "#hcc=" + encodeURIComponent(accessToken) });
  } catch (err) {
    setStatus(err, "err");
  } finally {
    reportBtn.removeAttribute("aria-busy");
  }
});
const proxyFillBtn = document.getElementById("proxyFillBtn");
const ocrBtn = document.getElementById("ocrBtn");
const attachStepBtn = document.getElementById("attachStepBtn");
const dangKyBySelect = document.getElementById("dangKyBy");
const dangKyByLabel = document.querySelector('label[for="dangKyBy"]');
const requestModeSelect = document.getElementById("requestMode");
const requestModeLabel = document.querySelector('label[for="requestMode"]');
const statusEl = document.getElementById("status");
const statusDetailsToggle = document.getElementById("statusDetailsToggle");
const statusDetailsEl = document.getElementById("statusDetails");
const reviewCardEl = document.getElementById("reviewCard");
const supportCodeBtn = document.getElementById("supportCode");
const supportCodeValueEl = document.getElementById("supportCodeValue");
const uploadLabel = document.querySelector('label[for="fileInput"]');

// Danh sách thủ tục lấy từ BE: [{ key, label, roles:[{value,label}], useDangKyBy }]
// Các thủ tục Bắc Ninh có khối "Thông tin trong trường hợp được ủy quyền". Mỗi thủ tục chọn một
// loại đối tượng và một chủ thể nguồn khác nhau; dùng map để thủ tục mới không phải rải if/else.
const BAC_NINH_AUTHORIZED_PERSON_CONFIG = new Map([
  ["ho-tro-nguoi-cao-tuoi-bac-ninh", {
    subjectOption: "Người cao tuổi",
    sourceLabel: "người cao tuổi",
    missingFilesMessage: "Chưa có CCCD hoặc tờ khai để đọc thông tin người cao tuổi.",
  }],
  ["ho-tro-chi-phi-hoa-tang-bac-ninh", {
    subjectOption: "Cá nhân khác là Công dân Việt Nam",
    sourceLabel: "người được ủy quyền",
    missingFilesMessage: "Chưa có Biên bản/Văn bản ủy quyền để đọc thông tin người được ủy quyền.",
  }],
  ["dang-ky-bien-dong-dat-dai-bac-ninh", {
    subjectOption: "Cá nhân khác là Công dân Việt Nam",
    sourceLabel: "người được ủy quyền",
    missingFilesMessage: "Chưa có Giấy/Văn bản ủy quyền để đọc thông tin người được ủy quyền.",
  }],
]);
const BAC_NINH_THREE_STEP_PROCEDURES = new Set([
  "ho-tro-chi-phi-hoa-tang-bac-ninh",
  "dang-ky-bien-dong-dat-dai-bac-ninh",
]);
const currentBacNinhAuthorizedPersonConfig = () =>
  BAC_NINH_AUTHORIZED_PERSON_CONFIG.get(currentConfig()?.key) || null;
const isBacNinhAuthorizedPersonProcedure = () =>
  !!currentBacNinhAuthorizedPersonConfig();
const isBacNinhThreeStepProcedure = (config = currentConfig()) =>
  BAC_NINH_THREE_STEP_PROCEDURES.has(config?.key);

let PROCEDURES = [];
let lastProcessSession = null; // { procedure, sessionId }
let selectedProcedureKey = "";
// Thủ tục sở hữu file/kết quả của phiên đang làm. Khác selectedProcedureKey ở màn chọn chung
// HKD: lúc đó selection tạm rỗng nhưng vẫn phải nhớ file cũ thuộc thủ tục nào để không mang sang hồ sơ khác.
let workProcedureKey = "";
let selectedBusinessPageKey = "";
let procedureSearchQuery = "";
let procedureAutoDetected = false; // chỉ dùng để hiển thị nguồn lựa chọn; ô thủ tục luôn cho phép sửa tay
let manualProcedureOverride = false; // giữ lựa chọn tay trên URL hiện tại, reset khi reload/chuyển URL
let procedureDetectRun = 0;  // bỏ kết quả detect cũ nếu SPA đã phát sinh nhịp render mới hơn
let currentUser = null; // user đang đăng nhập; dùng cho default theo phường/tài khoản ở HKD.
// Mã của lượt FILL từ nút gộp HKD. Lưu cùng phiên theo tab để panel dựng lại sau mỗi
// WebForms postback vẫn hiện đúng mã; requestId của attachment plan không được ghi đè vào đây.
let businessFillSupportCode = "";
const DEFAULT_PROCEDURE_KEYS = [];
const SEARCH_PROCEDURE_LIMIT = 5;

// Chế độ đính kèm "tách hồ sơ" (split): CHỈ cho chứng thực. Mặc định TẮT = 1 hồ sơ nhiều file (merge).
const SPLIT_MODE_KEY = "autofill_attach_split_mode";
// Cài đặt "tách GIẤY TỜ trong 1 file" (bật/tắt ở settings.html) — KHÁC splitMode (tách hồ sơ).
const SPLIT_DOCUMENTS_SETTING_KEY = "autofill_attach_split_documents";
// Cài đặt "Người nộp = chủ hồ sơ (bỏ so khớp form)" (settings.html) — gửi BE qua options.submitterMode.
const SUBMITTER_OWNER_MODE_KEY = "autofill_submitter_owner_mode";
// Cài đặt "Không gộp giấy tờ" — CHỈ thủ tục chứng thực phân chia di sản (gửi BE qua options.splitDocuments).
const ESTATE_SPLIT_ATTACH_KEY = "autofill_estate_split_attachments";
const ESTATE_SPLIT_PROCEDURE_KEY = "chung-thuc-phan-chia-di-san";
// Bundle tách hồ sơ chứa dataUrl base64 có thể vượt trần 64 MiB của runtime.sendMessage.
// Popup ghi vào key cố định này; background nhận key, chuyển sang queue chính rồi xóa staging.
const SPLIT_ATTACH_QUEUE_STAGE_KEY = "autofill_split_attach_queue_stage";
const SPLIT_ATTACH_PROGRESS_KEY = "autofill_split_attach_progress";
const SPLIT_MODE_PROCEDURES = new Set(["chung-thuc-ban-sao", "chung-thuc-chu-ky"]);
const SPLIT_RELOADABLE_WALLET_CODES = new Set([
  "wallet-stale-modal",
  "wallet-modal-not-opened",
  "wallet-device-upload-not-opened",
]);
let attachSplitMode = false; // hiệu lực từ ô tick (đã khôi phục từ storage)
// Tách GIẤY TỜ bên trong một file (khác splitMode). Cài đặt toàn extension, đọc từ storage (settings.html).
let attachSplitDocuments = false;
// Cài đặt "Người nộp = chủ hồ sơ (bỏ so khớp form)" — gửi BE qua options.submitterMode="owner_as_submitter".
let submitterOwnerMode = false;
// Cài đặt "Không gộp giấy tờ" (phân chia di sản) — BẬT → gửi options.splitDocuments=true cho thủ tục đó.
let estateSplitAttachments = false;
let activeSplitRunId = null;
let splitProgressOriginTabId = null;

function isSplitEligibleProcedure() {
  return isAttachMode() && (
    SPLIT_MODE_PROCEDURES.has(currentConfig().key) ||
    isClientLocalSplitProcedure()
  );
}

function clientAttachmentCase(config = currentConfig()) {
  const value = config?.clientAttachmentCase;
  return value && typeof value === "object" ? value : null;
}

function isClientLocalSplitProcedure(config = currentConfig()) {
  return clientAttachmentCase(config)?.type === "single-row-local-split";
}

// ===== Embedded (floating panel) =====
const URL_PARAMS = new URLSearchParams(location.search);
const IS_EMBEDDED = URL_PARAMS.get("embedded") === "1";
const EMBEDDED_TAB_ID = URL_PARAMS.get("tabId") ? parseInt(URL_PARAMS.get("tabId"), 10) : null;
if (IS_EMBEDDED) document.body.classList.add("embedded");

async function getTargetTabId() {
  if (EMBEDDED_TAB_ID) return EMBEDDED_TAB_ID;
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab?.id;
}

async function sendToContent(payload) {
  const tabId = await getTargetTabId();
  if (!tabId) return { error: "Không xác định được tab form." };
  const isAttachmentAction = [
    "collectAttachmentContext",
    "attachFilesByPlan",
    "attachFilesViaWallet",
    "getDossierUrl",
  ].includes(payload?.action);

  const sendOnce = () => new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, payload, (res) => {
      const err = chrome.runtime.lastError;
      if (err) resolve({ __messageError: err.message || String(err) });
      else if (res === undefined) resolve({ __messageError: "NO_RESPONSE" });
      else resolve(res);
    });
  });
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  let res = await sendOnce();
  if (!res?.__messageError) return res;

  // Sau khi reload extension, tab đang mở có thể chưa có content.js mới.
  // Inject lại rồi gửi message thêm vài lần để chịu được WebForms postback/reload ngắn.
  for (const waitMs of [250, 800, 1600]) {
    if (waitMs) await sleep(waitMs);
    try {
      // Modal NNMT phải chạy cùng MAIN world với Angular/Zone.js. Inject riêng trước bridge
      // isolated để tab đang mở vẫn hoạt động ngay sau khi người dùng reload extension.
      await chrome.scripting.executeScript({
        target: isAttachmentAction ? { tabId } : { tabId, allFrames: true },
        world: "MAIN",
        files: ["content/attach-mae-main.js"],
      });
      await chrome.scripting.executeScript({
        target: isAttachmentAction ? { tabId } : { tabId, allFrames: true },
        // PHẢI khớp danh sách js của content_scripts trong manifest.json (trừ khối world: MAIN ở
        // trên). Thiếu một file thì tab vừa re-inject sẽ chạy thiếu tính năng một cách IM LẶNG —
        // vd thiếu enterprise-registration.js là mất nhận diện + tự tiến bước ở cổng ĐKKD qua mạng.
        files: ["api/config.js", "content/locations.js", "content/bbox-overlay.js", "content.js", "content/attach-mae.js", "content/fill-angular.js", "content/fill-liz.js", "content/fill-legacy.js", "content/fill-bacninh.js", "content/procedures/business-registration.js", "content/procedures/enterprise-registration.js", "content/agency-select.js", "content/review.js"],
      });
      res = await sendOnce();
      if (!res?.__messageError) return res;
    } catch (e) {
      console.warn("[Popup] Không inject được content script:", e?.message || e);
    }
  }

  return { error: "Không kết nối được trang. Hãy mở đúng trang form và tải lại trang." };
}

function sendToBackground(payload) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(payload, (res) => {
      const err = chrome.runtime.lastError;
      resolve(err ? { error: err.message || String(err) } : res);
    });
  });
}

function setStatusDetails(details = []) {
  if (!statusDetailsToggle || !statusDetailsEl) return;
  const safeDetails = [...new Set((Array.isArray(details) ? details : [])
    .map((item) => String(item || "").replace(/\s+/g, " ").trim().slice(0, 240))
    .filter(Boolean))].slice(0, 8);
  statusDetailsEl.textContent = "";
  statusDetailsEl.hidden = true;
  statusDetailsToggle.hidden = safeDetails.length === 0;
  statusDetailsToggle.textContent = "Xem chi tiết";
  statusDetailsToggle.setAttribute("aria-expanded", "false");
  if (!safeDetails.length) return;
  const list = document.createElement("ul");
  for (const detail of safeDetails) {
    const item = document.createElement("li");
    item.textContent = detail;
    list.appendChild(item);
  }
  statusDetailsEl.appendChild(list);
}

if (statusDetailsToggle && statusDetailsEl) {
  statusDetailsToggle.addEventListener("click", () => {
    const expanded = statusDetailsToggle.getAttribute("aria-expanded") === "true";
    statusDetailsToggle.setAttribute("aria-expanded", String(!expanded));
    statusDetailsToggle.textContent = expanded ? "Xem chi tiết" : "Ẩn chi tiết";
    statusDetailsEl.hidden = expanded;
    postPanelHeight();
  });
}

// friendlyError() + errorSupportCode() nằm ở api/errors.js (nạp trước popup.js) — 1 nguồn chân lý.
// setStatus nhận input là Error (ưu tiên map theo MÃ lỗi BE) hoặc string; lỗi luôn được rút gọn an toàn.
function setStatus(input, type, details = []) {
  setStatusDetails(details);
  if (type === "err") {
    const code = (typeof errorSupportCode === "function") ? errorSupportCode(input) : null;
    if (code) showSupportCode(code);
    statusEl.textContent = friendlyError(input);
  } else {
    statusEl.textContent = String(input == null ? "" : input);
  }
  statusEl.className = "status" + (type ? " " + type : "");
  statusEl.setAttribute("role", type === "err" ? "alert" : "status");
}

function splitProgressPresentation(progress) {
  const total = Math.max(0, Number(progress?.total) || 0);
  const completed = Math.max(0, Math.min(total, Number(progress?.completed) || 0));
  const succeeded = Math.max(0, Math.min(completed, Number(progress?.succeeded) || 0));
  const failed = Math.max(0, Math.min(completed, Number(progress?.failed) || 0));
  const activeOrdinal = Math.max(0, Number(progress?.activeOrdinal) || 0);

  if (!total) return null;
  if (progress?.status === "paused") {
    const ordinal = Number(progress?.paused?.ordinal) || activeOrdinal || completed + 1;
    return {
      type: "warn",
      message: `Đã đính kèm ${succeeded}/${total} hồ sơ.\nHồ sơ ${ordinal} chưa nhận được file; hàng đợi đang dừng tại tab đó.`,
    };
  }
  if (progress?.status === "completed") {
    if (failed > 0) {
      return {
        type: "warn",
        message: `Đã xử lý ${completed}/${total} hồ sơ: ${succeeded} thành công, ${failed} chưa thành công.\nVui lòng kiểm tra các tab được báo lỗi.`,
      };
    }
    return { type: "ok", message: `Đã đính kèm thành công ${succeeded}/${total} hồ sơ.` };
  }
  if (failed > 0) {
    return {
      type: "warn",
      message: `Đã xử lý ${completed}/${total} hồ sơ: ${succeeded} thành công, ${failed} chưa thành công.` +
        (activeOrdinal ? `\nĐang xử lý hồ sơ ${activeOrdinal}/${total}…` : ""),
    };
  }
  return {
    type: "info",
    message: `Đã đính kèm ${succeeded}/${total} hồ sơ.` +
      (activeOrdinal ? `\nĐang xử lý hồ sơ ${activeOrdinal}/${total}…` : ""),
  };
}

function renderSplitProgress(progress) {
  if (!progress || (Number(progress.expiresAt) || 0) <= Date.now()) return false;
  if (activeSplitRunId && progress.runId !== activeSplitRunId) return false;
  if (splitProgressOriginTabId && Number(progress.originTabId) !== Number(splitProgressOriginTabId)) return false;
  const presentation = splitProgressPresentation(progress);
  if (!presentation) return false;
  activeSplitRunId = progress.runId || activeSplitRunId;
  setStatus(presentation.message, presentation.type);
  return true;
}

async function restoreSplitProgressStatus() {
  try {
    splitProgressOriginTabId = splitProgressOriginTabId || await getTargetTabId();
    const stored = await chrome.storage.local.get(SPLIT_ATTACH_PROGRESS_KEY);
    const progress = stored?.[SPLIT_ATTACH_PROGRESS_KEY];
    if (!progress || Number(progress.originTabId) !== Number(splitProgressOriginTabId)) return false;
    return renderSplitProgress(progress);
  } catch (_) {
    return false;
  }
}

chrome.storage?.onChanged?.addListener?.((changes, areaName) => {
  if (areaName !== "local") return;
  const progress = changes?.[SPLIT_ATTACH_PROGRESS_KEY]?.newValue;
  if (!progress) return;
  renderSplitProgress(progress);
});

async function showPageToast(message, kind = "success") {
  const text = String(message || "").replace(/\s+/g, " ").trim();
  if (!text) return false;
  try {
    const res = await sendToContent({ action: "showPageToast", message: text, kind });
    if (res?.error) console.warn("[AutoFill] Không hiện được toast:", res.error);
    return !!res?.shown;
  } catch (error) {
    console.warn("[AutoFill] Không hiện được toast:", error);
    return false;
  }
}

// ===== Mã hỗ trợ: hiện request_id của lượt vừa chạy để cán bộ copy khi báo lỗi =====
let _supportCodeResetTimer = null;
function showSupportCode(id) {
  if (!supportCodeBtn || !supportCodeValueEl) return;
  if (!id) { hideSupportCode(); return; }
  supportCodeValueEl.textContent = id;
  supportCodeBtn.dataset.code = id;
  supportCodeBtn.classList.remove("copied");
  supportCodeBtn.hidden = false;
}
function hideSupportCode() {
  if (!supportCodeBtn) return;
  supportCodeBtn.hidden = true;
  supportCodeBtn.classList.remove("copied");
  delete supportCodeBtn.dataset.code;
  if (_supportCodeResetTimer) { clearTimeout(_supportCodeResetTimer); _supportCodeResetTimer = null; }
}
if (supportCodeBtn) {
  supportCodeBtn.addEventListener("click", async () => {
    const code = supportCodeBtn.dataset.code || "";
    if (!code) return;
    let ok = false;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(code);
        ok = true;
      }
    } catch { ok = false; }
    if (!ok) {
      // Fallback khi clipboard API bị chặn/không có focus (iframe sau khi đính kèm): textarea + execCommand
      // trong user-gesture. focus() trước khi select để execCommand không bị bỏ qua.
      try {
        const ta = document.createElement("textarea");
        ta.value = code; ta.style.position = "fixed"; ta.style.top = "0"; ta.style.opacity = "0";
        document.body.appendChild(ta); ta.focus(); ta.select();
        ok = document.execCommand("copy");
        ta.remove();
      } catch { ok = false; }
    }
    supportCodeBtn.classList.add("copied");
    // Báo ĐÚNG kết quả: fail thì nhắc bôi đen mã để copy tay (value đã cho user-select).
    supportCodeValueEl.textContent = ok ? "Đã sao chép ✓" : "Chưa copy được — bôi đen mã để copy tay";
    if (_supportCodeResetTimer) clearTimeout(_supportCodeResetTimer);
    _supportCodeResetTimer = setTimeout(() => {
      supportCodeBtn.classList.remove("copied");
      supportCodeValueEl.textContent = code;
    }, ok ? 1500 : 3000);
  });
}

// ===== Auth UI =====
const CAN_REMEMBER_LOGIN = chrome.extension?.inIncognitoContext !== true;
let rememberedLoginLoaded = false;
let loginPrefillRun = 0;

function renderRememberedLoginState(hasSaved) {
  rememberedLoginLoaded = Boolean(hasSaved);
  rememberLogin.checked = Boolean(hasSaved) && CAN_REMEMBER_LOGIN;
  rememberLogin.disabled = !CAN_REMEMBER_LOGIN;
  forgetLoginBtn.hidden = !hasSaved || !CAN_REMEMBER_LOGIN;
  if (!CAN_REMEMBER_LOGIN) {
    rememberLogin.title = "Không thể ghi nhớ đăng nhập trong cửa sổ ẩn danh.";
  }
}

function showLogin() {
  currentUser = null;
  // Mọi lối ĐĂNG XUẤT/hết phiên đều qua đây (nút Đăng xuất, 401, token hỏng) -> quên tỉnh/xã đã chọn tay
  // để lần đăng nhập sau seed lại TỪ TÀI KHOẢN. Khôi phục phiên còn hạn đi thẳng showMain() nên KHÔNG
  // reset ở lần mở lại bình thường (lựa chọn tay vẫn giữ khi chưa đăng xuất).
  void forgetStoredLocation();
  loginScreen.hidden = false;
  mainScreen.hidden = true;
  // Footer nằm NGOÀI mainScreen nên luôn hiển thị → phải tự ẩn nút báo cáo khi chưa đăng nhập.
  if (reportBtn) reportBtn.hidden = true;
  prefillLogin();
}

async function prefillLogin() {
  const run = ++loginPrefillRun;
  try {
    await RememberedLoginStore.clearLegacyPrefill();
    if (!CAN_REMEMBER_LOGIN) {
      if (run === loginPrefillRun) renderRememberedLoginState(false);
      return;
    }
    const saved = await RememberedLoginStore.get();
    if (run !== loginPrefillRun) return;
    renderRememberedLoginState(Boolean(saved));
    if (!saved) return;
    if (!loginUsername.value) loginUsername.value = saved.username;
    if (!loginPassword.value) loginPassword.value = saved.password;
  } catch (_) {
    if (run === loginPrefillRun) renderRememberedLoginState(false);
  }
}

async function clearRememberedLogin({ clearFields = false, announce = false } = {}) {
  ++loginPrefillRun; // vô hiệu hóa lượt đọc IndexedDB cũ nếu người dùng bấm xóa ngay lúc popup mở
  try {
    await RememberedLoginStore.clear();
    renderRememberedLoginState(false);
    if (clearFields) {
      loginUsername.value = "";
      loginPassword.value = "";
      loginUsername.focus();
    }
    if (announce) {
      loginStatus.textContent = "Đã xóa thông tin đăng nhập được ghi nhớ.";
      loginStatus.className = "status ok";
    }
  } catch (e) {
    console.warn("[Popup] Không xóa được thông tin đăng nhập đã nhớ:", e);
    if (announce) {
      loginStatus.textContent = "Chưa xóa được thông tin đã nhớ. Vui lòng thử lại.";
      loginStatus.className = "status err";
    }
  }
}

function showMain(user) {
  currentUser = user || null;
  loginScreen.hidden = true;
  mainScreen.hidden = false;
  if (reportBtn) reportBtn.hidden = false;
  userLabel.textContent = user?.name || user?.username || "";
  // /auth/me về sau khi khối địa chỉ đã dựng -> áp lại để lấy tỉnh/xã gắn trong tài khoản.
  void applyStoredLocation();
}

async function bootstrap() {
  const tokens = await AuthStore.getTokens();
  if (!tokens?.accessToken) {
    showLogin();
    return;
  }
  try {
    const me = await api.me();
    showMain(me);
    await loadProcedures();
    await restoreSplitMode();
    await restoreSplitDocumentsSetting();
    await restoreSession();
    await restoreConsent();   // khôi phục trạng thái đồng ý của phiên qua reload trang
    await autoDetectProcedure();
    restoreBusinessFillSupportCode();
    await restoreSplitProgressStatus();
    // Chặng 2 của luồng doanh nghiệp: wizard vừa đưa tới khối dữ liệu thì quét + điền luôn.
    await resumeEnterpriseFillIfPending();
  } catch (e) {
    await AuthStore.clearTokens();
    showLogin();
  }
}

loginBtn.addEventListener("click", async () => {
  const username = loginUsername.value.trim();
  const password = loginPassword.value;
  if (!username || !password) {
    loginStatus.textContent = "Nhập tên đăng nhập và mật khẩu.";
    loginStatus.className = "status err";
    return;
  }
  loginBtn.disabled = true;
  loginStatus.textContent = "Đang đăng nhập...";
  loginStatus.className = "status info";
  try {
    const data = await api.login(username, password);
    await AuthStore.saveTokens(data);
    if (CAN_REMEMBER_LOGIN && rememberLogin.checked) {
      try {
        await RememberedLoginStore.save(username, password);
        renderRememberedLoginState(true);
      } catch (e) {
        console.warn("[Popup] Đăng nhập thành công nhưng không lưu được thông tin ghi nhớ:", e);
        renderRememberedLoginState(false);
      }
    } else {
      await clearRememberedLogin();
    }
    loginPassword.value = "";
    loginStatus.textContent = "";
    showMain(data.user);
    await loadProcedures();
    await restoreSplitMode();
    await restoreSplitDocumentsSetting();
    await restoreSession();
    await restoreConsent();   // khôi phục trạng thái đồng ý của phiên qua reload trang
    await autoDetectProcedure();
    restoreBusinessFillSupportCode();
    await restoreSplitProgressStatus();
    // Chặng 2 của luồng doanh nghiệp: wizard vừa đưa tới khối dữ liệu thì quét + điền luôn.
    await resumeEnterpriseFillIfPending();
  } catch (e) {
    console.warn("[Popup] Đăng nhập lỗi:", e);
    const invalidRememberedLogin = rememberedLoginLoaded
      && (e?.status === 401 || e?.data?.error === "INVALID_CREDENTIALS");
    if (invalidRememberedLogin) {
      await clearRememberedLogin();
      loginPassword.value = "";
    }
    loginStatus.textContent = invalidRememberedLogin
      ? `${friendlyError(e)} Thông tin đã nhớ đã được xóa.`
      : friendlyError(e);   // INVALID_CREDENTIALS → "Sai tên đăng nhập hoặc mật khẩu."
    loginStatus.className = "status err";
  } finally {
    loginBtn.disabled = false;
  }
});

loginPassword.addEventListener("keydown", (e) => {
  if (e.key === "Enter") loginBtn.click();
});

rememberLogin.addEventListener("change", async () => {
  if (!rememberLogin.checked) await clearRememberedLogin();
});

forgetLoginBtn.addEventListener("click", async () => {
  await clearRememberedLogin({ clearFields: true, announce: true });
});

logoutBtn.addEventListener("click", async () => {
  await AuthStore.clearTokens();
  currentUser = null;
  await clearSession();
  files.length = 0;
  lastProcessSession = null;
  renderFiles();
  refreshAttachStepUI();
  hideSupportCode();
  setStatus("", "");
  showLogin();
});

// Tạo phiên mới: xoá file + kết quả + sessionId của TAB hiện tại (giữ đăng nhập, giữ thủ tục đã chọn).
if (newSessionBtn) {
  newSessionBtn.addEventListener("click", async () => {
    await clearSession();
    files.length = 0;
    lastProcessSession = null;
    // Đưa TẤT CẢ về mặc định: bỏ chọn thủ tục + mở khóa, xoá ô tìm, xoá card rà soát.
    selectedProcedureKey = "";
    selectedBusinessPageKey = "";
    procedureAutoDetected = false;
    manualProcedureOverride = false;
    closeProcedureDropdown();   // render lại trigger về "Chưa có thủ tục nào được chọn!"
    clearReviewCard();
    hideSupportCode();
    closePhoneUpload();
    await clearConsent();   // phiên mới → phải đồng ý lại (mỗi phiên 1 lần)
    showView("main");
    setStatus("", "");
    renderFiles();
    applyFormUI();
    refreshAttachStepUI();
    // Nhận diện lại theo TRANG HIỆN TẠI (giống lúc mới mở): trang form → tự chọn+khóa; không → để trống.
    await autoDetectProcedure();
    setStatus("Đã tạo phiên mới — sẵn sàng cho hồ sơ tiếp theo.", "ok");
  });
}

// ===== Thủ tục + cấu hình form =====
function normalizeProcedureSearch(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase()
    .trim();
}

const XUAN_HUONG_BUSINESS_ACT_TEXT =
  "(Hộ kinh doanh phải thực hiện đúng các quy định của pháp luật về đất đai, xây dựng, phòng cháy chữa cháy, bảo vệ môi trường, các quy định khác của pháp luật hiện hành và các điều kiện kinh doanh đối với ngành nghề có điều kiện)";

function isXuanHuongBusinessUser(user) {
  const haystack = [user?.xa, user?.name, user?.username].filter(Boolean).join(" ");
  return normalizeProcedureSearch(haystack).includes("xuan huong");
}

/** Tài khoản gắn tỉnh/thành Đà Nẵng (/auth/me trả `tinh`). */
function isDaNangBusinessUser(user) {
  return normalizeProcedureSearch(user?.tinh).includes("da nang");
}

// ===== Nghiệp vụ riêng phường Hải Châu — thành phố Đà Nẵng (chỉ áp cho tài khoản của địa bàn này) =====
// 1. Ô "Lý do giải thể" (trang Chấm dứt hoạt động) LUÔN là câu cố định, bất kể Thông báo chấm dứt
//    trong hồ sơ ghi lý do gì — kể cả khi backend không đọc được lý do nào.
const HAI_CHAU_DISSOLUTION_REASON = "Chấm dứt hoạt động kinh doanh";
// 2. Ô "Địa chỉ nhận kết quả" (trang Người nộp hồ sơ) LUÔN là Trung tâm Phục vụ Hành chính công của
//    phường, cho MỌI thủ tục hộ kinh doanh. Cổng để trống ô này và cán bộ phải gõ tay mỗi hồ sơ.
const HAI_CHAU_POSTAL_ADDRESS =
  "Trung tâm Phục vụ Hành chính công phường Hải Châu - 15 Lê Hồng Phong, thành phố Đà Nẵng (Quầy số 5 - khu A)";

/** Tài khoản phường Hải Châu — thành phố Đà Nẵng (/auth/me trả `xa` + `tinh`). */
function isHaiChauDaNangUser(user) {
  // Phải khớp CẢ phường lẫn tỉnh/thành: danh mục hành chính còn một "Xã Hải Châu" ở Thanh Hóa.
  return isDaNangBusinessUser(user) && normalizeProcedureSearch(user?.xa).includes("hai chau");
}

// ===== Nghiệp vụ riêng tỉnh Lâm Đồng (áp cho MỌI tài khoản của tỉnh) =====
// Ô mô tả của TỪNG DÒNG ngành nghề (textarea trắng ngay dưới tên ngành chính thức, trang "Ngành nghề
// kinh doanh") phải để TRỐNG. Địa bàn này chỉ nhận đúng tên ngành theo Hệ thống ngành kinh tế Việt Nam
// do cổng tự điền theo mã; phần chi tiết đọc thêm từ giấy đề nghị (vd "Bán buôn thực phẩm (bán buôn
// rau, quả)") không được ghi vào đây. Ô "Ngành, nghề chưa khớp mã" ở cuối trang KHÔNG thuộc quy tắc này.
function isLamDongBusinessUser(user) {
  return normalizeProcedureSearch(user?.tinh).includes("lam dong");
}

function buildBusinessDefaults(user) {
  const defaults = {};
  if (isXuanHuongBusinessUser(user)) defaults.businessActText = XUAN_HUONG_BUSINESS_ACT_TEXT;
  // Đà Nẵng: vai trò người nộp LUÔN là "Người có thẩm quyền ký Giấy đề nghị đăng ký Hộ kinh doanh",
  // kể cả khi nhân thân tài khoản khác chủ hộ (nghiệp vụ địa phương yêu cầu). Chỉ áp cho tài khoản
  // Đà Nẵng — tỉnh khác vẫn tự chốt vai trò theo đối chiếu tài khoản với chủ hộ như cũ.
  if (isDaNangBusinessUser(user)) defaults.forceSelfSubmitter = true;
  if (isLamDongBusinessUser(user)) defaults.skipBusinessLineDescription = true;
  if (isHaiChauDaNangUser(user)) {
    defaults.dissolutionReason = HAI_CHAU_DISSOLUTION_REASON;
    defaults.postalServiceAddress = HAI_CHAU_POSTAL_ADDRESS;
  }
  return Object.keys(defaults).length ? defaults : null;
}

function selectedProcedureConfig() {
  // CHƯA chọn → null (KHÔNG mặc định về thủ tục đầu tiên). Panel hiển thị "chưa chọn thủ tục".
  const key = selectedProcedureKey || procedureSelect.value;
  return PROCEDURES.find((p) => p.key === key) || null;
}

function currentBusinessPages() {
  const pages = selectedProcedureConfig()?.pages;
  return Array.isArray(pages) ? pages : [];
}

function selectedBusinessPage() {
  const pages = currentBusinessPages();
  if (!pages.length) return null;
  return pages.find((p) => p.key === selectedBusinessPageKey) || pages[0];
}

async function navigateSelectedBusinessPage(page) {
  if (!page) return;
  setStatus(`Đang mở trang "${page.label}"...`, "info");
  const res = await sendToContent({
    action: "navigateBusinessPage",
    page: page.key,
    label: page.label,
  });
  if (res?.error) {
    setStatus(res.error, "err");
    return;
  }
  const suffix = res?.already ? "đang ở trang này" : "đã gửi lệnh mở trang";
  setStatus(`Trang "${page.label}": ${suffix}.`, "ok");
}

function renderBusinessPages() {
  const pages = currentBusinessPages();
  if (!businessPagePanel || !businessPageButtons) return;
  businessPagePanel.hidden = !pages.length;
  businessPageButtons.innerHTML = "";
  if (!pages.length) {
    selectedBusinessPageKey = "";
    postPanelHeight();
    return;
  }

  if (!pages.some((p) => p.key === selectedBusinessPageKey)) {
    selectedBusinessPageKey = pages[0].key;
  }

  for (const page of pages) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "business-page-btn" + (page.key === selectedBusinessPageKey ? " active" : "");
    btn.setAttribute("role", "tab");
    btn.setAttribute("aria-selected", page.key === selectedBusinessPageKey ? "true" : "false");
    btn.textContent = page.label;
    btn.addEventListener("click", async () => {
      selectedBusinessPageKey = page.key;
      renderBusinessPages();
      try {
        await navigateSelectedBusinessPage(page);
      } catch (e) {
        console.warn("[Popup] Mở trang HKD lỗi:", e);
        setStatus("Không mở được trang. Vui lòng thử lại.", "err");
      }
    });
    businessPageButtons.appendChild(btn);
  }
  postPanelHeight();
}

// Mã TTHC dùng CHUNG một nguồn với ô "Đi đến thủ tục": danh mục ke_khai_links.json của backend,
// khớp theo `key` (cùng hệ key với registry). Không nhân bản mã sang chỗ thứ hai để khỏi lệch nhau.
function procedureCode(key) {
  if (!key) return "";
  const link = keKhaiLinks().find((item) => item.key === key);
  return (link && link.code) || "";
}

function getVisibleProcedures(query) {
  const q = normalizeProcedureSearch(query);
  if (!q) return [];  // CHƯA gõ tìm → KHÔNG gợi ý thủ tục nào (không mặc định chung-thuc-ban-sao)
  // Mã gõ tay hay rơi rụng/thừa dấu chấm ("2000815", "2.000.815") nên so theo phần SỐ. Cần ≥4
  // chữ số mới coi là đang tra mã, nếu không chữ "2" lẫn trong tên sẽ khớp mọi mã. Mã cũng KHÔNG
  // trộn vào haystack tên vì đúng lý do đó.
  const digits = q.replace(/\D+/g, "");
  const codeNeedle = digits.length >= 4 ? digits : "";
  return PROCEDURES.filter((p) => {
    const haystack = normalizeProcedureSearch(`${p.label || ""} ${p.key || ""}`);
    if (haystack.includes(q)) return true;
    return !!codeNeedle && procedureCode(p.key).replace(/\D+/g, "").includes(codeNeedle);
  }).slice(0, SEARCH_PROCEDURE_LIMIT);
}

function renderProcedureResults(query = procedureSearchQuery) {
  if (!procedureResults) return;
  const selected = selectedProcedureConfig();
  const prefix = procedureAutoDetected
    ? "Tự nhận diện: "
    : (manualProcedureOverride ? "Đã chọn thủ công: " : "Đang chọn: ");
  if (selectedProcedureLabel) {
    selectedProcedureLabel.textContent = "";
    if (selected) {
      selectedProcedureLabel.append(prefix);
      const strong = document.createElement("strong");
      strong.textContent = selected.label;
      selectedProcedureLabel.appendChild(strong);
    } else {
      // Chưa chọn thủ tục nào → hiện thông báo rõ trên UI.
      const none = document.createElement("span");
      none.className = "procedure-none";
      none.textContent = "Chưa có thủ tục nào được chọn!";
      selectedProcedureLabel.appendChild(none);
    }
  }

  // Tooltip tên ĐẦY ĐỦ (nhãn trong trigger chỉ 2 dòng nên có thể bị cắt "...").
  if (procedureTrigger) {
    procedureTrigger.title = selected ? prefix + selected.label : "";
  }

  // Tự nhận diện chỉ là trạng thái hiển thị; trigger luôn bấm được để cán bộ sửa khi detect sai.
  if (procedureTrigger) {
    procedureTrigger.disabled = false;
    procedureTrigger.classList.remove("locked");
    procedureTrigger.setAttribute("aria-disabled", "false");
  }
  procedureResults.innerHTML = "";
  const visible = getVisibleProcedures(query);
  if (!visible.length) {
    // CHỈ báo "Không tìm thấy" khi ĐÃ gõ tìm; chưa gõ → để TRỐNG (không gợi ý gì).
    if (normalizeProcedureSearch(query)) {
      const empty = document.createElement("div");
      empty.className = "procedure-empty";
      empty.textContent = "Không tìm thấy thủ tục.";
      procedureResults.appendChild(empty);
    }
    postPanelHeight();
    return;
  }

  for (const p of visible) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "procedure-option" + (p.key === selected?.key ? " active" : "");
    btn.setAttribute("role", "option");
    btn.setAttribute("aria-selected", p.key === selected?.key ? "true" : "false");
    const code = procedureCode(p.key);
    btn.title = code ? `${code} — ${p.label}` : p.label;

    const label = document.createElement("span");
    label.className = "procedure-option-label";
    label.textContent = p.label;
    btn.appendChild(label);

    btn.addEventListener("click", () => { void selectProcedure(p.key); });
    procedureResults.appendChild(btn);
  }
  postPanelHeight();
}

function shouldResetProcedureWork(nextKey) {
  const previousKey = workProcedureKey || selectedProcedureKey;
  return !!(previousKey && nextKey && previousKey !== nextKey);
}

function shouldPreserveProcedureWorkOnAutoDetect(previousKey, nextKey, source, fileCount, confirmedNavigation = false) {
  // Auto-detect ở bước kế tiếp chỉ là tín hiệu của trang, không phải xác nhận cán bộ đã mở hồ sơ mới.
  // Một số cổng bỏ mã thủ tục hoặc render text của thủ tục liên quan ở bước đính kèm; nếu tin tín hiệu
  // đó và reset ngay, toàn bộ file vừa dùng để điền sẽ biến mất. Chỉ thao tác chọn tay/phiên mới được
  // quyền đổi chủ sở hữu khi hồ sơ hiện tại vẫn còn file.
  return source === "auto"
    && !confirmedNavigation
    && !!previousKey
    && !!nextKey
    && previousKey !== nextKey
    && Number(fileCount || 0) > 0;
}

function resetProcedureWorkState() {
  // Vô hiệu mọi saveSession cũ đang đọc file lớn; bản lưu đó không được ghi file thủ tục trước trở lại.
  sessionWriteRevision++;
  files.length = 0;
  lastProcessSession = null;
  businessFillSupportCode = "";
  if (fileInput) fileInput.value = "";
  clearReviewCard();
  hideSupportCode();
  closePhoneUpload();
  currentConsentContext = null;
  pendingConsentTrigger = null;
  void sendToContent({ action: "clearPanelAutoRestore" });
  showView("main");
  setStatus("", "");
}

async function selectProcedure(key, { source = "manual", confirmedNavigation = false } = {}) {
  const next = PROCEDURES.find((p) => p.key === key) || PROCEDURES[0];
  if (!next) return;
  if (source === "manual") {
    manualProcedureOverride = true;
    procedureAutoDetected = false;
  }
  const previousKey = workProcedureKey || selectedProcedureKey;
  if (shouldPreserveProcedureWorkOnAutoDetect(
    previousKey,
    next.key,
    source,
    files.length,
    confirmedNavigation,
  )) {
    console.warn("[Popup] Bỏ qua auto-detect khác thủ tục để giữ hồ sơ đang làm", {
      previousKey,
      detectedKey: next.key,
      fileCount: files.length,
    });
    return false;
  }
  const selectionChanged = selectedProcedureKey !== next.key;
  const workOwnerChanged = workProcedureKey !== next.key;
  if (shouldResetProcedureWork(next.key)) resetProcedureWorkState();
  selectedProcedureKey = next.key;
  workProcedureKey = next.key;
  selectedBusinessPageKey = Array.isArray(next.pages) && next.pages.length ? next.pages[0].key : "";
  procedureSelect.value = next.key;
  closeProcedureDropdown();  // đã chọn → đóng combobox, trigger hiện "Đang chọn: X"
  syncKeKhaiSelection(next.key);
  // KHÔNG tự đặt cờ chạy wizard ở đây: chọn/nhận diện thủ tục là việc của panel, còn việc bấm
  // radio + Tiếp theo trên cổng phải do CÁN BỘ ra lệnh (nút "Quét và nhập dữ liệu"). Chỉ dọn cờ
  // khi chuyển sang thủ tục KHÁC, để lần mở dở trước không lỡ tay điều khiển hồ sơ đang mở.
  if (!next.enterprisePortal) await clearEnterpriseAutostart();
  applyFormUI();
  // Detect lại cùng thủ tục (reload/chuyển bước/DOM đổi) không ghi lại cả khối base64 lớn vào storage.
  if (selectionChanged || workOwnerChanged) await saveSession();
  return true;
}

async function clearEnterpriseAutostart() {
  try { await chrome.storage.local.remove(ENTERPRISE_ARM_KEY); } catch (_) { /* ignore */ }
}

/**
 * "Lên đạn" cho content/procedures/enterprise-registration.js chạy wizard 3 bước (loại đăng ký →
 * loại hình → Bắt đầu) vào khối dữ liệu hồ sơ trên cổng ĐKKD qua mạng.
 *
 * CHỈ gọi từ hành động CÓ CHỦ Ý của cán bộ (nút "Quét và nhập dữ liệu"), không gọi lúc nhận diện
 * thủ tục — trợ lý không được tự bấm radio trên trang cán bộ tự mở.
 *
 * Dữ liệu wizard lấy từ REGISTRY (enterpriseEntityLabel) nên chạy được cả khi cán bộ vào thẳng cổng
 * thay vì đi qua ô "Đi đến thủ tục".
 */
async function armEnterpriseAutostart(procedure) {
  if (!procedure?.enterprisePortal) return false;
  try {
    const stored = await chrome.storage.local.get(ENTERPRISE_ARM_KEY);
    const existing = stored?.[ENTERPRISE_ARM_KEY];
    // Cờ của ĐÚNG thủ tục này đang chạy dở: giữ nguyên để không reset bộ đếm chống lặp (tries) và
    // không ghi đè entityValue chi tiết hơn mà ô "Đi đến thủ tục" đã đặt.
    if (existing?.procedureKey === procedure.key) return true;
    await chrome.storage.local.set({
      [ENTERPRISE_ARM_KEY]: {
        registrationType: "NEW",
        registrationLabel: "Thành lập mới",
        entityLabel: procedure.enterpriseEntityLabel || "",
        entityValue: procedure.enterpriseEntityValue || "",
        procedureKey: procedure.key,
        procedureLabel: procedure.label,
        at: Date.now(),
      },
    });
    return true;
  } catch (error) {
    console.warn("[Popup] Không đặt được cờ mở hồ sơ doanh nghiệp:", error);
    return false;
  }
}

/**
 * Xử lý phần "vào hồ sơ" của cổng ĐKKD qua mạng cho nút "Quét và nhập dữ liệu".
 * Trả TRUE nghĩa là lượt bấm đã được tiêu thụ (đang mở hồ sơ) → người gọi phải dừng, chưa quét.
 * Trả FALSE khi không liên quan (cổng khác) hoặc đã ở trong khối dữ liệu → quét như bình thường.
 */
async function startEnterpriseDossierIfNeeded() {
  const cfg = currentConfig();
  if (!cfg.enterprisePortal) return false;
  // Hỏi THẲNG engine của cổng doanh nghiệp. Trước đây đọc enterpriseProcedureHint trong tín hiệu
  // detectProcedure của content.js — đường vòng đó phụ thuộc việc namespace đã gắn kịp hay chưa,
  // hint vắng một nhịp là cả bước "mở hồ sơ" bị bỏ qua im lặng và cán bộ bấm mãi không vào được.
  const res = await sendToContent({ action: "getEnterpriseStage" });
  if (!res?.ok) return false;         // không phải cổng doanh nghiệp / engine chưa nạp
  if (res.inDossier) return false;    // đã ở khối dữ liệu → quét như bình thường
  console.log("[Popup] Cổng doanh nghiệp đang ở bước:", res.stage);
  if (!(await armEnterpriseAutostart(cfg))) {
    setStatus("Không mở được hồ sơ đăng ký. Vui lòng thử lại.", "err");
    return true;
  }
  // Nối liền hai chặng: đánh dấu "vào hồ sơ xong thì quét luôn" để lượt bootstrap của panel trên
  // trang khối dữ liệu tự chạy tiếp, cán bộ chỉ bấm MỘT lần.
  await setEnterprisePendingFill(cfg.key);
  return true;
}

// Chặng 2 của luồng doanh nghiệp: sau khi wizard đưa tới khối dữ liệu, panel được dựng lại (trang
// tải lại) và tự bấm tiếp hộ. Cờ sống theo TAB và có hạn để lần mở dở dang không tự chạy về sau.
const ENTERPRISE_PENDING_FILL_KEY = "autofill_enterprise_pending_fill_" + (EMBEDDED_TAB_ID ?? "popup");
const ENTERPRISE_PENDING_TTL_MS = 15 * 60 * 1000;

async function setEnterprisePendingFill(procedureKey) {
  try {
    await chrome.storage.local.set({
      [ENTERPRISE_PENDING_FILL_KEY]: { procedureKey, at: Date.now() },
    });
  } catch (error) {
    console.warn("[Popup] Không ghi được cờ quét tiếp sau khi vào hồ sơ:", error);
  }
}

async function clearEnterprisePendingFill() {
  try { await chrome.storage.local.remove(ENTERPRISE_PENDING_FILL_KEY); } catch (_) { /* ignore */ }
}

/** Bootstrap gọi: đã vào tới khối dữ liệu và đang có cờ chờ → chạy tiếp chặng quét + điền. */
async function resumeEnterpriseFillIfPending() {
  let pending = null;
  try {
    const stored = await chrome.storage.local.get(ENTERPRISE_PENDING_FILL_KEY);
    pending = stored?.[ENTERPRISE_PENDING_FILL_KEY] || null;
  } catch (_) { return; }
  if (!pending) return;
  if (Date.now() - Number(pending.at || 0) > ENTERPRISE_PENDING_TTL_MS) return void clearEnterprisePendingFill();

  const cfg = currentConfig();
  if (!cfg.enterprisePortal || cfg.key !== pending.procedureKey) return;
  const stage = await sendToContent({ action: "getEnterpriseStage" });
  if (!stage?.ok) return;
  if (!stage.inDossier) return;              // wizard còn chạy dở → giữ cờ, chờ lượt tải trang sau
  await clearEnterprisePendingFill();
  // Không còn giấy tờ (phiên bị xoá giữa chừng) thì thôi, để cán bộ tự bấm.
  if (!files.length) return;
  if (fillAllBtn && !fillAllBtn.hidden && !fillAllBtn.disabled) fillAllBtn.click();
}

function hasStrongProcedureIdentity(key, signals) {
  const procedure = PROCEDURES.find((item) => item.key === key);
  if (!procedure?.detect || !signals) return false;
  const url = String(signals.url || "").toLowerCase();
  const detect = procedure.detect;
  if (detectUrlScopeOk(detect, url)) {
    const urlMatch = (detect.urlIncludes || [])
      .some((part) => part && url.includes(String(part).toLowerCase()));
    if (urlMatch) return true;
  }
  // Heading đúng toàn bộ tên thủ tục là bằng chứng điều hướng mạnh. Không dùng bodyText vì trang
  // đính kèm thường liệt kê tên nhiều thủ tục/tài liệu liên quan và dễ gây đổi nhầm pipeline.
  const expected = normDetect(detect.heading || procedure.label);
  return expected.length >= 6
    && (signals.visibleHeadings || []).some((heading) => normDetect(heading) === expected);
}

function commitProcedureSearch() {
  procedureSearchQuery = procedureSearchInput?.value.trim() || "";
  renderProcedureResults(procedureSearchQuery);
}

// ---- Combobox: mở/đóng dropdown thủ tục (nổi, không đẩy layout) ----
function isProcedureDropdownOpen() {
  return !!procedureDropdown && !procedureDropdown.hidden;
}
function openProcedureDropdown() {
  if (!procedureDropdown) return;
  procedureDropdown.hidden = false;
  procedureTrigger?.setAttribute("aria-expanded", "true");
  procedureSearchQuery = "";
  if (procedureSearchInput) procedureSearchInput.value = "";
  renderProcedureResults("");          // mở ra để trống, chờ gõ
  procedureSearchInput?.focus();
  postPanelHeight();
}
function closeProcedureDropdown() {
  if (!procedureDropdown) return;
  procedureDropdown.hidden = true;
  procedureTrigger?.setAttribute("aria-expanded", "false");
  procedureSearchQuery = "";
  if (procedureSearchInput) procedureSearchInput.value = "";
  renderProcedureResults("");           // cập nhật lại nhãn trigger
  postPanelHeight();
}
function toggleProcedureDropdown() {
  if (isProcedureDropdownOpen()) closeProcedureDropdown();
  else openProcedureDropdown();
}

// ---- Tự nhận diện thủ tục theo trang đang mở ----
function normDetect(value) {
  return normalizeProcedureSearch(value).replace(/\s+/g, " ").trim();
}

// Cổng gate: rule có `urlScope` chỉ được xét khi URL đang mở thuộc cổng đó (OR nhiều mảnh).
// Khác `urlIncludes` (tự khớp một mình) — `urlScope` KHÔNG tự nhận diện, chỉ giới hạn phạm vi để
// các cụm text/heading bên dưới được so khớp. Dùng khi URL chỉ có ObjectId theo phường (không định
// danh thủ tục) nhưng vẫn muốn chắc chắn đúng cổng trước khi tin vào text (vd Lâm Đồng lamdong.gov.vn).
function detectUrlScopeOk(detect, url) {
  const scope = detect.urlScope || [];
  if (!scope.length) return true;
  return scope.some((u) => u && url.includes(String(u).toLowerCase()));
}

// Khớp tín hiệu trang (URL + heading) với rule `detect` của thủ tục từ backend.
function detectProcedureKeyFromSignals(signals) {
  if (!signals) return "";
  const detectables = PROCEDURES.filter((p) => p && p.detect);
  const url = String(signals.url || "").toLowerCase();
  const body = normDetect(signals.bodyText || "");

  // HkdOnline dùng chung domain/URL. DOM procedure hint phải thắng rule URL chung:
  // - choice: màn chọn có nhiều option, không được đoán theo text option;
  // - change/create: loại hồ sơ đã được xác nhận bởi active step hoặc khối thông tin hồ sơ.
  const selected = selectedProcedureConfig();

  // Cổng ĐKKD qua mạng dùng CHUNG Registration.aspx/DW_DOCUMENTEdit.aspx cho MỌI loại hình doanh
  // nghiệp: URL, heading và body ("ĐĂNG KÝ DOANH NGHIỆP", "Thành lập mới...") không phân biệt được
  // CTCP với TNHH/DNTN, và các nhánh đoán theo text bên dưới từng trả nhầm thành thủ tục HỘ kinh doanh.
  if (String(signals.enterpriseProcedureHint || "")) {
    const entityLabel = normDetect(signals.enterpriseEntityLabel || "");
    if (entityLabel) {
      // Hồ sơ đã tạo: cổng in rõ "Loại hình doanh nghiệp" → chốt đúng thủ tục theo loại hình đó.
      // Loại hình chưa có thủ tục tương ứng (vd TNHH) thì để TRỐNG, không nhận bừa sang CTCP.
      const matched = PROCEDURES.find((item) => item.enterpriseEntityLabel
        && normDetect(item.enterpriseEntityLabel) === entityLabel);
      return matched ? matched.key : "";
    }
    // Chưa chốt loại hình (wizard, trang chủ cổng, màn đăng nhập): giữ thủ tục doanh nghiệp đang
    // chọn nếu có; không thì rơi xuống rule urlIncludes để nhận theo domain — đúng như cổng HKD.
    if (isEnterprisePortalProcedure(selected)) return selected.key;
  }

  if (url.includes("hokinhdoanh.dkkd.gov.vn")) {
    const hint = String(signals.businessProcedureHint || "");
    const changeProcedure = PROCEDURES.find((item) => item.businessWorkflow === "change");
    const hintedWorkflowProcedure = PROCEDURES.find((item) => item.businessWorkflow === hint);
    const createProcedure = PROCEDURES.find((item) => item.key === "dang-ky-kinh-doanh");
    if (hintedWorkflowProcedure && hint !== "change") return hintedWorkflowProcedure.key;
    if (hint === "change-exact" && changeProcedure) return changeProcedure.key;
    // Màn tìm kiếm được dùng chung cho CHN/REI. Chỉ giữ workflow đã được người dùng chọn;
    // nếu chưa có thì để dropdown mở, không tự đoán thành thủ tục thay đổi nội dung.
    if (hint === "shared-business-search") {
      return selected?.businessWorkflow ? selected.key : "";
    }
    // Các bước tìm kiếm/xác nhận dùng chung cho mọi nhánh CHN. Nếu popup đã chọn một nhánh
    // cụ thể (vd chấm dứt), phải giữ nhánh đó thay vì đổi về thủ tục thay đổi nội dung chung.
    if (hint === "change" && selected?.businessWorkflow) return selected.key;
    if (hint === "change" && changeProcedure) return changeProcedure.key;
    if (hint === "create" && createProcedure) return createProcedure.key;
    // Registration.aspx chỉ liệt kê các loại đăng ký. Text của các option không chứng minh
    // người dùng đã chọn loại nào, kể cả khi popup vừa khôi phục một thủ tục từ session cũ.
    if (hint === "choice") return "";
    // Trang phụ/đính kèm không còn marker wizard: giữ loại HKD đã chọn qua phiên popup.
    if (selected && (selected.key === createProcedure?.key || selected.businessWorkflow)) {
      return selected.key;
    }
  }

  // 0) Một số thủ tục dùng chung URL cổng chứng thực, nên cần ưu tiên cụm tên thủ tục
  //    rất đặc trưng trước rule URL chung.
  if (body) {
    let bestPriority = "";
    let bestPriorityScore = 0;
    for (const p of detectables) {
      if (!p.detect.textPriority) continue;
      if (!detectUrlScopeOk(p.detect, url)) continue;
      const phrases = (p.detect.textIncludes || []).map(normDetect).filter(Boolean);
      if (!phrases.length) continue;
      if (!phrases.every((ph) => body.includes(ph))) continue;
      const score = phrases.reduce((s, ph) => s + ph.length, 0);
      if (score > bestPriorityScore) {
        bestPriority = p.key;
        bestPriorityScore = score;
      }
    }
    if (bestPriority) return bestPriority;
  }

  // 1) URL khớp — đặc trưng từng thủ tục (mạnh nhất). Vd liên thông mã 2.000986, moj nop-ho-so/<id>.
  //    urlScope (nếu có) GIỚI HẠN host: mã QG như maThuTucHanhChinh=1.013949 dùng chung nhiều cổng iGate
  //    (Bắc Ninh vs Lâm Đồng) → chỉ khớp khi đúng cổng đã khai urlScope.
  for (const p of detectables) {
    const inc = p.detect.urlIncludes || [];
    if (!detectUrlScopeOk(p.detect, url)) continue;
    if (inc.some((u) => u && url.includes(String(u).toLowerCase()))) return p.key;
  }

  // 2) Heading khớp tên thủ tục (eForm hộ tịch/chứng thực moj). Chọn label DÀI NHẤT khớp
  //    để tránh nhầm (vd "đăng ký khai sinh" vs "đăng ký lại khai sinh").
  const headings = (signals.headings || []).map(normDetect).filter(Boolean);
  let best = "";
  let bestLen = 0;
  for (const p of detectables) {
    if (p.detect.headingDisabled) continue;
    if (!detectUrlScopeOk(p.detect, url)) continue;
    const want = normDetect(p.detect.heading || p.label);
    if (want.length < 6) continue;
    const hit = headings.some((h) => h === want || h.startsWith(want) || want.startsWith(h));
    if (hit && want.length > bestLen) {
      best = p.key;
      bestLen = want.length;
    }
  }
  if (best) return best;

  // 3) Văn bản trang chứa ĐỦ các cụm đặc trưng (cổng SPA dùng chung URL, vd laichau). Chọn match
  //    có TỔNG độ dài cụm dài nhất (đặc trưng nhất) để tránh nhầm giữa các thủ tục cùng cổng.
  if (body) {
    let bestScore = 0;
    for (const p of detectables) {
      if (!detectUrlScopeOk(p.detect, url)) continue;
      const phrases = (p.detect.textIncludes || []).map(normDetect).filter(Boolean);
      if (!phrases.length) continue;
      if (!phrases.every((ph) => body.includes(ph))) continue;
      const score = phrases.reduce((s, ph) => s + ph.length, 0);
      if (score > bestScore) {
        best = p.key;
        bestScore = score;
      }
    }
  }
  return best;
}

// Cổng ĐKKD qua mạng (dangkyquamang.dkkd.gov.vn) chỉ phục vụ nhóm thủ tục thành lập/thay đổi
// DOANH NGHIỆP. Thủ tục hộ kinh doanh (cổng hokinhdoanh) không bao giờ đúng ở đây.
function isEnterprisePortalProcedure(procedure) {
  return !!procedure?.enterprisePortal;
}

function setProcedureDetected(detected) {
  procedureAutoDetected = detected;
  renderProcedureResults();
}

// Đang ở cổng ĐKKD qua mạng mà lựa chọn hiện tại là thủ tục của cổng KHÁC (điển hình: hộ kinh
// doanh còn lại từ phiên trước) → phải xóa, nếu không panel hiển thị sai tên thủ tục cho cán bộ.
function shouldClearProcedureOnEnterprisePortal(signals) {
  if (!String(signals?.enterpriseProcedureHint || "")) return false;
  if (!selectedProcedureKey) return false;
  return !isEnterprisePortalProcedure(selectedProcedureConfig());
}

// Màn "Chọn loại đăng ký trực tuyến" là điểm bắt đầu dùng chung của mọi thủ tục HKD.
// Không được mang lựa chọn đã lưu từ hồ sơ trước sang đây; chỉ xóa loại thủ tục, giữ file
// để người dùng vẫn có thể chọn đúng thủ tục rồi tiếp tục mà không phải tải lại tài liệu.
async function enterBusinessProcedureChoiceMode() {
  const hadSelectedProcedure = !!selectedProcedureKey;
  selectedProcedureKey = "";
  selectedBusinessPageKey = "";
  procedureSelect.value = "";
  procedureAutoDetected = false;
  manualProcedureOverride = false;
  closeProcedureDropdown();
  applyFormUI();
  if (hadSelectedProcedure) await saveSession();
}

// Trang hiện tại KHÔNG khớp thủ tục nào (detectProcedureKeyFromSignals=null) mà lựa chọn đang có là
// do TỰ nhận diện → xóa, để panel không kẹt "Đang chọn: A" khi đã sang trang/thủ tục B chưa hỗ trợ
// detect. CHỈ xóa nhãn lựa chọn; workProcedureKey (sở hữu file/kết quả) KHÔNG đụng → không mất tài liệu.
async function clearAutoDetectedSelection() {
  const hadSelected = !!selectedProcedureKey;
  selectedProcedureKey = "";
  if (procedureSelect) procedureSelect.value = "";
  closeProcedureDropdown();
  applyFormUI();
  setProcedureDetected(false);   // procedureAutoDetected=false + render → "Chưa có thủ tục nào được chọn!"
  if (hadSelected) await saveSession();
}

// Gọi content script lấy tín hiệu trang → nếu nhận diện được thì chọn và ghi nhận nguồn tự động.
async function autoDetectProcedure({ clearChoiceSelection = true } = {}) {
  // Người dùng đã sửa detect sai: giữ lựa chọn tay đến khi reload/chuyển URL.
  if (manualProcedureOverride) {
    setProcedureDetected(false);
    return !!selectedProcedureKey;
  }
  try {
    // Cổng WebForms (ĐKKD qua mạng, HkdOnline) tải lại trang ở mỗi bước: lượt hỏi đầu tiên có thể
    // rơi đúng lúc content script chưa gắn xong listener → res không có `signals`. Trước đây bỏ cuộc
    // ngay và panel KẸT ở "Đang chọn:" (thay vì "Tự nhận diện:") cho tới khi cán bộ chọn tay, vì
    // không còn nhịp nào gọi lại. Thử lại vài nhịp ngắn rồi mới chịu thua.
    let res = null;
    for (const waitMs of [0, 400, 1200]) {
      if (waitMs) await new Promise((resolve) => setTimeout(resolve, waitMs));
      res = await sendToContent({ action: "detectProcedure" });
      if (res?.signals) break;
    }
    if (!res?.signals) {
      console.warn("[Popup] Không lấy được tín hiệu trang để nhận diện thủ tục:", res?.error || res);
    }
    if (res?.signals?.businessProcedureHint === "choice") {
      // Khi vừa mở popup/chuyển URL: bỏ lựa chọn cũ. Khi người dùng đã chọn tay rồi bấm
      // xử lý: giữ lựa chọn đó để engine biết phải bấm loại đăng ký nào trên cổng.
      if (clearChoiceSelection) await enterBusinessProcedureChoiceMode();
      else setProcedureDetected(false);
      return false;
    }
    const key = detectProcedureKeyFromSignals(res?.signals);
    if (key && PROCEDURES.some((p) => p.key === key)) {
      const applied = await selectProcedure(key, {
        source: "auto",
        confirmedNavigation: hasStrongProcedureIdentity(key, res.signals),
      });
      setProcedureDetected(applied !== false);
      return applied !== false;
    }
    // Không nhận diện được mà đang ở cổng doanh nghiệp: phải XÓA lựa chọn cũ (điển hình là thủ tục
    // hộ kinh doanh còn lại từ phiên trước), nếu không panel hiển thị sai tên thủ tục cho cán bộ.
    if (shouldClearProcedureOnEnterprisePortal(res?.signals)) {
      await enterBusinessProcedureChoiceMode();
      return false;
    }
    // Cổng THƯỜNG: không nhận ra thủ tục nào + đang có lựa chọn TỰ nhận diện (không phải chọn tay) →
    // xóa để panel không kẹt "Đang chọn: A" khi đã sang trang/thủ tục khác. CHỈ xóa khi có res.signals
    // (trang thật) — tránh xóa oan lúc content script chưa gắn kịp (đã retry [0,400,1200] ở trên).
    if (res?.signals && selectedProcedureKey && !manualProcedureOverride) {
      await clearAutoDetectedSelection();
      return false;
    }
  } catch (e) {
    /* không nhận diện được → quay về chọn tay */
  }
  setProcedureDetected(false);
  return false;
}

// Panel nổi (embedded) nhận tín hiệu trang dvc đổi URL (SPA, không F5) → nhận diện lại thủ tục.
// CHỈ đổi khi thủ tục KHÁC hiện tại để tránh reset file/UI khi trang đổi URL nhưng cùng thủ tục.
async function reDetectProcedureOnNav(run = 0) {
  if (manualProcedureOverride) return;
  try {
    const res = await sendToContent({ action: "detectProcedure" });
    if (run && run !== procedureDetectRun) return;
    if (res?.signals?.businessProcedureHint === "choice") {
      await enterBusinessProcedureChoiceMode();
      return;
    }
    const key = detectProcedureKeyFromSignals(res?.signals);
    if (key && PROCEDURES.some((p) => p.key === key)) {
      const applied = key === selectedProcedureKey
        ? true
        : await selectProcedure(key, {
          source: "auto",
          confirmedNavigation: hasStrongProcedureIdentity(key, res.signals),
        });
      setProcedureDetected(applied !== false);
      return;
    }
    // Không nhận diện được mà đang ở cổng doanh nghiệp: xóa lựa chọn cũ của cổng khác (xem
    // autoDetectProcedure ở trên).
    if (shouldClearProcedureOnEnterprisePortal(res?.signals)) {
      await enterBusinessProcedureChoiceMode();
      return;
    }
    // Cổng THƯỜNG: sang trang/thủ tục KHÁC không detect được + lựa chọn hiện tại là do TỰ nhận diện →
    // xóa để không kẹt "Đang chọn: A". Chỉ khi có res.signals (trang thật) và không phải chọn tay.
    if (res?.signals && selectedProcedureKey && !manualProcedureOverride) {
      await clearAutoDetectedSelection();
    }
  } catch (e) {
    /* không nhận diện được → giữ nguyên trạng thái hiện tại */
  }
}

if (IS_EMBEDDED) {
  window.addEventListener("message", (e) => {
    if (e.source !== window.parent) return;
    if (e.data?.type !== "autofill-hcc-page-changed"
      && e.data?.type !== "autofill-hcc-url-changed") return;
    const isUrlNavigation = e.data.type === "autofill-hcc-url-changed" || e.data.reason === "url";
    if (isUrlNavigation) {
      manualProcedureOverride = false;
      setProcedureDetected(false);
    } else if (manualProcedureOverride) {
      return;
    }
    const run = ++procedureDetectRun;
    // Nhiều nhịp render SPA có thể báo liên tiếp. Chỉ lượt mới nhất được quyền đổi thủ tục.
    void reDetectProcedureOnNav(run);
  });
}

async function loadProcedures() {
  try {
    const res = await api.procedures();
    PROCEDURES = res.procedures || [];
  } catch (e) {
    if (e.unauthorized) {
      await AuthStore.clearTokens();
      showLogin();
      return;
    }
    console.warn("[Popup] Tải danh sách thủ tục lỗi:", e);
    setStatus("Không tải được danh sách thủ tục. Kiểm tra mạng rồi thử lại.", "err");
    return;
  }
  procedureSelect.innerHTML = "";
  for (const p of PROCEDURES) {
    const opt = document.createElement("option");
    opt.value = p.key;
    opt.textContent = p.label;
    procedureSelect.appendChild(opt);
  }
  // Không mặc định chọn thủ tục nào khi mở: key không hợp lệ/rỗng → để TRỐNG, chờ user chọn
  // hoặc trang tự nhận diện (autoDetectProcedure).
  if (!PROCEDURES.some((p) => p.key === selectedProcedureKey)) {
    selectedProcedureKey = "";
  }
  const selectedCfg = PROCEDURES.find((p) => p.key === selectedProcedureKey);
  selectedBusinessPageKey = Array.isArray(selectedCfg?.pages) && selectedCfg.pages.length ? selectedCfg.pages[0].key : "";
  procedureSelect.value = selectedProcedureKey;
  procedureSearchQuery = "";
  if (procedureSearchInput) procedureSearchInput.value = "";
  renderProcedureResults();
  applyFormUI();
}

function currentConfig() {
  return selectedProcedureConfig() || { roles: [] };
}

// Khi thủ tục dùng requestMode và chọn "Bản thân" → chỉ cần 1 CCCD (role requester).
function isSelfMode() {
  const cfg = currentConfig();
  return !!cfg.useRequestMode && requestModeSelect.value === "self";
}

function effectiveRoles() {
  const cfg = currentConfig();
  if (isSelfMode()) return cfg.roles.filter((r) => r.value === "requester");
  return cfg.roles || [];
}

function isAttachMode() {
  const cfg = currentConfig();
  return cfg.mode === "attach";
}

function hasAttachmentStep() {
  const cfg = currentConfig();
  return !!cfg.hasAttachmentStep;
}

// Thủ tục agent: BE tự suy luận loại giấy tờ → không cần chọn role.
function isAgentMode() {
  const cfg = currentConfig();
  return cfg.mode === "agent" || (!isAttachMode() && !(cfg.roles && cfg.roles.length));
}

// ===== File picker =====
const files = []; // { file, role, dataUrl?, restored? }

// ===== Lưu/khôi phục phiên (thủ tục + file) qua các lần chuyển trang =====
// Khi WebForms reload sang trang mới, panel được content.js tự bật lại; phần này khôi phục
// thủ tục + file đã chọn để user chỉ cần chọn file 1 lần rồi điền cho mọi trang.
// Session lưu THEO TAB (autofill_session_<tabId>) → mỗi tab 1 phiên; tab mới không bị
// kéo thủ tục/file của tab cũ sang. Bản popup đứng riêng (không nhúng) dùng key "popup".
const SESSION_KEY = "autofill_session_" + (EMBEDDED_TAB_ID ?? "popup");
const UNKNOWN_WORK_PROCEDURE_KEY = "__legacy_unknown__";
let sessionWriteRevision = 0;
let sessionWriteQueue = Promise.resolve();

function enqueueSessionWrite(operation) {
  sessionWriteQueue = sessionWriteQueue.catch(() => { }).then(operation);
  return sessionWriteQueue;
}

async function saveSession() {
  const revision = sessionWriteRevision;
  try {
    await ensureSelectedFilesLoaded();
    if (revision !== sessionWriteRevision) return;
    const snapshot = {
      procedureKey: selectedProcedureKey,
      workProcedureKey,
      businessFillSupportCode,
      files: files.map((it) => ({
        name: it.file.name,
        type: it.file.type || "image/jpeg",
        dataUrl: it.dataUrl,
        role: it.role || "doc",
      })),
    };
    await enqueueSessionWrite(async () => {
      if (revision !== sessionWriteRevision) return;
      await chrome.storage.local.set({ [SESSION_KEY]: snapshot });
    });
    return true;
  } catch (e) {
    console.warn("[Popup] Không lưu được phiên thủ tục/file", {
      sessionKey: SESSION_KEY,
      procedureKey: workProcedureKey || selectedProcedureKey,
      fileCount: files.length,
      error: e,
    });
    return false;
  }
}

async function clearSession() {
  businessFillSupportCode = "";
  workProcedureKey = "";
  sessionWriteRevision++;
  void sendToContent({ action: "clearPanelAutoRestore" });
  try {
    await enqueueSessionWrite(() => chrome.storage.local.remove(SESSION_KEY));
  } catch (e) { /* ignore */ }
}

async function restoreSession() {
  let saved = null;
  try {
    const res = await chrome.storage.local.get(SESSION_KEY);
    saved = res?.[SESSION_KEY];
  } catch (e) {
    console.warn("[Popup] Không đọc được phiên thủ tục/file", { sessionKey: SESSION_KEY, error: e });
  }
  if (!saved) return;
  businessFillSupportCode = String(saved.businessFillSupportCode || "").trim();
  const savedFiles = Array.isArray(saved.files) ? saved.files : [];
  workProcedureKey = String(saved.workProcedureKey || saved.procedureKey || "").trim();
  // Session từ bản extension cũ có thể đã giữ file sau khi selection bị đưa về rỗng ở màn HKD.
  // Đánh dấu không rõ nguồn để lần chọn thủ tục cụ thể kế tiếp phải xóa, tránh dùng nhầm hồ sơ.
  if (!workProcedureKey && savedFiles.length) workProcedureKey = UNKNOWN_WORK_PROCEDURE_KEY;
  if (saved.procedureKey && PROCEDURES.some((p) => p.key === saved.procedureKey)) {
    selectedProcedureKey = saved.procedureKey;
    selectedBusinessPageKey = "";
    procedureSelect.value = saved.procedureKey;
  }
  files.length = 0;
  for (const f of savedFiles) {
    if (!f?.dataUrl) continue;
    // File khôi phục không có File object thật, nhưng đã có sẵn dataUrl nên đủ để gửi BE.
    files.push({
      file: { name: f.name, type: f.type }, role: f.role || "doc", dataUrl: f.dataUrl,
      restored: true
    });
  }
  renderProcedureResults();
  applyFormUI();
}

function restoreBusinessFillSupportCode() {
  // Chỉ khôi phục trên thủ tục HKD; cùng tab có thể được điều hướng sang một thủ tục/cổng khác.
  if (businessFillSupportCode && currentBusinessPages().length) {
    showSupportCode(businessFillSupportCode);
  }
}

function defaultRoleFor(file) {
  if (isAttachMode()) return "attachment";
  if (isAgentMode()) return "doc"; // role không quan trọng, BE tự suy luận
  const roles = effectiveRoles();
  // PDF thường là giấy tờ chứng minh (chứng sinh / khai sinh cũ / báo tử...).
  if (file.type === "application/pdf") {
    const docRole = roles.find((r) =>
      ["birthProof", "birthCert", "deathNotif"].includes(r.value)
    );
    if (docRole) return docRole.value;
  }
  return roles[0]?.value;
}

function renderFiles() {
  const roles = effectiveRoles();
  const agent = isAgentMode();
  const attach = isAttachMode();
  fileList.innerHTML = "";
  files.forEach((item, i) => {
    const li = document.createElement("li");
    const name = document.createElement("span");
    name.className = "fname";
    name.textContent = item.file.name;
    name.title = item.file.name;
    li.append(name);
    if (item.fromPhone) {
      const badge = document.createElement("span");
      badge.className = "from-phone";
      badge.textContent = "📱";
      badge.title = "Ảnh tải từ điện thoại";
      li.append(badge);
    }
    // Agent: không hiện dropdown role (BE tự suy luận).
    if (!agent && !attach) {
      const sel = document.createElement("select");
      for (const r of roles) {
        const o = document.createElement("option");
        o.value = r.value;
        o.textContent = r.label;
        if (r.value === item.role) o.selected = true;
        sel.appendChild(o);
      }
      sel.addEventListener("change", () => {
        item.role = sel.value;
      });
      li.append(sel);
    }
    const rm = document.createElement("button");
    rm.className = "rm";
    rm.textContent = "×";
    rm.addEventListener("click", () => {
      files.splice(i, 1);
      renderFiles();
      refreshAttachStepUI();
      saveSession();
    });
    li.append(rm);
    fileList.appendChild(li);
  });
}

function refreshAttachStepUI() {
  // Cập nhật trạng thái nút ủy quyền theo số file (chạy cả khi thêm/bớt file, trước early-return).
  if (proxyFillBtn) {
    proxyFillBtn.hidden = !isBacNinhAuthorizedPersonProcedure();
    proxyFillBtn.disabled = !files.length || !!window.__AUTOFILL_HCC_POPUP_BUSY__;
  }
  if (!attachStepBtn) return;
  const cfg = currentConfig();
  // Không bắt buộc process bước 2 trước: chỉ cần thủ tục có bước đính kèm + đã chọn file.
  // ĐKKD đã gộp đính kèm vào nút "Quét nhập thông tin và đính kèm" → ẩn nút đính kèm riêng.
  attachStepBtn.hidden = !cfg.hasAttachmentStep || isAttachMode() || !!currentBusinessPages().length;
  attachStepBtn.disabled = !cfg.hasAttachmentStep || !files.length || window.__AUTOFILL_HCC_POPUP_BUSY__;
}

// Mở/đóng khối chi tiết giấy tờ + báo lại chiều cao để panel (iframe) co giãn theo.
function setUploadHintOpen(open) {
  if (!uploadHintBox || !uploadHintToggle) return;
  uploadHintBox.hidden = !open;
  uploadHintToggle.setAttribute("aria-expanded", open ? "true" : "false");
  postPanelHeight();
}
if (uploadHintToggle) {
  uploadHintToggle.addEventListener("click", () => {
    setUploadHintOpen(uploadHintToggle.getAttribute("aria-expanded") !== "true");
  });
}
if (uploadHintClose) {
  uploadHintClose.addEventListener("click", () => setUploadHintOpen(false));
}

function applyFormUI() {
  const cfg = currentConfig();
  const showDangKy = !!cfg.useDangKyBy;
  dangKyBySelect.style.display = showDangKy ? "" : "none";
  if (dangKyByLabel) dangKyByLabel.style.display = showDangKy ? "" : "none";

  const showMode = !!cfg.useRequestMode;
  requestModeSelect.style.display = showMode ? "" : "none";
  if (requestModeLabel) requestModeLabel.style.display = showMode ? "" : "none";

  // Mô tả giấy tờ cần tải lên: mặc định THU GỌN (chỉ 1 dòng trigger), bấm mới mở.
  // Đổi thủ tục → luôn reset về đóng để không mang khối chi tiết dài từ thủ tục trước sang.
  if (uploadHintEl) uploadHintEl.textContent = cfg.uploadHint || "";
  if (uploadHintToggle) uploadHintToggle.hidden = !cfg.uploadHint;
  setUploadHintOpen(false);
  if (uploadLabel) {
    uploadLabel.textContent = isAttachMode() ? "+ Thêm tệp đính kèm" : "+ Thêm file ảnh/PDF/DOCX";
  }
  renderBusinessPages();
  if (fileInput) {
    fileInput.accept = isAttachMode()
      ? ".pdf,.jpg,.jpeg,.png,.xml,.mp3,.mp4,.wav,.mov,.docx,audio/*,video/*,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      : "image/*,application/pdf,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  }
  // ĐKKD gộp quét + đính kèm vào 1 nút "Quét nhập thông tin và đính kèm" → ẩn nút "Quét và nhập dữ liệu".
  const isBusiness = !!currentBusinessPages().length;
  if (ocrBtn) {
    ocrBtn.hidden = isBusiness;
    refreshOcrButtonLabel();
  }
  // Nút gộp (quét cả 8 trang + tự đính kèm) chỉ hiện cho thủ tục đăng ký kinh doanh.
  if (fillAllBtn) fillAllBtn.hidden = !isBusiness;
  // Nút "Điền thông tin người ủy quyền" chỉ hiện cho thủ tục Bắc Ninh có khối ủy quyền.
  if (proxyFillBtn) {
    proxyFillBtn.hidden = !isBacNinhAuthorizedPersonProcedure();
    proxyFillBtn.disabled = !files.length || !!window.__AUTOFILL_HCC_POPUP_BUSY__;
  }
  // Case local split bắt buộc N file = N tab nên không cho trạng thái checkbox chung can thiệp.
  // Checkbox chỉ còn dành cho các thủ tục mà người dùng thực sự được chọn tách/gộp.
  if (splitModeRow) {
    splitModeRow.style.display = isSplitEligibleProcedure() && !isClientLocalSplitProcedure() ? "" : "none";
  }
  if (!currentConfig().hasAttachmentStep) {
    lastProcessSession = null;
  } else if (lastProcessSession?.procedure !== currentConfig().key) {
    lastProcessSession = null;
  }

  if (!isAgentMode()) {
    // Role hợp lệ theo chế độ hiện tại (self → chỉ requester).
    const validRoles = new Set(effectiveRoles().map((r) => r.value));
    for (const it of files) {
      if (isAttachMode()) it.role = "attachment";
      else if (!validRoles.has(it.role)) it.role = effectiveRoles()[0]?.value;
    }
  } else {
    for (const it of files) it.role = "doc";
  }
  renderFiles();
  refreshAttachStepUI();
}

// Nút "Điền thông tin người ủy quyền" (Bắc Ninh): đọc file bằng purpose=authorized_person rồi
// gửi content điền khối "Thông tin trong trường hợp được ủy quyền" trên cổng.
if (proxyFillBtn) {
  proxyFillBtn.addEventListener("click", async () => {
    if (window.__AUTOFILL_HCC_POPUP_BUSY__) return;
    const authorizedConfig = currentBacNinhAuthorizedPersonConfig();
    if (!authorizedConfig) return;
    if (!(await requireConsent(proxyFillBtn))) return;
    window.__AUTOFILL_HCC_POPUP_BUSY__ = true;
    proxyFillBtn.disabled = true;
    try {
      await ensureSelectedFilesLoaded();
      const payloadFiles = buildPayloadFiles();
      if (!payloadFiles.length) throw new Error(authorizedConfig.missingFilesMessage);
      setStatus(`Đang đọc thông tin ${authorizedConfig.sourceLabel}...`, "info");
      const cfg = currentConfig();
      const res = await api.process({
        procedure: cfg.key,
        options: { purpose: "authorized_person" },
        files: payloadFiles,
      });
      if (!Array.isArray(res.fields) || !res.fields.length) {
        const specific = (Array.isArray(res.errors) ? res.errors : []).find((message) =>
          /ủy quyền|uy quyen/i.test(String(message || ""))
        );
        throw new Error(specific || `Không trích xuất được thông tin ${authorizedConfig.sourceLabel} từ hồ sơ.`);
      }
      const fillRes = await sendToContent({
        action: "fillBacNinhAuthorizedPerson",
        procedure: cfg.key,
        subjectOption: authorizedConfig.subjectOption,
        fields: res.fields,
      });
      if (fillRes?.error) throw new Error(fillRes.error);
      setStatus(`Đã điền ${fillRes?.filled || res.fields.length} trường thông tin ${authorizedConfig.sourceLabel}.`, "ok");
    } catch (e) {
      console.warn("[AutoFill-BN] Điền thông tin người ủy quyền lỗi:", e);
      setStatus(e?.message || String(e), "err");
    } finally {
      window.__AUTOFILL_HCC_POPUP_BUSY__ = false;
      refreshAttachStepUI();
      if (proxyFillBtn) proxyFillBtn.disabled = !files.length;
    }
  });
}

procedureSelect.addEventListener("change", () => { void selectProcedure(procedureSelect.value); });
// Trigger giống ô select → bấm mở/đóng dropdown.
if (procedureTrigger) procedureTrigger.addEventListener("click", toggleProcedureDropdown);
// Bấm ra ngoài combobox → đóng dropdown.
document.addEventListener("mousedown", (e) => {
  if (isProcedureDropdownOpen() && procedureCombo && !procedureCombo.contains(e.target)) {
    closeProcedureDropdown();
  }
});
if (procedureSearchInput) {
  // Combobox realtime: gõ tới đâu lọc tới đó (tối đa SEARCH_PROCEDURE_LIMIT kết quả).
  procedureSearchInput.addEventListener("input", commitProcedureSearch);
  procedureSearchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const first = getVisibleProcedures(procedureSearchInput.value.trim())[0];
      if (first) void selectProcedure(first.key);  // Enter → chọn kết quả đầu tiên (tự đóng)
    } else if (e.key === "Escape") {
      e.preventDefault();
      closeProcedureDropdown();
    }
  });
}
requestModeSelect.addEventListener("change", applyFormUI);
if (splitModeToggle) {
  splitModeToggle.addEventListener("change", () => {
    attachSplitMode = !!splitModeToggle.checked;
    chrome.storage.local.set({ [SPLIT_MODE_KEY]: attachSplitMode });
  });
}

async function restoreSplitMode() {
  try {
    const res = await chrome.storage.local.get(SPLIT_MODE_KEY);
    attachSplitMode = !!res[SPLIT_MODE_KEY];
  } catch (_) { attachSplitMode = false; }
  if (splitModeToggle) splitModeToggle.checked = attachSplitMode;
}

// Đọc cài đặt "tách giấy tờ trong file" từ storage (do settings.html ghi). Không có ô tick ở popup.
async function restoreSplitDocumentsSetting() {
  try {
    const result = await chrome.storage.local.get([SPLIT_DOCUMENTS_SETTING_KEY, SUBMITTER_OWNER_MODE_KEY, ESTATE_SPLIT_ATTACH_KEY]);
    attachSplitDocuments = result[SPLIT_DOCUMENTS_SETTING_KEY] === true;
    submitterOwnerMode = result[SUBMITTER_OWNER_MODE_KEY] === true;
    estateSplitAttachments = result[ESTATE_SPLIT_ATTACH_KEY] === true;
  } catch (_) { attachSplitDocuments = false; submitterOwnerMode = false; estateSplitAttachments = false; }
}
// settings.html bật/tắt → đồng bộ ngay vào popup đang mở (không cần mở lại popup).
chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName !== "local") return;
  if (changes[SPLIT_DOCUMENTS_SETTING_KEY]) attachSplitDocuments = changes[SPLIT_DOCUMENTS_SETTING_KEY].newValue === true;
  if (changes[SUBMITTER_OWNER_MODE_KEY]) submitterOwnerMode = changes[SUBMITTER_OWNER_MODE_KEY].newValue === true;
  if (changes[ESTATE_SPLIT_ATTACH_KEY]) estateSplitAttachments = changes[ESTATE_SPLIT_ATTACH_KEY].newValue === true;
});

fileInput.addEventListener("change", () => {
  for (const f of fileInput.files) files.push({ file: f, role: defaultRoleFor(f) });
  fileInput.value = "";
  renderFiles();
  refreshAttachStepUI();
  saveSession();
});

function readAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = () => reject(r.error);
    r.readAsDataURL(file);
  });
}

// ===== Thêm ảnh từ điện thoại qua QR =====
// Phiên upload BE chỉ là CẦU NỐI: ảnh điện thoại được kéo về files[] y như ảnh chọn tay,
// rồi "Quét và nhập"/"Đính kèm" chạy như thường (không đụng /process).
const phoneUploadBtn = document.getElementById("phoneUploadBtn");
const qrCard = document.getElementById("qrCard");
let phoneUploadSid = null;
let phoneUploadWs = null;
let phoneReconcile = null;     // poll ĐỐI SOÁT: LUÔN chạy làm lưới an toàn (kể cả khi WS không kết nối/miss event)
let phone404 = 0;              // đếm 404 liên tiếp → chỉ đóng khi phiên THẬT SỰ hết hạn (không phải chớp mạng)
const pulledFids = new Set();  // fid đã kéo về files[] → chống trùng (WS và poll dùng chung)

function stopPhoneUploadChannel() {
  if (phoneUploadWs) {
    try { phoneUploadWs.onclose = null; phoneUploadWs.onmessage = null; phoneUploadWs.onerror = null; phoneUploadWs.close(); } catch (_) { }
    phoneUploadWs = null;
  }
  if (phoneReconcile) { clearInterval(phoneReconcile); phoneReconcile = null; }
}

function closePhoneUpload() {
  phoneUploadSid = null; // đặt null TRƯỚC để mọi guard bằng sid tự vô hiệu
  pulledFids.clear();
  phone404 = 0;
  stopPhoneUploadChannel();
  if (qrCard) { qrCard.hidden = true; qrCard.innerHTML = ""; }
}

function setQrStatus(text) {
  const el = qrCard && qrCard.querySelector(".qr-stat");
  if (el) el.textContent = text;
}

// Kéo các fid CHƯA có về files[] (bọc như ảnh chọn tay). Tải SONG SONG cho nhanh.
// Nhận `list` từ WS (chỉ lô mới) HOẶC từ poll đối soát (toàn bộ) — pulledFids khử trùng.
async function pullPhoneFiles(list) {
  if (!phoneUploadSid) return 0;
  const sid = phoneUploadSid;
  const fresh = (list || []).filter((f) => f && f.fid && !pulledFids.has(f.fid));
  fresh.forEach((f) => pulledFids.add(f.fid)); // giữ chỗ trước → lô/poll khác không kéo trùng
  const results = await Promise.all(fresh.map(async (f) => {
    const res = await api.fetchUploadFileDataUrl(sid, f.fid);
    if (!res || !res.dataUrl) { pulledFids.delete(f.fid); return null; } // tải lỗi → cho kéo lại lượt sau
    return { f, res };
  }));
  if (phoneUploadSid !== sid) return 0; // phiên đã đổi/đóng giữa chừng → bỏ kết quả
  let added = 0;
  for (const r of results) {
    if (!r) continue;
    const type = r.res.type || r.f.type || "image/jpeg";
    files.push({
      file: { name: r.f.name || "anh-dien-thoai.jpg", type },
      role: defaultRoleFor({ type }), dataUrl: r.res.dataUrl,
      fromPhone: true,
    });
    added++;
  }
  if (added) {
    renderFiles();
    refreshAttachStepUI();
    saveSession();
    const n = files.filter((it) => it.fromPhone).length;
    setQrStatus(`✅ Đã nhận ${n} ảnh từ điện thoại — có thể gửi tiếp hoặc bấm "Quét và nhập".`);
  }
  return added;
}

// 1 lượt đối soát: đọc toàn bộ danh sách file của phiên, kéo cái còn thiếu.
// Lỗi CHỚP MẠNG → bỏ qua, thử lại lượt sau (KHÔNG đóng kênh). Chỉ đóng khi 404 lặp lại (hết hạn thật).
async function reconcilePhoneOnce() {
  if (!phoneUploadSid) return;
  const sid = phoneUploadSid;
  try {
    const s = await api.getUploadSession(sid);
    phone404 = 0;
    await pullPhoneFiles(s.files);
  } catch (e) {
    if (e && e.status === 404) {
      if (++phone404 >= 2 && phoneUploadSid === sid) {
        closePhoneUpload();
        setStatus("Phiên tải ảnh đã hết hạn. Bấm lại để tạo mã QR mới.", "err");
      }
    }
    // lỗi khác (timeout/chớp mạng 4G) → im lặng, lượt sau thử lại
  }
}

async function openPhoneUpload() {
  if (!currentUser) { setStatus("Bà con đăng nhập trước khi tải ảnh từ điện thoại ạ.", "err"); return; }
  try {
    closePhoneUpload();
    setStatus("Đang tạo mã QR…", "info");
    const s = await api.createUploadSession();
    phoneUploadSid = s.session_id;
    renderQrCard(s);
    subscribePhoneUpload(s.session_id);                 // WS: giao tức thì (nếu proxy cho WS)
    phoneReconcile = setInterval(reconcilePhoneOnce, 2000); // lưới an toàn: LUÔN chạy, bắt cả lô WS bỏ sót
    setStatus("", "");
  } catch (e) {
    if (e.unauthorized) { await AuthStore.clearTokens(); setStatus("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", "err"); showLogin(); return; }
    console.warn("[Popup] Tạo mã QR lỗi:", e);
    setStatus("Không tạo được mã QR. Vui lòng thử lại.", "err");
  }
}

function renderQrCard(s) {
  if (!qrCard) return;
  qrCard.hidden = false;
  qrCard.innerHTML =
    `<button type="button" class="qr-close" title="Đóng mã QR">×</button>
     <div class="qr-body">
       <img class="qr-img" alt="Mã QR tải ảnh từ điện thoại" src="data:image/png;base64,${s.qr_png_base64}">
       <div class="qr-info">
         <div class="qr-cap">Quét mã bằng camera điện thoại để thêm ảnh. Ảnh sẽ tự về danh sách bên dưới.</div>
         <div class="qr-stat">Đang chờ điện thoại quét mã…</div>
       </div>
     </div>`;
  const close = qrCard.querySelector(".qr-close");
  if (close) close.addEventListener("click", closePhoneUpload);
}

// WS chỉ để GIAO NHANH; nếu proxy không cho WS thì reconcile poll (2s) vẫn gánh đủ.
function subscribePhoneUpload(sid) {
  try {
    phoneUploadWs = new WebSocket(`${window.WS_BASE}/ws/upload-sessions/${encodeURIComponent(sid)}`);
    phoneUploadWs.onmessage = async (ev) => {
      let d; try { d = JSON.parse(ev.data); } catch (_) { return; }
      if (d.type === "session_opened") setQrStatus("📱 Điện thoại đã kết nối — mời bà con chụp/chọn ảnh…");
      else if (d.type === "files_added") await pullPhoneFiles(d.files);
    };
    phoneUploadWs.onerror = () => { try { phoneUploadWs && phoneUploadWs.close(); } catch (_) { } };
    // onclose: KHÔNG cần làm gì — reconcile poll đã luôn chạy làm lưới an toàn.
  } catch (_) { /* WS không mở được cũng không sao, đã có reconcile poll */ }
}

if (phoneUploadBtn) phoneUploadBtn.addEventListener("click", openPhoneUpload);

async function ensureSelectedFilesLoaded() {
  for (const it of files) if (!it.dataUrl) it.dataUrl = await readAsDataUrl(it.file);
}

function buildPayloadFiles() {
  return files.map((it) => ({
    name: it.file.name,
    type: it.file.type || "image/jpeg",
    dataUrl: it.dataUrl,
    role: it.role || "doc",
  }));
}

// ĐÍNH KÈM: chuyển ảnh (jpg/png) sang PDF (lossless) trước khi đưa lên cổng. File vốn đã là PDF/khác → giữ nguyên.
// Chỉ áp cho luồng attach; OCR vẫn gửi ảnh gốc. Lỗi convert 1 file → giữ nguyên file đó, không chặn cả lô.
async function toPdfForAttach(payloadFiles) {
  if (!window.PdfConvert) return payloadFiles; // thiếu lib → không chặn attach
  const out = [];
  for (const f of payloadFiles) {
    if (f.dataUrl && PdfConvert.isImage(f.type, f.name)) {
      try {
        const pdf = await PdfConvert.imageToPdf(f.dataUrl, f.name, f.type);
        out.push({ ...f, ...pdf }); // name/type/dataUrl thành PDF; giữ role
      } catch (e) {
        console.warn("[PdfConvert] Không chuyển được ảnh sang PDF, giữ nguyên:", f.name, e);
        out.push(f);
      }
    } else {
      out.push(f);
    }
  }
  return out;
}

// DỰNG file theo kế hoạch BE:
// - sourceSegments: trích/gộp đúng các trang từ một hoặc nhiều file;
// - sourceFileIndexes: contract cũ, gộp nguyên các file.
// Tách trang lỗi phải dừng, không được đính nhầm cả PDF gốc vào một thành phần.
async function applyMergeGroups(payloadFiles, attachments) {
  const hasSegments = (attachments || []).some(
    (a) => Array.isArray(a.sourceSegments) && a.sourceSegments.length > 0
  );
  const hasMerge = (attachments || []).some(
    (a) => Array.isArray(a.sourceFileIndexes) && a.sourceFileIndexes.length > 1
  );
  if (!hasMerge && !hasSegments) return { files: payloadFiles, attachments };
  if (!window.PdfConvert) throw new Error("Thiếu bộ xử lý PDF để tách hoặc gộp tài liệu.");

  const outFiles = [];
  const outAtts = [];
  for (const item of attachments) {
    const segments = Array.isArray(item.sourceSegments) && item.sourceSegments.length
      ? item.sourceSegments
      : null;
    const src = Array.isArray(item.sourceFileIndexes) && item.sourceFileIndexes.length
      ? item.sourceFileIndexes
      : [item.fileIndex];
    const sources = src.map((i) => payloadFiles[i]).filter(Boolean);
    if (!segments && !sources.length) continue;

    let file = segments
      ? payloadFiles[Number(segments[0]?.fileIndex)]
      : sources[0];
    if (segments) {
      // Không fallback sang file đầu: làm vậy sẽ đưa toàn bộ PDF hỗn hợp vào sai hàng.
      const composed = await PdfConvert.composeSegmentsToPdf(
        payloadFiles,
        segments,
        item.documentName || file?.name || "tai-lieu"
      );
      file = { ...(file || {}), ...composed };
    } else if (sources.length > 1) {
      try {
        const merged = await PdfConvert.mergeToPdf(sources, item.documentName || sources[0].name);
        file = { ...sources[0], ...merged }; // giữ role, thay name/type/dataUrl
      } catch (e) {
        console.warn("[PdfConvert] Gộp PDF thất bại, đính file đầu:", e);
        file = sources[0];
      }
    }
    const newIndex = outFiles.length;
    outFiles.push(file);
    const rewritten = { ...item, fileIndex: newIndex, sourceFileIndexes: [newIndex] };
    delete rewritten.sourceSegments;
    outAtts.push(rewritten);
  }
  return { files: outFiles, attachments: outAtts };
}

// Đăng ký hộ kinh doanh (cổng HkdOnline): luồng đính kèm nhiều postback → giao content chạy state machine.
async function runBusinessAttach(cfg, options) {
  const payloadFiles = await toPdfForAttach(buildPayloadFiles());
  if (!payloadFiles.length) return { error: "Chưa có file nào." };

  setStatus("Đang phân tích & phân loại tài liệu...", "info");
  const planRes = await api.attachmentPlan({ procedure: cfg.key, options, files: payloadFiles });
  console.log("[BE AttachmentPlan][HKD]", {
    attachments: planRes.attachments, extracted: planRes.extracted, errors: planRes.errors,
  });
  const attachments = planRes.attachments || [];
  if (!attachments.length) {
    const reason = Array.isArray(planRes.errors) && planRes.errors.length
      ? planRes.errors.join("; ")
      : "Backend chưa trả về kế hoạch đính kèm.";
    return { error: reason };
  }

  const startRes = await sendToContent({
    action: "startAttachAllBusiness",
    files: payloadFiles,
    attachments,
  });
  if (startRes?.error) return startRes;
  return {
    ok: true,
    message: "Đang tự đính kèm hồ sơ (khai báo loại → tải file → gán loại → lưu). Đừng thao tác trên trang tới khi xong.",
  };
}

async function runAttachmentPlanForCurrentFiles(options = {}) {
  const cfg = currentConfig();
  if (cfg.key === "dang-ky-kinh-doanh") return await runBusinessAttach(cfg, options);
  const payloadFiles = await toPdfForAttach(buildPayloadFiles());
  if (!payloadFiles.length) return { error: "Chưa có file nào." };

  setStatus("Đang đọc thành phần hồ sơ trên trang...", "info");
  const ctxRes = await sendToContent({ action: "collectAttachmentContext", procedure: cfg.key });
  if (ctxRes?.error) return { error: ctxRes.error };
  if (ctxRes?.attachmentContext) options.attachmentContext = ctxRes.attachmentContext;

  // Case metadata-only: toàn bộ plan + đổi tên + chia tab chạy tại extension.
  // Backend chỉ nhận tên/type/size để ghi trace, KHÔNG nhận dataUrl hay binary file.
  if (isClientLocalSplitProcedure(cfg)) {
    options.splitMode = true;
    const local = buildClientLocalSplitPlan(payloadFiles, clientAttachmentCase(cfg));
    if (local.error) return { error: local.error };
    setStatus("Đang tạo mã hỗ trợ cho lượt đính kèm...", "info");
    const traceRes = await api.clientAttachmentTrace({
      procedure: cfg.key,
      options,
      files: local.files.map((file) => ({
        name: file.name,
        type: file.type || "application/octet-stream",
        role: file.role || "attachment",
        size: attachmentPayloadByteSize(file),
      })),
      attachments: local.attachments,
    });
    const localAttachRes = await attachSplitAcrossTabs(
      local.files,
      local.attachments,
      cfg.key,
      traceRes,
    );
    return {
      ...localAttachRes,
      requestId: localAttachRes?.requestId || traceRes?.requestId,
    };
  }

  // Gửi lựa chọn "tách hồ sơ" về BE để lưu vào trace (phục vụ thống kê tách/gộp).
  // Chỉ gắn với thủ tục có ô tick (chứng thực bản sao/chữ ký) — true/false theo người dùng chọn.
  if (isSplitEligibleProcedure()) options.splitMode = !!attachSplitMode;
  if (cfg.supportsSplitDocuments) options.splitDocuments = !!attachSplitDocuments;
  // Toggle "Không gộp giấy tờ" chỉ áp dụng riêng thủ tục phân chia di sản → BẬT = tách mỗi giấy tờ 1 dòng.
  if (cfg.key === ESTATE_SPLIT_PROCEDURE_KEY) options.splitDocuments = !!estateSplitAttachments;

  setStatus("Đang phân tích tài liệu đính kèm...", "info");
  const planRes = await api.attachmentPlan({ procedure: cfg.key, options, files: payloadFiles });
  console.log("[BE AttachmentPlan]", {
    attachments: planRes.attachments,
    extracted: planRes.extracted,
    stats: planRes.stats,
    errors: planRes.errors,
  });
  const rawAttachments = planRes.attachments || [];
  if (!rawAttachments.length) {
    // Backend trả lý do cụ thể trong errors (vd không tìm thấy giấy chứng sinh) → hiện cho người dùng.
    const reason = Array.isArray(planRes.errors) && planRes.errors.length
      ? planRes.errors.join("; ")
      : "Backend chưa trả về kế hoạch đính kèm file.";
    return { error: reason };
  }

  // GỘP file theo kế hoạch (CCCD mặt trước/sau → 1 PDF) trước khi gửi content.
  const { files: sendFiles, attachments } = await applyMergeGroups(payloadFiles, rawAttachments);

  // Chế độ TÁCH HỒ SƠ (split): mỗi tài liệu 1 hồ sơ riêng → điều phối đa-tab.
  if (attachSplitMode && isSplitEligibleProcedure() && sendFiles.length > 1) {
    return await attachSplitAcrossTabs(sendFiles, attachments, cfg.key, planRes);
  }

  // Hotfix Hải Châu (Đà Nẵng) — merge 1 tab: chèn 1 file ẢO vào STT1 (BE đã đẩy giấy tờ thật xuống dòng
  // "Thêm thành phần"). Directive `stt1VirtualCopy` chỉ có với tài khoản Hải Châu → account khác không đổi.
  let sendAttachments = attachments;
  if (planRes.stt1VirtualCopy) {
    const src = attachments.find((a) => a && Number.isInteger(a.fileIndex) && sendFiles[a.fileIndex]) || attachments[0];
    const virtual = buildStt1VirtualItem(planRes.stt1VirtualCopy, src, sendFiles);
    if (virtual) sendAttachments = [virtual, ...attachments];
  }

  setStatus("Đang đính kèm file vào hồ sơ...", "info");
  // File lớn (hợp đồng vài chục MB) → tổng payload base64 vượt giới hạn 64MiB của tabs.sendMessage.
  // Chuyển file qua chrome.storage.local (permission unlimitedStorage — KHÔNG dính giới hạn message),
  // chỉ gửi KEY kèm kế hoạch; content.js đọc lại rồi xoá key.
  const attachMode = attachSplitMode && isSplitEligibleProcedure() ? "split" : "merge";
  const approxBytes = sendFiles.reduce((s, f) => s + String(f?.dataUrl || "").length, 0);
  let attachMsg = { action: "attachFilesByPlan", procedure: cfg.key, files: sendFiles, attachments: sendAttachments, mode: attachMode };
  let attachFilesKey = "";
  if (approxBytes > 45 * 1024 * 1024) {
    attachFilesKey = "__af_attach_files_" + Date.now();
    try {
      await chrome.storage.local.set({ [attachFilesKey]: { files: sendFiles } });
      attachMsg = { action: "attachFilesByPlan", procedure: cfg.key, attachments: sendAttachments, mode: attachMode, filesStorageKey: attachFilesKey };
    } catch (e) {
      attachFilesKey = ""; // ghi storage lỗi → gửi trực tiếp (có thể vẫn vượt nhưng còn cơ hội)
    }
  }
  const attachRes = await sendToContent(attachMsg);
  if (attachFilesKey) { try { await chrome.storage.local.remove(attachFilesKey); } catch (e) { /* ignore */ } }
  // Kèm mã hỗ trợ (BE đã tạo trace dù đính kèm phía trang lỗi) để cán bộ báo lỗi có mã tra.
  if (attachRes?.error) return { ...attachRes, requestId: planRes.requestId };

  const names = (attachRes?.fileNames || []).join(", ");
  const skippedNames = (attachRes?.skippedNames || []).join(", ");
  const attachedCount = Number.isInteger(attachRes?.attached) ? attachRes.attached : sendFiles.length;
  const skippedCount = Number.isInteger(attachRes?.skipped) ? attachRes.skipped : 0;

  // Người dùng tải `payloadFiles.length` file GỐC; BE có thể GỘP nhiều file thành 1 nhóm (1 PDF) →
  // còn `sendFiles.length` nhóm. Phải báo rõ số file gốc + gộp thành nhóm nào, tránh hiểu nhầm
  // "4/4" là đã mất 3 file. Nếu không gộp (số nhóm = số file) thì giữ câu cũ cho gọn.
  const uploadedCount = payloadFiles.length;
  const isMerged = uploadedCount > sendFiles.length;
  let msg = isMerged
    ? `Đã tải lên ${uploadedCount} file, gộp thành ${sendFiles.length} nhóm hồ sơ; đã đính kèm ${attachedCount}/${sendFiles.length} nhóm.`
    : `Đã đính kèm ${attachedCount}/${sendFiles.length} file vào hồ sơ.`;
  if (isMerged) {
    // Liệt kê từng nhóm gồm những file gốc nào (theo sourceFileIndexes của kế hoạch TRƯỚC khi gộp).
    const groupLines = (rawAttachments || [])
      .map((a) => {
        const src = Array.isArray(a.sourceFileIndexes) && a.sourceFileIndexes.length
          ? a.sourceFileIndexes
          : [a.fileIndex];
        const srcNames = src.map((i) => payloadFiles[i]?.name).filter(Boolean).join(" + ");
        return srcNames ? `• ${a.documentName || "Hồ sơ"} ← ${srcNames}` : "";
      })
      .filter(Boolean);
    if (groupLines.length) msg += `\n${groupLines.join("\n")}`;
  } else if (names) {
    msg += `\n${names}`;
  }
  if (skippedCount) msg += `\nBỏ qua ${skippedCount} file đã có trong hồ sơ.`;
  if (skippedNames) msg += `\nĐã có: ${skippedNames}`;
  // errors[] từ BE có thể chứa chi tiết kỹ thuật → chỉ log, KHÔNG nối thô vào thông báo thành công.
  if (planRes.errors?.length) console.warn("[AutoFill-Attach] Cảnh báo xử lý:", planRes.errors);
  // Đính chưa đủ (attachedCount < số nhóm) → cảnh báo (warn) thay vì báo thành công trọn vẹn.
  const warn = attachedCount < sendFiles.length;
  const toastMessage = warn
    ? "Đã xử lý xong bước đính kèm. Vui lòng rà soát hồ sơ."
    : "Đã đính kèm xong hồ sơ.";
  await showPageToast(toastMessage, warn ? "warn" : "success");
  return { ok: true, message: msg, warn, requestId: planRes.requestId };
}

// Lấy plan item của BE cho file thứ `origIndex`, rồi đổi sang vị trí của file trong bundle gửi cho tab.
// sourceFileIndexes là fallback khi PdfConvert chưa gộp được nhiều mặt giấy tùy thân.
function planItemForFile(attachments, origIndex, file, bundleIndex = 0) {
  const it = (attachments || []).find((a) => a && a.fileIndex === origIndex) ||
    (attachments || []).find((a) => Array.isArray(a?.sourceFileIndexes) && a.sourceFileIndexes.includes(origIndex)) ||
    {};
  return {
    ...it,
    fileIndex: bundleIndex,
    fileName: file?.name || it.fileName,
    documentName: it.documentName || file?.name,
    detectedType: it.detectedType || it.documentName || file?.name,
  };
}

function attachmentPayloadByteSize(file) {
  const dataUrl = String(file?.dataUrl || "");
  const comma = dataUrl.indexOf(",");
  const payload = comma >= 0 ? dataUrl.slice(comma + 1) : dataUrl;
  if (!payload) return 0;
  const padding = payload.endsWith("==") ? 2 : payload.endsWith("=") ? 1 : 0;
  return Math.max(Math.floor(payload.length * 3 / 4) - padding, 0);
}

function clientLocalDocumentName(fileName) {
  const raw = String(fileName || "");
  const dot = raw.lastIndexOf(".");
  const stem = dot > 0 ? raw.slice(0, dot) : raw;
  const normalized = stem
    .normalize("NFC")
    .replace(/[^\p{L}\p{N}_\-\s]+/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
  // Cổng dùng Zod string.max(50), tức giới hạn theo JS string.length.
  return (normalized || "Ban_dich_va_giay_to_can_dich").slice(0, 50).trim();
}

function clientLocalFileExtension(fileName) {
  const match = String(fileName || "").match(/(\.[^.\s]+)$/);
  return match ? match[1] : "";
}

function buildClientLocalSplitPlan(payloadFiles, config) {
  const componentName = String(config?.componentName || "").trim();
  const componentIndex = Number(config?.componentIndex);
  if (!componentName || !Number.isInteger(componentIndex) || componentIndex < 1) {
    return { error: "Cấu hình thành phần hồ sơ đính kèm cục bộ không hợp lệ." };
  }

  const files = [];
  const attachments = [];
  for (let index = 0; index < payloadFiles.length; index++) {
    const source = payloadFiles[index];
    const documentName = clientLocalDocumentName(source?.name);
    const safeFileName = documentName + clientLocalFileExtension(source?.name);
    const file = { ...source, name: safeFileName, originalName: source?.name || safeFileName };
    files.push(file);
    attachments.push({
      fileIndex: index,
      fileName: safeFileName,
      documentName,
      componentName,
      componentIndex,
      target: "existing",
      needsAddComponent: false,
      appendOnOccupied: false,
      detectedType: componentName,
      // Nếu tên bản dịch có chữ CCCD vẫn phải vào hàng 1; không được áp heuristic giấy tùy thân.
      forceFirstRow: true,
    });
  }
  return { files, attachments };
}

function isSignatureIdentityPlanItem(item) {
  if (item?.bundleRole === "identity") return true;
  if (item?.bundleRole === "signature_document") return false;
  return Number(item?.componentIndex) === 2;
}

async function buildSignatureSplitBundles(payloadFiles, attachments) {
  const entries = payloadFiles.map((file, index) => ({
    file,
    planItem: planItemForFile(attachments, index, file),
  }));
  const identityEntries = entries.filter((entry) => isSignatureIdentityPlanItem(entry.planItem));
  const documentEntries = entries.filter((entry) => !isSignatureIdentityPlanItem(entry.planItem));
  if (!documentEntries.length) {
    return { error: "Không tìm thấy giấy tờ, văn bản cần chứng thực chữ ký để đính vào STT1." };
  }

  const hasBundleContract = entries.some((entry) =>
    entry.planItem?.bundleId || entry.planItem?.bundleRole || entry.planItem?.identityScope);
  if (hasBundleContract) {
    const invalid = entries.find((entry) =>
      !entry.planItem?.bundleId ||
      !["signature_document", "identity"].includes(entry.planItem?.bundleRole));
    if (invalid) {
      return {
        error: `Kế hoạch nhiều hồ sơ thiếu quan hệ bundle cho ${invalid.file?.name || "một tệp"}.`,
      };
    }

    const bundleOrder = [];
    const grouped = new Map();
    for (const entry of entries) {
      const bundleId = String(entry.planItem.bundleId);
      if (!grouped.has(bundleId)) grouped.set(bundleId, []);
      grouped.get(bundleId).push(entry);
      if (entry.planItem.bundleRole === "signature_document" && !bundleOrder.includes(bundleId)) {
        bundleOrder.push(bundleId);
      }
    }
    if (bundleOrder.length !== grouped.size) {
      return { error: "Có bundle giấy tờ tùy thân nhưng thiếu văn bản cần chứng thực chữ ký." };
    }

    const bundles = [];
    for (const bundleId of bundleOrder) {
      const group = grouped.get(bundleId) || [];
      const documents = group.filter((entry) => entry.planItem.bundleRole === "signature_document");
      const identities = group.filter((entry) => entry.planItem.bundleRole === "identity");
      if (documents.length !== 1) {
        return { error: `Bundle ${bundleId} phải có đúng một văn bản cần chứng thực chữ ký.` };
      }
      if (identities.length > 1) {
        return { error: `Bundle ${bundleId} có nhiều nhóm giấy tờ tùy thân chưa được backend gộp.` };
      }

      const ordered = [...documents, ...identities];
      const files = ordered.map((entry) => entry.file);
      const planItems = ordered.map((entry, bundleIndex) => ({
        ...entry.planItem,
        fileIndex: bundleIndex,
        sourceFileIndexes: [bundleIndex],
        fileName: entry.file?.name || entry.planItem.fileName,
        documentName: entry.planItem.documentName || entry.file?.name,
        target: "existing",
        componentIndex: entry.planItem.bundleRole === "identity" ? 2 : 1,
        needsAddComponent: false,
        appendOnOccupied: false,
      }));
      bundles.push({ files, planItems });
    }
    return { bundles };
  }

  // Contract cũ chỉ an toàn khi có tối đa một identity dùng chung. Nhiều identity nhưng không có
  // bundleId không đủ dữ liệu để biết file nào thuộc người ký nào, nên phải dừng thay vì gộp liều.
  if (identityEntries.length > 1) {
    return { error: "Backend chưa trả quan hệ ghép hồ sơ cho nhiều giấy tờ tùy thân." };
  }

  let sharedIdentityFile = null;
  let sharedIdentityPlan = null;
  if (identityEntries.length) {
    const firstIdentity = identityEntries[0];
    sharedIdentityFile = firstIdentity.file;
    sharedIdentityPlan = firstIdentity.planItem;
  }

  return {
    bundles: documentEntries.map((entry, bundleIndex) => {
      const files = [entry.file];
      const planItems = [planItemForFile([entry.planItem], 0, entry.file, 0)];
      // CCCD chỉ thuộc hồ sơ/tab đầu tiên. Các bundle đưa vào queue từ tab thứ hai trở đi
      // chỉ có đúng một giấy tờ STT1, không lặp giấy tùy thân sang hồ sơ mới.
      if (bundleIndex === 0 && sharedIdentityFile && sharedIdentityPlan) {
        files.push(sharedIdentityFile);
        planItems.push({
          ...sharedIdentityPlan,
          fileIndex: 1,
          sourceFileIndexes: [1],
          fileName: sharedIdentityFile.name || sharedIdentityPlan.fileName,
          target: "existing",
          componentIndex: 2,
          needsAddComponent: false,
          appendOnOccupied: false,
        });
      }
      return { files, planItems };
    }),
  };
}

// Hotfix Hải Châu (Đà Nẵng) — Chứng thực bản sao: BE ra directive `stt1VirtualCopy` và đã đẩy HẾT giấy tờ
// thật xuống dòng "Thêm thành phần" (target=new). Ô cố định STT1 cần 1 file ẢO = COPY (DÙNG LẠI byte, đổi
// tên) của 1 file thật. Trả về plan item ảo (cờ `virtualCopy`) trỏ tới ĐÚNG fileIndex của file nguồn nên
// KHÔNG tốn payload. No-op (null) cho mọi tài khoản/thủ tục khác (directive không có).
function buildStt1VirtualItem(directive, source, files) {
  if (!directive || !source) return null;
  const idx = Number.isInteger(source.fileIndex) ? source.fileIndex : -1;
  if (idx < 0 || !Array.isArray(files) || !files[idx]) return null;
  const srcName = files[idx]?.name || source.documentName || "tai-lieu";
  return {
    ...source,
    virtualCopy: true,
    target: "existing",
    componentIndex: directive.componentIndex || 1,
    componentName: directive.componentName || source.componentName || "",
    needsAddComponent: false,
    appendOnOccupied: false,
    documentName: directive.documentName || srcName,
    fileIndex: idx,
    sourceFileIndexes: [idx],
    fileName: srcName,
  };
}

function buildDefaultSplitBundles(payloadFiles, attachments, stt1Virtual = null) {
  return payloadFiles.map((file, index) => {
    const real = planItemForFile(attachments, index, file, 0);
    const planItems = [real];
    // Hải Châu: mỗi tab thêm 1 file ẢO vào STT1 = copy chính file của tab (real.fileIndex = 0 trong bundle).
    if (stt1Virtual) {
      const virtual = buildStt1VirtualItem(stt1Virtual, real, [file]);
      if (virtual) planItems.push(virtual);
    }
    return { files: [file], planItems };
  });
}

// Tách hồ sơ: bundle[0] → tab hiện tại; bundle[1..] → hàng đợi tuần tự, mỗi lần chỉ 1 tab active.
// Riêng chứng thực chữ ký: ưu tiên bundleId từ BE; identity shared chỉ có ở bundle đầu, identity
// matched đi theo đúng người ký. Contract cũ chỉ fallback cho tối đa một identity dùng chung.
async function attachSplitAcrossTabs(payloadFiles, attachments, procedure, planRes) {
  const built = procedure === "chung-thuc-chu-ky"
    ? await buildSignatureSplitBundles(payloadFiles, attachments)
    : { bundles: buildDefaultSplitBundles(payloadFiles, attachments, planRes?.stt1VirtualCopy) };
  if (built.error) return built;
  const bundles = built.bundles || [];
  if (!bundles.length) return { error: "Không có tài liệu để tách hồ sơ." };
  const firstBundle = bundles[0];
  const rest = bundles.slice(1);
  const originTabId = await getTargetTabId();
  splitProgressOriginTabId = originTabId || splitProgressOriginTabId;
  activeSplitRunId = null;
  await sendToBackground({ action: "clearAllPendingAttach" }); // dọn hàng đợi cũ

  // URL hồ sơ SẠCH (chỉ giữ maThuTuc/tinhThanhId) — lấy TRƯỚC khi đính để tab mới là hồ sơ MỚI.
  const urlRes = await sendToContent({ action: "getDossierUrl" });
  const dossierUrl = urlRes?.url;
  if (!dossierUrl) {
    return { error: "Không lấy được URL hồ sơ để mở tab mới. Hãy mở đúng trang nộp hồ sơ chứng thực." };
  }

  // Bundle đầu → tab hiện tại.
  setStatus("Đang đính kèm tài liệu 1 vào hồ sơ hiện tại...", "info");
  const firstRes = await sendToContent({
    action: "attachFilesByPlan",
    procedure,
    files: firstBundle.files,
    attachments: firstBundle.planItems,
    mode: "split",
  });
  let currentTabRecovery = null;
  if (firstRes?.error) {
    if (!SPLIT_RELOADABLE_WALLET_CODES.has(String(firstRes.code || ""))) return firstRes;
    const tabId = await getTargetTabId();
    const staged = await sendToBackground({
      action: "stageDossierTabAttach",
      tabId,
      files: firstBundle.files,
      attachments: firstBundle.planItems,
      procedure,
      recoveryCode: firstRes.code,
    });
    if (staged?.error) return { error: staged.error, code: firstRes.code };
    currentTabRecovery = { tabId, code: firstRes.code };
  }

  // Không mở đồng thời: background chỉ tạo tab kế tiếp sau khi tab active báo thành công/thất bại.
  // Cả bản sao và chữ ký đều đi qua cùng queue này; khác nhau chỉ ở nội dung từng bundle.
  let queueRes = { ok: true, remaining: 0 };
  let splitRunId = null;
  if (rest.length) {
    splitRunId = globalThis.crypto?.randomUUID?.() || `split-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    activeSplitRunId = splitRunId;
    const queueItems = rest.map((bundle, index) => ({
      ordinal: index + 2,
      url: dossierUrl,
      files: bundle.files,
      attachments: bundle.planItems,
      procedure,
    }));
    try {
      await chrome.storage.local.set({
        [SPLIT_ATTACH_QUEUE_STAGE_KEY]: { items: queueItems, stagedAt: Date.now() },
      });
      // Chỉ gửi key nhẹ qua runtime message; tuyệt đối không nhét dataUrl của cả queue vào message.
      queueRes = await sendToBackground({
        action: "startSplitAttachQueue",
        waitForTabId: currentTabRecovery?.tabId || null,
        itemsStorageKey: SPLIT_ATTACH_QUEUE_STAGE_KEY,
        runId: splitRunId,
        originTabId,
        procedure,
        totalBundles: bundles.length,
        initialCompleted: currentTabRecovery ? 0 : 1,
        initialSucceeded: currentTabRecovery ? 0 : 1,
      });
    } catch (e) {
      queueRes = { error: `Không lưu được hàng đợi tách hồ sơ: ${e?.message || String(e)}` };
    } finally {
      // Background cũng xóa sau khi nhận; popup xóa lần nữa để dọn khi message thất bại giữa chừng.
      try { await chrome.storage.local.remove(SPLIT_ATTACH_QUEUE_STAGE_KEY); } catch (_) { /* ignore */ }
    }
    if (queueRes?.error) {
      activeSplitRunId = null;
      await sendToBackground({ action: "clearAllPendingAttach" });
      return { error: queueRes.error };
    }
  }

  // Khi tab đầu lỗi modal, queue chờ chính tab đó. Reload xong, content báo terminal thì background
  // mới được tạo tab thứ hai; popup bị hủy bởi reload cũng không làm mất tiến trình.
  if (currentTabRecovery) {
    const reloadRes = await sendToBackground({
      action: "reloadDossierTabAttach",
      tabId: currentTabRecovery.tabId,
    });
    if (reloadRes?.error) {
      return { error: `Không tải lại được tab hiện tại để phục hồi modal: ${reloadRes.error}` };
    }
  }

  let msg = `Đã đính kèm thành công 1/1 hồ sơ.`;
  let msgType = "ok";
  if (splitRunId) {
    try {
      const stored = await chrome.storage.local.get(SPLIT_ATTACH_PROGRESS_KEY);
      const progress = stored?.[SPLIT_ATTACH_PROGRESS_KEY];
      const presentation = progress?.runId === splitRunId ? splitProgressPresentation(progress) : null;
      msg = presentation?.message || (currentTabRecovery
        ? `Đang xử lý hồ sơ 1/${bundles.length}…`
        : `Đã đính kèm 1/${bundles.length} hồ sơ.\nĐang xử lý hồ sơ 2/${bundles.length}…`);
      msgType = presentation?.type || "info";
    } catch (_) {
      msg = currentTabRecovery
        ? `Đang xử lý hồ sơ 1/${bundles.length}…`
        : `Đã đính kèm 1/${bundles.length} hồ sơ.\nĐang xử lý hồ sơ 2/${bundles.length}…`;
      msgType = "info";
    }
  }
  if (planRes?.errors?.length) console.warn("[AutoFill-Attach] Cảnh báo xử lý:", planRes.errors);
  if (!currentTabRecovery) await showPageToast("Đã đính kèm xong hồ sơ hiện tại.", "success");
  return {
    ok: true,
    message: msg,
    warn: msgType === "warn",
    inProgress: msgType === "info",
    requestId: planRes?.requestId,
  };
}

// ===== BƯỚC CHẤP THUẬN XỬ LÝ DỮ LIỆU (PDPL) =====
// Mỗi PHIÊN đồng ý 1 lần: gate ở ocrBtn/attachStepBtn. Đồng ý → BE lưu bằng chứng PDF → view-result
// (CHƯA fill) → "Về màn hình" → bấm lại mới điền thật. Reset khi "Tạo phiên mới".
const CONSENT_VERSION = "v1.1";
// 2 kho grants: (1) theo PHIÊN/tab — reset khi "Tạo phiên mới"; (2) theo NGƯỜI (CCCD) — TOÀN CỤC, BỀN
// qua phiên vì consent gắn theo (người + thủ tục): cùng CCCD làm lại đúng thủ tục thì không hỏi lại.
const CONSENT_KEY = "autofill_consent_" + (EMBEDDED_TAB_ID ?? "popup");
const CONSENT_CCCD_KEY = "autofill_consent_cccd";
const CONSENT_STATEMENTS = [
  "Tôi đã đọc, hiểu phạm vi giấy tờ, thông tin được xử lý và mục đích nêu trên; đồng ý cho Trợ lý hồ sơ HCC đọc, xử lý và tự động điền dữ liệu vào biểu mẫu.",
  "Tôi xác nhận tự chịu trách nhiệm về tính chính xác, hợp pháp của các thông tin nêu trên và về việc thực hiện thủ tục hành chính của mình.",
];
// Mục TÙY CHỌN (không chặn nút Đồng ý): xin lưu data lần xử lý khi điền lỗi để tối ưu hệ thống.
const CONSENT_OPTIMIZE_STATEMENT =
  "Khi hệ thống điền bị lỗi hoặc thiếu sót, tôi đồng ý cho Trợ lý lưu lại dữ liệu của lần xử lý này để phân tích, cải thiện và tối ưu hệ thống.";
const CONSENT_DOCS = [
  "Giấy tờ tùy thân (căn cước công dân/căn cước) của người liên quan trong hồ sơ",
  "Giấy tờ hộ tịch, giấy tờ phù hợp với thủ tục đang thực hiện",
  "Các tài liệu khác bạn chủ động tải lên cho hồ sơ này",
];
// Consent theo (người + thủ tục): key = "cccd:<CCCD tài khoản VNeID>|<mã thủ tục>" (bền qua phiên), hoặc
// "session|<mã thủ tục>" khi cổng không đọc được CCCD (reset khi "Tạo phiên mới").
let consentGrants = {};            // { "<key>": { logId, at } }
let currentConsentContext = null;  // {key, principal, proc} của lượt đang xét — acceptConsent lưu đúng key

const csViews = {
  main: document.getElementById("view-main"),
  consent: document.getElementById("view-consent"),
  result: document.getElementById("view-result"),
  legal: document.getElementById("view-legal"),
};
function showView(which) {
  for (const [k, el] of Object.entries(csViews)) if (el) el.hidden = k !== which;
}
// Đọc danh tính tài khoản VNeID trên cổng → dựng consent key (người + thủ tục). Đọc không ra CCCD →
// key theo phiên. Không throw: cổng lạ/không có content script → principal null → fallback phiên.
async function resolveConsentContext() {
  let principal = null;
  try {
    const r = await sendToContent({ action: "getPortalPrincipal" });
    principal = r?.principal || null;
  } catch (e) { /* cổng không đọc được → fallback phiên */ }
  const proc = currentConfig()?.key || selectedProcedureKey || "";
  const base = principal && principal.cccd ? "cccd:" + principal.cccd : "session";
  return { key: base + "|" + proc, principal, proc };
}
// Nút đang chờ chạy tiếp sau khi đồng ý (ocrBtn/attachStepBtn/fillAllBtn). Đồng ý xong → về màn chính
// rồi tự bấm lại đúng nút này để "đồng ý phát chạy luôn", không qua màn trung gian.
let pendingConsentTrigger = null;
// Chốt chặn PDPL: (người/phiên + thủ tục) này đã đồng ý → cho qua; chưa → nhớ nút + context, mở điều khoản.
async function requireConsent(triggerEl) {
  // Một số luồng chỉ xử lý file hoàn toàn tại extension và được registry miễn consent riêng.
  // Dùng cờ BE để không vô tình miễn consent cho mọi thủ tục đính kèm local về sau.
  if (currentConfig()?.skipConsent === true) {
    currentConsentContext = null;
    pendingConsentTrigger = null;
    return true;
  }
  const ctx = await resolveConsentContext();
  currentConsentContext = ctx;
  if (consentGrants[ctx.key]) return true;
  pendingConsentTrigger = triggerEl || null;
  openConsent();
  return false;
}
function escapeConsent(s) { const d = document.createElement("div"); d.textContent = String(s || ""); return d.innerHTML; }

async function restoreConsent() {
  consentGrants = {};
  try {
    const r = await chrome.storage.local.get([CONSENT_KEY, CONSENT_CCCD_KEY]);
    const byCccd = r && r[CONSENT_CCCD_KEY];   // grants theo người (bền)
    const sess = r && r[CONSENT_KEY];          // grants theo phiên/tab
    if (byCccd && typeof byCccd === "object") Object.assign(consentGrants, byCccd);
    // Bỏ qua bản cũ (lưu 1 flag {granted,...}); chỉ nhận map key mới.
    if (sess && typeof sess === "object" && !("granted" in sess)) Object.assign(consentGrants, sess);
  } catch (e) { consentGrants = {}; }
}
async function clearConsent() {
  // "Tạo phiên mới": chỉ xoá grants theo PHIÊN; GIỮ grants theo CCCD (nhớ theo người + thủ tục).
  for (const k of Object.keys(consentGrants)) if (!k.startsWith("cccd:")) delete consentGrants[k];
  try { await chrome.storage.local.remove(CONSENT_KEY); } catch (e) { /* ignore */ }
}
async function persistConsent() {
  // Tách kho: cccd:* → key toàn cục bền; còn lại (session:*) → key theo tab.
  const sess = {};
  const byCccd = {};
  for (const [k, v] of Object.entries(consentGrants)) {
    if (k.startsWith("cccd:")) byCccd[k] = v; else sess[k] = v;
  }
  try {
    await chrome.storage.local.set({ [CONSENT_KEY]: sess, [CONSENT_CCCD_KEY]: byCccd });
  } catch (e) { /* ignore */ }
}

function openConsent() {
  const label = (currentConfig() && currentConfig().label) || "";
  const procName = document.getElementById("consentProcName");
  if (procName) procName.textContent = label ? `“${label}”` : "của thủ tục này";
  const list = document.getElementById("consentDocList");
  if (list) list.innerHTML = CONSENT_DOCS.map((d) => `<li>${escapeConsent(d)}</li>`).join("");
  const c0 = document.getElementById("consentC0"), c1 = document.getElementById("consentC1"), c2 = document.getElementById("consentC2");
  if (c0) c0.checked = false;
  if (c1) c1.checked = false;
  if (c2) c2.checked = false;
  document.getElementById("consentErr")?.remove(); // bỏ lỗi cũ (nếu lần trước upload lỗi)
  syncConsent();
  showView("consent");
}
function syncConsent() {
  const a = document.getElementById("consentC0")?.checked;
  const b = document.getElementById("consentC1")?.checked;
  const c = document.getElementById("consentC2")?.checked; // TÙY CHỌN, không chặn nút Đồng ý
  const accept = document.getElementById("consentAcceptBtn");
  if (accept) accept.disabled = !(a && b); // chỉ 2 mục bắt buộc mới quyết định
  const sa = document.getElementById("consentSelectAll");
  if (sa) { if (a && b && c) { sa.textContent = "✓ Đã chọn tất cả"; sa.disabled = true; } else { sa.textContent = "Chọn tất cả"; sa.disabled = false; } }
}
function selectAllConsent() {
  const c0 = document.getElementById("consentC0"), c1 = document.getElementById("consentC1"), c2 = document.getElementById("consentC2");
  if (c0) c0.checked = true;
  if (c1) c1.checked = true;
  if (c2) c2.checked = true;
  syncConsent();
}
function consentStamp() {
  const d = new Date(), p = (n) => String(n).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())} ${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}`;
}
function newConsentLogId() { return "HS-C" + String(Math.floor(10000 + Math.random() * 90000)); } // HS-C + 5 số
function setConsentError(msg) {
  let box = document.getElementById("consentErr");
  if (!box) {
    box = document.createElement("div");
    box.id = "consentErr"; box.className = "cs-msg warn"; box.style.margin = "0 0 8px";
    const actions = document.querySelector("#view-consent .cs-actions");
    if (actions) actions.insertBefore(box, actions.firstChild);
  }
  box.textContent = msg;
}

async function acceptConsent() {
  const accept = document.getElementById("consentAcceptBtn");
  if (accept && accept.disabled) return;
  const cfg = currentConfig();
  const logId = newConsentLogId();
  const at = consentStamp();
  const optimize = !!document.getElementById("consentC2")?.checked;
  // Ghi vào bằng chứng ĐÚNG những gì đã tick: 2 mục bắt buộc + mục tối ưu nếu người dùng chọn.
  const statements = optimize ? [...CONSENT_STATEMENTS, CONSENT_OPTIMIZE_STATEMENT] : [...CONSENT_STATEMENTS];
  // Context (key + principal) do requireConsent tính khi mở điều khoản; nếu thiếu thì tính lại tại đây.
  const ctx = currentConsentContext || await resolveConsentContext();
  if (accept) { accept.disabled = true; accept.textContent = "Đang ghi nhận…"; }
  try {
    // Chỉ khi BE lưu bằng chứng THÀNH CÔNG mới coi phiên là đã đồng ý.
    await api.saveConsent({
      logId, version: CONSENT_VERSION,
      procedure: cfg?.key || "", procedureLabel: cfg?.label || "",
      statements, optimize, at,
      principalCccd: ctx?.principal?.cccd || null,   // chủ thể dữ liệu (VNeID) — ghi vào biên bản
      principalName: ctx?.principal?.name || null,
    });
  } catch (e) {
    if (accept) { accept.disabled = false; accept.textContent = "Đồng ý và tự động điền"; }
    if (e.unauthorized) { await AuthStore.clearTokens(); setStatus("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", "err"); showLogin(); return; }
    console.warn("[Popup] Lưu bằng chứng chấp thuận lỗi:", e);
    setConsentError("Không lưu được bằng chứng chấp thuận. Vui lòng thử lại.");
    return;
  }
  if (accept) accept.textContent = "Đồng ý và tự động điền";
  // Đánh dấu ĐÚNG key (người/phiên + thủ tục) này đã đồng ý — lần sau cùng key sẽ không hỏi lại.
  consentGrants[ctx.key] = { logId, at };
  await persistConsent();
  // Đồng ý xong → về thẳng màn chính và CHẠY LUÔN hành động đang chờ (không qua màn "đã ghi nhận").
  showView("main");
  const trigger = pendingConsentTrigger;
  pendingConsentTrigger = null;
  if (trigger) trigger.click(); // gate giờ đã pass (granted=true) → handler chạy tiếp OCR/điền/đính kèm
}
function declineConsent() {
  const inner = document.getElementById("consentResultInner");
  if (inner) inner.innerHTML =
    `<div class="cs-msg warn"><b>✍️ Bạn đã chọn không cho Trợ lý xử lý giấy tờ.</b><br>Các trường sẽ ở chế độ <b>tự nhập thủ công</b>. Bạn có thể quay lại và đồng ý bất cứ lúc nào để dùng tự động điền.</div>`;
  showView("result");
}

document.getElementById("consentC0")?.addEventListener("change", syncConsent);
document.getElementById("consentC1")?.addEventListener("change", syncConsent);
document.getElementById("consentSelectAll")?.addEventListener("click", selectAllConsent);
document.getElementById("consentAcceptBtn")?.addEventListener("click", acceptConsent);
document.getElementById("consentDeclineBtn")?.addEventListener("click", declineConsent);
document.getElementById("consentBackBtn")?.addEventListener("click", () => showView("main"));
document.getElementById("consentLegalBtn")?.addEventListener("click", () => showView("legal"));
document.getElementById("consentLegalBack")?.addEventListener("click", () => showView("consent"));

// ===== OCR & điền =====
ocrBtn.addEventListener("click", async () => {
  if (window.__AUTOFILL_HCC_POPUP_BUSY__) return;
  // Chốt chặn PDPL phải đứng TRƯỚC bước mở hồ sơ của cổng doanh nghiệp.
  //
  // Bấm nút khi chưa vào khối dữ liệu là lệnh "mở hồ sơ": wizard chạy 3 bước rồi trang tải lại,
  // panel dựng lại và TỰ bấm nút này lần nữa để quét. Nếu hỏi đồng ý sau bước mở hồ sơ thì màn
  // điều khoản chỉ hiện ở lượt tự bấm đó — tức là cán bộ đã bị đưa vào hồ sơ rồi mới được hỏi.
  // Hỏi trước thì trình tự đúng như nghiệp vụ yêu cầu: đồng ý → vào hồ sơ → quét và điền.
  // Khoá đồng ý là (người/phiên + thủ tục) và restoreConsent() giữ qua reload, nên lượt tự bấm
  // sau khi vào hồ sơ không bị hỏi lại.
  if (!(await requireConsent(ocrBtn))) return;
  // Cổng ĐKKD qua mạng: trước khối dữ liệu hồ sơ còn wizard 3 bước (loại đăng ký → loại hình →
  // Bắt đầu). Bấm nút này CHÍNH LÀ lệnh vào hồ sơ; chưa vào tới nơi thì mở hồ sơ rồi dừng lượt —
  // chưa có form để điền nên gọi backend lúc này chỉ tốn lượt OCR.
  if (await startEnterpriseDossierIfNeeded()) return;
  // Kiểm file SAU bước mở hồ sơ: khi chưa vào khối dữ liệu, lượt bấm này là lệnh MỞ HỒ SƠ nên
  // vẫn phải chạy được dù cán bộ chưa đính giấy tờ nào.
  if (!files.length) {
    setStatus("Chưa có file nào.", "err");
    return;
  }
  // Cổng DVC quốc gia còn chặn một modal "Thông tin chung" trước bước kê khai — bấm hộ rồi mới
  // quét. Chưa qua được thì dừng lượt bấm, KHÔNG gọi backend cho phí lượt OCR.
  if (!(await passInfoModalIfAny())) return;
  window.__AUTOFILL_HCC_POPUP_BUSY__ = true;
  ocrBtn.disabled = true;
  clearReviewCard(); // xoá card rà soát của lần trước trước khi chạy lại
  hideSupportCode(); // ẩn mã hỗ trợ của lượt trước tới khi có kết quả mới
  refreshAttachStepUI();
  try {
    setStatus("Đang đọc file...", "info");
    await ensureSelectedFilesLoaded();

    // Nhận diện lại thủ tục theo TRANG HIỆN TẠI ngay trước khi gửi (tránh dùng thủ tục cũ bị khóa
    // stale từ trang trước khi đổi trang/đăng nhập lại trong cùng tab).
    await autoDetectProcedure({ clearChoiceSelection: false });
    if (!selectedProcedureKey) {
      setStatus("Chưa chọn thủ tục. Hãy tìm & chọn thủ tục, hoặc mở đúng trang biểu mẫu rồi thử lại.", "err");
      return;
    }

    const cfg = currentConfig();
    const payloadFiles = buildPayloadFiles();
    const options = {};
    // Bắc Ninh 3 bước: bước quét đầu là đọc ĐƠN đăng ký (registration_form).
    if (isBacNinhThreeStepProcedure(cfg)) options.purpose = "registration_form";
    if (cfg.useDangKyBy) options.dangKyBy = dangKyBySelect.value;
    if (cfg.useRequestMode) options.requestMode = requestModeSelect.value;
    let page = null;
    if (currentBusinessPages().length) {
      // Tự nhận trang đang mở từ breadcrumb (đã bỏ nút chọn trang thủ công).
      const det = await sendToContent({ action: "detectBusinessPage" });
      const key = det && !det.error ? det.pageKey : null;
      if (!key) {
        setStatus("Chưa nhận diện được trang đăng ký kinh doanh đang mở. Hãy mở đúng trang biểu mẫu rồi thử lại.", "err");
        return;
      }
      page = currentBusinessPages().find((p) => p.key === key) || { key, label: det.label || key };
      options.page = key;
      options.businessPage = key;
    }

    if (isAttachMode()) {
      const attachRes = await runAttachmentPlanForCurrentFiles(options);
      showSupportCode(attachRes?.requestId);
      if (attachRes?.error) setStatus(attachRes.error, "err");
      else setStatus(attachRes.message, attachRes.warn ? "warn" : (attachRes.inProgress ? "info" : "ok"));
      return;
    }

    // Các thủ tục cần đối chiếu người yêu cầu cổng đã điền sẵn (VNeID) với CCCD upload.
    if (
      cfg.key === "ho-tro-mai-tang" ||
      cfg.key === "ho-tro-mai-tang-huu-tri-xa-hoi" ||
      cfg.key === "dieu-chinh-huu-tri-xa-hoi" ||
      cfg.key === "mai-tang-dan-cong-hoa-tuyen" ||
      cfg.key === "xac-nhan-tinh-trang-hon-nhan" ||
      cfg.key === "khai-sinh-dang-ky-lai" ||
      cfg.key === "khai-sinh-ket-hop-nhan-cha-me-con" ||
      cfg.key === "khai-tu" ||
      cfg.key === "khai-tu-dang-ky-lai" ||
      cfg.key === "thay-doi-cai-chinh-ho-tich" ||
      cfg.key === "trich-luc-ks" ||
      cfg.key === "xet-tuyen-vien-chuc" ||
      cfg.key === "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham" ||
      cfg.key === "cap-lai-giay-chung-nhan-du-dieu-kien-an-toan-thuc-pham" ||
      cfg.key === "dinh-chinh-sai-sot-lam-dong" ||
      cfg.key === "giai-quyet-che-do-khang-chien" ||
      cfg.key === "di-chuyen-ho-so-nguoi-huong-tro-cap" ||
      cfg.key === "sua-doi-thong-tin-ho-so-nguoi-co-cong" ||
      cfg.key === "tro-cap-xa-hoi-hang-thang" ||
      cfg.key === "xac-dinh-muc-do-khuyet-tat" ||
      cfg.key === "cap-gcn-attp-nong-lam-thuy-san" ||
      cfg.key === "cap-moi-giay-phep-hanh-nghe-chuyen-tiep" ||
      cfg.key === "cap-chung-chi-hanh-nghe-duoc" ||
      cfg.key === "cap-van-ban-chap-thuan-tau-ca" ||
      cfg.key === "cap-giay-phep-khai-thac-thuy-san" ||
      cfg.key === "dang-ky-bien-phap-bao-dam-qsdd" ||
      cfg.key === "xoa-dang-ky-tau-ca" ||
      cfg.key === "xoa-dang-ky-phuong-tien-thuy" ||
      cfg.key === "dang-ky-bien-dong-dat-dai-da-nang" ||
      cfg.key === "cap-gcn-so-nha-da-nang" ||
      cfg.key === "xac-nhan-ho-so-so-nha-da-nang" ||
      cfg.key === "cap-phep-long-duong-via-he" ||
      cfg.key === "cap-giay-phep-chat-ha-cay-xanh" ||
      cfg.key === "cap-ban-sao-van-bang-so-goc" ||
      cfg.key === "chap-thuan-dau-noi-tam" ||
      // [Bắc Ninh] Điền thông tin tài khoản: cổng prefill Họ tên + Số định danh (VNeID) → mốc chọn người.
      cfg.key === "dien-thong-tin-tai-khoan-bac-ninh"
    ) {
      const ctxRes = await sendToContent({ action: "collectFormContext" });
      if (ctxRes?.formContext) options.formContext = ctxRes.formContext;
      if (
        cfg.key === "khai-sinh-ket-hop-nhan-cha-me-con" &&
        (
          !["birth_registration", "parent_child_recognition"].includes(options.formContext?.formVariant) ||
          !Array.isArray(options.formContext?.formSignature) ||
          options.formContext.formSignature.length !== 3
        )
      ) {
        setStatus(
          "Không nhận diện được mẫu khai sinh hoặc mẫu nhận cha, mẹ, con đang mở. Hãy mở đúng eForm rồi thử lại.",
          "err"
        );
        return;
      }
    }

    setStatus(page
      ? `Đang xử lý trang "${page.label}" trên máy chủ...`
      : "Đang xử lý trên máy chủ (OCR + trích trường)...",
      "info"
    );
    // Toggle "Người nộp = chủ hồ sơ": bỏ so khớp mỏ neo UI (BE thủ tục nào hỗ trợ mới honor).
    if (submitterOwnerMode) options.submitterMode = "owner_as_submitter";
    if (cfg.hasAttachmentStep) {
      lastProcessSession = null;
      refreshAttachStepUI();
    }
    const res = await api.process({ procedure: cfg.key, options, files: payloadFiles });
    console.log("[BE]", { extracted: res.extracted, stats: res.stats });
    lastProcessSession = res.sessionId ? { procedure: cfg.key, sessionId: res.sessionId } : null;
    showSupportCode(res.requestId || res.sessionId);

    await dispatchFill(res.fields || [], res.errors || [], page);

    // Rà soát bbox: thủ tục bật review → nạp sources + đẩy xuống content + hiện card "Xem trên ảnh".
    try { await maybeShowReview(res.requestId || res.sessionId, res.reviewToken); }
    catch (err) { console.warn("[AutoFill] review:", err); }
  } catch (e) {
    if (e.unauthorized) {
      await AuthStore.clearTokens();
      setStatus("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", "err");
      showLogin();
    } else {
      console.warn("[AutoFill] Quét & nhập dữ liệu lỗi:", e);
      setStatus(e, "err");   // map theo mã lỗi BE / status; text kỹ thuật bị lược
    }
  } finally {
    window.__AUTOFILL_HCC_POPUP_BUSY__ = false;
    ocrBtn.disabled = false;
    refreshAttachStepUI();
  }
});

// ===== Fill TẤT CẢ 8 trang đăng ký kinh doanh: 1 lần OCR/LLM → extension tự lặp fill→lưu→sang trang =====
if (fillAllBtn) {
  fillAllBtn.addEventListener("click", async () => {
    if (window.__AUTOFILL_HCC_POPUP_BUSY__) return;
    // Chốt chặn PDPL đứng TRƯỚC bước mở hồ sơ — xem chú thích cùng chỗ ở nút "Quét và nhập dữ liệu":
    // phải đồng ý điều khoản rồi mới vào hồ sơ, không phải vào hồ sơ rồi mới được hỏi.
    if (!(await requireConsent(fillAllBtn))) return;
    // Cổng ĐKKD qua mạng: khai "pages" nên panel hiện nút này thay cho "Quét và nhập dữ liệu".
    // Chưa vào khối dữ liệu thì lượt bấm này là lệnh MỞ HỒ SƠ (wizard 3 bước), chưa quét.
    if (await startEnterpriseDossierIfNeeded()) return;
    window.__AUTOFILL_HCC_POPUP_BUSY__ = true;
    fillAllBtn.disabled = true;
    // Lượt mới phải bỏ mã cũ trước khi gọi BE. Mã mới chỉ lấy từ /process (fill),
    // tuyệt đối không thay bằng requestId của /attachments/plan chạy ngay sau đó.
    businessFillSupportCode = "";
    hideSupportCode();
    try {
      setStatus("Đang đọc file...", "info");
      await ensureSelectedFilesLoaded();
      // Ghi trạng thái đã xóa mã cũ ngay trong phiên hiện tại. Nếu /process lỗi hoặc người dùng
      // reload thủ công, panel không được khôi phục nhầm mã của hồ sơ trước.
      await saveSession();
      await autoDetectProcedure({ clearChoiceSelection: false });
      const cfg = currentConfig();
      if (!currentBusinessPages().length) {
        setStatus("Chỉ dùng cho thủ tục đăng ký kinh doanh.", "err");
        return;
      }
      const payloadFiles = buildPayloadFiles();
      if (!payloadFiles.length) {
        setStatus("Chưa có file để quét.", "err");
        return;
      }
      const options = { page: "__all__", allPages: true };
      const isAmendmentWorkflow = !!cfg.businessWorkflow;
      if (isAmendmentWorkflow) {
        const detected = await sendToContent({ action: "detectBusinessChangeStage" });
        if (!detected || detected.stage === "unknown") {
          setStatus("Trang hiện tại không thuộc luồng nghiệp vụ hộ kinh doanh đã chọn. Hãy mở đúng hồ sơ rồi chạy lại.", "err");
          return;
        }
        options.businessStage = detected.stage;
        // Pipeline thay đổi tự quyết định page theo nội dung hồ sơ, không chạy đủ 8 trang.
        delete options.allPages;
        options.page = `__${cfg.businessWorkflow}__`;
      }

      setStatus(" Đang phân tích tài liệu...", "info");
      const res = await api.process({ procedure: cfg.key, options, files: payloadFiles });
      console.log("[BE fill-all]", { extracted: res.extracted, stats: res.stats });
      businessFillSupportCode = String(res.requestId || res.sessionId || "").trim();
      showSupportCode(businessFillSupportCode);
      // Ghi trước khi content bắt đầu state machine: các postback sẽ phá iframe/popup hiện tại.
      await saveSession();
      const pages = res.pages || {};
      if (!Object.keys(pages).length) {
        setStatus(isAmendmentWorkflow
          ? "Backend không xác định được trang thay đổi/người nộp từ hồ sơ. Kiểm tra lại tài liệu."
          : "Backend không trả dữ liệu 8 trang. Kiểm tra lại.", "err");
        return;
      }
      if (isAmendmentWorkflow && (!res.businessFlow || res.businessFlow.workflow !== cfg.businessWorkflow)) {
        setStatus("Backend chưa trả đúng metadata luồng nghiệp vụ hộ kinh doanh.", "err");
        return;
      }
      const businessSearch = res.businessFlow?.search || res.extracted?.businessSearch || null;
      if (isAmendmentWorkflow) {
        console.log("[HKD businessFlow]", JSON.stringify({
          workflow: res.businessFlow?.workflow,
          search: businessSearch,
          pageOrder: res.businessFlow?.pageOrder,
        }));
      }

      // Gộp bước đính kèm: lấy kế hoạch đính kèm cho CÙNG bộ file để tự đính kèm sau khi điền xong 8 trang.
      let attachPayload = null;
      try {
        setStatus("Đang phân tích & phân loại tài liệu đính kèm...", "info");
        const attachFiles = await toPdfForAttach(payloadFiles);
        const planRes = await api.attachmentPlan({ procedure: cfg.key, options: {}, files: attachFiles });
        console.log("[BE AttachmentPlan][HKD merged]", { attachments: planRes.attachments, errors: planRes.errors });
        const attachments = planRes.attachments || [];
        if (attachments.length) attachPayload = { files: attachFiles, attachments };
        else console.warn("[HKD] Không có kế hoạch đính kèm — chỉ điền 8 trang:", planRes.errors);
      } catch (e) {
        console.warn("[HKD] Lỗi lấy kế hoạch đính kèm — chỉ điền 8 trang:", e?.message || e);
      }

      // Cổng ĐKKD qua mạng có engine điền RIÊNG (content/procedures/enterprise-registration.js):
      // menu trang, nút Lưu và id control khác hẳn HkdOnline nên không dùng chung state machine.
      const startRes = await sendToContent({
        action: cfg.enterprisePortal
          ? "startEnterpriseFillAll"
          : (isAmendmentWorkflow ? "startChangeBusiness" : "startFillAllBusiness"),
        // Gửi kèm dữ liệu wizard để engine tự mở hồ sơ nếu lượt bấm này rơi vào lúc còn ở wizard
        // (lưới đỡ cho bước tiền kiểm getEnterpriseStage).
        enterpriseFlow: cfg.enterprisePortal ? {
          registrationType: "NEW",
          registrationLabel: "Thành lập mới",
          entityLabel: cfg.enterpriseEntityLabel || "",
          entityValue: cfg.enterpriseEntityValue || "",
          procedureKey: cfg.key,
          procedureLabel: cfg.label,
        } : null,
        pages,
        businessFlow: res.businessFlow || null,
        businessSearch,
        attachPayload,
        businessDefaults: buildBusinessDefaults(currentUser),
      });
      if (startRes?.error) {
        setStatus(startRes.error, "err");
        return;
      }
      if (startRes?.openingDossier) {
        // Chặng mở hồ sơ đang chạy trên cổng; panel sẽ tự quét tiếp khi tới khối dữ liệu.
        await setEnterprisePendingFill(cfg.key);
        setStatus("", "");
        return;
      }
      if (isAmendmentWorkflow) {
        const pageCount = res.businessFlow.pageOrder?.length || Object.keys(pages).length;
        setStatus(attachPayload
          ? `Đang tiếp tục từ bước hiện tại, sửa ${pageCount} trang cần thiết rồi tự đính kèm. Đừng thao tác trên trang.`
          : `Đang tiếp tục từ bước hiện tại và sửa ${pageCount} trang cần thiết. Đừng thao tác trên trang.`, "ok");
      } else {
        setStatus(attachPayload
          ? "Đang tự điền & lưu 8 trang rồi TỰ ĐÍNH KÈM. Đừng thao tác trên trang cho tới khi xong."
          : "Đang tự điền & lưu lần lượt 8 trang. Đừng thao tác trên trang cho tới khi xong.", "ok");
      }
    } catch (e) {
      if (e.unauthorized) {
        await AuthStore.clearTokens();
        setStatus("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", "err");
        showLogin();
      } else {
        console.warn("[AutoFill] Điền & lưu 8 trang lỗi:", e);
        setStatus(e, "err");
      }
    } finally {
      window.__AUTOFILL_HCC_POPUP_BUSY__ = false;
      fillAllBtn.disabled = false;
    }
  });
}

if (attachStepBtn) {
  attachStepBtn.addEventListener("click", async () => {
    if (window.__AUTOFILL_HCC_POPUP_BUSY__) return;
    await autoDetectProcedure({ clearChoiceSelection: false }); // giữ lựa chọn tay ở màn HKD dùng chung
    const cfg = currentConfig();
    if (!cfg.hasAttachmentStep) {
      setStatus("Thủ tục này chưa có bước đính kèm tự động.", "err");
      return;
    }
    if (!files.length) {
      setStatus("Chưa có file nào để đính kèm.", "err");
      return;
    }
    // Chốt chặn PDPL: đính kèm cũng xử lý dữ liệu → cần đồng ý trong phiên (đồng ý xong tự chạy lại).
    if (!(await requireConsent(attachStepBtn))) return;

    window.__AUTOFILL_HCC_POPUP_BUSY__ = true;
    if (ocrBtn) ocrBtn.disabled = true;
    attachStepBtn.disabled = true;
    hideSupportCode(); // ẩn mã hỗ trợ của lượt trước tới khi có kết quả mới
    try {
      setStatus("Đang đọc file...", "info");
      await ensureSelectedFilesLoaded();
      // Bắc Ninh 3 bước: bước đính kèm phải mở đúng tab "Thành phần hồ sơ" trước.
      if (isBacNinhThreeStepProcedure(cfg)) {
        const tabRes = await sendToContent({ action: "openBacNinhTab", tabName: "taithanhphan" });
        if (tabRes?.error) throw new Error(tabRes.error);
      }
      // Không bắt buộc đã process bước 2: nếu có session đúng thủ tục thì truyền để backend dùng hint,
      // không có thì vẫn đính kèm bình thường (planner xử lý session=None).
      const sid = lastProcessSession?.procedure === cfg.key ? lastProcessSession.sessionId : null;
      const res = await runAttachmentPlanForCurrentFiles(sid ? { sessionId: sid } : {});
      showSupportCode(res?.requestId);
      if (res?.error) {
        console.warn("[Popup] Attach step failed", res);
        setStatus(res.error, "err");
      } else {
        setStatus(res.message, res.warn ? "warn" : "ok");
      }
    } catch (e) {
      if (e.unauthorized) {
        await AuthStore.clearTokens();
        setStatus("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", "err");
        showLogin();
      } else {
        console.warn("[AutoFill] Đính kèm lỗi:", e);
        setStatus(e, "err");
      }
    } finally {
      window.__AUTOFILL_HCC_POPUP_BUSY__ = false;
      if (ocrBtn) ocrBtn.disabled = false;
      refreshAttachStepUI();
    }
  });
}

function hasMeaningfulFieldValue(field) {
  if (!field || field.default === true) return false;
  const value = field.value;
  if (value == null) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") return Object.keys(value).length > 0;
  return true; // số 0 và boolean false vẫn là giá trị hợp lệ
}

function hasUsableProcessData(fields) {
  return Array.isArray(fields) && fields.some(hasMeaningfulFieldValue);
}

function safeFieldCodes(values) {
  return [...new Set((Array.isArray(values) ? values : [])
    .map((value) => String(value || "").trim())
    .filter((value) => value && value.length <= 80 && /^[\p{L}\p{N}_$.[\]-]+$/u.test(value)))]
    .slice(0, 12);
}

function buildFillDetails(fillRes, processErrors, totalFields) {
  const details = [];
  const filled = Math.max(0, Number(fillRes?.filled || 0));
  const notFound = safeFieldCodes(fillRes?.notFound);
  const fillErrors = Array.isArray(fillRes?.errors) ? fillRes.errors : [];
  const extractWarnings = Array.isArray(processErrors) ? processErrors : [];
  if (filled < totalFields) details.push(`Có ${Math.max(0, totalFields - filled)} thông tin chưa được điền.`);
  if (notFound.length) details.push(`Mã ô hỗ trợ: ${notFound.join(", ")}.`);
  if (fillErrors.length) details.push(`Có ${fillErrors.length} cảnh báo khi điền biểu mẫu.`);
  if (extractWarnings.length) details.push(`Có ${extractWarnings.length} cảnh báo khi đọc hồ sơ.`);
  return details;
}

async function dispatchFill(allFields, errors, page = null) {
  // errors[] từ BE có thể chứa chi tiết OCR/LLM kỹ thuật → chỉ log, KHÔNG hiện thô lên UI.
  if (errors && errors.length) console.warn("[AutoFill] Cảnh báo trích xuất:", errors);
  if (!hasUsableProcessData(allFields)) {
    const details = Array.isArray(errors) && errors.length
      ? [`Có ${errors.length} cảnh báo khi đọc hồ sơ.`]
      : [];
    setStatus("Không đọc được thông tin từ giấy tờ. Kiểm tra lại ảnh/tệp rồi thử lại.", "err", details);
    return { ok: false, reason: "no-usable-data", filled: 0 };
  }
  setStatus(page
    ? `Đang điền dữ liệu vào trang "${page.label}"...`
    : "Đang điền dữ liệu vào biểu mẫu...",
    "info"
  );
  const procedure = currentConfig()?.key || "";
  let panelMinimized = false;
  try {
    // Bắc Ninh 3 bước: trước khi điền phải mở đúng tab "Nhập đơn đăng ký".
    if (BAC_NINH_THREE_STEP_PROCEDURES.has(procedure)) {
      const tabRes = await sendToContent({ action: "openBacNinhTab", tabName: "nhapdondangky" });
      if (tabRes?.error) {
        setStatus(tabRes.error, "err");
        return { ok: false, reason: "registration-tab-unavailable", filled: 0 };
      }
    }
    // Trang có thể reload ngay sau khi cán bộ bấm sang bước đính kèm. Chốt session trước khi ẩn
    // iframe để panel mới luôn dựng lại được đúng file, kể cả lượt save từ input còn đang chạy.
    const sessionSaved = await saveSession();
    if (sessionSaved === false) {
      console.warn("[AutoFill] Điền tiếp nhưng phiên file chưa được lưu bền vững", {
        procedure,
        fileCount: files.length,
      });
    }
    // Chỉ ẩn SAU khi BE đã trả dữ liệu dùng được, nhưng TRƯỚC khi content bắt đầu điền DOM.
    const panelRes = await sendToContent({ action: "minimizePanelForFill", procedure });
    panelMinimized = !!panelRes?.minimized;
    if (panelRes?.error) console.warn("[AutoFill] Không thu nhỏ được panel trước khi điền:", panelRes.error);

    const fillRes = await sendToContent({
      action: "fillFields",
      fields: allFields,
      procedure,
      businessPage: page?.key || "",
      // Mọi trang HKD đều cần defaults theo địa bàn (ghi chú ngành nghề, lý do giải thể, địa chỉ
      // nhận kết quả...), không riêng trang ngành nghề như trước.
      businessDefaults: page?.key ? buildBusinessDefaults(currentUser) : null,
    });
    const filled = Math.max(0, Number(fillRes?.filled || 0));
    const details = buildFillDetails(fillRes, errors, allFields.length);
    if (fillRes?.error || filled === 0) {
      console.warn("[AutoFill] Điền form lỗi:", fillRes?.error || fillRes);
      if (panelMinimized) await sendToContent({ action: "restorePanelAfterFillFailure" });
      setStatus(
        fillRes?.error || "Không điền được dữ liệu vào biểu mẫu. Vui lòng kiểm tra trang và thử lại.",
        "err",
        details
      );
      return { ok: false, reason: "fill-failed", filled: 0, details };
    }

    const hasWarnings = filled < allFields.length
      || !!fillRes?.notFound?.length
      || !!fillRes?.errors?.length
      || !!errors?.length;
    const pageSuffix = page ? ` ở trang "${page.label}"` : "";
    const message = hasWarnings
      ? `Đã điền ${filled} thông tin${pageSuffix}. Vui lòng rà soát các ô còn trống.`
      : `Đã điền ${filled} thông tin${pageSuffix}.`;
    setStatus(message, hasWarnings ? "warn" : "ok", details);
    await showPageToast(
      hasWarnings
        ? `Đã điền ${filled} thông tin. Vui lòng rà soát các ô còn trống.`
        : `Đã điền xong ${filled} thông tin.`,
      hasWarnings ? "warn" : "success"
    );
    if (panelMinimized) await sendToContent({ action: "markPanelFillComplete" });
    return { ok: true, filled, partial: hasWarnings, details };
  } catch (error) {
    console.warn("[AutoFill] Điền form lỗi:", error);
    if (panelMinimized) {
      try { await sendToContent({ action: "restorePanelAfterFillFailure" }); } catch (_) { /* ignore */ }
    }
    setStatus("Không điền được dữ liệu vào biểu mẫu. Vui lòng kiểm tra trang và thử lại.", "err");
    return { ok: false, reason: "fill-exception", filled: 0 };
  }
}

// ===== Rà soát bbox: card "Xem trên ảnh" cho từng ô AI đã điền =====
function clearReviewCard() {
  if (!reviewCardEl) return;
  reviewCardEl.hidden = true;
  reviewCardEl.innerHTML = "";
  postPanelHeight();
}

// Nạp sources theo requestId (BE trả 404 nếu thủ tục không bật review) → đẩy xuống content + render card.
async function maybeShowReview(requestId, reviewToken) {
  clearReviewCard();
  if (!requestId || !reviewToken) return;
  const sources = await api.getReviewSources(requestId, reviewToken);
  const byName = sources && sources.fields;
  if (!byName || !Object.keys(byName).length) return;
  await sendToContent({
    action: "attachSources",
    sourcesByName: byName,
    baseUrl: window.BACKEND_URL,
    requestId,
    reviewToken,
  });
  renderReviewCard(byName);
}

function renderReviewCard(byName) {
  if (!reviewCardEl) return;
  const entries = Object.entries(byName);
  const withBbox = entries.filter(([, s]) => Array.isArray(s.bbox)).length;
  reviewCardEl.innerHTML = "";

  // Thu gọn mặc định: chỉ hiện nút tiêu đề; bấm mới xổ danh sách (tránh khối dài choán panel).
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "review-card__toggle";
  toggle.setAttribute("aria-expanded", "false");
  const tLabel = document.createElement("span");
  tLabel.textContent = `🔍 Rà soát thông tin AI đã điền (${entries.length} mục, ${withBbox} có ảnh nguồn)`;
  const caret = document.createElement("span");
  caret.className = "review-card__caret";
  caret.setAttribute("aria-hidden", "true");
  caret.textContent = "▾";
  toggle.append(tLabel, caret);
  reviewCardEl.appendChild(toggle);

  const body = document.createElement("div");
  body.className = "review-card__body";
  body.hidden = true;
  toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") !== "true";
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    body.hidden = !open;
    postPanelHeight();
  });

  if (entries.length > 1) {
    const allBtn = document.createElement("button");
    allBtn.type = "button";
    allBtn.className = "review-card__all";
    allBtn.textContent = "▶ Rà soát tất cả (dùng ‹ › để lướt)";
    allBtn.addEventListener("click", () => sendToContent({ action: "reviewAll" }));
    body.appendChild(allBtn);
  }

  const list = document.createElement("ul");
  list.className = "review-card__list";
  for (const [name, src] of entries) {
    const li = document.createElement("li");
    li.className = "review-item";
    const text = document.createElement("div");
    text.className = "review-item__text";
    const lab = document.createElement("div");
    lab.className = "review-item__label";
    lab.textContent = src.label || name;
    const val = document.createElement("div");
    val.className = "review-item__value";
    val.textContent = src.value || "";
    val.title = src.value || "";
    text.append(lab, val);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "review-item__btn" + (src.bbox ? "" : " no-bbox");
    btn.textContent = src.bbox ? "Xem trên ảnh" : "Xem ảnh";
    btn.addEventListener("click", () => sendToContent({ action: "reviewField", name }));
    li.append(text, btn);
    list.appendChild(li);
  }
  body.appendChild(list);
  reviewCardEl.appendChild(body);

  reviewCardEl.hidden = false;
  postPanelHeight();
}

// ===== Auto-fit chiều cao: báo chiều cao nội dung cho panel cha (content.js) =====
function postPanelHeight() {
  if (!IS_EMBEDDED) return;
  // Đo body.scrollHeight (chiều cao NỘI DUNG thật) chứ KHÔNG dùng documentElement.scrollHeight:
  // documentElement luôn ≥ viewport iframe, nên khi panel đã cao rồi thì nó không bao giờ báo nhỏ hơn
  // → panel bị "bánh cóc" chỉ phình không co lại (thừa khoảng trắng ở cuối khi thu gọn nội dung).
  const h = Math.ceil(document.body.scrollHeight) + 2;
  parent.postMessage({ type: "autofill-hcc-resize", height: h }, "*");
}
if (IS_EMBEDDED) {
  // Panel cha có thể bị display:none trong lúc fill, khiến iframe giữ chiều cao tối thiểu.
  // Khi panel được mở lại ở bước đính kèm, đo lại theo yêu cầu thay vì chờ ResizeObserver tự phát hiện.
  window.addEventListener("message", (e) => {
    if (e.source !== window.parent || e.data?.type !== "autofill-hcc-request-resize") return;
    postPanelHeight();
  });
}
if (IS_EMBEDDED && typeof ResizeObserver !== "undefined") {
  const ro = new ResizeObserver(() => postPanelHeight());
  // Quan sát body (chiều cao nội dung) — đổi thủ tục / mở-đóng khối giấy tờ đều đổi body → báo lại panel.
  ro.observe(document.body);
  window.addEventListener("load", postPanelHeight);
}

// ===== Khởi động =====
// Các khối UI phía dưới cũng khởi tạo bất đồng bộ. Giữ Promise này để ô "Đi đến thủ tục"
// không được selectProcedure()/saveSession() trước khi file của tab đã restore xong.
const popupBootstrapReady = bootstrap();

// ===== Lịch sử cập nhật (changelog) — thuần FE, dữ liệu ở changelog.js =====
// Trigger là nút "★ Lịch sử" trên HEADER panel (content.js) → gửi postMessage vào iframe này.
(function initReleaseHistory() {
  const pop = document.getElementById("releasePopover");
  const closeBtn = document.getElementById("releaseClose");
  const list = document.getElementById("releaseList");
  if (!pop || !list) return;

  // Version hiện tại lấy TỰ ĐỘNG từ manifest → đánh dấu bản "đang dùng" trong danh sách.
  let current = "";
  try { current = (chrome.runtime.getManifest() || {}).version || ""; } catch (_) { }

  const releases = (typeof APP_RELEASES !== "undefined" && Array.isArray(APP_RELEASES)) ? APP_RELEASES : [];
  list.innerHTML = "";
  for (const r of releases) {
    const isCurrent = String(r.version) === String(current);
    const art = document.createElement("article");
    art.className = "release" + (isCurrent ? " current" : "");

    const meta = document.createElement("div");
    meta.className = "release-meta";
    const ver = document.createElement("span");
    ver.className = "release-version";
    ver.textContent = "Phiên bản " + r.version;
    meta.appendChild(ver);
    if (isCurrent) {
      const b = document.createElement("span");
      b.className = "badge-current";
      b.textContent = "ĐANG DÙNG";
      meta.appendChild(b);
    }
    if (r.date) {
      const d = document.createElement("span");
      d.className = "release-date";
      d.textContent = r.date;
      meta.appendChild(d);
    }
    art.appendChild(meta);

    const ul = document.createElement("ul");
    for (const it of (r.items || [])) {
      const li = document.createElement("li");
      li.textContent = it;
      ul.appendChild(li);
    }
    art.appendChild(ul);
    list.appendChild(art);
  }

  function setOpen(open) { pop.hidden = !open; }
  // Nút "★ Lịch sử" trên header panel (content.js) gửi message vào iframe → toggle popover.
  window.addEventListener("message", (e) => {
    if (e.data && e.data.type === "autofill-hcc-open-history") setOpen(pop.hidden);
  });
  closeBtn && closeBtn.addEventListener("click", () => setOpen(false));
  document.addEventListener("click", (e) => {
    if (!pop.hidden && !pop.contains(e.target)) setOpen(false);
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") setOpen(false); });
})();


// ===== LOCATION MANAGEMENT: Chọn tỉnh/xã =====
const provinceSelect = document.getElementById("provinceSelect");
const wardSelect = document.getElementById("wardSelect");
const locationStatus = document.getElementById("locationStatus");
const locationSection = document.getElementById("locationSection");

const LOCATION_STORAGE_KEY = "autofill_user_location";
// Cờ MỘT LẦN cho content/agency-select.js: mở trang thủ tục xong thì tự chọn Tỉnh/Xã ở khối
// "Chọn cơ quan thực hiện". Chỉ đặt khi người dùng bấm "Mở trang kê khai" → không tự động can
// thiệp khi cán bộ tự duyệt cổng bằng tay.
const AGENCY_ARM_KEY = "autofill_agency_autoselect";
// Cờ tương ứng cho content/procedures/enterprise-registration.js: thủ tục thành lập doanh nghiệp
// nộp thẳng trên dangkyquamang.dkkd.gov.vn (không qua khối "Chọn cơ quan thực hiện" của cổng QG),
// nên phần "lên đạn" là loại đăng ký + loại hình cần chọn ở wizard ba bước đầu.
const ENTERPRISE_ARM_KEY = "autofill_enterprise_autostart";
let currentLocation = { province: "", provinceSlug: "", ward: "" };

// Popup chạy trong iframe extension, KHÔNG có content/locations.js (đó là bản cho content script).
// Bản dùng ở đây là popup-locations.js → window.popupLocationManager; nhận cả hai tên cho chắc.
function locationStore() {
  return window.popupLocationManager || window.locationManager || null;
}

async function initLocationManager() {
  const store = locationStore();
  if (!store) {
    locationStatus.textContent = '✗ Chưa nạp được dữ liệu tỉnh/xã';
    locationStatus.className = 'status err';
    console.error('[Popup] Thiếu popup-locations.js — không có dữ liệu tỉnh/xã');
    return;
  }
  if (!store.loaded) {
    try {
      await store.load();
    } catch (error) {
      locationStatus.textContent = '✗ Lỗi nạp dữ liệu tỉnh/xã';
      locationStatus.className = 'status err';
      console.error('[Popup] Failed to load LocationManager:', error);
      return;
    }
  }

  // Danh sách tỉnh dựng trước; địa chỉ mặc định do applyStoredLocation() chốt (có thể phải chờ
  // /auth/me trả về nên tách riêng, gọi lại được nhiều lần).
  for (const prov of store.getProvinces()) {
    const option = document.createElement('option');
    option.value = prov.slug;
    option.textContent = prov.text;
    provinceSelect.appendChild(option);
  }
  await applyStoredLocation();

  // Event listeners — KHÔNG có nút Lưu: chọn tới đâu ghi tới đó.
  provinceSelect.addEventListener('change', (e) => {
    const slug = e.target.value;
    currentLocation.provinceSlug = slug;
    currentLocation.province = slug ? (e.target.options[e.target.selectedIndex]?.textContent || '') : '';
    currentLocation.ward = '';
    currentLocation.source = "manual";   // đã tự chọn -> đừng để mặc định tài khoản ghi đè nữa
    loadWards(slug, '');
    void persistLocation();
  });

  wardSelect.addEventListener('change', (e) => {
    currentLocation.ward = e.target.value;
    currentLocation.source = "manual";
    void persistLocation();
  });

  postPanelHeight();   // applyStoredLocation() ở trên đã đồng bộ nhãn + tóm tắt + gợi ý kê khai
}

async function persistLocation() {
  try {
    await chrome.storage.local.set({
      [LOCATION_STORAGE_KEY]: { username: currentUser?.username || "", ...currentLocation },
    });
  } catch (error) {
    locationStatus.textContent = '✗ Lỗi lưu địa chỉ';
    locationStatus.className = 'status err';
    console.error('[Popup] Failed to save location:', error);
    return;
  }
  showLocationSummary();
  refreshKeKhaiHint();
}

/**
 * Chốt địa chỉ đang dùng rồi đổ lên UI. Thứ tự ưu tiên:
 *   1. Lựa chọn cán bộ TỰ đổi (source: "manual") — không bao giờ bị ghi đè.
 *   2. Mặc định đã lưu của CHÍNH tài khoản đang đăng nhập.
 *   3. Tỉnh/xã gắn trong tài khoản (/auth/me) — giống cách tro-ly-nguoi-dan-backend seed location
 *      cho phiên chat mới (app/chat/router.py: location_for(user.tinh, user.xa)).
 * Gọi được nhiều lần: bootstrap() lấy /auth/me xong sẽ gọi lại để áp mặc định của tài khoản.
 */
async function applyStoredLocation() {
  const store = locationStore();
  if (!store?.loaded || !provinceSelect?.options.length) return;

  let stored = null;
  try { stored = (await chrome.storage.local.get(LOCATION_STORAGE_KEY))[LOCATION_STORAGE_KEY]; }
  catch (_) { /* dùng mặc định tài khoản */ }

  const keepStored = stored
    && (stored.source === "manual" || stored.username === currentUser?.username);
  const fromAccount = keepStored ? null : accountLocation(store);
  if (fromAccount) {
    currentLocation = fromAccount;
    await persistLocation();
  } else if (stored) {
    currentLocation = { ...currentLocation, ...stored };
  }

  provinceSelect.value = currentLocation.provinceSlug || "";
  loadWards(currentLocation.provinceSlug, currentLocation.ward);
  showLocationSummary();
  syncDestCombos();
  refreshKeKhaiHint();
}

/**
 * Đăng xuất -> QUÊN lựa chọn tỉnh/xã đã lưu (kể cả "manual"). Nhờ vậy phiên đăng nhập SAU (kể cả
 * cùng tài khoản) sẽ seed lại tỉnh/xã TỪ TÀI KHOẢN (accountLocation) thay vì giữ lựa chọn tay cũ.
 * Trước đây source="manual" giữ mãi -> đổi tay rồi logout/login vẫn ra chỗ đã đổi, không về theo tài khoản.
 */
async function forgetStoredLocation() {
  try { await chrome.storage.local.remove(LOCATION_STORAGE_KEY); } catch (_) { /* ignore */ }
  currentLocation = { province: "", provinceSlug: "", ward: "" };
  if (provinceSelect) provinceSelect.value = "";
  if (wardSelect) { wardSelect.innerHTML = ""; wardSelect.disabled = true; }
}

/** Tỉnh/xã gắn trong tài khoản -> địa chỉ mặc định, kèm dấu vết để biết là máy tự điền. */
function accountLocation(store) {
  const mapped = store?.locationFor?.(currentUser?.tinh, currentUser?.xa);
  if (!mapped?.provinceSlug) return null;
  return { ...mapped, source: "account", username: currentUser?.username || "" };
}

function locationIsComplete() {
  return !!(currentLocation.provinceSlug && currentLocation.ward);
}

function showLocationSummary() {
  if (locationIsComplete()) {
    locationStatus.textContent = `✓ ${currentLocation.ward}, ${currentLocation.province}`;
    locationStatus.className = 'status ok';
  } else if (currentLocation.provinceSlug) {
    locationStatus.textContent = 'Chọn tiếp Phường/Xã để trợ lý điền hộ trên cổng.';
    locationStatus.className = 'status warn';
  } else {
    locationStatus.textContent = '';
    locationStatus.className = 'status';
  }
}

/** Địa chỉ đổi -> cập nhật lại gợi ý ở mục "Mở trang kê khai" (mục đó init sau, có thể chưa sẵn). */
function refreshKeKhaiHint() {
  try {
    if (keKhaiSection && !keKhaiSection.hidden) updateKeKhaiUI();
  } catch (_) { /* mục kê khai chưa khởi tạo xong */ }
}

/** Chọn thủ tục ở "Loại thủ tục" -> thanh kê khai bám theo (nếu thủ tục đó có link). */
function syncKeKhaiSelection(key) {
  try {
    if (!keKhaiSelect || !keKhaiLinks().some((item) => item.key === key)) return;
    keKhaiSelect.value = key;
    updateKeKhaiUI();
  } catch (_) { /* mục kê khai chưa khởi tạo xong */ }
}

function loadWards(provinceSlug, selectedWard) {
  wardSelect.innerHTML = '';
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = '-- Chọn phường/xã --';
  wardSelect.appendChild(placeholder);

  const data = provinceSlug ? locationStore()?.getWards(provinceSlug) : null;
  wardSelect.disabled = !data;
  if (!data) return;

  for (const ward of data.communes) {
    const option = document.createElement('option');
    option.value = ward;
    option.textContent = ward;
    if (ward === selectedWard) {
      option.selected = true;
      currentLocation.ward = ward;
    }
    wardSelect.appendChild(option);
  }
  syncDestCombos();
}

// Init location UI when popup loads
if (locationSection) {
  initLocationManager().catch(err => {
    console.error('[Popup] LocationManager init error:', err);
  });
}


// ===== Ô "Thủ tục" trong khối Đi đến thủ tục: 13 thủ tục có link kê khai =====
// Chọn ở đây set luôn pipeline điền tự động (cùng hệ key với auto-fill-hcc-backend).
const keKhaiSection = document.getElementById("keKhaiSection");
const keKhaiSelect = document.getElementById("keKhaiSelect");
const keKhaiStatus = document.getElementById("keKhaiStatus");

const KE_KHAI_STORAGE_KEY = "autofill_last_ke_khai_key";

// Danh mục link kê khai do BACKEND giữ (/api/v1/procedures/ke-khai-links) — extension không đóng gói
// data/procedure-links.js nữa. initKeKhaiPicker() nạp một lần rồi mọi chỗ đọc qua hàm này.
let keKhaiLinkList = [];

function keKhaiLinks() {
  return keKhaiLinkList;
}

function selectedKeKhaiLink() {
  return keKhaiLinks().find((item) => item.key === keKhaiSelect.value) || null;
}

function updateKeKhaiUI() {
  const link = selectedKeKhaiLink();
  if (!link) {
    keKhaiStatus.textContent = '';
    keKhaiStatus.className = 'status';
    return;
  }
  // Thủ tục doanh nghiệp nộp thẳng trên cổng ĐKKD qua mạng: không có khối chọn cơ quan, trợ lý đi
  // tiếp bằng ba bước wizard (loại đăng ký → loại hình → Bắt đầu) để vào khối dữ liệu hồ sơ.
  if (link.enterpriseFlow) {
    keKhaiStatus.textContent = `Trợ lý sẽ mở cổng đăng ký doanh nghiệp qua mạng, chọn "Thành lập mới doanh nghiệp" và "${link.enterpriseFlow.entityLabel}" rồi bấm "Bắt đầu" để vào hồ sơ. Cần đăng nhập tài khoản ĐKKD trước.`;
    keKhaiStatus.className = 'status info';
    return;
  }
  // Cổng React mới bắt chọn Tỉnh/Xã trước khi vào biểu mẫu → trợ lý điền hộ nếu đã có địa chỉ.
  if (link.needsAgencySelect && !locationIsComplete()) {
    keKhaiStatus.textContent = 'Thủ tục này cần chọn Tỉnh/Xã trên cổng — chọn địa chỉ ở mục trên để trợ lý điền hộ.';
    keKhaiStatus.className = 'status warn';
  } else if (link.needsAgencySelect) {
    keKhaiStatus.textContent = link.autoConfirm
      ? `Trợ lý sẽ chọn ${currentLocation.ward}, ${currentLocation.province}, bấm "Nộp trực tuyến" rồi "Xác nhận" để vào hồ sơ.`
      : `Trợ lý sẽ tự chọn ${currentLocation.ward}, ${currentLocation.province} và mở biểu mẫu kê khai.`;
    keKhaiStatus.className = 'status info';
  } else {
    keKhaiStatus.textContent = 'Sẽ mở tại tab hiện tại: ' + link.url;
    keKhaiStatus.className = 'status info';
  }
}

async function initKeKhaiPicker() {
  try {
    await popupBootstrapReady;
  } catch (error) {
    console.warn("[Popup] Khởi tạo chính chưa hoàn tất trước ô Đi đến thủ tục:", error);
  }
  try {
    const res = await api.keKhaiLinks();
    keKhaiLinkList = Array.isArray(res?.links) ? res.links : [];
  } catch (error) {
    keKhaiLinkList = [];
    console.error('[Popup] Không lấy được danh mục link kê khai từ backend:', error);
  }

  const links = keKhaiLinks();
  if (!links.length) {
    keKhaiSection.hidden = true;
    keKhaiSection.dataset.unavailable = "1";   // chế độ "Toàn bộ" không được bật lại mục rỗng
    // applyDestOpen() có thể đã chạy trước lúc này và lỡ hiện nút "Chuyển thủ tục khác" -> thu lại.
    try { refreshSwitchProcBtn(); } catch (_) { /* khối Đi đến thủ tục chưa init xong */ }
    console.error('[Popup] Không có link kê khai nào — kiểm tra /api/v1/procedures/ke-khai-links');
    return;
  }

  for (const item of links) {
    const option = document.createElement('option');
    option.value = item.key;
    option.textContent = item.label;
    // Mã TTHC (backend khai ở data/ke_khai_links.json) để cán bộ tra bằng mã in trên giấy.
    // Để ở data-* chứ KHÔNG ghép vào textContent — ghép vào thì gõ "2" trong tên khớp mọi mã.
    if (item.code) option.dataset.code = item.code;
    keKhaiSelect.appendChild(option);
  }

  const saved = await chrome.storage.local.get(KE_KHAI_STORAGE_KEY);
  const savedKey = saved[KE_KHAI_STORAGE_KEY];
  // Ưu tiên thủ tục đang chọn ở "Loại thủ tục" (cùng hệ key với auto-fill-hcc-backend).
  const preferred = links.some((item) => item.key === selectedProcedureKey)
    ? selectedProcedureKey
    : (links.some((item) => item.key === savedKey) ? savedKey : '');
  keKhaiSelect.value = preferred;

  keKhaiSelect.addEventListener('change', () => {
    updateKeKhaiUI();
    void onKeKhaiProcedureChosen();
  });
  // savedKey là lựa chọn tiện ích dùng chung để lần sau mở nhanh, KHÔNG phải pipeline của tab này.
  // Chỉ event change hoặc nút mở trang mới được quyền gọi onKeKhaiProcedureChosen(); nếu gọi ngay
  // khi init, tab mới chưa có session sẽ kế thừa nhầm tên thủ tục của tab trước.
  syncDestCombos();
  updateKeKhaiUI();
  // initKeKhaiPicker() chạy async, chốt danh mục SAU applyDestOpen() đầu tiên -> phải chỉnh lại nút.
  try { refreshSwitchProcBtn(); } catch (_) { /* khối Đi đến thủ tục chưa init xong */ }
  postPanelHeight();
}

/** Chọn thủ tục ở chế độ Toàn bộ = chọn luôn pipeline điền tự động (cùng hệ key với backend). */
async function onKeKhaiProcedureChosen() {
  const link = selectedKeKhaiLink();
  if (!link) return;
  try { await chrome.storage.local.set({ [KE_KHAI_STORAGE_KEY]: link.key }); } catch (_) { /* ignore */ }
  if (PROCEDURES.some((p) => p.key === link.key) && selectedProcedureKey !== link.key) {
    await selectProcedure(link.key, { source: "manual" });
  }
}

/** Mở trang kê khai của thủ tục đang chọn, kèm "lên đạn" cho content/agency-select.js. */
async function openKeKhaiPage() {
  const link = selectedKeKhaiLink();
  if (!link) return false;
  await onKeKhaiProcedureChosen();
  if (link.needsAgencySelect && locationIsComplete()) {
    await chrome.storage.local.set({
      [AGENCY_ARM_KEY]: {
        province: currentLocation.province,
        ward: currentLocation.ward,
        procedureKey: link.key,
        // Trang kết quả có thể liệt kê nhiều dịch vụ -> content script cần tên để bấm đúng thẻ.
        procedureLabel: link.label,
        // Bấm hộ "Xác nhận" ở modal Thông tin chung để vào thẳng wizard hồ sơ.
        autoConfirm: !!link.autoConfirm,
        at: Date.now(),
      },
    });
  } else {
    await chrome.storage.local.remove(AGENCY_ARM_KEY);
  }
  // Thủ tục doanh nghiệp: "lên đạn" cho content/procedures/enterprise-registration.js bấm hộ ba
  // bước wizard trên dangkyquamang.dkkd.gov.vn. Thủ tục khác phải XÓA cờ để lần mở trước bỏ dở
  // không lỡ tay điều khiển wizard của hồ sơ đang mở.
  if (link.enterpriseFlow) {
    await chrome.storage.local.set({
      [ENTERPRISE_ARM_KEY]: {
        ...link.enterpriseFlow,
        procedureKey: link.key,
        procedureLabel: link.label,
        at: Date.now(),
      },
    });
  } else {
    await chrome.storage.local.remove(ENTERPRISE_ARM_KEY);
  }
  // Điều hướng phá iframe popup hiện tại; chốt file xuống storage trước khi đổi URL.
  await saveSession();
  const tabId = await getTargetTabId();
  if (tabId) await chrome.tabs.update(tabId, { url: link.url });
  else await chrome.tabs.create({ url: link.url });
  return true;
}

if (keKhaiSection) {
  initKeKhaiPicker().catch(err => {
    console.error('[Popup] KeKhaiPicker init error:', err);
  });
}





// ===== Combobox có ô tìm kiếm cho <select> dài (34 tỉnh / 3321 xã / 13 thủ tục) =====
// <select> gốc VẪN là nguồn dữ liệu và nơi phát sự kiện `change` — mọi code sẵn có (loadWards,
// persistLocation, onKeKhaiProcedureChosen…) không phải sửa gì. Widget này chỉ là lớp nhìn:
// đọc <option> mỗi lần mở, lọc theo từ khoá, chọn xong thì set .value rồi dispatch change.
function enhanceSelectWithSearch(select, { searchPlaceholder }) {
  if (!select || select.dataset.enhanced === "1") return null;
  select.dataset.enhanced = "1";

  const combo = document.createElement("div");
  combo.className = "combo";
  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "combo-trigger";
  trigger.setAttribute("aria-haspopup", "listbox");
  trigger.setAttribute("aria-expanded", "false");
  const label = document.createElement("span");
  label.className = "combo-label";
  const caret = document.createElement("span");
  caret.className = "combo-caret";
  caret.textContent = "▾";
  caret.setAttribute("aria-hidden", "true");
  trigger.append(label, caret);

  const dropdown = document.createElement("div");
  dropdown.className = "combo-dropdown";
  dropdown.hidden = true;
  const search = document.createElement("input");
  search.type = "text";
  search.className = "combo-search";
  search.autocomplete = "off";
  search.placeholder = searchPlaceholder || "Tìm...";
  const list = document.createElement("div");
  list.className = "combo-list";
  list.setAttribute("role", "listbox");
  dropdown.append(search, list);
  combo.append(trigger, dropdown);
  select.after(combo);

  const options = () => Array.from(select.options).filter((opt) => opt.value !== "");
  const currentOption = () => select.options[select.selectedIndex] || null;
  const placeholderText = () => select.options[0]?.textContent || "-- Chọn --";

  function syncTrigger() {
    const picked = select.value ? currentOption() : null;
    label.textContent = picked ? picked.textContent : placeholderText();
    label.classList.toggle("placeholder", !picked);
    trigger.disabled = select.disabled;
    if (select.disabled) close();
  }

  function renderList(query) {
    const needle = normalizeProcedureSearch(query);
    // Mã TTHC gõ tay hay rơi rụng/thừa dấu chấm ("2000815", "2.000.815") nên so theo phần SỐ.
    // Cần ≥4 chữ số mới coi là đang tra mã — nếu không, chữ "2" lẫn trong tên thủ tục sẽ khớp
    // mọi mã. Mã cũng KHÔNG nằm trong textContent của <option> vì lý do đó: nó ở data-code,
    // nên danh sách tỉnh/xã (dùng chung widget này, không khai mã) không bị ảnh hưởng.
    const digits = needle.replace(/\D+/g, "");
    const codeNeedle = digits.length >= 4 ? digits : "";
    list.innerHTML = "";
    const matched = options().filter((opt) => {
      if (!needle) return true;
      if (normalizeProcedureSearch(opt.textContent).includes(needle)) return true;
      return !!codeNeedle && (opt.dataset.code || "").replace(/\D+/g, "").includes(codeNeedle);
    });
    if (!matched.length) {
      const empty = document.createElement("div");
      empty.className = "combo-empty";
      empty.textContent = "Không tìm thấy";
      list.appendChild(empty);
      return;
    }
    for (const opt of matched) {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "combo-option" + (opt.value === select.value ? " active" : "");
      item.setAttribute("role", "option");
      item.textContent = opt.textContent;
      // Mã chỉ để tra cứu và xem khi rê chuột, KHÔNG hiện thành dòng riêng cho đỡ rối danh sách.
      if (opt.dataset.code) item.title = `${opt.dataset.code} — ${opt.textContent}`;
      item.addEventListener("click", () => {
        select.value = opt.value;
        // Phát `change` để handler gốc của select chạy y như người dùng bấm select thật.
        select.dispatchEvent(new Event("change", { bubbles: true }));
        syncTrigger();
        close();
      });
      list.appendChild(item);
    }
  }

  function open() {
    if (select.disabled) return;
    dropdown.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
    search.value = "";
    renderList("");
    search.focus();
    postPanelHeight();
  }

  function close() {
    if (dropdown.hidden) return;
    dropdown.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
    postPanelHeight();
  }

  trigger.addEventListener("click", () => (dropdown.hidden ? open() : close()));
  search.addEventListener("input", () => renderList(search.value));
  search.addEventListener("keydown", (e) => { if (e.key === "Escape") { close(); trigger.focus(); } });
  document.addEventListener("click", (e) => {
    if (!dropdown.hidden && !combo.contains(e.target)) close();
  });
  // loadWards()/initKeKhaiPicker() đổi option hoặc value bằng code -> nhãn phải bám theo.
  select.addEventListener("change", syncTrigger);

  syncTrigger();
  return { syncTrigger };
}

// ===== ĐI ĐẾN THỦ TỤC =====
// KHÔNG có nút bật/tắt: panel tự đổi màn theo trang cổng đang mở.
//   đang ở trang chủ / tra cứu DVC  -> hiện khối chọn Địa chỉ + Thủ tục + nút mở trang
//   đã vào trang thủ tục / hồ sơ    -> trả về màn Giấy tờ + Quét như cũ
// Trạng thái do content/agency-select.js báo (atPortalHome), cổng khác trả unsupported -> luôn ẩn.
const destSection = document.getElementById("destSection");
const destPickers = document.getElementById("destPickers");
const destGoBtn = document.getElementById("destGoBtn");
const destBackBtn = document.getElementById("destBackBtn");
const switchProcedureBtn = document.getElementById("switchProcedureBtn");
const procedureSection = document.getElementById("procedureSection");
const docsSection = document.getElementById("docsSection");

// Cán bộ TỰ bấm "Chuyển thủ tục khác" -> giữ màn "Đi đến thủ tục" mở dù đang đứng trong trang thủ
// tục (atPortalHome = false). Cờ tắt khi bấm "Quay lại", khi mở trang thủ tục mới, hoặc khi trang
// về lại trang chủ cổng (lúc đó panel tự mở, không cần cờ tay nữa).
let destManualOpen = false;

/** Không có danh mục link kê khai (backend lỗi) thì màn "Đi đến thủ tục" vô dụng -> giấu luôn nút. */
function refreshSwitchProcBtn() {
  if (!switchProcedureBtn) return;
  switchProcedureBtn.hidden = keKhaiSection?.dataset.unavailable === "1";
}

function applyDestOpen(open) {
  if (!destSection || !destPickers) return;
  const usable = keKhaiSection?.dataset.unavailable !== "1";
  const showDest = open && usable;
  destSection.hidden = !showDest;
  destPickers.hidden = !showDest;
  // Đang chọn điểm đến thì ẩn combo "Loại thủ tục" (ô "Thủ tục" bên dưới đã set luôn pipeline)
  // và ẩn khối Giấy tờ — chưa vào form thì chưa có gì để quét.
  if (procedureSection) procedureSection.hidden = showDest;
  if (docsSection) docsSection.hidden = showDest;
  // Panel tự mở vì đang ở trang chủ cổng thì KHÔNG có màn nào để quay về -> chỉ hiện nút khi mở tay.
  if (destBackBtn) destBackBtn.hidden = !(showDest && destManualOpen);
  refreshSwitchProcBtn();
  if (showDest) refreshKeKhaiHint();
  postPanelHeight();
}

/** Hỏi content script đang ở đâu rồi đổi màn cho khớp. */
async function refreshDestVisibility() {
  const state = await sendToContent({ action: "getPortalFlowState" });
  const atPortalHome = !!state && !state.unsupported && !!state.atPortalHome;
  if (atPortalHome) destManualOpen = false;
  applyDestOpen(atPortalHome || destManualOpen);
}

/** "Chuyển thủ tục khác": mở màn chọn Tỉnh/Xã + Thủ tục ngay giữa lúc đang ở trang thủ tục. */
function onSwitchProcedureClick() {
  destManualOpen = true;
  // Vào màn với đúng thủ tục đang chọn ở "Loại thủ tục" cho khỏi phải dò lại từ đầu.
  syncKeKhaiSelection(selectedProcedureKey);
  syncDestCombos();
  applyDestOpen(true);
}

/** "Quay lại": bỏ cờ mở tay rồi để trạng thái trang quyết định như cũ. */
function onDestBackClick() {
  destManualOpen = false;
  void refreshDestVisibility();
}

async function onDestGoClick() {
  const link = selectedKeKhaiLink();
  if (!link) {
    keKhaiStatus.textContent = "Chưa chọn thủ tục.";
    keKhaiStatus.className = "status err";
    return;
  }
  if (link.needsAgencySelect && !locationIsComplete()) {
    locationStatus.textContent = "Chưa chọn đủ Tỉnh/Thành phố và Phường/Xã.";
    locationStatus.className = "status err";
    return;
  }
  destGoBtn.disabled = true;
  try {
    await openKeKhaiPage();
    destManualOpen = false;   // đã đi tới thủ tục mới -> lần sau lại theo trạng thái trang
    keKhaiStatus.textContent = "Đang mở trang thủ tục…";
    keKhaiStatus.className = "status ok";
  } catch (error) {
    keKhaiStatus.textContent = "✗ Không mở được trang thủ tục";
    keKhaiStatus.className = "status err";
    console.error("[Popup] Mở trang thủ tục lỗi:", error);
  } finally {
    destGoBtn.disabled = false;
  }
}

const destCombos = {};

/** Code nạp dữ liệu (loadWards, khôi phục lựa chọn cũ…) set .value/.selected mà KHÔNG phát `change`
 *  -> nhãn trigger phải được đồng bộ tay sau mỗi lần đổi danh sách. */
function syncDestCombos() {
  for (const combo of Object.values(destCombos)) combo?.syncTrigger();
}

async function initDestSection() {
  if (!destSection || !destGoBtn) return;
  destCombos.province = enhanceSelectWithSearch(provinceSelect, { searchPlaceholder: "Tìm tỉnh/thành phố..." });
  destCombos.ward = enhanceSelectWithSearch(wardSelect, { searchPlaceholder: "Tìm phường/xã..." });
  destCombos.keKhai = enhanceSelectWithSearch(keKhaiSelect, { searchPlaceholder: "Tìm theo tên hoặc mã (vd 2.000815)..." });

  destGoBtn.addEventListener("click", () => void onDestGoClick());
  destBackBtn?.addEventListener("click", onDestBackClick);
  switchProcedureBtn?.addEventListener("click", onSwitchProcedureClick);
  // Ẩn trước, chờ biết đang ở trang nào rồi mới quyết -> không chớp khối sai màn lúc mở panel.
  applyDestOpen(false);
  await refreshDestVisibility();

  // content/agency-select.js bắn tin mỗi khi trang cổng đổi (kể cả SPA giữ nguyên URL).
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg?.action === "portalFlowChanged") void refreshDestVisibility();
  });
}

function refreshOcrButtonLabel() {
  if (!ocrBtn) return;
  // Nhãn nút riêng theo thủ tục (BE cấu hình fillButtonLabel, vd "Điền thông tin tài khoản").
  const customLabel = selectedProcedureConfig()?.fillButtonLabel;
  ocrBtn.textContent = isBacNinhThreeStepProcedure()
    ? "Nhập đơn đăng ký"
    : (isAttachMode() ? "Đính kèm vào hồ sơ" : (customLabel || "Quét và nhập dữ liệu"));
}

/**
 * Cổng DVC quốc gia chèn thêm modal "Thông tin chung" giữa lúc vào hồ sơ (xem luồng
 * tro-ly-nguoi-dan-backend/app/chat/flow.py): thấy modal thì bấm Xác nhận hộ rồi mới quét & điền.
 * Cổng khác trả unsupported -> đi thẳng như cũ.
 */
async function passInfoModalIfAny() {
  const state = await sendToContent({ action: "getPortalFlowState" });
  // Cổng khác (không có wizard này) hoặc đã ở bước kê khai -> quét luôn như cũ.
  if (!state || state.unsupported || state.formReady) return true;

  if (state.infoModal) {
    setStatus("Đang xác nhận Thông tin chung…", "info");
    const res = await sendToContent({ action: "confirmInfoModal" });
    if (res?.formReady) return true;
    // Xác nhận xong thường rơi vào bước "Thông tin chủ hồ sơ" -> dặn luôn cho khỏi bấm quét hụt.
    const after = await sendToContent({ action: "getPortalFlowState" });
    if (after?.formReady) return true;
    setStatus(after?.ownerInfo ? after.ownerStepHint
      : 'Đã bấm Xác nhận. Chờ cổng mở bước kê khai rồi bấm lại "Quét và nhập dữ liệu".', "warn");
    return false;
  }

  // Bước "Thông tin chủ hồ sơ": cổng chưa dựng biểu mẫu kê khai nên quét cũng không điền được gì.
  if (state.ownerInfo) {
    setStatus(state.ownerStepHint, "warn");
    return false;
  }
  return true;
}

initDestSection().catch((err) => console.error("[Popup] Dest section init error:", err));
