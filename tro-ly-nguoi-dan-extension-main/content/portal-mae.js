// portal-mae.js — engine cho CỔNG BỘ NÔNG NGHIỆP & MÔI TRƯỜNG dichvucongnnmt.mae.gov.vn
// (Angular Material). Nhiệm vụ: trang "chọn nơi và loại" (form#ngSelectAgencyForm1) —
// chọn Tỉnh + radio "Sở/Ban ngành" + Sở NN&MT + "Trường hợp giải quyết" theo lựa chọn
// của người dân (cấp mới / cấp lại), rồi bấm "Đồng ý và tiếp tục" để vào trang kê khai.
//
// DOM (id mat-select-N/mat-radio-N đổi theo thứ tự render — KHÔNG dùng; formcontrolname ổn định):
//   - mat-select[formcontrolname="agency1"]            → Tỉnh/Thành phố
//   - mat-radio-group[formcontrolname="selectedLevel"] → radio (value "1" = Sở/Ban ngành,
//     value "0" = Phường/Xã — thủ tục giải quyết ở cấp xã đi nhánh này, BE gửi agencyLevel)
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
  // Chỉ form đang HIỆN: cổng Bộ Xây dựng giữ khối hộp thoại (ẩn) trong DOM cả khi đã sang trang kê
  // khai — tin form ẩn là đọc/chọn nhầm ô của trang khác.
  const maeForm = () =>
    Array.from(document.querySelectorAll("form#ngSelectAgencyForm1, form#ngSelectAgencyForm"))
      .find((form) => isVisible(form)) || null;
  // Tìm ô TRONG form đang hiện trước (trang kê khai có thể có mat-select trùng formcontrolname).
  const matSelect = (control) => {
    const selector = `mat-select[formcontrolname="${control}"]`;
    return maeForm()?.querySelector(selector) || document.querySelector(selector);
  };
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
      // body.click() không đóng được mat-select → panel treo trên hộp thoại. Đóng đúng cách.
      await closeMatPanel("");
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

  // Cùng một radio-group: value "1" = Sở/Ban ngành, value "0" = Phường/Xã (cổng tích sẵn "0").
  // Thủ tục giải quyết ở cấp xã (Bộ Nội vụ — người có công từ trần) cần nhánh "0".
  async function clickLevelRadio(wantValue) {
    const group = await waitFor(
      () => document.querySelector('mat-radio-group[formcontrolname="selectedLevel"]'), 5000);
    if (!group) return { error: 'Không thấy radio "Sở/Ban ngành - Phường/Xã".' };
    const input = Array.from(group.querySelectorAll('input[type="radio"]'))
      .find((r) => r.value === wantValue);
    if (!input) {
      return { error: `Không thấy nút radio ${wantValue === "0" ? '"Phường/Xã"' : '"Sở/Ban ngành"'}.` };
    }
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
      // Thủ tục không khai trường hợp nào (hộp thoại Bộ Xây dựng, BE không gửi token) → giữ
      // lựa chọn cổng đang để; chưa có thì lấy option đầu như chính cổng vẫn làm.
      if (!variantMatch && !variantAvoid) return true;
      if (variantAvoid && text.includes(variantAvoid)) return false;
      if (variantMatch && text.includes(variantMatch)) return true;
      return !!variantAvoid; // có token tránh (cap_moi) → option "sạch" là hợp lệ
    };
    if (current && good(current)) return { ok: true, kept: true };
    const res = await pickMatOption(sel, good, variantLabel || variantMatch || "trường hợp");
    if (res.error) return { error: `Trường hợp giải quyết: ${res.error}` };
    return res;
  }

  // ── Hộp thoại "Chọn trường hợp giải quyết" (Bộ Xây dựng): ĐỌC danh sách lựa chọn ──────────
  // BE hỏi công dân nơi xử lý (Đơn vị thực hiện) + trường hợp/thời gian (Trường hợp giải quyết)
  // theo đúng chữ trên cổng, nên phải mở từng ô, đọc option rồi đóng lại mà KHÔNG đổi giá trị.
  const textOf = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  const matSelectRaw = (sel) =>
    textOf(sel?.querySelector?.(".mat-select-value-text, .mat-mdc-select-value-text"));

  // Option của ĐÚNG dropdown vừa mở: panel mang id "<id mat-select>-panel" (aria-controls/owns
  // trỏ tới nó). Không tìm thấy panel riêng mới quét chung overlay — tránh đọc lẫn danh sách của
  // một dropdown khác chưa kịp đóng.
  function panelOptions(sel) {
    let scoped = null;
    const ids = [sel?.id ? `${sel.id}-panel` : "",
      ...String(sel?.getAttribute?.("aria-controls") || sel?.getAttribute?.("aria-owns") || "")
        .split(/\s+/)].filter(Boolean);
    for (const id of ids) {
      const node = document.getElementById(id);
      if (!node) continue;
      const inside = node.matches("mat-option") ? [node] : Array.from(node.querySelectorAll("mat-option"));
      if (inside.length) { scoped = (scoped || []).concat(inside); }
    }
    return (scoped || overlayOptions()).filter((o) => {
      if (!isVisible(o)) return false;
      if (o.classList.contains("mat-option-disabled") || o.getAttribute("aria-disabled") === "true") {
        return false;
      }
      if (o.querySelector("input")) return false; // dòng ô tìm kiếm của ngx-mat-select-search
      return !!textOf(o);
    });
  }

  // Đóng dropdown mà KHÔNG đóng hộp thoại: bấm lại option đang chọn (giá trị giữ nguyên); không
  // có thì bấm lớp nền trong suốt CUỐI CÙNG — lớp nền đầu tiên thuộc hộp thoại, bấm vào là đóng
  // luôn cả hộp thoại.
  async function closeMatPanel(currentText) {
    const options = overlayOptions();
    const selected = options.find((o) => o.classList.contains("mat-selected")
      || o.getAttribute("aria-selected") === "true")
      || (currentText ? options.find((o) => fold(o.textContent) === fold(currentText)) : null);
    if (selected) {
      clickLikeUser(selected);
    } else {
      const backdrops = document.querySelectorAll(
        ".cdk-overlay-transparent-backdrop, .cdk-overlay-backdrop");
      const last = backdrops[backdrops.length - 1];
      if (last) clickLikeUser(last);
    }
    await waitFor(() => !overlayOptions().length, 1500, 100);
  }

  async function readMatSelectOptions(control) {
    const sel = matSelect(control);
    if (!sel || !isVisible(sel)) return null; // ô ẩn = cổng đã tự chọn lựa chọn duy nhất
    // Còn dropdown khác đang mở (hoặc đang đóng dở) → đóng hẳn trước, không thì đọc lẫn danh sách.
    if (overlayOptions().length) await closeMatPanel("");
    const current = matSelectRaw(sel);
    clickLikeUser(sel.querySelector(".mat-select-trigger") || sel);
    const read = () => panelOptions(sel);
    let options = (await waitFor(() => (read().length ? read() : null), 3000)) || [];
    if (options.length) {
      await sleep(250); // danh sách có thể nạp dần → đọc lại một nhịp cho đủ
      options = read();
    }
    const labels = Array.from(new Set(options.map(textOf))).slice(0, 40);
    await closeMatPanel(current);
    return { options: labels, current };
  }

  // Ô "Trường hợp giải quyết" chỉ hiện khi thủ tục có từ 2 trường hợp, và Angular render nó SAU
  // ô Đơn vị thực hiện. Đọc ngay lúc hộp thoại vừa mở là tưởng "không có gì để hỏi" rồi bấm
  // Đồng ý với trường hợp mặc định → chờ ô này một nhịp trước khi đọc.
  const MAE_PROCESS_WAIT_MS = 2500;

  async function readMaeDialogOptions() {
    const form = maeForm();
    if (!form || form.id !== "ngSelectAgencyForm") return { ok: false, reason: "not-dialog" };
    await waitFor(() => {
      const process = matSelect("procedureProcess");
      return process && isVisible(process);
    }, MAE_PROCESS_WAIT_MS);
    const out = { ok: true };
    for (const [key, control] of [["agency", "agency"], ["process", "procedureProcess"]]) {
      const res = await readMatSelectOptions(control);
      if (res && res.options.length) out[key] = res;
    }
    // Hai ô ra CÙNG một danh sách = đọc lẫn panel → không gửi ô nơi xử lý (giữ nguyên trên cổng).
    if (out.agency && out.process
      && out.agency.options.join("\n") === out.process.options.join("\n")) {
      delete out.agency;
    }
    return out;
  }

  // Chọn ĐÚNG nhãn công dân đã chốt (BE gửi lại nguyên văn chữ đọc từ cổng).
  async function pickExactOption(control, label, what) {
    const want = fold(label);
    const sel = await waitFor(() => {
      const el = matSelect(control);
      return el && isVisible(el) ? el : null;
    }, 3000);
    if (!sel) return { ok: true, skipped: true };
    // Nhãn có thể đã bị cắt bớt phần đuôi trên đường đi (nhãn trường hợp của cổng rất dài) →
    // nhãn đủ dài thì chấp nhận khớp phần ĐẦU; nhãn ngắn vẫn phải khớp trọn để không nhầm dòng.
    const same = (text) => text === want || (want.length >= 60 && text.startsWith(want));
    if (same(matSelectValue(sel))) return { ok: true, kept: true };
    const res = await pickMatOption(sel, same, label);
    if (res.error) return { error: `${what}: ${res.error}` };
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

  async function fillMaeAgency({
    province, agency, ward, agencyLevel, variant, variantMatch, variantAvoid, agencyExact, processExact,
  }) {
    const form = await waitFor(maeForm, 6000);
    if (!form) return { error: "Không thấy form chọn cơ quan trên trang." };

    // Rẽ nhánh theo ID FORM chứ không dò DOM: hộp thoại Bộ Xây dựng (ngSelectAgencyForm) chỉ có
    // Đơn vị thực hiện + Trường hợp giải quyết. Dò "có ô Tỉnh không" sẽ rủi ro vì Angular render
    // chậm — trang MAE thật mà ô chưa kịp hiện thì bị bỏ qua im lặng, hỏng đường đang chạy tốt.
    if (form.id === "ngSelectAgencyForm") {
      // Đơn vị thực hiện đã được chọn từ bước "Chọn cơ quan thực hiện" trên DVCQG → giữ nguyên,
      // chỉ đụng vào khi backend gửi tên cơ quan cụ thể (nhãn đúng nguyên văn công dân đã chọn,
      // hoặc tên Sở để khớp chứa).
      if (fold(agencyExact)) {
        const unitRes = await pickExactOption("agency", agencyExact, "Đơn vị thực hiện");
        if (unitRes.error) return unitRes;
        await sleep(400); // đổi đơn vị có thể nạp lại danh sách trường hợp
      } else if (fold(agency)) {
        const unitSel = await waitFor(() => matSelect("agency"), 5000);
        if (unitSel && !matSelectValue(unitSel).includes(fold(agency))) {
          const res = await pickMatOption(unitSel, (text) => text.includes(fold(agency)), agency);
          if (res.error) return { error: `Đơn vị thực hiện: ${res.error}` };
        }
      }
      const processRes = fold(processExact)
        ? await pickExactOption("procedureProcess", processExact, "Trường hợp giải quyết")
        : await pickProcedureProcess(
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

    // 2a) Cấp XÃ: radio "Phường/Xã" + chọn đúng xã rồi Đồng ý. Hộp thoại này không có ô
    //     "Trường hợp giải quyết" nên dừng ở đây, không chạy tiếp nhánh Sở bên dưới.
    if (agencyLevel === "ward") {
      const levelRes = await clickLevelRadio("0");
      if (levelRes.error) return levelRes;
      const wardSel = await waitFor(() => matSelect("agency"), 5000);
      if (!wardSel) return { error: "Không thấy ô chọn Phường/Xã." };
      const wantWard = fold(ward);
      if (!wantWard) return { error: "Tài khoản chưa gắn phường/xã nên em chưa biết chọn ô nào." };
      if (!matSelectValue(wardSel).includes(wantWard)) {
        // Option ghi đủ "Phường Nghĩa Lộ"/"Xã An Thạnh"; tên từ tài khoản có thể thiếu tiền tố
        // → khớp hai chiều như ô Tỉnh.
        const res = await pickMatOption(
          wardSel,
          (text) => text === wantWard || text.includes(wantWard)
            || (text.length >= 4 && wantWard.includes(text)),
          ward,
          { timeout: 9000 },
        );
        if (res.error) return { error: `Phường/Xã: ${res.error}` };
      }
      const agreeWard = await waitFor(findAgreeButton, 4000);
      if (!agreeWard) return { error: 'Không thấy nút "Đồng ý và tiếp tục".' };
      clickLikeUser(agreeWard);
      return { ok: true, level: "ward", ward };
    }

    // 2) Radio "Sở/Ban ngành" (value="1").
    const radioRes = await clickLevelRadio("1");
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
      ward: msg.ward || "",
      agencyLevel: msg.agencyLevel || "",
      variant: msg.variant || "",
      variantMatch: msg.variantMatch || "",
      variantAvoid: msg.variantAvoid || "",
      agencyExact: msg.agencyExact || "",
      processExact: msg.processExact || "",
    })
      .then(sendResponse)
      .catch((e) => sendResponse({ error: String(e?.message || e) }));
    return true; // async
  });

  // Đọc danh sách lựa chọn của hộp thoại "Chọn trường hợp giải quyết" (gọi lúc gửi page_status).
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.action !== "readMaeDialogOptions") return;
    if (!maeForm()) return;
    readMaeDialogOptions()
      .then(sendResponse)
      .catch((e) => sendResponse({ ok: false, error: String(e?.message || e) }));
    return true; // async
  });
})();
