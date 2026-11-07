import type { ProcedureSim } from "../../registry";

// Thủ tục đăng ký khai tử (1.000656).
// Đã chuyển sang Cổng DVC quốc gia mới (SurveyJS, pipeline khai_tu_dvcqg). Lượt cũ cùng mã vẫn là eForm moj (2053) →
// giữ cả hai mẫu, Monitor chọn theo output từng lượt (comp "sjs-*" = cổng mới).
const sim: ProcedureSim = {
  forms: [2053],
  surveyjs: "khai-tu",
};
export default sim;
