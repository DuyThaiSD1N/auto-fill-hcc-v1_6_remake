// Chạy trong MAIN world: biểu mẫu Cổng DVC quốc gia mới (/nop-ho-so) là SurveyJS trong React. Ô
// dropdown/ngày (flatpickr) chỉ nhận giá trị qua MODEL survey — gõ vào DOM không cập nhật model. Isolated
// content script không đọc được fiber React của trang → cầu nối CustomEvent như fill-lamdong-main.js.
// Ngoài ra chặn hộp thoại chọn tệp của OS khi extension bấm nút "Tải lên file" để nạp tệp thẳng vào input.
(() => {
  if (!/(^|\.)dichvucong\.gov\.vn$/.test(location.hostname)) return;

  const REQUEST_EVENT = "__HCC_SJS_REQUEST__";
  const RESULT_EVENT = "__HCC_SJS_RESULT__";
  if (window.__HCC_SJS_HANDLER__) document.removeEventListener(REQUEST_EVENT, window.__HCC_SJS_HANDLER__);

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const fold = (s) => String(s ?? "")
    .replace(/Đ/g, "D").replace(/đ/g, "d")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  // Tiền tố hành chính khác nhau giữa nguồn ("Nghệ An") và option ("Tỉnh Nghệ An").
  const stripAdmin = (s) => fold(s).replace(/^(tinh|thanh pho|tp|xa|phuong|thi tran|dac khu)\s+/, "");

  // ---- Tìm model survey qua fiber React ----
  let cachedSurvey = null;
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

  function findSurvey() {
    if (cachedSurvey && document.querySelector("[data-name]")) return cachedSurvey;
    const nodes = Array.from(document.querySelectorAll(".sd-root-modern, .sv-root-modern, [data-name]")).slice(0, 40);
    for (const node of nodes) {
      const fiber = fiberOf(node);
      const survey = fiber && surveyFromFiber(fiber);
      if (survey) { cachedSurvey = survey; return survey; }
    }
    return null;
  }

  // BE gửi tên gốc (vd "citizenQuanhe"); data-name thật kèm hậu tố "__<số>" đổi theo phiên bản biểu mẫu.
  function findQuestion(survey, name) {
    const all = survey.getAllQuestions(false) || [];
    const matches = all.filter((q) => q.name === name || String(q.name).startsWith(`${name}__`));
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

  async function setOne(survey, field) {
    const q = findQuestion(survey, field.name);
    if (!q) return { ok: false, reason: "not-found" };
    if (q.isReadOnly) return { ok: false, reason: "readonly" };
    // Giá trị mặc định cho ô cổng tự đổ: đã có giá trị thì giữ nguyên, coi như xong.
    if (field.onlyIfEmpty && !q.isEmpty?.()) return { ok: true, kept: true };
    const type = q.getType?.() || "";
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
  async function setArea(survey, field) {
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
      const q = survey.getQuestionByName(node.getAttribute("data-name"));
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
    const survey = findSurvey();
    if (!survey) return { ok: false, error: "no-survey" };
    installRelationGuards(survey);
    // Engine tự chọn quan hệ / tự điền khối: bộ giữ khối không chụp, không ghi lại trong lượt này.
    toolWriting = true;
    try {
      return await setValuesCore(survey, fields);
    } finally {
      toolWriting = false;
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
      if (lookupDone && field.comp !== "sjs-area") {
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

  // ---- Chặn hộp thoại chọn tệp của OS ----
  let suppressPicker = false;
  const nativeClick = HTMLInputElement.prototype.click;
  const nativeShowPicker = HTMLInputElement.prototype.showPicker;
  function interceptFileInput(input) {
    if (!suppressPicker || input?.type !== "file") return false;
    document.querySelectorAll("input[data-hcc-picker]").forEach((el) => el.removeAttribute("data-hcc-picker"));
    input.setAttribute("data-hcc-picker", "1");
    return true;
  }
  if (!window.__HCC_SJS_PICKER_PATCHED__) {
    window.__HCC_SJS_PICKER_PATCHED__ = true;
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

  function emptyRequired() {
    const survey = findSurvey();
    if (!survey) return { ok: false, error: "no-survey" };
    const names = (survey.getAllQuestions(true) || [])
      .filter((q) => !q.isReadOnly && q.isEmpty?.() && (q.isRequired || labelMarksRequired(q)))
      .map((q) => q.name);
    return { ok: true, names };
  }

  async function handleRequest(event) {
    let requestId = "";
    let result;
    try {
      const payload = JSON.parse(String(event.detail || "{}"));
      requestId = String(payload.requestId || "");
      if (payload.op === "setValues") result = await setValues(Array.isArray(payload.fields) ? payload.fields : []);
      else if (payload.op === "fillPlace") result = await fillPlace(payload.place || {});
      else if (payload.op === "emptyRequired") result = emptyRequired();
      else if (payload.op === "suppressPicker") { suppressPicker = !!payload.on; result = { ok: true }; }
      else if (payload.op === "ping") result = { ok: !!findSurvey() };
      else result = { ok: false, error: "unknown-op" };
    } catch (e) {
      result = { ok: false, error: String(e?.message || e) };
    }
    document.dispatchEvent(new CustomEvent(RESULT_EVENT, { detail: JSON.stringify({ requestId, ...result }) }));
  }

  window.__HCC_SJS_HANDLER__ = handleRequest;
  document.addEventListener(REQUEST_EVENT, handleRequest);
})();
