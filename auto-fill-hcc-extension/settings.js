const SPLIT_DOCUMENTS_SETTING_KEY = "autofill_attach_split_documents";

const splitDocumentsSetting = document.getElementById("splitDocumentsSetting");
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
    const values = await chrome.storage.local.get({ [SPLIT_DOCUMENTS_SETTING_KEY]: false });
    splitDocumentsSetting.checked = values[SPLIT_DOCUMENTS_SETTING_KEY] === true;
  } catch (error) {
    splitDocumentsSetting.checked = false;
    showStatus("Không đọc được cài đặt. Đang dùng mặc định không tách hồ sơ.", true);
  }
}

splitDocumentsSetting.addEventListener("change", async () => {
  try {
    await chrome.storage.local.set({
      [SPLIT_DOCUMENTS_SETTING_KEY]: splitDocumentsSetting.checked === true,
    });
    showStatus("Đã lưu cài đặt.");
  } catch (error) {
    showStatus("Không lưu được cài đặt. Vui lòng thử lại.", true);
    await restoreSettings();
  }
});

void restoreSettings();
