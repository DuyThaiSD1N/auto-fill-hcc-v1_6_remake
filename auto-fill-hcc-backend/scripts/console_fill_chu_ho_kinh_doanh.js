// ============================================================================
// GIẢ LẬP FILL TRANG "Thông tin về chủ hộ kinh doanh" (thủ tục Đăng ký kinh doanh)
// ----------------------------------------------------------------------------
// Dùng để test tay trên cổng dangkykinhdoanh.gov.vn mà KHÔNG cần chạy backend/OCR:
// dán cả file này vào Console của Chrome khi đang ở đúng trang "Chủ hộ kinh doanh".
//
// - Sửa CASE ở ngay dưới để đổi dữ liệu giả lập. Ô nào để "" thì bỏ qua (giống mapper).
// - buildFields() dựng ĐÚNG payload backend trả về cho trang này
//   (app/pipelines/dang_ky_kinh_doanh/process/mapper.py, nhánh "chu-ho-kinh-doanh"),
//   nên test ở đây khớp với luồng thật của extension.
// - Ô điền được tô viền XANH, ô không tìm thấy tô viền ĐỎ; cuối cùng in bảng kết quả.
// - Trang này là ASP.NET WebForms: chọn Quốc gia/Tỉnh sẽ postback để nạp lại Phường/Xã
//   → script tự chờ postback xong mới điền ô kế tiếp. Nếu cổng reload TOÀN TRANG thì
//   dán lại file này một lần nữa (console không sống sót qua reload).
// ============================================================================

(async () => {
  // ==========================================================================
  // 1. DỮ LIỆU GIẢ LẬP — sửa tự do
  // ==========================================================================
  const CASE = {
    hoTen: "NGUYỄN VĂN AN",       // giấy hay ghi IN HOA, script tự chuẩn hóa như mapper
    gioiTinh: "Nam",              // "Nam" | "Nữ"
    ngaySinh: "5/3/1990",         // d/m/yyyy hoặc dd/mm/yyyy
    soDinhDanh: "024090001234",
    diaChi: {
      quocGia: "Việt Nam",
      tinh: "Bắc Ninh",
      xa: "Hiệp Hòa",
      diaChi: "Thôn Đại Đồng",
    },
    dienThoai: "0912345678",
    email: "an.nguyen@example.com",
    fax: "",
    website: "",
  };

  // ==========================================================================
  // 2. DỰNG FIELD GIỐNG HỆT MAPPER BACKEND
  // ==========================================================================
  const PERS = "ctl00$C$OWN_PCtl$PERSCtl";
  const ADDR = PERS + "$ADDRCCtl";

  const properName = (v) =>
    String(v || "").trim().split(/\s+/).filter(Boolean)
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(" ");

  const genderCode = (v) => {
    const t = String(v || "").trim().toLowerCase();
    if (!t) return "";
    return t.startsWith("nữ") || t.startsWith("nu") ? "F" : "M";
  };

  const normalizeDate = (v) => {
    const m = String(v || "").trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    return m ? `${m[1].padStart(2, "0")}/${m[2].padStart(2, "0")}/${m[3]}` : String(v || "");
  };

  function buildFields(c) {
    const a = c.diaChi || {};
    return [
      // "P" = chủ hộ là CÁ NHÂN. Radio này có thể postback dựng lại cả khối bên dưới → điền đầu tiên.
      { name: "ctl00$C$OWNER_TYPE_RbBox", comp: "dom-radio", value: "P" },
      { name: `${PERS}$FULL_NAMEFld`, comp: "dom-input", value: properName(c.hoTen) },
      { name: `${PERS}$GENDER_IDFld`, comp: "dom-radio", value: genderCode(c.gioiTinh) },
      { name: `${PERS}$DATE_OF_BIRTHFld`, comp: "dom-date", value: normalizeDate(c.ngaySinh) },
      { name: `${PERS}$PERS_DOC_NOFld`, comp: "dom-input", value: c.soDinhDanh },
      { name: `${ADDR}$COUNTRY_IDFld`, comp: "dom-select", value: a.quocGia || "Việt Nam" },
      { name: `${ADDR}$CITY_IDFld`, comp: "dom-select", value: a.tinh },
      { name: `${ADDR}$WARD_IDFld`, comp: "dom-select", value: a.xa },
      { name: `${ADDR}$STREET_NUMBERFld`, comp: "dom-input", value: a.diaChi },
      { name: `${PERS}$PHONEFld`, comp: "dom-input", value: c.dienThoai },
      { name: `${PERS}$FAXFld`, comp: "dom-input", value: c.fax },
      { name: `${PERS}$EMAILFld`, comp: "dom-input", value: c.email },
      { name: `${PERS}$URLFld`, comp: "dom-input", value: c.website },
      // Mapper bỏ field rỗng — giả lập y hệt để không "điền" ô trống.
    ].filter((f) => f.value !== undefined && f.value !== null && String(f.value) !== "");
  }

  // ==========================================================================
  // 3. TIỆN ÍCH DOM
  // ==========================================================================
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // Bỏ dấu + bỏ tiền tố loại đơn vị để so tên tỉnh/xã ("Tỉnh Bắc Ninh" ≡ "Bắc Ninh").
  const fold = (s) =>
    String(s == null ? "" : s)
      .normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/đ/g, "d").replace(/Đ/g, "D")
      .toLowerCase().replace(/\s+/g, " ").trim();

  const stripAdminPrefix = (s) =>
    fold(s).replace(/^(tinh|thanh pho|tp\.?|xa|phuong|thi tran|tt\.?|quan|huyen)\s+/, "").trim();

  function byName(name) {
    return (
      document.querySelector(`[name="${name}"]`) ||
      document.getElementById(name.replace(/\$/g, "_"))
    );
  }

  function radiosByName(name) {
    const list = Array.from(document.querySelectorAll(`input[type="radio"][name="${name}"]`));
    if (list.length) return list;
    // WebForms RadioButtonList: name có thể gắn hậu tố; dò thêm theo id prefix.
    const idPrefix = name.replace(/\$/g, "_");
    return Array.from(document.querySelectorAll('input[type="radio"]'))
      .filter((el) => el.id.startsWith(idPrefix) || el.name.startsWith(name));
  }

  function setNativeValue(el, value) {
    const proto = el instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
    if (setter) setter.call(el, value); else el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function mark(el, ok) {
    if (!el) return;
    el.style.outline = ok ? "2px solid #16a34a" : "2px solid #dc2626";
    el.style.outlineOffset = "1px";
  }

  // ASP.NET UpdatePanel: chờ async postback kết thúc (nếu trang có PageRequestManager).
  function waitPostback(timeout = 8000) {
    const prm = window.Sys?.WebForms?.PageRequestManager?.getInstance?.();
    if (!prm) return sleep(400);
    if (!prm.get_isInAsyncPostBack()) return sleep(250);
    return new Promise((resolve) => {
      const done = () => { try { prm.remove_endRequest(done); } catch (e) { /* ignore */ } resolve(); };
      prm.add_endRequest(done);
      setTimeout(done, timeout);
    });
  }

  function pickOption(select, wanted) {
    const opts = Array.from(select.options || []).filter((o) => o.value !== "" && o.value !== "0");
    const w = fold(wanted);
    const ws = stripAdminPrefix(wanted);
    return (
      opts.find((o) => fold(o.text) === w) ||
      opts.find((o) => stripAdminPrefix(o.text) === ws) ||
      opts.find((o) => fold(o.value) === w) ||
      (ws.length >= 3 ? opts.find((o) => stripAdminPrefix(o.text).startsWith(ws)) : null) ||
      null
    );
  }

  // Chờ tới khi <select> có option khớp (option con nạp sau postback của ô cha).
  async function waitOption(name, wanted, timeout = 8000) {
    const deadline = Date.now() + timeout;
    for (;;) {
      const el = byName(name);
      const opt = el && pickOption(el, wanted);
      if (opt || Date.now() > deadline) return { el, opt: opt || null };
      await sleep(200);
    }
  }

  // ==========================================================================
  // 4. ĐIỀN TỪNG LOẠI Ô
  // ==========================================================================
  async function fillField(f) {
    if (f.comp === "dom-radio") {
      const list = radiosByName(f.name);
      const target = list.find((el) => fold(el.value) === fold(f.value));
      if (!target) return { ok: false, el: list[0] || null };
      if (!target.checked) {
        target.click();
        // Radio loại chủ hộ / giới tính có thể postback dựng lại khối bên dưới.
        await waitPostback();
      }
      mark(target.closest("label") || target, true);
      return { ok: true, el: target };
    }

    if (f.comp === "dom-select") {
      const { el, opt } = await waitOption(f.name, f.value);
      if (!el || !opt) return { ok: false, el };
      if (el.value !== opt.value) {
        el.value = opt.value;
        el.dispatchEvent(new Event("change", { bubbles: true }));
        // Quốc gia/Tỉnh postback để nạp Phường/Xã → phải chờ xong mới sang ô sau.
        await waitPostback();
      }
      mark(el, true);
      return { ok: true, el };
    }

    // dom-input / dom-date đều là <input type=text> trên cổng này.
    const el = byName(f.name);
    if (!el) return { ok: false, el: null };
    if (el.disabled) el.disabled = false;
    if (el.readOnly) el.readOnly = false;
    setNativeValue(el, String(f.value));
    mark(el, true);
    return { ok: true, el };
  }

  // ==========================================================================
  // 5. CHẠY
  // ==========================================================================
  const fields = buildFields(CASE);
  console.log("%c[GiaLap] Payload giả lập cho trang chu-ho-kinh-doanh:", "font-weight:bold", fields);

  const report = [];
  for (const f of fields) {
    let ok = false;
    let el = null;
    try {
      ({ ok, el } = await fillField(f));
    } catch (e) {
      console.warn("[GiaLap] Lỗi điền", f.name, e);
    }
    if (!ok && el) mark(el, false);
    report.push({
      "Ô": f.name.replace(/^ctl00\$C\$/, ""),
      comp: f.comp,
      "Giá trị": f.value,
      "Kết quả": ok ? "OK" : "KHÔNG THẤY",
    });
    await sleep(80);
  }

  console.table(report);
  const missed = report.filter((r) => r["Kết quả"] !== "OK");
  console.log(
    `%c[GiaLap] Điền ${report.length - missed.length}/${report.length} ô.` +
      (missed.length ? ` Thiếu: ${missed.map((r) => r["Ô"]).join(", ")}` : " Đủ hết."),
    `font-weight:bold;color:${missed.length ? "#dc2626" : "#16a34a"}`
  );
  if (missed.length) {
    console.log(
      "[GiaLap] Ô thiếu thường do: chưa ở đúng trang chủ hộ, khối chủ hộ chưa hiện " +
        "(chọn radio 'Cá nhân' trước), hoặc cổng vừa postback toàn trang → dán lại script."
    );
  }
})();
