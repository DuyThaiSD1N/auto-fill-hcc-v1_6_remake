// Popup = client thuần: đăng nhập, chọn thủ tục + file, gửi BE xử lý, nhận fields →
// nhờ content.js điền DOM. Toàn bộ OCR/LLM/mapping nằm ở backend.

// ===== DOM refs =====
const loginScreen = document.getElementById("loginScreen");
const mainScreen = document.getElementById("mainScreen");
const loginUsername = document.getElementById("loginUsername");
const loginPassword = document.getElementById("loginPassword");
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
const handwritingToggle = document.getElementById("handwritingToggle");
const handwritingRow = document.getElementById("handwritingRow");
const splitModeToggle = document.getElementById("splitModeToggle");
const splitModeRow = document.getElementById("splitModeRow");
const ocrBtn = document.getElementById("ocrBtn");
const attachStepBtn = document.getElementById("attachStepBtn");
const dangKyBySelect = document.getElementById("dangKyBy");
const dangKyByLabel = document.querySelector('label[for="dangKyBy"]');
const requestModeSelect = document.getElementById("requestMode");
const requestModeLabel = document.querySelector('label[for="requestMode"]');
const statusEl = document.getElementById("status");
const reviewCardEl = document.getElementById("reviewCard");
const supportCodeBtn = document.getElementById("supportCode");
const supportCodeValueEl = document.getElementById("supportCodeValue");
const uploadLabel = document.querySelector('label[for="fileInput"]');

// Danh sách thủ tục lấy từ BE: [{ key, label, roles:[{value,label}], useDangKyBy }]
let PROCEDURES = [];
let lastProcessSession = null; // { procedure, sessionId }
let selectedProcedureKey = "";
let selectedBusinessPageKey = "";
let procedureSearchQuery = "";
let procedureLocked = false; // true = thủ tục tự nhận diện theo trang, khóa không cho đổi tay
let currentUser = null; // user đang đăng nhập; dùng cho default theo phường/tài khoản ở HKD.
const DEFAULT_PROCEDURE_KEYS = [];
const SEARCH_PROCEDURE_LIMIT = 5;

// Chế độ đính kèm "tách hồ sơ" (split): CHỈ cho chứng thực. Mặc định TẮT = 1 hồ sơ nhiều file (merge).
const SPLIT_MODE_KEY = "autofill_attach_split_mode";
const SPLIT_MODE_PROCEDURES = new Set(["chung-thuc-ban-sao", "chung-thuc-chu-ky"]);
const SPLIT_RELOADABLE_WALLET_CODES = new Set([
  "wallet-stale-modal",
  "wallet-modal-not-opened",
  "wallet-device-upload-not-opened",
]);
let attachSplitMode = false; // hiệu lực từ ô tick (đã khôi phục từ storage)

function isSplitEligibleProcedure() {
  return isAttachMode() && SPLIT_MODE_PROCEDURES.has(currentConfig().key);
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
        files: ["content/bbox-overlay.js", "content.js", "content/attach-mae.js", "content/fill-angular.js", "content/fill-liz.js", "content/fill-legacy.js", "content/fill-bacninh.js", "content/procedures/business-registration.js", "content/review.js"],
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

// friendlyError() + errorSupportCode() nằm ở api/errors.js (nạp trước popup.js) — 1 nguồn chân lý.
// setStatus nhận input là Error (ưu tiên map theo MÃ lỗi BE) hoặc string; lỗi luôn được rút gọn an toàn.
function setStatus(input, type) {
  if (type === "err") {
    const code = (typeof errorSupportCode === "function") ? errorSupportCode(input) : null;
    if (code) showSupportCode(code);
    statusEl.textContent = friendlyError(input);
  } else {
    statusEl.textContent = String(input == null ? "" : input);
  }
  statusEl.className = "status" + (type ? " " + type : "");
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
function showLogin() {
  currentUser = null;
  loginScreen.hidden = false;
  mainScreen.hidden = true;
  prefillLogin();
}

async function prefillLogin() {
  try {
    const saved = await CredStore.get();
    if (!saved) return;
    if (saved.username && !loginUsername.value) loginUsername.value = saved.username;
  } catch (_) {
  }
}

function showMain(user) {
  currentUser = user || null;
  loginScreen.hidden = true;
  mainScreen.hidden = false;
  userLabel.textContent = user?.name || user?.username || "";
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
    await restoreSession();
    await restoreConsent();   // khôi phục trạng thái đồng ý của phiên qua reload trang
    await autoDetectAndLockProcedure();
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
    await CredStore.save(username);
    loginPassword.value = "";
    loginStatus.textContent = "";
    showMain(data.user);
    await loadProcedures();
    await restoreSplitMode();
    await restoreSession();
    await restoreConsent();   // khôi phục trạng thái đồng ý của phiên qua reload trang
    await autoDetectAndLockProcedure();
  } catch (e) {
    console.warn("[Popup] Đăng nhập lỗi:", e);
    loginStatus.textContent = friendlyError(e);   // INVALID_CREDENTIALS → "Sai tên đăng nhập hoặc mật khẩu."
    loginStatus.className = "status err";
  } finally {
    loginBtn.disabled = false;
  }
});

loginPassword.addEventListener("keydown", (e) => {
  if (e.key === "Enter") loginBtn.click();
});

logoutBtn.addEventListener("click", async () => {
  await AuthStore.clearTokens();
  currentUser = null;
  await clearSession();
  files.length = 0;
  if (handwritingToggle) handwritingToggle.checked = false;
  lastProcessSession = null;
  renderFiles();
  refreshAttachStepUI();
  setStatus("", "");
  showLogin();
});

// Tạo phiên mới: xoá file + kết quả + sessionId của TAB hiện tại (giữ đăng nhập, giữ thủ tục đã chọn).
if (newSessionBtn) {
  newSessionBtn.addEventListener("click", async () => {
    await clearSession();
    files.length = 0;
    if (handwritingToggle) handwritingToggle.checked = false;
    lastProcessSession = null;
    // Đưa TẤT CẢ về mặc định: bỏ chọn thủ tục + mở khóa, xoá ô tìm, xoá card rà soát.
    selectedProcedureKey = "";
    selectedBusinessPageKey = "";
    procedureLocked = false;
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
    await autoDetectAndLockProcedure();
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

function buildBusinessDefaults(user) {
  if (!isXuanHuongBusinessUser(user)) return null;
  return { businessActText: XUAN_HUONG_BUSINESS_ACT_TEXT };
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

function getVisibleProcedures(query) {
  const q = normalizeProcedureSearch(query);
  if (!q) return [];  // CHƯA gõ tìm → KHÔNG gợi ý thủ tục nào (không mặc định chung-thuc-ban-sao)
  return PROCEDURES.filter((p) => {
    const haystack = normalizeProcedureSearch(`${p.label || ""} ${p.key || ""}`);
    return haystack.includes(q);
  }).slice(0, SEARCH_PROCEDURE_LIMIT);
}

function renderProcedureResults(query = procedureSearchQuery) {
  if (!procedureResults) return;
  const selected = selectedProcedureConfig();
  const prefix = procedureLocked ? "🔒 Tự nhận diện: " : "Đang chọn: ";
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

  // Trang tự nhận diện → KHÓA (không cho đổi tay) + đóng dropdown.
  // KHÔNG dùng thuộc tính [disabled] vì disabled chặn tooltip title khi hover;
  // dùng class .locked (chỉ để tạo kiểu) + openProcedureDropdown() đã tự return khi locked.
  if (procedureTrigger) {
    procedureTrigger.disabled = false;
    procedureTrigger.classList.toggle("locked", procedureLocked);
    procedureTrigger.setAttribute("aria-disabled", procedureLocked ? "true" : "false");
  }
  if (procedureLocked && procedureDropdown && !procedureDropdown.hidden) {
    procedureDropdown.hidden = true;
    if (procedureTrigger) procedureTrigger.setAttribute("aria-expanded", "false");
  }
  procedureResults.innerHTML = "";
  if (procedureLocked) {
    postPanelHeight();
    return;
  }
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
    btn.title = p.label;

    const label = document.createElement("span");
    label.className = "procedure-option-label";
    label.textContent = p.label;
    btn.appendChild(label);

    btn.addEventListener("click", () => selectProcedure(p.key));
    procedureResults.appendChild(btn);
  }
  postPanelHeight();
}

function selectProcedure(key) {
  const next = PROCEDURES.find((p) => p.key === key) || PROCEDURES[0];
  if (!next) return;
  selectedProcedureKey = next.key;
  selectedBusinessPageKey = Array.isArray(next.pages) && next.pages.length ? next.pages[0].key : "";
  procedureSelect.value = next.key;
  closeProcedureDropdown();  // đã chọn → đóng combobox, trigger hiện "Đang chọn: X"
  applyFormUI();
  saveSession();
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
  if (procedureLocked || !procedureDropdown) return;
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
  for (const p of detectables) {
    const inc = p.detect.urlIncludes || [];
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

function setProcedureLocked(locked) {
  procedureLocked = locked;
  renderProcedureResults();
}

// Màn "Chọn loại đăng ký trực tuyến" là điểm bắt đầu dùng chung của mọi thủ tục HKD.
// Không được mang lựa chọn đã lưu từ hồ sơ trước sang đây; chỉ xóa loại thủ tục, giữ file
// để người dùng vẫn có thể chọn đúng thủ tục rồi tiếp tục mà không phải tải lại tài liệu.
async function enterBusinessProcedureChoiceMode() {
  const hadSelectedProcedure = !!selectedProcedureKey;
  selectedProcedureKey = "";
  selectedBusinessPageKey = "";
  procedureSelect.value = "";
  procedureLocked = false;
  closeProcedureDropdown();
  applyFormUI();
  if (hadSelectedProcedure) await saveSession();
}

// Gọi content script lấy tín hiệu trang → nếu nhận diện được thì chọn + khóa thủ tục.
async function autoDetectAndLockProcedure({ clearChoiceSelection = true } = {}) {
  try {
    const res = await sendToContent({ action: "detectProcedure" });
    if (res?.signals?.businessProcedureHint === "choice") {
      // Khi vừa mở popup/chuyển URL: bỏ lựa chọn cũ. Khi người dùng đã chọn tay rồi bấm
      // xử lý: giữ lựa chọn đó để engine biết phải bấm loại đăng ký nào trên cổng.
      if (clearChoiceSelection) await enterBusinessProcedureChoiceMode();
      else setProcedureLocked(false);
      return false;
    }
    const key = detectProcedureKeyFromSignals(res?.signals);
    if (key && PROCEDURES.some((p) => p.key === key)) {
      selectProcedure(key);
      setProcedureLocked(true);
      return true;
    }
  } catch (e) {
    /* không nhận diện được → quay về chọn tay */
  }
  setProcedureLocked(false);
  return false;
}

// Panel nổi (embedded) nhận tín hiệu trang dvc đổi URL (SPA, không F5) → nhận diện lại thủ tục.
// CHỈ đổi khi thủ tục KHÁC hiện tại để tránh reset file/UI khi trang đổi URL nhưng cùng thủ tục.
async function reDetectProcedureOnNav() {
  try {
    const res = await sendToContent({ action: "detectProcedure" });
    if (res?.signals?.businessProcedureHint === "choice") {
      await enterBusinessProcedureChoiceMode();
      return;
    }
    const key = detectProcedureKeyFromSignals(res?.signals);
    if (key && PROCEDURES.some((p) => p.key === key)) {
      if (key !== selectedProcedureKey) selectProcedure(key);
      setProcedureLocked(true);
    }
  } catch (e) {
    /* không nhận diện được → giữ nguyên trạng thái hiện tại */
  }
}

if (IS_EMBEDDED) {
  window.addEventListener("message", (e) => {
    if (e.data?.type === "autofill-hcc-url-changed") reDetectProcedureOnNav();
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
  // hoặc trang tự nhận diện (autoDetectAndLockProcedure).
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

async function saveSession() {
  try {
    await ensureSelectedFilesLoaded();
    await chrome.storage.local.set({
      [SESSION_KEY]: {
        procedureKey: selectedProcedureKey,
        hasHandwriting: !!(handwritingToggle && handwritingToggle.checked),
        files: files.map((it) => ({
          name: it.file.name,
          type: it.file.type || "image/jpeg",
          dataUrl: it.dataUrl,
          role: it.role || "doc",
          hasHandwriting: !!it.hasHandwriting,
        })),
      },
    });
  } catch (e) { /* ignore quota/serialize errors */ }
}

async function clearSession() {
  try { await chrome.storage.local.remove(SESSION_KEY); } catch (e) { /* ignore */ }
}

async function restoreSession() {
  let saved = null;
  try {
    const res = await chrome.storage.local.get(SESSION_KEY);
    saved = res?.[SESSION_KEY];
  } catch (e) { /* ignore */ }
  if (!saved) return;
  if (saved.procedureKey && PROCEDURES.some((p) => p.key === saved.procedureKey)) {
    selectedProcedureKey = saved.procedureKey;
    selectedBusinessPageKey = "";
    procedureSelect.value = saved.procedureKey;
  }
  if (handwritingToggle) handwritingToggle.checked = !!saved.hasHandwriting;
  files.length = 0;
  for (const f of saved.files || []) {
    if (!f?.dataUrl) continue;
    // File khôi phục không có File object thật, nhưng đã có sẵn dataUrl nên đủ để gửi BE.
    files.push({ file: { name: f.name, type: f.type }, role: f.role || "doc", dataUrl: f.dataUrl,
      hasHandwriting: !!f.hasHandwriting, restored: true });
  }
  renderProcedureResults();
  applyFormUI();
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
    // Tick "viết tay" từng tài liệu (ẩn ở chế độ đính kèm — luôn OCR raw).
    if (!attach) {
      const hwLabel = document.createElement("label");
      hwLabel.className = "hw-file";
      hwLabel.title = "Tài liệu có viết tay → OCR Vintern";
      const hwCb = document.createElement("input");
      hwCb.type = "checkbox";
      hwCb.checked = !!item.hasHandwriting;
      hwCb.addEventListener("change", () => {
        item.hasHandwriting = hwCb.checked;
        // Đồng bộ tick master: bật khi TẤT CẢ file được tick.
        if (handwritingToggle) handwritingToggle.checked = files.length > 0 && files.every((it) => it.hasHandwriting);
        saveSession();
      });
      hwLabel.append(hwCb, document.createTextNode(" viết tay"));
      li.append(hwLabel);
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
    ocrBtn.textContent = isAttachMode() ? "Đính kèm vào hồ sơ" : "Quét và nhập dữ liệu";
  }
  // Nút gộp (quét cả 8 trang + tự đính kèm) chỉ hiện cho thủ tục đăng ký kinh doanh.
  if (fillAllBtn) fillAllBtn.hidden = !isBusiness;
  // Đính kèm luôn dùng OCR raw → ẩn lựa chọn "Có bản viết tay".
  if (handwritingRow) handwritingRow.style.display = isAttachMode() ? "none" : "";
  // Ô tick "tách hồ sơ" chỉ hiện với thủ tục chứng thực (bản sao/chữ ký) ở chế độ đính kèm.
  if (splitModeRow) splitModeRow.style.display = isSplitEligibleProcedure() ? "" : "none";
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

procedureSelect.addEventListener("change", () => selectProcedure(procedureSelect.value));
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
      if (first) selectProcedure(first.key);  // Enter → chọn kết quả đầu tiên (tự đóng)
    } else if (e.key === "Escape") {
      e.preventDefault();
      closeProcedureDropdown();
    }
  });
}
requestModeSelect.addEventListener("change", applyFormUI);
if (handwritingToggle) handwritingToggle.addEventListener("change", () => {
  // Tick trên cùng (master) → tích/bỏ viết tay cho TẤT CẢ tài liệu.
  const on = !!handwritingToggle.checked;
  files.forEach((it) => { it.hasHandwriting = on; });
  renderFiles();
  saveSession();
});
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

fileInput.addEventListener("change", () => {
  // File mới kế thừa trạng thái tick master ("viết tay tất cả").
  const hw = !!(handwritingToggle && handwritingToggle.checked);
  for (const f of fileInput.files) files.push({ file: f, role: defaultRoleFor(f), hasHandwriting: hw });
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
    try { phoneUploadWs.onclose = null; phoneUploadWs.onmessage = null; phoneUploadWs.onerror = null; phoneUploadWs.close(); } catch (_) {}
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
      hasHandwriting: false, fromPhone: true,
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
    phoneUploadWs.onerror = () => { try { phoneUploadWs && phoneUploadWs.close(); } catch (_) {} };
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
    hasHandwriting: !!it.hasHandwriting,
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
        out.push({ ...f, ...pdf }); // name/type/dataUrl thành PDF; giữ role/hasHandwriting
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

// GỘP theo kế hoạch BE: item có sourceFileIndexes>1 → gộp các file gốc thành 1 PDF (đúng thứ tự),
// rồi viết lại fileIndex. Không có nhóm gộp nào → trả nguyên. Lỗi gộp 1 nhóm → đính file đầu, không chặn.
async function applyMergeGroups(payloadFiles, attachments) {
  const hasMerge = (attachments || []).some(
    (a) => Array.isArray(a.sourceFileIndexes) && a.sourceFileIndexes.length > 1
  );
  if (!hasMerge || !window.PdfConvert) return { files: payloadFiles, attachments };

  const outFiles = [];
  const outAtts = [];
  for (const item of attachments) {
    const src = Array.isArray(item.sourceFileIndexes) && item.sourceFileIndexes.length
      ? item.sourceFileIndexes
      : [item.fileIndex];
    const sources = src.map((i) => payloadFiles[i]).filter(Boolean);
    if (!sources.length) continue;

    let file = sources[0];
    if (sources.length > 1) {
      try {
        const merged = await PdfConvert.mergeToPdf(sources, item.documentName || sources[0].name);
        file = { ...sources[0], ...merged }; // giữ role/hasHandwriting, thay name/type/dataUrl
      } catch (e) {
        console.warn("[PdfConvert] Gộp PDF thất bại, đính file đầu:", e);
        file = sources[0];
      }
    }
    const newIndex = outFiles.length;
    outFiles.push(file);
    outAtts.push({ ...item, fileIndex: newIndex, sourceFileIndexes: [newIndex] });
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
  // Gửi lựa chọn "tách hồ sơ" về BE để lưu vào trace (phục vụ thống kê tách/gộp).
  // Chỉ gắn với thủ tục có ô tick (chứng thực bản sao/chữ ký) — true/false theo người dùng chọn.
  if (isSplitEligibleProcedure()) options.splitMode = !!attachSplitMode;

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

  setStatus("Đang đính kèm file vào hồ sơ...", "info");
  const attachRes = await sendToContent({
    action: "attachFilesByPlan",
    procedure: cfg.key,
    files: sendFiles,
    attachments,
    mode: attachSplitMode && isSplitEligibleProcedure() ? "split" : "merge",
  });
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

function isSignatureIdentityPlanItem(item) {
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

  let sharedIdentityFile = null;
  let sharedIdentityPlan = null;
  if (identityEntries.length) {
    const firstIdentity = identityEntries[0];
    sharedIdentityFile = firstIdentity.file;
    sharedIdentityPlan = firstIdentity.planItem;
    if (identityEntries.length > 1) {
      if (!window.PdfConvert) {
        return { error: "Không thể gộp các file giấy tùy thân để dùng chung cho STT2." };
      }
      try {
        const merged = await PdfConvert.mergeToPdf(
          identityEntries.map((entry) => entry.file),
          sharedIdentityPlan.documentName || sharedIdentityFile.name
        );
        sharedIdentityFile = { ...sharedIdentityFile, ...merged };
      } catch (e) {
        return { error: `Không thể gộp các file giấy tùy thân cho STT2: ${e?.message || e}` };
      }
    }
  }

  return {
    bundles: documentEntries.map((entry) => {
      const files = [entry.file];
      const planItems = [planItemForFile([entry.planItem], 0, entry.file, 0)];
      if (sharedIdentityFile && sharedIdentityPlan) {
        files.push(sharedIdentityFile);
        planItems.push({
          ...sharedIdentityPlan,
          fileIndex: 1,
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

function buildDefaultSplitBundles(payloadFiles, attachments) {
  return payloadFiles.map((file, index) => ({
    files: [file],
    planItems: [planItemForFile(attachments, index, file, 0)],
  }));
}

// Tách hồ sơ: bundle[0] → tab hiện tại; bundle[1..] → hàng đợi tuần tự, mỗi lần chỉ 1 tab active.
// Riêng chứng thực chữ ký: mỗi bundle = 1 tài liệu STT1 + cùng một giấy tùy thân dùng chung ở STT2.
async function attachSplitAcrossTabs(payloadFiles, attachments, procedure, planRes) {
  const built = procedure === "chung-thuc-chu-ky"
    ? await buildSignatureSplitBundles(payloadFiles, attachments)
    : { bundles: buildDefaultSplitBundles(payloadFiles, attachments) };
  if (built.error) return built;
  const bundles = built.bundles || [];
  if (!bundles.length) return { error: "Không có tài liệu để tách hồ sơ." };
  const firstBundle = bundles[0];
  const rest = bundles.slice(1);
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
  if (rest.length) {
    queueRes = await sendToBackground({
      action: "startSplitAttachQueue",
      waitForTabId: currentTabRecovery?.tabId || null,
      items: rest.map((bundle, index) => ({
        ordinal: index + 2,
        url: dossierUrl,
        files: bundle.files,
        attachments: bundle.planItems,
        procedure,
      })),
    });
    if (queueRes?.error) return { error: queueRes.error };
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

  let msg =
    (currentTabRecovery
      ? `Tab hồ sơ hiện tại đang được tải lại để tiếp tục đính bộ tài liệu 1.\n`
      : `Đã đính kèm bộ tài liệu 1 vào hồ sơ hiện tại.\n`) +
    `Đã xếp hàng tuần tự ${rest.length} bộ tài liệu còn lại.\n` +
    `Hệ thống chỉ mở và xử lý một tab active; xong tab này mới chuyển sang tab tiếp theo.`;
  if (planRes?.errors?.length) console.warn("[AutoFill-Attach] Cảnh báo xử lý:", planRes.errors);
  return { ok: true, message: msg };
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
  if (!files.length) {
    setStatus("Chưa có file nào.", "err");
    return;
  }
  // Chốt chặn PDPL: chưa đồng ý trong phiên này → hiện điều khoản, KHÔNG điền (đồng ý xong tự chạy lại).
  if (!(await requireConsent(ocrBtn))) return;
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
    await autoDetectAndLockProcedure({ clearChoiceSelection: false });
    if (!selectedProcedureKey) {
      setStatus("Chưa chọn thủ tục. Hãy tìm & chọn thủ tục, hoặc mở đúng trang biểu mẫu rồi thử lại.", "err");
      return;
    }

    const cfg = currentConfig();
    const payloadFiles = buildPayloadFiles();
    const options = {};
    if (cfg.useDangKyBy) options.dangKyBy = dangKyBySelect.value;
    if (cfg.useRequestMode) options.requestMode = requestModeSelect.value;
    // Provider chọn theo TỪNG file (payloadFiles[].hasHandwriting). options.hasHandwriting chỉ là
    // fallback global (BE ưu tiên cờ per-file): bật nếu có bất kỳ tài liệu nào viết tay.
    options.hasHandwriting = payloadFiles.some((f) => f.hasHandwriting);
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
      else setStatus(attachRes.message, attachRes.warn ? "warn" : "ok");
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
      cfg.key === "cap-gcn-attp-nong-lam-thuy-san" ||
      cfg.key === "cap-moi-giay-phep-hanh-nghe-chuyen-tiep" ||
      cfg.key === "cap-chung-chi-hanh-nghe-duoc" ||
      cfg.key === "cap-van-ban-chap-thuan-tau-ca" ||
      cfg.key === "cap-giay-phep-khai-thac-thuy-san" ||
      cfg.key === "dang-ky-bien-phap-bao-dam-qsdd" ||
      cfg.key === "xoa-dang-ky-tau-ca" ||
      cfg.key === "xoa-dang-ky-phuong-tien-thuy" ||
      cfg.key === "dang-ky-bien-dong-dat-dai-da-nang" ||
      cfg.key === "cap-giay-phep-chat-ha-cay-xanh"
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
    try { await maybeShowReview(res.requestId || res.sessionId); }
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
    // Chốt chặn PDPL: luồng quét + đính kèm 8 trang cũng xử lý dữ liệu → chưa đồng ý phiên thì hỏi trước.
    if (!(await requireConsent(fillAllBtn))) return;
    window.__AUTOFILL_HCC_POPUP_BUSY__ = true;
    fillAllBtn.disabled = true;
    try {
      setStatus("Đang đọc file...", "info");
      await ensureSelectedFilesLoaded();
      await autoDetectAndLockProcedure({ clearChoiceSelection: false });
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
      options.hasHandwriting = payloadFiles.some((f) => f.hasHandwriting);

      setStatus(" Đang phân tích tài liệu...", "info");
      const res = await api.process({ procedure: cfg.key, options, files: payloadFiles });
      console.log("[BE fill-all]", { extracted: res.extracted, stats: res.stats });
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

      const startRes = await sendToContent({
        action: isAmendmentWorkflow ? "startChangeBusiness" : "startFillAllBusiness",
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
    await autoDetectAndLockProcedure({ clearChoiceSelection: false }); // giữ lựa chọn tay ở màn HKD dùng chung
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

async function dispatchFill(allFields, errors, page = null) {
  // errors[] từ BE có thể chứa chi tiết OCR/LLM kỹ thuật → chỉ log, KHÔNG hiện thô lên UI.
  if (errors && errors.length) console.warn("[AutoFill] Cảnh báo trích xuất:", errors);
  if (!allFields.length) {
    setStatus("Không đọc được trường nào từ giấy tờ. Kiểm tra lại ảnh/tệp rồi thử lại.", "err");
    return;
  }
  setStatus(page
    ? `Đang điền ${allFields.length} trường vào trang "${page.label}"...`
    : `Đang điền ${allFields.length} trường vào form...`,
    "info"
  );
  const fillRes = await sendToContent({
    action: "fillFields",
    fields: allFields,
    procedure: currentConfig()?.key || "",
    businessPage: page?.key || "",
    businessDefaults: page?.key === "nganh-nghe-kinh-doanh" ? buildBusinessDefaults(currentUser) : null,
  });
  if (fillRes.error) {
    console.warn("[AutoFill] Điền form lỗi:", fillRes.error);
    setStatus(fillRes.error, "err");   // content trả câu sạch (dọn ở content.js); vẫn qua friendlyError để chắc
    return;
  }
  let msg = page
    ? `Đã điền ${fillRes.filled}/${allFields.length} trường ở trang "${page.label}".`
    : `Đã điền ${fillRes.filled}/${allFields.length} trường.`;
  if (fillRes.notFound?.length) msg += `\nKhông khớp: ${fillRes.notFound.join(", ")}`;
  // KHÔNG nối errors[] thô vào thông báo thành công (đã log ở trên).
  // Điền đủ → ok; điền một phần → warn (vàng); không điền được ô nào → err.
  const type = fillRes.filled >= allFields.length ? "ok" : (fillRes.filled ? "warn" : "err");
  setStatus(msg, type);
}

// ===== Rà soát bbox: card "Xem trên ảnh" cho từng ô AI đã điền =====
function clearReviewCard() {
  if (!reviewCardEl) return;
  reviewCardEl.hidden = true;
  reviewCardEl.innerHTML = "";
  postPanelHeight();
}

// Nạp sources theo requestId (BE trả 404 nếu thủ tục không bật review) → đẩy xuống content + render card.
async function maybeShowReview(requestId) {
  clearReviewCard();
  if (!requestId) return;
  const sources = await api.getReviewSources(requestId);
  const byName = sources && sources.fields;
  if (!byName || !Object.keys(byName).length) return;
  await sendToContent({
    action: "attachSources",
    sourcesByName: byName,
    baseUrl: window.BACKEND_URL,
    requestId,
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
if (IS_EMBEDDED && typeof ResizeObserver !== "undefined") {
  const ro = new ResizeObserver(() => postPanelHeight());
  // Quan sát body (chiều cao nội dung) — đổi thủ tục / mở-đóng khối giấy tờ đều đổi body → báo lại panel.
  ro.observe(document.body);
  window.addEventListener("load", postPanelHeight);
}

// ===== Khởi động =====
bootstrap();

// ===== Lịch sử cập nhật (changelog) — thuần FE, dữ liệu ở changelog.js =====
// Trigger là nút "★ Lịch sử" trên HEADER panel (content.js) → gửi postMessage vào iframe này.
(function initReleaseHistory() {
  const pop = document.getElementById("releasePopover");
  const closeBtn = document.getElementById("releaseClose");
  const list = document.getElementById("releaseList");
  if (!pop || !list) return;

  // Version hiện tại lấy TỰ ĐỘNG từ manifest → đánh dấu bản "đang dùng" trong danh sách.
  let current = "";
  try { current = (chrome.runtime.getManifest() || {}).version || ""; } catch (_) {}

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
