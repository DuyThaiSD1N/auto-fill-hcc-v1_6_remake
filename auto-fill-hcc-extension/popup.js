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
const uploadLabel = document.querySelector('label[for="fileInput"]');

// Danh sách thủ tục lấy từ BE: [{ key, label, roles:[{value,label}], useDangKyBy }]
let PROCEDURES = [];
let lastProcessSession = null; // { procedure, sessionId }
let selectedProcedureKey = "";
let selectedBusinessPageKey = "";
let procedureSearchQuery = "";
let procedureLocked = false; // true = thủ tục tự nhận diện theo trang, khóa không cho đổi tay
const DEFAULT_PROCEDURE_KEYS = [];
const SEARCH_PROCEDURE_LIMIT = 5;

// Chế độ đính kèm "tách hồ sơ" (split): CHỈ cho chứng thực. Mặc định TẮT = 1 hồ sơ nhiều file (merge).
const SPLIT_MODE_KEY = "autofill_attach_split_mode";
const SPLIT_MODE_PROCEDURES = new Set(["chung-thuc-ban-sao", "chung-thuc-chu-ky"]);
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
      await chrome.scripting.executeScript({
        target: isAttachmentAction ? { tabId } : { tabId, allFrames: true },
        files: ["content/bbox-overlay.js", "content.js", "content/fill-angular.js", "content/fill-liz.js", "content/fill-legacy.js", "content/fill-bacninh.js", "content/procedures/business-registration.js", "content/review.js"],
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

// Biến lỗi kỹ thuật lằng nhằng (OpenAI 500, JSON, request id, traceback...) thành 1 câu ngắn dễ hiểu.
// Giữ lại câu người-đọc-được nếu có (vd "Không bóc tách được trường nào."), gắn thêm lý do ngắn.
function friendlyError(text) {
  const raw = String(text ?? "").trim();
  if (!raw) return "Có lỗi xảy ra, vui lòng thử lại.";

  // Tách câu người-đọc-được khỏi dòng kỹ thuật (agent:/reason:/OCR:, JSON, Error code, request id...).
  const TECH = /(error code|req_[a-z0-9]{6,}|traceback|exception|"type"|"message"|"param"|help\.|\{['"]?\s*error|http\/?\s?\d{3}|^\s*(agent|reason|ocr)\s*:)/i;
  const lines = raw.split(/\n+/).map((s) => s.trim()).filter(Boolean);
  const humanLines = lines.filter((l) =>
    l.length < 120 && !TECH.test(l) && !/[{}]/.test(l) && !/failed to fetch|networkerror|net::/i.test(l));
  const humanMsg = humanLines.join(" ").trim();
  const hasTech = humanLines.length < lines.length || /[{}]|error code|failed to fetch/i.test(raw);

  // Không có noise kỹ thuật → vốn đã là thông báo cho người dùng, giữ nguyên (chỉ cắt nếu quá dài).
  if (!hasTech) {
    const msg = humanMsg || raw;
    return msg.length > 200 ? msg.slice(0, 197) + "..." : msg;
  }

  // Có noise → quy về 1 lý do ngắn.
  const low = raw.toLowerCase();
  let reason = "Có lỗi khi xử lý, vui lòng thử lại.";
  if (/500|502|503|server_error|server had an error|internal server|overloaded/.test(low))
    reason = "Máy chủ AI đang bận, vui lòng thử lại sau.";
  else if (/429|rate.?limit|quá tải/.test(low))
    reason = "Hệ thống đang quá tải, thử lại sau ít phút.";
  else if (/timeout|timed out|deadline/.test(low))
    reason = "Xử lý quá lâu, vui lòng thử lại.";
  else if (/401|403|unauthorized|forbidden/.test(low))
    reason = "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.";
  else if (/failed to fetch|networkerror|econnrefused|net::|connection refused/.test(low))
    reason = "Không kết nối được máy chủ, kiểm tra mạng rồi thử lại.";
  else if (/400|422|bad request|validation/.test(low))
    reason = "Dữ liệu gửi lên không hợp lệ.";

  // Có câu tiếng Việt rõ nghĩa (không phải fragment kỹ thuật) → giữ + gắn lý do; không thì chỉ lý do.
  if (humanMsg && !/error|exception|fetch/i.test(humanMsg)) return `${humanMsg} ${reason}`;
  return reason;
}

function setStatus(text, type) {
  // Lỗi hiển thị cho user luôn được rút gọn/dễ hiểu; thông báo info/ok giữ nguyên.
  statusEl.textContent = type === "err" ? friendlyError(text) : text;
  statusEl.className = "status" + (type ? " " + type : "");
}

// ===== Auth UI =====
function showLogin() {
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
    await autoDetectAndLockProcedure();
  } catch (e) {
    loginStatus.textContent = e.message || "Đăng nhập thất bại.";
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
        setStatus("Không mở được trang: " + (e.message || e), "err");
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

// Khớp tín hiệu trang (URL + heading) với rule `detect` của thủ tục từ backend.
function detectProcedureKeyFromSignals(signals) {
  if (!signals) return "";
  const detectables = PROCEDURES.filter((p) => p && p.detect);
  const url = String(signals.url || "").toLowerCase();
  const body = normDetect(signals.bodyText || "");

  // 0) Một số thủ tục dùng chung URL cổng chứng thực, nên cần ưu tiên cụm tên thủ tục
  //    rất đặc trưng trước rule URL chung.
  if (body) {
    let bestPriority = "";
    let bestPriorityScore = 0;
    for (const p of detectables) {
      if (!p.detect.textPriority) continue;
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

// Gọi content script lấy tín hiệu trang → nếu nhận diện được thì chọn + khóa thủ tục.
async function autoDetectAndLockProcedure() {
  try {
    const res = await sendToContent({ action: "detectProcedure" });
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
    const key = detectProcedureKeyFromSignals(res?.signals);
    if (key && key !== selectedProcedureKey && PROCEDURES.some((p) => p.key === key)) {
      selectProcedure(key);
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
    setStatus("Không tải được danh sách thủ tục: " + e.message, "err");
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
      ? ".pdf,.jpg,.jpeg,.png,.xml,.mp3,.mp4,.wav,.mov,audio/*,video/*"
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
  if (attachRes?.error) return attachRes;

  const names = (attachRes?.fileNames || []).join(", ");
  const skippedNames = (attachRes?.skippedNames || []).join(", ");
  const attachedCount = Number.isInteger(attachRes?.attached) ? attachRes.attached : sendFiles.length;
  const skippedCount = Number.isInteger(attachRes?.skipped) ? attachRes.skipped : 0;
  let msg = `Đã đính kèm ${attachedCount}/${sendFiles.length} file vào hồ sơ.`;
  if (skippedCount) msg += `\nBỏ qua ${skippedCount} file đã có trong hồ sơ.`;
  if (names) msg += `\n${names}`;
  if (skippedNames) msg += `\nĐã có: ${skippedNames}`;
  if (planRes.errors?.length) msg += `\nCảnh báo xử lý: ${planRes.errors.join("; ")}`;
  return { ok: true, message: msg };
}

// Lấy plan item của BE cho file gốc thứ `origIndex`, reset fileIndex=0 (gửi kèm đúng 1 file lẻ).
function planItemForFile(attachments, origIndex, file) {
  const it = (attachments || []).find((a) => a && a.fileIndex === origIndex) || {};
  return {
    ...it,
    fileIndex: 0,
    fileName: file?.name || it.fileName,
    documentName: it.documentName || file?.name,
    detectedType: it.detectedType || it.documentName || file?.name,
  };
}

// Tách hồ sơ: file[0] → STT1 tab hiện tại; file[1..] → mỗi file 1 tab/hồ sơ mới (poller tự đính ở Bước 3).
async function attachSplitAcrossTabs(payloadFiles, attachments, procedure, planRes) {
  const rest = payloadFiles.slice(1);
  await sendToBackground({ action: "clearAllPendingAttach" }); // dọn hàng đợi cũ

  // URL hồ sơ SẠCH (chỉ giữ maThuTuc/tinhThanhId) — lấy TRƯỚC khi đính để tab mới là hồ sơ MỚI.
  const urlRes = await sendToContent({ action: "getDossierUrl" });
  const dossierUrl = urlRes?.url;
  if (!dossierUrl) {
    return { error: "Không lấy được URL hồ sơ để mở tab mới. Hãy mở đúng trang nộp hồ sơ chứng thực." };
  }

  // file[0] → STT1 tab hiện tại.
  setStatus("Đang đính kèm tài liệu 1 vào hồ sơ hiện tại...", "info");
  const firstRes = await sendToContent({
    action: "attachFilesByPlan",
    procedure,
    files: [payloadFiles[0]],
    attachments: [planItemForFile(attachments, 0, payloadFiles[0])],
    mode: "split",
  });
  if (firstRes?.error) return firstRes;

  // file[1..] → mỗi file 1 tab/hồ sơ mới.
  let opened = 0;
  const openErrors = [];
  for (let i = 0; i < rest.length; i++) {
    const r = await sendToBackground({
      action: "openDossierTabAndAttach",
      url: dossierUrl,
      file: rest[i],
      planItem: planItemForFile(attachments, i + 1, rest[i]),
      procedure,
    });
    if (r?.error) openErrors.push(r.error);
    else opened++;
  }

  let msg =
    `Đã đính kèm tài liệu 1 vào hồ sơ hiện tại (STT1).\n` +
    `Đã mở ${opened} tab hồ sơ mới cho ${rest.length} tài liệu còn lại.\n` +
    `Ở MỖI tab mới: bấm "Bước tiếp theo" tới Bước 3, hệ thống sẽ tự đính file vào STT1.`;
  if (openErrors.length) msg += `\nLỗi mở tab: ${openErrors.join("; ")}`;
  if (planRes?.errors?.length) msg += `\nCảnh báo xử lý: ${planRes.errors.join("; ")}`;
  return { ok: true, message: msg };
}

// ===== OCR & điền =====
ocrBtn.addEventListener("click", async () => {
  if (window.__AUTOFILL_HCC_POPUP_BUSY__) return;
  if (!files.length) {
    setStatus("Chưa có file nào.", "err");
    return;
  }
  window.__AUTOFILL_HCC_POPUP_BUSY__ = true;
  ocrBtn.disabled = true;
  clearReviewCard(); // xoá card rà soát của lần trước trước khi chạy lại
  refreshAttachStepUI();
  try {
    setStatus("Đang đọc file...", "info");
    await ensureSelectedFilesLoaded();

    // Nhận diện lại thủ tục theo TRANG HIỆN TẠI ngay trước khi gửi (tránh dùng thủ tục cũ bị khóa
    // stale từ trang trước khi đổi trang/đăng nhập lại trong cùng tab).
    await autoDetectAndLockProcedure();
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
      if (attachRes?.error) setStatus(attachRes.error, "err");
      else setStatus(attachRes.message, "ok");
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
      cfg.key === "dinh-chinh-sai-sot-lam-dong" ||
      cfg.key === "giai-quyet-che-do-khang-chien" ||
      cfg.key === "di-chuyen-ho-so-nguoi-huong-tro-cap" ||
      cfg.key === "sua-doi-thong-tin-ho-so-nguoi-co-cong"
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
      setStatus("Lỗi: " + e.message, "err");
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
    window.__AUTOFILL_HCC_POPUP_BUSY__ = true;
    fillAllBtn.disabled = true;
    try {
      setStatus("Đang đọc file...", "info");
      await ensureSelectedFilesLoaded();
      await autoDetectAndLockProcedure();
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
      options.hasHandwriting = payloadFiles.some((f) => f.hasHandwriting);

      setStatus(" Đang phân tích tài liệu...", "info");
      const res = await api.process({ procedure: cfg.key, options, files: payloadFiles });
      console.log("[BE fill-all]", { extracted: res.extracted, stats: res.stats });
      const pages = res.pages || {};
      if (!Object.keys(pages).length) {
        setStatus("Backend không trả dữ liệu 8 trang. Kiểm tra lại.", "err");
        return;
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

      const startRes = await sendToContent({ action: "startFillAllBusiness", pages, attachPayload });
      if (startRes?.error) {
        setStatus(startRes.error, "err");
        return;
      }
      setStatus(attachPayload
        ? "Đang tự điền & lưu 8 trang rồi TỰ ĐÍNH KÈM. Đừng thao tác trên trang cho tới khi xong."
        : "Đang tự điền & lưu lần lượt 8 trang. Đừng thao tác trên trang cho tới khi xong.", "ok");
    } catch (e) {
      if (e.unauthorized) {
        await AuthStore.clearTokens();
        setStatus("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", "err");
        showLogin();
      } else {
        setStatus("Lỗi: " + (e?.message || e), "err");
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
    await autoDetectAndLockProcedure(); // khớp lại thủ tục theo trang hiện tại trước khi đính kèm
    const cfg = currentConfig();
    if (!cfg.hasAttachmentStep) {
      setStatus("Thủ tục này chưa có bước đính kèm tự động.", "err");
      return;
    }
    if (!files.length) {
      setStatus("Chưa có file nào để đính kèm.", "err");
      return;
    }

    window.__AUTOFILL_HCC_POPUP_BUSY__ = true;
    if (ocrBtn) ocrBtn.disabled = true;
    attachStepBtn.disabled = true;
    try {
      setStatus("Đang đọc file...", "info");
      await ensureSelectedFilesLoaded();
      // Không bắt buộc đã process bước 2: nếu có session đúng thủ tục thì truyền để backend dùng hint,
      // không có thì vẫn đính kèm bình thường (planner xử lý session=None).
      const sid = lastProcessSession?.procedure === cfg.key ? lastProcessSession.sessionId : null;
      const res = await runAttachmentPlanForCurrentFiles(sid ? { sessionId: sid } : {});
      if (res?.error) {
        console.warn("[Popup] Attach step failed", res);
        setStatus(res.error, "err");
      } else {
        setStatus(res.message, "ok");
      }
    } catch (e) {
      if (e.unauthorized) {
        await AuthStore.clearTokens();
        setStatus("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", "err");
        showLogin();
      } else {
        setStatus("Lỗi: " + e.message, "err");
      }
    } finally {
      window.__AUTOFILL_HCC_POPUP_BUSY__ = false;
      if (ocrBtn) ocrBtn.disabled = false;
      refreshAttachStepUI();
    }
  });
}

async function dispatchFill(allFields, errors, page = null) {
  if (!allFields.length) {
    setStatus("Không bóc tách được trường nào.\n" + errors.join("\n"), "err");
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
    businessPage: page?.key || "",
  });
  if (fillRes.error) {
    setStatus(fillRes.error, "err");
    return;
  }
  let msg = page
    ? `Đã điền ${fillRes.filled}/${allFields.length} trường ở trang "${page.label}".`
    : `Đã điền ${fillRes.filled}/${allFields.length} trường.`;
  if (fillRes.notFound?.length) msg += `\nKhông khớp: ${fillRes.notFound.join(", ")}`;
  if (errors.length) msg += `\nLỗi: ${errors.join("; ")}`;
  setStatus(msg, fillRes.filled ? "ok" : "err");
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
