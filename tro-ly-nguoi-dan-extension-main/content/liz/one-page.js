// Chặng cuối trên trang nộp một trang của cổng Bộ VHTTDL (dichvucong.bvhttdl.gov.vn, form liz). BE điều phối ở
// chat/tu_phap_moi.py (registry lizFlow), extension khai supportsLizFlow:
//   - selectResultMethod: tích ô cam kết (nút "Lưu và nộp hồ sơ" của cổng chỉ mở sau khi tích), gạt ô "Đề nghị nhận
//     kết quả bản giấy tại nhà qua Bưu chính công ích (VNPost)" theo postOffice; tích thì cổng mọc khối người nhận
//     (recipient_*) → điền theo khối "Thông tin người nộp hồ sơ", báo ô đã điền / ô bắt buộc còn trống;
//     fillRecipient=false (câu hỏi VNPost sau ô cam kết): không điền, chỉ cuộn tới khối người nhận + báo ô còn trống;
//   - guidedSubmit: tích lại ô cam kết, soát ô bắt buộc đang hiện, chờ nút nộp mở rồi bấm, đọc thông báo lỗi của cổng;
//   - chặng ô cam kết riêng (sidebar khai supportsLizCommitSelf):
//       lizCommitWatch: đọc ô cam kết + theo dõi — công dân tự tích / bỏ tích thì báo sidebar (lizCommitChanged);
//       lizCommitTick: công dân bấm nút cam "Tích ô cam kết" → cuộn tới ô rồi tích, trả trạng thái ô;
//       guidedSubmit nhận commitSelf: không tích hộ, ô chưa tích thì không bấm nộp, trả commit=false.
// Trang khác (DVCQG SurveyJS, cổng bộ iGate…) có engine riêng → ở đây im lặng.
(() => {
  if (window.__TLND_LIZ_ONE_PAGE__) return;
  window.__TLND_LIZ_ONE_PAGE__ = true;
  const H = (window.__TLND__ = window.__TLND__ || {});

  const HOST = "dichvucong.bvhttdl.gov.vn";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const textOf = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  const cleanLabel = (s) => String(s || "").replace(/\*/g, "").replace(/\s+/g, " ").trim();
  const fold = (s) => cleanLabel(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d");
  const shown = (el) => !!el && el.getClientRects().length > 0;
  const ourPage = () => location.hostname === HOST && H.detectFormKind?.() === "liz";
  H.isLizOnePage = ourPage;

  async function waitFor(fn, timeout, step = 150) {
    for (let waited = 0; waited <= timeout; waited += step) {
      const value = fn();
      if (value) return value;
      await sleep(step);
    }
    return fn();
  }

  // Ô cam kết hiện HAI lần (đầu và cuối trang), không id/name → khớp theo chữ của <label> bọc ô.
  function commitBoxes(label) {
    const want = fold(label).slice(0, 40);
    if (!want) return [];
    return Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter((input) => fold(textOf(input.closest("label"))).includes(want));
  }

  // Hai ô có thể cùng một model (tích ô này cổng tự tích ô kia) → xét lại từng ô ngay trước khi bấm.
  async function tickCommit(label) {
    const boxes = commitBoxes(label);
    if (!boxes.length) return false;
    for (const box of boxes) {
      if (box.checked || box.disabled) continue;
      box.click();
      await waitFor(() => box.checked, 1000);
      await sleep(150);
    }
    return boxes.every((box) => box.checked);
  }

  // ── Chặng ô cam kết ──
  let commitWatch = ""; // nhãn ô cam kết đang theo dõi (BE gửi), rỗng = chưa theo dõi
  let commitLast = null;
  let commitTicking = false; // trợ lý đang tích theo nút cam → sự kiện change của chính cú bấm đó không báo lại

  // Ô cam kết có thể hiện hai lần: chỉ xét ô đang hiện (không có thì xét hết), đủ mọi ô đã tích mới tính là đã tích.
  function commitState(label) {
    const all = commitBoxes(label);
    const boxes = all.filter(shown).length ? all.filter(shown) : all;
    const unticked = boxes.filter((box) => !box.checked);
    return { found: boxes.length > 0, checked: boxes.length > 0 && !unticked.length, unticked: unticked[0] || null };
  }

  // Chỉ cuộn cho công dân thấy ô — không con trỏ, không dòng gợi ý (user 10/11: bỏ chữ nền xanh trên trang).
  function showCommit(box) {
    (box?.closest("label") || box)?.scrollIntoView?.({ block: "center", behavior: "smooth" });
  }

  function watchCommit(msg) {
    const label = String(msg.commitLabel || "");
    if (!label) return { ok: false, found: false, checked: false };
    commitWatch = label;
    const state = commitState(label);
    commitLast = state.checked;
    return { ok: true, found: state.found, checked: state.checked };
  }

  async function tickCommitForCitizen(msg) {
    const label = String(msg.commitLabel || "");
    if (!label) return { ok: false, found: false, checked: false };
    commitWatch = label;
    const before = commitState(label);
    if (before.found && !before.checked) {
      showCommit(before.unticked);
      commitTicking = true;
      try {
        await tickCommit(label);
      } finally {
        commitTicking = false;
      }
    }
    const state = commitState(label);
    commitLast = state.checked;
    return { ok: true, found: state.found, checked: state.checked };
  }

  // Công dân tích / bỏ tích trên trang → báo sidebar một lần mỗi lần đổi (ô kia cùng model đổi theo sau một nhịp).
  document.addEventListener("change", (event) => {
    const target = event.target;
    if (!commitWatch || commitTicking || !ourPage() || target?.type !== "checkbox") return;
    if (!commitBoxes(commitWatch).includes(target)) return;
    setTimeout(() => {
      if (commitTicking) return;
      const state = commitState(commitWatch);
      if (state.checked === commitLast) return;
      commitLast = state.checked;
      try {
        chrome.runtime.sendMessage({ __tlnd: "lizCommitChanged", checked: state.checked },
          () => void chrome.runtime.lastError);
      } catch (_) { /* extension vừa reload: bỏ lượt báo này */ }
    }, 250);
  }, true);

  const fieldOf = (control) => control?.closest("mat-form-field") || null;
  const valueOf = (mf) => {
    if (!mf) return "";
    if (mf.querySelector("mat-select")) {
      return cleanLabel(textOf(mf.querySelector(".mat-mdc-select-value-text, .mat-select-value-text")));
    }
    return String(mf.querySelector("input, textarea")?.value || "").trim();
  };
  const labelOf = (mf) => cleanLabel(textOf(mf?.querySelector("mat-label")));

  // Ô của khối "Thông tin người nộp hồ sơ" theo đầu nhãn (nhãn đầy đủ: "Tên người nộp / Tên đơn vị"…).
  function applicantValue(prefix) {
    for (const group of document.querySelectorAll(".group")) {
      if (!fold(textOf(group.querySelector(".group-header"))).includes("thong tin nguoi nop")) continue;
      for (const mf of group.querySelectorAll("mat-form-field")) {
        if (fold(labelOf(mf)).startsWith(prefix)) return valueOf(mf);
      }
    }
    return "";
  }

  // Khối người nhận mọc khi tích VNPost: nguồn lấy từ khối người nộp; ô đã có giá trị thì giữ.
  const RECIPIENT = [
    { selector: 'input[name="recipient_name"]', from: "ten nguoi nop" },
    { selector: 'input[name="recipient_phone"]', from: "so dien thoai" },
    { selector: 'input[name="recipient_address"]', from: "dia chi chi tiet" },
    { selector: 'mat-select[name="recipient_commune_id"]', from: "dia chi hanh chinh" },
  ];

  const invalid = (mf) => {
    const input = mf.querySelector("input");
    return !!input && !!String(input.value || "").trim() && input.validity && !input.validity.valid;
  };

  // Ô bắt buộc đang hiện mà trống (hoặc sai mẫu, vd số điện thoại người nhận) — nhãn để BE đọc lên.
  function requiredEmpty(root = document) {
    const out = [];
    for (const mf of root.querySelectorAll("mat-form-field")) {
      if (!shown(mf) || mf.closest(".cdk-overlay-container")) continue;
      const control = mf.querySelector("mat-select") || mf.querySelector("input, textarea");
      if (!control || control.disabled || control.getAttribute("aria-disabled") === "true") continue;
      const required = !!mf.querySelector(".mat-mdc-form-field-required-marker, .mat-form-field-required-marker")
        || control.required || control.getAttribute("aria-required") === "true";
      if (required && (!valueOf(mf) || invalid(mf))) out.push(labelOf(mf) || cleanLabel(control.getAttribute("name")));
    }
    return out.filter(Boolean);
  }

  function recipientMissing() {
    return RECIPIENT.map((spec) => fieldOf(document.querySelector(spec.selector)))
      .filter((mf) => mf && (!valueOf(mf) || invalid(mf))).map(labelOf).filter(Boolean);
  }

  async function fillRecipient() {
    const filled = [];
    const fields = [];
    for (const spec of RECIPIENT) {
      const mf = fieldOf(document.querySelector(spec.selector));
      if (!mf) continue;
      fields.push(mf);
      const source = applicantValue(spec.from);
      if (valueOf(mf) || !source || typeof H.fillLizFieldElement !== "function") continue;
      try {
        if (await H.fillLizFieldElement(mf, source) === "ok" && valueOf(mf)) filled.push(labelOf(mf));
      } catch (e) {
        console.warn("[TLND] điền người nhận liz lỗi:", e);
      }
    }
    const missing = fields.filter((mf) => !valueOf(mf) || invalid(mf)).map(labelOf).filter(Boolean);
    return { filled, missing };
  }

  async function selectResultMethod(msg) {
    const commit = msg.commitLabel ? await tickCommit(msg.commitLabel) : undefined;
    if (typeof msg.postOffice !== "boolean") return { ok: true, commit, filled: [], missing: [] };
    const box = document.querySelector('input[type="checkbox"][name="post_office"]');
    if (!box) return { ok: false, commit, error: "Không thấy ô nhận kết quả qua Bưu chính công ích (VNPost)." };
    if (box.checked !== msg.postOffice) {
      box.click();
      await waitFor(() => box.checked === msg.postOffice, 1500);
    }
    if (box.checked !== msg.postOffice) return { ok: false, commit, error: "Ô VNPost không đổi trạng thái." };
    if (!msg.postOffice) return { ok: true, commit, filled: [], missing: [] };
    const appeared = await waitFor(() => document.querySelector('input[name="recipient_name"]'), 3000);
    if (!appeared) return { ok: true, commit, filled: [], missing: [] };
    await sleep(300);
    if (msg.fillRecipient === false) {
      // Câu hỏi VNPost sau ô cam kết (BE 13/11): công dân tự điền khối người nhận + chọn cách thanh toán lệ phí →
      // chỉ cuộn tới khối đó, trả các ô người nhận còn trống để trợ lý kể tên.
      (fieldOf(appeared) || appeared).scrollIntoView?.({ block: "center", behavior: "smooth" });
      return { ok: true, commit, filled: [], missing: recipientMissing() };
    }
    return { ok: true, commit, ...(await fillRecipient()) };
  }

  const submitButton = () => Array.from(document.querySelectorAll("button.style_btn"))
    .filter((b) => shown(b) && fold(textOf(b)).includes("luu va nop ho so"));

  // Thông báo cổng nháy lên sau khi bấm (snackbar / toast / hộp thoại) — chữ "thành công" không phải lỗi.
  function portalMessage() {
    const nodes = document.querySelectorAll("mat-snack-bar-container, .mat-mdc-snack-bar-container, simple-snack-bar, "
      + ".toast-container .toast, .toast-message, .swal2-popup, mat-dialog-container, .mat-mdc-dialog-container");
    for (const node of nodes) {
      const text = textOf(node);
      if (shown(node) && text && !fold(text).includes("thanh cong")) return text.slice(0, 300);
    }
    return "";
  }

  async function submit(msg) {
    if (msg.commitLabel && msg.commitSelf) {
      // Chặng ô cam kết riêng: nộp không tích hộ — ô chưa tích thì không bấm, cuộn cho công dân thấy ô.
      const state = commitState(msg.commitLabel);
      commitWatch = msg.commitLabel;
      commitLast = state.checked;
      if (state.found && !state.checked) {
        showCommit(state.unticked);
        return { ok: false, clicked: false, commit: false, missing: [] };
      }
    }
    const commit = msg.commitLabel && !msg.commitSelf ? await tickCommit(msg.commitLabel) : true;
    const missing = requiredEmpty();
    if (missing.length) return { ok: false, clicked: false, missing };
    const button = await waitFor(() => submitButton().find((b) => !b.disabled), 5000);
    if (!button) {
      return {
        ok: false, clicked: false,
        message: commit ? "Nút Lưu và nộp hồ sơ của cổng vẫn đang khoá."
          : "Chưa tích được ô cam kết nên nút Lưu và nộp hồ sơ của cổng còn khoá.",
      };
    }
    button.click();
    const message = await waitFor(portalMessage, 2500);
    return { ok: !message, clicked: true, message };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = String(msg?.action || "");
    if (!["selectResultMethod", "guidedSubmit", "lizCommitWatch", "lizCommitTick"].includes(action) || !ourPage()) {
      return;
    }
    if (action === "lizCommitWatch") {
      sendResponse(watchCommit(msg));
      return;
    }
    if (action === "lizCommitTick") {
      tickCommitForCitizen(msg).then(sendResponse)
        .catch((e) => sendResponse({ ok: false, found: false, checked: false, error: String(e?.message || e) }));
      return true; // async
    }
    const run = action === "selectResultMethod" ? selectResultMethod(msg) : submit(msg);
    run.then(sendResponse).catch((e) => sendResponse({ ok: false, clicked: false, error: String(e?.message || e) }));
    return true; // async
  });
})();
