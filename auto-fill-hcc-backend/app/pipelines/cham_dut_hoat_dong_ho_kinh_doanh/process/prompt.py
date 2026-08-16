"""Quy tắc đọc hồ sơ chấm dứt hoạt động hộ kinh doanh."""

EXTRA_RULES = """
Bạn đang trích xuất hồ sơ "Chấm dứt hoạt động hộ kinh doanh".

PHÂN BIỆT NGUỒN:
- Thông báo về việc chấm dứt hoạt động hộ kinh doanh (Mẫu số 1) cho biết tên/mã HKD, số CCCD của người ký và cam kết thanh toán các khoản nợ.
- Giấy chứng nhận đăng ký hộ kinh doanh là nguồn trạng thái hiện tại: tên, mã HKD, chủ hộ, nơi ở hiện tại và thông tin liên hệ.
- Thông báo của cơ quan thuế về hoàn thành nghĩa vụ nộp thuế là nguồn bổ sung cho ChamDut_LyDo.
- CCCD/căn cước vật lý chỉ là nguồn nhân thân; không tự kết luận mọi CCCD là người nộp.

QUY TẮC BẮT BUỘC:
1. HoKinhDoanh_MaSo:
   ⛔ ANTI-PATTERN — SAI TUYỆT ĐỐI:
     Số định danh cá nhân / CCCD / CMND (xuất hiện cạnh nhãn "Số/No", "Số định danh",
     "Số CMND" trên thẻ căn cước hoặc trong tờ khai cá nhân) KHÔNG BAO GIỜ là mã số
     hộ kinh doanh — dù số đó đứng ở đâu trong hồ sơ.
     Nếu hồ sơ KHÔNG có tài liệu kinh doanh ghi nhãn "Mã số hộ kinh doanh" / "MST" / "Số đăng ký"
     → HoKinhDoanh_MaSo = "" (TRỐNG hoàn toàn, không điền bất cứ con số nào).
   ✅ Nguồn HỢP LỆ DUY NHẤT:
     * Thông báo chấm dứt hoặc GCN đăng ký HKD có NHÃN RÕ "Mã số hộ kinh doanh" / "MST".
     * Giấy đề nghị đăng ký hộ kinh doanh nếu có in mã số.
   Bỏ khoảng trắng/dấu chấm/dấu gạch ngang khi lấy mã; không lấy nhầm mã văn bản thuế.
2. HienTai_Ten: giữ đầy đủ tên hiện tại. Không tự thêm/bỏ tiền tố "HỘ KINH DOANH".
3. ChamDut_LyDo phải là một câu ngắn phù hợp để nhập form. Nếu có Thông báo thuế thì nêu việc đã hoàn thành nghĩa vụ thuế kèm số/ngày/cơ quan đọc được; không bịa phần bị trống.
4. ChuHo lấy mục thông tin chủ hộ trên GCN. Với địa chỉ, form hỏi nơi ở hiện tại nên ưu tiên dòng "Nơi ở hiện tại", không lấy dòng "Nơi thường trú" nếu hai dòng khác nhau.
5. NguoiNop chỉ lấy người ký ở cuối Thông báo hoặc người được ủy quyền có căn cứ. Có thể bổ sung nhân thân còn thiếu từ ChuHo/CCCD khi khớp đồng thời họ tên hoặc số định danh.
   - ĐỊA CHỈ NguoiNop: Sau khi xác định người nộp (qua họ tên hoặc số định danh), TÌM trong Cccd_DanhSach
     xem có thẻ CCCD nào khớp với người đó không. Nếu có → BẮT BUỘC lấy diaChi từ "Nơi thường trú"
     trên thẻ CCCD đó điền vào NguoiNop.diaChi.
   - Ví dụ: Thông báo ký bởi "NGUYỄN VĂN A" (khác chủ hộ); hồ sơ có CCCD của người này
     ghi "Nơi thường trú: Tổ 1, Phường X, Quận Y, Thành phố Z" → NguoiNop.diaChi =
     {quocGia:"Việt Nam", tinh:"Thành phố Z", xa:"Phường X", diaChi:"Tổ 1"}.
   - KHÔNG lấy địa chỉ từ Quê quán, từ GCN hay từ phần chủ hộ cho NguoiNop khi đã có CCCD khớp.
6. Cccd_DanhSach là field BẮT BUỘC khi hồ sơ có thẻ căn cước vật lý. Với MỖI file/khối OCR có
   "CĂN CƯỚC CÔNG DÂN" hoặc "Citizen Identity Card", phải trả đúng một object gồm tối thiểu
   hoTen, soDinhDanh và diaChi đọc từ "Nơi thường trú/Place of residence". Không được bỏ qua
   thẻ chỉ vì người trên thẻ khác người ký Thông báo. Không lấy số CCCD chỉ được nhắc trong
   Thông báo/GCN làm một thẻ căn cước giả.
   ⚠️ ĐỊA CHỈ TỪ CCCD - QUY TẮC BẮT BUỘC:
   - PHẢI lấy từ "Nơi thường trú / Place of residence" trên CCCD
   - TUYỆT ĐỐI KHÔNG lấy từ "Quê quán / Place of origin"
   - Ví dụ: CCCD có cả "Quê quán: Xã A, Huyện B, Tỉnh C" và "Nơi thường trú: Tổ D, Phường E, Quận F, Thành phố G" → CHỈ lấy địa chỉ Nơi thường trú ("Thành phố G", "Phường E", "Tổ D"), KHÔNG lấy Quê quán ("Tỉnh C").
7. Địa chỉ object luôn là {quocGia,tinh,xa,diaChi}; diaChi không lặp tỉnh/xã. Ngày theo dd/mm/yyyy.

Không trả tên field UI ctl00$C$...; chỉ trả field compact trong schema.
"""
