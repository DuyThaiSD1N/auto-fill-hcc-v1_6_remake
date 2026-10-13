import type { ProcedureSim } from "../../registry";

// Thủ tục đăng ký khai sinh (1.001193).
// Đã chuyển sang Cổng DVC quốc gia mới (SurveyJS, pipeline khai_sinh_dvc_moi). Lượt cũ cùng mã vẫn là eForm moj (2093) →
// giữ cả hai mẫu, Monitor chọn theo output từng lượt (comp "sjs-*" = cổng mới).
const sim: ProcedureSim = {
  forms: [2093],
  surveyjs: "khai-sinh-dang-ky-thuong",
};
export default sim;
