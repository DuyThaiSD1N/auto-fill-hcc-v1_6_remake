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
    const text = `Đang điền khối ${step}/${total}${label ? " — " + label : ""}\nCông dân chưa thao tác trên trang giúp em ạ.`;
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

  if (IS_TOP_FRAME) {
    chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
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
