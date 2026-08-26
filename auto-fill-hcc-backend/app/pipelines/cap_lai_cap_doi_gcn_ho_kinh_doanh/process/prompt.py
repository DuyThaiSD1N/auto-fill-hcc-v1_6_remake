"""Quy tắc đọc hồ sơ cấp lại/cấp đổi GCN đăng ký hộ kinh doanh."""

EXTRA_RULES = """
Bạn đang trích xuất hồ sơ "Cấp lại Giấy chứng nhận đăng ký hộ kinh doanh, Cấp đổi sang Giấy chứng nhận đăng ký hộ kinh doanh".

PHÂN BIỆT NGUỒN:
- Giấy đề nghị cấp lại/cấp đổi (Mẫu số 2) cho biết tên, mã HKD, số định danh, loại yêu cầu, lý do và người ký.
- Giấy chứng nhận đăng ký hộ kinh doanh là nguồn trạng thái hiện tại: tên, mã HKD, chủ hộ và thông tin liên hệ.
- CCCD/căn cước vật lý chỉ là nguồn nhân thân; không tự kết luận mọi CCCD là người nộp.

QUY TẮC BẮT BUỘC:
1. HoKinhDoanh_MaSo: lấy đúng dãy tại nhãn "Mã số hộ kinh doanh". Bỏ khoảng trắng/dấu chấm/dấu gạch nhưng giữ toàn bộ chữ số; mã cũ có thể không đủ 12 chữ số.
2. DeNghi_Loai chỉ nhận cap_lai hoặc cap_doi. Chọn cap_lai khi tiêu đề/ô đánh dấu nói cấp lại; chọn cap_doi chỉ khi tài liệu nói rõ cấp đổi sang Giấy chứng nhận đăng ký hộ kinh doanh. Không biến cap_doi thành cap_lai.
3. DeNghi_LyDo giữ ngắn gọn, đúng nội dung người khai. Nếu ô lý do trống hoặc không đọc được thì để trống, tuyệt đối không suy đoán.
4. HienTai_Ten giữ đầy đủ tên hiện tại; không tự thêm hoặc bỏ tiền tố "HỘ KINH DOANH".
5. NguoiKy chỉ lấy người ký cuối Giấy đề nghị hoặc người được ủy quyền có căn cứ. Có thể bổ sung nhân thân còn thiếu từ ChuHo/CCCD khi khớp họ tên hoặc số định danh.
6. Cccd_DanhSach là field BẮT BUỘC khi hồ sơ có thẻ căn cước vật lý. Với MỖI file/khối OCR có "CĂN CƯỚC CÔNG DÂN", "Citizen Identity Card" hoặc "THẺ CĂN CƯỚC", trả đúng một object gồm tối thiểu hoTen, soDinhDanh và diaChi đọc từ "Nơi thường trú/Place of residence". Không lấy số CCCD chỉ được nhắc trong Giấy đề nghị/GCN làm thẻ căn cước giả.
7. Địa chỉ object luôn là {quocGia,tinh,xa,diaChi}; diaChi không lặp tỉnh/xã. Ngày theo dd/mm/yyyy.

8. ỦY QUYỀN: áp dụng cùng logic thủ tục Đăng ký kinh doanh hộ kinh doanh.
	 - Nhận diện giấy ủy quyền thật qua tiêu đề "GIẤY ỦY QUYỀN"/"VĂN BẢN ỦY QUYỀN" và các mục bên ủy quyền, bên được ủy quyền.
	 - Bên ủy quyền (thường là chủ hộ) -> UyQuyen_NguoiUyQuyen_HoTen, UyQuyen_NguoiUyQuyen_SoDinhDanh.
	 - Bên được ủy quyền (người đi nộp hồ sơ thay) -> đầy đủ nhóm UyQuyen_NguoiDuocUyQuyen_* từ giấy ủy quyền.
		 Giấy ủy quyền là nguồn chính; chỉ dùng CCCD của đúng người đó để bù field bị thiếu. Trả UyQuyen_CoGiayUyQuyen=true.
	 - Người được ủy quyền có thể chỉ xuất hiện trong giấy ủy quyền, không có CCCD kèm theo; vẫn phải trả nhóm UyQuyen_* để hệ thống đối chiếu với tài khoản đăng nhập.
	 - Nếu có từ 2 CCCD, trả HasMultipleCCCD=true và liệt kê đủ trong Cccd_DanhSach; không suy vai trò theo thứ tự file.
	 - Không đưa người chỉ có trong giấy ủy quyền vào Cccd_DanhSach.

Không trả tên field UI ctl00$C$...; chỉ trả field compact trong schema.
"""
