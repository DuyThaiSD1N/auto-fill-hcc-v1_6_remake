import type { ProcedureSim } from "../../registry";

// Đăng ký xe lần đầu toàn trình — xe sản xuất, lắp ráp trong nước (1.012575). Cổng DVC Bộ Công an
// (dichvucong.bocongan.gov.vn), form-builder jQuery + bootstrap-select, ô name CongDan__fs* / CongDan_*.
const sim: ProcedureSim = {
  bca: "dang-ky-xe-lan-dau-sxlr",
  note: "Phần III–V điền sẵn từ giấy; người dân nhập Mã bảo mật + bấm Tra cứu thì cổng ghi đè bằng dữ liệu CSDL. Ba ô ảnh đầu trang thuộc bước đính kèm, không mô phỏng ở đây.",
};
export default sim;
