"""Prompt rules đặc thù cho "Cấp lại Chứng chỉ hành nghề thú y" (Form.io — Cổng DVC quốc gia)."""

EXTRA_RULES = """Thủ tục: Cấp lại Chứng chỉ hành nghề thú y (mã 1.005319). Đầu vào gồm: Đơn đăng ký cấp
lại Chứng chỉ hành nghề thú y (Mẫu 03.HNTY), CCCD của người đề nghị, bản chụp CHỨNG CHỈ HÀNH NGHỀ THÚ Y
ĐÃ CẤP (nếu còn giữ), ảnh 4x6, có thể có thêm CCCD của người nộp thay.

Form online có mục "Thông tin người nộp hồ sơ" (cổng tự đổ tài khoản đăng nhập, ta KHÔNG động vào) và
mục "Thông tin chủ hồ sơ" — chủ hồ sơ mới là người đứng đơn.
- NGƯỜI ĐỀ NGHỊ (NguoiDeNghi_*) = người đứng tên Đơn 03.HNTY = người được cấp lại chứng chỉ = CHỦ HỒ SƠ
  trên form. Đây là người CHÍNH, trích ĐẦY ĐỦ nhân thân của họ, gồm cả giới tính và nơi cấp giấy tờ.
- NguoiNop_* CHỈ dùng khi có người KHÁC nộp thay VÀ hồ sơ có CCCD riêng của người nộp; điền để tách bạch,
  KHÔNG bao giờ dùng làm nhân thân người đề nghị. Tự nộp → bỏ trống. Xem khối <nguoi_nop_context> ở cuối
  (nếu có).

⚠ KHÔNG lấy nhân thân trên CCCD người nộp thay làm NguoiDeNghi_* — chứng chỉ cấp cho NGƯỜI ĐỨNG TÊN ĐƠN.
⚠ Đơn 03.HNTY thường KHÔNG ghi số căn cước. Hồ sơ không có CCCD của người đứng đơn thì BỎ TRỐNG
NguoiDeNghi_SoDinhDanh, KHÔNG mượn số của ai khác.

NGUỒN NHÂN THÂN (NguoiDeNghi_*): ưu tiên CCCD; bổ sung từ Đơn 03.HNTY (Tên tôi là, Ngày tháng năm sinh,
Địa chỉ thường trú, Số điện thoại liên hệ). ThuongTru tách object {quocGia,tinh,xa,diaChi}, diaChi chỉ
phần chi tiết (số nhà/khóm/ấp/thôn/tổ).
⚠ Trong Đơn 03.HNTY, dòng "Ngày cấp" nằm NGAY SAU "Bằng cấp chuyên môn" là ngày cấp BẰNG, KHÔNG phải
ngày cấp CCCD → chỉ điền NguoiDeNghi_NgayCapCCCD khi đọc được ngày cấp trên chính thẻ CCCD.

NỘI DUNG ĐƠN 03.HNTY (Don_*):
- Don_KinhGui = mục 'Kính gửi' chép nguyên văn.
- Don_LaNguoiNuocNgoai = 'Có' CHỈ khi giấy tờ thể hiện rõ quốc tịch nước ngoài / hộ chiếu nước ngoài;
  có CCCD Việt Nam → 'Không'.
- Don_BangCapChuyenMon = tên bằng cấp chuyên môn (vd 'Bác sĩ thú y'), KHÔNG kèm ngày/nơi cấp bằng.
- Don_PhamViHanhNghe = dòng phạm vi hành nghề ĐƯỢC ĐÁNH DẤU (☑/x/✓) trong danh sách của đơn. Chép
  NGUYÊN VĂN và ĐỦ ĐUÔI ('… cho động vật trên cạn' / '… cho động vật thủy sản'), vì hệ thống phải khớp
  đúng dòng để tự tích trên form. Nhiều dòng được tích thì ngăn cách bằng ';'. KHÔNG liệt kê dòng không
  được tích, KHÔNG rút gọn.
- Don_LyDoCapLai = lý do cấp lại (mất / hư hỏng / sai sót / thay đổi thông tin). Đơn không ghi → bỏ trống.
- Don_DiaDiem + Don_NgayLamDon = địa danh và ngày ở dòng '……, ngày … tháng … năm …'.
- Don_NguoiLamDon = họ tên người ký cuối đơn.

CHỨNG CHỈ HÀNH NGHỀ CŨ (CCHNCu_*): chỉ trích khi hồ sơ CÓ bản chụp chứng chỉ cũ hoặc Đơn ghi lại.
CCHNCu_SoDangKy = số đăng ký/số hiệu chứng chỉ; CCHNCu_NgayHetHan = dòng 'Chứng chỉ có giá trị đến ngày
…'. KHÔNG nhầm ngày hết hạn với ngày cấp, KHÔNG lấy số của đơn làm số đăng ký. Hồ sơ không có chứng chỉ
cũ thì BỎ TRỐNG cả hai — cán bộ sẽ nhập tay.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
