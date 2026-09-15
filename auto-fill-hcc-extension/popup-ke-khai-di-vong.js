/**
 * Thủ tục ĐI VÒNG — thủ tục cổng tỉnh CHƯA liên thông với Cổng DVC quốc gia.
 *
 * Mở thẳng trang DVC của thủ tục đích thì "Nộp trực tuyến" không dẫn tới cổng tỉnh. Đường đi được:
 *   1. Mở trang DVC của một thủ tục CẦU cùng tỉnh đã liên thông, chọn cơ quan, "Nộp trực tuyến",
 *      đăng nhập — cổng quốc gia chuyển sang eform cổng tỉnh kèm phiên đăng nhập;
 *   2. Tới eform cổng tỉnh (mã TTHC của thủ tục cầu) thì đổi tham số mã sang thủ tục ĐÍCH —
 *      việc này do content/portal-doi-ma-tthc.js làm.
 *
 * Cấu hình nằm ở extension (không ở backend ke_khai_links.json): link đích trong danh mục backend
 * được ghi đè ngay khi panel nạp danh mục. URL trang DVC lấy từ chính link cầu trong danh mục, không
 * chép cứng UUID.
 */
(function (goc) {
  const QUY_TAC = [
    {
      // [Tỉnh Bắc Ninh] Đăng ký mua, thuê mua, thuê nhà ở xã hội… — đi vòng qua thủ tục hỗ trợ người
      // cao tuổi (đã liên thông DVC quốc gia ↔ Bắc Ninh).
      dich: "1.014632",
      cau: "1.014589",
      host: "dichvucong.bacninh.gov.vn",
      thamSo: "_org_bn_hoso_noptructuyen_maThuTucHanhChinh",
    },
  ];

  // Các cờ này mô tả TRANG DVC (khối chọn cơ quan, thẻ "Nộp trực tuyến", modal xác nhận) — trang đó
  // là của thủ tục cầu nên phải lấy theo link cầu.
  const TRUONG_TRANG_DVC = [
    "needsAgencySelect", "provinceOnlyAgency", "selectSo", "selectSoProvinces",
    "submitCardIncludes", "autoConfirm",
  ];

  function apDungDiVong(links, quyTac = QUY_TAC) {
    if (!Array.isArray(links)) return [];
    return links.map((link) => {
      const q = link && quyTac.find((x) => x.dich === link.code);
      if (!q) return link;
      const cau = links.find((x) => x && x.code === q.cau && x.url);
      if (!cau) return link;
      const moi = { ...link, url: cau.url, cauLabel: cau.label };
      for (const truong of TRUONG_TRANG_DVC) {
        if (truong in cau) moi[truong] = cau[truong];
        else delete moi[truong];
      }
      moi.doiMaThuTuc = { host: q.host, thamSo: q.thamSo, tu: q.cau, sang: q.dich };
      return moi;
    });
  }

  const api = { QUY_TAC, apDungDiVong };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  goc.KeKhaiDiVong = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
