const SPLIT_DOCUMENTS_SETTING_KEY = "autofill_attach_split_documents";
const SUBMITTER_OWNER_MODE_KEY = "autofill_submitter_owner_mode";
// Không gộp giấy tờ — CHỈ thủ tục chứng thực phân chia di sản (gửi BE qua options.splitDocuments).
const ESTATE_SPLIT_ATTACH_KEY = "autofill_estate_split_attachments";

const splitDocumentsSetting = document.getElementById("splitDocumentsSetting");
const submitterOwnerModeSetting = document.getElementById("submitterOwnerModeSetting");
const estateSplitAttachmentsSetting = document.getElementById("estateSplitAttachmentsSetting");
const saveStatus = document.getElementById("saveStatus");
let statusTimer = null;

function showStatus(message, error = false) {
  saveStatus.textContent = message;
  saveStatus.className = error ? "save-status error" : "save-status";
  if (statusTimer) clearTimeout(statusTimer);
  statusTimer = setTimeout(() => {
    saveStatus.textContent = "";
  }, 2200);
}

async function restoreSettings() {
  try {
    const values = await chrome.storage.local.get({
      [SPLIT_DOCUMENTS_SETTING_KEY]: false,
      [SUBMITTER_OWNER_MODE_KEY]: false,
      [ESTATE_SPLIT_ATTACH_KEY]: false,
    });
    splitDocumentsSetting.checked = values[SPLIT_DOCUMENTS_SETTING_KEY] === true;
    submitterOwnerModeSetting.checked = values[SUBMITTER_OWNER_MODE_KEY] === true;
    estateSplitAttachmentsSetting.checked = values[ESTATE_SPLIT_ATTACH_KEY] === true;
  } catch (error) {
    splitDocumentsSetting.checked = false;
    submitterOwnerModeSetting.checked = false;
    estateSplitAttachmentsSetting.checked = false;
    showStatus("Không đọc được cài đặt. Đang dùng mặc định.", true);
  }
}

function bindToggle(input, key) {
  input.addEventListener("change", async () => {
    try {
      await chrome.storage.local.set({ [key]: input.checked === true });
      showStatus("Đã lưu cài đặt.");
    } catch (error) {
      showStatus("Không lưu được cài đặt. Vui lòng thử lại.", true);
      await restoreSettings();
    }
  });
}

bindToggle(splitDocumentsSetting, SPLIT_DOCUMENTS_SETTING_KEY);
bindToggle(submitterOwnerModeSetting, SUBMITTER_OWNER_MODE_KEY);
bindToggle(estateSplitAttachmentsSetting, ESTATE_SPLIT_ATTACH_KEY);

void restoreSettings();

// ── Hỏi đánh giá sau khi gửi hồ sơ — cài đặt THEO TÀI KHOẢN ────────────────────────────────
// Máy quầy có nhiều cán bộ dùng chung nên không thể lưu một cờ chung: lưu bảng
// {tên đăng nhập: bật/tắt}. Tài khoản chưa có trong bảng = BẬT (mọi máy đang chạy không đổi).
// Trang này mở ở TAB RIÊNG, không giữ token nên không tự hỏi được /auth/me — popup ghi sẵn tên
// đăng nhập ra CURRENT_USERNAME_KEY. Chưa có tên thì KHÓA công tắc: lưu lúc đó là lưu nhầm cho
// tài khoản khác đang có trong bảng.
const RATING_ENABLED_BY_USER_KEY = "autofill_rating_enabled_by_user";
const CURRENT_USERNAME_KEY = "autofill_current_username";

const ratingCardSetting = document.getElementById("ratingCardSetting");
const ratingAccountName = document.getElementById("ratingAccountName");
const ratingSaveStatus = document.getElementById("ratingSaveStatus");
let ratingUsername = "";
let ratingStatusTimer = null;

function showRatingStatus(message, error = false) {
  ratingSaveStatus.textContent = message;
  ratingSaveStatus.className = error ? "save-status error" : "save-status";
  if (ratingStatusTimer) clearTimeout(ratingStatusTimer);
  ratingStatusTimer = setTimeout(() => { ratingSaveStatus.textContent = ""; }, 2200);
}

async function restoreRatingSetting() {
  try {
    const store = await chrome.storage.local.get([RATING_ENABLED_BY_USER_KEY, CURRENT_USERNAME_KEY]);
    ratingUsername = String(store?.[CURRENT_USERNAME_KEY] || "").trim();
    const map = store?.[RATING_ENABLED_BY_USER_KEY];
    ratingCardSetting.checked = !(ratingUsername && map && typeof map === "object"
      && map[ratingUsername] === false);
  } catch (_) {
    ratingUsername = "";
    ratingCardSetting.checked = true;
  }
  ratingCardSetting.disabled = !ratingUsername;
  ratingAccountName.textContent = ratingUsername || "chưa đăng nhập";
  if (!ratingUsername) {
    ratingSaveStatus.textContent = "Đăng nhập trên trợ lý rồi mở lại trang này để đổi cài đặt.";
    ratingSaveStatus.className = "save-status";
  }
}

ratingCardSetting.addEventListener("change", async () => {
  if (!ratingUsername) return;
  try {
    const store = await chrome.storage.local.get([RATING_ENABLED_BY_USER_KEY]);
    const map = { ...(store?.[RATING_ENABLED_BY_USER_KEY] || {}) };
    map[ratingUsername] = ratingCardSetting.checked === true;
    await chrome.storage.local.set({ [RATING_ENABLED_BY_USER_KEY]: map });
    showRatingStatus("Đã lưu cài đặt.");
  } catch (_) {
    showRatingStatus("Không lưu được cài đặt. Vui lòng thử lại.", true);
    await restoreRatingSetting();
  }
});

void restoreRatingSetting();
