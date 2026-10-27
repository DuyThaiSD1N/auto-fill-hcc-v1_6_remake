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
