// portal-doi-ma-tthc.js — chặng CỔNG TỈNH của thủ tục ĐI VÒNG (quy tắc ở popup-ke-khai-di-vong.js).
//
// Thủ tục đích chưa liên thông DVC quốc gia nên panel mở trang DVC của thủ tục CẦU. Chọn cơ quan,
// "Nộp trực tuyến", đăng nhập vẫn do content/agency-select.js làm như mọi thủ tục; cổng quốc gia
// chuyển sang eform cổng tỉnh với mã TTHC của thủ tục cầu, ví dụ
//   https://dichvucong.bacninh.gov.vn/web/guest/eform?...&_org_bn_hoso_noptructuyen_maThuTucHanhChinh=1.014589
// File này đổi tham số mã sang thủ tục đích rồi tải lại trang, phiên đăng nhập cổng tỉnh vẫn giữ.
//
// CHỈ đổi khi cờ "Đi đến thủ tục" (autofill_agency_autoselect) mang doiMaThuTuc khớp host: cán bộ
// thật sự làm thủ tục cầu thì không có cờ đó và không bị đổi nhầm. Không dùng provincePortalFlow của
// cờ — content/portal-quangninh.js chỉ kiểm host nên sẽ chạy nhầm trên cổng tỉnh này.
(() => {
  if (window.top !== window) return;
  if (window.__HCC_DOI_MA_TTHC__) return;
  window.__HCC_DOI_MA_TTHC__ = true;

  const ARM_KEY = "autofill_agency_autoselect";
  // Bằng chặng chờ đăng nhập bên agency-select.js: công dân xác thực VNeID lâu bao nhiêu cũng được.
  const ARM_TTL_MS = 30 * 60 * 1000;
  // Đổi mã mà cổng vẫn trả về mã cầu (không cho mở thủ tục đích) thì dừng, không tải lại vô hạn.
  const SO_LAN_DOI_TOI_DA = 2;
  const log = (...args) => console.log("[DoiMaTTHC]", ...args);

  /** URL eform với mã đích, hoặc null nếu trang này không phải eform mang mã cầu. */
  function urlSauDoiMa(href, flow) {
    if (!flow || !flow.host || !flow.thamSo || !flow.tu || !flow.sang) return null;
    let url;
    try { url = new URL(href); } catch (e) { return null; }
    if (url.hostname !== flow.host) return null;
    if (url.searchParams.get(flow.thamSo) !== flow.tu) return null;
    url.searchParams.set(flow.thamSo, flow.sang);
    return url.toString();
  }

  /** Việc cần làm ở trang này theo cờ: null | {viec:"doi",url} | {viec:"xong"|"het-han"|"bo-cuoc"}. */
  function viecCanLam(arm, href, bayGio, ttlMs, soLanToiDa = 2) {
    const flow = arm && arm.doiMaThuTuc;
    if (!flow) return null;
    let url;
    try { url = new URL(href); } catch (e) { return null; }
    if (url.hostname !== flow.host) return null;
    if (bayGio - Number(arm.at || 0) > ttlMs) return { viec: "het-han" };
    const ma = url.searchParams.get(flow.thamSo);
    if (ma === flow.sang) return { viec: "xong" };
    if (ma !== flow.tu) return null;
    if (Number(arm.doiMaLanThu || 0) >= soLanToiDa) return { viec: "bo-cuoc" };
    return { viec: "doi", url: urlSauDoiMa(href, flow) };
  }

  let dangDoi = false;

  async function kiem() {
    if (dangDoi) return;
    let arm;
    try {
      arm = (await chrome.storage.local.get(ARM_KEY))?.[ARM_KEY] || null;
    } catch (error) {
      console.warn("[DoiMaTTHC] không đọc được cờ:", error);
      return;
    }
    const viec = viecCanLam(arm, location.href, Date.now(), ARM_TTL_MS, SO_LAN_DOI_TOI_DA);
    if (!viec) return;
    const flow = arm.doiMaThuTuc;
    if (viec.viec !== "doi") {
      try { await chrome.storage.local.remove(ARM_KEY); } catch (_) { /* ignore */ }
      if (viec.viec === "xong") log("đã ở thủ tục đích", flow.sang, "— dọn cờ");
      if (viec.viec === "het-han") log("cờ đã quá hạn — bấm 'Đi đến thủ tục' lại");
      if (viec.viec === "bo-cuoc") {
        console.warn(`[DoiMaTTHC] đã đổi ${SO_LAN_DOI_TOI_DA} lần mà cổng vẫn về mã ${flow.tu} — dừng`);
      }
      return;
    }
    dangDoi = true;
    // Ghi số lần TRƯỚC khi rời trang: cổng đá ngược về mã cầu thì lượt sau biết đã thử bao nhiêu.
    try {
      await chrome.storage.local.set({
        [ARM_KEY]: { ...arm, doiMaLanThu: Number(arm.doiMaLanThu || 0) + 1, at: Date.now() },
      });
    } catch (_) { /* không ghi được thì vẫn đổi — mất bộ đếm chứ không mất việc */ }
    log("đổi mã TTHC", flow.tu, "→", flow.sang);
    location.replace(viec.url);
  }

  // Cờ có thể được ghi SAU khi trang đã tải (bấm "Đi đến thủ tục" ở tab khác).
  try {
    chrome.storage?.onChanged?.addListener((changes, area) => {
      if (area === "local" && changes[ARM_KEY]) void kiem();
    });
  } catch (_) { /* ngữ cảnh không có storage thì thôi */ }

  void kiem();
})();
