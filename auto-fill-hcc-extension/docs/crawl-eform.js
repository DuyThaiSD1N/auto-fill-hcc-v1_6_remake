/**
 * CRAWL E-FORM — quét toàn bộ ô nhập của một biểu mẫu trên cổng dịch vụ công.
 *
 * DÙNG:
 *   1. Mở đúng trang/bước có biểu mẫu cần lấy (đợi form hiện đủ, bấm mở các panel đang thu gọn).
 *   2. F12 → tab Console. Lần đầu Chrome chặn dán, gõ  allow pasting  rồi Enter.
 *   3. Dán NGUYÊN file này vào Console, Enter.
 *   4. Kết quả: bảng tóm tắt in ra Console, JSON đầy đủ đã nằm trong clipboard (Ctrl+V để gửi đi).
 *      Không copy được thì lấy ở biến  window.__eform  hoặc chạy  copy(window.__eform.json).
 *
 * MỖI Ô TRẢ VỀ:
 *   name       tên ô để điền (BE gửi đúng tên này), vd "data[fullname]".
 *   label      nhãn hiển thị cạnh ô.
 *   section    tiêu đề khối chứa ô, vd "Thông tin chung".
 *   panel      khoá panel Form.io bọc ô, vd "thongTinChung".
 *   scope      selector khoanh vùng panel đó — dán thẳng vào DON_SCOPE của schema.
 *   selector   selector trỏ ĐÚNG một ô, dùng khi name bị trùng giữa các khối.
 *   duplicate  true nếu trang có từ 2 ô trở lên cùng name (nguồn gốc mọi vụ điền nhầm khối).
 *   autofill   dấu vết của trợ lý trên ô: "filled" đã điền, "not-filled" tô đỏ, rỗng là chưa chạm tới.
 *              Chạy SAU khi bấm Quét và nhập dữ liệu thì cột này cho biết dữ liệu đã đi vào ô nào.
 *
 * KÈM THEO: nếu trang đã bấm Quét và nhập dữ liệu, kết quả có thêm "autofillReport" — bản extension
 * đang chạy và quyết định vùng dò của TỪNG ô (dung-khoi = đúng khối, ca-trang = dò cả trang, bo-o = bỏ).
 * Không thấy mục này nghĩa là bản extension đang chạy cũ hơn bản biết ghi báo cáo.
 *
 * An toàn: chỉ ĐỌC DOM, không bấm, không sửa, không gửi dữ liệu đi đâu.
 */
(() => {
  // Lớp mô tả LOẠI component của Form.io, không phải khoá field → bỏ khi tìm khoá.
  const FORMIO_TYPES = new Set([
    "panel", "columns", "column", "content", "htmlelement", "textfield", "textarea", "number",
    "password", "checkbox", "selectboxes", "select", "radio", "button", "email", "url",
    "phonenumber", "tags", "address", "datetime", "day", "time", "currency", "survey",
    "signature", "hidden", "container", "datamap", "datagrid", "editgrid", "tree", "fieldset",
    "well", "tabs", "table", "form", "custom", "file", "label-hidden", "modified", "multiple",
    "disabled", "required", "invalid", "danger", "alert",
  ]);

  const clean = (value) => String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  const nodeText = (el) => clean(el && (el.innerText || el.textContent));

  const classList = (el) => {
    const raw = el && el.getAttribute && el.getAttribute("class");
    return raw ? String(raw).split(/\s+/).filter(Boolean) : [];
  };

  // Khoá field/panel = lớp "formio-component-x" mà x KHÔNG phải tên loại component.
  function componentKeys(el) {
    return classList(el)
      .map((cls) => /^formio-component-(.+)$/.exec(cls))
      .filter(Boolean)
      .map((m) => m[1])
      .filter((key) => !FORMIO_TYPES.has(key.toLowerCase()));
  }

  function ancestors(el) {
    const out = [];
    for (let node = el && el.parentElement; node; node = node.parentElement) out.push(node);
    return out;
  }

  function fieldKeyOf(el) {
    for (const node of [el, ...ancestors(el)]) {
      // Chạm thẻ panel là đã ra khỏi thẻ bọc của ô → khoá panel KHÔNG phải khoá field.
      if (node !== el && classList(node).includes("formio-component-panel")) break;
      const keys = componentKeys(node);
      if (keys.length) return keys[0];
    }
    return "";
  }

  function panelKeyOf(el) {
    for (const node of ancestors(el)) {
      if (!classList(node).includes("formio-component-panel")) continue;
      const keys = componentKeys(node);
      if (keys.length) return keys[0];
    }
    return "";
  }

  // Tiêu đề khối: card-header của panel Form.io, hoặc thẻ tiêu đề gần nhất phía trên (khối Angular).
  function sectionOf(el) {
    for (const node of ancestors(el)) {
      const header = node.querySelector && node.querySelector(":scope > .card > .card-header, :scope > .card-header");
      if (header) {
        const title = nodeText(header);
        if (title) return title.slice(0, 120);
      }
      const heading = node.querySelector && node.querySelector(":scope > h1, :scope > h2, :scope > h3, :scope > h4, :scope > legend");
      if (heading) {
        const title = nodeText(heading);
        if (title) return title.slice(0, 120);
      }
    }
    return "";
  }

  function labelOf(el) {
    const byAria = el.getAttribute && el.getAttribute("aria-labelledby");
    if (byAria) {
      const found = byAria
        .split(/\s+/)
        .map((id) => document.getElementById(id))
        .filter(Boolean)
        .map(nodeText)
        .filter(Boolean);
      if (found.length) return found.join(" ").slice(0, 160);
    }
    if (el.id) {
      const bound = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (bound) return nodeText(bound).slice(0, 160);
    }
    // CHỈ nhận nhãn nằm trong đúng thẻ bọc của ô này. Trước đây leo 4 cấp rồi vớ lấy <label> đầu
    // tiên thấy được nên ô không có nhãn riêng bị gán nhãn của ô bên cạnh.
    for (const node of ancestors(el)) {
      const direct = node.querySelector && node.querySelector(":scope > label");
      if (direct) {
        const text = nodeText(direct);
        if (text) return text.slice(0, 160);
      }
      if (classList(node).includes("formio-component-panel")) break;
      if (componentKeys(node).length) {
        const label = node.querySelector && node.querySelector("label");
        const text = label ? nodeText(label) : "";
        return text ? text.slice(0, 160) : "";
      }
    }
    return "";
  }

  function visible(el) {
    if (el.offsetParent) return true;
    const rect = el.getBoundingClientRect ? el.getBoundingClientRect() : null;
    return !!(rect && (rect.width || rect.height));
  }

  function optionsOf(el) {
    if (String(el.tagName).toLowerCase() !== "select" || !el.options) return null;
    const texts = Array.from(el.options).map((opt) => clean(opt.text)).filter(Boolean);
    return { count: texts.length, sample: texts.slice(0, 8) };
  }

  const AUTOFILL_MARKS = ["autofill-filled", "autofill-not-filled", "autofill-default"];

  function autofillMark(el) {
    for (const node of [el, ...ancestors(el).slice(0, 5)]) {
      const found = AUTOFILL_MARKS.filter((mark) => classList(node).includes(mark));
      if (found.length) return found[0].replace("autofill-", "");
    }
    return "";
  }

  const SKIP_TYPES = new Set(["hidden", "submit", "button", "image", "reset"]);
  const controls = Array.from(document.querySelectorAll("input, select, textarea")).filter((el) => {
    const type = String(el.getAttribute && el.getAttribute("type") || "").toLowerCase();
    return !SKIP_TYPES.has(type);
  });

  const fields = controls.map((el) => {
    const tag = String(el.tagName).toLowerCase();
    const name = clean(el.getAttribute && el.getAttribute("name"));
    const fieldKey = fieldKeyOf(el);
    const panelKey = panelKeyOf(el);
    return {
      name,
      label: labelOf(el),
      section: sectionOf(el),
      panel: panelKey,
      scope: panelKey ? `.formio-component-${panelKey}` : "",
      selector: [
        panelKey ? `.formio-component-${panelKey}` : "",
        fieldKey ? `.formio-component-${fieldKey}` : "",
        name ? `${tag}[name="${name}"]` : tag,
      ]
        .filter(Boolean)
        .join(" "),
      tag,
      type: clean(el.getAttribute && el.getAttribute("type")) || (tag === "select" ? "select" : tag),
      id: clean(el.id),
      value: tag === "select" ? clean(el.options && el.options[el.selectedIndex] && el.options[el.selectedIndex].text) : clean(el.value),
      placeholder: clean(el.getAttribute && el.getAttribute("placeholder")),
      checked: tag === "input" && /^(checkbox|radio)$/i.test(el.type || "") ? !!el.checked : null,
      disabled: !!el.disabled,
      readonly: !!(el.getAttribute && el.getAttribute("readonly") !== null),
      visible: visible(el),
      // Dấu vết của trợ lý: ô nào đã được extension điền/tô đỏ — soi ngay được là dữ liệu đã đi vào đâu.
      autofill: autofillMark(el),
      options: optionsOf(el),
    };
  });

  const byName = new Map();
  for (const field of fields) {
    if (!field.name) continue;
    byName.set(field.name, (byName.get(field.name) || 0) + 1);
  }
  for (const field of fields) field.duplicate = (byName.get(field.name) || 0) > 1;

  const duplicates = Object.fromEntries(Array.from(byName.entries()).filter(([, n]) => n > 1));
  const panels = Array.from(new Set(fields.map((f) => f.panel).filter(Boolean)));
  const sections = Array.from(new Set(fields.map((f) => f.section).filter(Boolean)));

  // Báo cáo do extension ghi ra DOM sau lần điền gần nhất (xem publishStandardFillReport trong
  // content.js). Không có nghĩa là: hoặc chưa bấm Quét lần nào trên trang này, hoặc bản extension đang
  // chạy CŨ hơn bản có ghi báo cáo.
  let autofillReport = null;
  try {
    const raw = document.documentElement.getAttribute("data-autofill-report");
    if (raw) autofillReport = JSON.parse(raw);
  } catch (e) {
    autofillReport = { error: "không đọc được data-autofill-report" };
  }

  const result = {
    url: location.href,
    autofillReport,
    title: clean(document.title),
    crawledAt: new Date().toISOString(),
    total: fields.length,
    panels,
    sections,
    duplicates,
    fields,
  };
  result.json = JSON.stringify(result, null, 2);

  window.__eform = result;

  console.log(
    `%c[crawl-eform] ${fields.length} ô • ${panels.length} panel • ${Object.keys(duplicates).length} tên bị trùng`,
    "font-weight:bold",
  );
  if (Object.keys(duplicates).length) {
    console.warn("[crawl-eform] Tên trùng giữa các khối (phải khoanh vùng khi điền):", duplicates);
  }
  if (autofillReport && autofillReport.version) {
    console.log(`[crawl-eform] Extension đang chạy: v${autofillReport.version}, điền lúc ${autofillReport.at}`);
    console.table(autofillReport.scope || []);
  } else {
    console.warn(
      "[crawl-eform] KHÔNG thấy báo cáo của extension trên trang. Hoặc chưa bấm Quét và nhập dữ liệu " +
        "lần nào ở trang này, hoặc bản extension đang chạy cũ hơn bản biết ghi báo cáo.",
    );
  }
  console.table(
    fields.map((f) => ({
      name: f.name,
      label: f.label,
      section: f.section,
      panel: f.panel,
      value: f.value,
      visible: f.visible,
      autofill: f.autofill,
      trung: f.duplicate,
    })),
  );

  try {
    if (typeof copy === "function") {
      copy(result.json);
      console.log("[crawl-eform] Đã copy JSON vào clipboard — Ctrl+V để dán gửi đi.");
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(result.json);
      console.log("[crawl-eform] Đã copy JSON vào clipboard — Ctrl+V để dán gửi đi.");
    }
  } catch (e) {
    console.warn("[crawl-eform] Không copy được, lấy thủ công bằng: copy(window.__eform.json)", e);
  }

  return result;
})();
