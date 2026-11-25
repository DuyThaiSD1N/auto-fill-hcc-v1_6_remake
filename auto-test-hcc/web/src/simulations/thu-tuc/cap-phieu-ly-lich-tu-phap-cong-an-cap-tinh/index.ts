import type { ProcedureSim } from "../../registry";

// Cấp Phiếu lý lịch tư pháp — Công an cấp tỉnh (3.000333). Biểu mẫu SurveyJS trên Cổng DVC quốc gia mới
// (dichvucong.gov.vn/nop-ho-so), KHÔNG phải cổng bocongan. Radio "Loại tờ khai" (1 Cá nhân / 2 Khai hộ) đổi cả bộ ô.
const sim: ProcedureSim = {
  surveyjs: "ly-lich-tu-phap",
  note: "Cá nhân = tài khoản là người yêu cầu (nhân thân cổng khoá); Khai hộ = tài khoản là người được ủy quyền / cha mẹ, khai tay toàn bộ người yêu cầu.",
};
export default sim;
