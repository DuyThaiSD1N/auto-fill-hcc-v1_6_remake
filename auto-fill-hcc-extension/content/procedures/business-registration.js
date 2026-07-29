// Thủ tục ĐĂNG KÝ KINH DOANH (đăng ký hộ KD 8 trang: fill-all, ngành nghề, copy-person, cascade địa chỉ).
// Procedure-specific — tách khỏi content.js. Namespace window.__HCC__.
(() => {
  const H = window.__HCC__ || (window.__HCC__ = {});
  const { sleep, norm, fieldCandidates, setNativeValue, waitFor, readAcctContact,
    fillFormStandard, findStandardInput, findStandardSelect, isPostbackAddressField } = H;

function foldBusinessPageText(value) {
  return norm(String(value || "")
    .replace(/Đ/g, "D")
    .replace(/đ/g, "d")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, ""));
}

const BUSINESS_PAGE_LABELS = {
  "hinh-thuc-dang-ky": "Hình thức đăng ký",
  "dia-chi": "Địa chỉ",
  "nganh-nghe-kinh-doanh": "Ngành nghề kinh doanh",
  "ten-ho-kinh-doanh": "Tên hộ kinh doanh",
  "chu-ho-kinh-doanh": "Thông tin về chủ hộ kinh doanh",
  "thong-tin-ve-von": "Thông tin về vốn",
  "thong-tin-ve-thue": "Thông tin về thuế",
  "nguoi-nop-ho-so": "Người nộp hồ sơ",
};

function currentBusinessPageLabel() {
  const sitemap = document.querySelector("#ctl00_LV4_SiteMapPath1")
    || document.querySelector('[id*="SiteMapPath"]');
  if (!sitemap) return "";
  const parts = Array.from(sitemap.querySelectorAll("span"))
    .map((node) => norm(node.textContent))
    .filter(Boolean);
  return parts[parts.length - 1] || norm(sitemap.textContent);
}

function findBusinessPageLink(label) {
  const wanted = foldBusinessPageText(label);
  if (!wanted) return null;
  const links = Array.from(document.querySelectorAll(".left-menu a, #ctl00_C_BLCtl_CtlList a"));
  return links.find((link) => foldBusinessPageText(link.textContent) === wanted) ||
    links.find((link) => {
      const text = foldBusinessPageText(link.textContent);
      return text && (text.includes(wanted) || wanted.includes(text));
    });
}

function detectBusinessPageKey() {
  const label = currentBusinessPageLabel();
  const wanted = foldBusinessPageText(label);
  if (!wanted) return { pageKey: null, label: "" };
  // So khớp theo độ trùng từ (token overlap) thay vì substring, vì breadcrumb có thể rút gọn
  // nhãn (vd "Thông tin vốn" trên breadcrumb vs "Thông tin về vốn" ở menu). Chọn trang trùng
  // nhiều từ nhất → phân biệt được vốn/thuế (đều có "thông tin").
  const wantedTokens = wanted.split(" ").filter(Boolean);
  let best = null;
  let bestScore = 0;
  for (const [key, lbl] of Object.entries(BUSINESS_PAGE_LABELS)) {
    const candSet = new Set(foldBusinessPageText(lbl).split(" ").filter(Boolean));
    const overlap = wantedTokens.filter((t) => candSet.has(t)).length;
    if (overlap > bestScore) {
      bestScore = overlap;
      best = key;
    }
  }
  const enough = bestScore >= 2 || (bestScore >= 1 && wantedTokens.length === 1);
  return { pageKey: enough ? best : null, label };
}

async function navigateBusinessRegistrationPage(pageKey, labelFromPopup) {
  const label = labelFromPopup || BUSINESS_PAGE_LABELS[pageKey] || "";
  if (!label) return { error: "Thiếu tên trang đăng ký kinh doanh." };

  const current = currentBusinessPageLabel();
  if (current && foldBusinessPageText(current).includes(foldBusinessPageText(label))) {
    return { ok: true, already: true, label };
  }

  const link = findBusinessPageLink(label);
  if (!link) {
    return { error: `Không tìm thấy menu trang "${label}". Hãy mở đúng hồ sơ đăng ký kinh doanh.` };
  }

  try {
    if (typeof link.scrollIntoView === "function") link.scrollIntoView({ block: "center" });
    link.click();
    await sleep(250);
    return { ok: true, navigating: true, label };
  } catch (e) {
    return { error: `Không mở được trang "${label}": ${e?.message || e}` };
  }
}

const FILLALL_KEY = "autofill_fillall_state";

function getFillAllState() {
  return new Promise((resolve) => {
    try {
      chrome.storage.local.get(FILLALL_KEY, (res) => {
        if (chrome.runtime.lastError) return resolve(null);
        resolve((res && res[FILLALL_KEY]) || null);
      });
    } catch (e) { resolve(null); }
  });
}

function setFillAllState(st) {
  return new Promise((resolve) => {
    try { chrome.storage.local.set({ [FILLALL_KEY]: st }, () => resolve()); }
    catch (e) { resolve(); }
  });
}

function clearFillAllState() {
  return new Promise((resolve) => {
    try { chrome.storage.local.remove(FILLALL_KEY, () => resolve()); }
    catch (e) { resolve(); }
  });
}

function findBusinessSaveButton() {
  const luu = Array.from(document.querySelectorAll('input[type="submit"]'))
    .filter((b) => norm(b.value) === "lưu");
  return luu.find((b) => /save/i.test(b.id) || /save/i.test(b.name || "") ||
    /\b(save-btn|default)\b/.test(b.className)) || luu[0] || null;
}

function injectMainWorld(code) {
  try {
    const s = document.createElement("script");
    s.textContent = code;
    (document.documentElement || document.head).appendChild(s);
    s.remove();
    return true;
  } catch (e) { return false; }
}

function ensureConfirmOverride() {
  if (window.__AF_CONFIRM_OVERRIDE__) return;
  window.__AF_CONFIRM_OVERRIDE__ = true;
  injectMainWorld("try{window.Confirm=function(){return true};window.confirm=function(){return true};}catch(e){}");
}

function doAspPostback(target, arg) {
  const et = document.getElementById("__EVENTTARGET");
  const ea = document.getElementById("__EVENTARGUMENT");
  const form = (et && et.form) || document.forms.namedItem("aspnetForm") || document.querySelector("form");
  if (form && et) {
    et.value = target;
    if (ea) ea.value = arg || "";
    console.log("[FillAll] submit postback ->", target);
    try { form.submit(); return true; } catch (e) { /* thử cách khác */ }
  }
  return injectMainWorld("try{__doPostBack(" + JSON.stringify(target) + "," + JSON.stringify(arg || "") + ");}catch(e){}");
}

function goToBusinessPageByKey(pageKey) {
  const label = BUSINESS_PAGE_LABELS[pageKey] || "";
  const link = findBusinessPageLink(label);
  if (!link) {
    console.warn("[FillAll] Không tìm thấy menu trang:", label);
    return false;
  }
  const href = link.getAttribute("href") || "";
  const m = href.match(/__doPostBack\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]\s*\)/);
  if (m) return doAspPostback(m[1], m[2]);
  try { link.click(); return true; } catch (e) { return false; }
}

function clickSaveDetectReload(btn) {
  return new Promise((resolve) => {
    let done = false;
    const onLeave = () => { if (!done) { done = true; resolve(true); } };
    window.addEventListener("beforeunload", onLeave, { once: true });
    window.addEventListener("pagehide", onLeave, { once: true });
    try { btn.click(); } catch (e) { /* ignore */ }
    setTimeout(() => {
      if (done) return;
      done = true;
      window.removeEventListener("beforeunload", onLeave);
      window.removeEventListener("pagehide", onLeave);
      resolve(false);
    }, 2600);
  });
}

function getNnCodes(st) {
  const f = ((st.pages && st.pages["nganh-nghe-kinh-doanh"]) || []).find((x) => x.name === "__businessLines");
  return f ? f.value : null; // {codes:[...], main:"..."}
}

function getAddedBusinessCodes() {
  const codes = [];
  const rows = Array.from(document.querySelectorAll("#ctl00_C_CtlList tr"));
  for (const r of rows) {
    for (const td of r.querySelectorAll("td")) {
      const t = (td.textContent || "").trim();
      if (/^\d{3,6}$/.test(t)) { codes.push(t); break; }
    }
  }
  return codes;
}

function findBusinessRowByCode(code) {
  const wanted = String(code).trim();
  const rows = Array.from(document.querySelectorAll("#ctl00_C_CtlList tr"));
  return rows.find((r) => Array.from(r.querySelectorAll("td")).some((td) => (td.textContent || "").trim() === wanted)) || null;
}

function isBusinessMainSet(code) {
  const row = findBusinessRowByCode(code);
  const radio = row && row.querySelector('input[name="ismain"]');
  return !!(radio && radio.checked);
}

function addOneBusinessCode(code) {
  const input = findStandardInput(["ctl00$C$newBusinessLineCode"]);
  const hidden = findStandardInput(["ctl00$C$newBusinessLineCodeVal"]);
  const addBtn = document.querySelector('input[name="ctl00$C$BtnAddBl"], #ctl00_C_BtnAddBl');
  if (!input || !addBtn) {
    console.warn("[FillAll] Ngành nghề: không thấy ô mã / nút Thêm");
    return Promise.resolve(false);
  }
  setNativeValue(input, code, { typing: true, commit: true });
  if (hidden) setNativeValue(hidden, code, { typing: false, commit: true });
  console.log("[FillAll] thêm mã ngành:", code);
  return clickSaveDetectReload(addBtn);
}

function setBusinessMainAndUpdate(code) {
  const row = findBusinessRowByCode(code);
  const radio = row && row.querySelector('input[name="ismain"]');
  const upd = document.querySelector('input[name="ctl00$C$btnUpdateMain"], #ctl00_C_btnUpdateMain');
  if (!radio || !upd) {
    console.warn("[FillAll] Ngành nghề: không thấy radio chính / nút Cập nhật chính cho mã", code);
    return Promise.resolve(false);
  }
  radio.checked = true;
  radio.dispatchEvent(new Event("click", { bubbles: true }));
  radio.dispatchEvent(new Event("change", { bubbles: true }));
  console.log("[FillAll] cập nhật ngành chính:", code);
  return clickSaveDetectReload(upd);
}

async function handleNganhNghePage(st) {
  const nn = getNnCodes(st);

  // Không có mã VSIC → điền ô ngành nghề dạng text tự do (nếu có) rồi sang trang kế.
  if (!nn || !Array.isArray(nn.codes) || !nn.codes.length) {
    const fields = ((st.pages && st.pages["nganh-nghe-kinh-doanh"]) || []).filter((f) => f.name !== "__businessLines");
    if (fields.length) { try { await fillFormStandard(fields); } catch (e) { /* ignore */ } }
    await sleep(400);
    return void advanceFillAll(st);
  }

  const skip = st.nnSkip || [];
  const added = getAddedBusinessCodes();
  const remaining = nn.codes.filter((c) => !added.includes(c) && !skip.includes(c));
  console.log("[FillAll] ngành nghề — đã có:", added, "| còn cần:", remaining);

  // Chặn lặp vô hạn: quá nhiều lần thêm thì dừng.
  if ((st.nnAdds || 0) > nn.codes.length + 5) {
    console.warn("[FillAll] Ngành nghề: quá số lần thêm cho phép, chuyển sang cập nhật chính.");
  } else if (remaining.length) {
    const code = remaining[0];
    st.nnAdds = (st.nnAdds || 0) + 1;
    await setFillAllState(st);
    const reloaded = await addOneBusinessCode(code);
    if (reloaded) return;           // postback → resume xử lý mã kế
    st.nnSkip = [...skip, code];    // không thêm được → bỏ qua mã này
    await setFillAllState(st);
    return void stepFillAll();      // thử mã tiếp theo ngay
  }

  // Đã thêm hết → set ngành chính (1 lần).
  if (nn.main && !st.nnMainDone && !isBusinessMainSet(nn.main)) {
    st.nnMainDone = true;
    await setFillAllState(st);
    const reloaded = await setBusinessMainAndUpdate(nn.main);
    if (reloaded) return;
  }
  return void advanceFillAll(st);
}

const COPY_PERSON_CFG = {
  "nguoi-nop-ho-so": {
    copyBtn: 'input[name="ctl00$C$btnIS_SIGNER"], #ctl00_C_btnIS_SIGNER',
    nameFilled: () => !!((document.getElementById("ctl00_C_PERSCtl_FULL_NAMEFld_Vw") || {}).textContent || "").trim(),
    addrMatch: /\$C\$PERSCtl\$ADDRCCtl/,
    captureContact: true,
    readPhone: () => readAcctContact("ctl00_C_PERSCtl_PHONEFld"),
    readEmail: () => readAcctContact("ctl00_C_PERSCtl_EMAILFld"),
  },
  "chu-ho-kinh-doanh": {
    copyBtn: 'input[name="ctl00$C$OWN_PCtl$btnIS_SIGNER"], #ctl00_C_OWN_PCtl_btnIS_SIGNER',
    // Ô họ tên chủ hộ là INPUT (disabled) chứ không phải span _Vw.
    nameFilled: () => !!((document.getElementById("ctl00_C_OWN_PCtl_PERSCtl_FULL_NAMEFld") || {}).value || "").trim(),
    addrMatch: /OWN_PCtl\$PERSCtl\$ADDRCCtl/,
    captureContact: false,
  },
};

async function handleCopyPersonPage(st, targetKey) {
  ensureConfirmOverride();
  const cfg = COPY_PERSON_CFG[targetKey];
  const fields = (st.pages && st.pages[targetKey]) || [];

  // 1. Điền trường CẤU TRÚC (không phải địa chỉ, không phải thông tin cá nhân/liên hệ do copy điền),
  //    vd radio loại chủ thể (OWNER_TYPE) / loại người nộp (PERS_SUBGroup) — 1 lần.
  if (st.filledStep !== st.step) {
    st.filledStep = st.step;
    await setFillAllState(st);
    const structural = fields.filter((f) =>
      !cfg.addrMatch.test(f.name || "") &&
      !/FULL_NAME|GENDER|DATE_OF_BIRTH|PERS_DOC_NO|PHONE|FAX|EMAIL|URL/i.test(f.name || "")
    );
    if (structural.length) { try { await fillFormStandard(structural); } catch (e) { /* ignore */ } }
    await sleep(300);
  }

  // "Person đã sẵn": có HỌ TÊN; với trang cần bắt liên hệ thì PHẢI có sđt HOẶC email (cổng có thể tự
  // nạp tên nhưng sđt/email chỉ có SAU khi bấm Sao chép → không được chỉ xét tên).
  const personReady = () => cfg.nameFilled() && (!cfg.captureContact || cfg.readPhone() || cfg.readEmail());

  // 2. Bấm "Sao chép thông tin đăng ký tài khoản" cho tới khi person sẵn (nút trong UpdatePanel → AJAX → CHỜ).
  if (!personReady() && (st.copyTries || 0) < 3) {
    const copyBtn = document.querySelector(cfg.copyBtn);
    if (copyBtn) {
      st.copyTries = (st.copyTries || 0) + 1;
      await setFillAllState(st);
      console.log("[FillAll]", targetKey, "— bấm Sao chép thông tin đăng ký tài khoản");
      try { copyBtn.click(); } catch (e) { /* ignore */ }
      const ok = await waitFor(personReady, 7000, 250);
      if (!ok) return; // đang reload / copy chưa xong → xử lý lần kế
    }
  }

  // 2b. (Người nộp) bắt SĐT + EMAIL tài khoản — CHỈ đánh dấu đã bắt KHI THỰC SỰ CÓ giá trị.
  if (cfg.captureContact && !st.acctCaptured) {
    const ph = cfg.readPhone();
    const em = cfg.readEmail();
    if (ph || em) {
      st.acctPhone = ph;
      st.acctEmail = em;
      st.acctCaptured = true;
      await setFillAllState(st);
      console.log("[FillAll] bắt từ tài khoản — sđt:", ph, "| email:", em);
    } else {
      console.warn("[FillAll] người nộp: chưa thấy sđt/email tài khoản (copy chưa nạp?)");
    }
  }

  // 3. Điền ĐỊA CHỈ từ backend — cascade inline (quốc gia→tỉnh→xã→số nhà).
  const addrFields = fields.filter((f) => cfg.addrMatch.test(f.name || ""));
  try { await fillAddressCascade(addrFields); } catch (e) { /* ignore */ }

  // 4. Lưu.
  const saveBtn = findBusinessSaveButton();
  if (!saveBtn || saveBtn.disabled) return void advanceFillAll(st);
  st.phase = "saving";
  await setFillAllState(st);
  const reloaded = await clickSaveDetectReload(saveBtn);
  if (reloaded) return;
  return void advanceFillAll(st);
}

function applyAccountContact(fields, st) {
  if (!st.acctPhone && !st.acctEmail) return fields;
  return fields.map((f) => {
    const nm = f.name || "";
    if (st.acctPhone && /PHONE/i.test(nm)) return { ...f, value: st.acctPhone };
    if (st.acctEmail && /EMAIL/i.test(nm)) return { ...f, value: st.acctEmail };
    return f;
  });
}

function areaFold(s) {
  return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/gi, "d")
    .toLowerCase().replace(/\s+/g, " ").trim()
    .replace(/^(phuong|xa|thi tran|tinh|thanh pho|tp)\s+/, "");
}

function areaSelectedText(sel) {
  const opt = sel && sel.selectedOptions && sel.selectedOptions[0];
  return opt ? opt.textContent : "";
}

function areaFindOption(sel, target) {
  const t = areaFold(target);
  if (!t) return null;
  const opts = Array.from(sel.options).filter((o) => o.value);
  return opts.find((o) => areaFold(o.textContent) === t)
    || (t.length > 2 ? opts.find((o) => areaFold(o.textContent).includes(t)) : null);
}

function areaIsAt(sel, target) {
  return !!target && areaFold(areaSelectedText(sel)) === areaFold(target);
}

function areaChoose(sel, target) {
  const opt = areaFindOption(sel, target);
  if (!opt) return false;
  sel.value = opt.value;
  sel.dispatchEvent(new Event("input", { bubbles: true }));
  sel.dispatchEvent(new Event("change", { bubbles: true })); // → onchange __doPostBack
  return true;
}

async function fillAddressCascade(fields) {
  const selInfo = (key) => {
    const f = fields.find((x) => new RegExp(key).test(x.name || ""));
    return f && f.value ? { f, target: String(f.value) } : null;
  };
  const chooseAndWait = async (info, waitReady) => {
    if (!info) return;
    const el = findStandardSelect(fieldCandidates(info.f));
    if (!el || areaIsAt(el, info.target)) return;
    if (!areaFindOption(el, info.target)) { console.warn("[FillAll] địa chỉ: chưa có option", info.target); return; }
    areaChoose(el, info.target); // dispatch change → onchange __doPostBack (AJAX partial)
    console.log("[FillAll] địa chỉ chọn:", info.target);
    if (waitReady) await waitFor(waitReady, 8000, 250);
    else await sleep(900);
  };

  const country = selInfo("COUNTRY_IDFld");
  const city = selInfo("CITY_IDFld");
  const ward = selInfo("WARD_IDFld");

  await chooseAndWait(country);
  // Chọn tỉnh xong → CHỜ danh sách xã nạp lại đến khi có option đích.
  await chooseAndWait(city, () => {
    if (!ward) return true;
    const w = findStandardSelect(fieldCandidates(ward.f));
    return w && !!areaFindOption(w, ward.target);
  });
  await chooseAndWait(ward);

  // Số nhà: set value KHÔNG kích onchange (tránh thêm 1 postback thừa); nút Lưu sẽ submit giá trị này.
  const sf = fields.find((x) => /STREET_NUMBER/.test(x.name || ""));
  if (sf && sf.value) {
    const el = findStandardInput(fieldCandidates(sf));
    if (el && norm(el.value) !== norm(String(sf.value))) {
      setNativeValue(el, sf.value, { typing: false, change: false, commit: false });
      console.log("[FillAll] địa chỉ số nhà:", sf.value);
    }
  }
}

async function handleAddressCascadePage(st, targetKey) {
  ensureConfirmOverride();
  const fields = applyAccountContact((st.pages && st.pages[targetKey]) || [], st);

  // 1. Điền các trường KHÔNG postback (phone/email/fax/website/radio...) 1 lần.
  if (st.filledStep !== st.step) {
    st.filledStep = st.step;
    await setFillAllState(st);
    const nonAddr = fields.filter((f) => !isPostbackAddressField(f));
    if (nonAddr.length) { try { await fillFormStandard(nonAddr); } catch (e) { /* ignore */ } }
  }

  // 2. Cascade địa chỉ (inline). Nếu là full-postback thì reload sẽ cắt ngang → resume chạy tiếp phần còn lại.
  try { await fillAddressCascade(fields.filter((f) => isPostbackAddressField(f))); } catch (e) { /* ignore */ }

  // 3. Lưu.
  const saveBtn = findBusinessSaveButton();
  if (!saveBtn || saveBtn.disabled) return void advanceFillAll(st);
  st.phase = "saving";
  await setFillAllState(st);
  const reloaded = await clickSaveDetectReload(saveBtn);
  if (reloaded) return;
  return void advanceFillAll(st);
}

// Điền xong 8 trang → nếu popup gửi kèm kế hoạch đính kèm (nút "Quét nhập thông tin và đính kèm")
// thì TỰ CHẠY TIẾP state machine đính kèm; không thì kết thúc.
async function finishFillAllThenAttach(st) {
  const payload = st && st.attachPayload;
  await clearFillAllState();
  if (payload && Array.isArray(payload.files) && payload.files.length
      && Array.isArray(payload.attachments) && payload.attachments.length
      && typeof H.startAttachAllBusiness === "function") {
    H.setRunProgressText("✓ Đã điền xong 8 trang. Bắt đầu đính kèm hồ sơ…\n(đừng thao tác tới khi xong)");
    await H.startAttachAllBusiness(payload.files, payload.attachments);
    setTimeout(H.stepAttachAll, 400);
    return;
  }
  H.endFillAllUI("✓ Đã điền xong 8 trang. Vui lòng rà soát rồi bấm Nộp.");
}

async function advanceFillAll(st) {
  st.step += 1;
  st.retries = 0; st.phase = "fill"; st.filledStep = -1; st.navCount = 0;
  st.nnAdds = 0; st.nnSkip = []; st.nnMainDone = false; st.copyTries = 0;
  await setFillAllState(st);
  if (st.step >= st.order.length) {
    return void finishFillAllThenAttach(st);
  }
  goToBusinessPageByKey(st.order[st.step]);
}

async function stepFillAll() {
  const st = await getFillAllState();
  if (!st || !Array.isArray(st.order)) return;
  const order = st.order;

  const finish = async () => { await finishFillAllThenAttach(st); };

  if (st.step >= order.length) return finish();
  const targetKey = order[st.step];
  const _det = detectBusinessPageKey();
  console.log("[FillAll] step", st.step, "phase", st.phase, "target", targetKey, "onPage", _det.pageKey, `(${_det.label})`);
  H.setFillAllProgress(st.step + 1, order.length, BUSINESS_PAGE_LABELS[targetKey] || targetKey);

  // Vừa reload sau khi bấm Lưu → coi như đã lưu → sang trang kế.
  if (st.phase === "saving") {
    return void advanceFillAll(st);
  }

  // Chưa đúng trang mục tiêu → điều hướng tới (postback reload). Có chặn vòng lặp: quá 3 lần không
  // tới được trang thì bỏ qua trang đó (tránh kẹt vô hạn khi breadcrumb không nhận diện được).
  const { pageKey } = detectBusinessPageKey();
  if (pageKey !== targetKey) {
    st.navCount = (st.navStep === st.step ? (st.navCount || 0) : 0) + 1;
    st.navStep = st.step;
    if (st.navCount > 3) return void advanceFillAll(st); // không tới được → bỏ qua trang này
    await setFillAllState(st);
    return void goToBusinessPageByKey(targetKey);
  }

  ensureConfirmOverride();

  // Trang NGÀNH NGHỀ: xử lý riêng (thêm lần lượt mọi mã + set ngành chính), KHÔNG dùng fill/save chung.
  if (targetKey === "nganh-nghe-kinh-doanh") {
    return void handleNganhNghePage(st);
  }

  // Trang có nút "Sao chép thông tin đăng ký tài khoản" (Người nộp, Chủ hộ): copy điền tên+liên hệ,
  // ta chỉ điền địa chỉ từ backend.
  if (targetKey === "nguoi-nop-ho-so" || targetKey === "chu-ho-kinh-doanh") {
    return void handleCopyPersonPage(st, targetKey);
  }

  // Trang Địa chỉ trụ sở: cascade địa chỉ (quốc gia→tỉnh→xã→số nhà) + phone/email/website.
  if (targetKey === "dia-chi") {
    return void handleAddressCascadePage(st, targetKey);
  }

  // Điền field trang này (chỉ 1 lần/step: mid-fill có thể postback như trang ngành nghề).
  if (st.filledStep !== st.step) {
    st.filledStep = st.step;
    await setFillAllState(st); // persist TRƯỚC khi fill để postback giữa chừng không fill lại
    const fields = applyAccountContact((st.pages && st.pages[targetKey]) || [], st);
    if (fields.length) {
      try { await fillFormStandard(fields); } catch (e) { /* ignore */ }
    }
    await sleep(800); // để form "dirty" + cascade địa danh xong → nút Lưu bật
  }

  const saveBtn = findBusinessSaveButton();
  if (!saveBtn || saveBtn.disabled) return void advanceFillAll(st); // không có gì để lưu → sang trang kế

  st.phase = "saving";
  await setFillAllState(st);
  const reloaded = await clickSaveDetectReload(saveBtn);
  if (reloaded) return; // đang reload → bước "saving" xử lý ở lần load kế

  // Không reload = bị validation chặn → retry tối đa 2 lần rồi sang trang kế.
  st.retries = (st.retries || 0) + 1;
  st.phase = "fill";
  if (st.retries < 2) {
    st.filledStep = -1; // cho phép fill lại
    await setFillAllState(st);
    return void stepFillAll();
  }
  return void advanceFillAll(st);
}

// ===================== ĐÍNH KÈM HỘ KINH DOANH (cổng HkdOnline, nhiều postback) =====================
// Luồng: (declare) mở modal cài đặt → khai báo loại tài liệu → đóng modal → click mục đầu (postback)
//        (upload) trang tải: nhét TẤT CẢ file vào 1 input → "Tải lên" (postback)
//        (classify) gán "Loại đính kèm" cho từng dòng theo phân loại BE → "Lưu" (postback) → xong.
// State resume qua chrome.storage (autofill_attachall_state), giữ dataUrl file để nhét ở pha upload.
const ATTACH_KEY = "autofill_attachall_state";

// category cổng → giá trị option ở modal (#attId) và ở "Loại đính kèm" (droptypleAttach) + nhãn hiển thị.
const ATTACH_TYPE = {
  BUSREGFRM: { attId: "1_BUSREGFRM", droptyple: "BUSREGFRM", label: "Giấy đề nghị đăng ký hộ kinh doanh" },
  CPID: { attId: "2_CPID", droptyple: "CPID", label: "Bản sao giấy tờ pháp lý của cá nhân" },
  OTHERS: { attId: "20_OTHERS", droptyple: "OTHERS", label: "Khác" },
};

function getAttachAllState() {
  return new Promise((resolve) => {
    try {
      chrome.storage.local.get(ATTACH_KEY, (res) => {
        if (chrome.runtime.lastError) return resolve(null);
        resolve((res && res[ATTACH_KEY]) || null);
      });
    } catch (e) { resolve(null); }
  });
}
function setAttachAllState(st) {
  return new Promise((resolve) => {
    try { chrome.storage.local.set({ [ATTACH_KEY]: st }, () => resolve()); }
    catch (e) { resolve(); }
  });
}
function clearAttachAllState() {
  return new Promise((resolve) => {
    try { chrome.storage.local.remove(ATTACH_KEY, () => resolve()); }
    catch (e) { resolve(); }
  });
}

function foldName(name) {
  return foldBusinessPageText(String(name || "").replace(/\.[^.]+$/, ""));
}

function attachProgressText(st) {
  const label = {
    declare: "khai báo loại tài liệu",
    upload: "tải file lên",
    classify: "gán loại & lưu",
    done: "hoàn tất",
  }[st.phase] || "xử lý";
  return `Đang đính kèm hồ sơ — ${label}\n(đừng thao tác tới khi xong)`;
}

// Khởi tạo phiên (gọi từ content handler). plan[i] khớp files[i] theo attachment.fileIndex.
async function startAttachAllBusiness(files, attachments) {
  const plan = files.map((f, i) => {
    const a = (attachments || []).find((x) => x && x.fileIndex === i) || {};
    const category = ATTACH_TYPE[a.category] ? a.category : "OTHERS"; // BUSREGFRM | CPID | OTHERS
    return { fileName: f.name, category, documentName: a.documentName || f.name };
  });
  // Các loại PHÂN BIỆT cần khai báo trong modal (giữ thứ tự xuất hiện) + số tài liệu mỗi loại.
  const declareTypes = [];
  const declareCounts = {};
  for (const p of plan) {
    if (!declareTypes.includes(p.category)) declareTypes.push(p.category);
    declareCounts[p.category] = (declareCounts[p.category] || 0) + 1;
  }
  const st = { files, plan, declareTypes, declareCounts, declared: [], phase: "declare", uploadTries: 0 };
  await setAttachAllState(st);
  return { ok: true, started: true };
}

// ---- helpers DOM ----
function onUploadPage() {
  return !!document.getElementById("ctl00_C_FileUploadCtl");
}
// Danh sách LOẠI đã khai, hiện dưới "Văn bản đính kèm" trong container #ctl00_C_BLCtl_CtlAttList
// (KHÁC #ctl00_C_BLCtl_CtlList = menu 8 trang). Bấm 1 item bất kỳ → điều hướng tới trang tải file.
function attachTypeLinks() {
  return Array.from(document.querySelectorAll('#ctl00_C_BLCtl_CtlAttList a[id*="LnkEdit"]'))
    .filter((a) => /__doPostBack/.test(a.getAttribute("href") || ""));
}
function clickAttachTypeLink(link) {
  const href = link.getAttribute("href") || "";
  const m = href.match(/__doPostBack\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]\s*\)/);
  if (m) return doAspPostback(m[1], m[2]);
  try { link.click(); return true; } catch (e) { return false; }
}
function uploadedRows() {
  return Array.from(document.querySelectorAll("#ctl00_C_CtlList tr"))
    .filter((tr) => tr.querySelector('select[id*="droptypleAttach"]'));
}
function declaredLabelsFold() {
  // CHỈ đọc bảng loại đã khai trong modal (#tblAtt). KHÔNG đọc a[id*="LnkEdit"] — đó là MENU 8 trang
  // bên trái (Hình thức đăng ký, Địa chỉ...), không phải loại tài liệu đã khai → tránh nhận nhầm.
  const out = [];
  document.querySelectorAll('#tblAtt tbody tr').forEach((el) => {
    const t = foldBusinessPageText(el.textContent);
    if (t) out.push(t);
  });
  return out;
}
// Đặt "Số tài liệu" trong modal khai loại (validateItemCount của cổng yêu cầu số ≥ 1).
function setAttachItemCount(n) {
  const inp = document.getElementById("itemCount")?.querySelector("input");
  if (inp) setNativeValue(inp, String(n || 1), { typing: false, commit: true });
}
function hasDeclared(labelFold) {
  return declaredLabelsFold().some((x) => x.includes(labelFold));
}
function chooseOption(sel, value, labelFold) {
  const opts = Array.from(sel.options);
  const opt = opts.find((o) => o.value === value)
    || (labelFold ? opts.find((o) => foldBusinessPageText(o.textContent) === labelFold) : null)
    || (labelFold ? opts.find((o) => foldBusinessPageText(o.textContent).includes(labelFold)) : null);
  if (!opt) return false;
  sel.value = opt.value;
  sel.dispatchEvent(new Event("input", { bubbles: true }));
  sel.dispatchEvent(new Event("change", { bubbles: true }));
  return true;
}
async function ensureAttachModalOpen() {
  let sel = document.getElementById("attId");
  if (sel && H.isVisible(sel)) return sel;
  // Icon ⚙ mở modal qua handler jQuery của cổng. click() của content-script LÀ event DOM thật nên
  // handler jQuery vẫn nhận (CSP chỉ chặn INLINE script — không chặn dispatch event; KHÔNG inject nữa).
  const icon = document.getElementById("ctl00_C_BLCtl_ImgAttachmentSettings")
    || document.querySelector("img.settings, .right.settings, .settings");
  if (icon) { try { icon.click(); } catch (e) { /* ignore */ } }
  const ok = await waitFor(() => { const s = document.getElementById("attId"); return s && H.isVisible(s); }, 6000, 250);
  return ok ? document.getElementById("attId") : null; // null = không mở được (để caller xử lý)
}
function closeAttachModal() {
  const dlg = document.getElementById("attachment")?.closest(".ui-dialog");
  const x = dlg?.querySelector(".ui-dialog-titlebar-close");
  if (x) { try { x.click(); return; } catch (e) { /* fallthrough */ } }
  injectMainWorld("try{(window.jQuery||window.$)('#attachment').dialog('close');}catch(e){}");
}

// ---- các pha ----
function isTypeDeclared(st, cat) {
  return (st.declared || []).includes(cat) || hasDeclared(foldBusinessPageText(ATTACH_TYPE[cat].label));
}

async function handleDeclarePhase(st) {
  st.declared = st.declared || [];
  const missing = st.declareTypes.filter((c) => !isTypeDeclared(st, c));
  if (missing.length) {
    const sel = await ensureAttachModalOpen();
    if (!sel) {
      st.declareTries = (st.declareTries || 0) + 1;
      await setAttachAllState(st);
      if (st.declareTries > 3) {
        return void failAttachAll("Không mở được cửa sổ khai báo loại tài liệu (icon ⚙ cạnh 'Văn bản đính kèm').");
      }
      return void setTimeout(stepAttachAll, 800);
    }
    for (const cat of missing) {
      const t = ATTACH_TYPE[cat];
      if (!chooseOption(sel, t.attId, foldBusinessPageText(t.label))) continue;
      // "Số tài liệu" phải là số ≥ 1 (validateItemCount của cổng) → set = số file thuộc loại này.
      setAttachItemCount((st.declareCounts && st.declareCounts[cat]) || 1);
      await waitFor(() => { const b = document.getElementById("AddAtt"); return b && !b.disabled; }, 5000, 200);
      const addBtn = document.getElementById("AddAtt");
      if (!addBtn) continue;
      if (addBtn.disabled) { try { addBtn.removeAttribute("disabled"); } catch (e) { /* ignore */ } }
      try { addBtn.click(); } catch (e) { /* ignore */ }
      // Khai báo lưu SERVER (AJAX SaveAttachment) → nhớ vào state (không đọc DOM #tblAtt sau khi
      // đóng modal / đổi trang được nữa).
      const ok = await waitFor(() => hasDeclared(foldBusinessPageText(t.label)), 6000, 300);
      if (ok && !st.declared.includes(cat)) st.declared.push(cat);
      await sleep(300);
    }
    closeAttachModal();
    await setAttachAllState(st);
    await sleep(600);
    // Sau khi khai, danh sách loại (CtlAttList) hiện dưới "Văn bản đính kèm" → chờ render để điều hướng.
    await waitFor(() => attachTypeLinks().length > 0 || onUploadPage(), 5000, 300);
  }

  // Đã khai loại xong → sang pha tải file. stepAttachAll tự điều hướng (bấm 1 item CtlAttList) sang
  // trang có ô Tải lên rồi upload/gán loại.
  st.phase = "upload";
  await setAttachAllState(st);
  return void setTimeout(stepAttachAll, 300);
}

async function handleUploadPhase(st) {
  // Đã có dòng file (postback "Tải lên" xong) → chuyển sang gán loại.
  const existing = uploadedRows();
  if (existing.length) return void handleClassifyPhase(st, existing);

  const input = document.getElementById("ctl00_C_FileUploadCtl");
  const btn = document.getElementById("ctl00_C_BtnSaveNoTyple");
  if (!input || !btn) return; // trang chưa sẵn
  st.uploadTries = (st.uploadTries || 0) + 1;
  if (st.uploadTries > 3) return void failAttachAll("Tải file lên thất bại (thử lại quá số lần).");
  st.uploaded = true; // sau postback "Tải lên" → dòng file hiện ra → pha classify
  await setAttachAllState(st);
  const files = (st.files || []).map((f) => H.dataUrlToFile(f, ""));
  H.setFilesOnInput(input, files, { allowMultiple: true, assumeConsumed: true });
  await sleep(500);
  const reloaded = await clickSaveDetectReload(btn); // "Tải lên" → postback
  if (reloaded) return; // reload xong → dòng file hiện ra → pha classify
  return void stepAttachAll();
}

function categoryForFileName(st, folded) {
  if (!folded) return null;
  const p = (st.plan || []).find((x) => foldName(x.fileName) === folded);
  if (p) return p.category;
  const p2 = (st.plan || []).find((x) => folded.includes(foldName(x.fileName)) || foldName(x.fileName).includes(folded));
  return p2 ? p2.category : null;
}

async function handleClassifyPhase(st, rows) {
  if (st.phase !== "classify") { st.phase = "classify"; await setAttachAllState(st); H.setRunProgressText(attachProgressText(st)); }
  const plan = st.plan || [];
  const sameCount = rows.length === plan.length; // dòng cùng thứ tự file đã tải
  rows.forEach((row, i) => {
    const sel = row.querySelector('select[id*="droptypleAttach"]');
    if (!sel) return;
    // Ưu tiên map theo THỨ TỰ (tên file cổng hiển thị có thể lệch khoảng trắng "đa ng ky..." → khớp tên
    // dễ sai). Chỉ dùng tên làm fallback khi số dòng ≠ số file.
    const nameEl = row.querySelector('span[id*="Label22"]') || row.querySelector("td:nth-child(2)");
    const byName = categoryForFileName(st, foldName(nameEl?.textContent || ""));
    const category = sameCount ? (plan[i] && plan[i].category) || byName : byName;
    const t = ATTACH_TYPE[category] || ATTACH_TYPE.OTHERS;
    console.log("[Attach] classify row", i, nameEl?.textContent?.trim(), "→", t.droptyple);
    chooseOption(sel, t.droptyple, foldBusinessPageText(t.label));
  });
  await sleep(400);
  const saveBtn = document.getElementById("ctl00_C_BtnSave");
  if (!saveBtn) return void finishAttachAll();
  // Nút "Lưu" mặc định disabled → bật lại sau khi đã gán loại (đổi droptyple làm form "dirty").
  if (saveBtn.disabled) { try { saveBtn.removeAttribute("disabled"); } catch (e) { /* ignore */ } }
  st.phase = "done";
  await setAttachAllState(st);
  const reloaded = await clickSaveDetectReload(saveBtn); // "Lưu" → postback
  if (reloaded) return; // done xử lý ở lần load kế
  return void finishAttachAll();
}

async function finishAttachAll() {
  await clearAttachAllState();
  H.endFillAllUI("✓ Đã đính kèm xong hồ sơ. Vui lòng rà soát rồi bấm Nộp.");
}
async function failAttachAll(msg) {
  await clearAttachAllState();
  H.endFillAllUI("⚠ " + msg);
}

async function stepAttachAll() {
  const st = await getAttachAllState();
  if (!st) return;
  H.setRunProgressText(attachProgressText(st));
  ensureConfirmOverride();

  if (st.phase === "done") return void finishAttachAll();

  st.declared = st.declared || [];
  const declaredAll = st.declareTypes.every((c) => isTypeDeclared(st, c));
  console.log("[Attach] phase", st.phase, "| declared", st.declared, "declaredAll", declaredAll,
    "| hasGear", !!document.getElementById("ctl00_C_BLCtl_ImgAttachmentSettings"),
    "| onUploadPage", onUploadPage(), "| rows", uploadedRows().length);

  // B1 — KHAI LOẠI (modal ⚙): icon `.settings` là sidebar, có ở MỌI trang → khai được ở bất cứ đâu.
  // Chưa khai đủ + trang có icon ⚙ → mở modal khai luôn (KHÔNG cần ở trang có ô tải file).
  if (!declaredAll && (document.getElementById("ctl00_C_BLCtl_ImgAttachmentSettings")
      || document.querySelector(".settings"))) {
    return void handleDeclarePhase(st);
  }

  // B2 — ĐIỀU HƯỚNG tới trang có ô tải file (#ctl00_C_FileUploadCtl). Sau khi khai loại, cổng hiện
  // danh sách loại trong #ctl00_C_BLCtl_CtlAttList → bấm 1 item bất kỳ sẽ ra trang tải file.
  if (!onUploadPage()) {
    const links = attachTypeLinks();
    if (links.length) {
      st.navTries = (st.navTries || 0) + 1;
      await setAttachAllState(st);
      if (st.navTries > 5) {
        return void failAttachAll("Không mở được trang tải file sau khi khai loại. Hãy bấm 1 mục trong danh sách 'Văn bản đính kèm'.");
      }
      H.setRunProgressText("Mở trang tải văn bản đính kèm…\n(đừng thao tác tới khi xong)");
      clickAttachTypeLink(links[0]); // postback → trang tải file (ATTACHMENTS.aspx)
      return;
    }
    // Chưa thấy danh sách loại: nếu đã khai (state) thì reload để cổng dựng CtlAttList (khai đã lưu server).
    if (declaredAll) {
      st.attListReloads = (st.attListReloads || 0) + 1;
      await setAttachAllState(st);
      if (st.attListReloads <= 2) { location.reload(); return; }
      H.setRunProgressText("✓ Đã khai loại. Hãy bấm 1 mục trong danh sách 'Văn bản đính kèm' để mở trang tải file.");
      return;
    }
    await setAttachAllState(st);
    H.setRunProgressText("Đang khai loại tài liệu…");
    return;
  }
  st.navTries = 0;
  st.attListReloads = 0;
  await setAttachAllState(st);

  const rows = uploadedRows();
  // Đã có dòng file (đã tải lên) → gán loại & lưu.
  if (rows.length && (st.phase === "classify" || st.uploaded)) {
    return void handleClassifyPhase(st, rows);
  }
  // Đã khai xong, đang ở trang có ô file → tải file lên.
  return void handleUploadPhase(st);
}

  H.detectBusinessPageKey = detectBusinessPageKey;
  H.getFillAllState = getFillAllState;
  H.navigateBusinessRegistrationPage = navigateBusinessRegistrationPage;
  H.setFillAllState = setFillAllState;
  H.stepFillAll = stepFillAll;
  H.startAttachAllBusiness = startAttachAllBusiness;
  H.stepAttachAll = stepAttachAll;
  H.getAttachAllState = getAttachAllState;
})();