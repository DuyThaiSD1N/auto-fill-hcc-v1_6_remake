import type { ProcedureSim } from "../../registry";

// Cấp hộ chiếu phổ thông ở trong nước (1.001456) — eForm Nth cổng bocongan (CongDan__fs*), sau bước chọn trường hợp hồ sơ.
// Ô (17) chỉ có cơ quan đã chọn ở bước trước → extension chọn mục đầu tiên (firstOption). Giấy của người khác chủ tài
// khoản VNeID thì BE chặn, trả 0 ô.
const sim: ProcedureSim = {
  bca: "cap-ho-chieu-pho-thong",
  note: "Ô khoá theo CSDLQG (họ tên, số CCCD, giới tính, ngày sinh, cha/mẹ) BE không phát. Đính kèm (bảng Thành phần hồ sơ) ở bước sau, không mô phỏng ở đây.",
};
export default sim;
