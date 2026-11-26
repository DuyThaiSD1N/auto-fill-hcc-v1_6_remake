import type { ProcedureSim } from "../../registry";

// Đăng ký khai tử có yếu tố nước ngoài (1.001766) — cổng Bộ Tư pháp, eForm khai tử 2053 (pipeline khai_tu_nuoc_ngoai).
const sim: ProcedureSim = {
  forms: [2053],
  note: "Mẫu 2053 chụp 26/09/2026 chưa có ô ngày sinh người yêu cầu (NgaySinhC) mà mapping BA của 1.001766 có — ô này "
    + "hiện là không tìm thấy trên mô phỏng. Ô mục I (ngày sinh, số định danh, ngày/nơi cấp) cổng đổ sẵn theo tài khoản.",
};
export default sim;
