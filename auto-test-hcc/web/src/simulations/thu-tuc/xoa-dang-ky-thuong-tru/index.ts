import type { ProcedureSim } from "../../registry";

// Xóa đăng ký thường trú (1.003197) — link kê khai là trang thủ tục bocongan (tthc?matt=26348) → "Nộp hồ sơ" → trang
// thường trú TT=THUONGTRU_02, cùng bộ id với Đăng ký thường trú. Có khối chủ hộ; khối nơi đề nghị ẩn.
const sim: ProcedureSim = {
  bca: "xoa-dang-ky-thuong-tru",
  note: "Trường hợp theo lý do xóa ở mục 10 CT01 (người đề nghị là chủ hộ → nhãn \"Cả hộ\"); Nội dung đề nghị chỉ ghi khi câu CT01 có chữ \"xóa\".",
};
export default sim;
