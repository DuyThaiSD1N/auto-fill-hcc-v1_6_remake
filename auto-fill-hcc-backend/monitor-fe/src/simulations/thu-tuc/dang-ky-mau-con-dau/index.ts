import type { ProcedureSim } from "../../registry";

// Đăng ký mẫu con dấu mới (2.001428) — eForm Nth cổng bocongan (CongDan__fs*), sau bước chọn trường hợp hồ sơ.
// Ô (1) chỉ có cơ quan đã chọn ở bước trước → extension chọn mục đầu tiên (firstOption).
const sim: ProcedureSim = {
  bca: "dang-ky-mau-con-dau",
  note: "Hình thức nhận kết quả + đính kèm ở bước sau (trang Thông tin hồ sơ), không mô phỏng ở đây.",
};
export default sim;
