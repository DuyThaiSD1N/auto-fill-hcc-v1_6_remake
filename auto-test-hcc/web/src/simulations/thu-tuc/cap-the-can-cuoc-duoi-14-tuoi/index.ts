import type { ProcedureSim } from "../../registry";

// Cấp thẻ căn cước cho người dưới 14 tuổi — MỘT key cho 2 mã: 1.012549 (cấp tỉnh) và 1.014062 (cấp xã), cùng trang
// dvc-CCCD-duoi-14-tuoi.html; mã theo radio "Cấp thực hiện" (có xã trên giấy = Cấp Xã). Không đính kèm.
const sim: ProcedureSim = {
  bca: "duoi-14-tuoi",
  note: "Mã thủ tục theo radio Cấp thực hiện: Cấp Tỉnh = 1.012549, Cấp Xã = 1.014062. Quan hệ với trẻ chọn theo tài khoản đăng nhập.",
};
export default sim;
