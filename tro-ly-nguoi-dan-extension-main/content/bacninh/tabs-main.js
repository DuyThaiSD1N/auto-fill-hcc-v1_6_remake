// Chạy trong MAIN world trên cổng Bắc Ninh (dichvucong.bacninh.gov.vn, Liferay): chuyển tab của trang nộp hồ sơ bằng
// đúng hàm của cổng Liferay.Portal.Tabs.show. Hàm này phát sự kiện "showTab" mà cổng nghe để ẩn/hiện nút "Bước tiếp
// theo" / "Nộp hồ sơ" — tự đổi class ẩn/hiện của tab thì nút Nộp hồ sơ ở tab cuối vẫn ẩn. Content script (isolated) không
// gọi được Liferay, còn bấm thẻ <a href="javascript:…"> thì CSP cổng chặn → gọi qua sự kiện DOM (detail là chuỗi tên
// tab vì object không đi qua ranh giới hai world).
(() => {
  if (window.__TLND_BN_TABS_MAIN__) return;
  window.__TLND_BN_TABS_MAIN__ = true;

  document.addEventListener("tlnd-bn-show-tab", (event) => {
    const name = String(event.detail || "");
    const list = document.querySelector('ul[data-tabs-namespace$="nhapTab"]');
    const names = list ? Array.from(list.querySelectorAll("li[data-tab-name]")).map((li) => li.dataset.tabName) : [];
    if (!name || !names.includes(name)) return;
    try {
      window.Liferay?.Portal?.Tabs?.show(list.getAttribute("data-tabs-namespace"), names, name);
    } catch (e) {
      console.warn("[TLND-BN] chuyển tab lỗi:", e);
    }
  });
})();
