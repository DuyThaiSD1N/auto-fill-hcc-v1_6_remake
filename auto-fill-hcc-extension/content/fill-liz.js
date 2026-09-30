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
  // Nhãn cổng hay kèm dấu chấm/hai chấm/dấu * bắt buộc ở cuối ("…tại điểm.") → bỏ để khớp đúng nhãn BE.
  const foldLabel = (s) => fold(s).replace(/[\s.:*]+$/, "");

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

  // Ô khai báo bằng `placeholder` (không có <mat-label>) — vd "Tên điểm du lịch…", "Trình độ ngoại ngữ…"
  // của thẻ HDV — chỉ có label nổi .mat-form-field-label / data-placeholder trên input → đọc lần lượt.
  function labelOf(matField) {
    const lbl = matField.querySelector("mat-label, .mat-form-field-label, .mdc-floating-label, label");
    const text = lbl && lbl.textContent.trim();
    if (text) return foldLabel(text);
    const inp = matField.querySelector("input, textarea");
    const ph = inp && (inp.getAttribute("data-placeholder") || inp.getAttribute("placeholder") ||
      inp.getAttribute("aria-label"));
    return ph ? foldLabel(ph) : "";
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
    const sec = fold(section), lab = foldLabel(label);
    // (1) khớp đúng (section, label).
    let mf = index.get(sec + "||" + lab);
    if (mf) return mf;
    // (2) section khớp lỏng (chứa nhau) + label đúng — phòng khi group-header có hậu tố.
    for (const [key, el] of index) {
      const [s, l] = key.split("||");
      if (l === lab && (s.includes(sec) || sec.includes(s))) return el;
    }
    // (3) chỉ khớp label — CHỈ khi BE không yêu cầu section. Có section mà không thấy ô đúng khối thì BỎ:
    // nhãn "Nơi cấp/Địa chỉ chi tiết" lặp giữa các khối, khối đích chưa render thì ô DUY NHẤT còn lại là
    // của khối khác (vd người nộp) → ghi đè nhầm người.
    if (sec) return null;
    const byLabel = [];
    for (const [key, el] of index) if (key.endsWith("||" + lab)) byLabel.push(el);
    return byLabel.length === 1 ? byLabel[0] : null;
  }

  const isDateField = (mf) => !!(mf.closest("liz-datepicker, liz-date") || mf.querySelector(
    "mat-datepicker-toggle, .mat-datepicker-toggle, input[matdatepicker], .mat-datepicker-input"
  ));

  // Dự phòng khi nhãn cổng in khác mọi nhãn BE biết (vd "Ngày cấp"/"Nơi cấp" của thẻ HDV cũ): BE gửi
  // `after` = nhãn ô MỐC đứng ngay trước → lấy ô ĐẦU TIÊN cùng loại (ngày / chữ) trong tối đa 3 ô sau mốc,
  // cùng section. Bỏ qua mat-select; hết section thì dừng — không bao giờ trượt sang khối khác.
  function findFieldAfter(index, f) {
    let anchor = null;
    for (const label of [].concat(f.after)) {
      anchor = findField(index, f.section || "", label);
      if (anchor) break;
    }
    if (!anchor) return null;
    const sec = sectionOf(anchor);
    const all = Array.from(document.querySelectorAll("mat-form-field")).filter(isVisible);
    const start = all.indexOf(anchor);
    const wantDate = f.comp === "liz-date";
    for (let i = start + 1; start >= 0 && i < all.length && i <= start + 3; i++) {
      const mf = all[i];
      if (sectionOf(mf) !== sec) break;
      if (mf.querySelector("mat-select") || isDateField(mf) !== wantDate) continue;
      return mf;
    }
    return null;
  }

  function inputOf(matField) {
    // Có form dùng <textarea> cho ô nội dung dài (tóm tắt tài liệu, ghi chú) — cùng cách gõ như input.
    return matField.querySelector(
      "input.mat-input-element, textarea.mat-input-element, input[matinput], textarea[matinput], input, textarea"
    );
  }

  // Ô chỉ nhận số (vd "Số lượng" của thông báo quảng cáo băng-rôn) mà BE gửi cả câu "Kích thước: 0.8m x 3m;
  // Số lượng: 105" → trình duyệt bỏ chuỗi, ô trống. Rút số: ưu tiên số sau "số lượng"; không có thì cộng các
  // số đi kèm đơn vị đếm ("30 tấm; 10 tấm" → 40); còn lại chỉ nhận khi chuỗi có ĐÚNG một số nguyên.
  function numberFromText(value) {
    const text = fold(value);
    const labeled = text.match(/so luong\s*[:\-]?\s*(\d[\d.]*)/);
    if (labeled) return labeled[1].replace(/\./g, "");
    const counted = [...text.matchAll(/(\d[\d.]*)\s*(tam|cai|chiec|bang|bo|to)\b/g)];
    if (counted.length) return String(counted.reduce((sum, m) => sum + Number(m[1].replace(/\./g, "")), 0));
    const all = text.match(/\d+/g) || [];
    return all.length === 1 ? all[0] : "";
  }

  // Ô text / ngày: gõ trực tiếp (ngày dạng dd/mm/yyyy). Bỏ qua ô disabled (cổng tự điền từ tài khoản).
  function fillLizText(matField, value) {
    const inp = inputOf(matField);
    if (!inp) return "notfound";
    if (inp.disabled || inp.readOnly) return "disabled";
    inp.focus();
    setNativeValue(inp, String(value));
    if (String(value).trim() && !String(inp.value || "").trim()) {
      const num = numberFromText(value);
      console.warn(`[AutoFill-LIZ] Ô từ chối "${value}" (type=${inp.type}) → thử số "${num}"`);
      if (!num) return "notmatch";
      setNativeValue(inp, num);
    }
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

    // Giá trị gộp "Xã …, Tỉnh …" (ô Địa chỉ hành chính): tách phần xã/tỉnh để lọc và để khớp chặt cả hai.
    const parts = String(value).split(",").map((p) => p.trim()).filter(Boolean);
    const bare = (p) => fold(p).replace(/^(xa|phuong|thi tran|dac khu|tinh|thanh pho|tp\.?)\s+/, "").trim();
    const wardBare = parts.length > 1 ? bare(parts[0]) : "";
    const provinceBare = parts.length > 1 ? bare(parts[parts.length - 1]) : "";
    const matchesArea = (text) => {
      const t = fold(text);
      return !!wardBare && t.includes(wardBare) && t.includes(provinceBare);
    };
    const pick = () => {
      const opts = matOptions().filter((o) => !o.querySelector("input"));
      return opts.find((o) => fold(o.textContent) === want) ||
        (wardBare ? opts.find((o) => matchesArea(o.textContent)) : null) ||
        opts.find((o) => optMatch(o.textContent, want)) || null;
    };

    // Ô lọc trong panel (ngx-mat-select-search). Danh sách chỉ nạp SẴN một phần (vd toàn Hà Nội) — option
    // tỉnh khác chỉ hiện khi gõ lọc, và bộ lọc tìm theo TÊN XÃ: gõ nguyên "Xã A, Tỉnh B" thì không ra gì.
    // Gõ tên xã trần trước; không ra thì thử nguyên chuỗi.
    const search = document.querySelector(
      ".cdk-overlay-pane .mat-select-search-inner input[type=text], .cdk-overlay-pane input[type=text], " +
      ".mat-select-search-inner input, .mat-select-panel input[type=text]"
    );
    if (search && !pick()) {
      const terms = [...new Set([wardBare ? parts[0].replace(/^(xã|phường|thị trấn|đặc khu)\s+/i, "") : "", String(value)])]
        .filter(Boolean);
      for (const term of terms) {
        search.focus();
        setNativeValue(search, term);
        search.dispatchEvent(new Event("input", { bubbles: true }));
        search.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true, key: term.slice(-1) }));
        await waitFor(() => !!pick(), 4000);
        if (pick()) break;
      }
    }

    const opts = matOptions();
    const target = pick();
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

  // Ô tích (liz-checkbox), khớp theo nhãn. Chỉ bấm khi trạng thái hiện tại KHÁC giá trị cần — chạy lại
  // lượt điền không được bỏ tích. Không bao giờ khớp mờ sang ô khác: nhãn phải bằng hoặc chứa trọn nhãn cần.
  // Nhóm nhiều ô trong một liz-checkbox (vd "Đã được cấp thẻ … loại: Nội địa / Quốc tế / Tại điểm"): BE gửi
  // kèm `option` = nhãn ô cần tích → trả về đúng <mat-checkbox> đó trong nhóm có nhãn `labels`. Không thấy
  // nhóm theo nhãn thì chỉ nhận ô có nhãn BẰNG ĐÚNG option, không khớp chứa nhau sang ô khác.
  function findLizOption(labels, option) {
    const want = fold(option);
    if (!want) return null;
    const boxes = Array.from(document.querySelectorAll("liz-checkbox")).filter(isVisible);
    const wants = labels.map(fold).filter(Boolean);
    const group = boxes.find((b) => wants.some((w) => fold(b.textContent).includes(w)));
    const opts = Array.from((group || document).querySelectorAll("liz-checkbox mat-checkbox")).filter(isVisible);
    return opts.find((o) => fold(o.textContent) === want) ||
      (group ? opts.find((o) => fold(o.textContent).startsWith(want)) : null) || null;
  }

  function findLizCheckbox(label, option, aliases) {
    if (option) return findLizOption([label, ...(aliases || [])], option);
    const want = fold(label);
    if (!want) return null;
    const boxes = Array.from(document.querySelectorAll("liz-checkbox")).filter(isVisible);
    return boxes.find((b) => fold(b.textContent) === want) ||
      boxes.find((b) => fold(b.textContent).includes(want)) || null;
  }

  async function fillLizCheckbox(label, value, option, aliases) {
    const box = findLizCheckbox(label, option, aliases);
    const input = box && box.querySelector("input[type=checkbox]");
    if (!input) return "notfound";
    if (input.disabled) return "disabled";
    const want = value === true || ["true", "1", "co", "yes"].includes(fold(value));
    // Khối phụ thuộc (vd "Thông tin người ủy quyền") render SAU khi tích, có thể chậm hơn vài trăm ms —
    // dựng chỉ mục sớm thì các ô của khối chưa có. Đếm ô hiển thị TRƯỚC khi bấm, chờ số đó đổi (tối đa 3s).
    const visibleFields = () => Array.from(document.querySelectorAll("mat-form-field")).filter(isVisible).length;
    if (input.checked !== want) {
      const before = visibleFields();
      input.click();
      await waitFor(() => input.checked === want, 1500);
      if (input.checked === want) await waitFor(() => visibleFields() !== before, 3000);
    }
    if (input.checked !== want) return "notmatch";
    markFilled(box.querySelector("mat-checkbox") || box);
    await sleep(200);
    return "ok";
  }

  async function fillFormLiz(fields) {
    injectAutofillStyles();
    clearAutofillMarks();
    const result = { filled: 0, notFound: [], errors: [], skipped: [] };
    let index = buildIndex();

    for (const f of fields) {
      if (f.comp === "liz-checkbox") {
        const r = await fillLizCheckbox(f.name, f.value, f.option, f.aliases);
        if (r === "ok") { result.filled++; index = buildIndex(); }
        else if (r === "disabled") result.skipped.push(f.name);
        else {
          result.notFound.push(f.name);
          console.warn(`[AutoFill-LIZ] Không tích được ô "${f.name}"${f.option ? ` / "${f.option}"` : ""} (${r})`);
        }
        continue;
      }
      // Nhãn chính trước, rồi từng alias — vẫn trong đúng section (nhãn cổng in khác bản mapping 1–2 chữ).
      let mf = null;
      for (const label of [f.name, ...(Array.isArray(f.aliases) ? f.aliases : [])]) {
        mf = findField(index, f.section || "", label);
        if (mf) break;
      }
      if (!mf && f.after) mf = findFieldAfter(index, f);
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
