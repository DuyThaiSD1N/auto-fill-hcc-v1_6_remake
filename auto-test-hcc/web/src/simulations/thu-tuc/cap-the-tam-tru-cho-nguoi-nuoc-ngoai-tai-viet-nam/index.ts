import type { ProcedureSim } from "../../registry";

// Cấp thẻ tạm trú cho người nước ngoài tại Việt Nam (1.003460) — eForm Nth cổng bocongan (CongDan__fs*), khuôn thị thực
// 1.001194. Hai ô ảnh đầu trang BE tự gắn; Ghi chú (Phần VIII) ghi trang của từng giấy trong tệp gộp.
const sim: ProcedureSim = {
  bca: "cap-the-tam-tru-nnn",
  note: "Quốc tịch / cửa khẩu / mục đích nhập cảnh chưa có danh mục cổng nên chưa kiểm option. Bảng Thành phần hồ sơ (3 dòng + Giấy tờ khác) cùng trang, không mô phỏng ở đây.",
};
export default sim;
