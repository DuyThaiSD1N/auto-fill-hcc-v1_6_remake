// Chạy trong MAIN world: biểu mẫu Cổng DVC quốc gia mới (/nop-ho-so) là SurveyJS trong React. Ô
// dropdown/ngày (flatpickr) chỉ nhận giá trị qua MODEL survey — gõ vào DOM không cập nhật model. Isolated
// content script không đọc được fiber React của trang → cầu nối CustomEvent. Bản chép từ
// auto-fill-hcc-extension/content/surveyjs-main.js, đổi tên sự kiện/thuộc tính để hai extension cài
// cùng máy không trả lời chồng lên nhau.
// Ngoài ra chặn hộp thoại chọn tệp của OS khi extension bấm nút "Tải lên file" để nạp tệp thẳng vào input.
(() => {
  if (!/(^|\.)dichvucong\.gov\.vn$/.test(location.hostname)) return;

  const REQUEST_EVENT = "__TLND_SJS_REQUEST__";
  const RESULT_EVENT = "__TLND_SJS_RESULT__";
  if (window.__TLND_SJS_HANDLER__) document.removeEventListener(REQUEST_EVENT, window.__TLND_SJS_HANDLER__);

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const fold = (s) => String(s ?? "")
    .replace(/Đ/g, "D").replace(/đ/g, "d")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  // Tiền tố hành chính khác nhau giữa nguồn ("Nghệ An") và option ("Tỉnh Nghệ An").
  const stripAdmin = (s) => fold(s).replace(/^(tinh|thanh pho|tp|xa|phuong|thi tran|dac khu)\s+/, "");

  // ---- Tìm model survey qua fiber React ----
  const isSurvey = (o) => !!o && typeof o.getQuestionByName === "function" && typeof o.getAllQuestions === "function";

  function fiberOf(el) {
    for (const key of Object.keys(el)) {
      if (key.startsWith("__reactFiber$") || key.startsWith("__reactInternalInstance$")) return el[key];
    }
    return null;
  }

  function surveyFromFiber(fiber) {
    for (let f = fiber, i = 0; f && i < 120; f = f.return, i++) {
      const props = f.memoizedProps || {};
      const found = [props.model, props.survey, props.question?.survey, props.element?.survey,
        props.creator?.survey, f.stateNode?.survey].find(isSurvey);
      if (found) return found;
    }
    return null;
  }

  // Model gắn với các ô ĐANG HIỂN THỊ, tìm lại ở mỗi lệnh — không giữ model qua các lệnh: cổng là ứng dụng một
  // trang, chuyển hồ sơ / dựng lại biểu mẫu thì tạo model mới mà trang không tải lại; model cũ vẫn nhận giá trị và
  // báo đã điền nhưng không còn trên màn hình (ô viền xanh mà trống). Trang có nhiều model (bản ẩn cùng câu hỏi)
  // → lấy model gắn với nhiều ô đang hiện nhất.
  function findSurvey() {
    const nodes = Array.from(document.querySelectorAll("[data-name]"));
    const shown = nodes.filter((n) => n.offsetParent !== null);
    const counts = new Map();
    for (const node of (shown.length ? shown : nodes).slice(0, 40)) {
      const fiber = fiberOf(node);
      const survey = fiber && surveyFromFiber(fiber);
      if (survey && survey.getQuestionByName(node.getAttribute("data-name"))) {
        counts.set(survey, (counts.get(survey) || 0) + 1);
      }
    }
    let best = null;
    for (const [survey, n] of counts) if (!best || n > counts.get(best)) best = survey;
    if (best) return best;
    for (const node of document.querySelectorAll(".sd-root-modern, .sv-root-modern")) {
      const fiber = fiberOf(node);
      const survey = fiber && surveyFromFiber(fiber);
      if (survey) return survey;
    }
    return null;
  }

  // BE gửi tên gốc (vd "citizenQuanhe"); data-name thật kèm hậu tố "__<số>" đổi theo phiên bản biểu mẫu.
  function findQuestion(survey, name) {
    const all = survey.getAllQuestions(false) || [];
    let matches = all.filter((q) => q.name === name || String(q.name).startsWith(`${name}__`));
    // Câu hỏi trong panel động (paneldynamic, vd "Nơi đăng ký khai sinh" của Lý lịch tư pháp khai hộ) không có trong
    // danh sách phẳng → tìm thêm ở câu hỏi lồng.
    if (!matches.length) {
      matches = (survey.getAllQuestions(false, false, true) || [])
        .filter((q) => q.name === name || String(q.name).startsWith(`${name}__`));
    }
    return matches.find((q) => q.isVisible) || matches[0] || null;
  }

  function choicesOf(q) {
    const list = q.visibleChoices?.length ? q.visibleChoices : (q.choices || []);
    // Bỏ option giả "item1" mẫu cổng để sẵn cho dropdown nạp từ API — giữ lại là tưởng danh mục đã nạp.
    return list
      .filter((c) => c && String(c.value) !== "item1")
      .map((c) => ({ value: c.value, text: String(c.text ?? c.calculatedText ?? c.value ?? "") }));
  }

  function matchScore(want, text, value) {
    const w = fold(want);
    if (!w) return 0;
    const t = fold(text);
    if (t === w || fold(value) === w) return 100;
    if (stripAdmin(t) === stripAdmin(w)) return 95;
    if (t && (t.includes(w) || w.includes(t))) return 80 - Math.min(20, Math.abs(t.length - w.length) / 4);
    const wt = new Set(w.split(" ")), tt = new Set(t.split(" "));
    const common = [...wt].filter((x) => tt.has(x)).length;
    return common ? Math.round((common / Math.max(wt.size, tt.size)) * 70) : 0;
  }

  function bestChoice(q, want) {
    let best = null;
    let bestScore = 0;
    for (const c of choicesOf(q)) {
      const s = matchScore(want, c.text, c.value);
      if (s > bestScore) { best = c; bestScore = s; }
    }
    return bestScore >= 50 ? best : null;
  }

  async function waitChoices(q, timeout = 8000) {
    const t0 = Date.now();
    while (Date.now() - t0 < timeout) {
      if (choicesOf(q).length) return true;
      await sleep(200);
    }
    return false;
  }

  function toIsoDate(value) {
    const m = String(value || "").trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    return m ? `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}` : String(value || "");
  }

  // Dropdown nạp danh mục lười qua API của cổng (tỉnh, xã theo tỉnh): mở dropdown một lần như cán bộ bấm để
  // cổng tự nạp, chờ danh sách về rồi đóng lại.
  async function openToLoad(q, timeout = 6000) {
    const root = document.querySelector(`[data-name="${CSS.escape(q.name)}"]`);
    const opener = root?.querySelector(".sd-dropdown, [role='combobox']");
    if (!opener) return false;
    const before = choicesOf(q).length;
    opener.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    opener.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    const t0 = Date.now();
    while (Date.now() - t0 < timeout && choicesOf(q).length <= before) await sleep(150);
    document.activeElement?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    document.activeElement?.blur?.();
    return choicesOf(q).length > before;
  }

  async function setChoice(q, value, code) {
    const pick = () => {
      // BE biết chắc mã option (danh mục tĩnh trong formJson) → khớp mã trước, rồi mới tới nhãn.
      if (code !== undefined && code !== null && code !== "") {
        const byCode = choicesOf(q).find((c) => String(c.value) === String(code));
        if (byCode) return byCode;
      }
      return bestChoice(q, value);
    };
    // Cascade tỉnh→xã: danh mục có thể đang tải sau khi ô cha vừa đổi → chờ ngắn trước.
    await waitChoices(q, 2000);
    let choice = pick();
    if (!choice && await openToLoad(q)) choice = pick();
    if (!choice) return { ok: false, reason: choicesOf(q).length ? "no-match" : "no-choices" };
    q.value = choice.value;
    return { ok: true, text: choice.text };
  }

  // Bảng nhiều dòng (matrixdynamic, vd "Ngành, nghề kinh doanh" của đăng ký thành lập hộ kinh doanh trên Cổng DVC quốc
  // gia): BE gửi mảng dòng {ma, ten, chiTiet, chinh}; cột dò theo tiêu đề. Danh mục ngành của cổng (nạp từ API theo chữ
  // gõ) ÍT ngành hơn danh mục cấp 4 đầy đủ của BE:
  // - Mã: chỉ nhận đúng mã. Chưa chọn được thì chọn TÊN trước rồi thử lại mã (danh mục mã có thể lọc theo tên); vẫn
  //   không có → không đoán, báo lại trong missingCodes để trợ lý / Auto Fill nói cho người dùng.
  // - Tên: chỉ khớp và chỉ gõ tìm theo CHỮ TÊN — không gõ mã vào ô lọc của cột tên (chữ gõ đọng lại, cán bộ tưởng tên
  //   ngành là "4719"); điền xong mà ô tên chỉ hiện một dãy số (mã) thì xoá. Tên chỉ ghi khi ô còn trống.
  // - Chi tiết ghi sau cùng (cổng có thể xoá khi đổi tên / mã) và ghi lại nếu bị xoá.
  // Điền lại với ít dòng hơn thì bỏ dòng thừa (bảng theo đúng danh sách BE). Lý do trượt ghi theo từng ô để dò trên
  // console.
  async function setMatrix(q, rows) {
    if (!Array.isArray(rows) || !rows.length) return { ok: false, reason: "no-rows" };
    const columns = q.columns || [];
    const col = (re) => columns.find((c) => re.test(fold(c.title || c.name)));
    const cols = { ma: col(/ma nganh/), ten: col(/ten nganh/), chiTiet: col(/chi tiet/), chinh: col(/nganh chinh/) };
    if (!cols.ma && !cols.ten) return { ok: false, reason: "no-columns" };
    if ((q.rowCount || 0) !== rows.length) q.rowCount = rows.length;
    await sleep(300);
    const visible = q.visibleRows || [];
    const failed = [];
    const missingCodes = [];
    for (let i = 0; i < rows.length; i++) {
      const row = visible[i];
      const want = rows[i] || {};
      if (!row) { failed.push(`${i + 1}(no-row)`); continue; }
      const notes = [];
      const cellOf = (c) => (c
        ? (row.getQuestionByColumnName?.(c.name) || (row.cells || []).find((x) => x.column === c)?.question || null)
        : null);
      const setCell = async (key, value, code, strict = false) => {
        const cq = cellOf(cols[key]);
        if (!cq || value === undefined || value === null || value === "") return true;
        if (cq.isReadOnly) {
          if (cq.isEmpty?.()) notes.push(`${key}:readonly`);
          return !cq.isEmpty?.();
        }
        const type = cq.getType?.() || "";
        if (["dropdown", "radiogroup", "tagbox"].includes(type)) {
          const r = await setCellChoice(cq, value, code, strict, key === "ten");
          if (!r.ok) notes.push(`${key}:${r.reason}`);
          return r.ok;
        }
        if (type === "checkbox") {
          const first = choicesOf(cq)[0];
          cq.value = value ? [first ? first.value : true] : [];
          return true;
        }
        if (type === "boolean") { cq.value = !!value; return true; }
        cq.value = String(value);
        return true;
      };
      const tenEmpty = () => !!cellOf(cols.ten)?.isEmpty?.();
      const had = (v) => v !== undefined && v !== null && v !== "" && !(Array.isArray(v) && !v.length);
      const clearCell = (cq) => {
        cq.clearValue?.();
        if (!cq.isEmpty?.()) cq.value = undefined;
      };
      const maCell = cellOf(cols.ma);
      const maBefore = maCell?.value;
      const tenBefore = cellOf(cols.ten)?.value;
      let ok = true;
      let maOk = await setCell("ma", want.ma, want.ma, true);
      const staleTen = cellOf(cols.ten);
      if (maOk && had(maBefore) && maCell?.value !== maBefore && staleTen && had(tenBefore)
          && staleTen.value === tenBefore) {
        // Điền lại dòng đang mang ngành khác: mã vừa đổi mà cổng không tự đổ lại tên → bỏ tên cũ để ghi tên mã mới.
        clearCell(staleTen);
      }
      let tenTried = false;
      if (!maOk && want.ten && tenEmpty()) {
        tenTried = true;
        ok = (await setCell("ten", want.ten, want.ma)) && ok;
        await sleep(300);
        maOk = await setCell("ma", want.ma, want.ma, true);
      }
      ok = maOk && ok;
      if (want.ma && maOk) await sleep(300);
      if (!tenTried && tenEmpty()) ok = (await setCell("ten", want.ten, want.ma)) && ok;
      if (cols.ma && want.ma && !maOk) {
        missingCodes.push(String(want.ma));
        // Cổng không có mã này: dòng chỉ hợp lệ khi đủ mã lẫn tên → bỏ mã cũ còn sót (điền lại) và tên vừa chọn theo chữ,
        // giữ ô chi tiết để người dùng biết dòng này kinh doanh gì; lượt điền lại sau đó ghi được ngành mới.
        if (maCell && !maCell.isEmpty?.()) clearCell(maCell);
        const tenLeft = cellOf(cols.ten);
        if (tenLeft && !tenLeft.isEmpty?.()) clearCell(tenLeft);
      }
      const tenCell = cellOf(cols.ten);
      if (tenCell && !tenCell.isEmpty?.() && isCodeText(cellText(tenCell))) {
        // Ô tên đang hiện một dãy số (mã ngành, kể cả cổng tự đổ mà không nạp được chữ tên) → xoá, để cán bộ chọn tên.
        clearCell(tenCell);
        notes.push("ten:code-shown");
        ok = false;
      }
      const chiTietCell = cellOf(cols.chiTiet);
      ok = (await setCell("chiTiet", want.chiTiet)) && ok;
      if (want.chiTiet && chiTietCell) {
        await sleep(300);
        if (chiTietCell.isEmpty?.()) ok = (await setCell("chiTiet", want.chiTiet)) && ok;
      }
      if (want.chinh) ok = (await setCell("chinh", true)) && ok;
      if (cols.ma && !want.ma) { notes.push("ma:missing"); ok = false; }
      if (!ok) failed.push(`${i + 1}(${notes.join(",")})`);
    }
    if (!failed.length) return { ok: true };
    return { ok: false, reason: `matrix-rows:${failed.join(";")}`, ...(missingCodes.length ? { missingCodes } : {}) };
  }

  // Chữ đang hiện trên một ô của bảng (mục đã chọn → chữ của mục; chưa nạp được mục → giá trị thô).
  function cellText(cq) {
    const item = cq?.selectedItem;
    return String(item?.text ?? item?.calculatedText ?? cq?.displayValue ?? cq?.value ?? "").trim();
  }

  // Chữ chỉ là một dãy số (mã ngành) — không phải tên ngành.
  const isCodeText = (text) => /^\d{2,}$/.test(String(text ?? "").replace(/[\s.]/g, ""));

  // Chữ gõ tìm ở cột tên: cả tên, rồi hai chữ đầu (cổng ghi tên theo danh mục cũ có thể khác chữ BE).
  function nameQueries(name) {
    const full = String(name ?? "").trim();
    const short = full.split(/\s+/).slice(0, 2).join(" ");
    return [...new Set([full, short].filter(Boolean))];
  }

  // Ô dropdown trong bảng KHÔNG có data-name (openToLoad không mở được) và danh mục ngành nạp từ API của cổng → mở theo
  // model / inputId, chưa thấy mục cần thì gõ chữ tìm vào ô lọc (danh mục nạp theo trang / theo chữ gõ).
  const CELL_OPENER = ".sd-dropdown, [role='combobox']";

  // strict (cột mã): chỉ nhận đúng mã, không đoán theo chữ — chọn nhầm ngành tệ hơn để trống cho cán bộ chọn.
  // nameOnly (cột tên): chỉ khớp theo chữ tên, bỏ mục có chữ là mã.
  function pickCellChoice(cq, value, code, strict, nameOnly = false) {
    const list = choicesOf(cq);
    if (code && !nameOnly) {
      const wantCode = String(code);
      const byCode = list.find((c) => String(c.value) === wantCode) ||
        list.find((c) => fold(c.text) === wantCode || fold(c.text).startsWith(`${wantCode} `));
      if (byCode || strict) return byCode || null;
    }
    const best = bestChoice(cq, value);
    return best && nameOnly && isCodeText(best.text) ? null : best;
  }

  async function waitCell(found, timeout) {
    const t0 = Date.now();
    while (Date.now() - t0 < timeout) {
      if (found()) return true;
      await sleep(250);
    }
    return found();
  }

  function cellElement(cq) {
    const el = (cq.inputId && document.getElementById(cq.inputId)) || (cq.id && document.getElementById(cq.id));
    if (!el) return null;
    return el.matches(CELL_OPENER) ? el : (el.querySelector(CELL_OPENER) || el.closest(CELL_OPENER) || el);
  }

  function setCellPopup(cq, visible) {
    try {
      const popup = cq.dropdownListModel?.popupModel;
      if (popup && "isVisible" in popup) { popup.isVisible = visible; return true; }
    } catch { /* bản survey-core khác: dùng DOM */ }
    return false;
  }

  async function openCell(cq, found) {
    if (setCellPopup(cq, true) && await waitCell(found, 5000)) return true;
    const el = cellElement(cq);
    if (el) {
      el.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
      el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    }
    return waitCell(found, 5000);
  }

  async function searchCell(cq, text, found) {
    if (!text) return false;
    let typed = false;
    try {
      const model = cq.dropdownListModel;
      if (model && "filterString" in model) { model.filterString = String(text); typed = true; }
    } catch { /* gõ qua DOM */ }
    if (!typed) {
      const input = cellElement(cq)?.querySelector("input");
      if (input) {
        const desc = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), "value");
        if (desc?.set) desc.set.call(input, String(text));
        else input.value = String(text);
        input.dispatchEvent(new Event("input", { bubbles: true }));
        typed = true;
      }
    }
    return typed && waitCell(found, 6000);
  }

  // Xoá chữ đã gõ vào ô lọc của dropdown: chữ đọng lại hiện đè lên ô (vd mã ngành trên ô tên ngành).
  function clearSearch(cq) {
    try {
      const model = cq.dropdownListModel;
      if (model && "filterString" in model) {
        if (model.filterString) model.filterString = "";
        return;
      }
    } catch { /* xoá qua DOM */ }
    const input = cellElement(cq)?.querySelector("input");
    if (!input || !input.value) return;
    const desc = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), "value");
    if (desc?.set) desc.set.call(input, "");
    else input.value = "";
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }

  // nameOnly (cột tên): chỉ gõ tìm và chỉ khớp theo chữ tên — KHÔNG gõ mã vào ô lọc của cột tên.
  async function setCellChoice(cq, value, code, strict, nameOnly = false) {
    const pick = () => pickCellChoice(cq, value, code, strict, nameOnly);
    const found = () => !!pick();
    let ok = found() || await waitCell(found, 1500);
    let opened = false;
    let typed = false;
    if (!ok) { opened = true; ok = await openCell(cq, found); }
    const queries = strict ? [code] : (nameOnly ? nameQueries(value) : [value, code]);
    for (const text of queries) {
      if (ok) break;
      typed = true;
      ok = await searchCell(cq, text, found);
    }
    const choice = pick();
    const count = choicesOf(cq).length;
    if (choice) cq.value = choice.value;
    if (typed) clearSearch(cq);
    if (opened && !setCellPopup(cq, false)) {
      document.activeElement?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    }
    return choice ? { ok: true } : { ok: false, reason: `${count ? "no-match" : "no-choices"}/${count}` };
  }

  // Bảng "Thành viên hộ gia đình" (matrixdynamic của đăng ký thành lập hộ kinh doanh trên Cổng DVC quốc gia, chỉ hiện
  // khi chủ thể là các thành viên hộ gia đình). Tên câu hỏi trên cổng chưa biết → tìm bảng theo tiêu đề cột; cột nào có
  // thì điền cột đó. BE gửi mảng dòng {hoTen, ngaySinh, soDinhDanh, gioiTinh, quocTich, danToc, noiThuongTru,
  // noiOHienTai}; dòng chuHo (chủ hộ) lấy theo các ô chủ hộ trên chính biểu mẫu (field.chuHoFrom: khoá → tên ô, địa chỉ
  // ghép số nhà, xã, tỉnh), ô đó trống mới dùng giá trị BE gửi.
  const MEMBER_COLUMNS = [
    ["hoTen", /ho va ten|ho ten/],
    ["ngaySinh", /ngay sinh|nam sinh/],
    ["soDinhDanh", /dinh danh|can cuoc|cccd/],
    ["gioiTinh", /gioi tinh/],
    ["quocTich", /quoc tich/],
    ["danToc", /dan toc/],
    ["noiThuongTru", /thuong tru/],
    ["noiOHienTai", /noi o|hien tai/],
  ];
  const MEMBER_REQUIRED = ["hoTen", "ngaySinh", "soDinhDanh"];

  function memberColumns(q) {
    const cols = {};
    for (const c of q.columns || []) {
      const text = fold(c.title || c.name);
      const hit = MEMBER_COLUMNS.find(([key, re]) => !cols[key] && re.test(text));
      if (hit) cols[hit[0]] = c;
    }
    return cols;
  }

  function isMemberMatrix(q) {
    if (!["matrixdynamic", "matrixdropdown"].includes(q?.getType?.() || "")) return false;
    const cols = memberColumns(q);
    return !!(cols.hoTen && (cols.soDinhDanh || cols.ngaySinh));
  }

  // Bảng chỉ hiện sau khi chọn chủ thể (field đứng ngay sau radio chủ thể) → chờ ngắn cho trang dựng bảng.
  async function findMemberMatrix(survey, timeout = 3000) {
    const t0 = Date.now();
    for (;;) {
      const hit = (survey.getAllQuestions(false) || []).find((q) => q.isVisible && isMemberMatrix(q));
      if (hit || Date.now() - t0 >= timeout) return hit || null;
      await sleep(250);
    }
  }

  // Chữ đang hiện của một ô ngoài bảng (phần chủ hộ). Ô chọn: chữ của mục đã chọn; danh mục chưa nạp (chỉ có mã) → "".
  function questionText(survey, name) {
    const q = findQuestion(survey, name);
    if (!q || q.isEmpty?.()) return "";
    if (!["dropdown", "radiogroup", "tagbox"].includes(q.getType?.() || "")) return String(q.value ?? "").trim();
    const item = q.selectedItem;
    const text = String(item?.text ?? item?.calculatedText ?? "").trim();
    if (text) return text;
    const shown = String(q.displayValue ?? "").trim();
    return shown && shown !== String(q.value ?? "").trim() ? shown : "";
  }

  function readOwner(survey, from) {
    const out = {};
    for (const [key, names] of Object.entries(from || {})) {
      const parts = (Array.isArray(names) ? names : [names]).map((n) => questionText(survey, n)).filter(Boolean);
      if (parts.length) out[key] = parts.join(", ");
    }
    return out;
  }

  // Ô ngày trong bảng: ô ngày (flatpickr) / mặt nạ ngày của SurveyJS lưu ISO; ô chữ thường ghi dd/mm/yyyy như trên giấy.
  function dateCellValue(cq, value) {
    const text = String(value ?? "").trim();
    const iso = /^\d{4}-\d{2}-\d{2}/.test(text) ? text.slice(0, 10) : toIsoDate(text);
    const type = cq.getType?.() || "text";
    const isoStore = cq.inputType === "date" || type !== "text" ||
      (cq.maskType === "datetime" && !cq.maskSettings?.saveMaskedValue);
    if (isoStore) return iso;
    const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    return m ? `${m[3]}/${m[2]}/${m[1]}` : text;
  }

  async function setMemberCell(cq, key, value) {
    if (cq.isReadOnly) return { ok: !cq.isEmpty?.(), reason: "readonly" };
    const type = cq.getType?.() || "";
    if (["dropdown", "radiogroup", "tagbox"].includes(type)) return setCellChoice(cq, value, undefined, false, true);
    if (["checkbox", "boolean", "file"].includes(type)) return { ok: false, reason: `type-${type}` };
    cq.value = key === "ngaySinh" ? dateCellValue(cq, value) : String(value);
    return { ok: true };
  }

  async function setMemberMatrix(survey, q, rows, from) {
    if (!Array.isArray(rows) || !rows.length) return { ok: false, reason: "no-rows" };
    const cols = memberColumns(q);
    if (!cols.hoTen) return { ok: false, reason: "no-columns" };
    const owner = from ? readOwner(survey, from) : {};
    if ((q.rowCount || 0) !== rows.length) q.rowCount = rows.length;
    await sleep(300);
    const visible = q.visibleRows || [];
    const failed = [];
    for (let i = 0; i < rows.length; i++) {
      const row = visible[i];
      if (!row) { failed.push(`${i + 1}(no-row)`); continue; }
      const given = rows[i] || {};
      const want = given.chuHo ? { ...given, ...owner } : given;
      const notes = [];
      for (const [key, col] of Object.entries(cols)) {
        const value = want[key];
        if (value === undefined || value === null || value === "") {
          if (MEMBER_REQUIRED.includes(key)) notes.push(`${key}:missing`);
          continue;
        }
        const cq = row.getQuestionByColumnName?.(col.name) ||
          (row.cells || []).find((x) => x.column === col)?.question || null;
        if (!cq) { notes.push(`${key}:no-cell`); continue; }
        const r = await setMemberCell(cq, key, value);
        if (!r.ok) notes.push(`${key}:${r.reason}`);
      }
      if (notes.length) failed.push(`${i + 1}(${notes.join(",")})`);
    }
    return failed.length ? { ok: false, reason: `matrix-rows:${failed.join(";")}` } : { ok: true };
  }

  async function setOne(survey, field) {
    // Bảng thành viên hộ gia đình: tên câu hỏi trên cổng chưa biết → không thấy theo tên thì tìm theo tiêu đề cột.
    const q = findQuestion(survey, field.name) ||
      (field.matrix === "members" ? await findMemberMatrix(survey) : null);
    if (!q) return { ok: false, reason: "not-found" };
    // Ô cổng tự đổ (onlyIfEmpty) đã có giá trị thì giữ nguyên, coi như xong — kiểm TRƯỚC ô chỉ đọc: chọn "Bản thân"
    // cổng chép giấy tờ tùy thân / nơi cư trú của tài khoản rồi KHOÁ các ô đó, kiểm sau thì ô đúng giá trị bị tô đỏ.
    if (field.onlyIfEmpty && !q.isEmpty?.()) return { ok: true, kept: true };
    if (q.isReadOnly) return { ok: false, reason: "readonly" };
    // BE trả ô về TRỐNG (giấy không có giá trị): xoá cả giá trị cổng tự đổ, isolated tô đỏ để hỏi người dân.
    if (field.clear) {
      q.clearValue?.();
      if (!q.isEmpty?.()) q.value = undefined;
      return { ok: false, reason: "cleared-by-be" };
    }
    const type = q.getType?.() || "";
    if (field.matrix === "members") {
      return { ...(await setMemberMatrix(survey, q, field.value, field.chuHoFrom)), qName: q.name };
    }
    if (field.comp === "sjs-matrix" || type === "matrixdynamic") return setMatrix(q, field.value);
    if (field.comp === "sjs-boolean" || type === "boolean") {
      q.value = field.value === true || ["true", "1", "co"].includes(fold(field.value));
      return { ok: true };
    }
    if (field.comp === "sjs-dropdown" || field.comp === "sjs-radio" ||
        ["dropdown", "radiogroup", "tagbox"].includes(type)) {
      return setChoice(q, field.value, field.code);
    }
    if (field.comp === "sjs-date" || q.inputType === "date") {
      q.value = field.code || toIsoDate(field.value);
      return { ok: true };
    }
    q.value = q.inputType === "number" ? Number(String(field.value).replace(/\D/g, "")) || field.value : String(field.value);
    return { ok: true };
  }

  // Khối địa chỉ trong nước chỉ hiện sau khi chọn radio và tên ô khác nhau giữa biểu mẫu → dò theo nhãn
  // hiển thị trong CÙNG khối (.sd-panel) với radio. Nhãn so nguyên cụm để "Giới tính" không khớp "tỉnh".
  // `isChanged(q)` (điền đợt 2): ô con nào bị cán bộ sửa sau lượt điền đầu thì không ghi cả cụm.
  async function setArea(survey, field, isChanged = null) {
    const value = field.value || {};
    const radio = field.radio ? findQuestion(survey, field.radio) : null;
    const radioEl = radio && document.querySelector(`[data-name="${CSS.escape(radio.name)}"]`);
    const scope = radioEl?.closest(".sd-panel") || document;
    await sleep(400);
    const candidates = [];
    // Một khối có thể chứa nhiều cụm địa chỉ (khai sinh: Nơi sinh + Quê quán) → chỉ lấy các ô nằm SAU radio
    // này và TRƯỚC radio kế tiếp theo thứ tự DOM.
    let afterRadio = !radioEl;
    for (const node of scope.querySelectorAll("[data-name]")) {
      if (node === radioEl) { afterRadio = true; continue; }
      if (!afterRadio) continue;
      // Câu hỏi trong panel động (vd nơi đăng ký khai sinh của Lý lịch tư pháp) không có ở getQuestionByName.
      const q = survey.getQuestionByName(node.getAttribute("data-name")) ||
        findQuestion(survey, node.getAttribute("data-name"));
      if (radioEl && q?.getType?.() === "radiogroup") break;
      if (!q || q === radio || q.isReadOnly || !q.isVisible) continue;
      const label = fold([...node.querySelectorAll(".sd-title, label.floating-label")]
        .map((l) => l.textContent).join(" ") || q.title);
      candidates.push({ q, label, type: q.getType?.() });
    }
    const pick = (re, type) => candidates.find((c) => c.type === type && re.test(c.label))?.q || null;
    const steps = [
      [pick(/quoc gia/, "dropdown"), value.quocGia || "Việt Nam"],
      [pick(/tinh thanh pho/, "dropdown"), value.tinh],
      [pick(/xa phuong|phuong xa/, "dropdown"), value.xa],
    ];
    if (isChanged) {
      const detailQ = value.diaChi ? pick(/chi tiet|dia chi/, "text") : null;
      const targets = steps.filter(([q, want]) => q && want).map(([q]) => q).concat(detailQ ? [detailQ] : []);
      if (targets.some(isChanged)) return { ok: false, reason: "changed" };
    }
    const results = [];
    for (const [q, want] of steps) {
      if (q && want) results.push({ name: q.name, ...(await setChoice(q, want)) });
    }
    // Nhãn ô chi tiết khác nhau giữa biểu mẫu: "Nơi cư trú địa chỉ chi tiết" (trích lục) / "Địa chỉ" (cải chính).
    const detail = pick(/chi tiet|dia chi/, "text");
    if (detail && value.diaChi) {
      detail.value = String(value.diaChi);
      results.push({ name: detail.name, ok: true });
    }
    if (!results.length) return { ok: false, reason: "not-found" };
    // Trả từng ô con để isolated tô đúng ô thật (tên ô gộp của BE không có trên trang).
    const parts = results.map(({ name, ok }) => ({ name, ok }));
    const failed = results.filter((r) => !r.ok).map((r) => r.reason);
    return failed.length ? { ok: false, reason: failed.join(","), parts } : { ok: true, parts };
  }

  // Ô có cờ `lookup` (vd họ tên + số định danh + ngày sinh người mất ở khai tử) kích hoạt API tra cứu CSDL dân
  // cư của cổng: điền xong nhóm đó thì chờ cổng tra, ô nào cổng vừa tự đổ thì không ghi đè.
  const LOOKUP_WAIT_MS = 2500;

  async function setValues(fields) {
    let survey = findSurvey();
    if (!survey) return { ok: false, error: "no-survey" };
    let res;
    // Cổng dựng lại biểu mẫu GIỮA lượt điền (máy chậm, danh mục tải xong muộn) → giá trị nằm ở model đã bị thay:
    // điền lại một lần trên model mới.
    for (let lan = 0; lan < 2; lan++) {
      res = await setValuesOn(survey, fields);
      const now = findSurvey();
      if (!now || now === survey) return res;
      survey = now;
    }
    return res;
  }

  async function setValuesOn(survey, fields) {
    installRelationGuards(survey);
    installPhoneGuard(survey);
    // Engine tự chọn quan hệ / tự điền khối: bộ giữ khối không chụp, không ghi lại trong lượt này.
    toolWriting = true;
    try {
      return await setValuesCore(survey, fields);
    } finally {
      toolWriting = false;
      rememberFill(survey);
    }
  }

  async function setValuesCore(survey, fields) {
    const before = new Map((survey.getAllQuestions(false) || []).map((q) => [q.name, q.isEmpty?.()]));
    const results = [];
    let lookupDone = false;
    for (const field of fields) {
      if (!lookupDone && !field.lookup && results.some((r) => r.lookup && r.ok)) {
        lookupDone = true;
        await sleep(LOOKUP_WAIT_MS);
      }
      if (lookupDone && field.comp !== "sjs-area" && !field.clear) {
        const q = findQuestion(survey, field.name);
        if (q && before.get(q.name) && !q.isEmpty?.()) {
          results.push({ name: field.name, ok: true, kept: true, reason: "portal-filled" });
          continue;
        }
      }
      try {
        const r = field.comp === "sjs-area" ? await setArea(survey, field) : await setOne(survey, field);
        if (field.lookup) r.lookup = true;
        results.push({ name: field.name, ...r });
        // Đổi quan hệ / radio làm cổng dựng lại hoặc hiện thêm ô phía sau → chờ render.
        if (r.ok && (field.comp === "sjs-dropdown" || field.comp === "sjs-radio")) await sleep(250);
      } catch (e) {
        results.push({ name: field.name, ok: false, reason: String(e?.message || e) });
      }
    }
    return { ok: true, results };
  }

  // ---- Điền đợt 2 ----
  // Sau lượt điền đầu, lớp soát của BE có thể sửa vài ô. Ghi lại RIÊNG các ô đó, và chỉ khi ô còn đúng giá trị
  // engine vừa điền (hoặc vẫn trống): ô đã được sửa tay hay cổng vừa tự đổ thì giữ nguyên. Ảnh model chụp ngay
  // sau lượt điền gần nhất làm mốc so; cổng dựng model mới thì không còn mốc → ghi như thường.
  let lastFill = null;
  function rememberFill(survey) {
    lastFill = { survey, values: snapshotBlock(survey.getAllQuestions(false) || []) };
  }

  const isChoiceField = (field) => field?.comp === "sjs-dropdown" || field?.comp === "sjs-radio";
  const choiceKey = (q) => choicesOf(q).map((c) => String(c.value)).join("|");

  async function patchValues(fields) {
    const survey = findSurvey();
    if (!survey) return { ok: false, error: "no-survey" };
    const known = lastFill?.survey === survey ? lastFill.values : null;
    const all = survey.getAllQuestions(false) || [];
    const before = snapshotBlock(all);
    const written = new Set();
    const results = [];
    toolWriting = true;
    try {
      for (let i = 0; i < fields.length; i++) {
        const field = fields[i];
        // Ô địa chỉ gộp: tên ô của BE không có trên trang, setArea dò các ô con theo nhãn và tự kiểm ô con bị sửa.
        if (field.comp === "sjs-area") {
          try {
            const changed = (q) => !!known && !q.isEmpty?.() && !sameValue(q.value, known.get(q.name));
            const r = await setArea(survey, field, changed);
            for (const part of r.parts || []) if (part.ok) written.add(part.name);
            results.push({ name: field.name, ...r });
          } catch (e) {
            results.push({ name: field.name, ok: false, reason: String(e?.message || e) });
          }
          continue;
        }
        const q = findQuestion(survey, field.name);
        if (!q || !q.isVisible) { results.push({ name: field.name, ok: false, reason: "not-found" }); continue; }
        if (known && !q.isEmpty?.() && !sameValue(q.value, known.get(q.name))) {
          results.push({ name: field.name, ok: false, reason: "changed" });
          continue;
        }
        // Ô chọn kế tiếp có thể lấy danh mục theo ô này (tỉnh → xã): nhớ danh mục cũ để biết lúc cổng nạp xong
        // danh mục mới — chọn ngay trên danh mục cũ là chọn nhầm xã của tỉnh trước.
        const next = isChoiceField(field) && isChoiceField(fields[i + 1]) ? findQuestion(survey, fields[i + 1].name) : null;
        const nextChoices = next ? choiceKey(next) : "";
        const old = cloneValue(q.value);
        try {
          const r = await setOne(survey, field);
          if (r.ok) written.add(q.name);
          results.push({ name: field.name, ...r, lookup: !!field.lookup });
          if (r.ok && isChoiceField(field)) {
            await sleep(300);
            const t0 = Date.now();
            while (next && !sameValue(old, q.value) && choiceKey(next) === nextChoices && Date.now() - t0 < 5000) await sleep(200);
          }
        } catch (e) {
          results.push({ name: field.name, ok: false, reason: String(e?.message || e) });
        }
      }
      // Ô tra cứu dân cư đổi → cổng tra lại; tra không ra thì cổng làm trống các ô nó từng đổ. Ô đang có giá trị
      // trước lượt này mà bị làm trống theo thì ghi lại.
      if (results.some((r) => r.ok && r.lookup)) {
        await sleep(LOOKUP_WAIT_MS);
        const cleared = all.filter((q) => before.has(q.name) && !written.has(q.name) &&
          q.isVisible && !q.isReadOnly && q.isEmpty?.());
        if (cleared.length) await restoreBlock(survey, cleared, before);
      }
    } finally {
      toolWriting = false;
    }
    rememberFill(survey);
    return { ok: true, results };
  }

  // ---- Giữ khối thông tin người được cấp khi đổi ô "Quan hệ…" ----
  // Biểu mẫu trích lục / cải chính khai resetValueIf "{<ô quan hệ>} <> <Bản thân>" cho cả khối người được
  // cấp: mỗi lần ô quan hệ đổi sang lựa chọn khác "Bản thân", SurveyJS xoá trắng khối, kể cả dữ liệu đã
  // điền / sửa tay. Chọn "Bản thân" thì trigger copyvalue chép thông tin người nộp vào khối. Giữ khối bằng
  // cách chụp trước khi đổi rồi ghi lại sau khi cổng xoá:
  //   - đổi giữa các lựa chọn khác "Bản thân" (kể cả từ trống): ghi lại đúng dữ liệu đang có;
  //   - người dùng đổi sang "Bản thân": lưu ảnh khối lúc đó; đổi tiếp sang lựa chọn khác thì ghi lại đúng
  //     ảnh đã lưu (ô trống vẫn trống) — dữ liệu người nộp cổng vừa chép không được giữ lại;
  //   - "Bản thân" do engine tự chọn khi điền: không có ảnh, đổi sang lựa chọn khác thì để cổng xoá.
  // Chỉ áp cho các ô quan hệ khai dưới đây; khai sinh / khai tử giữ nguyên hành vi của cổng.
  const RELATION_GUARD_NAMES = ["citizenQuanhe", "citizenQuanhevsngcaichinhhotich1"];
  const guardedSurveys = new WeakSet();
  let toolWriting = false;
  let restoringBlock = false;
  const baseName = (name) => String(name || "").replace(/__\d+$/, "");
  const cloneValue = (v) => (v === undefined ? v : JSON.parse(JSON.stringify(v)));
  const sameValue = (a, b) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);

  function snapshotBlock(questions) {
    const snap = new Map();
    for (const q of questions) if (!q.isEmpty?.()) snap.set(q.name, cloneValue(q.value));
    return snap;
  }

  // Ghi lại theo thứ tự trên trang: loại / nơi cư trú trước để ô địa chỉ hiện ra; ô chọn chờ cổng chạy
  // chuỗi tỉnh → xã (đổi tỉnh làm cổng xoá xã rồi nạp lại danh mục) nên soát lại vài lượt.
  async function restoreBlock(survey, questions, snap) {
    restoringBlock = true;
    try {
      const targets = questions.filter((q) => snap.has(q.name));
      for (let pass = 0; pass < 3; pass++) {
        let changed = false;
        for (const q of targets) {
          const want = snap.get(q.name);
          if (sameValue(q.value, want)) continue;
          q.value = cloneValue(want);
          changed = true;
          if (["dropdown", "radiogroup"].includes(q.getType?.())) await sleep(300);
        }
        if (!changed && pass > 0) break;
        await sleep(800);
      }
    } finally {
      restoringBlock = false;
    }
  }

  function installRelationGuards(survey) {
    if (guardedSurveys.has(survey)) return;
    guardedSurveys.add(survey);
    const all = survey.getAllQuestions(false) || [];
    for (const relation of all.filter((q) => RELATION_GUARD_NAMES.includes(baseName(q.name)))) {
      const block = all.filter((q) => String(q.resetValueIf || "").includes(`{${relation.name}}`));
      if (!block.length) continue;
      const selfValue = choicesOf(relation).find((c) => fold(c.text) === "ban than")?.value;
      const isSelf = (v) => selfValue !== undefined && v !== undefined && v !== null && String(v) === String(selfValue);
      let beforeSelf = null;   // ảnh khối lúc người dùng đổi sang "Bản thân"
      let pending = null;      // ảnh khối ngay trước lần đổi hiện tại
      survey.onValueChanging.add((_sender, opt) => {
        if (opt.name !== relation.name || restoringBlock) return;
        if (toolWriting) { pending = null; return; }
        pending = { from: opt.oldValue, snap: snapshotBlock(block) };
        if (isSelf(opt.value) && !isSelf(opt.oldValue)) beforeSelf = pending.snap;
      });
      survey.onValueChanged.add((_sender, opt) => {
        if (opt.name !== relation.name || restoringBlock || toolWriting) return;
        const change = pending;
        pending = null;
        if (!change || isSelf(opt.value)) return;
        let snap = change.snap;
        if (isSelf(change.from)) {
          snap = beforeSelf;
          beforeSelf = null;
          if (!snap) return;   // "Bản thân" do engine chọn: để cổng xoá như bình thường
        }
        // Chạy sau các xử lý đồng bộ của cổng cho cùng lần đổi (resetValueIf, trigger).
        setTimeout(() => { void restoreBlock(survey, block, snap); }, 0);
      });
    }
  }

  // ---- Giữ khối người nộp khi đổi SĐT ----
  // Cổng nghe mọi lần đổi ô SĐT người nộp và gọi API tra công dân (get-citizen-by-code); API trả lỗi thì cổng ghi rỗng
  // giấy tờ, số, ngày cấp, nơi cấp, nơi cư trú của người nộp — cả khi gõ tay lẫn khi engine điền. Chụp khối ngay trước
  // khi SĐT đổi; trong vài giây sau (chờ API về), ô nào cổng làm trống thì ghi lại đúng giá trị đã chụp, ô cổng đổ giá
  // trị mới thì giữ nguyên.
  const PHONE_GUARD_NAME = "citizenPhone";
  const PHONE_CLEAR_WINDOW_MS = 8000;
  // Tên cờ theo sự kiện riêng của từng extension: cài cả hai extension thì mỗi bên giữ bộ của mình.
  const PHONE_GUARD_FLAG = `${REQUEST_EVENT}PHONE_GUARD`;

  async function restoreClearedByPortal(survey, block, snap) {
    const cleared = () => block.filter((q) => snap.has(q.name) && q.isEmpty?.());
    const t0 = Date.now();
    while (Date.now() - t0 < PHONE_CLEAR_WINDOW_MS && !cleared().length) await sleep(200);
    if (!cleared().length) return;
    // Cổng xoá liền một loạt ô → chờ hết loạt rồi mới ghi lại.
    await sleep(400);
    await restoreBlock(survey, block, new Map(cleared().map((q) => [q.name, snap.get(q.name)])));
  }

  function installPhoneGuard(survey) {
    if (!survey || survey[PHONE_GUARD_FLAG]) return;
    const phone = (survey.getAllQuestions(false) || []).find((q) => baseName(q.name) === PHONE_GUARD_NAME);
    const panel = phone?.parent;
    if (!panel?.isPanel) return;
    survey[PHONE_GUARD_FLAG] = true;
    const block = (panel.questions || []).filter((q) => q !== phone);
    let snap = null;
    survey.onValueChanging.add((_sender, opt) => {
      if (opt.name === phone.name && !restoringBlock) snap = snapshotBlock(block);
    });
    survey.onValueChanged.add((_sender, opt) => {
      if (opt.name !== phone.name || restoringBlock || !snap?.size) return;
      const taken = snap;
      snap = null;
      void restoreClearedByPortal(survey, block, taken);
    });
  }

  // Cán bộ gõ tay SĐT trước / ngoài lượt điền → cài bộ giữ ngay khi biểu mẫu có ô SĐT người nộp.
  clearInterval(window[`${PHONE_GUARD_FLAG}_TIMER`]);
  window[`${PHONE_GUARD_FLAG}_TIMER`] = setInterval(() => {
    const node = document.querySelector(`[data-name^="${PHONE_GUARD_NAME}"]`);
    const fiber = node && fiberOf(node);
    installPhoneGuard(fiber && surveyFromFiber(fiber));
  }, 1500);

  // ---- Chặn hộp thoại chọn tệp của OS ----
  let suppressPicker = false;
  const nativeClick = HTMLInputElement.prototype.click;
  const nativeShowPicker = HTMLInputElement.prototype.showPicker;
  function interceptFileInput(input) {
    if (!suppressPicker || input?.type !== "file") return false;
    document.querySelectorAll("input[data-tlnd-picker]").forEach((el) => el.removeAttribute("data-tlnd-picker"));
    input.setAttribute("data-tlnd-picker", "1");
    return true;
  }
  if (!window.__TLND_SJS_PICKER_PATCHED__) {
    window.__TLND_SJS_PICKER_PATCHED__ = true;
    HTMLInputElement.prototype.click = function (...args) {
      if (interceptFileInput(this)) return undefined;
      return nativeClick.apply(this, args);
    };
    if (typeof nativeShowPicker === "function") {
      HTMLInputElement.prototype.showPicker = function (...args) {
        if (interceptFileInput(this)) return undefined;
        return nativeShowPicker.apply(this, args);
      };
    }
    // Cổng tự phát sự kiện click lên input (dispatchEvent) cũng mở hộp chọn tệp → chặn ngay pha capture.
    window.addEventListener("click", (event) => {
      if (interceptFileInput(event.target)) event.preventDefault();
    }, true);
  }

  // Tìm câu hỏi theo nhãn hiển thị: tiêu đề model, hoặc nhãn nổi chỉ có trong DOM (vd "Tại" không có
  // tiêu đề trong model — aria-label là tên ô).
  function questionByLabel(survey, want) {
    const byTitle = (survey.getAllQuestions(true) || []).find((q) => fold(q.title) === want);
    if (byTitle) return byTitle;
    for (const node of document.querySelectorAll("[data-name]")) {
      const labels = node.querySelectorAll(".sd-title, label.floating-label");
      if (![...labels].some((label) => fold(label.textContent) === want)) continue;
      const q = survey.getQuestionByName(node.getAttribute("data-name"));
      if (q) return q;
    }
    return null;
  }

  // "Kính gửi" / "Tại" có mặt ở mọi biểu mẫu mới nhưng tên câu hỏi khác nhau giữa thủ tục → tìm theo
  // nhãn; chỉ ghi khi ô còn trống để không đè giá trị cán bộ đã chọn.
  async function fillPlace(place) {
    const survey = findSurvey();
    if (!survey) return { ok: false, error: "no-survey" };
    const writable = (q) => q && !q.isReadOnly && q.isEmpty?.();
    const results = [];
    const kinhGui = questionByLabel(survey, "kinh gui");
    if (writable(kinhGui) && place.kinhGui) {
      kinhGui.value = place.kinhGui;
      results.push({ name: kinhGui.name, ok: true });
    }
    const tai = questionByLabel(survey, "tai");
    if (writable(tai) && place.tai) results.push({ name: tai.name, ...(await setChoice(tai, place.tai)) });
    return { ok: true, results };
  }

  // Khối người nộp/người yêu cầu của tờ khai (họ tên cổng đổ từ tài khoản; SĐT, nơi cư trú do trợ lý/công dân
  // điền) → làm thông tin người nhận kết quả qua bưu điện. Tên ô địa chỉ khác nhau giữa biểu mẫu → dò theo nhãn
  // trong CÙNG khối với ô họ tên, dừng ở ô đầu tiên của người khác (NDK/Ngdc = người được đăng ký/được cấp…).
  const OTHER_PERSON = /NDK|Ngdc/i;
  function shownText(q) {
    if (!q || q.isEmpty?.()) return "";
    const item = q.selectedItem;
    return String(item?.text ?? item?.calculatedText ?? q.displayValue ?? q.value ?? "").trim();
  }

  function requesterInfo() {
    const survey = findSurvey();
    if (!survey) return { ok: false, error: "no-survey" };
    const nameQ = findQuestion(survey, "citizenName");
    const info = { name: shownText(nameQ), phone: shownText(findQuestion(survey, "citizenPhone")),
      tinh: "", xa: "", diaChi: "" };
    const anchor = nameQ && document.querySelector(`[data-name="${CSS.escape(nameQ.name)}"]`);
    const scope = anchor?.closest(".sd-panel") || anchor?.closest(".sd-page");
    let started = false;
    for (const node of scope ? scope.querySelectorAll("[data-name]") : []) {
      const dn = node.getAttribute("data-name") || "";
      if (node === anchor) { started = true; continue; }
      if (!started) continue;
      if (OTHER_PERSON.test(dn)) break;
      const q = survey.getQuestionByName(dn);
      if (!q || !q.isVisible) continue;
      const label = fold([...node.querySelectorAll(".sd-title, label.floating-label")]
        .map((l) => l.textContent).join(" ") || q.title);
      const type = q.getType?.();
      if (type === "dropdown" && !info.tinh && /tinh thanh pho/.test(label)) info.tinh = shownText(q);
      else if (type === "dropdown" && !info.xa && /xa phuong|phuong xa/.test(label)) info.xa = shownText(q);
      else if (type === "text" && !info.phone && /dien thoai/.test(label)) info.phone = shownText(q);
      else if (type === "text" && !info.diaChi && /chi tiet|dia chi/.test(label) && !/email|thu dien tu/.test(label)) {
        info.diaChi = shownText(q);
      }
    }
    return { ok: true, ...info };
  }

  // Ô bắt buộc còn trống sau khi điền (kể cả ô BE không gửi, vd quan hệ chưa xác định) → tô đỏ.
  // Cổng có ô bắt buộc chỉ đánh dấu bằng "*" trong nhãn (isRequired = false, kiểm tra ở validator riêng của
  // cổng), vd "Quan hệ với người được khai tử *" → xét cả nhãn hiển thị.
  function labelMarksRequired(q) {
    const node = document.querySelector(`[data-name="${CSS.escape(q.name)}"]`);
    if (!node) return false;
    if (node.querySelector('[aria-required="true"]')) return true;
    return [...node.querySelectorAll(".sd-title, label.floating-label")]
      .some((label) => /\*\s*$/.test(String(label.textContent || "").trim()));
  }

  // Nhãn hiển thị (bỏ dấu "*") để trợ lý đọc cho công dân biết ô nào còn thiếu trước khi nộp.
  function questionLabel(q) {
    const node = document.querySelector(`[data-name="${CSS.escape(q.name)}"]`);
    const shown = node && [...node.querySelectorAll(".sd-title, label.floating-label")]
      .map((label) => String(label.textContent || "").replace(/\s+/g, " ").trim()).find(Boolean);
    return String(shown || q.title || q.name).replace(/\s*\*\s*$/, "").trim();
  }

  function emptyRequired() {
    const survey = findSurvey();
    if (!survey) return { ok: false, error: "no-survey" };
    const questions = (survey.getAllQuestions(true) || [])
      .filter((q) => !q.isReadOnly && q.isEmpty?.() && (q.isRequired || labelMarksRequired(q)));
    return {
      ok: true,
      names: questions.map((q) => q.name),
      labels: questions.map((q) => questionLabel(q)),
    };
  }

  // ---- Bổ sung ô còn trống sau khi điền (content/field-review-surveyjs.js) ----
  // Chỉ các câu ĐANG HIỆN trên trang, theo thứ tự DOM: model khai cả câu ẩn (visible:false, có câu vẫn isRequired
  // như citizenTinhtranghonnhanmap*), và tiêu đề trong model thường chỉ là tên câu — nhãn thật nằm trên trang.
  const REVIEW_KINDS = { dropdown: "select", radiogroup: "radio", text: "text", comment: "text" };
  const shownQuestionEl = (q) => Array.from(document.querySelectorAll(`[data-name="${CSS.escape(q.name)}"]`))
    .find((el) => el.getClientRects().length > 0) || null;

  function reviewKind(q) {
    const type = q.getType?.() || "";
    if (type === "text" && q.inputType === "date") return "date";
    return REVIEW_KINDS[type] || "";
  }

  function reviewValue(q, kind) {
    if (q.isEmpty?.()) return "";
    if (kind === "select" || kind === "radio") return shownText(q);
    if (kind === "date") {
      const m = String(q.value || "").match(/^(\d{4})-(\d{2})-(\d{2})/);
      return m ? `${m[3]}/${m[2]}/${m[1]}` : String(q.value || "");
    }
    return String(q.value ?? "").trim();
  }

  // Tiêu đề khối gần nhất có chữ — khối điều kiện (vd "đã ly hôn") không có tiêu đề → lấy khối bọc ngoài.
  function sectionTitle(node) {
    for (let panel = node.closest(".sd-panel"); panel; panel = panel.parentElement?.closest(".sd-panel")) {
      const title = Array.from(panel.querySelectorAll(".sd-panel__title")).find((t) => t.closest(".sd-panel") === panel);
      const text = String(title?.textContent || "").replace(/\s+/g, " ").trim();
      if (text) return text;
    }
    return "";
  }

  function reviewList() {
    const survey = findSurvey();
    if (!survey) return { ok: false, error: "no-survey" };
    const questions = [];
    const seen = new Set();
    for (const node of document.querySelectorAll(".sd-question[data-name]")) {
      if (!node.getClientRects().length) continue;
      const q = survey.getQuestionByName(node.getAttribute("data-name"));
      if (!q || seen.has(q.name) || !q.isVisible || q.isReadOnly) continue;
      const kind = reviewKind(q);
      if (!kind) continue;
      seen.add(q.name);
      questions.push({
        name: q.name, kind,
        // "Số lượng bản sao * (điền 0 nếu không cần)": dấu "*" có thể nằm giữa nhãn.
        label: questionLabel(q).replace(/\s*\*\s*/g, " ").trim(),
        required: !!q.isRequired || labelMarksRequired(q),
        value: reviewValue(q, kind),
        section: sectionTitle(node),
        options: kind === "radio" ? choicesOf(q).map((c) => c.text.trim()) : [],
      });
    }
    return { ok: true, questions };
  }

  // Ô Xã/Phường: ô Tỉnh/Thành phố đứng trước nó trong cùng khối.
  function provinceBefore(survey, q) {
    const node = shownQuestionEl(q);
    if (!node || !/xa phuong|phuong xa/.test(fold(questionLabel(q)))) return null;
    let found = null;
    for (const el of (node.closest(".sd-panel") || document).querySelectorAll(".sd-question[data-name]")) {
      if (el === node) break;
      const p = survey.getQuestionByName(el.getAttribute("data-name"));
      if (p?.getType?.() === "dropdown" && p.isVisible && /tinh thanh pho/.test(fold(questionLabel(p)))) found = p;
    }
    return found;
  }

  // Cổng hay hỏng nạp danh sách Xã sau khi chọn Tỉnh: bấm "Làm mới" cạnh ô; vẫn rỗng thì chọn lại tỉnh cho cổng
  // nạp lại danh sách (gán lại đúng giá trị cũ thì model không đổi nên phải xoá rồi gán).
  async function reloadChoices(survey, q) {
    const refresh = shownQuestionEl(q)?.querySelector('button[title="Làm mới"]');
    if (refresh) {
      refresh.click();
      if (await waitChoices(q, 3000)) return;
    }
    const province = provinceBefore(survey, q);
    if (!province || province.isEmpty?.()) return;
    const value = province.value;
    province.value = undefined;
    await sleep(300);
    province.value = value;
    if (!(await waitChoices(q, 3000))) await openToLoad(q);
  }

  async function reviewChoices(name) {
    const survey = findSurvey();
    const q = survey?.getQuestionByName(name);
    if (!q) return { ok: false, error: "not-found" };
    const texts = () => [...new Set(choicesOf(q).map((c) => c.text.trim()).filter(Boolean))].slice(0, 400);
    if (!(await waitChoices(q, 1500))) await openToLoad(q);
    if (!texts().length) await reloadChoices(survey, q);
    const options = texts();
    const province = options.length ? null : provinceBefore(survey, q);
    return { ok: true, options, province: province ? shownText(province) : "" };
  }

  async function reviewSet(name, kind, value) {
    const comp = { select: "sjs-dropdown", radio: "sjs-radio", date: "sjs-date" }[kind] || "sjs-text";
    const res = await setValues([{ name, comp, value }]);
    return res.ok ? (res.results?.[0] || { ok: false, reason: "not-found" }) : res;
  }

  // ---- Trạng thái tải lên của tệp đính kèm ----
  // Cổng hiện tên tệp lên dòng ngay khi bắt đầu tải và GIỮ dòng đó khi tải hỏng (biểu tượng đỏ — vd tường lửa của
  // cổng chặn tệp gần 2 MB) → tên tệp không đủ làm bằng chứng. Trạng thái thật nằm ở props React `fileInfo` của
  // dòng tệp: uploadStatus pending/uploading/success/error; tệp có sẵn của hồ sơ không có uploadStatus.
  const DELETE_FILE_BUTTON = 'button[title="Xóa file"]';

  // React giữ HAI bản fiber (current / alternate) và phần tử DOM chỉ trỏ cố định MỘT bản → đọc props qua đó có thể ra
  // bản CŨ (tệp đã tải xong vẫn đọc ra "uploading" khi không còn lượt vẽ lại nào). Trạng thái tải chỉ đi tới
  // (pending → uploading → success/error) → lấy bản đi xa hơn, chỉ trong các bản cùng tên với tên đang hiện trên dòng.
  const UPLOAD_RANK = { pending: 0, uploading: 1 };
  function latestFileInfo(button) {
    const nameOf = (x) => String(x?.file?.name || x?.fileName || "");
    const score = (x) => (UPLOAD_RANK[x.uploadStatus] ?? 2) * 2 + (x.fileId || x.id ? 1 : 0);
    for (let f = fiberOf(button), i = 0; f && i < 10; f = f.return, i++) {
      const own = f.memoizedProps?.fileInfo;
      if (!own) continue;
      const shown = String(button.closest("div.justify-between")?.querySelector(".truncate")?.textContent || "").trim();
      const candidates = [own, f.alternate?.memoizedProps?.fileInfo]
        .filter((x) => x && (!shown || nameOf(x) === shown));
      return { info: candidates.sort((a, b) => score(b) - score(a))[0] || own, level: i };
    }
    return null;
  }

  function uploadEntries(name) {
    const out = [];
    for (const button of document.querySelectorAll(DELETE_FILE_BUTTON)) {
      if (!button.offsetParent) continue; // bảng vẽ hai lần, bản cho điện thoại đang ẩn
      const info = latestFileInfo(button)?.info;
      if (!info) continue;
      const fileName = String(info.file?.name || info.fileName || "");
      if (!name || fileName === name) {
        out.push({ name: fileName, status: String(info.uploadStatus || "success"), button });
      }
    }
    return out;
  }

  // Xoá các dòng tệp theo trạng thái (tải hỏng "error", kẹt "pending"/"uploading" — cổng ghi kết quả tải vào sai
  // dòng khi tải chồng), theo tên hoặc mọi tệp: bấm "Xóa file" rồi xác nhận "Xóa" ở hộp thoại cổng.
  async function removeUploads(name, statuses) {
    const match = (e) => statuses.includes(e.status);
    let removed = 0;
    for (let round = 0; round < 20; round++) {
      const failed = uploadEntries(name).find(match);
      if (!failed) break;
      failed.button.click();
      let confirm = null;
      for (let w = 0; w < 20 && !confirm; w++) {
        await sleep(100);
        confirm = [...document.querySelectorAll('[role="dialog"] button, .modal button, button')]
          .find((b) => b.offsetParent && String(b.textContent || "").trim() === "Xóa");
      }
      if (!confirm) break;
      const before = uploadEntries(name).filter(match).length;
      confirm.click();
      for (let w = 0; w < 20; w++) {
        await sleep(100);
        if (uploadEntries(name).filter(match).length < before) break;
      }
      removed++;
    }
    return { ok: true, removed };
  }

  // Vòng bổ sung ô (luồng bản 2): mỗi lần một giá trị của form đổi (công dân gõ thẳng, trợ lý điền) báo cho
  // content/field-review-surveyjs.js đếm lại ô và tô lại màu. Model có thể dựng lại khi React vẽ lại → gắn theo
  // từng model.
  const CHANGED_EVENT = "__TLND_SJS_CHANGED__";
  const watchedSurveys = new WeakSet();
  function reviewWatch() {
    const survey = findSurvey();
    if (!survey) return { ok: false, error: "no-survey" };
    if (!watchedSurveys.has(survey)) {
      watchedSurveys.add(survey);
      survey.onValueChanged.add(() => document.dispatchEvent(new CustomEvent(CHANGED_EVENT)));
    }
    return { ok: true };
  }

  async function handleRequest(event) {
    let requestId = "";
    let result;
    try {
      const payload = JSON.parse(String(event.detail || "{}"));
      requestId = String(payload.requestId || "");
      if (payload.op === "setValues") result = await setValues(Array.isArray(payload.fields) ? payload.fields : []);
      else if (payload.op === "patchValues") result = await patchValues(Array.isArray(payload.fields) ? payload.fields : []);
      else if (payload.op === "fillPlace") result = await fillPlace(payload.place || {});
      else if (payload.op === "emptyRequired") result = emptyRequired();
      else if (payload.op === "requesterInfo") result = requesterInfo();
      else if (payload.op === "reviewList") result = reviewList();
      else if (payload.op === "reviewChoices") result = await reviewChoices(String(payload.name || ""));
      else if (payload.op === "reviewWatch") result = reviewWatch();
      else if (payload.op === "reviewSet") {
        result = await reviewSet(String(payload.name || ""), String(payload.kind || ""), String(payload.value ?? ""));
      }
      else if (payload.op === "uploadStatus") {
        result = { ok: true, statuses: uploadEntries(String(payload.name || "")).map((e) => e.status) };
      } else if (payload.op === "removeUploads") {
        const statuses = Array.isArray(payload.statuses) ? payload.statuses.map(String) : ["error"];
        result = await removeUploads(String(payload.name || ""), statuses);
      }
      else if (payload.op === "suppressPicker") { suppressPicker = !!payload.on; result = { ok: true }; }
      else if (payload.op === "ping") result = { ok: !!findSurvey() };
      else result = { ok: false, error: "unknown-op" };
    } catch (e) {
      result = { ok: false, error: String(e?.message || e) };
    }
    document.dispatchEvent(new CustomEvent(RESULT_EVENT, { detail: JSON.stringify({ requestId, ...result }) }));
  }

  window.__TLND_SJS_HANDLER__ = handleRequest;
  document.addEventListener(REQUEST_EVENT, handleRequest);
})();
