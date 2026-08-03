// Cầu nối isolated world -> MAIN world cho modal "Thêm giấy tờ" của cổng NNMT.
// Angular/Zone.js của cổng chỉ xử lý ổn định chuỗi autocomplete/submit trong cùng MAIN world.
(() => {
  const H = window.__HCC__ || (window.__HCC__ = {});
  const REQUEST_EVENT = "__HCC_MAE_ADD_DOCUMENT_REQUEST__";
  const RESULT_EVENT = "__HCC_MAE_ADD_DOCUMENT_RESULT__";
  const READY_ATTR = "data-hcc-mae-main-ready";

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  async function waitForMainWorld(timeout = 4000) {
    const started = Date.now();
    while (Date.now() - started < timeout) {
      if (document.documentElement?.getAttribute(READY_ATTR) === "1") return true;
      await sleep(100);
    }
    return false;
  }

  function requestMainWorld(items) {
    return new Promise(async (resolve) => {
      const ready = await waitForMainWorld();
      if (!ready) {
        resolve({ error: "Engine MAIN world cho modal Thêm giấy tờ chưa được nạp." });
        return;
      }

      const requestId = globalThis.crypto?.randomUUID?.() ||
        `${Date.now()}-${Math.random().toString(16).slice(2)}`;
      let settled = false;
      const finish = (result) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        document.removeEventListener(RESULT_EVENT, onResult);
        resolve(result);
      };
      const onResult = (event) => {
        try {
          const result = JSON.parse(String(event.detail || "{}"));
          if (result.requestId !== requestId) return;
          finish(result);
        } catch {
          // Bỏ qua event không thuộc bridge này.
        }
      };
      const timer = setTimeout(
        () => finish({ error: "MAIN world không phản hồi thao tác Thêm giấy tờ." }),
        35000
      );

      document.addEventListener(RESULT_EVENT, onResult);
      document.dispatchEvent(new CustomEvent(REQUEST_EVENT, {
        detail: JSON.stringify({
          requestId,
          items: (items || []).map((item) => ({
            componentName: item?.componentName || "",
            loaiBan: item?.loaiBan || "Bản chính",
            quantity: item?.quantity || 1,
          })),
        }),
      }));
    });
  }

  async function ensureMaeAddDocumentRows(items) {
    if (!location.hostname.endsWith("dichvucongnnmt.mae.gov.vn")) {
      return { error: "Target add-document-dialog chỉ hỗ trợ cổng dichvucongnnmt.mae.gov.vn." };
    }
    try {
      const result = await requestMainWorld(items);
      if (result?.error) throw new Error(result.error);

      for (const row of result?.rows || []) {
        if (items?.[row.index] && row.componentName) {
          // Engine upload ở content.js phải khớp theo nhãn thực tế được Angular render.
          items[row.index].componentName = row.componentName;
        }
      }
      return { ok: true };
    } catch (error) {
      console.warn("[AutoFill-MAE-Attach] Không tạo được hàng giấy tờ:", error);
      return { error: error?.message || String(error) };
    }
  }

  H.ensureMaeAddDocumentRows = ensureMaeAddDocumentRows;
})();
