import type { ProcedureSim } from "../../registry";

// Cấp đổi thẻ căn cước (2.001195) — Cổng DVC Bộ Công an, trang dvc-CCCD-cap-doi-hoac-cap-lai.html?TT=CAP_DOI (cùng trang
// với cấp lại 2.001194 ?TT=CAP_LAI, khác bảng lý do). Không đính kèm.
const sim: ProcedureSim = {
  bca: "cap-doi-cap-lai",
  note: "Radio người kê khai, Phần II và SĐT/email Phần I đổi theo tài khoản VNeID đăng nhập — chọn tài khoản ở thanh trên form.",
};
export default sim;
