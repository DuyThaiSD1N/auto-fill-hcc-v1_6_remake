import type { ProcedureSim } from "../../registry";

// Cấp Giấy xác nhận tình trạng hôn nhân (1.004873) — form CŨ eForm Bộ Tư pháp (dichvucongnganhtuphap.moj.gov.vn),
// key -eform chạy pipeline cũ xac_nhan_tthn; bản Cổng DVC quốc gia mới là xac-nhan-tinh-trang-hon-nhan.
const sim: ProcedureSim = {
  forms: [2089],
};
export default sim;
