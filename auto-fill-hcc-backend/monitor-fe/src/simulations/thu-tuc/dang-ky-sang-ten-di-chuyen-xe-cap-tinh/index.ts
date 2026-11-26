import type { ProcedureSim } from "../../registry";

// Đăng ký sang tên, di chuyển xe tại Công an cấp tỉnh (2.000076). Cổng DVC Bộ Công an (dichvucong.bocongan.gov.vn),
// form-builder jQuery + bootstrap-select, ô name CongDan__fs* / CongDan_*. BE chọn chủ xe tự nộp / khai hộ theo tài khoản.
const sim: ProcedureSim = {
  bca: "dang-ky-sang-ten-di-chuyen-xe",
  note: "Ô chủ xe / khối người được ủy quyền hiện theo ô Phần I mà BE tích (BE đã so tài khoản VNeID). Phần VI (chứng từ, thông tin xe, LPTB) cổng tự điền sau Tra cứu, không mô phỏng. Thủ tục không có đính kèm.",
};
export default sim;
