import type { ProcedureSim } from "../../registry";

// Thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc (1.004859).
// Đã chuyển sang Cổng DVC quốc gia mới (SurveyJS, pipeline cai_chinh_dvc_moi). Lượt cũ cùng mã vẫn là eForm moj (2028) →
// giữ cả hai mẫu, Monitor chọn theo output từng lượt (comp "sjs-*" = cổng mới).
const sim: ProcedureSim = {
  forms: [2028],
  surveyjs: "thay-doi-cai-chinh-ho-tich",
};
export default sim;
