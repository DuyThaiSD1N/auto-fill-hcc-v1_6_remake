"""Prompt rules đặc thù cho "Cấp, cấp lại Giấy phép khai thác thủy sản" (Form.io — cổng Nông nghiệp &
Môi trường)."""

EXTRA_RULES = """Thủ tục: Cấp, cấp lại Giấy phép khai thác thủy sản. Đầu vào gồm: CCCD của người đề nghị
(chủ tàu) và Đơn đề nghị cấp Giấy phép khai thác thủy sản (Mẫu số 04.KT — cấp mới) HOẶC Đơn đề nghị cấp
lại (Mẫu số 05.KT — cấp lại), có thể có thêm CCCD của người nộp thay.

Form online có: nhân thân người nộp/chủ hồ sơ (Phần I/II) VÀ nội dung Đơn đề nghị (Phần III) — trích cả hai.

HAI vai — tách RIÊNG:
- NGƯỜI ĐỀ NGHỊ (NguoiDeNghi_*) = CHỦ HỒ SƠ = chủ tàu đứng tên Đơn Mẫu 04/05.KT. Đây là người CHÍNH.
  Trích toàn bộ nhân thân của người này.
- NGƯỜI NỘP (NguoiNop_*) = tài khoản đứng nộp trên cổng. ĐA SỐ tự nộp → CHÍNH LÀ chủ tàu → BỎ TRỐNG
  NguoiNop_*. Chỉ khi có người khác NỘP THAY và hồ sơ có CCCD RIÊNG của người nộp thì trích NguoiNop_* từ
  CCCD đó. Xem khối <nguoi_nop_context> ở cuối (nếu có).

⚠ KHÔNG lấy CCCD người nộp thay làm NguoiDeNghi_* — giấy phép cấp cho chủ tàu đứng tên Đơn.

NGUỒN NHÂN THÂN (NguoiDeNghi_*): ưu tiên CCCD; bổ sung từ Đơn Mẫu 04/05.KT (Họ tên chủ tàu, Mã định
danh/CCCD, Loại giấy tờ, Cơ quan cấp, ngày cấp, Nơi thường trú, Điện thoại). Số định danh ưu tiên 12 chữ
số. Nơi cấp: CCCD gắn chip không in nhãn riêng → lấy 'Cơ quan cấp' ở Đơn. Chuẩn hóa tên cơ quan (Cục Cảnh
sát QLHC về TTXH / Bộ Công an). ThuongTru tách object {quocGia,tinh,xa,diaChi}, diaChi chỉ chi tiết (số
nhà/khóm/ấp/thôn).

⚠ NGÀY CẤP CCCD (NguoiDeNghi_NgayCap): ưu tiên lấy 'Ngày cấp'/'Ngày cấp CCCD' ghi trên Đơn Mẫu 04/05.KT.
→ LẤY TỪ Đơn/Tờ khai, KHÔNG điền ngày khác, KHÔNG bịa.

⚠ NGÀY SINH (NguoiDeNghi_NgaySinh): CHỈ lấy từ CCCD (dòng 'Ngày sinh/Date of birth'). Đơn Mẫu 04/05.KT
KHÔNG có mục ngày sinh → nếu hồ sơ chỉ có Đơn (không có ảnh CCCD) thì BỎ TRỐNG ngày sinh. TUYỆT ĐỐI KHÔNG
lấy 'Ngày cấp'/'Ngày cấp CCCD' hay bất kỳ ngày nào khác trong Đơn/Giấy phép làm ngày sinh.

NỘI DUNG ĐƠN ĐỀ NGHỊ (Phần III) — chung: ToKhai_KinhGui = mục 'Kính gửi'; ToKhai_DiaDanh = tên tỉnh/thành
nơi lập đơn; ToKhai_LoaiGiayTo = 'Loại giấy tờ' (số định danh 12 số → 'Thẻ Căn cước công dân'); ToKhai_CoQuanCap
= 'Cơ quan cấp'.

HAI TRƯỜNG HỢP LOẠI TRỪ — chỉ điền nhóm ứng với Đơn THỰC SỰ có:
- ĐƠN CẤP MỚI (Mẫu 04.KT): điền CapMoi_SoDangKy (Số đăng ký tàu/Số GCN đăng ký tàu cá) / CapMoi_SoGcnAtkt
  (Số GCN an toàn kỹ thuật) / CapMoi_TrangThietBi / CapMoi_ThietBiGsht (thiết bị giám sát hành trình) /
  CapMoi_NgheChinh / CapMoi_NghePhu. BỎ TRỐNG mọi CapLai_*.
- ĐƠN CẤP LẠI (Mẫu 05.KT): điền CapLai_SoGiayPhep_GiayPhep + CapLai_SoGiayPhep_ToKhai / CapLai_NgayCap /
  CapLai_NgayHetHan / CapLai_LyDo (lý do đã tích: 'Giấy phép bị mất'/'Giấy phép bị hư hỏng'/'Thay đổi
  thông tin'/'Giấy phép hết hạn'). BỎ TRỐNG mọi CapMoi_*.
  ⚠ SỐ GIẤY PHÉP CŨ tách 2 trường theo ĐÚNG NGUỒN (Python tự chọn nguồn — ĐỪNG tự ưu tiên, ĐỪNG chép chéo):
    • CapLai_SoGiayPhep_GiayPhep = số in trên CHÍNH tờ 'GIẤY PHÉP KHAI THÁC THỦY SẢN' (dòng 'Số: …',
      vd '30/LC/2025/ĐNa-GPKTTS'). Hồ sơ KHÔNG kèm tờ giấy phép → bỏ trống.
    • CapLai_SoGiayPhep_ToKhai = số ghi trong Đơn Mẫu 05 (dòng 'Tôi đã được cấp Giấy phép … số: …').
    Mỗi trường CHỈ lấy ĐÚNG nguồn của nó.
  ⚠ NGÀY CẤP / NGÀY HẾT HẠN của giấy phép cũ: ưu tiên đọc ở chính tờ GIẤY PHÉP; dự phòng Đơn Mẫu 05.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
