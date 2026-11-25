import type { ProcedureSim } from "../../registry";

// Cấp thẻ căn cước cho người từ đủ 14 tuổi — 2.000200 (cấp tỉnh) / 1.014061 (cấp xã), cùng trang
// dvc-CCCD-tren-14-tuoi.html; mã theo radio "Cấp thực hiện". Không đính kèm.
const sim: ProcedureSim = {
  bca: "tu-du-14-tuoi",
  note: "Mã thủ tục theo radio Cấp thực hiện: Cấp Tỉnh = 2.000200, Cấp Xã = 1.014061. Radio người kê khai + Phần II theo tài khoản đăng nhập.",
};
export default sim;
