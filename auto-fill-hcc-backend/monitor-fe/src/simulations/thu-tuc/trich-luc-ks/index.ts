import type { ProcedureSim } from "../../registry";

// Cấp bản sao Trích lục hộ tịch, bản sao Giấy khai sinh (2.000635).
// Đã chuyển sang Cổng DVC quốc gia mới (SurveyJS, pipeline trich_luc_dvc_moi). Lượt cũ cùng mã vẫn là eForm moj (2086) →
// giữ cả hai mẫu, Monitor chọn theo output từng lượt (comp "sjs-*" = cổng mới).
const sim: ProcedureSim = {
  forms: [2086],
  surveyjs: "trich-luc-ks",
};
export default sim;
