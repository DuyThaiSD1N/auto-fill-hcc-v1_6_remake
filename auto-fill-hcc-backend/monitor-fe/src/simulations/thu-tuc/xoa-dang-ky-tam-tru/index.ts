import type { ProcedureSim } from "../../registry";

// Xóa đăng ký tạm trú (1.010028) — cùng trang + bộ id với Đăng ký tạm trú, TT=TAMTRU_06. Cơ quan cổng chọn sẵn
// Hà Nội / Ba Đình nên BE chọn đè; khối nhận kết quả theo email trên giấy.
const sim: ProcedureSim = {
  bca: "xoa-dang-ky-tam-tru",
  note: "Lượt trước 24/11 chưa có khối nhận kết quả (cboRECEIVER_TYPE) → ô Email nhận kết quả đỏ theo lựa chọn mặc định \"Qua email\" của cổng.",
};
export default sim;
