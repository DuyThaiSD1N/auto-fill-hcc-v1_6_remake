import type { ProcedureSim } from "../../registry";

// Thông báo lưu trú (2.001159) — Cổng DVC Bộ Công an, trang thong-bao-luu-tru.html. Mỗi người lưu trú một lượt modal
// "Thêm mới người lưu trú" (comp bca-guest-list), mô phỏng thành một dòng bảng theo id ô guest_*.
const sim: ProcedureSim = {
  bca: "thong-bao-luu-tru",
  note: "Cơ quan thực hiện (accomStay_cbo*) BE gửi không kèm cityId/wardId — extension tự lấy cặp ô này; trang không có đính kèm.",
};
export default sim;
