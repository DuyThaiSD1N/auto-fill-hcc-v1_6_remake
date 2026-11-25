import type { ProcedureSim } from "../../registry";

// Đăng ký thường trú (1.004222) — Cổng DVC Bộ Công an, trang dang-ky-thuong-tru.html?TT=THUONGTRU_01 (jQuery +
// bootstrap-select, ô id = name). Khối chủ hộ cổng tự điền + khoá khi lập hộ mới.
const sim: ProcedureSim = {
  bca: "dang-ky-thuong-tru",
  note: "Thứ tự điền: Cơ quan → Trường hợp → Hình thức → người đề nghị; đổi ô trước là cổng xoá ô sau.",
};
export default sim;
