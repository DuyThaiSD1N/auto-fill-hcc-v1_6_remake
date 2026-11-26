import type { ProcedureSim } from "../../registry";

// Đăng ký xe lần đầu toàn trình — xe nhập khẩu (1.013066). Cổng DVC Bộ Công an (dichvucong.bocongan.gov.vn),
// form-builder jQuery + bootstrap-select, ô name CongDan__fs* / CongDan_*. Cùng nền form với 1.012575, khác Phần V.
const sim: ProcedureSim = {
  bca: "dang-ky-xe-lan-dau-nhap-khau",
  note: "Phần III–V điền sẵn từ giấy; người dân nhập Mã bảo mật + bấm Tra cứu thì cổng ghi đè bằng dữ liệu CSDL (Thuế, Hải quan, Cục Đăng kiểm). Ba ô ảnh đầu trang: Auto Fill gắn ở lượt điền, trợ lý gắn ở bước Đính kèm (lượt điền của trợ lý để trống là đúng).",
};
export default sim;
