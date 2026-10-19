// Bổ sung ô còn trống trên trang nộp một trang của Cổng DVC quốc gia (dichvucong.gov.vn/nop-ho-so, form SurveyJS)
// sau khi điền. Cùng giao thức fieldReviewMark / fieldReviewNext / fieldReviewStop với content/field-review.js
// (tờ khai eForm cũ) nên sidebar và BE (chat/field_review) dùng chung; file này chỉ khác ở cách đọc/ghi ô:
//   - danh sách ô + giá trị + bắt buộc đọc qua model survey ở MAIN world (content/surveyjs-main.js, op review*),
//     chỉ các câu đang hiện và sửa được — chọn tình trạng hôn nhân / mục đích / nơi cư trú xong, các ô chi tiết
//     vừa hiện ra được hỏi ở lượt sau;
//   - tô màu bằng thuộc tính data-tlnd-mark (React vẽ lại là ghi đè class), thêm màu cam cho ô không bắt buộc;
//   - con trỏ + khung gợi ý dùng chung H.fieldReviewPointer của content/field-review.js.
// Ô bắt buộc = cổng đánh dấu (isRequired / "*" ở nhãn) HOẶC tên BE khai (registry REQUIRED); ô BE khai noAsk
// (Kính gửi, ngày lập tờ khai…) không tô, không đếm, không hỏi; ô BE khai zeroIsEmpty (số lượng bản sao — cổng để
// sẵn 0) còn 0 mà công dân chưa trả lời trong vòng này thì coi là trống; ô textDates (ô chữ cổng kiểm regex ngày,
// vd ngày chết khai tử) báo BE là ô ngày nhận cả tháng-năm / năm nhưng ghi vào cổng dạng chữ; ô lookup (tra cứu CSDL
// dân cư) điền xong chờ cổng đổ dữ liệu rồi mới tìm ô kế tiếp.
(() => {
  if (window.__TLND_FIELD_REVIEW_SJS__) return;
  window.__TLND_FIELD_REVIEW_SJS__ = true;
  const H = (window.__TLND__ = window.__TLND__ || {});

  const MARK_ATTR = "data-tlnd-mark";
  const ASKING_ATTR = "data-tlnd-fr-asking";
  const STYLE_ID = "tlnd-sjs-field-review-style";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const LOOKUP_WAIT_MS = 2500; // như engine điền (surveyjs-main.js): cổng tra CSDL dân cư rồi tự đổ các ô
  const baseName = (name) => String(name || "").replace(/__\d+$/, "");
  // Ô công dân đã trả lời qua vòng bổ sung (giá trị nào cũng là của công dân, kể cả 0).
  const answered = new Set();

  function injectStyles() {
    H.injectSurveyJsMarkStyles?.();
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      [${MARK_ATTR}="optional"] .sd-input, [${MARK_ATTR}="optional"] fieldset {
        background-color: #fff3e0 !important; outline: 2px solid #fb8c00 !important;
        outline-offset: 1px !important; border-radius: 3px !important; }
      [${ASKING_ATTR}] { outline: 3px solid #1e66f5 !important; outline-offset: 2px !important;
        box-shadow: 0 0 0 6px rgba(30, 102, 245, .22) !important; border-radius: 4px !important; }
    `;
    (document.head || document.documentElement).appendChild(style);
  }

  const questionEl = (name) => Array.from(document.querySelectorAll(`[data-name="${CSS.escape(name)}"]`))
    .find((el) => el.getClientRects().length > 0) || null;

  async function questions(msg) {
    const res = await H.callSurveyJs({ op: "reviewList" }, 10000);
    const skip = new Set(msg.noAsk || []);
    const textDates = new Set(msg.textDates || []);
    const list = (res?.ok && Array.isArray(res.questions) ? res.questions : []).filter((q) => !skip.has(baseName(q.name)));
    for (const q of list) {
      if (q.kind === "text" && textDates.has(baseName(q.name))) { q.kind = "date"; q.textDate = true; }
    }
    return list;
  }

  async function markAll(msg) {
    injectStyles();
    const need = new Set(msg.required || []);
    const zero = new Set(msg.zeroIsEmpty || []);
    const stats = { filled: 0, optional: 0, required: 0 };
    const list = await questions(msg);
    for (const q of list) {
      q.required = q.required || need.has(baseName(q.name));
      if (zero.has(baseName(q.name)) && q.value !== "" && Number(q.value) === 0 && !answered.has(q.name)) q.value = "";
      const kind = q.value ? "filled" : q.required ? "not-filled" : "optional";
      H.setSurveyJsMark?.(questionEl(q.name), kind);
      stats[q.value ? "filled" : q.required ? "required" : "optional"] += 1;
    }
    return { list, stats };
  }

  function unfocus() {
    document.querySelectorAll(`[${ASKING_ATTR}]`).forEach((el) => el.removeAttribute(ASKING_ATTR));
    H.fieldReviewPointer?.unfocus();
  }

  async function focusQuestion(q) {
    unfocus();
    const el = questionEl(q.name);
    if (!el) return;
    await H.fieldReviewPointer?.focus(el);
    el.setAttribute(ASKING_ATTR, "1");
  }

  function publicField(q, options, province) {
    return {
      key: q.name, name: baseName(q.name), role: "", kind: q.kind, yearOnly: false, partialDate: !!q.textDate,
      label: q.label, group: "",
      section: q.section || "", required: !!q.required, options, value: q.value || "",
      // Ô Xã mà Tỉnh đã có nhưng bấm "Làm mới" / chọn lại tỉnh cổng vẫn không nạp danh sách → BE mời tải lại / bỏ qua.
      ...(province ? { optionsFailed: true, province } : {}),
    };
  }

  async function next(msg) {
    const skip = new Set(Array.isArray(msg.skip) ? msg.skip : []);
    let applied = null;
    if (msg.apply && msg.apply.key) {
      const target = (await questions(msg)).find((q) => q.name === msg.apply.key);
      // Ô ngày dạng chữ: ghi đúng chuỗi dd/mm/yyyy | mm/yyyy | yyyy (đường ô ngày lịch đổi sang yyyy-mm-dd).
      const res = target ? await H.callSurveyJs({
        op: "reviewSet", name: target.name, kind: target.textDate ? "text" : target.kind,
        value: String(msg.apply.value ?? ""),
      }, 20000) : null;
      const ok = !!res?.ok;
      applied = { key: msg.apply.key, ok };
      if (ok) answered.add(msg.apply.key);
      // Điền không được thì không hỏi lại ô đó ngay ở lượt này (BE cũng ghi vào danh sách bỏ qua).
      if (!ok) skip.add(msg.apply.key);
      // Ô phụ thuộc (vd chọn "đã ly hôn" → ba ô bản án) hiện ra sau một nhịp vẽ của React; ô tra cứu thì chờ cổng
      // tra CSDL đổ giới tính, dân tộc… kẻo hỏi đúng ô cổng sắp tự điền.
      const lookup = ok && (msg.lookup || []).includes(baseName(msg.apply.key));
      await sleep(lookup ? LOOKUP_WAIT_MS : 350);
    }
    const { list, stats } = await markAll(msg);
    // focus: công dân xin sửa một ô đã hỏi → về đúng ô đó dù đã có giá trị; không thì ô trống kế tiếp.
    const q = (msg.focus && list.find((x) => x.name === msg.focus)) || list.find((x) => !x.value && !skip.has(x.name));
    if (!q) { unfocus(); return { ok: true, applied, field: null, stats }; }
    let options = q.kind === "radio" ? q.options || [] : [];
    let province = "";
    if (q.kind === "select") {
      const res = await H.callSurveyJs({ op: "reviewChoices", name: q.name }, 20000);
      options = Array.isArray(res?.options) ? res.options : [];
      if (!options.length) province = String(res?.province || "");
    }
    await focusQuestion(q);
    return { ok: true, applied, field: publicField(q, options, province), stats };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = String(msg?.action || "");
    if (!action.startsWith("fieldReview")) return;
    // all_frames: chỉ frame chứa form SurveyJS trả lời; tờ khai eForm do content/field-review.js trả lời.
    if (H.detectFormKind?.() !== "surveyjs" || typeof H.callSurveyJs !== "function") return;
    if (action === "fieldReviewMark") {
      markAll(msg).then(({ stats }) => sendResponse({ ok: true, stats }))
        .catch((e) => sendResponse({ ok: false, error: String(e?.message || e) }));
      return true;
    }
    if (action === "fieldReviewStop") {
      unfocus();
      sendResponse({ ok: true });
      return;
    }
    if (action === "fieldReviewNext") {
      next(msg).then(sendResponse).catch((e) => sendResponse({ ok: false, error: String(e?.message || e) }));
      return true;
    }
  });
})();
