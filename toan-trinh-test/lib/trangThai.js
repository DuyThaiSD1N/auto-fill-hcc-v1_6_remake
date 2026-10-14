/**
 * HccTrangThai — panel đang ở trạng thái nào, gộp từ nhiều tín hiệu.
 *
 * Vì sao cần: mọi việc "chỉ làm khi cán bộ rảnh" (trước mắt là tự nạp lại
 * extension khi có bản mới) đều phải trả lời được câu "rảnh là rảnh thế nào".
 * Một tín hiệu đơn lẻ luôn sai ở đâu đó:
 *
 *   - chỉ nhìn cờ BUSY của luồng điền/đính kèm  → cán bộ đang gõ tay vào form
 *     trên cổng thì vẫn bị coi là rảnh;
 *   - chỉ nhìn document.hasFocus() của panel     → cán bộ gõ vào TRANG GỐC là
 *     iframe mất focus ngay, tưởng nhầm đã bỏ đi;
 *   - chỉ nhìn "panel có mở không"               → mở suốt buổi, không bao giờ
 *     rảnh, việc cần làm không bao giờ chạy.
 *
 * Ba trạng thái:
 *
 *   "dang-lam-viec"      có request đang chạy, hoặc vừa có thao tác (chuột/
 *                        phím/cuộn) trên panel HOẶC trên trang gốc, hoặc con
 *                        trỏ đang nằm trong một ô nhập, hoặc bên gọi tự khai
 *                        đang bận (đính kèm, hàng đợi tách hồ sơ…).
 *   "mo-khong-lam-viec"  panel đang hiển thị, cửa sổ vẫn được focus, nhưng
 *                        không có thao tác nào trong NGUONG_HOAT_DONG_MS.
 *   "chay-nen"           tab bị ẩn, hoặc cả cửa sổ mất focus liên tục
 *                        NGUONG_NEN_MS — cán bộ đã sang việc khác.
 *
 * Trạng thái được tính LẠI mỗi giây chứ không chỉ khi có sự kiện: "rảnh" là
 * thứ xuất hiện do KHÔNG có gì xảy ra, mà không-có-gì thì không bắn event nào.
 */
(() => {
  "use strict";
  if (window.HccTrangThai) return; // nạp trùng (panel dựng lại) — giữ đúng một bộ đếm

  const NGUONG_HOAT_DONG_MS = 20 * 1000;
  const NGUONG_NEN_MS = 15 * 1000;
  const NHIP_KIEM_MS = 1000;
  const NHIP_GOM_HOAT_DONG_MS = 2000; // gom bớt mousemove, khỏi cập nhật 60 lần/giây

  const DANG_LAM_VIEC = "dang-lam-viec";
  const MO_KHONG_LAM_VIEC = "mo-khong-lam-viec";
  const CHAY_NEN = "chay-nen";

  let soRequest = 0;
  let lucHoatDongCuoi = Date.now();
  let lucMatFocusTu = 0;      // 0 = đang có focus
  let coTinTuTrangGoc = false; // đã từng nhận tin từ content.js chưa
  let focusTheoTrangGoc = true;
  let anTheoTrangGoc = false;
  let layCoBanNgoai = () => false;
  let trangThai = DANG_LAM_VIEC;
  const nguoiTheoDoi = new Set();

  function dangGo() {
    const el = document.activeElement;
    // Con trỏ nằm trong ô nhập = cán bộ đang giữa chừng một việc, kể cả khi đã
    // dừng gõ vài phút để đọc giấy tờ. Không tính theo thời gian gõ cuối.
    return !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable);
  }

  function dangAn() {
    if (coTinTuTrangGoc) return anTheoTrangGoc;
    return document.visibilityState === "hidden";
  }

  function coFocus() {
    // Ưu tiên tin từ trang gốc: document.hasFocus() của CHÍNH iframe panel chỉ
    // đúng khi focus nằm trong panel — cán bộ gõ vào form trên cổng là nó trả
    // false ngay, trong khi cửa sổ vẫn đang được dùng.
    if (coTinTuTrangGoc) return focusTheoTrangGoc;
    try { return document.hasFocus(); } catch (e) { return true; }
  }

  function tinh() {
    if (soRequest > 0) return DANG_LAM_VIEC;
    let banNgoai = false;
    try { banNgoai = !!layCoBanNgoai(); } catch (e) { banNgoai = true; } // hỏi không được thì coi là bận
    if (banNgoai) return DANG_LAM_VIEC;

    const gio = Date.now();
    if (dangAn()) return CHAY_NEN;
    if (!coFocus()) {
      if (lucMatFocusTu === 0) lucMatFocusTu = gio;
      if (gio - lucMatFocusTu >= NGUONG_NEN_MS) return CHAY_NEN;
    } else {
      lucMatFocusTu = 0;
    }
    if (dangGo()) return DANG_LAM_VIEC;
    if (gio - lucHoatDongCuoi < NGUONG_HOAT_DONG_MS) return DANG_LAM_VIEC;
    return MO_KHONG_LAM_VIEC;
  }

  function capNhat() {
    const moi = tinh();
    if (moi === trangThai) return;
    const cu = trangThai;
    trangThai = moi;
    for (const cb of nguoiTheoDoi) {
      try { cb(moi, cu); } catch (e) { console.warn("[TrangThai] người theo dõi ném lỗi:", e); }
    }
  }

  let lucGomCuoi = 0;
  function ghiNhanHoatDong() {
    const gio = Date.now();
    if (gio - lucGomCuoi < NHIP_GOM_HOAT_DONG_MS) {
      lucHoatDongCuoi = gio;
      return;
    }
    lucGomCuoi = gio;
    lucHoatDongCuoi = gio;
    capNhat();
  }

  // ---- đếm request: bọc fetch của CHÍNH trang panel -----------------------
  // Bọc một lần ở đây thay vì sửa hàng chục chỗ gọi: mọi lượt gọi API cổng lẫn
  // mọi lượt kéo file từ agent đều đi qua fetch, và code THÊM về sau cũng được
  // tính mà không phải nhớ gì.
  function bocFetch() {
    const goc = window.fetch;
    if (typeof goc !== "function" || goc.__hccDaBoc) return;
    const boc = function (...tham) {
      soRequest++;
      capNhat();
      let p;
      try {
        p = goc.apply(this, tham);
      } catch (e) {
        soRequest--;
        throw e;
      }
      return Promise.resolve(p).finally(() => {
        soRequest = Math.max(0, soRequest - 1);
        // Request vừa xong CŨNG là hoạt động: đừng để một lượt tải 30 giây
        // trở thành "im lặng 30 giây" rồi bị coi là rảnh ngay khi tải xong.
        lucHoatDongCuoi = Date.now();
        capNhat();
      });
    };
    boc.__hccDaBoc = true;
    window.fetch = boc;
  }

  // ---- tin từ trang gốc (content.js) --------------------------------------
  function nhanTinTrangGoc(e) {
    if (e.source !== window.parent) return; // chỉ tin frame cha, đúng lối các message khác
    const d = e.data;
    if (!d || typeof d !== "object") return;
    if (d.type === "autofill-hcc-hoat-dong") {
      coTinTuTrangGoc = true;
      ghiNhanHoatDong();
    } else if (d.type === "autofill-hcc-trang-thai-trang") {
      coTinTuTrangGoc = true;
      focusTheoTrangGoc = !!d.focus;
      anTheoTrangGoc = !!d.an;
      if (focusTheoTrangGoc) lucMatFocusTu = 0;
      capNhat();
    }
  }

  const HccTrangThai = {
    DANG_LAM_VIEC, MO_KHONG_LAM_VIEC, CHAY_NEN,
    NGUONG_HOAT_DONG_MS, NGUONG_NEN_MS,

    /** Gắn listener và bắt đầu tính. `layCoBanNgoai()` trả true khi bên gọi tự
     *  biết mình đang bận (luồng đính kèm, hàng đợi tách hồ sơ, …). */
    batDau(opts = {}) {
      if (typeof opts.layCoBanNgoai === "function") layCoBanNgoai = opts.layCoBanNgoai;
      if (this.__daBatDau) return;
      this.__daBatDau = true;
      bocFetch();
      for (const ev of ["mousemove", "mousedown", "keydown", "wheel", "touchstart", "click"]) {
        document.addEventListener(ev, ghiNhanHoatDong, { passive: true, capture: true });
      }
      document.addEventListener("visibilitychange", capNhat);
      window.addEventListener("message", nhanTinTrangGoc);
      // Nhịp đều: "rảnh" sinh ra từ việc KHÔNG có gì xảy ra, nên không có event
      // nào để bám vào — phải tự hỏi lại.
      setInterval(capNhat, NHIP_KIEM_MS);
      capNhat();
    },

    hienTai() { return tinh(); },
    dangBan() { return this.hienTai() === DANG_LAM_VIEC; },
    soRequestDangChay() { return soRequest; },

    /** Bắn khi trạng thái ĐỔI. Trả hàm gỡ theo dõi. */
    theoDoi(cb) {
      nguoiTheoDoi.add(cb);
      return () => nguoiTheoDoi.delete(cb);
    },

    /** Cho code không đi qua fetch (XHR, thao tác dài) tự khai. */
    moViec() { soRequest++; capNhat(); },
    dongViec() { soRequest = Math.max(0, soRequest - 1); lucHoatDongCuoi = Date.now(); capNhat(); },

    /** Dùng trong test. */
    __datLai() {
      soRequest = 0; lucHoatDongCuoi = Date.now(); lucMatFocusTu = 0;
      coTinTuTrangGoc = false; focusTheoTrangGoc = true; anTheoTrangGoc = false;
      layCoBanNgoai = () => false; trangThai = DANG_LAM_VIEC;
    },
    __ghiNhanHoatDong: ghiNhanHoatDong,
    __nhanTinTrangGoc: nhanTinTrangGoc,
  };

  window.HccTrangThai = HccTrangThai;
})();
