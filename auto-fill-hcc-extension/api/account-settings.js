// Cài đặt THEO TÀI KHOẢN — lưu ở BE (GET/PATCH /api/v1/account/settings), đi theo cán bộ sang máy khác.
// Bản sao đặt trong chrome.storage.local vì content script không có token, không gọi BE được: nó chỉ
// đọc bản sao này lúc đính kèm. Không có bản sao (chưa đăng nhập, BE cũ chưa có endpoint) = mặc định.
// content.js khai lại chuỗi khoá này (content script không nạp file này) — sửa ở đây thì sửa cả bên đó.
const ACCOUNT_SETTINGS_KEY = "autofill_account_settings";
const ACCOUNT_SETTINGS_PATH = "/api/v1/account/settings";

const AccountSettings = {
  async refresh() {
    const settings = await apiJson(ACCOUNT_SETTINGS_PATH);
    await chrome.storage.local.set({ [ACCOUNT_SETTINGS_KEY]: settings || {} });
    return settings || {};
  },
  async save(changes) {
    const settings = await apiJson(ACCOUNT_SETTINGS_PATH, {
      method: "PATCH",
      body: JSON.stringify(changes || {}),
    });
    await chrome.storage.local.set({ [ACCOUNT_SETTINGS_KEY]: settings || {} });
    return settings || {};
  },
  // Đăng xuất / đổi tài khoản: bỏ bản sao để cài đặt của người trước không áp sang người sau.
  async forget() {
    await chrome.storage.local.remove(ACCOUNT_SETTINGS_KEY);
  },
};

if (typeof window !== "undefined") {
  window.AccountSettings = AccountSettings;
}
