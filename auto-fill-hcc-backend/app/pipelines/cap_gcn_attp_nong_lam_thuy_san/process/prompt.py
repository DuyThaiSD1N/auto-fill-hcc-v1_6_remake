"""Quy tắc trích xuất cho cấp GCN ATTP nông, lâm, thủy sản."""

EXTRA_RULES = """<critical_rules>
1. Chỉ trả field nguồn có trong schema. Không trả field UI dạng data[...].
2. Đơn đề nghị Phụ lục I Thông tư 17/2025/TT-BNNMT là nguồn chính cho eForm Đơn đề nghị.
3. Bản thuyết minh Phụ lục II và Giấy đăng ký kinh doanh chỉ bổ sung khi Đơn thiếu; không ghi đè dữ liệu rõ ràng trên Đơn.
4. CCCD là nguồn mạnh nhất cho nhân thân của đúng người. Không lấy tên cơ sở làm họ tên chủ hồ sơ.
5. Không dùng tên file hoặc thứ tự upload để quyết định vai trò. Không chắc field nào thì bỏ field đó.
</critical_rules>

<document_classification>
1. Đơn Phụ lục I có tiêu đề "ĐƠN ĐỀ NGHỊ CẤP GIẤY CHỨNG NHẬN CƠ SỞ ĐỦ ĐIỀU KIỆN AN TOÀN THỰC PHẨM"
   và các mục 1 Tên cơ sở, 2 Địa chỉ, 3 Điện thoại, 4 Mã số đăng ký, 5 Thông tin đăng ký, 6 Mặt hàng.
2. Bản thuyết minh Phụ lục II có tiêu đề "BẢN THUYẾT MINH", "Điều kiện bảo đảm an toàn thực phẩm" và
   các phần I Thông tin chung, II Mô tả về sản phẩm, III Tóm tắt hiện trạng điều kiện cơ sở.
3. CCCD/thẻ căn cước có số định danh, họ tên, ngày sinh, giới tính, nơi cư trú và mặt sau ngày cấp/cơ quan cấp.
4. Giấy đăng ký kinh doanh/doanh nghiệp/hộ kinh doanh có tên cơ sở, mã số, địa chỉ, ngày đăng ký và cơ quan đăng ký.
</document_classification>

<don_rules>
1. Don_DiaDanh và Don_NgayDon lấy từ dòng địa danh/ngày tháng trên Đơn; ngày trả dd/mm/yyyy.
2. Don_TenCoSo lấy nguyên mục 1. Don_DaiDienCoSo chỉ lấy họ tên ở phần "ĐẠI DIỆN CƠ SỞ" hoặc chữ ký cuối đơn.
   Hai field này là hai khái niệm khác nhau, không tự sao chép tên cơ sở sang tên đại diện.
3. Don_DiaChiCoSo lấy mục 2 và tách {quocGia,tinh,xa,diaChi}; bỏ cấp huyện cũ khỏi diaChi nếu tách chắc chắn.
4. Don_DienThoai và Don_Email lấy mục 3; đây là liên hệ cơ sở, không phải mặc định liên hệ người nộp.
5. Don_MaSoDKKD lấy mục 4. Don_SoDangKy, Don_NgayCapDKKD, Don_NoiCapDKKD lấy đúng ba phần của mục 5.
6. Don_MatHang lấy mục 6. Don_LyDoCap chỉ trả nội dung được ghi sau nhãn "Lý do cấp".
</don_rules>

<supporting_document_rules>
1. ThuyetMinh_TenCoSo, ThuyetMinh_DiaChiCoSo lấy mục I.1 và I.2. ThuyetMinh_MatHang lấy tên sản phẩm ở mục II.
2. Không trích toàn bộ các bảng thiết bị, nhà xưởng, hóa chất vì cổng không có eForm tương ứng; tài liệu vẫn được đính kèm nguyên bản.
3. DangKy_MaSo là mã số doanh nghiệp/hộ kinh doanh. DangKy_SoDangKy chỉ trả khi tài liệu có số GCN riêng khác mã số.
4. DangKy_NgayCap ưu tiên ngày đăng ký/cấp lần đầu; không lấy ngày thay đổi gần nhất nếu đơn đang hỏi ngày cấp đăng ký ban đầu.
</supporting_document_rules>

<person_rules>
1. Gộp mặt trước/mặt sau cùng CCCD theo số định danh/MRZ. Một người trả Person1_*, người khác trả Person2_*.
2. Mỗi nhóm Person* chỉ chứa dữ liệu của một người; không trộn ngày cấp/nơi cấp giữa hai CCCD.
3. Person*_NoiCuTru có dạng {quocGia,tinh,xa,diaChi}; diaChi chỉ giữ số nhà, đường, tổ/thôn/xóm.
4. LLM không quyết định ai là người nộp. Python sẽ đối chiếu cả họ tên và số định danh với formContext.
</person_rules>

<source_priority>
1. Field eForm: Đơn Phụ lục I > Giấy đăng ký kinh doanh > Bản thuyết minh.
2. Nhân thân đại diện: CCCD khớp Don_DaiDienCoSo > CCCD khớp DangKy_NguoiDaiDien > chỉ họ tên trên Đơn.
3. Địa chỉ chủ hồ sơ cá nhân: CCCD đúng người > địa chỉ cơ sở trên Đơn/Bản thuyết minh.
4. Không bịa email, ngày cấp, nơi cấp hoặc địa chỉ chi tiết khi hồ sơ không ghi.
</source_priority>

<output_examples>
Đúng:
{"fields":{"Don_TenCoSo":"Cơ sở chế biến thủy sản Minh Hải","Don_DiaChiCoSo":{"quocGia":"Việt Nam","tinh":"Đà Nẵng","xa":"Phường Hải Châu","diaChi":"Số 12 đường A"},"Don_DienThoai":"0901234567","Don_MatHang":"Thủy sản đông lạnh","Don_DaiDienCoSo":"NGUYỄN VĂN MINH","Person1_HoTen":"NGUYỄN VĂN MINH","Person1_SoDinhDanh":"048012345678"}}

Sai:
{"fields":{"data[organization]":"Cơ sở Minh Hải","Don_DaiDienCoSo":"Cơ sở chế biến thủy sản Minh Hải"}}
Lý do sai: trả field UI và lấy tên cơ sở làm họ tên đại diện.
</output_examples>

<reminder>Chỉ trả JSON facts thuộc schema; không trả data[...] và không suy vai trò người nộp từ thứ tự file.</reminder>"""
