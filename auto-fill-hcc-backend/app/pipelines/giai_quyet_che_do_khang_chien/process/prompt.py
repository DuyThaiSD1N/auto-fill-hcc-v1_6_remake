"""Quy tắc trích xuất vai trò cho thủ tục giải quyết chế độ người HĐKC."""

EXTRA_RULES = """<critical_rules>
1. Ba nhóm định danh có ý nghĩa khác nhau: ChuHoSo_*, NguoiNop_* và NguoiCoCong_*.
2. Với Mẫu 12, ChuHoSo_* là cá nhân nhận mai táng phí ở Mục 2a (hoặc người nhận trợ cấp tại Mục 3
   nếu Mục 2a cùng người/thiếu); NguoiCoCong_* là người có công đã chết ở Mục 1.
3. Tuyệt đối không đưa người có công đã chết vào ChuHoSo_*.
4. NguoiNop_* chỉ được trả theo requester_context; UI chỉ dùng phân vai, không sao chép giá trị UI.
5. Không trả nhóm Nguoi_* cũ, DaiDienThanNhan_*, Person1_*, Person2_* hoặc field UI data[...].
   Không bịa; ô trống thì bỏ.
</critical_rules>

<chu_ho_so>
1. Mẫu 12: lấy ChuHoSo_* từ Mục 2 "Người hoặc tổ chức nhận mai táng phí", nhánh a) Cá nhân. Nếu
   Mục 2a và Mục 3 là cùng người thì hợp nhất thành một ChuHoSo_*; không tạo thêm vai trò.
2. Nếu Mẫu 12 chọn nhánh tổ chức và không có cá nhân nhận, không lấy người chết làm ChuHoSo_*.
3. Mẫu 11: nếu Mục 2 "đại diện thân nhân hưởng trợ cấp" có cá nhân thì người đó là ChuHoSo_*; nếu
   Mục 2 trống thì ChuHoSo_* mới là người đề nghị tại Mục 1.
4. Với cá nhân, ưu tiên CCCD đúng người cho ngày sinh, giới tính, số giấy tờ, ngày cấp, nơi cấp và quê
   quán. Ưu tiên Bản khai Mục 2/3 cho nơi thường trú, điện thoại, mối quan hệ; CCCD chỉ bổ sung phần thiếu.
5. Ngày cấp/nơi cấp phải đi cùng đúng số giấy tờ của chủ hồ sơ, không ghép với người có công đã chết.
</chu_ho_so>

<nguoi_co_cong>
1. NguoiCoCong_* luôn mô tả người hoạt động kháng chiến/người có công tại Mục 1.
2. Mẫu 12: bắt buộc tách người có công đã chết thành NguoiCoCong_*; ưu tiên trích lục khai tử/CCCD đúng
   người rồi Mục 1. NguoiCoCong_NgayMat lấy từ Mẫu 12 hoặc trích lục khai tử đúng người.
3. Mẫu 11: nếu người tại Mục 1 chính là ChuHoSo_* thì không lặp NguoiCoCong_*; nếu Mục 2 có đại diện
   khác người tại Mục 1 thì vẫn phải trả NguoiCoCong_* cho đúng người ở Mục 1.
4. Quê quán, nơi thường trú và giấy tờ phải thuộc đúng người tại Mục 1; không lấy dữ liệu Mục 2/3.
</nguoi_co_cong>

<nguoi_nop>
1. result="owner_match": người nộp chính là chủ hồ sơ; chỉ trả ChuHoSo_*, không lặp NguoiNop_*.
2. result="document_match": chỉ matched_requester_ocr được dùng cho NguoiNop_*.
3. result="no_document_match" hoặc "missing_ui_anchor": bỏ toàn bộ NguoiNop_* nhưng vẫn trả ChuHoSo_*,
   NguoiCoCong_* và dữ liệu nghiệp vụ.
4. Nếu UI có cả họ tên và CCCD thì tài liệu phải khớp cả hai trong cùng phạm vi. Không chọn người nộp
   theo tên file, thứ tự upload, chữ ký, quan hệ gia đình hoặc vì đó là CCCD duy nhất.
</nguoi_nop>

<dia_chi_va_giay_to>
1. Mọi địa chỉ trả object {quocGia,tinh,xa,diaChi}; bỏ cấp huyện/quận; diaChi chỉ giữ số nhà/đường/thôn/tổ.
2. Giữ nguyên địa danh đọc được trong output compact. Python mapper sẽ dùng bảng sáp nhập hành chính chung;
   không tự suy hoặc đổi tỉnh/xã bằng kiến thức phỏng đoán.
3. "Cục CS/Cục CSQLHC về TTXH" chuẩn hóa thành "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
4. Số định danh chỉ giữ chữ số; ngày chuẩn hóa dd/mm/yyyy khi OCR có đủ ngày tháng năm.
</dia_chi_va_giay_to>

<nghiep_vu>
1. HDKC_CheDo chép theo tiêu đề/nội dung chế độ đề nghị của Bản khai.
2. HDKC_QuaTrinh, HDKC_ThanhTich, HDKC_DuocTang chỉ trả khi Mẫu 11/giấy tờ kèm theo ghi rõ.
3. HoSoDinhKem liệt kê đúng tài liệu thực có; Bản khai là Bản chính, giấy tờ còn lại theo loại bản thể hiện.
</nghiep_vu>

Khi có deceased_subject_ocr, owner_recipient_ocr hoặc matched_requester_ocr, đây là phạm vi ưu tiên bắt
buộc để phân vai. Không lấy người ngoài đúng phạm vi làm Người có công, Chủ hồ sơ hoặc Người nộp.
"""
