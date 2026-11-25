import type { ProcedureSim } from "../../registry";

// Điều chỉnh thông tin về cư trú (1.010039) — cùng trang + bộ id với Đăng ký thường trú, TT=THUONGTRU_08.
// Trường hợp duy nhất "Thay đổi chủ hộ".
const sim: ProcedureSim = {
  bca: "dieu-chinh-thong-tin-ve-cu-tru",
  note: "Khối chủ hộ là chủ hộ hiện tại (cũ); bảng thành viên cùng thay đổi ghi quan hệ với chủ hộ mới theo CT01.",
};
export default sim;
