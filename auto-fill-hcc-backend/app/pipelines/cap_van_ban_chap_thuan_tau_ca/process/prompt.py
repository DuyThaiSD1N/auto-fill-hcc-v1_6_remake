"""Prompt rules đặc thù cho "Cấp văn bản chấp thuận đóng mới, cải hoán, thuê, mua tàu cá Việt Nam"
(Form.io — cổng Nông nghiệp & Môi trường)."""

EXTRA_RULES = """Thủ tục: Cấp văn bản chấp thuận đóng mới, cải hoán, thuê, mua tàu cá Việt Nam. Đầu vào
gồm: CCCD của người đề nghị và Tờ khai về việc chấp thuận đóng mới/cải hoán/thuê/mua tàu cá (Mẫu số
12.TC), có thể có thêm CCCD của người nộp thay.

HAI vai — tách RIÊNG:
- NGƯỜI ĐỀ NGHỊ (NguoiDeNghi_*) = CHỦ HỒ SƠ = chủ tàu / cá nhân, tổ chức đề nghị. Đây là người CHÍNH,
  đứng tên Tờ khai Mẫu 12. Trích toàn bộ nhân thân của người này.
- NGƯỜI NỘP (NguoiNop_*) = tài khoản đứng nộp trên cổng. ĐA SỐ tự nộp → CHÍNH LÀ người đề nghị → BỎ
  TRỐNG NguoiNop_*. Chỉ khi có người khác NỘP THAY và hồ sơ có CCCD RIÊNG của người nộp thì trích
  NguoiNop_* từ CCCD đó. Xem khối <nguoi_nop_context> ở cuối (nếu có).

⚠ KHÔNG lấy CCCD người nộp thay làm NguoiDeNghi_* — văn bản cấp cho NGƯỜI ĐỀ NGHỊ đứng tên Tờ khai.

⚠ BẮT BUỘC: CCCD LUÔN in ngày sinh (dòng "Ngày sinh / Date of birth") và giới tính (dòng "Giới tính /
Sex"). Khi có CCCD người đề nghị → PHẢI điền NguoiDeNghi_NgaySinh (dd/mm/yyyy) và NguoiDeNghi_GioiTinh
("Nam"/"Nữ"), TUYỆT ĐỐI không bỏ sót hai field này.

NGUỒN NHÂN THÂN (NguoiDeNghi_*): ưu tiên CCCD; bổ sung từ Tờ khai Mẫu 12 (Họ tên, Địa chỉ thường trú,
Mã định danh, Loại giấy tờ, Cơ quan cấp, ngày cấp). Số định danh: ưu tiên 12 chữ số. Nơi cấp: CCCD gắn
chip không in nhãn riêng → lấy 'Cơ quan cấp' ở Tờ khai. Chuẩn hóa tên cơ quan (Cục Cảnh sát QLHC về TTXH
/ Bộ Công an). ThuongTru tách object {quocGia,tinh,xa,diaChi}, diaChi chỉ chi tiết (số nhà/khóm/ấp/thôn).

NỘI DUNG TỜ KHAI (ToKhai_*): KinhGui = mục 'Kính gửi'; DiaDanh = tên tỉnh/thành nơi lập tờ khai; LoaiGiayTo
= mục 'Loại giấy tờ' (không ghi mà số định danh 12 số → 'Thẻ Căn cước công dân'); CoQuanCap = mục 'Cơ quan
cấp'.

THÔNG SỐ TÀU — Tờ khai Mẫu 12 có HAI khối LOẠI TRỪ, hồ sơ CHỈ khai MỘT:
- Khối "Trường hợp đóng mới tàu cá" → điền DongMoi_VatLieuVo / DongMoi_NgheKhaiThac / DongMoi_VungHoatDong.
- Khối "Trường hợp cải hoán/thuê/mua tàu cá" → điền CaiHoan_KichThuoc (Lmax x Bmax x D, m) /
  CaiHoan_ChieuChim (d, m) / CaiHoan_CongSuat (kW) / CaiHoan_VatLieuVo / CaiHoan_NgheKhaiThac /
  CaiHoan_VungHoatDong / CaiHoan_NoiDung (nội dung đề nghị cải hoán).
CHỈ điền nhóm field ứng với khối mà Tờ khai THỰC SỰ khai (khối kia bỏ trống hoàn toàn). ChieuChim/CongSuat
chỉ lấy phần SỐ.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
