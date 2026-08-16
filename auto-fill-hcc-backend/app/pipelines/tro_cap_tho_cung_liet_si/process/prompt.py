"""Quy tắc trích xuất hai vai trò cho trợ cấp thờ cúng liệt sĩ."""

EXTRA_RULES = """<critical_rules>
1. Output định danh CHỈ có hai vai trò: ChuHoSo_* và NguoiNop_*.
2. ChuHoSo_* là người đề nghị tại mục 1 Mẫu 18/người được ủy quyền thờ cúng liệt sĩ.
3. NguoiNop_* chỉ được trả theo requester_context. Không tạo Person1_*, Person2_* hoặc nhóm định danh ToKhai_* cũ.
4. ToKhai_MoiQuanHeVoiLietSi, ToKhai_LietSiThoCung, ToKhai_ThanNhan và LietSi_* là dữ liệu nghiệp vụ,
   không phải vai trò người nộp.
5. Không trả field UI data[...]. Không bịa; ô trống thì bỏ field.
</critical_rules>

<chu_ho_so>
1. Mục "1. Thông tin người đề nghị" của Đơn Mẫu 18 là nguồn xác định ChuHoSo_*.
2. Khối "BÊN ĐƯỢC ỦY QUYỀN" chỉ được hợp nhất vào ChuHoSo_* khi nội dung ủy quyền liên quan đúng việc
   thờ cúng liệt sĩ và người đó tương ứng người đề nghị trên Mẫu 18.
3. Ưu tiên họ tên, ngày sinh, số định danh, ngày cấp, nơi cấp:
   CCCD riêng đúng người -> giấy ủy quyền được chứng thực -> Mẫu 18.
4. Ưu tiên quê quán, nơi thường trú, điện thoại và quan hệ với liệt sĩ từ Mẫu 18. Giấy ủy quyền đúng người
   chỉ bổ sung tỉnh/xã còn thiếu; không thay địa chỉ Mẫu 18 bằng địa chỉ của bên ủy quyền.
5. Nếu Mẫu 18 chỉ ghi năm sinh nhưng giấy ủy quyền/CCCD đúng người có ngày đầy đủ, bắt buộc dùng ngày đầy đủ;
   không tạo 01/01/yyyy.
6. Không lấy BÊN ỦY QUYỀN, thân nhân trong bảng mục 2, liệt sĩ, người chết trong trích lục, cán bộ chứng thực,
   người tiếp nhận hoặc người ký làm ChuHoSo/NguoiNop.
7. Giới tính chỉ trả khi tài liệu của chính người đó ghi rõ Nam/Nữ. Cụm quan hệ "Con trai", "Con gái",
   "Anh", "Em" không phải giới tính và tuyệt đối không được dùng để suy giới tính.
</chu_ho_so>

<nguoi_nop>
1. Python đối chiếu tên/số định danh UI với OCR và chèn <requester_context>.
2. result="owner_match": người nộp chính là chủ hồ sơ; chỉ trả ChuHoSo_*, không lặp NguoiNop_*.
3. result="document_match": chỉ <matched_requester_ocr> được dùng cho NguoiNop_*.
4. result="no_document_match" hoặc "missing_ui_anchor": bỏ toàn bộ NguoiNop_* nhưng vẫn trích
   ChuHoSo_* và dữ liệu nghiệp vụ Mẫu 18.
5. Nếu UI có cả họ tên và CCCD thì tài liệu phải khớp cả hai trong cùng một khối. Không chọn theo tên file,
   thứ tự upload, chữ ký hoặc quan hệ gia đình.
6. UI chỉ dùng xác định vai trò; không sao chép giá trị từ UI vào output.
</nguoi_nop>

<dia_chi_va_giay_to>
1. Địa chỉ người trả object {quocGia,tinh,xa,diaChi}; bỏ cấp huyện/quận; diaChi chỉ giữ số nhà/đường/thôn/tổ.
2. Nếu Mẫu 18 thiếu tỉnh nhưng giấy ủy quyền của cùng người có địa chỉ đầy đủ thì dùng tỉnh từ giấy ủy quyền.
   Không đưa huyện/quận/thành phố thuộc tỉnh vào key tinh; không lặp cấp hành chính vào diaChi.
3. Nơi cấp CCCD cũ có "Cục CS/Cục CSQLHC về TTXH" thì chuẩn hóa thành
   "Cục Cảnh sát quản lý hành chính về trật tự xã hội". Không lấy cơ quan chứng thực làm nơi cấp.
4. Số định danh chỉ giữ chữ số; ngày chuẩn hóa dd/mm/yyyy khi OCR có đủ ngày tháng năm.
</dia_chi_va_giay_to>

<nghiep_vu_mau_18>
1. ToKhai_MoiQuanHeVoiLietSi lấy đúng dòng "Mối quan hệ với liệt sĩ" ở mục 1.
2. ToKhai_LietSiThoCung là MỘT CHUỖI họ tên liệt sĩ mà chủ hồ sơ được ủy quyền/đề nghị thờ cúng;
   không lấy tên bên ủy quyền hoặc thân nhân. Nếu có nhiều liệt sĩ thì nối tên bằng " và ".
   TUYỆT ĐỐI không trả array/list cho field này.
3. ToKhai_ThanNhan lấy mọi người không trống trong bảng mục 2, mỗi item
   {hoTen,namSinh,namMat,noiThuongTru,moiQuanHe}; namSinh/namMat chỉ là năm 4 chữ số.
   OCR có thể tách một dòng thành nhiều dòng hoặc lặp lại cùng người: so tên bỏ dấu/hoa thường, nếu năm sinh
   giống nhau hoặc một dòng thiếu năm thì gộp thành một item và bổ sung field còn trống; không trả dòng trùng.
4. LietSi_QueQuan trả chuỗi địa chỉ đầy đủ. LietSi_SoBang, LietSi_SoQuyetDinh, LietSi_NgayQuyetDinh
   chỉ trả khi đọc được từ tài liệu Bằng Tổ quốc ghi công phù hợp; không tự suy.
</nghiep_vu_mau_18>

Khi có <owner_proposal_ocr> hoặc <owner_authorization_ocr>, đây là phạm vi ưu tiên bắt buộc để phân vai.
Dù toàn văn OCR còn chứa nhiều người, không được lấy người ngoài các phạm vi đã chỉ định làm hai vai trò.
"""
