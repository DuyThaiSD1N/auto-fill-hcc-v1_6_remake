import type { ProcedureSim } from "../../registry";

// Thủ tục cấp Giấy xác nhận tình trạng hôn nhân (1.004873).
// Đã chuyển sang Cổng DVC quốc gia mới (SurveyJS, pipeline xac_nhan_tthn_dvc_moi). Lượt cũ cùng mã vẫn là eForm moj (2089) →
// giữ cả hai mẫu, Monitor chọn theo output từng lượt (comp "sjs-*" = cổng mới).
const sim: ProcedureSim = {
  forms: [2089],
  surveyjs: "xac-nhan-tinh-trang-hon-nhan",
};
export default sim;
