// Engine Cổng DVC quốc gia mới (dichvucong.gov.vn/nop-ho-so) — biểu mẫu SurveyJS trong React.
// Giá trị ghi qua MODEL survey ở MAIN world (content/surveyjs-main.js) vì dropdown/ngày không nhận gõ DOM;
// DOM chỉ dùng để tô kết quả và làm dự phòng khi model không đọc được.
// Đính kèm: bảng thành phần có nút "Tải lên file" theo dòng + MỘT input file dùng chung (không multiple)
// → bấm nút của dòng (hộp thoại OS bị chặn ở MAIN world) rồi nạp từng tệp.
// Tách khỏi content.js — dùng namespace window.__HCC__.
(() => {
  const H = window.__HCC__ || (window.__HCC__ = {});
  const {
    sleep, isVisible, dataUrlFilesForBatch, payloadForPlanItem, setFilesOnInput,
  } = H;

  const REQUEST_EVENT = "__HCC_SJS_REQUEST__";
  const RESULT_EVENT = "__HCC_SJS_RESULT__";
  const UPLOAD_BUTTON = 'button[title="Tải lên file"]';

  const fold = (s) => String(s ?? "")
    .replace(/Đ/g, "D").replace(/đ/g, "d")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  const stripAdmin = (s) => fold(s).replace(/^(tinh|thanh pho|tp|xa|phuong|thi tran|dac khu)\s+/, "");

  function callMain(payload, timeout = 60000) {
    return new Promise((resolve) => {
      const requestId = `sjs-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const onResult = (event) => {
        let data;
        try { data = JSON.parse(String(event.detail || "{}")); } catch { return; }
        if (data.requestId !== requestId) return;
        done(data);
      };
      const timer = setTimeout(() => done({ ok: false, error: "timeout" }), timeout);
      function done(data) {
        clearTimeout(timer);
        document.removeEventListener(RESULT_EVENT, onResult);
        resolve(data);
      }
      document.addEventListener(RESULT_EVENT, onResult);
      document.dispatchEvent(new CustomEvent(REQUEST_EVENT, { detail: JSON.stringify({ ...payload, requestId }) }));
    });
  }

  // data-name = "<tên>__<hậu tố số>"; bản mobile lặp lại DOM nên chỉ lấy phần tử đang hiện.
  function questionEl(name) {
    const nodes = Array.from(document.querySelectorAll("[data-name]")).filter((node) => {
      const dn = node.getAttribute("data-name") || "";
      return dn === name || dn.startsWith(`${name}__`);
    });
    return nodes.find((node) => isVisible(node)) || nodes[0] || null;
  }

  function matchScore(want, text) {
    const w = fold(want);
    const t = fold(text);
    if (!w || !t) return 0;
    if (t === w) return 100;
    if (stripAdmin(t) === stripAdmin(w)) return 95;
    if (t.includes(w) || w.includes(t)) return 80 - Math.min(20, Math.abs(t.length - w.length) / 4);
    const wt = new Set(w.split(" ")), tt = new Set(t.split(" "));
    const common = [...wt].filter((x) => tt.has(x)).length;
    return common ? Math.round((common / Math.max(wt.size, tt.size)) * 70) : 0;
  }

  // Dự phòng khi model không có danh mục (tải lười): mở dropdown thật rồi bấm option khớp nhất.
  async function pickDropdownDom(name, value) {
    const el = questionEl(name);
    const box = el?.querySelector(".sd-dropdown");
    if (!box) return false;
    box.click();
    let items = [];
    for (let i = 0; i < 20 && !items.length; i++) {
      await sleep(200);
      items = Array.from(el.querySelectorAll(".sv-list__item")).filter(isVisible);
    }
    let best = null;
    let bestScore = 0;
    for (const item of items) {
      const score = matchScore(value, item.textContent);
      if (score > bestScore) { best = item; bestScore = score; }
    }
    if (!best || bestScore < 50) {
      document.body.click();
      return false;
    }
    (best.querySelector(".sv-list__item-body") || best).click();
    await sleep(300);
    return true;
  }

  function setTextDom(name, value) {
    const input = questionEl(name)?.querySelector("input:not([type=hidden]):not([readonly]), textarea");
    if (!input) return false;
    const desc = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), "value");
    if (desc?.set) desc.set.call(input, String(value ?? ""));
    else input.value = String(value ?? "");
    ["input", "change", "blur"].forEach((type) => input.dispatchEvent(new Event(type, { bubbles: true })));
    return true;
  }

  // React vẽ lại là ghi đè `class` → class tô màu của content.js mất ngay. Đánh dấu bằng thuộc tính
  // data-hcc-mark (React không quản) + CSS riêng; màu giống autofill-filled / -default / -not-filled.
  const MARK_ATTR = "data-hcc-mark";
  function injectMarkStyles() {
    if (document.getElementById("hcc-sjs-mark-style")) return;
    const style = document.createElement("style");
    style.id = "hcc-sjs-mark-style";
    const rule = (kind, bg, color) =>
      `[${MARK_ATTR}="${kind}"] .sd-input, [${MARK_ATTR}="${kind}"] fieldset, tr[${MARK_ATTR}="${kind}"] {` +
      ` background-color: ${bg} !important; outline: 2px solid ${color} !important;` +
      " outline-offset: 1px !important; border-radius: 3px !important; }";
    style.textContent = [
      rule("filled", "#e8f5e9", "#4caf50"),
      rule("default", "#fff8e1", "#f9a825"),
      rule("not-filled", "#ffebee", "#e53935"),
    ].join("\n");
    (document.head || document.documentElement).appendChild(style);
  }

  function setMark(el, kind) {
    if (el) el.setAttribute(MARK_ATTR, kind);
  }

  function markField(field, ok) {
    setMark(questionEl(field.name), ok ? (field.default ? "default" : "filled") : "not-filled");
  }

  // "UBND xã X" từ tên xã của tài khoản trợ lý ("Xã X" / "Phường X" / "X").
  function kinhGuiFromWard(ward) {
    const text = String(ward || "").replace(/\s+/g, " ").trim();
    if (!text) return "";
    const m = text.match(/^(xã|phường|thị trấn|đặc khu)\s+(.+)$/i);
    return m ? `UBND ${m[1].toLowerCase()} ${m[2]}` : `UBND ${text}`;
  }

  async function fillFormSurveyJs(fields, toolAccount) {
    injectMarkStyles();
    document.querySelectorAll(`[${MARK_ATTR}]`).forEach((el) => el.removeAttribute(MARK_ATTR));
    const result = { filled: 0, notFound: [], errors: [], skipped: [] };
    const res = await callMain({ op: "setValues", fields });
    const byName = new Map((res.ok ? res.results || [] : []).map((r) => [r.name, r]));
    if (!res.ok) console.warn("[AutoFill-SurveyJS] không đọc được model survey:", res.error);

    for (const field of fields) {
      let r = byName.get(field.name) || { ok: false, reason: res.error || "not-found" };
      const domRetry = !r.ok && r.reason !== "readonly" &&
        (field.comp === "sjs-dropdown" || (!res.ok && field.comp === "sjs-text"));
      if (domRetry) {
        const ok = field.comp === "sjs-dropdown"
          ? await pickDropdownDom(field.name, field.value)
          : setTextDom(field.name, field.value);
        r = ok ? { ok: true } : r;
      }
      if (r.ok) result.filled++;
      else if (r.reason === "readonly") result.skipped.push(field.name);
      else {
        result.notFound.push(field.name);
        console.warn("[AutoFill-SurveyJS] chưa điền", field.name, r.reason);
      }
      if (Array.isArray(r.parts)) r.parts.forEach((part) => markField({ name: part.name }, part.ok));
      else markField(field, r.ok);
    }

    const place = { kinhGui: kinhGuiFromWard(toolAccount?.xa), tai: String(toolAccount?.tinh || "").trim() };
    if (place.kinhGui || place.tai) {
      const placeRes = await callMain({ op: "fillPlace", place }, 20000);
      for (const r of placeRes.results || []) {
        if (r.ok) result.filled++;
        markField({ name: r.name, default: true }, r.ok);
      }
    }

    const empty = await callMain({ op: "emptyRequired" }, 10000);
    for (const name of empty.names || []) {
      const el = questionEl(name);
      if (el && !el.getAttribute(MARK_ATTR)) setMark(el, "not-filled");
    }
    return result;
  }

  function uploadRows() {
    return Array.from(document.querySelectorAll("tr"))
      .filter((tr) => isVisible(tr) && tr.querySelector(UPLOAD_BUTTON));
  }

  function findUploadRow(item) {
    const rows = uploadRows();
    const want = fold(item.slotName || item.componentName).slice(0, 40);
    // Có tên dòng mà không khớp thì báo lỗi, không đính nhầm sang dòng cùng số thứ tự.
    if (want) return rows.find((tr) => fold(tr.textContent).includes(want)) || null;
    return rows[item.slotIndex || 0] || null;
  }

  // Thông báo nổi của cổng (toast) — để báo đúng lý do khi cổng từ chối tệp.
  function portalToasts() {
    return Array.from(document.querySelectorAll('[role="alert"], [role="status"], [class*="toast" i]'))
      .filter((el) => isVisible(el))
      .map((el) => String(el.textContent || "").replace(/\s+/g, " ").trim())
      .filter(Boolean);
  }

  async function attachSurveyJsByPlan(payloadFiles, attachments) {
    injectMarkStyles();
    const attachedNames = [];
    const errors = [];
    await callMain({ op: "suppressPicker", on: true }, 5000);
    try {
      for (let i = 0; i < attachments.length; i++) {
        const item = attachments[i];
        const payload = payloadForPlanItem(payloadFiles, item, i);
        if (!payload) { errors.push(`Không tìm thấy file "${item.fileName}".`); continue; }
        const [file] = dataUrlFilesForBatch([{ payload, documentName: item.documentName }]);
        const row = findUploadRow(item);
        const button = row?.querySelector(UPLOAD_BUTTON);
        if (!button) {
          errors.push(`Không tìm thấy dòng đính kèm "${item.slotName || ""}" trên trang.`);
          continue;
        }
        // Bằng chứng thành công = TÊN TỆP hiện thêm trên dòng (cổng tải xong mới hiện); chờ xong mới nạp tệp kế
        // tiếp vào cùng input. React có thể vẽ lại dòng → mỗi lượt dò lại dòng. Cổng có thể rút gọn tên dài →
        // nhận cả phần đầu tên khi nội dung dòng đã đổi.
        const wanted = fold(file.name);
        const head = fold(file.name.replace(/\.[^.]+$/, "")).slice(0, 12);
        const rowText = () => fold((findUploadRow(item) || row).textContent);
        const count = (text, part) => (part ? text.split(part).length - 1 : 0);
        const beforeText = rowText();
        const before = count(beforeText, wanted);
        const beforeHead = count(beforeText, head);
        const shown = () => {
          const text = rowText();
          return count(text, wanted) > before || (text !== beforeText && count(text, head) > beforeHead);
        };
        let portalError = "";
        // Một lượt: bấm "Tải lên file" của dòng → chờ cổng THẬT SỰ mở input (MAIN world bắt lệnh mở hộp chọn tệp
        // và gắn data-hcc-picker) → nạp MỘT tệp vào input dùng chung (không multiple) → chờ tên tệp hiện trên dòng.
        // Cổng còn bận lượt trước thì bỏ qua cú bấm (không có dấu) → bấm lại ngay, không chờ hết hạn.
        const openPicker = async () => {
          for (let click = 0; click < 2; click++) {
            document.querySelectorAll("input[data-hcc-picker]").forEach((el) => el.removeAttribute("data-hcc-picker"));
            const button = (findUploadRow(item) || row).querySelector(UPLOAD_BUTTON);
            if (!button) return null;
            button.click();
            for (let w = 0; w < 10; w++) {
              await sleep(100);
              const input = document.querySelector('input[type="file"][data-hcc-picker]');
              if (input?.isConnected) return input;
            }
          }
          // Cổng không mở input qua lệnh bắt được → dùng input dùng chung như trước.
          return document.querySelector('input[type="file"][accept*=".zip"]') ||
            document.querySelector('input[type="file"]');
        };
        const attempt = async (ticks) => {
          const input = await openPicker();
          if (!input) return false;
          const toastsBefore = new Set(portalToasts());
          if (!setFilesOnInput(input, [file], { allowMultiple: false, assumeConsumed: true })) return false;
          for (let t = 0; t < ticks && !portalError; t++) {
            await sleep(200);
            if (shown()) return true;
            // Lời từ chối dung lượng/định dạng ("Vui lòng chọn tệp nhỏ hơn 2MB!", "…tệp đúng định dạng!") không
            // chứa chữ lỗi nào → phải khớp riêng, không thì chờ hết hạn rồi nạp lại lần hai trong khi cổng đã từ
            // chối ngay.
            portalError = portalToasts()
              .find((msg) => !toastsBefore.has(msg)
                && /loi|that bai|khong|vuot|qua|nho hon \d|dung luong|dinh dang/.test(fold(msg))) || "";
          }
          return false;
        };
        // Tệp đã nạp mà hết hạn vẫn chưa hiện → nạp lại MỘT lần (kiểm lại trước để không đính trùng tệp lên muộn).
        // Hạn = 10s + 5s mỗi MB: tệp nặng đang tải dở mà nạp lại là đính trùng.
        const sizeMb = Math.ceil((file.size || 0) / (1024 * 1024));
        const firstTicks = Math.min(300, 50 + sizeMb * 25);
        const startedAt = Date.now();
        let attempts = 1;
        let ok = await attempt(firstTicks);
        if (!ok && !portalError) {
          ok = shown();
          if (!ok) { attempts = 2; ok = await attempt(firstTicks); }
        }
        console.info("[AutoFill-SurveyJS] đính kèm", {
          file: file.name, sizeKB: Math.round((file.size || 0) / 1024), ms: Date.now() - startedAt, attempts, ok,
        });
        if (ok) attachedNames.push(file.name);
        else {
          errors.push(`Không đính kèm được "${file.name}"${portalError ? ` (cổng báo: ${portalError})` : ""}.`);
          console.warn("[AutoFill-SurveyJS] đính kèm hụt", { file: file.name, portalError, rowText: rowText().slice(0, 300) });
        }
        const markRow = findUploadRow(item) || row;
        if (markRow.isConnected) setMark(markRow, ok ? "filled" : "not-filled");
      }
    } finally {
      await callMain({ op: "suppressPicker", on: false }, 5000);
    }
    if (errors.length) {
      return {
        error: errors.join("; "),
        attached: attachedNames.length,
        skipped: 0,
        fileNames: attachedNames,
        skippedNames: [],
      };
    }
    return {
      ok: true,
      method: "surveyjs",
      attached: attachedNames.length,
      skipped: 0,
      fileNames: attachedNames,
      skippedNames: [],
    };
  }

  // Đọc giá trị đang hiện của một câu hỏi (ô readonly cổng đổ từ tài khoản): dropdown lấy nhãn, text lấy value.
  function readSurveyJsValue(name) {
    const el = questionEl(name);
    if (!el) return "";
    const label = el.querySelector(".sd-dropdown__value .sv-string-viewer");
    if (label) return String(label.textContent || "").trim();
    const input = el.querySelector("input:not([type=hidden]):not(.sd-dropdown__filter-string-input), textarea");
    return String(input?.value || "").trim();
  }

  H.fillFormSurveyJs = fillFormSurveyJs;
  H.attachSurveyJsByPlan = attachSurveyJsByPlan;
  H.readSurveyJsValue = readSurveyJsValue;
})();
