import type { ProcedureSim } from "../../registry";

// Cấp thị thực cho người nước ngoài tại Việt Nam (1.001194) — eForm Nth cổng bocongan (CongDan__fs*). Hai ô ảnh đầu
// trang (chân dung 4x6 + trang nhân thân hộ chiếu) BE tự gắn; khối Thân nhân bảo lãnh khoá theo tài khoản đăng nhập.
const sim: ProcedureSim = {
  bca: "cap-thi-thuc-nnn",
  note: "Quốc tịch / cửa khẩu / mục đích nhập cảnh chưa có danh mục cổng nên chưa kiểm option. Bảng Thành phần hồ sơ (3 dòng) cùng trang, không mô phỏng ở đây.",
};
export default sim;
