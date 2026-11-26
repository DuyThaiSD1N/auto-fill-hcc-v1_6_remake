import type { ProcedureSim } from "../../registry";

// Tách hộ (1.010038) — cùng trang + bộ id với Đăng ký thường trú, TT=THUONGTRU_05. Người đề nghị là chủ hộ mới,
// không có khối chủ hộ; bảng thành viên là người tách theo.
const sim: ProcedureSim = {
  bca: "tach-ho",
  note: "Trường hợp BE gửi \"Tách hộ\", extension khớp lỏng theo chữ — danh mục cổng chưa có nên chưa kiểm option.",
};
export default sim;
