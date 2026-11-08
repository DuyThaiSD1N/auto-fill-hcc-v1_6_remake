// Adapter Handfree cho lõi HkdOnline lấy nguyên từ Auto-fill.
// Nghiệp vụ fill/attach nằm trong procedures/business-registration.js; file này chỉ nối
// message, tiến độ sidebar và kết quả sống qua full postback.
(() => {
  const H = window.__TLND__ || (window.__TLND__ = {});
  const IS_TOP_FRAME = window.top === window;
  const BUSINESS_HOST = "hokinhdoanh.dkkd.gov.vn";
  const RUN_KEY = "tlnd_business_registration_run";
  const RESULT_KEY = "tlnd_business_registration_result";
  const PAGE_ORDER = [
    "hinh-thuc-dang-ky", "dia-chi", "nganh-nghe-kinh-doanh", "ten-ho-kinh-doanh",
    "chu-ho-kinh-doanh", "thong-tin-ve-von", "thong-tin-ve-thue", "nguoi-nop-ho-so",
  ];
  let businessRunCancelled = false;
  let businessRunFinalizing = false;
  let businessProgressPhaseHint = "fill";
  let progressWrite = Promise.resolve();

  const isBusinessHost = () => String(location.hostname || "").toLowerCase() === BUSINESS_HOST;

  function storageGet(key) {
    return new Promise((resolve) => {
      try {
        chrome.storage.local.get(key, (result) => {
          if (chrome.runtime.lastError) return resolve(null);
          resolve(result?.[key] || null);
        });
      } catch (_) { resolve(null); }
    });
  }

  function storageSet(key, value) {
    return new Promise((resolve) => {
      try { chrome.storage.local.set({ [key]: value }, () => resolve()); }
      catch (_) { resolve(); }
    });
  }

  function storageRemove(key) {
    return new Promise((resolve) => {
      try { chrome.storage.local.remove(key, () => resolve()); }
      catch (_) { resolve(); }
    });
  }

  function notify(message) {
    try { chrome.runtime.sendMessage(message, () => void chrome.runtime.lastError); }
    catch (_) { /* sidebar sẽ khôi phục từ storage sau reload */ }
  }

  function touchBusinessActivity() {
    H.persistPageActivity?.();
  }

  function safeCount(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? Math.max(0, Math.trunc(parsed)) : fallback;
  }

  function progressReport(run, { ok = false, cancelled = false, message = "" } = {}) {
    const totalPages = safeCount(run?.totalPages, PAGE_ORDER.length) || PAGE_ORDER.length;
    const phase = String(run?.progressPhase || (run?.mode === "prepare" ? "bootstrap" : "fill"));
    const currentPage = phase === "attach"
      ? totalPages
      : Math.min(totalPages, safeCount(run?.currentPage));
    const filledPages = ok
      ? totalPages
      : Math.min(totalPages, safeCount(run?.filledPages, Math.max(0, currentPage - 1)));
    const plannedAttachments = safeCount(run?.attachmentsCount);
    const uploadedAttachments = Math.min(
      plannedAttachments,
      safeCount(run?.uploadedAttachments)
    );
    const attachmentCompleted = ok && phase === "attach";
    return {
      ok,
      cancelled,
      mode: String(run?.mode || ""),
      phase,
      currentPage,
      totalPages,
      filledPages,
      attached: attachmentCompleted ? plannedAttachments : 0,
      plannedAttachments,
      uploadedAttachments,
      attachmentStarted: phase === "attach" || !!run?.attachmentStarted,
      attachmentCompleted,
      errors: ok ? [] : [message || "Luồng HkdOnline đã dừng."],
      message,
      createdAt: Date.now(),
    };
  }

  // Lõi business cần đọc contact tài khoản sau nút Sao chép thông tin đăng ký tài khoản.
  H.readAcctContact = function readAcctContact(baseId) {
    const viewValue = String(document.getElementById(baseId + "_Vw")?.textContent || "").trim();
    if (viewValue) return viewValue;
    return String(document.getElementById(baseId)?.value || "").trim();
  };

  H.beginFillAllUI = function beginFillAllUI() {
    if (businessRunCancelled || businessRunFinalizing) return;
    touchBusinessActivity();
    const text = "Đang bắt đầu xử lý hồ sơ hộ kinh doanh…";
    if (typeof H.beginBusinessRunUI === "function") {
      H.beginBusinessRunUI(text, { phase: businessProgressPhaseHint });
    }
    else notify({ type: "businessProgress", text });
  };

  H.setRunProgressText = function setRunProgressText(text) {
    if (businessRunCancelled || businessRunFinalizing) return;
    touchBusinessActivity();
    const progressText = String(text || "");
    if (typeof H.updateBusinessRunUI === "function") H.updateBusinessRunUI(progressText);
    else notify({ type: "businessProgress", text: progressText });
    // Lưu text cùng RUN_KEY để postback kế tiếp dựng đúng nhãn trước khi state machine resume.
    progressWrite = progressWrite.then(async () => {
      if (businessRunFinalizing) return;
      const run = await storageGet(RUN_KEY);
      if (!run) return;
      run.progressText = progressText;
      if (run.mode === "prepare"
          || /—\s*(home|select-registration|search-business|select-change|confirm|unknown)\b/i.test(progressText)) {
        run.progressPhase = "bootstrap";
        run.progressLabel = "";
        run.currentPage = 0;
      } else if (/đính kèm|tài liệu/i.test(progressText)) {
        run.progressPhase = "attach";
        run.progressLabel = "";
        // Chỉ bước sang đính kèm sau khi đã hoàn thành toàn bộ 8 khối. Giữ mốc này trong
        // RUN_KEY để nếu lỗi/dừng giữa postback vẫn báo đúng tiến độ, không tụt về 0/8.
        run.currentPage = safeCount(run.totalPages, PAGE_ORDER.length);
        run.filledPages = run.currentPage;
        run.attachmentStarted = true;
        if (/gán loại|&\s*lưu|hoàn tất/i.test(progressText)) {
          run.uploadedAttachments = safeCount(run.attachmentsCount);
        }
      }
      run.updatedAt = Date.now();
      if (!businessRunFinalizing) await storageSet(RUN_KEY, run);
    });
  };

  H.setFillAllProgress = async function setFillAllProgress(step, total, label) {
    if (businessRunCancelled || businessRunFinalizing) return;
    touchBusinessActivity();
    const text = `Đang điền khối ${step}/${total}${label ? " — " + label : ""}\nCông dân chưa thao tác trên trang giúp tôi ạ.`;
    progressWrite = progressWrite.then(async () => {
      if (businessRunCancelled || businessRunFinalizing) return;
      const run = await storageGet(RUN_KEY);
      if (!run || businessRunCancelled || businessRunFinalizing) return;
      run.currentPage = Number(step || 0);
      run.totalPages = Number(total || run.totalPages || PAGE_ORDER.length);
      // step là khối đang xử lý (1-based), vì vậy số khối chắc chắn đã đi qua là step - 1.
      run.filledPages = Math.max(safeCount(run.filledPages), Math.max(0, Number(step || 0) - 1));
      run.progressText = text;
      run.progressLabel = String(label || "");
      run.progressPhase = "fill";
      run.updatedAt = Date.now();
      if (!businessRunCancelled && !businessRunFinalizing) await storageSet(RUN_KEY, run);
    });
    await progressWrite;
    if (businessRunCancelled || businessRunFinalizing) return;
    if (typeof H.updateBusinessRunUI === "function") {
      H.updateBusinessRunUI(text, { step, total, label, phase: "fill" });
    } else {
      notify({ type: "businessProgress", text });
    }
  };

  H.businessDraftReady = async function businessDraftReady() {
    if (businessRunCancelled) return;
    businessRunFinalizing = true;
    await progressWrite;
    await storageRemove(RUN_KEY);
    await storageRemove(RESULT_KEY);
    if (typeof H.finishBusinessRunUI === "function") await H.finishBusinessRunUI();
    notify({ type: "businessDraftReady" });
  };

  H.endFillAllUI = async function endFillAllUI(doneText) {
    if (businessRunCancelled) return;
    const text = String(doneText || "").trim();
    businessRunFinalizing = true;
    await progressWrite;
    const run = await storageGet(RUN_KEY);
    const ok = text.startsWith("✓") || text.startsWith("✅");
    const reportRun = {
      ...(run || {}),
      progressPhase: /đính kèm/i.test(text)
        ? "attach" : ((run?.mode === "prepare") ? "bootstrap" : (run?.progressPhase || "fill")),
    };
    const report = progressReport(reportRun, {
      ok,
      message: text.replace(/^[⚠️\s]+/, "") || "Luồng HkdOnline dừng không rõ nguyên nhân.",
    });
    await storageSet(RESULT_KEY, report);
    await storageRemove(RUN_KEY);
    if (typeof H.finishBusinessRunUI === "function") await H.finishBusinessRunUI(text);
    notify({ type: "businessFlowFinished", report });
  };

  // Workflow lấy từ action BE (create mặc định — tương thích BE cũ không gửi).
  function workflowOf(msg) {
    const value = String(msg?.workflow || "").trim().toLowerCase();
    return value || "create";
  }

  function detectStageFor(workflow) {
    if (workflow === "create") return H.detectBusinessCreateStage?.() || { stage: "unknown" };
    return H.detectBusinessChangeStage?.() || { stage: "unknown" };
  }

  async function startPrepare(msg) {
    if (!isBusinessHost()) return { error: "Chưa ở Hệ thống Đăng ký Hộ kinh doanh." };
    if (typeof H.setFillAllState !== "function" || typeof H.stepFillAll !== "function") {
      return { error: "Chưa nạp được lõi HkdOnline." };
    }
    const workflow = workflowOf(msg);
    await storageRemove(RESULT_KEY);
    touchBusinessActivity();
    businessRunCancelled = false;
    businessRunFinalizing = false;
    businessProgressPhaseHint = "bootstrap";
    await storageSet(RUN_KEY, {
      mode: "prepare",
      totalPages: 0,
      currentPage: 0,
      progressPhase: "bootstrap",
      updatedAt: Date.now(),
    });
    await H.setFillAllState({
      workflow,
      // Luồng thay đổi pha 1 dừng ở màn BE chỉ định (search-business) để nhận giấy tờ;
      // luồng thành lập mới giữ bootstrapOnly (đi hết wizard tạo hồ sơ nháp rồi dừng).
      bootstrapOnly: workflow === "create",
      stopAtStage: String(msg?.stop_at || "") || null,
      bootstrapDone: false,
      order: [],
      pages: {},
      step: 0,
      retries: 0,
      phase: "bootstrap",
      filledStep: -1,
    });
    setTimeout(() => { H.beginFillAllUI(); H.stepFillAll(); }, 60);
    return { ok: true, started: true, workflow };
  }

  async function startFullRun(msg) {
    if (!isBusinessHost()) return { error: "Chưa ở Hệ thống Đăng ký Hộ kinh doanh." };
    if (typeof H.setFillAllState !== "function" || typeof H.stepFillAll !== "function") {
      return { error: "Chưa nạp được lõi HkdOnline." };
    }
    const pages = msg?.pages || {};
    if (!Object.keys(pages).length) return { error: "Backend chưa trả dữ liệu các khối hồ sơ." };
    const workflow = workflowOf(msg);
    const businessFlow = msg?.businessFlow && typeof msg.businessFlow === "object" ? msg.businessFlow : null;
    // Thay đổi nội dung: thứ tự trang ĐỘNG từ pipeline (chỉ trang cần sửa + Người nộp hồ sơ);
    // thành lập mới giữ 8 trang cố định.
    let order = Array.isArray(businessFlow?.pageOrder) && businessFlow.pageOrder.length
      ? [...businessFlow.pageOrder]
      : [...PAGE_ORDER];
    // Hồ sơ kê "Địa chỉ nhận thông báo thuế = giống trụ sở chính": cổng không chép địa chỉ
    // ở lượt lưu đầu → chèn thêm 1 lượt trang thuế cuối order để tick lại rồi Lưu (đồng bộ
    // hành vi withFinalTaxPass của auto-fill).
    const taxKey = H.TAX_PAGE_KEY || "thong-tin-ve-thue";
    if (typeof H.taxWantsSameAsHeadOffice === "function"
        && order.includes(taxKey)
        && order[order.length - 1] !== taxKey
        && H.taxWantsSameAsHeadOffice((pages && pages[taxKey]) || [])) {
      order = [...order, taxKey];
    }
    const files = Array.isArray(msg?.files) ? msg.files : [];
    const attachments = Array.isArray(msg?.attachments) ? msg.attachments : [];
    const detected = detectStageFor(workflow);
    await storageRemove(RESULT_KEY);
    touchBusinessActivity();
    businessRunCancelled = false;
    businessRunFinalizing = false;
    businessProgressPhaseHint = ["main", "main-root"].includes(detected.stage) ? "fill" : "bootstrap";
    await storageSet(RUN_KEY, {
      mode: "full",
      totalPages: order.length,
      currentPage: 0,
      attachmentsCount: attachments.length,
      progressPhase: businessProgressPhaseHint,
      updatedAt: Date.now(),
    });
    await H.setFillAllState({
      workflow,
      businessFlow,
      businessSearch: businessFlow?.search || null,
      order,
      pages,
      step: 0,
      retries: 0,
      phase: "fill",
      filledStep: -1,
      bootstrapDone: ["main", "main-root"].includes(detected.stage),
      bootstrapOnly: false,
      businessDefaults: msg?.businessDefaults || null,
      attachPayload: files.length && attachments.length ? { files, attachments } : null,
    });
    setTimeout(() => { H.beginFillAllUI(); H.stepFillAll(); }, 60);
    return { ok: true, started: true, workflow, stage: detected.stage, pages: order.length };
  }

  async function clearBusinessRun({ preserveResult = false } = {}) {
    // WebForms reload toàn trang sau mỗi nút Lưu. Nếu công dân kết thúc phiên giữa chừng,
    // phải xóa cả state lõi và state adapter; nếu không content script mới sẽ tự chạy tiếp.
    const tasks = [
      H.clearFillAllState?.(),
      H.clearAttachAllState?.(),
      storageRemove(RUN_KEY),
    ];
    if (!preserveResult) tasks.push(storageRemove(RESULT_KEY));
    await Promise.all(tasks);
    return { ok: true };
  }

  H.isBusinessRunCancelled = () => businessRunCancelled;
  H.cancelBusinessRegistrationRun = async function cancelBusinessRegistrationRun() {
    businessRunCancelled = true;
    businessRunFinalizing = true;
    await progressWrite;
    const run = await storageGet(RUN_KEY);
    const report = progressReport(run, {
      cancelled: true,
      message: "Công dân đã dừng tiến trình tự động kê khai.",
    });
    await storageSet(RESULT_KEY, report);
    await clearBusinessRun({ preserveResult: true });
    if (typeof H.finishBusinessRunUI === "function") {
      await H.finishBusinessRunUI("Đã dừng tiến trình tự động kê khai.");
    }
    // Dùng chung hợp đồng kết quả với nhánh hoàn tất/lỗi để sidebar luôn đưa tiến độ vào chat.
    notify({ type: "businessFlowFinished", report });
    return { ok: true, cancelled: true };
  };

  // ── Trợ lý hộ kinh doanh: BE đi từng khối — mở khối, trỏ ô đang hỏi, điền ngay ô vừa trả lời. Lưu khối vẫn qua
  //    startBusinessRegistration (máy điền chạy đúng một trang). ──
  const HKD_FOCUS_ATTR = "data-tlnd-hkd-focus";
  // Nhớ khối đang mở ở chrome.storage, KHÔNG ở sessionStorage: jquery.dirrty.js của cổng xoá sạch sessionStorage mỗi
  // lần gửi form (postback bấm menu) → cờ mất, không ai báo đã tới khối.
  const HKD_OPEN_KEY = "tlnd_hkd_open_block";
  const HKD_OPEN_TTL_MS = 60000;

  // Trang reload sau khi bấm menu: đúng khối đang chờ → báo sidebar (iframe có thể chưa dựng xong → gửi lại tới khi xác nhận).
  async function hkdReportArrival() {
    const saved = await storageGet(HKD_OPEN_KEY);
    const pending = saved && Date.now() - Number(saved.at || 0) < HKD_OPEN_TTL_MS ? String(saved.page || "") : "";
    if (!pending || H.detectBusinessPageKey?.().pageKey !== pending) return;
    await storageRemove(HKD_OPEN_KEY);
    let tries = 0;
    console.log("[HKD] đã tới khối", pending, "→ báo sidebar");
    // Sidebar dựng lại sau reload có thể mất vài chục giây (khôi phục phiên) → gửi lại tới ~40 s.
    const send = () => {
      tries += 1;
      try {
        chrome.runtime.sendMessage({ type: "hkdArrived", page: pending, accountName: hkdAccountName() }, (res) => {
          void chrome.runtime.lastError;
          if (res?.ok) console.log("[HKD] sidebar đã nhận báo tới khối", pending, "lần", tries);
          else if (tries < 60) setTimeout(send, 700);
        });
      } catch (e) { if (tries < 60) setTimeout(send, 700); }
    };
    send();
  }

  async function hkdOpenBlock(page) {
    if (H.detectBusinessPageKey?.().pageKey === page) return { ok: true, here: true, accountName: hkdAccountName() };
    const label = H.businessPageLabel?.(page) || "";
    const menu = document.querySelectorAll("#ctl00_C_BLCtl_CtlList a, .left-menu a");
    // Chỉ coi là "không có khối" khi menu đã dựng đủ mà thiếu link (khối Ủy quyền / Thành viên chỉ có khi cần).
    if (menu.length >= 5 && !H.findBusinessPageLink?.(label)) return { ok: true, missing: true };
    await storageSet(HKD_OPEN_KEY, { page, at: Date.now() });  // ghi xong mới postback (trang rời đi có thể cắt lệnh ghi)
    return { ok: !!H.goToBusinessPageByKey?.(page), navigating: true };
  }

  function hkdFocus(names) {
    document.querySelectorAll(`[${HKD_FOCUS_ATTR}]`).forEach((el) => {
      el.style.outline = el.getAttribute(HKD_FOCUS_ATTR) === "-" ? "" : el.getAttribute(HKD_FOCUS_ATTR);
      el.style.outlineOffset = "";
      el.removeAttribute(HKD_FOCUS_ATTR);
    });
    let first = null;
    for (const name of names || []) {
      for (const el of document.querySelectorAll(`[name="${CSS.escape(name)}"]`)) {
        // Ô chọn xã bọc combobox jQuery (select ẩn) / radio nhỏ → tô khung bao quanh cho dễ thấy.
        const target = el.type === "radio" || el.type === "checkbox" || !el.offsetParent
          ? (el.closest("td, span, label") || el.parentElement || el) : el;
        if (!target.hasAttribute(HKD_FOCUS_ATTR)) target.setAttribute(HKD_FOCUS_ATTR, target.style.outline || "-");
        target.style.outline = "3px solid #0a9f78";
        target.style.outlineOffset = "2px";
        first = first || target;
      }
    }
    if (first) first.scrollIntoView({ block: "center", behavior: "smooth" });
    return { ok: true, found: !!first };
  }

  // Nút "Sao chép thông tin đăng ký tài khoản" (khối chủ hộ và khối người nộp) là submit thường, ngoài UpdatePanel
  // → cả trang reload, lời đáp cho sidebar mất. Nhớ yêu cầu ở chrome.storage, trang mới tải xong mới đọc kết quả và
  // báo sidebar hkdCopied. Khối người nộp còn so nhân thân vừa sao chép với chủ hộ BE gửi (trùng số định danh HOẶC
  // họ tên = chủ hộ tự nộp); không có chủ hộ để so → sameAsOwner null, BE tự quyết.
  const HKD_COPY_KEY = "tlnd_hkd_copy_account";
  const hkdRead = (id) => String(document.getElementById(id)?.value
    || document.getElementById(`${id}_Vw`)?.textContent || "").replace(/\s+/g, " ").trim();
  const HKD_COPY = {
    "chu-ho-kinh-doanh": {
      btn: "ctl00$C$OWN_PCtl$btnIS_SIGNER",
      ready: () => !!hkdRead("ctl00_C_OWN_PCtl_PERSCtl_FULL_NAMEFld"),
    },
    "nguoi-nop-ho-so": {
      btn: "ctl00$C$btnIS_SIGNER",
      ready: () => !!hkdRead("ctl00_C_PERSCtl_FULL_NAMEFld")
        && !!(hkdRead("ctl00_C_PERSCtl_PHONEFld") || hkdRead("ctl00_C_PERSCtl_EMAILFld")),
    },
  };
  // Tên người đăng nhập ở góc trên mọi trang HkdOnline — BE dùng để hỏi "chủ hộ có phải là … không".
  const hkdAccountName = () => String(document.getElementById("ctl00_LV2_LblFullNameValue")?.textContent || "")
    .replace(/\s+/g, " ").trim();

  async function hkdCopyAccount(page, owner) {
    const cfg = HKD_COPY[page];
    const btn = document.querySelector(`[name="${cfg.btn}"]`);
    if (btn && !cfg.ready()) {
      await storageSet(HKD_COPY_KEY, { page, owner, at: Date.now() });
      try { btn.click(); } catch (e) { /* ignore */ }
      await H.waitFor?.(cfg.ready, 8000, 250);
      if (!cfg.ready()) return { ok: true, reloading: true };  // trang reload → hkdReportCopy báo sau
      await storageRemove(HKD_COPY_KEY);
    }
    return hkdCopyResult(page, owner);
  }

  async function hkdReportCopy() {
    const saved = await storageGet(HKD_COPY_KEY);
    if (!saved || !HKD_COPY[saved.page] || Date.now() - Number(saved.at || 0) > HKD_OPEN_TTL_MS) return;
    if (H.detectBusinessPageKey?.().pageKey !== saved.page) return;
    await storageRemove(HKD_COPY_KEY);
    await H.waitFor?.(HKD_COPY[saved.page].ready, 5000, 250);
    const res = hkdCopyResult(saved.page, saved.owner || null);
    let tries = 0;
    const send = () => {
      tries += 1;
      try {
        chrome.runtime.sendMessage({ type: "hkdCopied", page: saved.page, copied: res.copied,
          same: res.sameAsOwner }, (ack) => {
          void chrome.runtime.lastError;
          if (!ack?.ok && tries < 60) setTimeout(send, 700);
        });
      } catch (e) { if (tries < 60) setTimeout(send, 700); }
    };
    send();
  }

  function hkdCopyResult(page, owner) {
    const fold = (s) => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/gi, "d")
      .toLowerCase().replace(/\s+/g, " ").trim();
    const copied = HKD_COPY[page].ready();
    let same = null;
    if (page === "nguoi-nop-ho-so") {
      const id = hkdRead("ctl00_C_PERSCtl_PERS_DOC_NOFld").replace(/\D/g, "");
      const name = fold(hkdRead("ctl00_C_PERSCtl_FULL_NAMEFld"));
      const ownerId = String(owner?.soDinhDanh || "").replace(/\D/g, "");
      const ownerName = fold(owner?.hoTen);
      // Hai bên cùng có số định danh thì CHỈ so số: trùng họ tên khác số là hai người, coi là một sẽ
      // ghép nơi ở chủ hộ sang người nộp. Thiếu số ở một bên mới phải dựa vào họ tên.
      if (copied && id && ownerId) same = id === ownerId;
      else if (copied && name && ownerName) same = name === ownerName;
    }
    console.log("[HKD]", page, "— sao chép tài khoản:", copied, "| trùng chủ hộ:", same);
    return { ok: true, copied, sameAsOwner: same };
  }

  // "Kiểm tra trùng tên" của cổng là AJAX (HOUSEHOLDName.aspx/GetExistName[F]) đổ HTML vào hộp thoại jQuery — gọi thẳng
  // API đó để đọc được kết quả. HTML trả về chỉ phân tích bằng DOMParser (không chạy script, không tải ảnh).
  async function hkdCheckName(kind, name) {
    const type = String(document.getElementById("hdHOUSEHOLDType")?.value || "HH").trim();
    const foreign = kind === "f";
    try {
      const res = await fetch(`/HkdOnline/Forms/APP/HOUSEHOLDName.aspx/${foreign ? "GetExistNameF" : "GetExistName"}`, {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({ [foreign ? "name_f" : "name"]: `${String(name || "").toUpperCase()}::${type}` }),
      });
      const data = await res.json();
      const doc = new DOMParser().parseFromString(String(data?.d || ""), "text/html");
      const names = [...doc.querySelectorAll("tr")].map((tr) => [...tr.cells].map((c) => c.textContent.trim()))
        .filter((cells) => cells.length >= 2 && /^\d+$/.test(cells[0])).map((cells) => cells[1]);
      const text = String(doc.body?.textContent || "").replace(/\s+/g, " ").trim();
      console.log("[HKD] kiểm trùng tên:", names.length, "tên trong danh sách");
      return { ok: res.ok && !!text, text: text.slice(0, 600), names: names.slice(0, 50) };
    } catch (e) {
      return { ok: false, error: String(e?.message || e) };
    }
  }

  // Bước "Chuẩn bị": Khối dữ liệu → nút Chuẩn bị (ctl00$C$btnAccept). Cả hai lần bấm đều reload trang → nhớ bước ở
  // chrome.storage; tải xong đọc kết quả: sang Trang xác nhận (có nút Nộp ctl00$C$BtnSave) = xong, còn lỗi thì cổng
  // liệt kê trong khung notificationPanel ("(Tên khối) Nội dung lỗi"). KHÔNG bao giờ bấm nút Nộp.
  const HKD_PREP_KEY = "tlnd_hkd_prepare";
  const hkdAcceptBtn = () => document.querySelector('[name="ctl00$C$btnAccept"]');

  async function hkdPrepare() {
    if (hkdAcceptBtn()) {
      await storageSet(HKD_PREP_KEY, { step: "result", at: Date.now() });
      hkdAcceptBtn().click();
      return { ok: true, navigating: true };
    }
    const link = document.querySelector('a[title="Document edit"]')
      || [...document.querySelectorAll("a")].find((a) => (a.textContent || "").trim() === "Khối dữ liệu");
    if (!link) return { ok: false, errors: ["Không thấy nút Chuẩn bị / mục Khối dữ liệu trên trang"] };
    await storageSet(HKD_PREP_KEY, { step: "accept", at: Date.now() });
    link.click();
    return { ok: true, navigating: true };
  }

  async function hkdReportPrepare() {
    const saved = await storageGet(HKD_PREP_KEY);
    if (!saved || Date.now() - Number(saved.at || 0) > HKD_OPEN_TTL_MS) return;
    if (saved.step === "accept" && hkdAcceptBtn()) {
      await storageSet(HKD_PREP_KEY, { step: "result", at: Date.now() });
      hkdAcceptBtn().click();
      return;
    }
    await storageRemove(HKD_PREP_KEY);
    const ok = !!document.querySelector('[name="ctl00$C$BtnSave"]');
    const errors = ok ? [] : [...document.querySelectorAll('.notificationPanel a[id$="_TextLink"]')]
      .map((a) => (a.textContent || "").replace(/\s+/g, " ").trim()).filter(Boolean);
    console.log("[HKD] chuẩn bị hồ sơ:", ok ? "sang Trang xác nhận" : `${errors.length} lỗi`);
    let tries = 0;
    const send = () => {
      tries += 1;
      try {
        chrome.runtime.sendMessage({ type: "hkdPrepared", ok, errors: errors.slice(0, 20) }, (ack) => {
          void chrome.runtime.lastError;
          if (!ack?.ok && tries < 60) setTimeout(send, 700);
        });
      } catch (e) { if (tries < 60) setTimeout(send, 700); }
    };
    send();
  }

  // Khối người (chủ hộ / người nộp) đã Lưu thì cổng hiện ở chế độ XEM: nơi ở chỉ là chữ, không có ô chọn. Phải tích
  // "Sửa đổi dữ liệu" (…$PERSCtl$PERSONChange, postback reload) mới sửa được → nhớ các ô cần điền, tích, tải xong điền
  // tiếp (hkdResumeFill).
  const HKD_REFILL_KEY = "tlnd_hkd_refill";

  async function hkdEnableEdit(fields) {
    const addr = fields.find((f) => /\$PERSCtl\$ADDRCCtl\$/.test(f?.name || ""));
    if (!addr) return false;
    const el = document.querySelector(`[name="${addr.name}"]`);
    if (el && !el.disabled) return false;
    const prefix = addr.name.slice(0, addr.name.indexOf("ADDRCCtl$"));
    const box = document.querySelector(`[name="${prefix}PERSONChange"]`);
    if (!box || box.checked) return false;
    await storageSet(HKD_REFILL_KEY, { fields, page: H.detectBusinessPageKey?.().pageKey || "", at: Date.now() });
    console.log("[HKD] khối đã lưu ở chế độ xem → tích Sửa đổi dữ liệu rồi điền tiếp");
    box.click();
    return true;
  }

  async function hkdResumeFill() {
    const saved = await storageGet(HKD_REFILL_KEY);
    if (!saved || Date.now() - Number(saved.at || 0) > HKD_OPEN_TTL_MS) return;
    if (saved.page && H.detectBusinessPageKey?.().pageKey !== saved.page) return;
    await storageRemove(HKD_REFILL_KEY);
    await hkdFill(saved.fields || []);
  }

  async function hkdFill(fields) {
    const list = Array.isArray(fields) ? fields : [];
    const submitter = list.find((f) => f?.name === "__copySubmitter");
    if (submitter) return hkdCopyAccount("nguoi-nop-ho-so", submitter.value?.owner || null);
    if (list.some((f) => f?.name === "__copyAccount" && f.value)) {
      const res = await hkdCopyAccount("chu-ho-kinh-doanh", null);
      if (res.reloading) return res;
      if (list.every((f) => /^__/.test(f?.name || ""))) return res;  // chỉ sao chép → báo BE để hỏi tiếp
    }
    const real = list.filter((f) => f && !/^__/.test(f.name || ""));
    if (await hkdEnableEdit(real)) return { ok: true, reloading: true };
    const address = real.filter((f) => /\$ADDRC?Ctl\$/.test(f.name || ""));
    const rest = real.filter((f) => !address.includes(f));
    // Radio cấu trúc (loại chủ thể, địa chỉ nhận thông báo thuế) trước khối địa chỉ: cổng dựng lại khối theo radio.
    try { if (rest.length) await H.fillFormStandard(rest); } catch (e) { /* ignore */ }
    try { if (address.length) await H.fillAddressCascade?.(address); } catch (e) { /* ignore */ }
    return { ok: true };
  }

  // Nút "Nộp hồ sơ" của trợ lý (công dân bấm / nói rồi xác nhận): bấm nút Nộp trên Trang xác nhận. Cổng tự hỏi
  // confirm() "Bạn có chắc chắn…" — để nguyên cho công dân bấm OK; luật nhận nộp (BtnSave) ghi cú bấm như bấm tay.
  function hkdSubmit() {
    const btn = document.querySelector('[name="ctl00$C$BtnSave"]');
    if (!btn) return { ok: false };
    btn.click();
    return { ok: true };
  }

  if (IS_TOP_FRAME) {
    chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
      if (msg?.action === "hkdSubmit") {
        // Trả lời TRƯỚC khi bấm: confirm() của cổng chặn trang tới khi công dân bấm OK / Cancel.
        const btn = document.querySelector('[name="ctl00$C$BtnSave"]');
        sendResponse({ ok: !!btn });
        if (btn) setTimeout(hkdSubmit, 50);
        return false;
      }
      if (msg?.action === "hkdOpenBlock") {
        hkdOpenBlock(String(msg.page || "")).catch((e) => ({ error: String(e?.message || e) })).then(sendResponse);
        return true;
      }
      if (msg?.action === "hkdFocus") {
        sendResponse(hkdFocus(msg.names));
        return false;
      }
      if (msg?.action === "hkdPrepare") {
        hkdPrepare().then(sendResponse);
        return true;
      }
      if (msg?.action === "hkdCheckName") {
        hkdCheckName(msg.kind, msg.name).then(sendResponse);
        return true;
      }
      if (msg?.action === "hkdFill") {
        hkdFill(msg.fields).catch((e) => ({ error: String(e?.message || e) })).then(sendResponse);
        return true;
      }
      if (msg?.action === "prepareBusinessRegistration") {
        // Exception phải trả về dạng {error} — reject âm thầm làm sidebar báo mù
        // "Trang HkdOnline chưa nhận lệnh tự điền" và luồng đứng im.
        startPrepare(msg)
          .catch((e) => ({ error: `Lỗi khởi động HkdOnline: ${e?.message || e}` }))
          .then(sendResponse);
        return true;
      }
      if (msg?.action === "startBusinessRegistration") {
        startFullRun(msg)
          .catch((e) => ({ error: `Lỗi khởi động HkdOnline: ${e?.message || e}` }))
          .then(sendResponse);
        return true;
      }
      if (msg?.action === "getBusinessRuntimeContext") {
        Promise.all([storageGet(RUN_KEY), storageGet(RESULT_KEY)]).then(([run, result]) => {
          const freshResult = result && Date.now() - Number(result.createdAt || 0) < 30 * 60 * 1000
            ? result : null;
          sendResponse({
            ok: true,
            businessHost: isBusinessHost(),
            businessStage: isBusinessHost()
              ? ((H.detectBusinessAnyStage?.() || H.detectBusinessCreateStage?.())?.stage || "unknown")
              : "",
            businessProcedureHint: isBusinessHost() ? (H.detectBusinessProcedureHint?.() || "") : "",
            businessActive: !!run,
            businessResult: freshResult,
          });
        });
        return true;
      }
      if (msg?.action === "ackBusinessResult") {
        storageRemove(RESULT_KEY).then(() => sendResponse({ ok: true }));
        return true;
      }
      if (msg?.action === "clearBusinessRegistrationState") {
        clearBusinessRun().then(sendResponse);
        return true;
      }
    });

    // Mỗi full postback tạo content context mới; tự nhặt state đã persist và chạy tiếp.
    if (isBusinessHost()) {
      setTimeout(hkdReportArrival, 400);
      setTimeout(hkdReportCopy, 450);
      setTimeout(hkdReportPrepare, 500);
      setTimeout(hkdResumeFill, 600);
      setTimeout(async () => {
        touchBusinessActivity();
        const fillState = await H.getFillAllState?.();
        if (fillState) return void H.stepFillAll?.();
        const attachState = await H.getAttachAllState?.();
        if (attachState) H.stepAttachAll?.();
      }, 350);
    }
  }
})();
