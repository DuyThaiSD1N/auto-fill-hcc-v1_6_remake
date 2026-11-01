// Cổng Bắc Ninh (dichvucong.bacninh.gov.vn, Liferay) — phần trang CHUNG của luồng 4 tab do BE điều phối
// (auto-fill-hcc-backend chat/bac_ninh.py):
//   - tab đang mở (bnTab 1..4: Chọn cơ quan tiếp nhận / Nhập đơn đăng ký / Tải thành phần hồ sơ / Thông tin đăng ký
//     nhận kết quả) cho page_status;
//   - tab đầu: đọc / chọn ô "Cơ quan tiếp nhận, giải quyết hồ sơ" (select2 donViTiepNhanId);
//   - chuyển tab bằng hàm của cổng (content/bacninh/tabs-main.js, MAIN world) qua H.activateBacNinhTab;
//   - tab nhận kết quả: đọc / chọn radio "noiNhanKetQua" theo value của cổng, kèm điểm tiếp nhận (nếu cổng hiện) hoặc
//     hai ô tích "Gửi hồ sơ qua bưu điện" / "Nhận kết quả qua bưu điện" (khi chọn bưu chính);
//   - bấm "Nộp hồ sơ" rồi đọc lời cổng báo khi chặn (khung #validateHoSo);
//   - trang hoàn thiện thông tin tài khoản (/vneidsso, người làm lần đầu): nhận ra trang, bấm "Lưu" rồi đọc lỗi.
(() => {
  if (window.__TLND_BN_TAB_FLOW__) return;
  window.__TLND_BN_TAB_FLOW__ = true;
  const H = (window.__TLND__ = window.__TLND__ || {});

  const PFX = "_org_bn_hoso_noptructuyen_";
  const TABS = ["chondonvitiepnhan", "nhapdondangky", "taithanhphan", "hinhthucnhanketqua"];
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const textOf = (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  const shown = (el) => !!el && el.getClientRects().length > 0;
  const fold = (s) => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/gi, "d")
    .replace(/\s+/g, " ").trim().toLowerCase();

  // Pane của tab: <li id="..._nhapTab<mã>TabsId"> ↔ <div id="..._nhapTab<mã>TabsSection">, pane ẩn mang class "hide".
  function tabSection(li) {
    const id = String(li?.id || "");
    return id.endsWith("TabsId") ? document.getElementById(id.slice(0, -"TabsId".length) + "TabsSection") : null;
  }

  function currentTab() {
    for (const [index, name] of TABS.entries()) {
      const li = document.querySelector(`li[data-tab-name="${name}"]`);
      const link = li?.querySelector("a");
      const section = tabSection(li);
      if (link?.classList.contains("active") && !section?.classList.contains("hide")) return index + 1;
    }
    return 0;
  }

  const ourPage = () => location.hostname === "dichvucong.bacninh.gov.vn"
    && !!document.querySelector(`li[data-tab-name="${TABS[0]}"]`);

  async function showTab(name) {
    if (!TABS.includes(name) || typeof H.activateBacNinhTab !== "function") return { ok: false };
    const res = await H.activateBacNinhTab(name);
    return { ok: !!res?.shown, tab: currentTab() };
  }

  // ── Tab đầu: cơ quan tiếp nhận ──

  const agencySelect = () => document.getElementById(`${PFX}donViTiepNhanId`);
  function agencyText() {
    const select = agencySelect();
    const option = select?.selectedOptions?.[0];
    return select?.value && option ? textOf(option) : "";
  }

  async function agency(msg) {
    const value = String(msg.value || "");
    let ok = true;
    if (value) {
      // Engine Bắc Ninh chọn select2 theo chữ + phát change để cổng ghi "Kính gửi" và nạp lại tab nhận kết quả.
      if (typeof H.fillFormBacNinh === "function") {
        await H.fillFormBacNinh([{ name: "donViTiepNhanId", comp: "bn-select", value }]);
      }
      await sleep(300);
      ok = fold(agencyText()) === fold(value);
    }
    const options = Array.from(agencySelect()?.options || []).filter((o) => o.value).map(textOf).filter(Boolean);
    return { ok, selected: agencyText(), options };
  }

  // ── Tab nhận kết quả ──

  const resultRadios = () => Array.from(document.querySelectorAll(`input[type="radio"][name="${PFX}noiNhanKetQua"]`));
  // Chọn "Tại nơi nộp hồ sơ" cổng có thể hiện thêm danh sách điểm tiếp nhận (theo cơ quan tiếp nhận) bắt chọn một điểm.
  const pointRadios = () => Array.from(document.querySelectorAll(
    `input[type="radio"][name="${PFX}noiNhanKetQuadiemTiepNhanId"]`)).filter(shown);

  // Chọn bưu chính cổng hiện hai ô tích (class chkNhanKetQua): guiBuuChinh / nhanBuuChinh, tích được cả hai.
  const postalBoxes = () => Array.from(document.querySelectorAll("input.chkNhanKetQua[type=\"checkbox\"]")).filter(shown);
  const postalName = (box) => String(box.name || "").replace(PFX, "");

  async function tick(radio) {
    if (!radio || radio.checked) return !!radio;
    // click() chạy đủ handler change của cổng (ẩn/hiện khối địa chỉ bưu chính / điểm tiếp nhận).
    radio.click();
    if (!radio.checked) {
      radio.checked = true;
      radio.dispatchEvent(new Event("change", { bubbles: true }));
    }
    await sleep(400);
    return radio.checked;
  }

  function resultState() {
    const checked = resultRadios().find((r) => r.checked);
    const point = pointRadios().find((r) => r.checked);
    return {
      checked: checked ? checked.value : "",
      options: resultRadios().filter(shown).map((r) => ({ value: r.value, label: textOf(r.closest("div")) })),
      point: point ? point.value : "",
      points: pointRadios().map((r) => ({
        value: r.value,
        label: textOf(r.closest("label")),
        address: textOf(r.closest(".card-body")?.querySelector("p")),
      })),
      postal: postalBoxes().map((b) => ({ name: postalName(b), label: textOf(b.closest("label")), checked: b.checked })),
    };
  }

  async function result(msg) {
    let ok = true;
    const pick = String(msg.value || "");
    if (pick) {
      const target = resultRadios().find((r) => r.value === pick);
      ok = shown(target) && await tick(target);
      const point = String(msg.point || "");
      if (ok && point) {
        // Danh sách điểm hiện sau khi chọn "Tại nơi nộp hồ sơ".
        for (let waited = 0; waited < 2000 && !pointRadios().length; waited += 200) await sleep(200);
        ok = await tick(pointRadios().find((r) => r.value === point));
      }
    }
    if (Array.isArray(msg.postal)) {
      // Tích đúng các ô được chọn, bỏ tích ô còn lại; click() để cổng ẩn/hiện khối địa chỉ của ô đó.
      for (const box of postalBoxes()) {
        const want = msg.postal.includes(postalName(box));
        if (box.checked !== want) box.click();
        if (box.checked !== want) {
          box.checked = want;
          box.dispatchEvent(new Event("change", { bubbles: true }));
        }
      }
      await sleep(300);
      ok = ok && postalBoxes().every((b) => b.checked === msg.postal.includes(postalName(b)));
    }
    return { ok, ...resultState() };
  }

  // ── Nộp hồ sơ ──

  const warnings = () => Array.from(document.querySelectorAll(`#${PFX}validateHoSo li, #${PFX}validateHoSo .alert`))
    .filter(shown).map(textOf).filter(Boolean).join("; ");

  async function submit() {
    // Đọc nơi nhận TRƯỚC khi đổi tab: trang 2 tab để khối bưu chính ở tab đầu, đổi tab là khối đó ẩn đi.
    // Đang nhận tại nơi nộp mà cổng có danh sách điểm tiếp nhận chưa chọn → chưa bấm, để trợ lý nhắc chọn điểm.
    const state = resultState();
    if (state.points.length && !state.point) return { clicked: false, missing: "point", ...state };
    // Bưu chính mà chưa tích gửi hồ sơ / nhận kết quả qua bưu điện → nhắc chọn trước.
    if (state.postal.length && !state.postal.some((b) => b.checked)) return { clicked: false, missing: "postal", ...state };
    // Nút Nộp hồ sơ chỉ hiện ở tab cuối của trang (cổng ẩn/hiện khi đổi tab): tab nhận kết quả, trang 2 tab là tab
    // đính kèm.
    for (const name of [TABS[3], TABS[2]]) {
      if (shown(document.getElementById(`${PFX}nopTrucTuyen`))) break;
      if (document.querySelector(`li[data-tab-name="${name}"]`)) await showTab(name);
    }
    const button = document.getElementById(`${PFX}nopTrucTuyen`);
    if (!shown(button) || button.disabled) return { clicked: false, message: "Chưa thấy nút Nộp hồ sơ trên trang." };
    const before = warnings();
    button.click();
    for (let waited = 0; waited < 4000; waited += 200) {
      await sleep(200);
      const now = warnings();
      if (now && now !== before) return { clicked: true, message: now.slice(0, 200) };
    }
    return { clicked: true, message: "" };
  }

  // ── Trang hoàn thiện thông tin tài khoản ──

  const accountForm = () => (location.hostname === "dichvucong.bacninh.gov.vn"
    ? document.querySelector('form[id$="_frmCongDanAction"][id*="_taikhoan_sso_vneid_"]') : null);
  const accountErrors = () => Array.from(document.querySelectorAll(
    ".help-block-error, #toast-container .toast-message, .toast-error .toast-message"))
    .filter(shown).map(textOf).filter(Boolean);

  async function saveAccount() {
    const form = accountForm();
    const button = form?.querySelector('button[type="submit"]');
    if (!shown(button)) return { clicked: false, message: "Chưa thấy nút Lưu trên trang." };
    const before = new Set(accountErrors());
    button.click();
    // Lưu được thì cổng chuyển trang (content script này mất, sidebar nhận null); lỗi hiện dưới ô / thông báo nổi.
    for (let waited = 0; waited < 4000; waited += 200) {
      await sleep(200);
      const fresh = accountErrors().filter((t) => !before.has(t));
      if (fresh.length) return { clicked: true, message: fresh.slice(0, 3).join("; ").slice(0, 200) };
    }
    return { clicked: true, message: "" };
  }

  H.bacNinhTab = () => (ourPage() ? currentTab() : 0);
  H.bacNinhAccountForm = () => !!accountForm();
  H.bacNinhAgency = () => (ourPage() ? agencyText() : "");

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    const action = String(msg?.action || "");
    if (action === "bnAccountSave") {
      if (!accountForm()) return;
      saveAccount().then(sendResponse).catch((e) => sendResponse({ clicked: false, message: String(e?.message || e) }));
      return true;
    }
    if (!["bnShowTab", "bnAgency", "bnResult", "bnSubmit"].includes(action) || !ourPage()) return;
    const run = action === "bnShowTab" ? showTab(String(msg.tab || "")) : action === "bnAgency" ? agency(msg)
      : action === "bnResult" ? result(msg) : submit();
    run.then(sendResponse).catch((e) => sendResponse({ ok: false, error: String(e?.message || e) }));
    return true;
  });
})();
