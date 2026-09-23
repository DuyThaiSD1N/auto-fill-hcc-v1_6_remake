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
// Khóa MỘT HỒ SƠ (gửi BE qua options.dossierId → traces.dossier_id + collection dossiers).
// KHÁC lastProcessSession.sessionId: cái đó là request_id của LƯỢT QUÉT, cố ý đổi mỗi lần quét
// lại để planner đính kèm bám đúng lượt mới nhất — không phải danh tính hồ sơ.
// Sinh LƯỜI ở lượt process/đính kèm đầu tiên; sống qua reload nhờ nằm trong session của tab;
// chết khi: bấm Gửi hồ sơ · đổi thủ tục · Tạo phiên mới · đăng xuất · đóng tab.
let dossierId = "";
// Hồ sơ này đã có ít nhất một lần bấm "Gửi hồ sơ". Không xoá khóa ngay lúc đó (chứng thực tách
// nhiều tab còn nộp tiếp trên cùng khóa) — chỉ đánh dấu để LƯỢT process/đính kèm SAU xoay khóa.
let dossierSubmitted = false;
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
    await restoreScanWatermark(); // mốc "giấy tờ này của công dân trước" phải sống qua redirect
    await restoreScanDaGo();      // file cán bộ đã gỡ tay cũng phải sống qua redirect
    await restoreConsent();   // khôi phục trạng thái đồng ý của phiên qua reload trang
    await autoDetectProcedure();
    restoreBusinessFillSupportCode();
    await restoreSplitProgressStatus();
    // Dựng lại lời đề nghị "dùng lại hồ sơ trước" — cổng dịch vụ công redirect/postback liên tục,
    // panel bị dựng lại thường xuyên, phải hiện lại được sau mỗi lần đó chứ không mất theo RAM.
    await renderPrevSessionOffer();
    // Chặng 2 của luồng doanh nghiệp: wizard vừa đưa tới khối dữ liệu thì quét + điền luôn.
    await resumeEnterpriseFillIfPending();
    // Cán bộ vừa bấm nộp ở lượt trước, trang điều hướng làm panel nạp lại → mở lại màn đánh giá.
    await resumePendingRating();
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
    await restoreScanWatermark(); // mốc "giấy tờ này của công dân trước" phải sống qua redirect
    await restoreScanDaGo();      // file cán bộ đã gỡ tay cũng phải sống qua redirect
    await restoreConsent();   // khôi phục trạng thái đồng ý của phiên qua reload trang
    await autoDetectProcedure();
    restoreBusinessFillSupportCode();
    await restoreSplitProgressStatus();
    // Dựng lại lời đề nghị "dùng lại hồ sơ trước" — cổng dịch vụ công redirect/postback liên tục,
    // panel bị dựng lại thường xuyên, phải hiện lại được sau mỗi lần đó chứ không mất theo RAM.
    await renderPrevSessionOffer();
    // Chặng 2 của luồng doanh nghiệp: wizard vừa đưa tới khối dữ liệu thì quét + điền luôn.
    await resumeEnterpriseFillIfPending();
    // Cán bộ vừa bấm nộp ở lượt trước, trang điều hướng làm panel nạp lại → mở lại màn đánh giá.
    await resumePendingRating();
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
  await clearPrevSession(); // rời phiên làm việc → không để giấy tờ công dân nằm lại trên máy
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
    // Cất giấy tờ hồ sơ vừa xong sang ngăn "hồ sơ trước" TRƯỚC khi xoá bất cứ thứ gì — đây là
    // nguồn duy nhất để mời dùng lại khi cùng công dân làm thủ tục tiếp theo.
    archiveCurrentSessionAsPrev();
    await clearSession();
    files.length = 0;
    lastProcessSession = null;
    resetScanBatchImportState(); // cong dan tiep theo, cung popup dang mo -> phai thu gom batch lai tu dau
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
    void renderPrevSessionOffer(); // mời dùng lại giấy tờ vừa cất, nếu vẫn là cùng công dân
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

// ===== Nghiệp vụ riêng phường Đắk Bla — tỉnh Lâm Đồng (chỉ áp cho tài khoản của địa bàn này) =====
// Ô "Lý do giải thể" (trang Chấm dứt hoạt động) LUÔN là câu cố định, bất kể Thông báo chấm dứt
// trong hồ sơ ghi lý do gì — kể cả khi backend không đọc được lý do nào.
const DAK_BLA_DISSOLUTION_REASON = "Hộ kinh doanh không hiệu quả";

/** Tài khoản phường Đắk Bla — tỉnh Lâm Đồng (/auth/me trả `xa` + `tinh`). */
function isDakBlaLamDongUser(user) {
  // Phải khớp CẢ phường lẫn tỉnh: chỉ địa bàn này mới ghi đè lý do giải thể.
  return normalizeProcedureSearch(user?.tinh).includes("lam dong")
    && normalizeProcedureSearch(user?.xa).includes("dak bla");
}

function buildBusinessDefaults(user) {
  const defaults = {};
  if (isXuanHuongBusinessUser(user)) defaults.businessActText = XUAN_HUONG_BUSINESS_ACT_TEXT;
  // Đà Nẵng: vai trò người nộp LUÔN là "Người có thẩm quyền ký Giấy đề nghị đăng ký Hộ kinh doanh",
  // kể cả khi nhân thân tài khoản khác chủ hộ (nghiệp vụ địa phương yêu cầu). Chỉ áp cho tài khoản
  // Đà Nẵng — tỉnh khác vẫn tự chốt vai trò theo đối chiếu tài khoản với chủ hộ như cũ.
  if (isDaNangBusinessUser(user)) defaults.forceSelfSubmitter = true;
  if (isHaiChauDaNangUser(user)) {
    defaults.dissolutionReason = HAI_CHAU_DISSOLUTION_REASON;
    defaults.postalServiceAddress = HAI_CHAU_POSTAL_ADDRESS;
  }
  if (isDakBlaLamDongUser(user)) defaults.dissolutionReason = DAK_BLA_DISSOLUTION_REASON;
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

// ── Khóa một hồ sơ (dossierId) ─────────────────────────────────────────────────────────
function newDossierId() {
  try { return crypto.randomUUID(); } catch (_) { }
  return "d-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
}

/** Sinh LƯỜI ở lượt process/đính kèm đầu tiên = đúng mốc "bắt đầu làm hồ sơ" phía BE.
 *
 *  Hồ sơ đã có sự kiện nộp thì LƯỢT NÀY là hồ sơ mới → xoay khóa. Cố ý xoay ở đây chứ không
 *  xoay ngay lúc bấm nộp: chứng thực tách nhiều tab dùng CHUNG một khóa và nộp N lần, xoay
 *  sớm là mất các lần nộp sau. Luật này đúng cho mọi thủ tục nên không phải khai cấu hình
 *  riêng cho nhóm đa tab — mà quên khai cấu hình là kiểu lỗi âm thầm, rất lâu sau mới lộ. */
function ensureDossierId() {
  if (!dossierId || dossierSubmitted) {
    dossierId = newDossierId();
    dossierSubmitted = false;
    void saveSession(); // phải nằm trong storage trước khi trang reload, nếu không 1 hồ sơ đếm thành 2
  }
  return dossierId;
}

/** Kết thúc hồ sơ (đã nộp hoặc bỏ dở) → lượt sau tự sinh khóa mới.
 *  Không báo BE: hồ sơ không có submit_clicked_at đã đủ nghĩa "làm dở", và lối "đóng tab"
 *  thì không gọi được BE nữa nên báo cũng không đầy đủ. */
function closeDossier(reason) {
  if (!dossierId) return;
  console.log("[AutoFill] Kết thúc hồ sơ", { dossierId, reason });
  dossierId = "";
  dossierSubmitted = false;
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
  // Cất giấy tờ của hồ sơ đang đóng vào ngăn "hồ sơ trước" TRƯỚC khi xoá files[] — để còn mời
  // dùng lại được nếu vẫn là cùng công dân (xem archiveCurrentSessionAsPrev).
  archiveCurrentSessionAsPrev();
  // Vô hiệu mọi saveSession cũ đang đọc file lớn; bản lưu đó không được ghi file thủ tục trước trở lại.
  sessionWriteRevision++;
  files.length = 0;
  lastProcessSession = null;
  closeDossier("procedure-change");
  businessFillSupportCode = "";
  if (fileInput) fileInput.value = "";
  clearReviewCard();
  hideSupportCode();
  closePhoneUpload();
  currentConsentContext = null;
  pendingConsentTrigger = null;
  resetScanBatchImportState(); // phien lam viec moi -> phai thu gom batch lai tu dau (xem gan ensureScanAgentConnected)
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
  // Có thủ tục đang làm việc (tự nhận diện hay chọn tay đều tính) → dò máy quét, không đợi
  // cán bộ bấm gì. Hàm tự bỏ qua nếu đã kết nối từ lần chọn trước.
  ensureScanAgentConnected();
  // Agent có thể đã kết nối sẵn từ trước (vd đổi thủ tục, hoặc "Phiên mới" trong cùng popup) →
  // thử gom batch quét gần nhất ngay, không đợi onConnected (chỉ bắn 1 lần lúc SSE mở).
  void attemptBatchImport();
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

// Mã loại hình doanh nghiệp của cổng ĐKKD qua mạng (trùng value radio $CtlEntType: SC = công ty
// cổ phần, LLC1/LLC2 = TNHH một/hai thành viên trở lên, PRI = doanh nghiệp tư nhân, PARTNER = hợp
// danh). Cổng in nhãn loại hình MỖI CHỖ MỘT KIỂU — khối "Thông tin về hồ sơ" có bản ghi "Công ty
// TNHH hai thành viên trở lên", nhãn radio của wizard ghi đủ "Công ty trách nhiệm hữu hạn hai thành
// viên trở lên", có bản dùng số "2 thành viên" — nên so NGUYÊN VĂN với registry là trượt. Rút cả hai
// vế về mã rồi mới so.
//
// Không suy ra được mã thì trả "" và để bên gọi bỏ qua: thà không nhận diện còn hơn nhận nhầm loại
// hình (chọn sai là hồ sơ thật phải bỏ đi làm lại).
function enterpriseEntityCode(label) {
  const text = normDetect(label);
  if (!text) return "";
  if (text.includes("hop danh")) return "PARTNER";
  if (text.includes("tu nhan")) return "PRI";
  if (text.includes("trach nhiem huu han") || /\btnhh\b/.test(text)) {
    // "một thành viên" / "1 thành viên" / "MTV" vs "hai thành viên" / "2 thành viên".
    if (/\bmtv\b/.test(text) || /\b(mot|1) thanh vien\b/.test(text)) return "LLC1";
    if (/\b(hai|2) thanh vien\b/.test(text)) return "LLC2";
    return "";   // TNHH nhưng không rõ một hay hai thành viên → không đoán
  }
  if (text.includes("co phan")) return "SC";
  return "";
}

// Mã loại hình của một thủ tục trong registry: ưu tiên `enterpriseEntityValue` (value radio, backend
// khai tay) rồi mới suy từ nhãn.
function enterpriseEntityCodeOf(procedure) {
  return String(procedure?.enterpriseEntityValue || "").trim().toUpperCase()
    || enterpriseEntityCode(procedure?.enterpriseEntityLabel || "");
}

// Khớp tín hiệu trang (URL + heading) với rule `detect` của thủ tục từ backend.
function detectProcedureKeyFromSignals(signals) {
  if (!signals) return "";
  // `detectDisabled` (backend đặt) = thủ tục này CHỈ được chọn tay, không bao giờ tự nhận diện.
  // Lọc ngay từ đây nên mọi bước nhận diện bên dưới (URL / heading / textIncludes) đều bỏ qua nó.
  const detectables = PROCEDURES.filter((p) => p && p.detect && !p.detectDisabled);
  const url = String(signals.url || "").toLowerCase();
  const body = normDetect(signals.bodyText || "");

  // HkdOnline dùng chung domain/URL. DOM procedure hint phải thắng rule URL chung:
  // - choice: màn chọn có nhiều option, không được đoán theo text option;
  // - change/create: loại hồ sơ đã được xác nhận bởi active step hoặc khối thông tin hồ sơ.
  const selected = selectedProcedureConfig();

  // Cổng ĐKKD qua mạng dùng CHUNG Registration.aspx/DW_DOCUMENTEdit.aspx cho MỌI loại hình doanh
  // nghiệp: URL, heading và body ("ĐĂNG KÝ DOANH NGHIỆP", "Thành lập mới...") không phân biệt được
  // CTCP với TNHH/DNTN, và các nhánh đoán theo text bên dưới từng trả nhầm thành thủ tục HỘ kinh doanh.
  //
  // Gate theo DOMAIN chứ không chỉ theo `enterpriseProcedureHint`: hint do content script của cổng
  // sinh ra, lượt postback nào nó chưa gắn kịp là hint rỗng và cả khối này bị bỏ qua → rơi xuống rule
  // urlIncludes, nơi CTCP và TNHH hai thành viên khai TRÙNG domain nên luôn trả về entry đứng trước
  // (CTCP). Đó chính là lỗi "đang điền hồ sơ TNHH tự nhảy sang công ty cổ phần". Trong phạm vi cổng
  // này, loại hình CHỈ được chốt bằng dòng "Loại hình doanh nghiệp" của chính hồ sơ.
  if (url.includes("dangkyquamang.dkkd.gov.vn") || String(signals.enterpriseProcedureHint || "")) {
    const entityLabel = normDetect(signals.enterpriseEntityLabel || "");
    if (entityLabel) {
      // Hồ sơ đã tạo: cổng in rõ "Loại hình doanh nghiệp" → chốt đúng thủ tục theo loại hình đó.
      // Loại hình chưa có thủ tục tương ứng (vd TNHH một thành viên) thì để TRỐNG, không nhận bừa.
      // Nhánh này dò THẲNG trong PROCEDURES (không qua `detectables`) nên phải tự loại thủ tục
      // bật detectDisabled — nếu không, loại hình khớp là nó vẫn tự chọn bất chấp cờ.
      const wantedCode = enterpriseEntityCode(entityLabel);
      const matched = PROCEDURES.find((item) => item.enterpriseEntityLabel
        && !item.detectDisabled
        && (normDetect(item.enterpriseEntityLabel) === entityLabel
          || (!!wantedCode && enterpriseEntityCodeOf(item) === wantedCode)));
      if (matched) return matched.key;
      // Không nhận diện được (loại hình chưa có thủ tục, hoặc thủ tục đó chỉ cho chọn tay):
      // GIỮ lựa chọn doanh nghiệp đang có thay vì trả rỗng. Cổng postback ở mọi bước nên trả rỗng
      // là mỗi lần tải trang lại xoá tên thủ tục cán bộ vừa chọn.
      if (isEnterprisePortalProcedure(selected)) return selected.key;
      return "";
    }
    // Chưa chốt loại hình (wizard chọn loại đăng ký/loại hình, trang chủ cổng, màn đăng nhập):
    // GIỮ thủ tục doanh nghiệp đang chọn; chưa chọn gì thì để TRỐNG cho cán bộ tự chọn.
    // KHÔNG rơi xuống rule urlIncludes như trước: domain này có nhiều loại hình cùng khai, đoán theo
    // domain là cầm chắc 50% sai và còn ghi đè lựa chọn tay sau mỗi lần postback.
    if (isEnterprisePortalProcedure(selected)) return selected.key;
    return "";
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
    // Luật nhận nút "Gửi hồ sơ" (BE: portal_submit.py) + base đang chạy → để content script và
    // background dùng được kể cả khi panel đã đóng. Ghi vào storage vì hai nơi đó không thấy
    // biến của popup. BE bản cũ không trả portalSubmit → bỏ qua, tính năng tắt lặng lẽ.
    if (res.portalSubmit && typeof res.portalSubmit === "object") {
      const base = (typeof activeBackendBase === "function") ? activeBackendBase() : BACKEND_URL;
      try {
        await chrome.storage.local.set({
          [SUBMIT_WATCH_KEY]: { rules: res.portalSubmit, base },
        });
      } catch (_) { /* không chặn luồng nạp thủ tục */ }
    }
    // Câu chữ phiếu đánh giá do BE giữ (app/dossiers/rating_card.py) — CÙNG bộ với Handfree.
    // Không chép cứng nhãn nào vào extension: sửa câu chữ hay đổi danh sách lý do chỉ cần
    // deploy BE. BE bản cũ không trả → màn đánh giá tắt lặng lẽ, không vỡ gì.
    if (res.ratingCard && Array.isArray(res.ratingCard.scale)) RATING_CARD = res.ratingCard;
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
// Ngăn "hồ sơ trước": snapshot của phiên vừa đóng, GIỮ LẠI (không xoá) để cán bộ dùng lại được
// bằng 1 chạm khi CÙNG một công dân làm thủ tục thứ hai (vd khai sinh liên thông + cấp bản sao).
// PHẢI nằm trong chrome.storage.local chứ không phải biến trong RAM: cổng dịch vụ công
// postback/redirect liên tục, panel bị dựng lại thường xuyên — giữ trong RAM là mất ngay lời đề
// nghị, cán bộ lại phải thêm tay từng file. Mỗi lần tạo phiên mới thì GHI ĐÈ ngăn này, nên tối đa
// luôn chỉ 2 bản/tab (hiện tại + trước đó), không phình theo số lượt tiếp dân.
const PREV_SESSION_KEY = "autofill_prev_session_" + (EMBEDDED_TAB_ID ?? "popup");
const PREV_SESSION_TTL_MS = 30 * 60 * 1000; // quá 30 phút thì không còn là "hồ sơ vừa xong" nữa
const UNKNOWN_WORK_PROCEDURE_KEY = "__legacy_unknown__";
let sessionWriteRevision = 0;
let sessionWriteQueue = Promise.resolve();

function enqueueSessionWrite(operation) {
  sessionWriteQueue = sessionWriteQueue.catch(() => { }).then(operation);
  return sessionWriteQueue;
}

// Hai hàm ánh xạ item files[] ↔ snapshot lưu trữ. Dùng CHUNG cho cả saveSession/restoreSession
// lẫn ngăn "hồ sơ trước" (archiveCurrentSessionAsPrev/reusePrevSession) — bộ field
// fromScan/rel/hash/canhBaoScan từng bị sót một lần khi chép tay, không chép lần hai.
function fileItemToSnapshot(it) {
  return {
    name: it.file.name,
    type: it.file.type || "image/jpeg",
    dataUrl: it.dataUrl,
    role: it.role || "doc",
    fromScan: it.fromScan || false,
    rel: it.rel || null,
    hash: it.hash || null,
    canhBaoScan: it.canhBaoScan || null,
  };
}
function fileItemFromSnapshot(f) {
  // File khôi phục không có File object thật, nhưng đã có sẵn dataUrl nên đủ để gửi BE.
  // rel/hash/canhBaoScan phục hồi lại để reconcileScanAgentFiles còn đối soát tiếp được.
  return {
    file: { name: f.name, type: f.type }, role: f.role || "doc", dataUrl: f.dataUrl,
    restored: true,
    fromScan: !!f.fromScan,
    rel: f.rel || null,
    hash: f.hash || null,
    canhBaoScan: f.canhBaoScan || null,
  };
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
      dossierId,
      dossierSubmitted,
      files: files.map(fileItemToSnapshot),
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
  dossierId = "";
  dossierSubmitted = false;
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
  // Khóa hồ sơ phải sống qua reload, nếu không một hồ sơ sẽ bị đếm thành nhiều.
  dossierId = String(saved.dossierId || "").trim();
  dossierSubmitted = !!saved.dossierSubmitted;
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
    files.push(fileItemFromSnapshot(f));
  }
  renderProcedureResults();
  applyFormUI();
}

// ===== Ngăn "hồ sơ trước" — dùng lại giấy tờ bằng 1 chạm =====
// Bài toán: watermark (xem attemptBatchImport) chặn được việc pin nhầm giấy tờ của công dân
// TRƯỚC vào hồ sơ công dân MỚI — nhưng lại chặn luôn ca hợp lệ "cùng một công dân làm thủ tục
// thứ hai" (khai sinh liên thông + cấp bản sao), khiến cán bộ phải thêm tay từng file.
//
// Không giải bằng cách thêm nút "giữ lại giấy tờ": nút bắt cán bộ quyết định TRƯỚC khi bấm, mà
// bấm nhầm thì hỏng im lặng (đúng nhược điểm của mọi phương án 2-nút). Thay vào đó: sau khi tạo
// phiên mới, hiện MỘT lời đề nghị kèm TÊN công dân của hồ sơ trước — quyết định trở thành phép
// so bằng mắt "người ngồi trước mặt có phải người này không", và mặc định luôn an toàn
// (không bấm = không có giấy tờ người khác lọt vào).
function archiveCurrentSessionAsPrev() {
  // Dựng snapshot ĐỒNG BỘ từ files[] ngay tại đây, KHÔNG đọc lại SESSION_KEY từ storage: bên gọi
  // xoá files[]/ghi đè session ngay sau lệnh này, đọc storage (bất đồng bộ) dễ vớ phải bản đã bị
  // dọn rỗng. File chưa kịp có dataUrl thì bỏ qua — khôi phục ra file rỗng còn tệ hơn là thiếu.
  const snapFiles = files.filter((it) => it.dataUrl).map(fileItemToSnapshot);
  if (!snapFiles.length) return; // không có giấy tờ nào thì không có gì để mời dùng lại
  const p = currentConsentContext?.principal; // {cccd, name} đọc từ VNeID trên trang, có thì mới có nhãn tên
  const snap = {
    files: snapFiles,
    procedureKey: selectedProcedureKey,
    workProcedureKey,
    archivedAt: Date.now(),
    principalName: p?.name || null,
    principalCccd: p?.cccd || null,
  };
  try {
    void chrome.storage.local.set({ [PREV_SESSION_KEY]: snap });
  } catch (e) {
    console.warn("[Popup] Không lưu được hồ sơ trước để dùng lại:", e);
  }
}

async function clearPrevSession() {
  try {
    await chrome.storage.local.remove(PREV_SESSION_KEY);
  } catch (e) { /* ignore */ }
}

async function readPrevSession() {
  let snap = null;
  try {
    const res = await chrome.storage.local.get(PREV_SESSION_KEY);
    snap = res?.[PREV_SESSION_KEY];
  } catch (e) { /* ignore */ }
  if (!snap || !Array.isArray(snap.files) || !snap.files.length) return null;
  if (Date.now() - Number(snap.archivedAt || 0) > PREV_SESSION_TTL_MS) {
    void clearPrevSession(); // quá hạn - dọn luôn, không giữ giấy tờ công dân trên máy lâu hơn cần thiết
    return null;
  }
  return snap;
}

const prevSessionOfferEl = document.getElementById("prevSessionOffer");

async function renderPrevSessionOffer() {
  if (!prevSessionOfferEl) return;
  // Lời đề nghị CHỈ có nghĩa khi hồ sơ đang trống: đã có giấy tờ nào đó (quét ra, thêm tay, hay
  // vừa bấm dùng lại) nghĩa là cán bộ đang làm hồ sơ cụ thể rồi — dọn luôn cả ngăn lưu để giấy tờ
  // của công dân trước không nằm lại trên máy.
  if (files.length) {
    if (!prevSessionOfferEl.hidden) {
      prevSessionOfferEl.hidden = true;
      void clearPrevSession();
    }
    return;
  }
  const snap = await readPrevSession();
  if (!snap) {
    prevSessionOfferEl.hidden = true;
    return;
  }
  const gio = new Date(snap.archivedAt).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
  // Nhãn nhận diện: có tên VNeID thì hiện tên (cán bộ nhìn là biết ngay có đúng người đang ngồi
  // trước mặt không); không có thì còn số file + giờ, vẫn đủ để phân biệt lượt.
  const moTa = (snap.principalName ? `${snap.principalName} · ` : "")
    + `${snap.files.length} giấy tờ · ${gio}`;

  prevSessionOfferEl.textContent = "";
  const label = document.createElement("span");
  label.className = "prev-offer-label";
  label.textContent = `📎 Hồ sơ trước — ${moTa}`;
  label.title = snap.principalCccd ? "CCCD: " + snap.principalCccd : "";
  const dungLaiBtn = document.createElement("button");
  dungLaiBtn.type = "button";
  dungLaiBtn.className = "prev-offer-use";
  dungLaiBtn.textContent = "Dùng lại";
  dungLaiBtn.title = "Đưa lại toàn bộ giấy tờ của hồ sơ trước vào danh sách (dùng khi CÙNG công dân làm thủ tục tiếp theo)";
  dungLaiBtn.addEventListener("click", () => void reusePrevSession());
  // CỐ Ý KHÔNG có nút "×" bỏ qua: nó xoá vĩnh viễn ngăn "hồ sơ trước", bấm nhầm
  // là mất hẳn giấy tờ không lấy lại được — trong khi lời đề nghị vốn đã tự ẩn
  // và tự dọn ngay khi có file mới vào danh sách. Một nút chỉ có mặt hại.
  prevSessionOfferEl.append(label, dungLaiBtn);
  prevSessionOfferEl.hidden = false;
}

async function reusePrevSession() {
  const snap = await readPrevSession();
  if (!snap) { void renderPrevSessionOffer(); return; }
  await clearPrevSession(); // dùng rồi thì thôi, không mời lại lần nữa
  for (const f of snap.files) {
    if (f?.dataUrl) files.push(fileItemFromSnapshot(f));
  }
  renderFiles();
  refreshAttachStepUI();
  saveSession();
  void renderPrevSessionOffer();
  setStatus(`Đã dùng lại ${snap.files.length} giấy tờ của hồ sơ trước.`, "ok");
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

// ===== Sửa tên file ngay trong danh sách =====
// File máy quét: đổi luôn tên THẬT trên đĩa qua agent (POST /v1/files/rename),
// rồi cập nhật item TẠI CHỖ — không xoá-thêm lại, để giữ nguyên vị trí trong
// danh sách và loại giấy tờ (role) cán bộ đã chọn.
//
// Đổi tên trên đĩa làm watcher bắn ra cặp `file.removed` (tên cũ) +
// `file.added` (tên mới). Cặp đó TỰ TIÊU nếu item đã kịp mang `rel` mới: handler
// xoá không tìm thấy rel cũ, handler thêm thấy trùng rel + trùng hash nên bỏ
// qua. Nhưng event có thể về TRƯỚC phản hồi API — nên đánh dấu rel vào
// `scanDangDoiTen` trước khi gọi, handler xoá thấy dấu này thì không gỡ item.
const scanDangDoiTen = new Set();

function batDauSuaTen(item, li, nameEl) {
  if (li.querySelector(".rename-input")) return; // dang sua roi
  const o = document.createElement("input");
  o.type = "text";
  o.className = "rename-input";
  o.value = item.file.name;
  o.setAttribute("aria-label", "Tên file mới");
  let xong = false;
  const huy = () => { if (!xong) { xong = true; renderFiles(); } };
  o.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); if (!xong) { xong = true; void ketThucSuaTen(item, o.value); } }
    else if (e.key === "Escape") { e.preventDefault(); huy(); }
  });
  o.addEventListener("blur", huy); // bấm ra ngoài = huỷ, không tự lưu (tránh sửa nhầm mà không hay)
  nameEl.replaceWith(o);
  o.focus();
  // Bôi đen phần tên, chừa đuôi file — đuôi gần như không bao giờ cần sửa.
  const cham = item.file.name.lastIndexOf(".");
  o.setSelectionRange(0, cham > 0 ? cham : item.file.name.length);
}

async function ketThucSuaTen(item, tenNhap) {
  const ten = String(tenNhap || "").trim();
  if (!ten || ten === item.file.name) { renderFiles(); return; }
  // File thêm tay/ảnh điện thoại: không có gì trên đĩa để đụng, chỉ đổi tên gửi lên BE.
  if (!item.fromScan || !item.rel) {
    item.file = { name: ten, type: item.file.type };
    renderFiles();
    capNhatTenTrenPreview(item);
    saveSession();
    return;
  }
  if (!scanAgentHelpers?.renameFile) {
    setStatus("Chưa kết nối được máy quét nên chưa đổi tên file trên đĩa được.", "err");
    renderFiles();
    return;
  }
  const relCu = item.rel;
  scanDangDoiTen.add(relCu);
  try {
    const res = await scanAgentHelpers.renameFile(relCu, ten);
    const relMoi = res?.rel || ten;
    scanDangDoiTen.add(relMoi); // chan luon event `file.added` cua chinh minh
    item.rel = relMoi;
    item.file = { name: String(relMoi).split("/").pop(), type: item.file.type };
    renderFiles();
    capNhatTenTrenPreview(item);
    saveSession();
    setStatus(`Đã đổi tên thành "${item.file.name}" (cả trên đĩa).`, "ok");
  } catch (e) {
    // Phân biệt đúng lý do để cán bộ biết phải làm gì, không nuốt thành "lỗi chung".
    const msg = e?.code === "NAME_EXISTS"
      ? `Trong thư mục quét đã có file tên "${ten}" rồi — đặt tên khác.`
      : e?.code === "BAD_NAME"
        ? "Tên không hợp lệ: phải là tên file trần và giữ đuôi .pdf."
        : `Không đổi tên được trên đĩa: ${e?.message || e}`;
    console.warn("[Popup] Đổi tên file máy quét lỗi:", relCu, e);
    setStatus(msg, "err");
    renderFiles();
  } finally {
    // Nới sau một nhịp để cặp event do chính lần đổi tên này sinh ra kịp đi qua.
    const cu = relCu, moi = item.rel;
    setTimeout(() => { scanDangDoiTen.delete(cu); scanDangDoiTen.delete(moi); }, 5000);
  }
}

// ===== Xem trước giấy tờ khi rê chuột =====
// Khung xem trước nằm TRÊN TRANG GỐC (content.js dựng) chứ không trong panel: panel chỉ rộng
// 360px, không xem nổi một tờ A4. Ở đây chỉ phát hiện hover rồi báo sang, không tự vẽ gì.
//
// Chỉ chạy ở chế độ panel nhúng (IS_EMBEDDED). Mở dạng popup toolbar thì không có "trang gốc"
// nào để vẽ lên, mà bản thân popup cũng tự đóng khi mất focus.
const PREVIEW_TRE_MS = 350; // re chuot luot qua danh sach thi khong nhay preview lien tuc
let previewHenHien = null;
let previewKeySeq = 0;
// Key của file ĐANG hiện trên khung xem trước. Theo dõi bằng KEY chứ không phải phần tử <li>:
// renderFiles() dựng lại toàn bộ danh sách nên tham chiếu <li> cũ thành rác ngay sau lần render
// kế tiếp, còn key thì sống theo item.
let previewKeyDangXem = "";
// Key file ĐANG GHIM ("" = không). Nhấn vào dòng file = ghim; content.js giữ trạng thái thật,
// đây chỉ là bản sao để tô dòng và để rê chuột không gửi lệnh đổi file vô ích.
let previewKeyGhim = "";
const previewDaGui = new Set(); // key da gui kem dataUrl -> lan sau chi gui key

function previewKeyCua(item) {
  // Khoá tạm trong bộ nhớ: saveSession() liệt kê field tường minh nên `_previewKey` không bị
  // ghi vào storage; mở lại popup thì sinh khoá mới, content.js cache lại — không sao.
  if (!item._previewKey) item._previewKey = "p" + (++previewKeySeq);
  return item._previewKey;
}

function batDauHoverPreview(item) {
  if (!IS_EMBEDDED) return;
  // Đang ghim file KHÁC → rê chuột không đổi khung (content.js cũng chặn, đây là để khỏi gửi).
  if (previewKeyGhim && item._previewKey !== previewKeyGhim) return;
  huyHenHienPreview();
  // VÀO LẠI ĐÚNG FILE ĐANG XEM → gửi NGAY, không đợi 350ms.
  // Vì sao cần: renderFiles() dựng lại toàn bộ <ul> (đổi tên, file quét mới về, đối soát...),
  // phá luôn <li> đang nằm dưới con trỏ → trình duyệt tự bắn mouseleave + mouseenter. Nếu vẫn
  // đợi 350ms thì lệnh ẩn (hẹn 300ms từ mouseleave) kịp nổ trước → khung TẮT rồi BẬT lại, kèm
  // dựng lại trình xem PDF từ đầu. Gửi ngay thì `hienPreview` bên content.js huỷ luôn lệnh ẩn
  // đang chờ, không có nhịp tắt nào cả.
  if (item._previewKey && previewKeyDangXem === item._previewKey) {
    parent.postMessage({
      type: "autofill-hcc-preview-show",
      key: item._previewKey, name: item.file.name, mime: item.file.type || "",
    }, "*");
    danhDauDongDangXem();
    return;
  }
  previewHenHien = setTimeout(() => {
    previewHenHien = null;
    void guiPreview(item, false);
  }, PREVIEW_TRE_MS);
}

// Gửi file sang content.js để hiện. Dùng chung cho rê chuột (ghim=false) và nhấn dòng (ghim=true).
async function guiPreview(item, ghim) {
  const key = previewKeyCua(item);
  // File vừa thêm bằng "+ Thêm file"/kéo-thả mới chỉ có File object, dataUrl phải đọc ra đã —
  // không đọc thì khung xem trước hiện trắng đúng lúc cán bộ cần kiểm tra nhất.
  if (!item.dataUrl && item.file instanceof Blob) {
    try { item.dataUrl = await readAsDataUrl(item.file); }
    catch (e) { console.warn("[Popup] Không đọc được file để xem trước:", e); }
  }
  const goi = { type: "autofill-hcc-preview-show", key, name: item.file.name, mime: item.file.type || "", ghim };
  if (!previewDaGui.has(key)) {
    goi.dataUrl = item.dataUrl || "";
    if (item.dataUrl) previewDaGui.add(key);
  }
  parent.postMessage(goi, "*");
  previewKeyDangXem = key;
  if (ghim) previewKeyGhim = key;
  danhDauDongDangXem();
}

// Nhấn vào dòng file → GHIM khung xem trước. Nhấn dòng khác khi đang ghim → chuyển ghim sang đó.
function ghimPreview(item) {
  if (!IS_EMBEDDED) return;
  huyHenHienPreview();
  void guiPreview(item, true);
}

// Xin content.js đóng hẳn (bỏ ghim). Nó báo lại "preview-hidden" → mới bỏ tô dòng.
function xinDongPreview() {
  if (!IS_EMBEDDED || !previewKeyDangXem) return;
  huyHenHienPreview();
  parent.postMessage({ type: "autofill-hcc-preview-close" }, "*");
}

// Sửa tên file trong lúc khung xem trước đang hiện chính file đó → đẩy tên mới sang ngay.
// Không gửi kèm dataUrl: nội dung không đổi, content.js đã cache rồi (xem preview-show ở đó).
function capNhatTenTrenPreview(item) {
  if (!IS_EMBEDDED || !item._previewKey || previewKeyDangXem !== item._previewKey) return;
  parent.postMessage({
    type: "autofill-hcc-preview-show",
    key: item._previewKey, name: item.file.name, mime: item.file.type || "",
  }, "*");
}

function huyHenHienPreview() {
  if (previewHenHien) { clearTimeout(previewHenHien); previewHenHien = null; }
}

// Tô sáng đúng dòng đang hiện trên khung xem trước. Gọi lại sau mỗi renderFiles() vì danh sách
// được dựng lại từ đầu, class cũ mất theo.
function danhDauDongDangXem() {
  if (!fileList) return;
  fileList.querySelectorAll("li.dang-xem, li.dang-ghim")
    .forEach((li) => li.classList.remove("dang-xem", "dang-ghim"));
  if (!previewKeyDangXem) return;
  const i = files.findIndex((it) => it._previewKey === previewKeyDangXem);
  const li = i >= 0 ? fileList.children[i] : null;
  li?.classList.add("dang-xem");
  if (li && previewKeyGhim === previewKeyDangXem) li.classList.add("dang-ghim");
}

function ketThucHoverPreview() {
  if (!IS_EMBEDDED) return;
  huyHenHienPreview();
  // Chỉ XIN ẩn — content.js mới là bên quyết định, vì nó biết con trỏ có đang ở trên khung
  // xem trước hay không (rê từ dòng file sang khung thì phải giữ nguyên để còn cuộn xem).
  // Cũng vì thế KHÔNG bỏ tô sáng ở đây: rê chuột sang khung để cuộn thì khung vẫn đang hiện
  // file đó, bỏ tô là mất luôn thông tin "đang xem file nào". Đợi content.js báo đã tắt hẳn.
  parent.postMessage({ type: "autofill-hcc-preview-hide" }, "*");
}

function renderFiles() {
  const roles = effectiveRoles();
  const agent = isAgentMode();
  const attach = isAttachMode();
  // Danh sách vừa đổi → xét lại lời đề nghị "dùng lại hồ sơ trước" (có file thì tự ẩn + dọn ngăn).
  // Rẻ: nhánh có-file thoát ngay, chỉ khi danh sách trống mới đọc storage.
  void renderPrevSessionOffer();
  fileList.innerHTML = "";
  files.forEach((item, i) => {
    const li = document.createElement("li");
    li.addEventListener("mouseenter", () => batDauHoverPreview(item));
    li.addEventListener("mouseleave", ketThucHoverPreview);
    li.addEventListener("click", (e) => {
      // Nút sửa tên / xoá, ô chọn vai trò, ô nhập tên có việc riêng — bấm vào chúng không ghim.
      if (e.target.closest("button, select, input, a, label")) return;
      ghimPreview(item);
    });
    const name = document.createElement("span");
    name.className = "fname";
    // Chỉ còn MỘT loại cảnh báo: nội dung file trên đĩa đã đổi so với bản đang
    // kẹp (reconcileScanAgentFiles). Nhãn "Đã xoá" đã bỏ — file biến mất khỏi
    // thư mục quét là chuyện bình thường sau khi nộp xong, cảnh báo chỉ gây nhiễu.
    // `canhBaoScan === "xoa"` còn sót trong session cũ sẽ rơi xuống nhánh else,
    // hiện tên trơn — không cần dọn dữ liệu cũ.
    if (item.canhBaoScan === "capNhat") {
      name.textContent = `Cập nhật — ${item.file.name}`;
      name.classList.add("fname-capnhat");
      name.title = "Nội dung file trên đĩa đã đổi — đã tự lấy lại bản mới nhất.";
    } else {
      name.textContent = item.file.name;
      name.title = item.file.name;
    }
    if (item._justAdded) {
      // Vừa kéo-thả vào khung xong — flash ngắn để cán bộ thấy rõ đã "vào khung"
      // thật, không phải thả hụt ra ngoài. Tự gỡ cờ + class sau khi hiệu ứng chạy
      // xong, không gọi lại renderFiles() (đỡ vẽ lại toàn bộ danh sách chỉ vì việc này).
      name.classList.add("fname-just-added");
      delete item._justAdded;
      setTimeout(() => name.classList.remove("fname-just-added"), 1500);
    }
    li.append(name);
    if (item.fromPhone) {
      const badge = document.createElement("span");
      badge.className = "from-phone";
      badge.textContent = "📱";
      badge.title = "Ảnh tải từ điện thoại";
      li.append(badge);
    }
    if (item.fromScan) {
      const badge = document.createElement("span");
      badge.className = "from-scan";
      badge.textContent = "🖨️";
      badge.title = "File tự về từ máy quét";
      li.append(badge);
    }
    // Nút sửa tên. File máy quét chỉ hiện khi agent CÓ khả năng "rename" — agent
    // bản cũ chưa có endpoint thì ẩn hẳn, đỡ để cán bộ bấm rồi mới ăn 404.
    // File thêm tay/ảnh điện thoại không có file trên đĩa để đụng tới nên luôn sửa được.
    if (!item.fromScan || scanAgentCaps.includes("rename")) {
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "rename";
      edit.textContent = "✎";
      edit.title = item.fromScan
        ? "Sửa tên file (đổi luôn tên trên đĩa trong thư mục quét)"
        : "Sửa tên file";
      edit.addEventListener("click", () => batDauSuaTen(item, li, name));
      li.append(edit);
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
      ghiNhanDaGo(item); // gỡ là một QUYẾT ĐỊNH — đừng tự pin lại ở lượt gom sau
      files.splice(i, 1);
      renderFiles();
      refreshAttachStepUI();
      saveSession();
    });
    li.append(rm);
    fileList.appendChild(li);
  });
  danhDauDongDangXem(); // danh sach vua dung lai -> to sang lai dong dang xem
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
  // Ô tick "tách hồ sơ" hiện cho MỌI thủ tục split-eligible, gồm cả case local (chứng thực chữ ký
  // người dịch CTV): tick = đa tab (mỗi file 1 hồ sơ), bỏ tick = 1 tab (gộp vào 1 hồ sơ) — giống
  // chứng thực bản sao/chữ ký.
  if (splitModeRow) {
    splitModeRow.style.display = isSplitEligibleProcedure() ? "" : "none";
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

// Kéo-thả file từ NGOÀI vào TOÀN BỘ nội dung popup — lối vào thủ công SONG
// SONG với nút "+ Thêm file" ở trên. ĐỘC LẬP với cơ chế tự pin file máy quét
// (attemptBatchImport phía dưới) — không liên quan, không phụ thuộc nhau.
//
// Nghe trên document CỦA CHÍNH popup.html (dù chạy độc lập hay nhúng trong
// iframe panel nổi) — vẫn là "ở extension", KHÔNG đụng gì tới trang gốc. Xem
// content.js (wireExternalFileDrop): tầng đó CHỈ nghe trên chính
// #autofill-hcc-panel (không nghe trên document trang gốc, cùng lý do) — lo
// phần diện tích thật sự thuộc trang gốc (header, viền quanh iframe); phần
// còn lại (toàn bộ nội dung bên trong iframe) do khối này lo, và khi rơi
// đúng vào #autofill-hcc-panel (ngoài iframe) thì content.js postMessage
// file sang đây (mục dưới) thay vì tự thêm được — file[] chỉ có ở đây.
function isFileDrag(e) {
  const types = e.dataTransfer?.types;
  return !!types && Array.from(types).includes("Files");
}

// Thêm file kéo-thả/nhận qua postMessage vào files[] — dùng chung cho cả 2 đường.
function addDroppedFiles(fileListLike) {
  const list = Array.from(fileListLike || []);
  console.log("[Popup][DnD] addDroppedFiles nhận", list.length, "file:", list.map((f) => f.name));
  if (!list.length) return;
  for (const f of list) files.push({ file: f, role: defaultRoleFor(f), _justAdded: true });
  renderFiles();
  refreshAttachStepUI();
  saveSession();
}

const dropOverlayEl = document.getElementById("dropOverlay");
if (dropOverlayEl) {
  let dragDepth = 0; // dragenter/dragleave long nhau khi re qua cac phan tu con - dem thay vi bat/tat theo 1 su kien
  // BUG ĐÃ SỬA: chỉ gỡ attribute `hidden` KHÔNG đủ để hiện — `.drop-overlay` trong popup.css có
  // sẵn `display: none` như một rule CSS thường (không gắn với [hidden]), nên gỡ `hidden` xong
  // phần tử vẫn `display:none` y nguyên, không bao giờ hiện. Phải tự set `style.display` (giống
  // hệt cách content.js làm với mask của nó).
  const showOverlay = () => {
    dropOverlayEl.hidden = false;
    dropOverlayEl.style.display = "flex";
    requestAnimationFrame(() => { dropOverlayEl.style.opacity = "1"; });
  };
  const hideOverlay = () => {
    dragDepth = 0;
    dropOverlayEl.style.opacity = "0";
    setTimeout(() => {
      if (dropOverlayEl.style.opacity === "0") { dropOverlayEl.style.display = "none"; dropOverlayEl.hidden = true; }
    }, 150);
  };
  document.addEventListener("dragenter", (e) => {
    if (!isFileDrag(e)) return;
    dragDepth++;
    showOverlay();
  });
  document.addEventListener("dragover", (e) => {
    if (isFileDrag(e)) e.preventDefault(); // bat buoc phai preventDefault thi drop moi ban ra
  });
  document.addEventListener("dragleave", (e) => {
    if (!isFileDrag(e)) return;
    dragDepth = Math.max(0, dragDepth - 1);
    if (dragDepth === 0) hideOverlay();
  });
  document.addEventListener("drop", (e) => {
    if (!isFileDrag(e)) return;
    e.preventDefault();
    hideOverlay();
    addDroppedFiles(e.dataTransfer?.files);
  });
}

// Panel nổi (embedded, xem content.js hàm wireExternalFileDrop): file rơi
// đúng vào #autofill-hcc-panel nhưng NGOÀI iframe (header, viền quanh) thì
// content.js postMessage file sang đây — files[] chỉ có ở popup.js, content.js
// không tự thêm được. `e.data.files` là mảng File thật (File/Blob clone được
// nguyên vẹn qua postMessage, không cần serialize).
console.log("[Popup][DnD] khởi tạo — IS_EMBEDDED:", IS_EMBEDDED, "dropOverlay:", !!dropOverlayEl);
if (IS_EMBEDDED) {
  // content.js báo khung xem trước đã tắt hẳn → bỏ tô sáng dòng file.
  window.addEventListener("message", (e) => {
    if (e.source !== window.parent || e.data?.type !== "autofill-hcc-preview-hidden") return;
    previewKeyDangXem = "";
    previewKeyGhim = "";
    danhDauDongDangXem();
  });
  // Bấm ra ngoài khung xem trước — kể cả bấm chỗ khác TRONG panel — là đóng. Trừ bấm vào một dòng
  // file: đó là ghim / chuyển ghim (xem renderFiles). Bắt ở pha capture để nút nào tự
  // stopPropagation cũng không nuốt mất.
  document.addEventListener("pointerdown", (e) => {
    if (!previewKeyDangXem || e.target.closest?.(".file-list li")) return;
    xinDongPreview();
  }, true);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") xinDongPreview();
  });
  // Con trỏ TRONG panel nhưng ngoài dòng file → báo content.js: bằng chứng đã rời khung xem tạm (khi
  // con trỏ nằm trên khung, panel không nhận được mousemove nào). Xem choChuotRoiDi bên content.js.
  let lucBaoChuotORaNgoai = 0;
  document.addEventListener("mousemove", (e) => {
    if (!previewKeyDangXem || previewKeyGhim || e.target.closest?.(".file-list li")) return;
    const gio = Date.now();
    if (gio - lucBaoChuotORaNgoai < 150) return; // mousemove bắn liên tục — gom bớt
    lucBaoChuotORaNgoai = gio;
    parent.postMessage({ type: "autofill-hcc-preview-chuot-o-panel" }, "*");
  }, { capture: true, passive: true });
  // content.js hỏi trước khi hiện hộp xác nhận "Cập nhật": panel có đang xử lý dở không. Cờ bận và bộ đếm
  // request chỉ sống trong iframe này, trang gốc không đọc được.
  window.addEventListener("message", (e) => {
    if (e.source !== window.parent || e.data?.type !== "autofill-hcc-hoi-ban") return;
    const ban = !!window.__AUTOFILL_HCC_POPUP_BUSY__
      || (window.HccTrangThai?.soRequestDangChay?.() || 0) > 0;
    parent.postMessage({ type: "autofill-hcc-tra-loi-ban", ban }, "*");
  });
  console.log("[Popup][DnD] đã gắn listener message (chờ content.js gửi autofill-hcc-drop-files).");
  window.addEventListener("message", (e) => {
    if (e.source !== window.parent) return; // khong phai tu trang cha (content.js) - bo qua
    if (e.data?.type !== "autofill-hcc-drop-files") return; // message khac (resize, page-changed...) khong phai viec o day
    console.log("[Popup][DnD] nhận message autofill-hcc-drop-files từ parent:", e.data);
    addDroppedFiles(e.data.files);
  });
}

function readAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = () => reject(r.error);
    r.readAsDataURL(file);
  });
}

// Hash toàn vẹn nội dung file (hex) — dùng để đối soát file kéo về từ máy
// quét với đúng nội dung đang nằm thật trên đĩa (xem reconcileScanAgentFiles).
async function sha256Hex(blob) {
  const buf = await blob.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buf);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
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
const pullingFids = new Set(); // fid ĐANG kéo dở — thả ra khi xong/hỏng để còn thử lại

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
  const fresh = (list || []).filter((f) => f && f.fid && !pulledFids.has(f.fid) && !pullingFids.has(f.fid));
  // Đánh dấu ĐANG kéo (khác với ĐÃ kéo): lượt poll 2s sau không kéo trùng, nhưng nếu lượt này
  // hỏng/treo thì fid được thả ra để thử lại. Trước đây đánh dấu thẳng vào pulledFids nên tải
  // treo là file bị khoá VĨNH VIỄN, không bao giờ kéo lại và không báo gì.
  fresh.forEach((f) => pullingFids.add(f.fid));
  // Kéo TUẦN TỰ: mỗi file đi qua service worker (fetch + base64 + cắt mảnh). Kéo song song
  // nhiều tệp lớn làm SW phình bộ nhớ rồi bị Chrome giết → mất cả lô.
  const results = [];
  try {
    for (const f of fresh) {
      const res = await api.fetchUploadFileDataUrl(sid, f.fid);
      if (!res || !res.dataUrl) {
        console.warn("[AutoFill] Không kéo được tệp từ điện thoại:", f.name || f.fid);
        setQrStatus("⚠️ Đang tải tài liệu từ điện thoại chậm/lỗi — em thử lại…");
        continue; // để dành cho lượt poll sau
      }
      pulledFids.add(f.fid);
      results.push({ f, res });
    }
  } finally {
    fresh.forEach((f) => pullingFids.delete(f.fid));
  }
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

// ===== Đính kèm tự động từ máy quét (scan-bridge agent chạy trên máy cán bộ) =====
// Khi có một thủ tục đang được làm việc (nhận diện tự động hoặc chọn tay), dò agent
// chạy cục bộ (xem lib/scanAgent.js); nếu có, nghe SSE và kéo file MỚI quét ra về
// files[] y hệt ảnh chọn tay/ảnh điện thoại — cán bộ không phải bấm "Thêm file" nữa.
// Máy không cài scan-bridge (đa số) thì dò mãi không thấy, không hiện gì, không ảnh
// hưởng luồng cũ.
const scanAgentStatusEl = document.getElementById("scanAgentStatus");
const scanRecentListEl = document.getElementById("scanRecentList");
let scanAgentConn = null; // giữ ĐÚNG MỘT kết nối suốt phiên popup, không dò lại mỗi lần detect

function setScanAgentStatus(state) {
  if (!scanAgentStatusEl) return;
  const TEXT = {
    da_ket_noi: "🖨️ Đã kết nối — file quét ra sẽ tự thêm vào danh sách.",
    mat_ket_noi: "🖨️ Mất kết nối, đang thử lại…",
    chua_chon_thu_muc: "🖨️ Đã thấy máy quét nhưng chưa chọn thư mục quét — mở icon agent ở khay hệ thống để chọn.",
  };
  // "dang_do": đa số máy không cài scan-bridge nên phần lớn thời gian sẽ dừng ở
  // trạng thái này — im lặng, không hiện gì, đỡ rối cho người không dùng tính năng.
  const text = TEXT[state] || "";
  scanAgentStatusEl.textContent = text;
  scanAgentStatusEl.hidden = !text;
}

// Tải + hash + thêm/cập nhật MỘT file quét vào files[] — dùng chung cho cả
// đường sống (SSE, handleScanAgentFile) lẫn đường batch-import (xem
// attemptBatchImport/addScanRecentItems bên dưới). KHÔNG tự renderFiles/
// saveSession ở đây: bên gọi tự quyết định gọi 1 lần sau khi xử lý xong cả
// loạt, tránh vẽ lại/ghi session nhiều lần khi thêm nhiều file liên tiếp.
// Trả true nếu files[] thực sự đổi (thêm mới hoặc cập nhật nội dung khác).
// tuDong=true: lượt thêm do MÁY quyết định (gom batch, hoặc event file.added của
// agent). Chỉ những lượt đó mới bị bộ nhớ "đã gỡ thủ công" chặn — cán bộ tự bấm
// thêm lại thì phải được, và lúc đó dấu cũ bị gỡ luôn (họ đã đổi ý).
async function importOneScanFile(evt, fetchBlob, { tuDong = false } = {}) {
  // CHỐT CHẶN TUỔI — đặt ở đây vì đây là chỗ DUY NHẤT cả ba đường thêm file
  // quét đều đi qua (gom batch, event file.added, và cán bộ bấm thêm tay).
  // Trước đây phép kiểm nằm ở nơi gọi: `attemptBatchImport` có, đường SSE thì
  // không — hôm nay chưa gây hại vì SSE lấy *thời điểm sự kiện* làm bằng chứng
  // "vừa xuất hiện" (nên không gửi mtimeMs, và phép kiểm dưới đây tự bỏ qua),
  // nhưng người viết đường thứ tư sẽ không có gì nhắc họ.
  //
  // Kiểm TRƯỚC khi tải: file cũ thì không việc gì phải kéo cả 6MB về rồi mới bỏ.
  const mtimeMs = Number(evt.mtimeMs) || 0;
  if (tuDong && mtimeMs && Date.now() - mtimeMs > BATCH_AUTO_MAX_AGE_MS) {
    console.info("[Popup] Không tự pin %s: file quét lúc %s, quá %d phút.",
      evt.rel, new Date(mtimeMs).toLocaleString(), Math.round(BATCH_AUTO_MAX_AGE_MS / 60000));
    return false;
  }
  // Chốt mốc thứ tự TRƯỚC await đầu tiên: nếu trong lúc đang tải mà có event xoá đúng rel này
  // (rất hay xảy ra khi đổi tên hàng loạt, và file 3MB tải mất cả giây) thì bỏ luôn kết quả —
  // không được push một file vừa bị xoá khỏi đĩa trở vào danh sách chờ gửi lên server.
  const seqBatDau = scanEventSeq;
  const blob = await fetchBlob();
  const dataUrl = await readAsDataUrl(blob);
  const hash = await sha256Hex(blob); // toan ven noi dung luc keo ve, dung de doi soat sau nay
  const seqXoa = scanRemovedAt.get(evt.rel);
  if (seqXoa != null && seqXoa > seqBatDau) return false; // da bi xoa/doi ten giua chung - bo qua
  // Đã bị cán bộ gỡ thủ công → không tự đưa lại vào. Kiểm SAU khi có hash vì
  // bộ nhớ này khoá theo nội dung, không theo tên.
  if (tuDong) {
    if (scanDaGo.has(hash)) return false;
  } else if (scanDaGo.delete(hash)) {
    luuScanDaGo(); // cán bộ chủ động thêm lại → bỏ dấu, lần sau tự pin bình thường
  }
  const name = String(evt.rel || "scan").split("/").pop();
  const type = blob.type || "application/pdf";
  // Ghi nhận mốc thời gian quét mới nhất mà PHIÊN NÀY đã nhận — dùng làm watermark cho phiên sau
  // (xem resetScanBatchImportState/attemptBatchImport). Batch-import có sẵn `mtimeMs`; đường SSE
  // sống chỉ có `at` (thời điểm agent phát event, xem watcher.go type Event).
  const ts = Number(evt.mtimeMs) || Date.parse(evt.at || "") || 0;
  if (ts > scanNewestMs) scanNewestMs = ts;

  const cu = files.find((it) => it.fromScan && it.rel === evt.rel);
  if (cu) {
    if (cu.hash === hash) return false; // dung noi dung, khong co gi de cap nhat
    cu.dataUrl = dataUrl;
    cu.hash = hash;
    cu.file = { name, type };
    cu.canhBaoScan = "capNhat";
  } else {
    files.push({
      file: { name, type }, role: defaultRoleFor({ type }), dataUrl, fromScan: true,
      rel: evt.rel || null, hash, canhBaoScan: null,
    });
  }
  return true;
}

// Agent bắn "file.added" cho CẢ file mới lẫn file đã có `rel` nhưng vừa bị
// ghi đè nội dung khác (không có event "file.changed" riêng — xem
// lib/scanAgent.js). Vì vậy PHẢI tự kiểm rel đã có trong files[] chưa: có
// rồi thì CẬP NHẬT lại đúng item đó (dataUrl/hash mới), không được thêm một
// dòng mới rồi bỏ mặc dòng cũ mang nội dung sai. (Việc kiểm/cập nhật nằm
// trong importOneScanFile ở trên.)
async function handleScanAgentFile(evt, fetchBlob) {
  try {
    const changed = await importOneScanFile(evt, fetchBlob, { tuDong: true });
    if (!changed) return;
    renderFiles();
    refreshAttachStepUI();
    saveSession();
  } catch (e) {
    console.warn("[Popup] Không tải được file từ máy quét:", e);
  }
}

// File quét biến mất khỏi thư mục sau khi đã kéo về: CỐ Ý KHÔNG báo gì.
// File quét biến mất khỏi thư mục → GỠ HẲN khỏi files[], không phải gắn nhãn.
//
// Nguy hiểm nếu không gỡ: file đã bị xoá/đổi tên vẫn nằm chờ và VẪN ĐƯỢC GỬI
// LÊN SERVER khi đính kèm — mà lý do nó bị xoá thường chính là vì nó sai
// (quét lỗi, quét nhầm người). Đây là hỏng SAI DỮ LIỆU, nặng hơn nhiều so với
// phiền phức "mất file đang muốn giữ".
//
// Đổi tên = một cặp `file.added` (tên mới) + `file.removed` (tên cũ), trùng
// `size` và trùng `at` — agent không có event "renamed" riêng. Xử lý gỡ theo
// `rel` là tự khớp luôn ca này: tên mới được thêm vào, tên cũ bị gỡ đi.
function handleScanAgentFileRemoved(evt) {
  if (!evt?.rel) return;
  // Cặp event do CHÍNH TA gây ra khi đổi tên: item đã được cập nhật tại chỗ rồi,
  // gỡ nó đi là xoá oan đúng file vừa đổi tên (xem ketThucSuaTen).
  if (scanDangDoiTen.has(evt.rel)) return;
  // Ghi mốc thứ tự để chặn ĐUA với lượt tải đang dở: importOneScanFile chạy
  // bất đồng bộ (fetch + hash + đọc dataUrl), file 3MB mất cả giây. Nếu event
  // xoá tới giữa chừng mà chỉ gỡ trong files[] thì lượt tải xong sau đó lại
  // push bản vừa bị xoá trở vào — đúng cái bug đang sửa, chỉ khó thấy hơn.
  scanRemovedAt.set(evt.rel, ++scanEventSeq);
  const truoc = files.length;
  for (let i = files.length - 1; i >= 0; i--) {
    const it = files[i];
    if (it.fromScan && it.rel === evt.rel) files.splice(i, 1);
  }
  if (files.length === truoc) return;
  // Gỡ im lặng, KHÔNG báo status: đổi tên hàng loạt sinh ra một loạt event xoá,
  // báo từng cái là đúng kiểu nhiễu vừa bỏ đi. Danh sách tự ngắn lại là phản hồi.
  renderFiles();
  refreshAttachStepUI();
  saveSession();
}

// Đối soát 1 LẦN mỗi phiên popup (không phải mỗi lần EventSource tự nối lại)
// giữa file đã kéo về (fromScan, còn rel) với trạng thái THẬT trên đĩa — bắt
// đúng ca "đã đính kèm rồi nhưng bị xoá/ghi đè thủ công trong lúc popup đóng",
// thứ mà riêng sự kiện sống (SSE) không thấy được vì lúc đó popup chưa mở.
let scanAgentReconciled = false;
async function reconcileScanAgentFiles({ listFiles, fetchBlob }) {
  if (scanAgentReconciled) return;
  scanAgentReconciled = true;
  const targets = files.filter((it) => it.fromScan && it.rel);
  if (!targets.length) return;
  let current;
  try {
    current = await listFiles();
  } catch (e) {
    console.warn("[Popup] Không đối soát được file máy quét (đọc /v1/files lỗi):", e);
    scanAgentReconciled = false; // loi tam thoi - lan noi lai ke tiep thu lai, khong coi la xong
    return;
  }
  // Chốt chặn XOÁ OAN: listFiles() của scanAgent.js trả `{files: []}` KHÔNG kèm `folder` khi
  // request hỏng (agent chưa chọn thư mục, 500, ổ mạng rớt...). Tin vào danh sách rỗng đó mà gỡ
  // là quét sạch mọi giấy tờ đang chờ của cán bộ. Chỉ gỡ khi chắc chắn đọc được thư mục thật.
  const listDangTinCay = typeof current?.folder === "string";
  const conThat = new Set((current.files || []).map((f) => f?.rel).filter(Boolean));
  let changed = false;
  for (const it of targets) {
    // Không còn trên đĩa → GỠ khỏi files[] (cùng chính sách với handleScanAgentFileRemoved):
    // file đã bị xoá/đổi tên trong lúc popup đóng thì không được lặng lẽ gửi lên server.
    if (!conThat.has(it.rel)) {
      if (!listDangTinCay) continue;
      const i = files.indexOf(it);
      if (i >= 0) { files.splice(i, 1); changed = true; }
      continue;
    }
    // Rel còn tồn tại — tải lại NỘI DUNG THẬT để so hash, không suy từ size/mtime
    // (đúng yêu cầu toàn vẹn: kích thước trùng không có nghĩa nội dung không đổi).
    try {
      const blob = await fetchBlob(it.rel);
      const hash = await sha256Hex(blob);
      if (hash !== it.hash) {
        it.hash = hash;
        it.dataUrl = await readAsDataUrl(blob); // dinh kem phai gui dung noi dung MOI, khong phai ban cu
        it.canhBaoScan = "capNhat";
        changed = true;
      } else if (it.canhBaoScan) {
        it.canhBaoScan = null; // xac nhan lai van con nguyen -> bo canh bao cu (vd tung bao xoa nham)
        changed = true;
      }
    } catch (e) {
      console.warn("[Popup] Không đối soát được nội dung file máy quét:", it.rel, e);
    }
  }
  if (changed) {
    renderFiles();
    refreshAttachStepUI(); // doi soat gio co the GO file -> trang thai nut dinh kem phai theo
    saveSession();
  }
}

// ===== Gom batch quét ra TRƯỚC lúc popup mở ("quét trước, mở extension
// sau" — luồng thực tế ở hành chính công, khác giả định ban đầu là mở popup
// rồi mới quét) =====
// Thiết kế đầy đủ: docs/superpowers/specs/2026-09-09-tu-dong-pin-file-quet-design.md
// (repo scan-bridge). Không dùng một ngưỡng thời gian cố định để tách "loạt
// quét công dân này" khỏi "loạt quét công dân khác" — ~70 máy, mỗi cán bộ
// thao tác một kiểu, không đoán được độ trễ mở popup sau khi quét xong. Thay
// vào đó so khoảng cách TƯƠNG ĐỐI giữa các lần quét: quét cách đợt trước rõ
// ràng → tự tin, tự pin thẳng; quét dồn dập đều đặn không có ranh giới rõ
// (vd quét dồn nhiều công dân liên tiếp, ca hiếm) → KHÔNG đoán liều, chỉ hiện
// danh sách để cán bộ tự chọn (mục "Kéo-thả" trong spec là tính năng RIÊNG,
// không liên quan cơ chế này).
const BATCH_SINGLE_FLOOR_MS = 5 * 60 * 1000; // file dung 1 minh: can cach file ke >= 5 phut moi tu tin
const BATCH_GAP_RATIO = 4; // ranh gioi phai >= 4 lan khoang cach noi bo lon nhat da thay
const BATCH_GAP_FLOOR_MS = 20 * 1000; // duoi 20s khong tinh la ranh gioi, chi la nhieu quet lien tuc
const BATCH_MAX_FILES = 30; // qua so nay ma chua thay ranh gioi -> khong doan, coi la khong tu tin
const BATCH_MAX_SPAN_MS = 30 * 60 * 1000; // qua 30 phut ma chua thay ranh gioi -> khong tu tin
const RECENT_LIST_WINDOW_MS = 2 * 60 * 60 * 1000; // cua so hien danh sach fallback: 2 gio gan nhat
// Trần tuổi cho lượt TỰ pin. Watermark chỉ chặn được "cũ hơn phiên trước" — lần
// đầu dùng trên một máy/tab nó bằng 0 nên KHÔNG chặn gì cả, mà thuật toán gom
// batch thì chỉ nhìn khoảng cách TƯƠNG ĐỐI: một thư mục có file cũ ba ngày vẫn
// cho ra "ranh giới rõ ràng" → tự tin → pin nguyên giấy tờ ba ngày trước vào hồ
// sơ đang làm. Đã gặp thật (thư mục Downloads, file 2026-09-08 lẫn 2026-07-30).
//
// Chặt hơn cửa sổ danh sách chọn tay (2 giờ) là CỐ Ý: tự động thì không có ai
// kiểm, còn danh sách thì cán bộ nhìn rồi mới bấm.
const BATCH_AUTO_MAX_AGE_MS = 30 * 60 * 1000;
const RECENT_LIST_MAX = 30; // toi da so dong hien trong danh sach fallback

// Đi ngược từ file mới nhất, mở rộng "batch" từng file, so khoảng cách tới
// file kế với các khoảng cách nội bộ đã thấy trong batch. Trả
// {confident, batch}: confident=true thì batch là danh sách nên tự pin;
// confident=false thì không có ranh giới rõ ràng, batch luôn rỗng.
function phanTichBatchGanNhat(chuaXuLy) {
  if (!chuaXuLy.length) return { confident: true, batch: [] }; // khong co gi moi - xong viec
  const list = [...chuaXuLy].sort((a, b) => b.mtimeMs - a.mtimeMs);
  const batch = [list[0]];
  let maxGapNoiBo = 0;
  for (let i = 1; i < list.length; i++) {
    const gap = list[i - 1].mtimeMs - list[i].mtimeMs;
    const nguong = batch.length === 1
      ? BATCH_SINGLE_FLOOR_MS
      : Math.max(BATCH_GAP_FLOOR_MS, BATCH_GAP_RATIO * maxGapNoiBo);
    if (gap >= nguong) break; // tim thay ranh gioi ro rang -> dung mo rong, tu tin voi batch hien tai
    batch.push(list[i]);
    maxGapNoiBo = Math.max(maxGapNoiBo, gap);
    if (batch.length >= BATCH_MAX_FILES ||
      (list[0].mtimeMs - list[i].mtimeMs) >= BATCH_MAX_SPAN_MS) {
      return { confident: false, batch: [] }; // qua dai ma chua thay ranh gioi -> khong doan
    }
  }
  return { confident: true, batch };
}

function formatRelativeTime(mtimeMs) {
  const diffMin = Math.max(0, Math.round((Date.now() - mtimeMs) / 60000));
  if (diffMin < 1) return "vừa xong";
  if (diffMin < 60) return `${diffMin} phút trước`;
  return `${Math.round(diffMin / 60)} giờ trước`;
}

let scanAgentHelpers = null; // cache {listFiles, fetchBlob, renameFile} tu lan onConnected gan nhat
let scanAgentCaps = []; // kha nang agent tu khai qua /v1/ping (agent ban cu -> rong -> an chuc nang)
let batchImportAttempted = false; // rieng theo PHIEN LAM VIEC (reset cung "files.length = 0"),
// KHAC voi scanAgentReconciled o tren (rieng theo POPUP)
let scanRecentPending = []; // danh sach cho fallback khi KHONG tu tin: [{rel, name, mtimeMs}]

// Mốc thứ tự sự kiện xoá, dùng để chặn đua với lượt tải đang dở (xem
// handleScanAgentFileRemoved/importOneScanFile). Chỉ tăng, không bao giờ reset trong phiên.
let scanEventSeq = 0;
const scanRemovedAt = new Map(); // rel -> seq cua lan xoa gan nhat

// ===== Watermark: chặn tự pin giấy tờ của CÔNG DÂN TRƯỚC vào hồ sơ mới =====
// Bug thật: bấm "Tạo phiên mới" xong, files[] rỗng nên không còn gì để loại trừ, mà loạt file mới
// nhất trên đĩa VẪN LÀ của công dân vừa xong (người mới chưa quét gì) → thuật toán gom batch thấy
// ranh giới rõ ràng → tự tin → pin nguyên hồ sơ người trước sang người mới. Sai người, im lặng,
// nhìn không ra (tên file toàn dạng 2026xxxx.pdf).
//
// Cách chặn: nhớ mốc thời gian quét mới nhất mà phiên trước đã dùng; phiên sau chỉ xét file MỚI
// HƠN mốc đó. Ưu điểm so với bắt cán bộ nhớ thứ tự thao tác: cả hai thứ tự đều đúng — quét người
// mới TRƯỚC rồi mới bấm tạo phiên (file mới hơn mốc → vẫn gom đúng), hay bấm tạo phiên trước rồi
// mới quét (SSE sống tự đưa vào) đều ra kết quả đúng, không phải nhớ gì.
const SCAN_WATERMARK_KEY = "autofill_scan_watermark_" + (EMBEDDED_TAB_ID ?? "popup");
let scanWatermarkMs = 0; // file co mtime <= moc nay da thuoc mot phien TRUOC
let scanNewestMs = 0;    // mtime moi nhat ma PHIEN NAY da nhan tu may quet

// Reset lại ở đúng 2 chỗ đang reset "files.length = 0" (resetProcedureWorkState
// + nút "Phiên mới") — công dân tiếp theo, kể cả trong cùng một popup đang mở,
// phải được thử gom batch lại từ đầu.
function resetScanBatchImportState() {
  // Đẩy watermark lên tới file quét mới nhất mà phiên vừa đóng đã nhận: từ giờ những file cũ hơn
  // hoặc bằng mốc này là giấy tờ của CÔNG DÂN TRƯỚC, không được tự pin vào hồ sơ mới nữa.
  // Giữ trong biến (không đọc lại storage lúc cần) vì attemptBatchImport chạy ngay sau đây vài
  // mili giây — đợi storage ghi xong mới đọc là vớ phải mốc cũ.
  if (scanNewestMs > scanWatermarkMs) scanWatermarkMs = scanNewestMs;
  scanNewestMs = 0;
  try {
    void chrome.storage.local.set({ [SCAN_WATERMARK_KEY]: scanWatermarkMs });
  } catch (e) { /* ignore - mat watermark chi lam mat loc, khong lam hong gi */ }
  batchImportAttempted = false;
  scanRecentPending = [];
  renderScanRecentList();
}

// ===== Nhớ file cán bộ đã GỠ THỦ CÔNG: không bao giờ tự pin lại =====
//
// Gỡ một dòng khỏi danh sách đính kèm là một QUYẾT ĐỊNH, không phải thao tác
// tạm. Trước đây nút × chỉ `files.splice()`: panel dựng lại sau redirect là
// attemptBatchImport chạy lại, thấy file đó "chưa có trong files[]" nên gom vào
// lần nữa — cán bộ gỡ xong quay lại thấy nó nằm đó, và nếu không để ý thì file
// vừa loại vẫn đi lên server.
//
// Nhớ theo HASH NỘI DUNG chứ không theo `rel`: quét đè lên đúng tên file cũ ra
// nội dung KHÁC thì đó là giấy tờ khác, phải được đưa vào bình thường — đúng
// với logic đối soát checksum đang có. Cùng nội dung, dù đổi tên hay nhân bản
// sang rel khác, vẫn là thứ đã bị loại.
const SCAN_DA_GO_KEY = "autofill_scan_da_go_" + (EMBEDDED_TAB_ID ?? "popup");
const SCAN_DA_GO_MAX = 200;                     // trần số bản ghi giữ lại
const SCAN_DA_GO_TTL_MS = 24 * 60 * 60 * 1000;  // quá một ngày thì không còn ý nghĩa
let scanDaGo = new Map(); // hash -> {rel, luc}

async function restoreScanDaGo() {
  try {
    const res = await chrome.storage.local.get(SCAN_DA_GO_KEY);
    const ds = Array.isArray(res?.[SCAN_DA_GO_KEY]) ? res[SCAN_DA_GO_KEY] : [];
    const now = Date.now();
    scanDaGo = new Map(
      ds.filter((e) => e && typeof e.hash === "string" && now - Number(e.luc || 0) < SCAN_DA_GO_TTL_MS)
        .map((e) => [e.hash, { rel: e.rel || null, luc: Number(e.luc) || now }])
    );
  } catch (e) { /* mất bộ nhớ này chỉ làm mất phép chặn, không làm hỏng gì */ }
}

function luuScanDaGo() {
  try {
    const ds = [...scanDaGo.entries()]
      .map(([hash, v]) => ({ hash, rel: v.rel, luc: v.luc }))
      .sort((a, b) => b.luc - a.luc)
      .slice(0, SCAN_DA_GO_MAX);
    scanDaGo = new Map(ds.map((e) => [e.hash, { rel: e.rel, luc: e.luc }]));
    void chrome.storage.local.set({ [SCAN_DA_GO_KEY]: ds });
  } catch (e) { /* ignore */ }
}

// Gọi từ nút × trên từng dòng. File kéo-thả không có hash/rel máy quét → bỏ qua.
function ghiNhanDaGo(item) {
  if (!item?.fromScan || !item.hash) return;
  scanDaGo.set(item.hash, { rel: item.rel || null, luc: Date.now() });
  luuScanDaGo();
}

// Đọc lại watermark lúc mở popup: panel bị dựng lại liên tục sau redirect/postback, mất mốc là
// quay lại đúng bug "bấm tạo phiên mới xong tự pin giấy tờ của công dân trước".
async function restoreScanWatermark() {
  try {
    const res = await chrome.storage.local.get(SCAN_WATERMARK_KEY);
    const ms = Number(res?.[SCAN_WATERMARK_KEY] || 0);
    if (Number.isFinite(ms) && ms > scanWatermarkMs) scanWatermarkMs = ms;
  } catch (e) { /* ignore */ }
}

function renderScanRecentList() {
  if (!scanRecentListEl) return;
  scanRecentListEl.textContent = "";
  if (!scanRecentPending.length) {
    scanRecentListEl.hidden = true;
    return;
  }
  scanRecentListEl.hidden = false;
  const hint = document.createElement("div");
  hint.className = "scan-recent-hint";
  hint.textContent = "Máy quét có nhiều file gần đây, chưa chắc cùng một người — chọn đúng file cần đính kèm:";
  scanRecentListEl.appendChild(hint);
  const addAllBtn = document.createElement("button");
  addAllBtn.type = "button";
  addAllBtn.className = "scan-recent-add-all";
  addAllBtn.textContent = "+ Thêm tất cả";
  addAllBtn.addEventListener("click", () => void addScanRecentItems([...scanRecentPending]));
  scanRecentListEl.appendChild(addAllBtn);
  for (const item of scanRecentPending) {
    const row = document.createElement("div");
    row.className = "scan-recent-row";
    const label = document.createElement("span");
    label.textContent = `${item.name} — ${formatRelativeTime(item.mtimeMs)}`;
    const addBtn = document.createElement("button");
    addBtn.type = "button";
    addBtn.textContent = "+";
    addBtn.title = "Thêm file này vào danh sách đính kèm";
    addBtn.addEventListener("click", () => void addScanRecentItems([item]));
    row.append(label, addBtn);
    scanRecentListEl.appendChild(row);
  }
}

async function addScanRecentItems(items) {
  if (!scanAgentHelpers) return;
  let any = false;
  for (const item of items) {
    try {
      const changed = await importOneScanFile({ rel: item.rel, mtimeMs: item.mtimeMs }, () => scanAgentHelpers.fetchBlob(item.rel));
      if (changed) any = true;
    } catch (e) {
      console.warn("[Popup] Không thêm được file từ danh sách gần đây:", item.rel, e);
    }
    scanRecentPending = scanRecentPending.filter((it) => it.rel !== item.rel);
  }
  renderScanRecentList();
  if (any) {
    renderFiles();
    refreshAttachStepUI();
    saveSession();
  }
}

// Thử gom + tự pin batch quét gần nhất — gọi 1 lần/phiên làm việc, từ 2 điểm:
// selectProcedure() (agent có thể đã kết nối từ trước) và onConnected của
// ScanAgent.connect() (agent kết nối muộn hơn, sau lúc khoá thủ tục). Guard
// "batchImportAttempted" PHẢI được set TRƯỚC await đầu tiên để 2 điểm gọi
// gần như đồng thời không chạy đúp (JS đơn luồng).
async function attemptBatchImport() {
  if (batchImportAttempted) return;
  if (!scanAgentHelpers) return; // agent chua ket noi kip - onConnected se tu goi lai
  batchImportAttempted = true;

  let current;
  try {
    current = await scanAgentHelpers.listFiles();
  } catch (e) {
    console.warn("[Popup] Không đọc được /v1/files để gom batch gần nhất:", e);
    batchImportAttempted = false; // loi tam thoi - lan sau thu lai, khong coi la xong
    return;
  }
  const daCo = new Set(files.filter((it) => it.fromScan && it.rel).map((it) => it.rel));
  const tren0Dia = (current.files || [])
    .filter((f) => f?.rel)
    .map((f) => ({ rel: f.rel, name: f.name || String(f.rel).split("/").pop(), mtimeMs: new Date(f.mtime).getTime() }))
    .filter((f) => Number.isFinite(f.mtimeMs));
  const chuaCo = tren0Dia.filter((f) => !daCo.has(f.rel));
  // Watermark: bỏ mọi file cũ hơn/bằng mốc phiên trước đã dùng — đây là chốt chặn "pin nhầm
  // giấy tờ công dân trước sang hồ sơ mới". File bị ghi đè (cùng rel, nội dung mới) có mtime
  // mới hơn mốc nên vẫn lọt qua, đúng với logic checksum đang có.
  const chuaXuLy = chuaCo.filter((f) => f.mtimeMs > scanWatermarkMs);

  // Nhật ký quyết định. Có nó thì câu "vì sao file này bị/không bị tự pin" trả
  // lời được bằng một dòng console, thay vì phải dựng lại cả môi trường để đoán
  // — đúng thứ đã ngốn cả buổi ngày 2026-09-11.
  console.info("[Popup] Gom batch quét:", {
    tren_dia: tren0Dia.length,
    da_co_trong_danh_sach: tren0Dia.length - chuaCo.length,
    bi_watermark_chan: chuaCo.length - chuaXuLy.length,
    con_ung_vien: chuaXuLy.length,
    watermark: scanWatermarkMs ? new Date(scanWatermarkMs).toLocaleString() : "chưa có",
  });
  if (!chuaXuLy.length) return;

  const { confident, batch } = phanTichBatchGanNhat(chuaXuLy);
  if (confident && !batch.length) return;
  // Lô "tự tin" nhưng đã quá cũ thì KHÔNG tự pin — rơi xuống danh sách chọn tay
  // để cán bộ nhìn rồi quyết. Xét file MỚI NHẤT của lô: lô đã liền mạch về thời
  // gian (BATCH_MAX_SPAN_MS), nên file mới nhất cũ thì cả lô đều cũ.
  const loQuaCu = batch.length > 0 && Date.now() - batch[0].mtimeMs > BATCH_AUTO_MAX_AGE_MS;
  console.info("[Popup] Quyết định:", !confident
    ? "không tự tin về ranh giới lô → để cán bộ chọn tay"
    : loQuaCu
      ? `lô mới nhất quét lúc ${new Date(batch[0].mtimeMs).toLocaleString()} — quá ${Math.round(BATCH_AUTO_MAX_AGE_MS / 60000)} phút → KHÔNG tự pin`
      : `tự pin ${batch.length} file`);
  if (confident && !loQuaCu) {
    let any = false;
    for (const item of batch) {
      try {
        const changed = await importOneScanFile(
          { rel: item.rel, mtimeMs: item.mtimeMs },
          () => scanAgentHelpers.fetchBlob(item.rel),
          { tuDong: true },
        );
        if (changed) any = true;
      } catch (e) {
        console.warn("[Popup] Không tự thêm được file từ batch gần nhất:", item.rel, e);
      }
    }
    if (any) {
      renderFiles();
      refreshAttachStepUI();
      saveSession();
    }
  } else {
    const now = Date.now();
    scanRecentPending = chuaXuLy
      .filter((f) => now - f.mtimeMs <= RECENT_LIST_WINDOW_MS)
      .sort((a, b) => b.mtimeMs - a.mtimeMs)
      .slice(0, RECENT_LIST_MAX);
    renderScanRecentList();
  }
}

// ---- Tự nạp lại khi agent đã đặt bản extension mới lên đĩa ----------------
//
// Vì sao extension phải tự làm: máy trạm không join domain nên Chrome TỪ CHỐI
// tự cập nhật extension tự host (đo 2026-09-11 — Chrome gắn nhãn [BLOCKED] cho
// chính sách tự host trên máy không được quản trị tập trung). Đường còn lại là
// chạy dạng unpacked: agent ghi đè thư mục, và chrome.runtime.reload() là thứ
// DUY NHẤT khiến Chrome đọc lại thư mục đó. Xem
// docs/superpowers/specs/2026-09-11-tu-cap-nhat-extension-qua-agent-design.md
// Nhịp kiểm lại khi đang bận. Ngắn lúc đầu (cán bộ vừa bấm xong một việc là
// rảnh ngay), rồi giãn ra: lý do bận phổ biến nhất là "panel đang mở" — thứ có
// thể kéo dài cả buổi, hỏi mỗi 2 giây suốt buổi chỉ tổ đánh thức service worker
// liên tục mà không được gì.
const EXT_UPDATE_CHU_KY_CHO_MS = 2000;
const EXT_UPDATE_CHU_KY_CHO_DAI_MS = 30000;
const EXT_UPDATE_SO_LUOT_NHANH = 10;
const EXT_UPDATE_THU_KEY = "autofill_ext_update_thu";
// Trần số lần thử cho CÙNG một version. Van an toàn: nếu vì lý do nào đó nạp
// lại xong mà version đang chạy vẫn không đổi (thư mục Chrome nạp KHÁC thư mục
// agent ghi — cán bộ trỏ nhầm chỗ), thì không có trần nghĩa là extension nạp
// lại vô tận và không dùng được nữa.
const EXT_UPDATE_TRAN_THU = 3;
let extUpdateChoSan = "";
let extUpdateHenGio = null;
let extUpdateSoLuotCho = 0;

function extUpdateVersionDangChay() {
  try { return chrome.runtime.getManifest()?.version || ""; } catch (_) { return ""; }
}

// Khởi động bộ theo dõi trạng thái. Cờ bận NGOÀI (luồng điền/đính kèm đang
// chạy) do popup.js tự khai, vì lib/trangThai.js không biết gì về nghiệp vụ.
if (window.HccTrangThai) {
  window.HccTrangThai.batDau({
    layCoBanNgoai: () => !!window.__AUTOFILL_HCC_POPUP_BUSY__,
  });
}

// Bận = nạp lại lúc này sẽ cắt ngang việc cán bộ đang làm dở.
//
// Ba tầng, cố ý tách rời:
//   1. Trạng thái của CHÍNH panel này — lib/trangThai.js gộp request đang chạy,
//      thao tác chuột/phím trên panel LẪN trên trang gốc, con trỏ trong ô nhập,
//      tab ẩn, cửa sổ mất focus.
//   2. Hàng đợi tách hồ sơ — sống trong chrome.storage, không thuộc panel nào.
//   3. Các TAB KHÁC — panel ở tab khác cũng bị giết khi nạp lại, nên phải hỏi.
async function extUpdateDangBanRon() {
  // Thiếu module (nạp lỗi) thì coi như bận vĩnh viễn: thà không bao giờ tự cập
  // nhật còn hơn nạp lại giữa lúc cán bộ đang làm.
  const tt = window.HccTrangThai ? window.HccTrangThai.hienTai() : "dang-lam-viec";
  if (tt === "dang-lam-viec") return true;

  try {
    const o = await chrome.storage.local.get("autofill_split_attach_queue");
    if (o && o.autofill_split_attach_queue) return true; // hàng đợi tách hồ sơ đang chạy
  } catch (_) { /* không đọc được storage thì coi như rảnh */ }

  try {
    const res = await chrome.runtime.sendMessage({ action: "hccCoTabNaoDangLamViec" });
    // Đòi câu trả lời RÕ RÀNG. `res` là undefined trên trình duyệt cũ (sendMessage
    // chưa trả Promise) mà KHÔNG ném lỗi; đọc `res?.co` rồi coi falsy là "rảnh"
    // nghĩa là ở đúng những máy đó extension sẽ nạp lại bất kể cán bộ đang làm gì.
    if (!res || typeof res.co !== "boolean") return true;
    if (res.co) return true;
  } catch (_) {
    return true; // không hỏi được background thì coi như bận
  }
  return false;
}

async function extUpdateDocSoLanThu(version) {
  try {
    const o = await chrome.storage.local.get(EXT_UPDATE_THU_KEY);
    const d = o?.[EXT_UPDATE_THU_KEY];
    return d && d.version === version ? Number(d.so) || 0 : 0;
  } catch (_) { return 0; }
}

async function extUpdateGhiSoLanThu(version, so) {
  try { await chrome.storage.local.set({ [EXT_UPDATE_THU_KEY]: { version, so, luc: Date.now() } }); }
  catch (_) { /* ghi hỏng thì mất van an toàn, không đáng chặn cập nhật */ }
}

async function extUpdateThuNapLai() {
  if (!extUpdateChoSan) return;
  if (await extUpdateDangBanRon()) { extUpdateHenLaiSau(); return; }
  extUpdateSoLuotCho = 0;

  const soDaThu = await extUpdateDocSoLanThu(extUpdateChoSan);
  if (soDaThu >= EXT_UPDATE_TRAN_THU) {
    console.warn("[Popup] Đã thử nạp lại", soDaThu, "lần mà vẫn chưa lên được bản",
      extUpdateChoSan, "— dừng lại. Kiểm tra thư mục Chrome đang nạp có đúng thư mục agent quản không.");
    extUpdateChoSan = "";
    return;
  }
  await extUpdateGhiSoLanThu(extUpdateChoSan, soDaThu + 1);

  // Ghi phiên xuống đĩa TRƯỚC khi nạp lại: reload dựng lại cả trang, files[]
  // chỉ sống sót nhờ restoreSession(). Không chờ ghi xong là mất đúng file vừa ghim.
  try { await saveSession(); } catch (_) { /* vẫn nạp lại: phiên cũ còn hơn kẹt bản cũ */ }

  // Gỡ panel ở MỌI tab trước khi nạp lại. Đo 2026-09-11: nạp lại KHÔNG làm panel
  // biến mất — nó ở nguyên đó nhưng mọi chrome.* bên trong ném "Extension
  // context invalidated", cán bộ bấm nút mà không có gì xảy ra. Gỡ đi thì hỏng
  // trở nên NHÌN THẤY ĐƯỢC, và tự lành: cờ "panel đang mở" được giữ nên lần
  // điều hướng kế tiếp content script mới tự mở lại panel.
  try { await chrome.runtime.sendMessage({ action: "hccGoPanelMoiTab" }); } catch (_) { /* ignore */ }

  console.info("[Popup] Nạp lại extension để lên bản", extUpdateChoSan);
  chrome.runtime.reload();
}

function extUpdateHenLaiSau() {
  extUpdateSoLuotCho++;
  const nhip = extUpdateSoLuotCho <= EXT_UPDATE_SO_LUOT_NHANH
    ? EXT_UPDATE_CHU_KY_CHO_MS
    : EXT_UPDATE_CHU_KY_CHO_DAI_MS;
  // Đang hẹn ĐÚNG nhịp cần thì thôi; đổi nhịp thì đặt lại đồng hồ.
  if (extUpdateHenGio && extUpdateHenGio.nhip === nhip) return;
  if (extUpdateHenGio) clearInterval(extUpdateHenGio.id);
  const id = setInterval(() => {
    if (!extUpdateChoSan) {
      clearInterval(id);
      extUpdateHenGio = null;
      return;
    }
    void extUpdateThuNapLai();
  }, nhip);
  extUpdateHenGio = { id, nhip };
}

// Gọi khi biết version đang nằm TRÊN ĐĨA — lúc SSE mở (onConnected) và khi agent
// báo vừa tráo xong (event extension.updated).
function extUpdateGhiNhan(versionTrenDia) {
  if (!versionTrenDia) return;
  const dangChay = extUpdateVersionDangChay();
  if (!dangChay) return;
  if (versionTrenDia === dangChay) {
    // Đã lên đúng bản: xoá bộ đếm để lần cập nhật SAU lại có đủ 3 lượt thử.
    extUpdateChoSan = "";
    extUpdateSoLuotCho = 0;
    chrome.storage.local.remove(EXT_UPDATE_THU_KEY).catch(() => { });
    return;
  }
  // So KHÁC chứ không so LỚN HƠN: hạ cấp (CMS lùi về bản cũ để chữa cháy) cũng
  // phải tới được máy trạm — đó đúng là lúc cần nó nhất.
  extUpdateChoSan = versionTrenDia;
  // Nhờ background kiểm ngay: nó ghi "bản mới đang chờ" để header hiện nút Cập nhật, khỏi chờ nhịp 1 phút.
  // Bắt cả hai kiểu hỏng: ném đồng bộ (context đã mất) và Promise bị reject (trình duyệt trả Promise dù có
  // callback) — reject không ai bắt là lỗi "unhandled rejection" nổi lên ngoài.
  try {
    const p = chrome.runtime.sendMessage({ action: "hccKiemBanMoiNgay" }, () => void chrome.runtime.lastError);
    if (p && typeof p.catch === "function") p.catch(() => { });
  } catch (_) { /* ignore */ }
  void extUpdateThuNapLai();
}

function ensureScanAgentConnected() {
  if (scanAgentConn || typeof ScanAgent === "undefined") return;
  scanAgentConn = ScanAgent.connect({
    onStatus: setScanAgentStatus,
    onFile: handleScanAgentFile,
    onFileRemoved: handleScanAgentFileRemoved, // GỠ khỏi files[], xem hàm đó
    onExtensionVersion: extUpdateGhiNhan, // bắn cả lúc dò thấy agent lẫn lúc agent tráo xong
    onConnected: (helpers) => {
      scanAgentHelpers = helpers;
      // Agent bản cũ không khai `caps` → mảng rỗng → nút sửa tên bị ẩn (xem renderFiles).
      const capsMoi = Array.isArray(helpers?.caps) ? helpers.caps : [];
      const doiCaps = capsMoi.join() !== scanAgentCaps.join();
      scanAgentCaps = capsMoi;
      if (doiCaps) renderFiles(); // vua biet agent ho tro gi -> ve lai de hien/an nut sua ten
      void (async () => {
        await reconcileScanAgentFiles(helpers);
        await attemptBatchImport();
      })();
    },
  });
}

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
  // Gắn ở ĐÂY (không ở từng call site) để mọi nhánh đính kèm — kể cả client-local split và
  // đăng ký kinh doanh — đều mang cùng một khóa hồ sơ. Thủ tục attach-only không gọi /process
  // nên đây là chỗ DUY NHẤT chấm được mốc bắt đầu cho nhóm đó.
  options.dossierId = ensureDossierId();
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
    // Ô tick "tách hồ sơ" quyết định: đa tab (mỗi file 1 hồ sơ) hay 1 tab (gộp vào hồ sơ hiện tại).
    // 1 file thì luôn 1 hồ sơ, không cần điều phối đa-tab.
    const splitOn = !!attachSplitMode && payloadFiles.length > 1;
    options.splitMode = splitOn;
    const local = buildClientLocalSplitPlan(payloadFiles, clientAttachmentCase(cfg), { merge: !splitOn });
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
    if (splitOn) {
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
    // 1 tab (gộp): đính TẤT CẢ tài liệu vào hồ sơ hiện tại; file thứ 2 trở đi tự thêm thành phần mới.
    setStatus("Đang đính kèm tài liệu vào hồ sơ...", "info");
    const mergeMsg = await buildLocalMergeAttachMessage(cfg.key, local.files, local.attachments);
    const mergeRes = await sendToContent(mergeMsg.message);
    if (mergeMsg.storageKey) { try { await chrome.storage.local.remove(mergeMsg.storageKey); } catch (_) { /* ignore */ } }
    return {
      ...mergeRes,
      requestId: mergeRes?.requestId || traceRes?.requestId,
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
  const failedNames = (attachRes?.failedNames || []).join(", ");
  if (failedNames) msg += `\nKhông đính kèm được, đã bỏ qua: ${failedNames}`;
  // Tệp BỊ LOẠI TỪ ĐẦU: planner bỏ tệp vượt trần dung lượng của cổng (Lào Cai 6 MB) TRƯỚC khi OCR nên
  // nó không có mặt trong kế hoạch, và số "đã đính kèm x/x" vẫn đẹp. Trước đây chỉ ghi console →
  // cán bộ đọc "Đã đính kèm 9/9 file" rồi bấm nộp, trong khi hồ sơ thiếu hẳn Giấy chứng nhận.
  // Nhận ra bằng cách soi tệp nào KHÔNG được mục kế hoạch nào tham chiếu. Tệp bị bỏ có chủ đích
  // (CCCD — planner ghi vào extracted.classified) thì không tính, để hồ sơ bình thường vẫn dọn được.
  const droppedNames = (() => {
    const used = new Set();
    for (const item of rawAttachments) {
      const src = Array.isArray(item?.sourceFileIndexes) && item.sourceFileIndexes.length
        ? item.sourceFileIndexes
        : [item?.fileIndex];
      for (const i of src) if (Number.isInteger(i)) used.add(i);
    }
    const classified = planRes.extracted?.classified;
    // Pipeline không khai classified → không phân biệt được "bỏ có chủ đích" với "bị loại" → im lặng
    // như cũ, không làm phiền các thủ tục khác.
    if (!Array.isArray(classified)) return [];
    const known = new Set(classified.map((c) => String(c?.fileName || "")));
    return payloadFiles
      .map((file, i) => (used.has(i) || known.has(String(file?.name || "")) ? "" : file?.name || ""))
      .filter(Boolean);
  })();
  if (droppedNames.length) {
    msg += `\n⚠ CHƯA vào hồ sơ ${droppedNames.length} tệp (thường do vượt dung lượng cổng cho phép):`
      + `\n${droppedNames.join(", ")}`
      + "\nHãy giảm DPI/quét lại cho nhẹ bớt rồi đính kèm lại — cổng cũng không nhận tệp quá nặng.";
  }
  // errors[] từ BE có thể chứa chi tiết kỹ thuật → đưa xuống "Xem chi tiết", KHÔNG nối thô vào câu chính.
  if (planRes.errors?.length) console.warn("[AutoFill-Attach] Cảnh báo xử lý:", planRes.errors);
  // Đính chưa đủ (attachedCount < số nhóm) hoặc có tệp bị loại → cảnh báo (warn) thay vì báo thành công
  // trọn vẹn. warn cũng giữ lại danh sách giấy tờ (clearFilesAfterAttach) để cán bộ còn tệp mà xử lý.
  const warn = attachedCount < sendFiles.length || droppedNames.length > 0;
  // errors[] của ENGINE đính kèm nói rõ dòng nào trượt ("Không khớp thành phần …", "Chỉ lên được 0/1
  // tệp …"). Trước đây bị nuốt hoàn toàn nên cán bộ thấy "đã đính kèm" mà hồ sơ vẫn thiếu.
  const attachErrors = (attachRes?.errors || []).filter(Boolean);
  if (attachErrors.length) {
    console.warn("[AutoFill-Attach] Lỗi khi gắn file vào trang:", attachErrors);
    if (warn) msg += `\nChưa xong: ${attachErrors.join("; ")}`;
  }
  const toastMessage = warn
    ? "Đã xử lý xong bước đính kèm. Vui lòng rà soát hồ sơ."
    : "Đã đính kèm xong hồ sơ.";
  await showPageToast(toastMessage, warn ? "warn" : "success");
  return { ok: true, message: msg, warn, requestId: planRes.requestId, details: planRes.errors || [] };
}

// Đính kèm XONG TRỌN VẸN → dọn danh sách giấy tờ. Giấy tờ đã nộp lên cổng rồi thì để lại trong
// khung "Giấy tờ" chỉ tổ rối, và nguy hiểm hơn là dễ nộp trùng sang thủ tục/hồ sơ kế tiếp.
//
// Cất sang ngăn "hồ sơ trước" TRƯỚC khi dọn (không thì dọn xong là mất hẳn): cùng công dân làm
// thủ tục thứ hai thì lời đề nghị "Dùng lại" hiện ra ngay — vì dọn xong files[] rỗng, đúng điều
// kiện renderPrevSessionOffer() cần. Xem mục 4.11 trong docs/tich-hop-scan-bridge.md.
//
// KHÔNG dọn khi warn/inProgress: còn nhóm chưa đính được hoặc luồng nhiều bước đang chạy dở —
// dọn đi là mất dấu việc còn dang dở, cán bộ không biết còn thiếu gì.
async function clearFilesAfterAttach(res) {
  if (!res || res.error || res.warn || res.inProgress) return;
  if (!files.length) return;
  archiveCurrentSessionAsPrev();
  files.length = 0;
  renderFiles();
  refreshAttachStepUI();
  await saveSession();
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

// merge=false (đa tab): mỗi file 1 hồ sơ/tab riêng — appendOnOccupied:false (mỗi tab ô trống, đính 1 file).
// merge=true (1 tab): tất cả file vào CÙNG hồ sơ hiện tại — appendOnOccupied:true để file thứ 2 trở đi
// tự thêm thành phần mới trong cùng hồ sơ (giống chứng thực bản sao/chữ ký gộp).
function buildClientLocalSplitPlan(payloadFiles, config, { merge = false } = {}) {
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
      appendOnOccupied: merge,
      detectedType: componentName,
      // Nếu tên bản dịch có chữ CCCD vẫn phải vào hàng 1; không được áp heuristic giấy tùy thân.
      forceFirstRow: true,
    });
  }
  return { files, attachments };
}

// Gửi lệnh đính kèm 1 tab (gộp) cho case local (CTV bản dịch). File lớn → chuyển qua
// chrome.storage.local để tránh vượt trần 64 MiB của tabs.sendMessage (giống nhánh đính kèm thường).
async function buildLocalMergeAttachMessage(procedure, files, attachments) {
  const approxBytes = files.reduce((sum, file) => sum + String(file?.dataUrl || "").length, 0);
  if (approxBytes > 45 * 1024 * 1024) {
    const storageKey = "__af_attach_files_" + Date.now();
    try {
      await chrome.storage.local.set({ [storageKey]: { files } });
      return {
        message: { action: "attachFilesByPlan", procedure, attachments, mode: "merge", filesStorageKey: storageKey },
        storageKey,
      };
    } catch (_) { /* ghi storage lỗi → gửi trực tiếp bên dưới */ }
  }
  return {
    message: { action: "attachFilesByPlan", procedure, files, attachments, mode: "merge" },
    storageKey: "",
  };
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
    // Tệp không có quan hệ hồ sơ (vd giấy tùy thân không khớp người ký nào) thì BỎ RIÊNG tệp đó rồi
    // đính tiếp phần còn lại. Trước đây hủy cả lượt: hỏng 1 tệp là mất sạch, mà kế hoạch được phát
    // lại y nguyên nên thử lại hỏng mãi (sự cố Nghĩa Hưng 21/09/2026, bản Handfree cùng bệnh).
    const usable = entries.filter((entry) => entry.planItem?.bundleId
      && ["signature_document", "identity"].includes(entry.planItem?.bundleRole));
    const skippedNames = entries.filter((entry) => !usable.includes(entry))
      .map((entry) => entry.file?.name || entry.planItem?.fileName || "một tệp");
    if (!usable.some((entry) => entry.planItem.bundleRole === "signature_document")) {
      return { error: "Kế hoạch nhiều hồ sơ không có giấy tờ, văn bản cần chứng thực chữ ký." };
    }
    if (skippedNames.length) {
      console.warn("[AutoFill-Split] bỏ tệp không có quan hệ hồ sơ:", skippedNames);
    }

    const bundleOrder = [];
    const grouped = new Map();
    for (const entry of usable) {
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
    return { bundles, skippedNames };
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
  if (built.skippedNames?.length) {
    showPageToast(`Bỏ qua ${built.skippedNames.length} tệp chưa xếp được vào hồ sơ nào: `
      + built.skippedNames.join(", "), "warn");
  }
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
      // Tab mới là hồ sơ KHÁC trên cổng nhưng vẫn thuộc cùng LƯỢT đính kèm này → dùng CHUNG
      // khóa. Số hồ sơ đếm bằng số sự kiện nộp, nên mỗi tab bấm nộp là một sự kiện trên khóa
      // này. Không mang theo thì tab mới không có session → cú bấm bị bỏ im lặng.
      dossierId,
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
// v1.1 (12/09/2026): đổi tên hệ thống trong lời xin phép thành "Trợ lý nhân dân".
// Đổi số khi SỬA nội dung xin phép (phạm vi/lời cam kết) — bằng chứng đã ký giữ số cũ.
const CONSENT_VERSION = "v1.1";
// 2 kho grants: (1) theo PHIÊN/tab — reset khi "Tạo phiên mới"; (2) theo NGƯỜI (CCCD) — TOÀN CỤC, BỀN
// qua phiên vì consent gắn theo (người + thủ tục): cùng CCCD làm lại đúng thủ tục thì không hỏi lại.
const CONSENT_KEY = "autofill_consent_" + (EMBEDDED_TAB_ID ?? "popup");
const CONSENT_CCCD_KEY = "autofill_consent_cccd";
const CONSENT_STATEMENTS = [
  "Tôi đã đọc, hiểu phạm vi giấy tờ, thông tin được xử lý và mục đích nêu trên; đồng ý cho Trợ lý nhân dân đọc, xử lý và tự động điền dữ liệu vào biểu mẫu.",
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
  rating: document.getElementById("view-rating"),
};
function showView(which) {
  for (const [k, el] of Object.entries(csViews)) if (el) el.hidden = k !== which;
}

// ── Đánh giá trải nghiệm sau khi bấm nộp hồ sơ ─────────────────────────────────────────────
// Câu chữ do BE cấp (dùng chung Handfree); BE bản cũ không trả → RATING_CARD rỗng → tắt lặng lẽ.
let RATING_CARD = null;
const RATING_PENDING_KEY = "autofill_rating_pending";
const RATING_DONE_KEY = "autofill_rating_done";
const RATING_DONE_MAX = 200;
// Mặt cười theo mức: 5 → 1. Vẽ bằng SVG thay vì emoji để cùng nét trên mọi máy cán bộ.
const RATING_FACE_COLOR = { 5: "#12a06a", 4: "#4aa96c", 3: "#c79a2b", 2: "#d97036", 1: "#cf4b3f" };
function ratingFaceSvg(v) {
  const mouth = v >= 4 ? "M8.5 14.5c1 1.6 2.2 2.4 3.5 2.4s2.5-.8 3.5-2.4"
    : v === 3 ? "M8.5 15h7"
      : "M8.5 16.6c1-1.6 2.2-2.4 3.5-2.4s2.5.8 3.5 2.4";
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
    stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9.2"/>
    <circle cx="9" cy="10" r=".9" fill="currentColor" stroke="none"/>
    <circle cx="15" cy="10" r=".9" fill="currentColor" stroke="none"/><path d="${mouth}"/></svg>`;
}
function ratingEsc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/** Hồ sơ đã hỏi rồi → không hỏi lại. Đánh dấu theo dossierId (không theo tab) vì chứng thực
 *  tách nhiều tab dùng CHUNG một khóa và tab nào cũng bấm nộp. */
async function markRatingDone(dossierId) {
  try {
    const store = await chrome.storage.local.get([RATING_PENDING_KEY, RATING_DONE_KEY]);
    const done = Array.isArray(store?.[RATING_DONE_KEY]) ? store[RATING_DONE_KEY] : [];
    if (dossierId && !done.includes(dossierId)) done.push(dossierId);
    await chrome.storage.local.set({
      [RATING_DONE_KEY]: done.slice(-RATING_DONE_MAX),
      [RATING_PENDING_KEY]: null,
    });
  } catch (_) { /* không chặn luồng */ }
}

/** Gửi phiếu. Lỗi mạng KHÔNG được chặn UI: cán bộ đã đánh giá xong thì không có gì để họ làm
 *  lại, và giữ màn hình lại chỉ khiến họ không quay về làm hồ sơ tiếp được. */
async function postRating(dossierId, payload) {
  try {
    await api.dossierRating({ dossierId, ...payload });
    return true;
  } catch (e) {
    console.warn("[AutoFill] Không gửi được đánh giá:", e?.message || e);
    return false;
  }
}

let ratingState = null; // { dossierId, level, reasons:Set, note }

function renderRatingView() {
  const card = RATING_CARD;
  const box = document.getElementById("ratingInner");
  if (!card || !box || !ratingState) return;
  const st = ratingState;

  const close = async (done) => {
    await markRatingDone(st.dossierId);
    ratingState = null;
    if (done) {
      // Cảm ơn hiện NGAY trong khung rồi tự về màn chính — cán bộ không phải bấm thêm nút nào.
      box.innerHTML = `<div class="rt-thanks"><span class="rt-thanks-face">${ratingFaceSvg(st.level || 5)}</span>
        <div class="rt-thanks-tt">${ratingEsc(card.thanks || "Cảm ơn đã đánh giá!")}</div>
        <div class="rt-thanks-sub">${ratingEsc(card.thanksSub || "")}</div></div>`;
      setTimeout(() => { if (!ratingState) showView("main"); }, 2600);
    } else {
      showView("main");
    }
  };

  // ── Bước 1: chọn mức ──
  if (!st.level) {
    box.innerHTML = `
      <div class="rt-title">${ratingEsc(card.title || "")}</div>
      <div class="rt-sub">${ratingEsc(card.subtitle || "")}</div>
      <div class="rt-scale">
        ${(card.scale || []).map((m) => `
          <button type="button" class="rt-opt" data-lv="${m.value}"
                  style="--rc:${RATING_FACE_COLOR[m.value] || "#12a06a"}">
            <span class="rt-face">${ratingFaceSvg(m.value)}</span>
            <span class="rt-nm">${ratingEsc(m.label)}</span>
          </button>`).join("")}
      </div>
      <div class="rt-privacy">🔒 ${ratingEsc(card.privacy || "")}</div>
      <div class="rt-actions"><button type="button" class="rt-skip">${ratingEsc(card.skipLabel || "Bỏ qua")}</button></div>`;

    box.querySelectorAll(".rt-opt").forEach((b) => b.addEventListener("click", () => {
      st.level = Number(b.dataset.lv);
      // GHI NGAY, không chờ bấm "Gửi đánh giá". Bước 2 là bước hay bị bỏ dở nhất; gom lại chờ
      // nó là mất phần lớn phiếu. Giống hệt rate_level của Handfree.
      void postRating(st.dossierId, { level: st.level });
      renderRatingView();
    }));
    box.querySelector(".rt-skip")?.addEventListener("click", () => {
      void postRating(st.dossierId, { skipped: true });
      void close(false);
    });
    return;
  }

  // ── Bước 2: lý do + ý kiến ──
  const good = st.level >= (Number(card.goodThreshold) || 4);
  const list = (good ? card.reasonsGood : card.reasonsBad) || [];
  const picked = (card.scale || []).find((m) => m.value === st.level);
  box.innerHTML = `
    <div class="rt-picked" style="--rc:${RATING_FACE_COLOR[st.level] || "#12a06a"}">
      <span class="rt-face">${ratingFaceSvg(st.level)}</span>
      <span class="rt-picked-nm">${ratingEsc(picked ? picked.label : "")}</span>
      <button type="button" class="rt-change">Chọn lại</button>
    </div>
    <div class="rt-reason-h">${ratingEsc(good ? (card.reasonPromptGood || "") : (card.reasonPromptBad || ""))}</div>
    <div class="rt-sub">${ratingEsc(card.reasonHint || "")}</div>
    <div class="rt-chips">
      ${list.map((t, k) => `<button type="button" class="rt-chip${st.reasons.has(t) ? " sel" : ""}" data-rs="${k}">
        <span class="rt-bx">${st.reasons.has(t) ? "✓" : ""}</span><span>${ratingEsc(t)}</span></button>`).join("")}
    </div>
    <textarea class="rt-note" rows="2" placeholder="${ratingEsc(card.notePlaceholder || "")}">${ratingEsc(st.note)}</textarea>
    <div class="rt-actions">
      <button type="button" class="rt-skip">${ratingEsc(card.skipLabel || "Bỏ qua")}</button>
      <button type="button" class="rt-send">${ratingEsc(card.submitLabel || "Gửi đánh giá")}</button>
    </div>`;

  const readNote = () => { st.note = box.querySelector(".rt-note")?.value || ""; };
  box.querySelector(".rt-change")?.addEventListener("click", () => {
    readNote(); st.level = 0; renderRatingView();
  });
  box.querySelectorAll(".rt-chip").forEach((b) => b.addEventListener("click", () => {
    readNote();
    const t = list[Number(b.dataset.rs)];
    if (st.reasons.has(t)) st.reasons.delete(t); else st.reasons.add(t);
    renderRatingView();
  }));
  box.querySelector(".rt-send")?.addEventListener("click", () => {
    readNote();
    void postRating(st.dossierId, {
      level: st.level, reasons: [...st.reasons], note: st.note.trim(),
    });
    void close(true);
  });
  // "Bỏ qua" ở bước 2 KHÔNG gửi skipped: mức đã chọn ở bước 1 vẫn là ý kiến thật, gửi
  // skipped=true sẽ ghi đè phiếu đó thành "bỏ qua" và xóa mất con số.
  box.querySelector(".rt-skip")?.addEventListener("click", () => { void close(false); });
}

/** Mở màn đánh giá cho một hồ sơ, nếu hồ sơ đó chưa từng được hỏi. */
function openRating(dossierId) {
  if (!dossierId || !RATING_CARD || ratingState) return;
  ratingState = { dossierId, level: 0, reasons: new Set(), note: "" };
  showView("rating");
  renderRatingView();
}

/** Đọc cờ ở storage rồi mở màn đánh giá. Gọi lúc panel dựng xong — bấm nộp thường kéo theo
 *  điều hướng/postback làm panel nạp lại, nên cờ ở storage mới là đường sống sót, không phải
 *  message runtime (message đó bắn lúc panel còn chưa tồn tại). */
async function resumePendingRating() {
  if (!RATING_CARD || ratingState) return;
  try {
    const store = await chrome.storage.local.get([RATING_PENDING_KEY, RATING_DONE_KEY]);
    const pending = store?.[RATING_PENDING_KEY];
    const dossierId = String(pending?.dossierId || "").trim();
    if (!dossierId) return;
    const done = Array.isArray(store?.[RATING_DONE_KEY]) ? store[RATING_DONE_KEY] : [];
    if (done.includes(dossierId)) return;
    // Cờ quá cũ (cán bộ đóng trình duyệt rồi mở lại hôm sau) thì bỏ — hỏi lúc đó là vô nghĩa.
    if (pending.at && Date.now() - Number(pending.at) > 30 * 60 * 1000) {
      await markRatingDone(dossierId);
      return;
    }
    openRating(dossierId);
  } catch (_) { /* không chặn luồng */ }
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
      else setStatus(attachRes.message, attachRes.warn ? "warn" : (attachRes.inProgress ? "info" : "ok"), attachRes.details);
      await clearFilesAfterAttach(attachRes);
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
      cfg.key === "xac-nhan-thong-tin-ho-tich" ||
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
      cfg.key === "cap-lai-chung-chi-hanh-nghe-thu-y" ||
      cfg.key === "cong-bo-co-so-du-dieu-kien-tiem-chung" ||
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
      // [Lào Cai] 1.115667: tài khoản prefill CongDan_tenCongDan/CongDan_soCmnd → mốc chọn CCCD người nộp.
      cfg.key === "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-lao-cai" ||
      cfg.key === "dang-ky-bien-dong-dat-dai-lao-cai" ||
      cfg.key === "chuyen-muc-dich-su-dung-dat-lao-cai" ||
      // [Lào Cai] 1.115679 (bản nộp ở Phường/Xã): hồ sơ hay nộp thay theo Giấy uỷ quyền, và khối
      // người nộp có 6 ô (*) phải điền theo giấy tờ của CHÍNH người đăng nhập → thiếu mốc tài khoản
      // là BE bỏ trống cả khối.
      cfg.key === "chuyen-muc-dich-su-dung-dat-khoan-1-dieu-175" ||
      // [Lào Cai] 1.115694: bắt buộc có mốc tài khoản, nếu không BE sẽ bỏ trống khối người nộp.
      cfg.key === "dang-ky-cap-gcn-dien-tich-tang-them-nhan-chuyen-quyen-mot-phan-thua" ||
      // [Lào Cai] 1.115693: chủ hộ hay thường trú ở tỉnh khác nơi có thửa đất nên gần như luôn ủy
      // quyền cho người tại địa phương đi nộp → mốc tài khoản là thứ DUY NHẤT tách được người nộp
      // khỏi chủ hồ sơ; thiếu nó BE phải đoán mode từ giấy tờ.
      cfg.key === "dang-ky-cap-gcn-dien-tich-tang-them-thay-doi-ranh-gioi" ||
      // [Lào Cai] 1.115677: Mẫu 39 hay do vợ/chồng ký nộp thay → phải có mốc tài khoản mới biết ai đi nộp.
      cfg.key === "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep" ||
      // [Lào Cai] 1.115671: người nộp thường là NGƯỜI ĐẠI DIỆN ký thay tổ chức → phải có mốc tài
      // khoản mới tách được nhân thân người nộp khỏi nhân thân chủ hồ sơ là tổ chức.
      cfg.key === "dang-ky-bien-dong-thoa-thuan-thanh-vien-ho-gia-dinh-theo-ban-an" ||
      // [Lào Cai] 1.115650: chủ hồ sơ thường là DOANH NGHIỆP, hồ sơ đầy người có số định danh (người
      cfg.key === "giao-thue-dat-lao-cai" ||
      // [Lào Cai] 1.115678: hồ sơ giao đất sau trúng đấu giá rất hay nộp thay theo Hợp đồng ủy quyền
      // → mốc tài khoản là thứ DUY NHẤT phân biệt "người trúng đấu giá tự nộp" với "người được ủy
      // quyền nộp thay"; thiếu nó BE phải đoán mode từ giấy tờ.
      cfg.key === "cho-thue-dat-thue-rung" ||
      // [Lào Cai] 1.115690 (hiến đất làm đường): bộ hồ sơ mẫu luôn có Giấy ủy quyền, người đi nộp là
      // người được ủy quyền chứ không phải người tặng cho → mốc tài khoản là thứ DUY NHẤT chốt được
      // mode; thiếu nó BE phải đoán từ giấy tờ và cảnh báo.
      cfg.key === "tang-cho-qsdd-nha-nuoc-chua-cap-gcn" ||
      // [Lào Cai] 1.115681: hồ sơ của TỔ CHỨC KINH TẾ, gần như luôn ủy quyền cho một pháp nhân
      // khác đi nộp → mốc tài khoản vừa chốt mode, vừa quyết định ô "Tên cơ quan/tổ chức" của
      // khối người nộp mang tên đơn vị được ủy quyền hay tên chủ hồ sơ; thiếu nó BE bỏ trống cả khối.
      cfg.key === "to-chuc-kinh-te-nhan-chuyen-nhuong-qsdd-du-an" ||
      // [Lào Cai] 1.115685: hồ sơ thường là người dân TỰ NỘP, nhưng khối "Thông tin người nộp" chỉ
      // được điền khi đối chiếu khớp với tài khoản đang đăng nhập → thiếu mốc là BE bỏ trống cả khối.
      cfg.key === "xac-dinh-lai-dien-tich-dat-o-truoc-01-7-2004" ||
      // [Lào Cai] 1.115682: ca thường gặp là CÁN BỘ MỘT CỬA nộp thay người dân (chủ hồ sơ thường
      // trú tỉnh khác nơi có thửa đất) → mốc tài khoản là thứ DUY NHẤT tách được người nộp khỏi chủ
      // hồ sơ; thiếu nó BE cố ý bỏ trống cả khối "Thông tin người nộp" thay vì điền nhầm nhân thân.
      cfg.key === "su-dung-dat-ket-hop-da-muc-dich-cap-xa" ||
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
    options.dossierId = ensureDossierId();
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
      options.dossierId = ensureDossierId();
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
        setStatus(res.message, res.warn ? "warn" : "ok", res.details);
        await clearFilesAfterAttach(res);
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
    // Nhãn đọc cho cán bộ (BE trả "label", vd "Thành phố Bắc Ninh"); tên khớp option trên cổng
    // DVC vẫn là prov.text và chỉ lấy theo slug ở handler 'change' bên dưới.
    option.textContent = prov.label || prov.text;
    provinceSelect.appendChild(option);
  }
  await applyStoredLocation();

  // Event listeners — KHÔNG có nút Lưu: chọn tới đâu ghi tới đó.
  provinceSelect.addEventListener('change', (e) => {
    const slug = e.target.value;
    currentLocation.provinceSlug = slug;
    // Tên tỉnh lưu lại phải là tên trong danh mục (khớp option trên cổng DVC), KHÔNG phải nhãn
    // đang hiển thị — nhãn có thể khác ("Thành phố Bắc Ninh") thì cổng không tìm ra option.
    currentLocation.province = slug
      ? (locationStore()?.getProvinces?.().find((p) => p.slug === slug)?.text || '')
      : '';
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

/**
 * Tỉnh mà thủ tục ĐẶC THÙ của địa phương bắt buộc phải chọn, đọc từ tiền tố nhãn trong
 * ke_khai_links.json ("Quảng Ninh - Tách thửa…"). Thủ tục chung trả null.
 */
function procedureProvinceFor(link) {
  const match = /^(.+?)\s+-\s+/.exec(String(link?.label || "").normalize("NFC"));
  if (!match) return null;
  return locationStore()?.findProvince?.(match[1]) || null;
}

/**
 * Địa bàn trợ lý sẽ chọn cho thủ tục này. Thủ tục riêng của một tỉnh (vd Quảng Ninh) LUÔN chọn
 * đúng tỉnh đó dù địa chỉ đang lưu là tỉnh khác — chọn tỉnh khác thì cổng không ra thẻ/biểu mẫu
 * của tỉnh. Xã chỉ giữ khi địa chỉ đang lưu thuộc chính tỉnh đó.
 */
function agencyLocationFor(link) {
  const forced = procedureProvinceFor(link);
  if (!forced || forced.slug === currentLocation.provinceSlug) return currentLocation;
  return { province: forced.text, provinceSlug: forced.slug, ward: "" };
}

/** Đủ địa chỉ để "lên đạn" cho MỘT thủ tục cụ thể.
 *
 * Chỉ cần Tỉnh/Thành phố: cổng cho tìm cơ quan khi mới chọn tỉnh, Phường/Xã là tuỳ chọn. Có xã thì
 * trợ lý chọn luôn xã, không có thì chỉ chọn tỉnh rồi bấm tìm.
 */
function locationIsCompleteFor(link) {
  return !!agencyLocationFor(link).provinceSlug;
}

/** Chưa chọn xã (hoặc thủ tục cấp tỉnh) -> trợ lý chỉ chọn ô Tỉnh/Thành phố trên cổng. */
function agencyProvinceOnly(link) {
  return !!(link && link.provinceOnlyAgency) || !agencyLocationFor(link).ward;
}

/**
 * Thủ tục này có tick radio "Sở" cho ĐỊA BÀN đang chọn không.
 *
 * `selectSo` = bật cho mọi tỉnh. `selectSoProvinces` = CHỈ bật ở những tỉnh liệt kê (slug theo
 * /locations/catalog, vd "danang") — cùng một mã TTHC nhưng tỉnh khác vẫn nộp ở Phường/Xã, bật
 * tràn cho cả nước là hồ sơ đi lạc cấp tiếp nhận ngay từ bước chọn cơ quan.
 */
function selectSoFor(link) {
  if (!link) return false;
  if (link.selectSo) return true;
  const provinces = Array.isArray(link.selectSoProvinces) ? link.selectSoProvinces : [];
  return provinces.includes(agencyLocationFor(link).provinceSlug);
}

/** Tên tỉnh để IN RA cho cán bộ đọc; chỗ điền hộ trên cổng vẫn dùng area.province. */
function provinceLabel(provinceText) {
  return locationStore()?.labelFor?.(provinceText) || provinceText;
}

/** Phần địa bàn trợ lý sẽ chọn hộ, để in ra status/toast cho khớp số ô thật trên cổng. */
function agencyAreaLabel(link) {
  const area = agencyLocationFor(link);
  const prov = provinceLabel(area.province);
  // Tick Sở thì cổng KHÔNG dùng tới ô Phường/Xã — in tên xã ra là báo sai việc trợ lý sắp làm.
  if (selectSoFor(link)) return `Sở của ${prov}`;
  if (agencyProvinceOnly(link)) return prov;
  return `${area.ward}, ${prov}`;
}

function showLocationSummary() {
  const prov = provinceLabel(currentLocation.province);
  if (locationIsComplete()) {
    locationStatus.textContent = `✓ ${currentLocation.ward}, ${prov}`;
    locationStatus.className = 'status ok';
  } else if (currentLocation.provinceSlug) {
    locationStatus.textContent = `✓ ${prov} (có thể chọn thêm Phường/Xã)`;
    locationStatus.className = 'status ok';
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
  if (link.needsAgencySelect && !locationIsCompleteFor(link)) {
    keKhaiStatus.textContent =
      'Thủ tục này cần chọn Tỉnh/Thành phố trên cổng — chọn địa chỉ ở mục trên để trợ lý điền hộ.';
    keKhaiStatus.className = 'status warn';
  } else if (link.needsAgencySelect) {
    const area = agencyAreaLabel(link);
    keKhaiStatus.textContent = link.autoConfirm
      ? `Trợ lý sẽ chọn ${area}, bấm "Nộp trực tuyến" rồi "Xác nhận" để vào hồ sơ.`
      : `Trợ lý sẽ tự chọn ${area} và mở biểu mẫu kê khai.`;
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
    const tuBackend = Array.isArray(res?.links) ? res.links : [];
    // Thủ tục cổng tỉnh chưa liên thông DVC quốc gia đi vòng qua thủ tục cầu — cấu hình ở
    // popup-ke-khai-di-vong.js, không phụ thuộc backend.
    keKhaiLinkList = window.KeKhaiDiVong ? window.KeKhaiDiVong.apDungDiVong(tuBackend) : tuBackend;
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
  if (link.needsAgencySelect && locationIsCompleteFor(link)) {
    const area = agencyLocationFor(link);
    await chrome.storage.local.set({
      [AGENCY_ARM_KEY]: {
        province: area.province,
        ward: area.ward,
        // Thủ tục cấp tỉnh: cổng chỉ render ô Tỉnh/Thành phố -> content script bỏ hẳn bước xã.
        // Chưa chọn xã cũng đi theo nhánh này: chỉ chọn tỉnh rồi bấm tìm cơ quan.
        provinceOnly: agencyProvinceOnly(link),
        // Thủ tục cấp Sở: tick radio "Sở" rồi chọn option đầu tiên trong dropdown thay vì chọn Phường/Xã.
        // Cờ chốt theo TỈNH đang chọn (xem selectSoFor) nên phải tính ở đây, không đọc thẳng link.
        selectSo: selectSoFor(link),
        // Trang kết quả cổng QG ra nhiều thẻ khác nhau ở CƠ QUAN THỰC HIỆN -> chuỗi này chốt đúng
        // thẻ phải bấm, thay cho quy ước "lấy thẻ đầu".
        submitCardIncludes: link.submitCardIncludes || "",
        // Thủ tục đặc thù của tỉnh: sau "Nộp trực tuyến" cổng QG ném sang cổng tỉnh, còn ba việc
        // nữa (bấm "Nộp hồ sơ" đúng dòng, đăng nhập riêng, chọn cơ quan tiếp nhận) do
        // content/portal-quangninh.js làm nốt theo đúng cấu hình này.
        provincePortalFlow: link.provincePortalFlow || null,
        // Thủ tục đi vòng (popup-ke-khai-di-vong.js): tới eform cổng tỉnh thì content/portal-doi-ma-tthc.js
        // đổi mã TTHC cầu sang mã đích. Không nhét vào provincePortalFlow — engine Quảng Ninh chỉ kiểm
        // host nên sẽ chạy nhầm trên cổng tỉnh khác.
        doiMaThuTuc: link.doiMaThuTuc || null,
        procedureKey: link.key,
        // Trang kết quả có thể liệt kê nhiều dịch vụ -> content script cần tên để bấm đúng thẻ. Thủ tục đi
        // vòng: trang DVC là của thủ tục CẦU nên dò thẻ theo tên cầu.
        procedureLabel: link.cauLabel || link.label,
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
const switchProcSection = document.getElementById("switchProcSection");
const procedureSection = document.getElementById("procedureSection");
const docsSection = document.getElementById("docsSection");

// Cán bộ TỰ bấm "Chuyển thủ tục khác" -> giữ màn "Đi đến thủ tục" mở dù đang đứng trong trang thủ
// tục (atPortalHome = false). Cờ tắt khi bấm "Quay lại", khi mở trang thủ tục mới, hoặc khi trang
// về lại trang chủ cổng (lúc đó panel tự mở, không cần cờ tay nữa).
let destManualOpen = false;

/** Không có danh mục link kê khai (backend lỗi) thì màn "Đi đến thủ tục" vô dụng -> giấu luôn nút. */
function refreshSwitchProcBtn() {
  if (!switchProcSection) return;
  // Đang ở màn "Đi đến thủ tục" thì đã có ô chọn thủ tục đầy đủ -> giấu khối này như "Loại thủ tục".
  switchProcSection.hidden = keKhaiSection?.dataset.unavailable === "1" || !destSection?.hidden;
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

// ===== "Chuyển thủ tục khác": picker thả xuống ngay dưới nút =====
// Chỉ chọn THỦ TỤC — Tỉnh/Xã dùng luôn địa chỉ đang lưu. Chọn xong là mở trang thủ tục đó ngay.
// Thủ tục cần chọn cơ quan mà chưa có Tỉnh thì mới mở màn "Đi đến thủ tục" đầy đủ để chọn địa chỉ.
const switchProcDropdown = document.getElementById("switchProcDropdown");
const switchProcSearch = document.getElementById("switchProcSearch");
const switchProcList = document.getElementById("switchProcList");

function renderSwitchProcList(query) {
  const needle = normalizeProcedureSearch(query);
  // Mã TTHC gõ tay hay rơi rụng/thừa dấu chấm -> so theo phần số, cần ≥4 chữ số mới coi là tra mã.
  const digits = needle.replace(/\D+/g, "");
  const codeNeedle = digits.length >= 4 ? digits : "";
  switchProcList.innerHTML = "";
  const matched = keKhaiLinks().filter((link) => {
    if (!needle) return true;
    if (normalizeProcedureSearch(link.label).includes(needle)) return true;
    return !!codeNeedle && String(link.code || "").replace(/\D+/g, "").includes(codeNeedle);
  });
  if (!matched.length) {
    const empty = document.createElement("div");
    empty.className = "combo-empty";
    empty.textContent = "Không tìm thấy";
    switchProcList.appendChild(empty);
    return;
  }
  for (const link of matched) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "combo-option" + (link.key === selectedProcedureKey ? " active" : "");
    item.setAttribute("role", "option");
    item.textContent = link.label;
    if (link.code) item.title = `${link.code} — ${link.label}`;
    item.addEventListener("click", () => void onSwitchProcedurePicked(link.key));
    switchProcList.appendChild(item);
  }
}

function setSwitchProcOpen(open) {
  if (!switchProcDropdown || !switchProcedureBtn) return;
  switchProcDropdown.hidden = !open;
  switchProcedureBtn.setAttribute("aria-expanded", open ? "true" : "false");
  if (open) {
    switchProcSearch.value = "";
    renderSwitchProcList("");
    switchProcSearch.focus();
  }
  postPanelHeight();
}

function onSwitchProcedureClick() {
  setSwitchProcOpen(switchProcDropdown?.hidden !== false);
}

async function onSwitchProcedurePicked(key) {
  setSwitchProcOpen(false);
  keKhaiSelect.value = key;
  updateKeKhaiUI();
  const link = selectedKeKhaiLink();
  // Thiếu Tỉnh cho thủ tục phải chọn cơ quan -> mở màn đầy đủ để chọn địa chỉ rồi bấm mở trang.
  if (link?.needsAgencySelect && !locationIsCompleteFor(link)) {
    destManualOpen = true;
    syncDestCombos();
    applyDestOpen(true);
    return;
  }
  await onDestGoClick();
  // Mở trang lỗi thì thông báo nằm ở khối đang ẩn -> đưa ra dòng trạng thái chính.
  if (keKhaiStatus.classList.contains("err")) setStatus(keKhaiStatus.textContent, "err");
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
  if (link.needsAgencySelect && !locationIsCompleteFor(link)) {
    locationStatus.textContent = "Chưa chọn Tỉnh/Thành phố.";
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
  switchProcSearch?.addEventListener("input", () => renderSwitchProcList(switchProcSearch.value));
  switchProcSearch?.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { setSwitchProcOpen(false); switchProcedureBtn.focus(); }
  });
  document.addEventListener("click", (e) => {
    if (switchProcDropdown && !switchProcDropdown.hidden
      && !switchProcDropdown.contains(e.target) && !switchProcedureBtn.contains(e.target)) setSwitchProcOpen(false);
  });
  // Ẩn trước, chờ biết đang ở trang nào rồi mới quyết -> không chớp khối sai màn lúc mở panel.
  applyDestOpen(false);
  await refreshDestVisibility();

  // content/agency-select.js bắn tin mỗi khi trang cổng đổi (kể cả SPA giữ nguyên URL).
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg?.action === "portalFlowChanged") void refreshDestVisibility();
    // Background vừa ghi mốc nộp. Đánh dấu vào RAM để lượt process/đính kèm SAU xoay khóa;
    // nếu chỉ ghi ở storage thì saveSession kế tiếp sẽ đè cờ mất và hồ sơ sau bị gộp vào hồ sơ
    // đã nộp. KHÔNG xoá khóa ở đây — tab tách còn nộp tiếp trên chính khóa này.
    if (msg?.action === "dossierSubmitted" && String(msg.tabId ?? "") === String(EMBEDDED_TAB_ID ?? "")) {
      dossierSubmitted = true;
      // Panel còn sống → mở màn đánh giá ngay. Trang điều hướng làm panel nạp lại thì message
      // này mất, nhưng cờ ở storage vẫn còn và resumePendingRating() sẽ mở.
      void resumePendingRating();
    }
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

  // Cổng đang chặn ở màn/modal đăng nhập VNeID: chưa đăng nhập thì chưa có bước kê khai nào để
  // điền, gọi backend lúc này chỉ tốn lượt OCR. content/agency-select.js đã đỗ ở chặng "login" và
  // sẽ tự vào hồ sơ khi công dân xác thực xong — cán bộ chỉ cần bấm quét lại sau đó.
  if (state.loginRequired) {
    setStatus(state.loginHint || "Cổng yêu cầu đăng nhập để vào hồ sơ.", "warn");
    return false;
  }

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
