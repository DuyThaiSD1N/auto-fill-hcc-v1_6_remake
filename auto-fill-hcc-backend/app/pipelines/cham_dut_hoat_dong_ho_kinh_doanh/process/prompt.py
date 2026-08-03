"""Quy tắc đọc hồ sơ chấm dứt hoạt động hộ kinh doanh."""

EXTRA_RULES = """
Bạn đang trích xuất hồ sơ "Chấm dứt hoạt động hộ kinh doanh".

PHÂN BIỆT NGUỒN:
- Thông báo về việc chấm dứt hoạt động hộ kinh doanh (Mẫu số 1) cho biết tên/mã HKD, số CCCD của người ký và cam kết thanh toán các khoản nợ.
- Giấy chứng nhận đăng ký hộ kinh doanh là nguồn trạng thái hiện tại: tên, mã HKD, chủ hộ, nơi ở hiện tại và thông tin liên hệ.
- Thông báo của cơ quan thuế về hoàn thành nghĩa vụ nộp thuế là nguồn bổ sung cho ChamDut_LyDo.
- CCCD/căn cước vật lý chỉ là nguồn nhân thân; không tự kết luận mọi CCCD là người nộp.

QUY TẮC BẮT BUỘC:
1. HoKinhDoanh_MaSo: ưu tiên đúng dãy tại nhãn "Mã số hộ kinh doanh"; bỏ khoảng trắng/dấu chấm, không lấy nhầm mã số văn bản thuế.
2. HienTai_Ten: giữ đầy đủ tên hiện tại. Không tự thêm/bỏ tiền tố "HỘ KINH DOANH".
3. ChamDut_LyDo phải là một câu ngắn phù hợp để nhập form. Nếu có Thông báo thuế thì nêu việc đã hoàn thành nghĩa vụ thuế kèm số/ngày/cơ quan đọc được; không bịa phần bị trống.
4. ChuHo lấy mục thông tin chủ hộ trên GCN. Với địa chỉ, form hỏi nơi ở hiện tại nên ưu tiên dòng "Nơi ở hiện tại", không lấy dòng "Nơi thường trú" nếu hai dòng khác nhau.
5. NguoiNop chỉ lấy người ký ở cuối Thông báo hoặc người được ủy quyền có căn cứ. Có thể bổ sung nhân thân còn thiếu từ ChuHo/CCCD khi khớp đồng thời họ tên hoặc số định danh.
6. Cccd_DanhSach là field BẮT BUỘC khi hồ sơ có thẻ căn cước vật lý. Với MỖI file/khối OCR có
   "CĂN CƯỚC CÔNG DÂN" hoặc "Citizen Identity Card", phải trả đúng một object gồm tối thiểu
   hoTen, soDinhDanh và diaChi đọc từ "Nơi thường trú/Place of residence". Không được bỏ qua
   thẻ chỉ vì người trên thẻ khác người ký Thông báo. Không lấy số CCCD chỉ được nhắc trong
   Thông báo/GCN làm một thẻ căn cước giả.
7. Địa chỉ object luôn là {quocGia,tinh,xa,diaChi}; diaChi không lặp tỉnh/xã. Ngày theo dd/mm/yyyy.

Không trả tên field UI ctl00$C$...; chỉ trả field compact trong schema.
"""
