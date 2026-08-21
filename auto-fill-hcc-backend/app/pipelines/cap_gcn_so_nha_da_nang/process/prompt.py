"""Prompt rules đặc thù cho "Cấp mới/cấp lại Giấy chứng nhận số nhà" (cổng DVC Đà Nẵng — Form.io)."""

EXTRA_RULES = """Thủ tục: Cấp mới/cấp lại Giấy chứng nhận số nhà (biển số nhà) — cổng DVC TP Đà Nẵng.
Đầu vào gồm: Đơn đề nghị cấp/cấp lại giấy chứng nhận số nhà (do chủ nhà điền tay, đã ký), Giấy chứng
nhận quyền sử dụng đất (sổ đỏ/sổ hồng), và CCCD của chủ nhà (nếu có).

HAI vai — tách RIÊNG:
- CHỦ HỒ SƠ (ChuHoSo_*) = CHỦ SỞ HỮU NHÀ, người KÝ Đơn đề nghị cấp giấy chứng nhận số nhà. Là đối tượng
  thụ hưởng (người được cấp GCN số nhà). Thường CÁ NHÂN; có thể TỔ CHỨC.
- NGƯỜI NỘP (NguoiNop_*) = người trực tiếp nộp hồ sơ trên cổng. Thủ tục số nhà HẦU NHƯ LUÔN TỰ NỘP: nếu
  KHÔNG có Hợp đồng ủy quyền thì người nộp CHÍNH LÀ chủ hồ sơ → NguoiNop_HoTen = ChuHoSo_HoTen, và nhân
  thân (ngày sinh/CCCD/địa chỉ) lấy từ CCCD/Đơn của chính chủ nhà. Chỉ khi có HỢP ĐỒNG ỦY QUYỀN (người
  khác nộp thay) thì NguoiNop mới KHÁC ChuHoSo.

⚠ PHÂN BIỆT 3 ĐỊA CHỈ (đừng lẫn):
1. ChuHoSo_DiaChiXinCap = địa chỉ NHÀ đang xin cấp số (vd "5A Ngõ Chi Lan, phường Hải Châu, TP Đà Nẵng")
   — ghi trong Đơn đề nghị ("đề nghị cấp giấy chứng nhận số nhà tại...").
2. NguoiNop_DiaChi = địa chỉ thường trú/LIÊN HỆ hiện tại của người nộp (Nơi thường trú trên CCCD / tổ dân
   phố ghi trong Đơn) — dùng cho nhóm địa chỉ liên hệ (tinh/xa/diaChi).
3. Địa chỉ trên Giấy chứng nhận QSDĐ = địa chỉ thửa đất theo hồ sơ đất — KHÔNG điền vào 2 trường trên.

ĐỊA CHỈ NGƯỜI NỘP (NguoiNop_DiaChi): tách object {quocGia,tinh,xa,diaChi}. tinh='Tỉnh/Thành phố …',
xa=phường/xã, diaChi số nhà/đường/tổ dân phố (KHÔNG kèm phường/xã/tỉnh).

GIỚI TÍNH: nếu không có nhãn "Giới tính", SUY từ danh xưng "Ông"/"Bà" trong Đơn đề nghị hoặc Giấy chứng
nhận QSDĐ ("Bà"→Nữ, "Ông"→Nam). Không có căn cứ thì bỏ.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
