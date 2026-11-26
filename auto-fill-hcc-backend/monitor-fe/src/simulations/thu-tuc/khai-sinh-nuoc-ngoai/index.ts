import type { ProcedureSim } from "../../registry";

// Đăng ký khai sinh có yếu tố nước ngoài (2.000528) — cổng Bộ Tư pháp, eForm khai sinh 2093 (cùng mẫu khai sinh thường,
// pipeline khai_sinh_nuoc_ngoai).
const sim: ProcedureSim = {
  forms: [2093],
  note: "Cổng dùng chung mẫu với đăng ký khai sinh trong nước.",
};
export default sim;
