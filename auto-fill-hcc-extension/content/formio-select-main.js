// Chạy trong MAIN world để điền ô select Form.io bằng chính API của component. Isolated content script không đọc
// được instance Form.io (__ngContext__ là expando của trang) nên chỉ mô phỏng gõ phím rồi đoán thời gian chờ API;
// với nguồn custom, mỗi lượt gõ còn làm Form.io chạy lại JS nạp danh sách của cổng → danh sách về trang đầu,
// dropdown trống hoặc ô hiện mã id.
// - Nguồn từ xa url/resource: updateItems(từ khoá, force) → chờ comp.loading tắt → chọn trong selectOptions.
// - Nguồn nạp sẵn/custom/values/json: chọn thẳng trong option đã có (selectOptions + kho Choices); thiếu thì nạp
//   thêm đúng đường của cổng (mở dropdown / một lượt từ khoá / cuộn trang).
(() => {
  const REQUEST_EVENT = "__HCC_FORMIO_SELECT_REQUEST__";
  const RESULT_EVENT = "__HCC_FORMIO_SELECT_RESULT__";
  const READY_ATTR = "data-hcc-formio-select-ready";
  const TARGET_ATTR = "data-hcc-formio-select-target";
  const REMOTE_SOURCES = new Set(["url", "resource"]);
  // Danh sách nạp SẴN khi dựng form (custom = JS của cổng tự gọi API, vd cổng Bộ XD). KHÔNG gọi updateItems cho
  // nhóm này: với custom mỗi lần tải lại là chạy lại JS của cổng (nạp jQuery + gọi API bất đồng bộ) → danh sách
  // bị xoá rồi nạp lại, Choices trống và ô hiện mã id — chính là lý do gõ tìm trên DOM trượt.
  const LOADED_SOURCES = new Set(["custom", "values", "json"]);
  // Ô nạp lười (vd panel "Thêm phương tiện" cổng Bộ XD): danh sách chỉ nạp khi mở dropdown lần đầu → mở
  // dropdown MỘT lần qua API Choices (như cán bộ bấm) để cổng tự nạp theo đường của nó. KHÔNG gọi
  // comp.updateItems(…, true) cho custom: ép chạy lại JS của cổng gây bão sự kiện Form.io (>1000 event/300ms),
  // trang khựng.
  const LAZY_WAIT_MS = 4000;
  const SEARCH_WAIT_MS = 3000;
  const PAGE_WAIT_MS = 2000;
  const MAX_PAGES = 10;
  const POLL_MS = 50;
  const LOAD_TIMEOUT_MS = 6000;
  // Không phát yêu cầu mạng (vd chưa đủ minSearch → setItems([]) đồng bộ) thì coi như xong sau quãng này.
  const NO_REQUEST_GRACE_MS = 600;
  const TOTAL_BUDGET_MS = 20000;

  if (window.__HCC_FORMIO_SELECT_HANDLER__) {
    document.removeEventListener(REQUEST_EVENT, window.__HCC_FORMIO_SELECT_HANDLER__);
  }

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  async function waitFor(fn, timeout, interval = 80) {
    const started = Date.now();
    while (Date.now() - started < timeout) {
      const result = fn();
      if (result) return result;
      await sleep(interval);
    }
    return null;
  }

  function fold(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  // Nhãn option Form.io là HTML từ template ("<span>Tỉnh Quảng Trị</span>", có thể có &amp;) → DOMParser
  // (document trơ, không chạy script/tải ảnh) để lấy text.
  function htmlText(value) {
    const text = String(value ?? "");
    if (!/[<&]/.test(text)) return text;
    try {
      return new DOMParser().parseFromString(text, "text/html").body.textContent || "";
    } catch {
      return text.replace(/<[^>]+>/g, "");
    }
  }

  function optionText(option) {
    if (option == null) return "";
    if (typeof option !== "object") return htmlText(option);
    const value = option.value;
    return htmlText(
      option.label || option.name || option.text ||
      (value && typeof value === "object" ? value.label || value.name || value.text || value.ten : "") ||
      (typeof value === "string" ? value : "")
    );
  }

  // Chỉ nhận option BẰNG giá trị hoặc CHỨA trọn cụm giá trị theo ranh giới từ. Không nhận chiều "giá trị chứa
  // option": danh sách chưa có option đúng thì option ngắn nằm lọt trong giá trị dài bị chọn nhầm
  // (vd "Xe taxi" nằm trong "Xe ô tô tải … và xe taxi tải").
  function matchScore(text, want) {
    const t = fold(text);
    const w = fold(want);
    if (!t || !w) return 0;
    if (t === w) return 3;
    if (` ${t} `.includes(` ${w} `)) return 2;
    return 0;
  }

  // Nguồn values lưu MÃ (vd dichVu = "MAU_2.002288.TAXI") → giá trị gửi đúng mã cũng khớp tuyệt đối.
  function optionScore(option, want) {
    const code = option && typeof option === "object" && typeof option.value === "string" ? option.value : "";
    if (code && fold(code) === fold(want)) return 3;
    return matchScore(optionText(option), want);
  }

  // Hoà điểm → option NGẮN hơn (gần giá trị hơn, vd "Hợp tác xã" hơn "Liên hiệp hợp tác xã").
  function bestOption(options, want) {
    let best = null;
    let bestScore = 0;
    let bestLen = Infinity;
    for (const option of options || []) {
      const text = optionText(option);
      const score = optionScore(option, want);
      if (!score) continue;
      const len = fold(text).length;
      if (score > bestScore || (score === bestScore && len < bestLen)) {
        best = option;
        bestScore = score;
        bestLen = len;
      }
    }
    return best;
  }

  // Server tìm theo chuỗi con hay tiền tố thì chưa biết → thử giá trị đầy đủ, cụm đầu ngắn dần, cuối cùng
  // danh sách mặc định (không từ khoá) cho danh mục nhỏ mà server tìm phân biệt hoa/thường hoặc dấu.
  function searchTerms(value) {
    const raw = String(value ?? "").replace(/\s+/g, " ").trim();
    const terms = [raw];
    const words = raw.split(" ");
    if (words.length > 3) terms.push(words.slice(0, 3).join(" "));
    if (words.length > 2) terms.push(words.slice(0, 2).join(" "));
    terms.push("");
    return [...new Set(terms)];
  }

  function formFromNgContext(el) {
    const roots = [];
    for (let node = el; node; node = node.parentElement) {
      const ctx = node.__ngContext__ || node.__ng_context__ || node.ngContext;
      if (ctx) roots.push(ctx);
    }
    const seen = new WeakSet();
    const scan = (obj, depth = 0) => {
      if (!obj || typeof obj !== "object" || seen.has(obj) || depth > 6) return null;
      seen.add(obj);
      if (obj.formio?.everyComponent) return obj.formio;
      let props = [];
      try { props = Object.getOwnPropertyNames(obj).slice(0, 180); } catch { return null; }
      for (const k of props) {
        let value;
        try { value = obj[k]; } catch { continue; }
        const hit = scan(value, depth + 1);
        if (hit) return hit;
      }
      if (Array.isArray(obj)) {
        for (const value of obj.slice(0, 180)) {
          const hit = scan(value, depth + 1);
          if (hit) return hit;
        }
      }
      return null;
    };
    for (const root of roots) {
      const hit = scan(root);
      if (hit) return hit;
    }
    return null;
  }

  function candidateForms(el) {
    const forms = new Set();
    try {
      Object.values(window.Formio?.forms || {}).forEach((form) => { if (form?.everyComponent) forms.add(form); });
    } catch { /* ignore */ }
    const fromCtx = formFromNgContext(el);
    if (fromCtx) forms.add(fromCtx);
    return [...forms];
  }

  // Khớp component theo id của khối bọc (div.formio-component id="e8517np") — duy nhất kể cả trong panel lặp /
  // editgrid, không phụ thuộc key trùng giữa các khối.
  function findComponent(el) {
    const wrapper = el.closest?.(".formio-component[id]");
    if (!wrapper) return null;
    for (const form of candidateForms(el)) {
      let hit = null;
      try {
        form.everyComponent((comp) => {
          if (hit) return;
          if (comp?.id === wrapper.id || comp?.element === wrapper) hit = comp;
        });
      } catch { /* ignore */ }
      if (hit && String(hit.component?.type || hit.type || "").toLowerCase() === "select") return hit;
    }
    return null;
  }

  function displayedLabel(el) {
    const wrapper = el.closest?.(".formio-component") || el.parentElement;
    const item = wrapper?.querySelector?.(".choices__list--single .choices__item:not(.choices__placeholder)");
    return String(item?.textContent || "").replace(/Remove item/gi, "").replace(/\s+/g, " ").trim();
  }

  // dataValue của Form.io có thể là BẢN SAO của object option → so theo nội dung, không so tham chiếu.
  function sameValue(a, b) {
    if (a === b) return true;
    if (!a || !b || typeof a !== "object" || typeof b !== "object") return false;
    try { return JSON.stringify(a) === JSON.stringify(b); } catch { return false; }
  }

  async function loadOptions(comp, term, deadline) {
    const before = comp.selectOptions;
    try {
      comp.updateItems(term, true);
    } catch (error) {
      console.warn("[AutoFill-Formio] updateItems lỗi:", comp.key, error);
      return false;
    }
    let sawLoading = !!comp.loading;
    const started = Date.now();
    const limit = Math.min(LOAD_TIMEOUT_MS, Math.max(0, deadline - started));
    while (Date.now() - started < limit) {
      await sleep(80);
      if (comp.loading) { sawLoading = true; continue; }
      if (comp.selectOptions !== before || sawLoading) return true;
      if (Date.now() - started >= NO_REQUEST_GRACE_MS) return true;
    }
    return false;
  }

  async function applyValue(comp, el, value, label) {
    try {
      comp.setValue(value, { modified: true });
    } catch (error) {
      console.warn("[AutoFill-Formio] setValue lỗi:", comp.key, error);
      return { handled: false, reason: "set-failed" };
    }
    const ok = !!await waitFor(() => sameValue(comp.dataValue, value) || matchScore(displayedLabel(el), label) === 3, 1500);
    return { handled: true, ok, label, reason: ok ? "" : "not-applied" };
  }

  function openDropdown(comp, el) {
    try {
      if (typeof comp.choices?.showDropdown === "function") {
        comp.choices.showDropdown(true);
        return true;
      }
    } catch { /* ignore */ }
    const wrapper = el.closest?.(".formio-component");
    const opener = wrapper?.querySelector?.(".choices__inner, .form-control.ui.selection.dropdown, .choices");
    if (!opener) return false;
    ["mousedown", "mouseup", "click"].forEach((type) =>
      opener.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window })));
    return true;
  }

  function closeDropdown(comp) {
    try { comp.choices?.hideDropdown?.(true); } catch { /* ignore */ }
  }

  // Option cán bộ THẤY trong dropdown. JS custom của cổng (vd Bộ XD: Màu sơn, Loại phương tiện, Loại hình cho
  // thuê, Nước sản xuất) đổ kết quả API thẳng vào Choices (instance.choices.setChoices) chứ không vào
  // comp.selectOptions → phải đọc kho của Choices, không thì luôn thấy 0 option.
  function choicesItems(comp, el) {
    let list = [];
    try { list = comp.choices?._store?.choices || []; } catch { list = []; }
    if (Array.isArray(list) && list.length) {
      return list
        .filter((c) => c && !c.placeholder && c.value !== undefined && c.value !== null && c.value !== "")
        .map((c) => ({ value: c.value, label: htmlText(c.label) }));
    }
    const wrapper = el.closest?.(".formio-component");
    return Array.from(wrapper?.querySelectorAll?.(".choices__list--dropdown .choices__item--choice[data-value]") || [])
      .map((node) => ({ value: node.getAttribute("data-value"), label: String(node.textContent || "").trim() }));
  }

  // selectOptions trước (setValue với đúng object của Form.io); mục chỉ có trong Choices đánh dấu choicesOnly.
  function allOptions(comp, el) {
    const out = Array.isArray(comp.selectOptions) ? [...comp.selectOptions] : [];
    const seen = new Set(out.map((o) => fold(optionText(o))));
    for (const item of choicesItems(comp, el)) {
      const key = fold(item.label);
      if (!key || seen.has(key)) continue;
      seen.add(key);
      out.push({ value: item.value, label: item.label, choicesOnly: true });
    }
    return out;
  }

  // JS custom có gửi từ khoá lên server (vd Nước sản xuất: body.keyword) thì tìm theo từ khoá; không thì chỉ
  // phân trang theo cuộn (gõ vào ô tìm chỉ lọc trong trang đã nạp).
  function supportsKeyword(comp) {
    return /\bkeyword\b/i.test(String(comp.component?.data?.custom || ""));
  }

  // Một lượt gõ = một sự kiện input: JS custom nghe input/search trên ô tìm rồi tự gọi API. Không phát keyup →
  // Choices không phát 'search' → Form.io không chạy lại JS custom (chạy lại là danh sách về trang 0).
  // Phải là Event thường: InputEvent có detail = 0, JS custom đọc `event.detail && event.detail.value` → 0 ≠
  // undefined → lấy 0 làm từ khoá (rỗng) thay vì đọc chữ trong ô.
  function typeKeyword(comp, el, text) {
    const input = comp.choices?.input?.element
      || el.closest?.(".formio-component")?.querySelector?.(".choices__input--cloned");
    if (!input) return false;
    const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), "value")?.set;
    if (setter) setter.call(input, text);
    else input.value = text;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  }

  // JS custom nạp trang kế khi danh sách dropdown cuộn gần đáy.
  function scrollToBottom(comp, el) {
    const lists = new Set();
    const own = comp.choices?.choiceList?.element;
    if (own) lists.add(own);
    el.closest?.(".formio-component")?.querySelectorAll?.(".choices__list--dropdown .choices__list")
      ?.forEach?.((node) => lists.add(node));
    lists.forEach((node) => {
      try { node.scrollTop = node.scrollHeight; } catch { /* ignore */ }
      node.dispatchEvent(new Event("scroll"));
    });
    return lists.size > 0;
  }

  // Nạp thêm option theo đúng đường của cổng, dừng NGAY khi thấy mục cần (không chờ cố định).
  async function loadUntilFound(comp, el, wants, find) {
    const count = () => allOptions(comp, el).length;
    const opened = openDropdown(comp, el);
    try {
      if (!count()) await waitFor(() => count() > 0, LAZY_WAIT_MS, POLL_MS);
      let picks = find();
      if (picks || !count()) return picks;
      if (wants.length === 1 && supportsKeyword(comp) && typeKeyword(comp, el, wants[0])) {
        picks = await waitFor(find, SEARCH_WAIT_MS, POLL_MS);
        if (picks) return picks;
      }
      for (let page = 0; page < MAX_PAGES; page++) {
        const before = count();
        if (!scrollToBottom(comp, el)) break;
        const grew = await waitFor(() => find() || count() > before, PAGE_WAIT_MS, POLL_MS);
        picks = find();
        if (picks || !grew) return picks;
      }
      return null;
    } finally {
      if (opened) closeDropdown(comp);
    }
  }

  // Mục chỉ có trong Choices: chọn như cán bộ bấm — Choices chọn mục rồi phát 'change' trên thẻ select, Form.io
  // tự đọc giá trị từ Choices. Giá trị lưu cùng dạng với chọn tay.
  async function selectViaChoices(comp, el, option) {
    const choices = comp.choices;
    if (typeof choices?.setChoiceByValue !== "function") return { handled: false, reason: "no-choices-api" };
    const label = optionText(option);
    try {
      choices.setChoiceByValue(option.value);
      const input = choices.input?.element;
      if (input) input.value = "";
      (choices.passedElement?.element || el).dispatchEvent(new Event("change", { bubbles: true }));
    } catch (error) {
      console.warn("[AutoFill-Formio] chọn qua Choices lỗi:", comp.key, error);
      return { handled: false, reason: "set-failed" };
    }
    const idOf = (v) => (v && typeof v === "object" ? String(v.value ?? v._id ?? v.id ?? "") : String(v ?? ""));
    const ok = !!await waitFor(() =>
      idOf(comp.dataValue) === String(option.value) || matchScore(displayedLabel(el), label) === 3, 1500);
    return { handled: true, ok, label, reason: ok ? "" : "not-applied" };
  }

  // Danh sách nạp sẵn / nạp bởi JS custom. Select nhiều: giá trị "A|B" (như fillStandardMultiSelect) → THAY toàn
  // bộ mục đang chọn (form hay chọn sẵn mục mặc định sai). Không khớp: custom → để trống (gõ DOM chỉ làm cổng
  // nạp lại); values/json → handled:false để đường DOM cũ xử lý như trước.
  async function fillFromLoadedList(comp, el, want, source) {
    const multiple = !!comp.component?.multiple;
    const wants = multiple ? want.split("|").map((s) => s.trim()).filter(Boolean) : [want];
    if (!multiple) {
      const current = displayedLabel(el);
      if (matchScore(current, want)) return { handled: true, ok: true, label: current, already: true };
    }
    const find = () => {
      const options = allOptions(comp, el);
      if (!options.length) return null;
      const found = wants.map((w) => bestOption(options, w));
      return found.every(Boolean) ? found : null;
    };
    const picks = find() || (source === "custom" ? await loadUntilFound(comp, el, wants, find) : null);
    if (!picks) {
      const count = allOptions(comp, el).length;
      return { handled: source === "custom", ok: false, reason: count ? "no-match" : "empty-list", options: count };
    }
    if (picks.every((o) => !o.choicesOnly)) {
      const value = multiple ? picks.map((o) => o.value) : picks[0].value;
      return applyValue(comp, el, value, picks.map(optionText).join(" | "));
    }
    if (multiple) return { handled: false, reason: "multiple-choices-only" };
    return selectViaChoices(comp, el, picks[0]);
  }

  async function fillSelect(el, value) {
    const want = String(value ?? "").trim();
    if (!want) return { handled: false, reason: "empty-value" };
    const comp = findComponent(el);
    if (!comp) {
      return {
        handled: false,
        reason: "no-component",
        wrapperId: el.closest?.(".formio-component[id]")?.id || "",
        forms: candidateForms(el).length,
      };
    }
    const source = String(comp.component?.dataSrc || "").toLowerCase();
    if (comp.disabled) return { handled: false, reason: "disabled" };
    if (typeof comp.setValue !== "function") return { handled: false, reason: "no-api" };
    if (LOADED_SOURCES.has(source)) return fillFromLoadedList(comp, el, want, source);
    if (!REMOTE_SOURCES.has(source)) return { handled: false, reason: `source:${source || "none"}`, key: comp.key };
    if (comp.component?.multiple) return { handled: false, reason: "multiple" };
    if (typeof comp.updateItems !== "function") return { handled: false, reason: "no-api" };

    const current = displayedLabel(el);
    if (matchScore(current, want)) return { handled: true, ok: true, label: current, already: true };

    const deadline = Date.now() + TOTAL_BUDGET_MS;
    // Chỉ dừng sớm khi khớp CHÍNH XÁC: từ khoá rút gọn có thể chỉ trả option "chứa" giá trị (vd "Liên hiệp
    // hợp tác xã") trong khi option bằng đúng giá trị nằm ở lượt sau.
    let best = null;
    let bestScore = 0;
    let bestTerm = null;
    let listTerm = null;
    let loadedAny = false;
    const consider = () => {
      const option = bestOption(comp.selectOptions, want);
      const score = option ? optionScore(option, want) : 0;
      if (score > bestScore) {
        best = option;
        bestScore = score;
        bestTerm = listTerm;
      }
    };
    consider();
    if (bestScore < 3) {
      for (const term of searchTerms(want)) {
        if (Date.now() >= deadline) break;
        if (!await loadOptions(comp, term, deadline)) continue;
        loadedAny = true;
        listTerm = term;
        consider();
        if (bestScore === 3) break;
      }
    }
    // Option tốt nhất thuộc danh sách đã bị lượt sau thay → nạp lại danh sách đó để option có mặt trong
    // selectOptions lúc setValue (Form.io tra nhãn từ đây; thiếu là ô hiện mã id).
    let option = best;
    if (best && listTerm !== bestTerm) {
      const label = optionText(best);
      if (await loadOptions(comp, bestTerm ?? "", deadline)) {
        option = (comp.selectOptions || []).find((o) => fold(optionText(o)) === fold(label)) || best;
      }
    }
    // Đã tải được danh sách mà không có option khớp → báo handled để bên gọi KHÔNG quay về đường DOM khớp
    // lỏng (thà để trống còn hơn chọn nhầm). Không tải được gì → handled:false để đường DOM thử tiếp.
    if (!option) return { handled: loadedAny, ok: false, reason: loadedAny ? "no-match" : "load-failed" };

    return applyValue(comp, el, option.value, optionText(option));
  }

  async function handleRequest(event) {
    let requestId = "";
    let result;
    try {
      const payload = JSON.parse(String(event.detail || "{}"));
      requestId = String(payload.requestId || "");
      const el = requestId
        ? document.querySelector(`[${TARGET_ATTR}="${CSS.escape(requestId)}"]`)
        : null;
      result = el ? await fillSelect(el, payload.value) : { handled: false, reason: "no-element" };
    } catch (error) {
      result = { handled: false, reason: "error", error: String(error?.message || error) };
    }
    document.dispatchEvent(new CustomEvent(RESULT_EVENT, {
      detail: JSON.stringify({ requestId, ...result }),
    }));
  }

  window.__HCC_FORMIO_SELECT_HANDLER__ = handleRequest;
  document.addEventListener(REQUEST_EVENT, handleRequest);
  const markReady = () => document.documentElement?.setAttribute(READY_ATTR, "1");
  if (document.documentElement) markReady();
  else document.addEventListener("readystatechange", markReady, { once: true });
})();
