// portal-mae.js — engine cho CỔNG BỘ NÔNG NGHIỆP & MÔI TRƯỜNG dichvucongnnmt.mae.gov.vn
// (Angular Material). Nhiệm vụ: trang "chọn nơi và loại" (form#ngSelectAgencyForm1) —
// chọn Tỉnh + radio "Sở/Ban ngành" + Sở NN&MT + "Trường hợp giải quyết" theo lựa chọn
// của người dân (cấp mới / cấp lại), rồi bấm "Đồng ý và tiếp tục" để vào trang kê khai.
//
// DOM (id mat-select-N/mat-radio-N đổi theo thứ tự render — KHÔNG dùng; formcontrolname ổn định):
//   - mat-select[formcontrolname="agency1"]            → Tỉnh/Thành phố
//   - mat-radio-group[formcontrolname="selectedLevel"] → radio (input value="1" = Sở/Ban ngành)
//   - mat-select[formcontrolname="agency"]             → Sở/Ban ngành hoặc Phường/Xã
//   - mat-select[formcontrolname="procedureProcess"]   → Trường hợp giải quyết (ẨN nếu chỉ 1
//     trường hợp; cổng TỰ chọn option ĐẦU nếu >1 → muốn "cấp lại" phải chủ động mở chọn)
//   - div.button-row button.btn-primary                → "Đồng ý và tiếp tục"
// Option của mat-select render vào div.cdk-overlay-container ở cuối <body> (không nằm trong
// mat-select) → phải mở dropdown rồi mới quét; khớp TEXT fold dấu, không tin data-value.
(() => {
  if (window.__TLND_PORTAL_MAE__) return;
  window.__TLND_PORTAL_MAE__ = true;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const fold = (s) => String(s || "")
    .replace(/Đ/g, "D").replace(/đ/g, "d")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/\s+/g, " ").trim().toLowerCase();
  const isVisible = (el) => {
    if (!el) return false;
    try {
      const style = getComputedStyle(el);
      return style.display !== "none" && style.visibility !== "hidden" && el.getClientRects().length > 0;
    } catch (_) { return false; }
  };
  async function waitFor(fn, timeout = 5000, step = 150) {
    const t0 = Date.now();
    while (Date.now() - t0 < timeout) {
      const v = fn();
      if (v) return v;
      await sleep(step);
    }
    return fn() || null;
  }
  // Angular Material mở dropdown ở click nhưng một số control cần trọn chuỗi pointer.
  function clickLikeUser(el) {
    for (const type of ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]) {
      try {
        el.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }));
      } catch (_) { el.click(); return; }
    }
  }

  // Hai biến thể cùng template Angular: trang "chọn nơi và loại" của MAE/GD&ĐT dùng id
  // ngSelectAgencyForm1 (đủ Tỉnh + radio Sở + Sở + Trường hợp), còn cổng Bộ Xây dựng mở HỘP
  // THOẠI id ngSelectAgencyForm chỉ có Đơn vị thực hiện + Trường hợp giải quyết.
  const maeForm = () =>
    document.querySelector("form#ngSelectAgencyForm1, form#ngSelectAgencyForm");
  const matSelect = (control) => document.querySelector(`mat-select[formcontrolname="${control}"]`);
  const matSelectValue = (sel) => fold(sel?.querySelector?.(".mat-select-value-text")?.textContent || "");

  function overlayOptions() {
    return Array.from(document.querySelectorAll(".cdk-overlay-container mat-option"))
      .filter((o) => isVisible(o));
  }

  // matcher(textFold) → true. Trả {ok} hoặc {error} kèm các option đã thấy để chẩn đoán từ xa.
  async function pickMatOption(sel, matcher, label, { timeout = 8000 } = {}) {
    clickLikeUser(sel.querySelector(".mat-select-trigger") || sel);
    let opt = null;
    const t0 = Date.now();
    let seen = [];
    while (Date.now() - t0 < timeout && !opt) {
      const options = overlayOptions();
      seen = options.map((o) => o.textContent.trim()).filter(Boolean);
      opt = options.find((o) => matcher(fold(o.textContent)));
      // ngx-mat-select-search: danh sách dài → gõ vào ô tìm kiếm trong panel (nếu có).
      if (!opt && options.length) {
        const search = document.querySelector(".cdk-overlay-container input.mat-select-search-input");
        if (search && !search.value && typeof label === "string" && label) {
          const desc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
          desc?.set?.call(search, label);
          search.dispatchEvent(new Event("input", { bubbles: true }));
        }
      }
      if (!opt) await sleep(250);
    }
    if (!opt) {
      try { document.body.click(); } catch (_) { /* đóng panel */ }
      return {
        error: `Không thấy option "${label}". Panel hiện: ` +
          (seen.length ? seen.join(" | ").slice(0, 220) : "(trống)"),
      };
    }
    try { opt.scrollIntoView({ block: "nearest" }); } catch (_) { /* bỏ qua */ }
    clickLikeUser(opt);
    await sleep(350);
    return { ok: true, picked: opt.textContent.trim() };
  }

  async function clickSoBanNganhRadio() {
    const group = await waitFor(
      () => document.querySelector('mat-radio-group[formcontrolname="selectedLevel"]'), 5000);
    if (!group) return { error: 'Không thấy radio "Sở/Ban ngành - Phường/Xã".' };
    const input = Array.from(group.querySelectorAll('input[type="radio"]'))
      .find((r) => r.value === "1");
    if (!input) return { error: 'Không thấy nút radio "Sở/Ban ngành".' };
    const button = input.closest("mat-radio-button");
    if (input.checked || button?.classList?.contains("mat-radio-checked")) return { ok: true };
    clickLikeUser(button?.querySelector("label") || button || input);
    await sleep(400);
    return { ok: true };
  }

  // Trường hợp giải quyết: cổng tự chọn option ĐẦU khi >1 → chỉ mở dropdown khi giá trị hiện
  // tại chưa đúng. variantMatch/variantAvoid là token fold từ BE ("cap lai" / "cap moi").
  async function pickProcedureProcess(variantMatch, variantAvoid, variantLabel) {
    const sel = await waitFor(() => {
      const el = matSelect("procedureProcess");
      return el && isVisible(el) ? el : null;
    }, 9000);
    if (!sel) return { ok: true, skipped: true }; // chỉ 1 trường hợp → cổng ẩn block, đã tự chọn
    const current = matSelectValue(sel);
    // Tên option đổi theo tỉnh: "Trường hợp 1: Cấp mới..." nhưng cũng có "TH1 - Cấp Giấy
    // phép..." (KHÔNG chứa "cấp mới") → cấp mới nhận bằng LOẠI TRỪ token cần tránh ("cap lai");
    // cấp lại bắt buộc chứa "cap lai".
    const good = (text) => {
      if (variantAvoid && text.includes(variantAvoid)) return false;
      if (variantMatch && text.includes(variantMatch)) return true;
      return !!variantAvoid; // có token tránh (cap_moi) → option "sạch" là hợp lệ
    };
    if (current && good(current)) return { ok: true, kept: true };
    const res = await pickMatOption(sel, good, variantLabel || variantMatch || "trường hợp");
    if (res.error) return { error: `Trường hợp giải quyết: ${res.error}` };
    return res;
  }

  function findAgreeButton() {
    const primary = Array.from(document.querySelectorAll("div.button-row button.btn-primary"))
      .find((b) => isVisible(b));
    if (primary) return primary;
    // Hộp thoại Bộ Xây dựng: nút class "applyBtn", nhãn chỉ "Đồng ý" (không có "và tiếp tục").
    const apply = Array.from(document.querySelectorAll("button.applyBtn")).find(isVisible);
    if (apply) return apply;
    const byText = (want) => Array.from(document.querySelectorAll("button"))
      .find((b) => isVisible(b) && fold(b.textContent).includes(want));
    return byText("dong y va tiep tuc") || byText("dong y") || null;
  }

  async function fillMaeAgency({ province, agency, variant, variantMatch, variantAvoid }) {
    const form = await waitFor(maeForm, 6000);
    if (!form) return { error: "Không thấy form chọn cơ quan trên trang." };

    // Rẽ nhánh theo ID FORM chứ không dò DOM: hộp thoại Bộ Xây dựng (ngSelectAgencyForm) chỉ có
    // Đơn vị thực hiện + Trường hợp giải quyết. Dò "có ô Tỉnh không" sẽ rủi ro vì Angular render
    // chậm — trang MAE thật mà ô chưa kịp hiện thì bị bỏ qua im lặng, hỏng đường đang chạy tốt.
    if (form.id === "ngSelectAgencyForm") {
      // Đơn vị thực hiện đã được chọn từ bước "Chọn cơ quan thực hiện" trên DVCQG → giữ nguyên,
      // chỉ đụng vào khi backend gửi tên cơ quan cụ thể.
      if (fold(agency)) {
        const unitSel = await waitFor(() => matSelect("agency"), 5000);
        if (unitSel && !matSelectValue(unitSel).includes(fold(agency))) {
          const res = await pickMatOption(unitSel, (text) => text.includes(fold(agency)), agency);
          if (res.error) return { error: `Đơn vị thực hiện: ${res.error}` };
        }
      }
      const processRes = await pickProcedureProcess(
        fold(variantMatch), fold(variantAvoid), variant || "trường hợp giải quyết");
      if (processRes.error) return processRes;
      const agreeBtn = await waitFor(findAgreeButton, 4000);
      if (!agreeBtn) return { error: 'Không thấy nút "Đồng ý".' };
      clickLikeUser(agreeBtn);
      return { ok: true, dialog: true, process: processRes.picked || (processRes.kept ? "ok" : "skipped") };
    }

    // 1) Tỉnh/Thành phố — option dạng "Thành phố Đà Nẵng"/"Tỉnh Quảng Trị"; khớp 2 chiều
    //    để "Tỉnh Quảng Trị" ăn cả option chỉ ghi "Quảng Trị".
    const provinceSel = await waitFor(() => matSelect("agency1"), 5000);
    if (!provinceSel) return { error: "Không thấy ô chọn Tỉnh/Thành phố." };
    const wantProvince = fold(province);
    if (wantProvince && !matSelectValue(provinceSel).includes(wantProvince)) {
      const res = await pickMatOption(
        provinceSel,
        (text) => text === wantProvince || text.includes(wantProvince) || (text.length >= 4 && wantProvince.includes(text)),
        province,
      );
      if (res.error) return { error: `Tỉnh: ${res.error}` };
      await sleep(600); // chờ danh sách cơ quan nạp lại theo tỉnh
    }

    // 2) Radio "Sở/Ban ngành" (value="1").
    const radioRes = await clickSoBanNganhRadio();
    if (radioRes.error) return radioRes;

    // 3) Sở Nông nghiệp và Môi trường — tên có hậu tố tỉnh ("… Đà Nẵng") → khớp substring.
    const agencySel = await waitFor(() => matSelect("agency"), 5000);
    if (!agencySel) return { error: "Không thấy ô chọn Sở/Ban ngành." };
    const wantAgency = fold(agency || "Sở Nông nghiệp và Môi trường") || "so nong nghiep va moi truong";
    if (!matSelectValue(agencySel).includes(wantAgency)) {
      const res = await pickMatOption(agencySel, (text) => text.includes(wantAgency),
        agency || "Sở Nông nghiệp và Môi trường", { timeout: 9000 });
      if (res.error) return { error: `Sở/Ban ngành: ${res.error}` };
    }

    // 4) Trường hợp giải quyết theo variant người dân đã chọn.
    const processRes = await pickProcedureProcess(
      fold(variantMatch), fold(variantAvoid),
      variant === "cap_lai" ? "Cấp lại" : "Cấp mới",
    );
    if (processRes.error) return processRes;

    // 5) "Đồng ý và tiếp tục" → SPA chuyển sang trang kê khai; watcher sidebar đọc tiếp.
    const agree = await waitFor(findAgreeButton, 4000);
    if (!agree) return { error: 'Không thấy nút "Đồng ý và tiếp tục".' };
    clickLikeUser(agree);
    return {
      ok: true,
      province: provinceSel ? provinceSel.textContent.trim().slice(0, 80) : "",
      process: processRes.picked || processRes.kept ? "ok" : "skipped",
    };
  }

  // Chỉ frame chứa form MAE mới trả lời (all_frames: frame khác im lặng).
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.action !== "fillMaeAgency") return;
    if (!maeForm()) return;
    fillMaeAgency({
      province: msg.province || "",
      agency: msg.agency || "",
      variant: msg.variant || "",
      variantMatch: msg.variantMatch || "",
      variantAvoid: msg.variantAvoid || "",
    })
      .then(sendResponse)
      .catch((e) => sendResponse({ error: String(e?.message || e) }));
    return true; // async
  });
})();
