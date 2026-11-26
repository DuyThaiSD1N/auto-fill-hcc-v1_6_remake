import type { ProcedureSim } from "../../registry";

// Thu hồi chứng nhận đăng ký xe, biển số xe tại Cục (2.000311). Cổng DVC Bộ Công an, ô CongDan__fs*.
// Mẫu dùng chung với cấp tỉnh (2.001485) và cấp xã (1.010919).
const sim: ProcedureSim = {
  bca: "thu-hoi-dang-ky-bien-so-xe",
  note: "Ô chủ xe / khối người được ủy quyền hiện theo ô Phần I mà BE tích (BE đã so tài khoản VNeID). Phần VI cổng ghi đè sau Tra cứu. Khối chủ xe mới bắt buộc theo Lý do thu hồi — mô phỏng không tính đỏ. Thủ tục không có đính kèm.",
};
export default sim;
