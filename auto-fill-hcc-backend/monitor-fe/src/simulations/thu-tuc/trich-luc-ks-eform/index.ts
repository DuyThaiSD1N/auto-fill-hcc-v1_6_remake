import type { ProcedureSim } from "../../registry";

// Cấp bản sao Trích lục hộ tịch, bản sao Giấy khai sinh (2.000635) — form CŨ eForm Bộ Tư pháp (dichvucongnganhtuphap.moj.gov.vn),
// key -eform chạy pipeline cũ trich_luc; bản Cổng DVC quốc gia mới là trich-luc-ks.
const sim: ProcedureSim = {
  forms: [2086],
};
export default sim;
