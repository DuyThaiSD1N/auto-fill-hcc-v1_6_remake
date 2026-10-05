// Chạy trong MAIN world để điền tờ khai SurveyJS của Cổng DVC quốc gia bản mới (dichvucong.gov.vn/nop-ho-so).
// Isolated content script không đọc được model SurveyJS (nằm trong React fiber của trang), còn gõ phím trên DOM
// thì không kích hoạt được visibleIf / trigger copyvalue / API tra cứu dân cư của cổng. Ở đây ghi thẳng
// `question.value` vào model nên cổng tự hiện ô phụ thuộc và tự chạy logic của nó.
//
// Hợp đồng field (backend app/pipelines/khai_tu_dvcqg/process/schema.py): {name, comp, value, code?, default?}
// - name: tên câu hỏi KHÔNG kèm đuôi "__<mã mẫu>" → khớp q.name === name hoặc bắt đầu bằng name + "__".
// - code: giá trị lưu trong model khi biết chắc (choice value tĩnh, ngày ISO); không có thì khớp theo nhãn.
// - comp: sv-text | sv-number | sv-date | sv-dropdown | sv-radio | sv-diachi.
(() => {
  const REQUEST_EVENT = "__HCC_SURVEY_FILL_REQUEST__";
  const RESULT_EVENT = "__HCC_SURVEY_FILL_RESULT__";
  const READY_ATTR = "data-hcc-survey-ready";
  // Ba ô kích hoạt API get-citizen-by-code của cổng: điền xong phải chờ cổng tra CSDL dân cư rồi mới điền
  // tiếp, ô nào cổng đã đổ dữ liệu thì không ghi đè.
  const LOOKUP_FIELDS = new Set(["citizenNDK_HoVaTen", "citizenNDK_SoDinhDanh", "citizenNDK_NgaySinh"]);
  const LOOKUP_WAIT_MS = 2500;
  const CHOICES_WAIT_MS = 6000;

  if (window.__HCC_SURVEY_FILL_HANDLER__) {
    document.removeEventListener(REQUEST_EVENT, window.__HCC_SURVEY_FILL_HANDLER__);
  }

  // Đính kèm (content.js attachDvcqgByPlan) bấm hộ nút "Tải lên file" để cổng ghi nhớ dòng đang chọn; nút đó
  // gọi input.click() mở hộp chọn tệp. Có user activation (cán bộ vừa bấm trong panel) thì hộp thoại bật thật
  // → nuốt input[type=file].click()/showPicker() khi <html data-hcc-suppress-picker="1">. Phải patch ở MAIN
  // world vì lệnh click do code React của trang gọi.
  const SUPPRESS_PICKER_ATTR = "data-hcc-suppress-picker";
  if (!window.__HCC_FILE_PICKER_GUARD__) {
    window.__HCC_FILE_PICKER_GUARD__ = true;
    const suppressed = (input) => input?.type === "file"
      && document.documentElement?.getAttribute(SUPPRESS_PICKER_ATTR) === "1";
    const nativeClick = HTMLInputElement.prototype.click;
    HTMLInputElement.prototype.click = function click(...args) {
      if (suppressed(this)) return undefined;
      return nativeClick.apply(this, args);
    };
    const nativeShowPicker = HTMLInputElement.prototype.showPicker;
    if (typeof nativeShowPicker === "function") {
      HTMLInputElement.prototype.showPicker = function showPicker(...args) {
        if (suppressed(this)) return undefined;
        return nativeShowPicker.apply(this, args);
      };
    }
    // Cổng tự phát sự kiện click lên input (dispatchEvent) cũng mở hộp chọn tệp → chặn hành vi mặc định
    // ngay pha capture.
    window.addEventListener("click", (event) => {
      if (suppressed(event.target)) event.preventDefault();
    }, true);
  }

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  async function waitFor(fn, timeout, interval = 100) {
    const started = Date.now();
    while (Date.now() - started < timeout) {
      const result = fn();
      if (result) return result;
      await sleep(interval);
    }
    return fn();
  }

  function fold(value) {
    return String(value ?? "")
      .replace(/Đ/g, "D").replace(/đ/g, "d")
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  }

  // Bỏ tiền tố đơn vị hành chính để "Tỉnh Nghệ An" khớp "Nghệ An" và ngược lại.
  function foldPlace(value) {
    return fold(value).replace(/^(tinh|thanh pho|tp|xa|phuong|thi tran|dac khu)\s+/, "");
  }

  function isSurvey(obj) {
    return !!obj && typeof obj.getQuestionByName === "function" && typeof obj.getAllQuestions === "function";
  }

  // Model SurveyJS nằm trong props của component React: leo fiber từ một câu hỏi lên tới khi gặp model.
  function findSurvey() {
    const nodes = document.querySelectorAll(".sd-root-modern, .sd-question[data-name]");
    for (const node of Array.from(nodes).slice(0, 20)) {
      const key = Object.keys(node).find((k) => k.startsWith("__reactFiber$") || k.startsWith("__reactInternalInstance$"));
      let fiber = key ? node[key] : null;
      for (let depth = 0; fiber && depth < 80; depth++, fiber = fiber.return) {
        const props = fiber.memoizedProps || {};
        for (const candidate of [props.model, props.survey, props.question?.survey, props.element?.survey,
          props.creator?.survey, fiber.stateNode?.survey]) {
          if (isSurvey(candidate)) return candidate;
        }
      }
    }
    return null;
  }

  function findQuestion(survey, name) {
    const all = survey.getAllQuestions(false);
    return all.find((q) => q.name === name) || all.find((q) => String(q.name).startsWith(`${name}__`)) || null;
  }

  function questionElement(q) {
    try {
      return document.querySelector(`.sd-question[data-name="${CSS.escape(q.name)}"]`)
        || document.getElementById(q.id);
    } catch (_) {
      return null;
    }
  }

  // Tô viền bằng một <style> riêng theo [data-name], KHÔNG gắn class: React vẽ lại câu hỏi là ghi đè
  // className, viền mất ngay sau vài ô.
  const MARK_STYLE_ID = "hcc-survey-marks";
  const MARK_COLORS = {
    "autofill-filled": ["#e8f5e9", "#4caf50"],
    "autofill-default": ["#fff8e1", "#f9a825"],
    "autofill-not-filled": ["#ffebee", "#e53935"],
  };
  const marks = new Map();

  function renderMarks() {
    let style = document.getElementById(MARK_STYLE_ID);
    if (!style) {
      style = document.createElement("style");
      style.id = MARK_STYLE_ID;
      (document.head || document.documentElement).appendChild(style);
    }
    style.textContent = Array.from(marks, ([name, cls]) => {
      const [bg, line] = MARK_COLORS[cls];
      return `.sd-question[data-name="${CSS.escape(name)}"] { background-color: ${bg} !important;`
        + ` outline: 2px solid ${line} !important; outline-offset: 1px !important; border-radius: 3px !important; }`;
    }).join("\n");
  }

  function mark(q, cls) {
    marks.set(q.name, cls);
    renderMarks();
  }

  const isEmpty = (value) => value === undefined || value === null || value === "" ||
    (Array.isArray(value) && !value.length);

  // Choice thật (bỏ placeholder "item1" mà mẫu cổng để sẵn cho dropdown nạp từ API).
  function realChoices(q) {
    const list = (q.visibleChoices && q.visibleChoices.length ? q.visibleChoices : q.choices) || [];
    return list.filter((c) => c && String(c.value) !== "item1");
  }

  function matchChoice(q, field) {
    const choices = realChoices(q);
    if (field.code !== undefined && field.code !== null && field.code !== "") {
      const byCode = choices.find((c) => String(c.value) === String(field.code));
      if (byCode) return byCode;
    }
    const want = fold(field.value);
    if (!want) return null;
    const text = (c) => c.text ?? c.title ?? c.value;
    const exact = choices.find((c) => fold(text(c)) === want);
    if (exact) return exact;
    const wantPlace = foldPlace(field.value);
    const place = choices.filter((c) => foldPlace(text(c)) === wantPlace);
    if (place.length === 1) return place[0];
    // Chứa nhau: chỉ nhận khi DUY NHẤT một option khớp, không đoán giữa nhiều option.
    const loose = choices.filter((c) => {
      const t = fold(text(c));
      return t && (t.includes(want) || want.includes(t));
    });
    return loose.length === 1 ? loose[0] : null;
  }

  // Dropdown nạp choices qua API của cổng (tỉnh, xã theo tỉnh): mở dropdown một lần như cán bộ bấm để cổng
  // tự nạp, rồi chờ danh sách về.
  async function ensureChoices(q) {
    if (realChoices(q).length) return true;
    const root = questionElement(q);
    const opener = root?.querySelector(".sd-dropdown, [role='combobox']");
    if (opener) {
      opener.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
      opener.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    }
    const ok = !!(await waitFor(() => realChoices(q).length > 0, CHOICES_WAIT_MS));
    if (opener) {
      document.activeElement?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      document.activeElement?.blur?.();
    }
    return ok;
  }

  async function setChoice(q, field) {
    let choice = matchChoice(q, field);
    if (!choice) {
      await ensureChoices(q);
      choice = matchChoice(q, field);
    }
    if (!choice) return { ok: false, reason: `không có lựa chọn khớp "${field.value}" (${realChoices(q).length} lựa chọn)` };
    q.value = choice.value;
    return { ok: true, label: choice.text ?? String(choice.value) };
  }

  function setScalar(q, field) {
    if (field.comp === "sv-number") {
      const n = Number(field.value);
      if (!Number.isFinite(n)) return { ok: false, reason: "không phải số" };
      q.value = n;
    } else if (field.comp === "sv-date") {
      q.value = field.code || field.value;
    } else {
      q.value = String(field.value);
    }
    return { ok: true };
  }

  // Cụm nơi chết: tên ô con chưa có trong backend → chọn radio rồi điền các ô HIỆN RA ngay sau radio trong
  // cùng panel, nhận vai theo placeholder/tiêu đề.
  async function fillAddressCluster(survey, radio, field) {
    const value = field.value || {};
    const choice = matchChoice(radio, { value: value.luaChon });
    if (!choice) return { ok: false, reason: `không có lựa chọn "${value.luaChon}"` };
    radio.value = choice.value;
    await sleep(400);
    const visible = survey.getAllQuestions(true);
    const start = visible.indexOf(radio);
    const parts = [];
    for (const q of visible.slice(start + 1, start + 12)) {
      if (q.parent !== radio.parent) continue;
      if (q.getType && ["radiogroup", "html"].includes(q.getType())) {
        if (q.getType() === "radiogroup") break;
        continue;
      }
      const label = fold(`${q.placeholder || ""} ${q.title || ""}`);
      const role = label.includes("quoc gia") ? "quocGia"
        : label.includes("tinh") ? "tinh"
          : (label.includes("phuong") || /\bxa\b/.test(label)) ? "xa"
            : label.includes("dia chi") ? "diaChi" : "";
      if (role && value[role] && !parts.some((p) => p.role === role)) parts.push({ role, q });
    }
    const done = [];
    for (const { role, q } of parts) {
      if (q.isReadOnly) continue;
      const sub = { comp: q.getType() === "dropdown" ? "sv-dropdown" : "sv-text", value: value[role] };
      const res = sub.comp === "sv-dropdown" ? await setChoice(q, sub) : setScalar(q, sub);
      mark(q, res.ok ? (field.default ? "autofill-default" : "autofill-filled") : "autofill-not-filled");
      done.push(`${role}:${res.ok ? "ok" : res.reason}`);
      if (role === "tinh") await sleep(300); // xã nạp theo tỉnh
    }
    return { ok: true, label: `${choice.text} (${done.join(", ") || "không có ô con"})` };
  }

  async function fillFields(fields) {
    const survey = await waitFor(findSurvey, 4000);
    if (!survey) return { handled: false, reason: "không tìm thấy model SurveyJS" };
    marks.clear();
    renderMarks();
    // Ảnh chụp giá trị trước khi điền: sau lượt tra cứu dân cư, ô nào cổng vừa tự đổ thì không ghi đè.
    const before = new Map(survey.getAllQuestions(false).map((q) => [q, q.value]));
    const results = [];
    let lookupDone = false;

    for (const field of fields || []) {
      const name = String(field?.name || "");
      if (!name || !String(field.comp || "").startsWith("sv-")) continue;
      if (!lookupDone && !LOOKUP_FIELDS.has(name) && results.some((r) => LOOKUP_FIELDS.has(r.name) && r.ok)) {
        lookupDone = true;
        await sleep(LOOKUP_WAIT_MS);
      }
      const q = findQuestion(survey, name);
      if (!q) {
        results.push({ name, ok: false, reason: "không có câu hỏi trên form" });
        continue;
      }
      if (q.isReadOnly) {
        results.push({ name, ok: false, skipped: true, reason: "cổng khóa ô này" });
        continue;
      }
      if (lookupDone && isEmpty(before.get(q)) && !isEmpty(q.value)) {
        results.push({ name, ok: false, skipped: true, reason: "cổng đã tự điền từ CSDL dân cư" });
        continue;
      }
      let res;
      try {
        if (field.comp === "sv-diachi") res = await fillAddressCluster(survey, q, field);
        else if (field.comp === "sv-dropdown" || field.comp === "sv-radio") res = await setChoice(q, field);
        else res = setScalar(q, field);
      } catch (error) {
        res = { ok: false, reason: String(error?.message || error) };
      }
      if (field.comp !== "sv-diachi") {
        mark(q, res.ok ? (field.default ? "autofill-default" : "autofill-filled") : "autofill-not-filled");
      } else if (res.ok) {
        mark(q, field.default ? "autofill-default" : "autofill-filled");
      }
      results.push({ name, ...res });
      await sleep(field.comp === "sv-radio" || field.comp === "sv-dropdown" ? 250 : 60);
    }
    return { handled: true, results };
  }

  async function handleRequest(event) {
    let requestId = "";
    let result;
    try {
      const payload = JSON.parse(String(event.detail || "{}"));
      requestId = String(payload.requestId || "");
      result = await fillFields(payload.fields);
    } catch (error) {
      result = { handled: false, reason: String(error?.message || error) };
    }
    document.dispatchEvent(new CustomEvent(RESULT_EVENT, {
      detail: JSON.stringify({ requestId, ...result }),
    }));
  }

  window.__HCC_SURVEY_FILL_HANDLER__ = handleRequest;
  document.addEventListener(REQUEST_EVENT, handleRequest);
  const markReady = () => document.documentElement?.setAttribute(READY_ATTR, "1");
  if (document.documentElement) markReady();
  else document.addEventListener("readystatechange", markReady, { once: true });
})();
