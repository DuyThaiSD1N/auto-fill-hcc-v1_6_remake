import type { ProcedureSim } from "../../registry";

// Đăng ký tạm trú (1.004194) — Cổng DVC Bộ Công an, trang dang-ky-tam-tru.html (bộ id *_CODE, khác trang thường trú).
// Cơ quan thực hiện người dân / trợ lý chọn trước, BE không điền.
const sim: ProcedureSim = {
  bca: "dang-ky-tam-tru",
  note: "Lượt trước 24/11 chưa có khối nhận kết quả → ô Email nhận kết quả đỏ; dòng xin ý kiến chỉ có khi chủ sở hữu chỗ ở khác người đăng ký.",
};
export default sim;
