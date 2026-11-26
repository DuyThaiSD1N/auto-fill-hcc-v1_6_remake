import type { ProcedureSim } from "../../registry";

// Đăng ký khai tử lưu động (1.000419) — cổng Bộ Tư pháp, eForm hộ tịch khai tử cùng uuid ô với mẫu 2053
// (pipeline khai_tu_luu_dong dùng chung mapper của khai tử có yếu tố nước ngoài).
const sim: ProcedureSim = {
  forms: [2053],
  note: "Form lưu động không có ô ngày sinh người yêu cầu và radio Có/Không đề nghị cấp bản sao (chỉ còn ô số lượng).",
};
export default sim;
