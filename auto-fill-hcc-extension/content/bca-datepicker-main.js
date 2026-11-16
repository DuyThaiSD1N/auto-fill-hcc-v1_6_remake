// Chạy trong MAIN world (Cổng DVC Bộ Công an): (1) ô ngày là bootstrap-datepicker (jQuery của trang). Gõ chữ từ isolated
// world thì lịch bật lên và treo, giá trị không vào model của picker (đóng lịch là mất) → gán qua API
// $.fn.datepicker("update") rồi đóng lịch. Cầu nối qua CustomEvent như fill-lamdong-main.js (manifest không có
// host_permissions *.gov.vn nên background không executeScript vào trang được).
(() => {
  if (location.hostname !== "dichvucong.dancuquocgia.gov.vn") return;

  const REQUEST_EVENT = "__HCC_BCA_DATES_REQUEST__";
  const RESULT_EVENT = "__HCC_BCA_DATES_RESULT__";

  if (window.__HCC_BCA_DATES_HANDLER__) {
    document.removeEventListener(REQUEST_EVENT, window.__HCC_BCA_DATES_HANDLER__);
  }

  function setOne({ id, value }) {
    const el = document.getElementById(id);
    if (!el) return { id, ok: false };
    const $ = window.jQuery;
    // Chỉ ô ĐÚNG là datepicker mới gọi API lịch — gọi lên ô chữ thường là vô tình dựng lịch mới.
    const isPicker = !!($ && $(el).data("datepicker")) || el.getAttribute("data-provide") === "datepicker";
    if (isPicker && $ && $.fn && $.fn.datepicker) {
      const $el = $(el);
      $el.datepicker("update", value);
      $el.trigger("change");
      $el.datepicker("hide");
    } else {
      el.value = value;
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }
    el.blur();
    return { id, ok: el.value === value, value: el.value };
  }

  function handleRequest(event) {
    let requestId = "";
    try {
      const payload = JSON.parse(String(event.detail || "{}"));
      requestId = String(payload.requestId || "");
      const dates = Array.isArray(payload.dates) ? payload.dates : [];
      document.dispatchEvent(new CustomEvent(RESULT_EVENT, {
        detail: JSON.stringify({ requestId, ok: true, results: dates.map(setOne) }),
      }));
    } catch (error) {
      document.dispatchEvent(new CustomEvent(RESULT_EVENT, {
        detail: JSON.stringify({ requestId, ok: false, error: String(error?.message || error) }),
      }));
    }
  }

  window.__HCC_BCA_DATES_HANDLER__ = handleRequest;
  document.addEventListener(REQUEST_EVENT, handleRequest);

  // Mở nhóm giấy tờ ở mục hồ sơ đính kèm bằng chính hàm của trang — dự phòng khi bấm <a href="javascript:
  // load_table_tphs_new(i)"> từ content script bị CSP chặn.
  const GROUP_REQUEST = "__HCC_BCA_LOAD_GROUP_REQUEST__";
  const GROUP_RESULT = "__HCC_BCA_LOAD_GROUP_RESULT__";
  if (window.__HCC_BCA_GROUP_HANDLER__) document.removeEventListener(GROUP_REQUEST, window.__HCC_BCA_GROUP_HANDLER__);
  function handleGroup(event) {
    let requestId = "";
    try {
      const payload = JSON.parse(String(event.detail || "{}"));
      requestId = String(payload.requestId || "");
      const ok = typeof window.load_table_tphs_new === "function" && Number.isInteger(payload.index);
      if (ok) window.load_table_tphs_new(payload.index);
      document.dispatchEvent(new CustomEvent(GROUP_RESULT, { detail: JSON.stringify({ requestId, ok }) }));
    } catch (error) {
      document.dispatchEvent(new CustomEvent(GROUP_RESULT, {
        detail: JSON.stringify({ requestId, ok: false, error: String(error?.message || error) }),
      }));
    }
  }
  window.__HCC_BCA_GROUP_HANDLER__ = handleGroup;
  document.addEventListener(GROUP_REQUEST, handleGroup);
})();
