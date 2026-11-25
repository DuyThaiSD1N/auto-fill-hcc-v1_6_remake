import type { ProcedureSim } from "../../registry";

// Xác nhận thông tin về cư trú (1.010041) — cùng trang + bộ id với Đăng ký thường trú, TT=THUONGTRU_09. Trường hợp
// "trên/khác địa bàn" theo nơi thường trú so với cơ quan; nhận bản giấy thì có ô Số lượng phiếu.
const sim: ProcedureSim = {
  bca: "xac-nhan-thong-tin-ve-cu-tru",
  note: "Trường hợp trên/khác địa bàn: BE so xã nơi thường trú với cơ quan, không rõ thì chọn \"trên địa bàn\" (tô vàng).",
};
export default sim;
