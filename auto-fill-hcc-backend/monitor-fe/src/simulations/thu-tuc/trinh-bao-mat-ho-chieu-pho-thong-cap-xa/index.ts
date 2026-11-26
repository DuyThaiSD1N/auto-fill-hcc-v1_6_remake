import type { ProcedureSim } from "../../registry";

// Trình báo mất hộ chiếu phổ thông cấp xã (1.010386) — eForm Nth cổng bocongan (CongDan__fs*). Khối Nơi tiếp nhận đầu
// trang khoá theo bước "Lựa chọn DVC" (cổng chọn sẵn Công an xã), BE không phát.
const sim: ProcedureSim = {
  bca: "trinh-bao-mat-ho-chieu-cap-xa",
  note: "Tài khoản khác người trên giấy không chặn (cha mẹ khai thay), chỉ bỏ ngày cấp / nơi cấp CCCD. Đính kèm 1 dòng (đơn TK05), không mô phỏng ở đây.",
};
export default sim;
