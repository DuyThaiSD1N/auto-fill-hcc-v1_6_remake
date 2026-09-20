// Engine fill cổng Bộ VHTTDL (dichvucong.bvhttdl.gov.vn) — Angular Material "liz-*".
// DOM đã strip formcontrolname → KHÔNG khớp được như fill-angular.js. Khớp ô theo
// (section = .group-header, nhãn = <mat-label>) vì nhãn LẶP giữa các phần (Ngày sinh/Số điện thoại/
// Ngày cấp/Nơi cấp/Địa chỉ...). BE gửi mỗi field kèm {name=<mat-label>, section=<group-header>, comp}.
// Tách từ content.js — dùng namespace window.__HCC__.
(() => {
  const H = window.__HCC__ || (window.__HCC__ = {});
  const {
    sleep, norm, setNativeValue, isVisible, waitFor, markFilled, markUnfilled,
    clearAutofillMarks, injectAutofillStyles,
  } = H;

  // norm() chỉ lowercase, KHÔNG bỏ dấu → fold bỏ dấu để khớp nhãn tiếng Việt ổn định.
  const fold = (s) => norm(s).normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").trim();

  // Text nhãn section của 1 mat-form-field: leo lên .group gần nhất → lấy .group-header.
  function sectionOf(matField) {
    const group = matField.closest(".group") ||
      (function () { // fallback: leo lên tới phần tử có con .group-header
        let cur = matField;
        for (let i = 0; cur && i < 8; i++, cur = cur.parentElement) {
          if (cur.querySelector && cur.querySelector(":scope > .group-header, :scope > div > .group-header")) return cur;
        }
        return null;
      })();
    if (!group) return "";
    const hdr = group.querySelector(".group-header");
    return hdr ? fold(hdr.textContent) : "";
  }

  function labelOf(matField) {
    const lbl = matField.querySelector("mat-label");
    return lbl ? fold(lbl.textContent) : "";
  }

  // Lập chỉ mục mọi mat-form-field theo (section, label) → phần tử. Nhãn lặp giữa section nên key gộp cả 2.
  function buildIndex() {
    const map = new Map();
    document.querySelectorAll("mat-form-field").forEach((mf) => {
      if (!isVisible(mf)) return;
      const key = sectionOf(mf) + "||" + labelOf(mf);
      if (!map.has(key)) map.set(key, mf);
    });
    return map;
  }

  function findField(index, section, label) {
    const sec = fold(section), lab = fold(label);
    // (1) khớp đúng (section, label).
    let mf = index.get(sec + "||" + lab);
    if (mf) return mf;
    // (2) section khớp lỏng (chứa nhau) + label đúng — phòng khi group-header có hậu tố.
    for (const [key, el] of index) {
      const [s, l] = key.split("||");
      if (l === lab && (s.includes(sec) || sec.includes(s))) return el;
    }
    // (3) chỉ khớp label (khi form không dựng section như mẫu) — chỉ nhận nếu DUY NHẤT.
    const byLabel = [];
    for (const [key, el] of index) if (key.endsWith("||" + lab)) byLabel.push(el);
    return byLabel.length === 1 ? byLabel[0] : null;
  }

  function inputOf(matField) {
    // Có form dùng <textarea> cho ô nội dung dài (tóm tắt tài liệu, ghi chú) — cùng cách gõ như input.
    return matField.querySelector(
      "input.mat-input-element, textarea.mat-input-element, input[matinput], textarea[matinput], input, textarea"
    );
  }

  // Ô text / ngày: gõ trực tiếp (ngày dạng dd/mm/yyyy). Bỏ qua ô disabled (cổng tự điền từ tài khoản).
  function fillLizText(matField, value) {
    const inp = inputOf(matField);
    if (!inp) return "notfound";
    if (inp.disabled || inp.readOnly) return "disabled";
    inp.focus();
    setNativeValue(inp, String(value));
    inp.dispatchEvent(new Event("input", { bubbles: true }));
    inp.dispatchEvent(new Event("blur", { bubbles: true }));
    markFilled(matField);
    return "ok";
  }

  const matOptions = () => Array.from(document.querySelectorAll(
    ".mat-select-panel mat-option, .cdk-overlay-pane mat-option, .mat-mdc-select-panel mat-option, mat-option"
  ));

  function optMatch(text, want) {
    const t = fold(text);
    return !!t && (t === want || t.includes(want) || want.includes(t));
  }

  // mat-select overlay: mở → (gõ lọc nếu có ô search) → chọn option khớp.
  async function fillLizSelect(matField, value) {
    const ms = matField.querySelector("mat-select");
    if (!ms) return fillLizText(matField, value); // fallback
    const want = fold(value);

    // Đã chọn sẵn đúng giá trị?
    const cur = fold((ms.querySelector(".mat-mdc-select-value-text, .mat-select-value-text") || {}).textContent || "");
    if (cur && optMatch(cur, want)) { markFilled(matField); return "ok"; }

    const trigger = ms.querySelector(".mat-mdc-select-trigger, .mat-select-trigger") || ms;
    trigger.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    trigger.click();
    await waitFor(() => matOptions().length > 0, 2500);

    // Ô lọc trong panel (mat-select có filter) → gõ để nạp option đúng.
    const search = document.querySelector(
      ".cdk-overlay-pane input[type=text], .mat-select-search-inner input, .mat-select-panel input[type=text]"
    );
    if (search) {
      search.focus();
      setNativeValue(search, String(value));
      search.dispatchEvent(new Event("input", { bubbles: true }));
      await waitFor(() => matOptions().some((o) => optMatch(o.textContent, want)), 2500);
    }

    const opts = matOptions();
    const target = opts.find((o) => fold(o.textContent) === want) || opts.find((o) => optMatch(o.textContent, want));
    if (!target) {
      console.warn(`[AutoFill-LIZ] mat-select không khớp "${value}". Option:`,
        opts.map((o) => o.textContent.trim()).filter(Boolean).slice(0, 25));
      const bd = document.querySelector(".cdk-overlay-backdrop");
      if (bd) bd.click();
      return "notmatch";
    }
    target.click();
    await sleep(150);
    markFilled(matField);
    return "ok";
  }

  async function fillFormLiz(fields) {
    injectAutofillStyles();
    clearAutofillMarks();
    const result = { filled: 0, notFound: [], errors: [], skipped: [] };
    const index = buildIndex();

    for (const f of fields) {
      const mf = findField(index, f.section || "", f.name);
      if (!mf) {
        result.notFound.push(f.name);
        console.warn(`[AutoFill-LIZ] Không thấy ô (section="${f.section}", label="${f.name}")`);
        continue;
      }
      try {
        let r;
        if (f.comp === "liz-select") r = await fillLizSelect(mf, f.value);
        else r = fillLizText(mf, f.value); // liz-input, liz-date
        if (r === "ok") result.filled++;
        else if (r === "disabled") result.skipped.push(f.name); // cổng tự điền, bỏ qua (không tính lỗi)
        else { result.notFound.push(f.name); markUnfilled(mf); }
      } catch (e) {
        result.errors.push(f.name);
        console.warn(`[AutoFill-LIZ] Lỗi điền ${f.name}:`, e);
      }
    }
    console.log("[AutoFill-LIZ] Kết quả:", result);
    return result;
  }

  H.fillFormLiz = fillFormLiz;
})();
