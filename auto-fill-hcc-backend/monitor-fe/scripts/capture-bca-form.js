// Chụp mẫu trang căn cước Cổng DVC Bộ Công an (dichvucong.bocongan.gov.vn/portal/p/home/dvc-CCCD-*.html) cho tab
// "Mô phỏng form" (Monitor + web Agent tự sửa).
//
// Cách dùng: đăng nhập VNeID, mở trang kê khai (Bước 1), F12 → Console → dán TOÀN BỘ file này → Enter. Trình duyệt tải
// về bca-form-<giờ>.json → lưu đè monitor-fe/src/simulations/mau-bca/<tên-mẫu>.json (cap-doi-cap-lai / duoi-14-tuoi),
// rồi chép thư mục simulations/ sang auto-test-hcc/web/src/simulations/.
//
// CHỈ ĐỌC: không gõ, không chọn, không bấm. KHÔNG lấy giá trị đang có trong ô (Phần I là dữ liệu cá nhân của tài khoản),
// chỉ lấy id, nhãn, loại ô, bắt buộc, khoá, option của select (danh mục công khai: giới tính, lý do cấp, tỉnh…).
// Select nạp theo ô khác (Công an xã, địa chỉ trạm, xã nhận kết quả) để engine tự dựng từ danh mục địa giới.
// Khối đang ẩn (Phần II khi tự kê khai, nhóm nhận kết quả…) vẫn được chụp, ghi "hiddenAtCapture" để dev đặt điều kiện.
(() => {
  const txt = (el) => (el?.textContent || "").replace(/\s+/g, " ").trim();
  const visible = (el) => !!el && getComputedStyle(el).display !== "none" && el.getClientRects().length > 0;
  // Select nạp theo ô khác → engine dựng từ danh mục (xem mau-bca/*.json).
  const DYNAMIC = {
    cboORGTinh: { options: "@provinces", optionPrefix: "Công an " },
    cboORGXa: { options: "@wards:cboORGTinh", optionPrefix: "Công an " },
    cboGET_RESULT_CITY_ADDR: { options: "@provinces" },
    cboGET_RESULT_VILLAGE_ADDR: { options: "@wards:cboGET_RESULT_CITY_ADDR" },
    cboDiaChiTram: { options: undefined },
  };
  const SKIP = new Set(["hidden", "button", "submit", "reset", "file", "image", "password"]);

  const labelOf = (el) => {
    if (el.id) {
      const byFor = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (txt(byFor)) return txt(byFor);
    }
    // Bố cục bootstrap: <div class="form-group"><label class="control-label">…</label><div>…ô…</div></div>.
    const group = el.closest(".form-group, .col-md-12, .col-md-6, .col-md-4, .col-md-3, .col-sm-6, .row");
    const head = group?.querySelector("label, .control-label");
    if (head && !head.contains(el) && txt(head)) return txt(head);
    return el.getAttribute("placeholder") || el.getAttribute("title") || "";
  };
  const clean = (label) => label.replace(/\s*\(\*\)\s*|\s*\*\s*$/g, "").replace(/:\s*$/, "").trim();
  const isRequired = (el, label) => el.required || el.getAttribute("aria-required") === "true" || /\(\*\)|\*\s*:?\s*$/.test(label)
    || !!el.closest(".form-group")?.querySelector(".required, .text-danger");

  // Tiêu đề khối: legend / panel-heading / thẻ h* / dòng chữ đậm "Phần I…", "II. …".
  const HEAD = "legend, .panel-heading, .card-header, .box-title, h3, h4, h5, .title, b, strong";
  const isHead = (el) => el.matches(HEAD) && txt(el).length > 3 && txt(el).length < 140 && !el.querySelector("input, select, textarea")
    && (/^(phần|phan|[IVX]+\.|\d+\.)/i.test(txt(el)) || el.matches("legend, .panel-heading, .card-header, .box-title, h3, h4, h5"));

  const form = {
    source: location.host + location.pathname + (new URLSearchParams(location.search).get("TT") ? `?TT=${new URLSearchParams(location.search).get("TT")}` : ""),
    title: txt(document.querySelector(".page-title, .title-page, h1, h2")) || document.title,
    capturedAt: new Date().toISOString(),
    inferred: false,
    sections: [],
  };
  let section = { title: "", fields: [] };
  form.sections.push(section);
  const seenRadio = new Set();
  const nodes = [...document.querySelectorAll(`${HEAD}, input, select, textarea`)];

  for (const el of nodes) {
    if (!el.matches("input, select, textarea")) {
      if (isHead(el)) {
        const block = el.closest("[id^=div], fieldset, .panel, .box, .card");
        section = { title: txt(el), fields: [] };
        if (block?.id) section.id = block.id;
        if (!visible(el)) section.hiddenAtCapture = true;
        form.sections.push(section);
      }
      continue;
    }
    const type = String(el.type || "").toLowerCase();
    if (el.tagName === "INPUT" && SKIP.has(type)) continue;
    // Ô tìm kiếm của bootstrap-select nằm trong dropdown, không phải ô của form.
    if (el.closest(".bootstrap-select .dropdown-menu, .bs-searchbox")) continue;
    const id = el.id || el.name;
    if (!id) continue;
    if (type === "radio") {
      const name = el.name || id;
      if (seenRadio.has(name)) continue;
      seenRadio.add(name);
      const group = [...document.querySelectorAll(`input[type=radio][name="${CSS.escape(name)}"]`)];
      const optLabel = (r) => txt(document.querySelector(`label[for="${CSS.escape(r.id)}"]`)) || txt(r.closest("label")) || r.value;
      const head = labelOf(group[0]);
      section.fields.push({
        id: name, kind: "radio", label: clean(group.some((r) => optLabel(r) === head) ? "" : head) || name,
        required: isRequired(group[0], head), options: group.map(optLabel), wide: true,
        radioIds: group.map((r) => r.id).filter(Boolean),
        ...(visible(group[0]) ? {} : { hiddenAtCapture: true }),
      });
      continue;
    }
    if (type === "checkbox") continue; // tích hợp BHYT/GPLX, cam đoan chkRULE — BE không điền
    const raw = labelOf(el);
    const field = {
      id, kind: el.tagName === "SELECT" ? "select" : /date|ngay|birth/i.test(id) || el.classList.contains("datepicker") ? "date" : "text",
      label: clean(raw) || id, required: isRequired(el, raw),
    };
    if (el.readOnly || el.disabled) field.readonly = true;
    if (el.tagName === "SELECT") {
      if (id in DYNAMIC) Object.assign(field, DYNAMIC[id]);
      else {
        field.options = [...el.options].filter((o) => o.value && !["-1", "0"].includes(o.value) && txt(o)).map(txt);
        if (!field.options.length) delete field.options;
      }
      if (field.options === undefined) delete field.options;
    }
    // Khoá theo tài khoản: chỉ ghi ô có giá trị hay không, KHÔNG ghi giá trị.
    if (field.readonly && String(el.value || "").trim()) field.note = "Cổng đổ sẵn theo tài khoản";
    if (!visible(el.closest(".bootstrap-select") || el) && !visible(el)) field.hiddenAtCapture = true;
    section.fields.push(field);
  }
  form.sections = form.sections.filter((s) => s.fields.length);
  const total = form.sections.reduce((n, s) => n + s.fields.length, 0);
  window.__capturedBcaForm = form;

  const blob = new Blob([JSON.stringify(form, null, 1)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `bca-form-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  console.log(`[capture-bca] XONG: ${form.sections.length} khối, ${total} ô, đã tải ${a.download}. `
    + "Đặt lại showWhen / showWhenDeclarant / portalDecides / portalMayFill theo mẫu cũ trước khi lưu đè.");
  return form;
})();
