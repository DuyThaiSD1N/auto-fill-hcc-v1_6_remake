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
