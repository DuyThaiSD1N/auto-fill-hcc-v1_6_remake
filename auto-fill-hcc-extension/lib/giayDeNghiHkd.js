// Phần thuần của tab "Tờ khai đăng ký hộ kinh doanh": chuẩn hoá, kiểm tra ô nhập, đọc số tiền bằng chữ.
// Tách khỏi trang để chạy test bằng node (không cần trình duyệt).
(() => {
  "use strict";

  const REPEAT_RE = /(.)\1{4,}/u; // "ttttt": gõ nhầm hoặc giữ phím

  function parseNgay(value) {
    const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value || "");
    if (!m) return null;
    const date = new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]));
    return date.getDate() === Number(m[1]) && date.getMonth() === Number(m[2]) - 1 ? date : null;
  }

  // "5/9/1990", "05-09-1990", "05.09.1990" → "05/09/1990"; dạng khác giữ nguyên để báo lỗi đúng chỗ.
  function chuanHoaNgay(value) {
    const text = String(value || "").trim();
    const m = /^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$/.exec(text);
    return m ? `${m[1].padStart(2, "0")}/${m[2].padStart(2, "0")}/${m[3]}` : text;
  }

  function loiNgay(value, { quaKhu = false } = {}) {
    if (!value) return "";
    const date = parseNgay(value);
    if (!date) return "Nhập theo dạng ngày/tháng/năm, ví dụ 05/09/1990";
    if (date.getFullYear() < 1900) return "Năm không hợp lệ";
    if (quaKhu && date > new Date()) return "Ngày không được ở tương lai";
    return "";
  }

  // Ô tờ khai ghi "Số định danh cá nhân": đúng 12 chữ số, không nhận CMND 9 số như giấy ủy quyền.
  const chuanHoaSoDinhDanh = (value) => String(value || "").replace(/[\s.-]/g, "");
  const loiSoDinhDanh = (value) => (value && !/^\d{12}$/.test(value) ? "Số định danh gồm đúng 12 chữ số" : "");

  const loiDienThoai = (value) => {
    if (!value) return "";
    return /^\+?\d{8,15}$/.test(String(value).replace(/[\s.()-]/g, "")) ? "" : "Số điện thoại chưa đúng";
  };

  const loiEmail = (value) => (value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? "Thư điện tử chưa đúng" : "");
  const loiMaNganh = (value) => (value && !/^\d{4}$/.test(value) ? "Mã ngành cấp bốn gồm đúng 4 chữ số" : "");
  const loiLaoDong = (value) => (value && !/^\d{1,6}$/.test(value) ? "Chỉ nhập số" : "");
  const loiChu = (value) => (value && REPEAT_RE.test(value) ? "Có vẻ gõ nhầm, kiểm tra lại" : "");

  // ── Số tiền ──
  const chiLaySo = (value) => String(value || "").replace(/\D/g, "").replace(/^0+(?=\d)/, "");
  const dinhDangTien = (value) => chiLaySo(value).replace(/\B(?=(\d{3})+(?!\d))/g, ".");

  const SO = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"];

  // Đọc một nhóm 3 chữ số. `dayDu`: nhóm đứng sau nhóm khác nên phải đọc cả "không trăm", "linh".
  function docNhom(n, dayDu) {
    const tram = Math.floor(n / 100);
    const chuc = Math.floor((n % 100) / 10);
    const donVi = n % 10;
    const out = [];
    if (tram || dayDu) out.push(`${SO[tram]} trăm`);
    if (chuc > 1) {
      out.push(`${SO[chuc]} mươi`);
      if (donVi === 1) out.push("mốt");
      else if (donVi === 5) out.push("lăm");
      else if (donVi) out.push(SO[donVi]);
    } else if (chuc === 1) {
      out.push("mười");
      if (donVi === 5) out.push("lăm");
      else if (donVi) out.push(SO[donVi]);
    } else if (donVi) {
      if (tram || dayDu) out.push("linh");
      out.push(SO[donVi]);
    }
    return out.join(" ");
  }

  // Dưới một tỷ: chín chữ số, ba nhóm triệu / nghìn / đơn vị. `dayDu` như docNhom, cho phần đứng sau "tỷ".
  function docDuoiTy(n, dayDu) {
    const trieu = Math.floor(n / 1e6);
    const nghin = Math.floor((n % 1e6) / 1e3);
    const donVi = n % 1e3;
    const out = [];
    let daCo = dayDu;
    for (const [nhom, ten] of [[trieu, "triệu"], [nghin, "nghìn"], [donVi, ""]]) {
      if (!nhom) continue;
      out.push(`${docNhom(nhom, daCo)}${ten ? ` ${ten}` : ""}`);
      daCo = true;
    }
    return out.join(" ");
  }

  // 150000000 → "Một trăm năm mươi triệu đồng". Tối đa 15 chữ số (nghìn tỷ); dài hơn trả rỗng để cán bộ tự ghi.
  function docTienBangChu(value) {
    const digits = chiLaySo(value);
    if (!digits || digits.length > 15) return "";
    const n = Number(digits);
    if (n === 0) return "Không đồng";
    const ty = Math.floor(n / 1e9);
    const conLai = n % 1e9;
    const parts = [];
    if (ty) parts.push(`${docDuoiTy(ty, false)} tỷ`);
    if (conLai) parts.push(docDuoiTy(conLai, ty > 0));
    const text = `${parts.join(" ")} đồng`;
    return text[0].toUpperCase() + text.slice(1);
  }

  // Dòng "Tổng số (bằng số, bằng chữ, VNĐ)" trên giấy.
  function dongVon(so, chu) {
    const bangSo = dinhDangTien(so);
    const bangChu = String(chu || "").trim();
    if (!bangSo) return bangChu;
    return bangChu ? `${bangSo} đồng (${bangChu})` : `${bangSo} đồng`;
  }

  // Ô Mã ngành là ô tìm: gõ chữ số → các ngành có mã BẮT ĐẦU bằng số đó, xếp theo mã. Gõ trống / có chữ cái
  // thì không gợi ý (tìm theo tên đã bỏ theo yêu cầu, tên ngành gõ tự do ở ô bên cạnh).
  function timTheoMa(danhMuc, query, gioiHan = 30) {
    const so = String(query || "").replace(/\s/g, "");
    if (!/^\d{1,4}$/.test(so) || !Array.isArray(danhMuc)) return [];
    return danhMuc
      .filter((item) => String(item?.ma || "").startsWith(so))
      .sort((a, b) => String(a.ma).localeCompare(String(b.ma)))
      .slice(0, gioiHan);
  }

  // ── Chuyển tờ khai cho Auto Fill điền cổng (không OCR) ──
  // Tab tờ khai ghi vào chrome.storage.session (chỉ trong RAM, đóng trình duyệt là mất), popup đọc khi bấm điền.
  const KHOA_AUTO_FILL = "hccToKhaiHkd";
  const coChu = (v) => String(v ?? "").trim() !== "";
  const coDiaChi = (a) => !!a && ["chiTiet", "xa", "tinh"].some((k) => coChu(a[k]));

  // Chỉ mấy ô điền sẵn theo tài khoản (địa danh, ngày lập, kính gửi) thì chưa phải tờ khai của ai: không chuyển.
  function coNoiDung(data) {
    if (!data) return false;
    const chu = ["hoTen", "soDinhDanh", "ngaySinh", "tenViet", "vonKinhDoanh", "ngayBatDau", "soLaoDong",
      "dienThoai", "truSoDienThoai"];
    return chu.some((k) => coChu(data[k])) || coDiaChi(data.truSo)
      || (Array.isArray(data.nganh) && data.nganh.some((n) => coChu(n?.ten) || coChu(n?.ma)));
  }

  // Tên hiện trên panel để cán bộ nhận ra tờ khai của ai trước khi điền.
  function tenToKhai(data) {
    const ten = String(data?.tenViet || "").trim();
    const chuHo = String(data?.hoTen || "").trim();
    if (ten && chuHo) return `${ten} (chủ hộ ${chuHo})`;
    return ten || (chuHo ? `chủ hộ ${chuHo}` : "chưa có tên");
  }

  // Giờ:phút của lần lưu, hiện cạnh bản xem trước và dòng Auto Fill.
  function gioPhut(ms) {
    const d = new Date(ms);
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  }

  const api = {
    chuanHoaNgay, loiNgay, chuanHoaSoDinhDanh, loiSoDinhDanh, loiDienThoai, loiEmail, loiMaNganh, loiLaoDong,
    loiChu, chiLaySo, dinhDangTien, docTienBangChu, dongVon, timTheoMa, KHOA_AUTO_FILL, coNoiDung, tenToKhai,
    gioPhut,
  };
  if (typeof window !== "undefined") window.HccGiayDeNghiHkd = api;
  if (typeof module !== "undefined") module.exports = api;
})();
