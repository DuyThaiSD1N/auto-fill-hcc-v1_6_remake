// panelMode.js — chế độ hiển thị khung Trợ lý: ĐẨY TRANG (mặc định) hay KHUNG BÊN
// trình duyệt (chrome.sidePanel).
//
// Nạp ở hai nơi CÓ chrome.sidePanel: service worker (importScripts) và sidebar.html
// (thẻ <script>). Content script KHÔNG nạp file này — API sidePanel không tồn tại
// trong ngữ cảnh content script, nên content.js phải HỎI background chứ không tự đoán;
// tự đoán ở đó luôn ra "không hỗ trợ" và chế độ khung bên sẽ chết âm thầm.
(() => {
  const KHOA = "tlnd_panel_mode";
  const DAY_TRANG = "push";
  const KHUNG_BEN = "sidepanel";

  // setPanelBehavior (Chrome/Edge 114+) là thứ DUY NHẤT bắt buộc: bật nó rồi thì
  // chính Chrome xử lý cú bấm icon, nên không vướng luật "phải nằm trong user
  // gesture" của sidePanel.open() — một listener async thì gesture đã mất.
  function hoTroKhungBen() {
    try {
      const sp = globalThis.chrome && chrome.sidePanel;
      return !!(sp && typeof sp.setOptions === "function"
        && typeof sp.setPanelBehavior === "function");
    } catch (_) { return false; }
  }

  // open() có từ Chrome 116 — CHỈ dùng để chuyển khung ngay lúc đổi cài đặt.
  // Thiếu nó thì chế độ khung bên vẫn chạy, chỉ là phải bấm icon một lần.
  function hoTroMoNgay() {
    try {
      return hoTroKhungBen() && typeof chrome.sidePanel.open === "function";
    } catch (_) { return false; }
  }

  function docCheDo() {
    return new Promise((resolve) => {
      try {
        chrome.storage.local.get([KHOA], (res) => {
          if (chrome.runtime.lastError) return resolve(DAY_TRANG);
          resolve(res && res[KHOA] === KHUNG_BEN ? KHUNG_BEN : DAY_TRANG);
        });
      } catch (_) { resolve(DAY_TRANG); }
    });
  }

  function ghiCheDo(mode) {
    const v = mode === KHUNG_BEN ? KHUNG_BEN : DAY_TRANG;
    return new Promise((resolve, reject) => {
      try {
        chrome.storage.local.set({ [KHOA]: v }, () => {
          const e = chrome.runtime.lastError;
          if (e) reject(new Error(e.message || "không ghi được cài đặt"));
          else resolve(v);
        });
      } catch (e) { reject(e); }
    });
  }

  // Chế độ ĐANG THỰC SỰ chạy = cài đặt lọc qua khả năng của trình duyệt. Máy thiếu
  // API thì dù cài đặt ghi "sidepanel" vẫn trả "push": không bao giờ để người dân
  // bấm icon rồi không có gì hiện ra.
  async function cheDoHieuLuc() {
    const dat = await docCheDo();
    return dat === KHUNG_BEN && hoTroKhungBen() ? KHUNG_BEN : DAY_TRANG;
  }

  // Đường sidebar cho khung bên. embedded=0 để sidebar.js biết KHÔNG có iframe cha
  // mà ẩn hai nút –/✕ (trình duyệt tự sở hữu khung). tabId vẫn nạp sẵn y như bố cục
  // đẩy trang, nhờ vậy toàn bộ logic khoá theo tab trong sidebar.js không phải sửa.
  function duongSidebar(tabId) {
    return `sidebar.html?embedded=0&tabId=${encodeURIComponent(String(tabId ?? ""))}`;
  }

  globalThis.__TLND_PANEL_MODE__ = {
    KHOA, DAY_TRANG, KHUNG_BEN,
    hoTroKhungBen, hoTroMoNgay, docCheDo, ghiCheDo, cheDoHieuLuc, duongSidebar,
  };
})();
