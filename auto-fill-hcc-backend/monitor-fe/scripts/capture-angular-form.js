// Chụp mẫu form Angular (lienthong.dichvucong.gov.vn…) cho tab "Mô phỏng form" của web Monitor.
//
// Cách dùng: đăng nhập cổng, mở tới bước "Kê khai", F12 → Console → dán TOÀN BỘ file này → Enter.
// Chạy xong trình duyệt tải về file lienthong-form-<giờ>.json → gửi cho dev, lưu vào
// monitor-fe/src/simulations/mau-angular/<tên-mẫu>.json.
//
// CHỈ ĐỌC: mở từng dropdown để chép danh sách option rồi đóng (Escape), không gõ, không chọn, không bấm
// chuyển bước. KHÔNG lấy giá trị đang có trong ô (dữ liệu cá nhân) — chỉ ghi ô đó có giá trị hay trống.
// Khối hiện theo điều kiện (dân tộc "Khác", chứng sinh BHXH, xác nhận qua VNeID…): bật khối đó trên
// một hồ sơ nháp rồi chạy lại; các lần chụp được gộp ở phía dev.
// Cũng chạy được trên HTML đã lưu (không có Angular): khi đó chỉ lấy bố cục, không mở được dropdown.
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const txt = (el) => (el?.textContent || "").replace(/\s+/g, " ").trim();
  const waitFor = async (fn, ms = 2500) => {
    for (let t = 0; t < ms; t += 100) { const v = fn(); if (v) return v; await sleep(100); }
    return fn();
  };
  // Trang đang chạy Angular thật (không phải HTML đã lưu mở lại) mới mở được dropdown.
  const live = typeof window.getAllAngularRootElements === "function" || !!window.ng;
  const esc = (target) => {
    for (const el of [target, document.activeElement, document.body].filter(Boolean)) {
      el.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", code: "Escape", keyCode: 27, bubbles: true }));
    }
    document.querySelector(".cdk-overlay-backdrop")?.click();
  };

  // Danh sách option của ng-select: panel có thể cuộn ảo → cuộn tới cuối, gom dần.
  async function ngSelectOptions(ng) {
    if (ng.classList.contains("ng-select-disabled")) return { skipped: "disabled" };
    const box = ng.querySelector(".ng-select-container") || ng;
    box.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    const panel = await waitFor(() => document.querySelector("ng-dropdown-panel"), 2000);
    if (!panel) return { skipped: "không mở được" };
    await waitFor(() => panel.querySelector(".ng-option:not(.ng-option-disabled)") || panel.querySelector(".ng-option"), 3000);
    const seen = new Map();
    const scroller = panel.querySelector(".ng-dropdown-panel-items") || panel;
    for (let i = 0; i < 400; i++) {
      panel.querySelectorAll(".ng-option").forEach((o) => {
        const t = txt(o);
        if (t && !/^(không có|no items|đang tải|loading)/i.test(t)) seen.set(t, true);
      });
      const before = scroller.scrollTop;
      scroller.scrollTop = before + scroller.clientHeight;
      await sleep(60);
      if (scroller.scrollTop === before) break;
    }
    esc(ng.querySelector("input"));
    await sleep(200);
    return seen.size ? { options: [...seen.keys()] } : { skipped: "rỗng — có thể phải gõ để tìm" };
  }

  async function matSelectOptions(ms) {
    if (ms.classList.contains("mat-select-disabled") || ms.getAttribute("aria-disabled") === "true") return { skipped: "disabled" };
    (ms.querySelector(".mat-select-trigger") || ms).click();
    const opts = await waitFor(() => {
      const list = document.querySelectorAll(".cdk-overlay-container mat-option");
      return list.length ? list : null;
    }, 2000);
    const options = opts ? [...opts].map(txt).filter(Boolean) : [];
    esc(ms);
    await sleep(250);
    return options.length ? { options } : { skipped: "không mở được" };
  }

  const kindOf = (el) => {
    const tag = el.tagName.toLowerCase();
    if (tag === "mat-radio-group" || el.querySelector("mat-radio-button")) return "radio";
    if (tag === "mat-checkbox" || el.querySelector("mat-checkbox, input[type=checkbox]")) return "checkbox";
    const inputs = [...el.querySelectorAll("input")].filter((i) => i.type !== "hidden");
    const placeholders = inputs.map((i) => (i.placeholder || i.getAttribute("aria-label") || "").toLowerCase()).join("|");
    const labels = [...el.querySelectorAll("mat-label, label")].map(txt).join("|").toLowerCase();
    if (/tỉnh|thành phố/.test(placeholders + labels) && /xã|phường/.test(placeholders + labels)) return "diachi";
    if (el.querySelector("mat-select") && inputs.length) return "ngaysinh";
    if (el.querySelector("ng-select") || tag === "ng-select") return "ng-select";
    if (el.querySelector("mat-select") || tag === "mat-select") return "mat-select";
    if (el.querySelector("mat-datepicker-toggle, mat-datepicker") || inputs.some((i) => i.getAttribute("matdatepicker") !== null)) return "date";
    if (el.querySelector("textarea")) return "textarea";
    if (inputs.some((i) => i.type === "number")) return "number";
    return "text";
  };

  const labelOf = (el) => {
    // <app-input formcontrolname placeholder="…" type="…"> của cổng mang sẵn nhãn.
    if (el.matches("app-input[placeholder]")) return el.getAttribute("placeholder").trim();
    if (el.matches("mat-radio-group")) {
      const head = [...el.children].find((c) => !c.querySelector("mat-radio-button") && txt(c));
      if (head) return txt(head).replace(/\s*\*$/, "");
    }
    if (el.matches("mat-checkbox")) {
      // Chữ của ô tích nằm trong <label> bọc ngoài hoặc ngay sau mat-checkbox, không nằm trong nó.
      const own = txt(el.querySelector(".mat-checkbox-label"));
      if (own) return own;
      const wrap = el.closest("label");
      if (wrap && txt(wrap)) return txt(wrap);
      return txt(el.nextElementSibling || el.parentElement).slice(0, 120);
    }
    if (el.matches("mat-radio-group")) return "";
    const own = el.querySelector("mat-label") || el.querySelector("label");
    if (own && txt(own)) return txt(own).replace(/\s*\*$/, "");
    const input = el.querySelector("input, textarea");
    return (input?.placeholder || input?.getAttribute("aria-label") || "").trim();
  };
  const required = (el) =>
    !!el.querySelector(".mat-form-field-required-marker, .required, [required], [aria-required=true]") ||
    /\*\s*$/.test(txt(el.querySelector("mat-label, label"))) || el.classList.contains("required");
  const readonly = (el) => {
    const inputs = [...el.querySelectorAll("input, textarea")].filter((i) => i.type !== "hidden");
    return !!el.querySelector(".mat-select-disabled, .ng-select-disabled, .mat-form-field-disabled") ||
      (inputs.length > 0 && inputs.every((i) => i.readOnly || i.disabled));
  };
  const hasValue = (el) => {
    if (el.querySelector(".ng-value, .mat-select-value-text")) return true;
    if (el.querySelector("mat-radio-button.mat-radio-checked, mat-checkbox.mat-checkbox-checked")) return true;
    return [...el.querySelectorAll("input, textarea")].some((i) => i.type !== "checkbox" && i.type !== "radio" && i.type !== "hidden" && String(i.value || "").trim());
  };

  const form = {
    source: location.host + location.pathname + location.hash.split("?")[0],
    title: txt(document.querySelector("h1, h2, .title-page, .header-title")),
    step: txt(document.querySelector(".head_steps .active:last-of-type, .step.active:last-of-type")),
    capturedAt: new Date().toISOString(),
    live,
    sections: [],
  };
  let section = { title: "", fields: [] };
  form.sections.push(section);
  const seenKeys = new Set();
  const nodes = [...document.querySelectorAll("div.title, [formcontrolname]")];
  const controls = nodes.filter((n) => n.matches("[formcontrolname]"));
  let done = 0;

  for (const el of nodes) {
    if (el.matches("div.title")) {
      // Tiêu đề khối có thể chứa luôn ô/nút (vd Loại cư trú nằm trong tiêu đề "Nơi cư trú") → lấy phần chữ đầu.
      const head = el.querySelector(":scope > span") || [...el.childNodes].find((n) => n.nodeType === 3 && n.textContent.trim());
      section = { title: txt(head) || txt(el), fields: [] };
      form.sections.push(section);
      continue;
    }
    const key = el.getAttribute("formcontrolname");
    // formcontrolname lồng (wrapper + input bên trong) → chỉ lấy lớp ngoài cùng.
    if (seenKeys.has(key) || el.parentElement?.closest(`[formcontrolname="${CSS.escape(key)}"]`)) continue;
    seenKeys.add(key);
    const kind = kindOf(el);
    const field = { key, kind, label: labelOf(el), required: required(el), readonly: readonly(el), hasValue: hasValue(el) };
    if (el.getAttribute("type")) field.portalType = el.getAttribute("type");
    if (kind === "radio" || kind === "checkbox") {
      field.options = [...el.querySelectorAll("mat-radio-button, mat-checkbox")].map((b) => ({
        value: b.querySelector("input")?.value ?? "", label: txt(b.querySelector(".mat-radio-label-content, .mat-checkbox-label") || b),
      }));
    }
    if (kind === "diachi") {
      field.parts = [...el.querySelectorAll("mat-form-field, ng-select")].filter((p) => !p.parentElement.closest("mat-form-field, ng-select"))
        .map((p) => ({ label: labelOf(p), kind: p.matches("ng-select") || p.querySelector("ng-select") ? "ng-select" : p.querySelector("input[aria-autocomplete], [matautocomplete]") ? "autocomplete" : "text", required: required(p), readonly: readonly(p) }));
    }
    if (live && !field.readonly) {
      try {
        if (kind === "ng-select") Object.assign(field, await ngSelectOptions(el.matches("ng-select") ? el : el.querySelector("ng-select")));
        else if (kind === "mat-select") Object.assign(field, await matSelectOptions(el.querySelector("mat-select") || el));
        else if (kind === "diachi") {
          const first = el.querySelector("ng-select");
          if (first) field.parts[0] = { ...field.parts[0], ...(await ngSelectOptions(first)) };
        }
      } catch (e) {
        field.skipped = String(e);
      }
    }
    section.fields.push(field);
    done++;
    if (live) console.log(`[capture] ${done}/${controls.length} ${key} (${kind})${field.options ? ` · ${field.options.length} option` : ""}`);
  }
  form.sections = form.sections.filter((s) => s.fields.length);
  form.total = seenKeys.size;
  window.__capturedForm = form;

  if (live) {
    const blob = new Blob([JSON.stringify(form, null, 1)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `lienthong-form-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    console.log(`[capture] XONG: ${form.total} ô, đã tải file ${a.download}`);
  }
  return form;
})();
