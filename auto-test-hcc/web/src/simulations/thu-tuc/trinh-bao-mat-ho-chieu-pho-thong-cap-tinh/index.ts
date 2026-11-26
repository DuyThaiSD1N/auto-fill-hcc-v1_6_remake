import type { ProcedureSim } from "../../registry";

// Trình báo mất hộ chiếu phổ thông cấp tỉnh (1.001445) — eForm Nth cổng bocongan (CongDan__fs*). Pipeline riêng, mẫu
// riêng với bản cấp xã: ô (17) Cơ quan tiếp nhận ở cuối trang, extension chọn mục đầu tiên (firstOption).
const sim: ProcedureSim = {
  bca: "trinh-bao-mat-ho-chieu-cap-tinh",
  note: "Ô khoá theo tài khoản VNeID BE không phát; giấy của người khác (từ 14 tuổi) thì BE chặn. Đính kèm 2 dòng ở bảng Thành phần hồ sơ, không mô phỏng ở đây.",
};
export default sim;
