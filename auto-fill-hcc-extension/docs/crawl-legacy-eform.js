/**
 * Crawl biểu mẫu eForm LEGACY (web-component x-*) của tokhaidientu.moj.gov.vn.
 * Dùng để dựng/đối chiếu UI_COMP_BY_NAME cho một thủ tục — vd "Cấp bản sao trích lục hộ tịch".
 *
 * ═══ CÁCH CHẠY ═══
 * 1. Mở trang thủ tục, đợi biểu mẫu hiện đầy đủ.
 * 2. F12 → tab Console → **đổi context sang iframe eForm** ở dropdown cạnh nút lọc
 *    (mặc định là "top"; chọn dòng chứa `tokhaidientu.moj.gov.vn`).
 *    BẮT BUỘC: iframe khác origin với trang cha nên chạy ở "top" sẽ bị chặn.
 * 3. Dán toàn bộ file này vào Console rồi Enter.
 *    (Lần đầu Chrome bắt gõ "allow pasting" — gõ đúng chữ đó rồi dán lại.)
 *
 * ═══ KẾT QUẢ ═══
 *   - Bảng field in ra Console (console.table)
 *   - window.__EFORM__.fields  : mảng field thô, còn giữ tham chiếu DOM
 *   - window.__EFORM__.json    : JSON để lưu ra file
 *   - window.__EFORM__.python  : đoạn UI_COMP_BY_NAME dán thẳng vào schema.py
 *   - Tự copy `python` vào clipboard nếu DevTools cho phép
 *
 * ═══ LƯU Ý QUAN TRỌNG ═══
 * eForm dựng khối con THEO ĐIỀU KIỆN. Field chỉ tồn tại trong DOM khi khối cha đã bung:
 *   · Tick (5) "Quan hệ với người được cấp bản sao" → hiện/ẩn khối nhân thân
 *   · Tick (11) "Nơi cư trú: Trong nước / Khác"     → đổi hẳn widget địa chỉ
 *   · Chọn (12) "Loại việc yêu cầu"                 → có thể hiện thêm ô
 * ⇒ Chạy 1 lần là THIẾU. Hãy tick qua từng nhánh rồi chạy lại; script tự gộp dồn
 *   vào window.__EFORM__ qua các lần chạy (xem dòng "đã gộp N field").
 */
(() => {
  "use strict";

  // Đúng danh sách tag mà content/fill-legacy.js biết điền. Thấy tag lạ → cần bổ sung filler.
  const COMP_TAGS = [
    "x-input",
    "x-input-number",
    "x-date",
    "x-date-text",
    "x-radio",
    "x-select",
    "x-select-default",
    "x-select-area",
  ];

  // Schema trích lục hiện có trong app/pipelines/trich_luc/process/schema.py — để đối chiếu
  // form THẬT với thứ backend đang khai. Đổi/xoá khi crawl thủ tục khác.
  const KNOWN = {
    HoVaTenC: "x-input",
    SoDinhDanhC: "x-input",
    LoaiGiayToDinhDanhC: "x-select",
    NYC_SoGiayToTuyThan: "raw",
    NgayCapDDC: "x-date",
    NoiCapDDC: "x-input",
    NYC_LoaiCuTru: "x-select",
    NYC_NoiCuTru: "x-radio",
    NYC_NoiCuTru_TrongNuoc: "x-select-area",
    NDK_HoVaTen: "x-input",
    NDK_NgaySinh: "x-date-text",
    NDK_GioiTinh: "x-select",
    NDK_DanToc: "x-select",
    NDK_DanTocKhac: "x-select-area",
    NDK_QuocTich: "x-select",
    NDK_SoDinhDanh: "x-input",
    NDK_LoaiGiayToTuyThan: "x-select",
    NDK_SoGiayToTuyThan: "x-input",
    NDK_NgayCap: "x-date",
    NDK_NoiCap: "x-input",
    NDK_LoaiCuTru: "x-select",
    NDK_NoiCuTru: "x-radio",
    NDK_NoiCuTru_TrongNuoc: "x-select-area",
    HoSo_LoaiYeuCau: "x-select",
    HoSo_CoQuanDangKy: "x-input",
    HoSo_TenGiayTo: "x-input",
    HoSo_So: "x-input",
    HoSo_QuyenSo: "x-input",
    HoSo_NgayCapSo: "x-date",
    PhuongThucNhanKQ: "x-radio",
    NYC_QuanHe: "x-radio",
    SoLuong: "raw",
  };
  // Tên thay thế giữa các phiên bản form (UI_ALIASES trong schema.py) — coi là CÙNG một field.
  const ALIASES = {
    HoVaTenC: ["NYC_HoVaTen"],
    SoDinhDanhC: ["NYC_SoDinhDanh"],
    LoaiGiayToDinhDanhC: ["NYC_LoaiGiayToTuyThan"],
    NYC_SoGiayToTuyThan: ["SoGiayToDinhDanhC"],
    NgayCapDDC: ["NYC_NgayCap"],
    NoiCapDDC: ["NYC_NoiCap"],
  };

  // ─────────────────────────── tìm document chứa eForm ───────────────────────────
  function findDoc() {
    if (document.querySelector(COMP_TAGS.join(","))) return document;
    for (const frame of document.querySelectorAll("iframe")) {
      try {
        const doc = frame.contentDocument || frame.contentWindow.document;
        if (doc && doc.querySelector(COMP_TAGS.join(","))) return doc;
      } catch (_) {
        /* khác origin — không đọc được từ đây, phải đổi context console */
      }
    }
    return null;
  }

  const doc = findDoc();
  if (!doc) {
    console.error(
      "%c[crawl-eform] Không thấy web-component x-* nào.",
      "color:#c62828;font-weight:bold"
    );
    console.info(
      "Nhiều khả năng bạn đang chạy ở context 'top' trong khi form nằm trong iframe khác origin.\n" +
        "→ Console → dropdown context (cạnh ô lọc) → chọn dòng 'tokhaidientu.moj.gov.vn' → dán lại."
    );
    const frames = Array.from(document.querySelectorAll("iframe")).map((f) => f.src);
    if (frames.length) console.info("iframe thấy được trên trang:", frames);
    return;
  }

  // ─────────────────────────── tiện ích ───────────────────────────
  const clean = (s) => String(s || "").replace(/\s+/g, " ").trim();

  /** Nhãn field: eForm không dùng <label for>, nhãn là text đứng NGAY TRƯỚC component. */
  function labelOf(el) {
    let node = el;
    for (let up = 0; up < 4 && node; up++) {
      for (let sib = node.previousSibling; sib; sib = sib.previousSibling) {
        const text = clean(sib.textContent);
        // Bỏ mẩu rác 1 ký tự và đoạn quá dài (thường là cả section).
        if (text.length > 1 && text.length <= 160) return text;
      }
      node = node.parentElement;
    }
    return "";
  }

  /** Tiêu đề mục (I. / II. ...) gần nhất phía trên — giúp nhóm field khi viết schema. */
  function sectionOf(el) {
    const heads = Array.from(doc.querySelectorAll("b, strong, h1, h2, h3, h4, legend, p"));
    let best = "";
    for (const h of heads) {
      const text = clean(h.textContent);
      if (!/^(I{1,3}|IV|V)[.、]/.test(text) || text.length > 120) continue;
      // compareDocumentPosition: h đứng TRƯỚC el thì lấy làm section hiện hành.
      if (h.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING) best = text;
    }
    return best;
  }

  /** Các lựa chọn của x-radio: value THẬT là hậu tố id sau dấu '-' (fill-legacy.js khớp theo đó). */
  function radioOptions(el) {
    return Array.from(el.querySelectorAll('input[type="checkbox"]')).map((box) => {
      const id = box.id || "";
      const label = el.querySelector(`label[for="${CSS.escape(id)}"]`);
      return {
        value: id.includes("-") ? id.slice(id.lastIndexOf("-") + 1) : box.value || "",
        label: clean(label && label.textContent),
        id,
        checked: !!box.checked,
      };
    });
  }

  /** Option của dropdown. Nhiều widget chỉ render list SAU KHI click → trả [] kèm cảnh báo. */
  function selectOptions(el) {
    const native = Array.from(el.querySelectorAll("select option"));
    if (native.length) {
      return native.map((o) => ({ value: o.value, label: clean(o.textContent) }));
    }
    const rendered = Array.from(el.querySelectorAll('[role="option"], .option-item, li'));
    return rendered
      .map((o) => ({ value: clean(o.getAttribute("data-value") || ""), label: clean(o.textContent) }))
      .filter((o) => o.label);
  }

  /** Ô con của x-date (name$="-day") và x-date-text (id$="-day"). */
  function datePartsOf(el, comp) {
    const attr = comp === "x-date" ? "name" : "id";
    return ["day", "month", "year"]
      .filter((p) => el.querySelector(`input[${attr}$="-${p}"]`))
      .join("/");
  }

  function currentValue(el, comp) {
    if (comp === "x-select") return clean(el.querySelector(".input-field-select")?.textContent);
    if (comp === "x-select-default") {
      return clean(el.querySelector('[id^="custom-select-default-"] div[tabindex]')?.textContent);
    }
    if (comp === "x-radio") return radioOptions(el).filter((o) => o.checked).map((o) => o.value).join(",");
    return clean(el.querySelector("input")?.value);
  }

  // ─────────────────────────── quét ───────────────────────────
  const found = [];

  for (const tag of COMP_TAGS) {
    for (const el of doc.querySelectorAll(`${tag}[name]`)) {
      const name = el.getAttribute("name");
      if (!name) continue;
      const row = {
        name,
        comp: tag,
        label: labelOf(el),
        section: sectionOf(el),
        value: currentValue(el, tag),
        el,
      };
      if (tag === "x-radio") row.options = radioOptions(el);
      if (tag === "x-select" || tag === "x-select-default") {
        row.options = selectOptions(el);
        if (!row.options.length) row.note = "dropdown chưa render option — mở nó ra rồi chạy lại";
      }
      if (tag === "x-date" || tag === "x-date-text") row.parts = datePartsOf(el, tag);
      found.push(row);
    }
  }

  // input trần không nằm trong component nào → fill-legacy.js gọi là comp "raw".
  for (const input of doc.querySelectorAll("input[name]")) {
    const name = input.getAttribute("name");
    if (!name || input.type === "checkbox" || input.type === "radio") continue;
    if (input.closest(COMP_TAGS.join(","))) continue;
    if (/-(day|month|year|name-date-input)$/.test(name)) continue; // ô con của x-date
    found.push({
      name,
      comp: "raw",
      label: labelOf(input),
      section: sectionOf(input),
      value: clean(input.value),
      el: input,
    });
  }

  // ─────────────────────────── gộp dồn qua nhiều lần chạy ───────────────────────────
  const store = (window.__EFORM__ = window.__EFORM__ || { fields: [], runs: 0 });
  store.runs++;
  const byName = new Map(store.fields.map((f) => [f.name + "|" + f.comp, f]));
  let added = 0;
  for (const row of found) {
    const key = row.name + "|" + row.comp;
    if (byName.has(key)) {
      Object.assign(byName.get(key), row); // cập nhật option/giá trị mới bung ra
    } else {
      byName.set(key, row);
      added++;
    }
  }
  store.fields = Array.from(byName.values()).sort(
    (a, b) => (a.section || "").localeCompare(b.section || "") || a.name.localeCompare(b.name)
  );

  // ─────────────────────────── xuất ───────────────────────────
  const fields = store.fields;

  console.log(
    `%c[crawl-eform] lần chạy #${store.runs}: thấy ${found.length} field, mới ${added}, tổng đã gộp ${fields.length}`,
    "color:#1565c0;font-weight:bold"
  );
  console.table(
    fields.map((f) => ({
      name: f.name,
      comp: f.comp,
      label: f.label,
      options: f.options ? f.options.length : "",
      parts: f.parts || "",
      note: f.note || "",
    }))
  );

  // Tên trùng nhau ở hai comp khác nhau → gần như chắc chắn crawl nhầm hoặc form có 2 widget cùng tên.
  const dup = fields
    .map((f) => f.name)
    .filter((n, i, a) => a.indexOf(n) !== i)
    .filter((n, i, a) => a.indexOf(n) === i);
  if (dup.length) console.warn("[crawl-eform] Tên xuất hiện ở nhiều comp:", dup);

  // Đối chiếu với schema backend.
  const alias = new Map();
  for (const [main, list] of Object.entries(ALIASES)) for (const a of list) alias.set(a, main);
  const canon = (n) => alias.get(n) || n;
  const live = new Set(fields.map((f) => canon(f.name)));
  const declared = new Set(Object.keys(KNOWN).map(canon));

  const missing = [...declared].filter((n) => !live.has(n));
  const extra = [...live].filter((n) => !declared.has(n));
  const wrongComp = fields
    .filter((f) => KNOWN[canon(f.name)] && KNOWN[canon(f.name)] !== f.comp && KNOWN[canon(f.name)] !== "raw")
    .map((f) => `${f.name}: schema=${KNOWN[canon(f.name)]} ≠ form=${f.comp}`);

  console.groupCollapsed("%c[crawl-eform] Đối chiếu với schema backend", "color:#6a1b9a;font-weight:bold");
  console.log("Schema khai nhưng KHÔNG thấy trên form (có thể do khối chưa bung):", missing);
  console.log("Có trên form nhưng schema CHƯA khai:", extra);
  console.log("Lệch comp:", wrongComp);
  console.groupEnd();

  const jsonFields = fields.map(({ el, ...rest }) => rest); // bỏ tham chiếu DOM để stringify được
  store.json = JSON.stringify(jsonFields, null, 2);

  store.python =
    "UI_COMP_BY_NAME = {\n" +
    fields
      .map((f) => {
        const cmt = [f.section, f.label].filter(Boolean).join(" · ");
        return `    ${JSON.stringify(f.name)}: ${JSON.stringify(f.comp)},` + (cmt ? `  # ${cmt}` : "");
      })
      .join("\n") +
    "\n}\n";

  console.log("%c→ window.__EFORM__.python  (dán vào schema.py)", "color:#2e7d32");
  console.log("%c→ window.__EFORM__.json    (lưu ra file)", "color:#2e7d32");
  console.log(store.python);

  try {
    if (typeof copy === "function") {
      copy(store.python);
      console.log("%c✓ Đã copy đoạn Python vào clipboard.", "color:#2e7d32;font-weight:bold");
    }
  } catch (_) {
    /* copy() chỉ có trong DevTools console, không phải lúc nào cũng dùng được */
  }

  return store;
})();
