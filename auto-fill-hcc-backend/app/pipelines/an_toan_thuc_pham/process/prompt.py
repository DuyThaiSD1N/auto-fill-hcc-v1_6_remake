"""Procedure-specific compact prompt rules for food safety certificate."""

EXTRA_RULES = """<critical_rules>
1. Chỉ trả field nguồn trong schema. Không trả field UI dạng data[...].
2. Đơn đề nghị cấp Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm là nguồn chính để xác định chủ cơ sở/chủ hồ sơ.
3. CCCD/CMND là nguồn mạnh nhất cho số định danh, ngày sinh, giới tính, ngày cấp, nơi cấp và địa chỉ cư trú của đúng người đó.
4. Không dùng tên file hoặc thứ tự upload để quyết định vai trò; OCR là nguồn chính.
5. Không bịa. Không chắc field nào thì bỏ field đó.
</critical_rules>

<document_classification>
1. Nhận diện Đơn đề nghị ATTP theo các cụm: "ĐƠN ĐỀ NGHỊ", "Cấp Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm",
   "tên cơ sở", "chủ cơ sở", "địa chỉ cơ sở", "kinh doanh dịch vụ ăn uống", "sản xuất thực phẩm".
2. Nhận diện CCCD/CMND/thẻ căn cước theo tiêu đề giấy tờ định danh, số định danh, ngày sinh, giới tính, nơi thường trú và mặt sau ngày cấp/nơi cấp.
3. Nhận diện Giấy khám sức khỏe theo tiêu đề "GIẤY KHÁM SỨC KHỎE", mục họ tên, ngày sinh, số CCCD/CMND, nơi ở hiện tại, kết luận sức khỏe.
4. Nhận diện Biên bản/Kết luận giám định y khoa chỉ khi tài liệu thật sự có tiêu đề/nội dung giám định y khoa; không gọi Giấy khám sức khỏe là giám định y khoa.
</document_classification>

<don_de_nghi_extraction>
1. Trích DonDeNghi_ChuCoSoHoTen từ dòng "Họ và tên chủ cơ sở", "Chủ cơ sở", hoặc người ký đại diện nếu đơn chỉ có một chủ cơ sở rõ ràng.
2. DonDeNghi_TenCoSo lấy từ "Tên cơ sở", "Tên cơ sở kinh doanh", hoặc tên quán/cơ sở.
3. DonDeNghi_DiaChiCoSo lấy từ "Địa chỉ cơ sở", "Địa chỉ cơ sở kinh doanh/sản xuất".
4. DonDeNghi_DiaChiChuCoSo chỉ trả nếu đơn có địa chỉ cư trú/thường trú của chính chủ cơ sở; không dùng địa chỉ cơ sở kinh doanh để thay thế.
5. DonDeNghi_DienThoai chỉ trả số điện thoại rõ ràng, ưu tiên số di động 10 chữ số; bỏ số bàn/chuỗi mơ hồ.
6. DonDeNghi_NganhNghe lấy từ nội dung đề nghị hoặc loại hình hoạt động, ví dụ "kinh doanh dịch vụ ăn uống".
</don_de_nghi_extraction>

<person_extraction>
1. Tự gộp mặt trước và mặt sau của cùng một CCCD thành cùng một Person* theo số định danh/MRZ/họ tên.
2. Nếu có một CCCD: trả Person1_*. Nếu có hai CCCD khác nhau: trả Person1_* và Person2_*.
3. Mỗi nhóm Person* phải lấy từ đúng một người, không trộn dữ liệu giữa hai CCCD.
4. Bắt buộc cố đọc Person*_NgayCap từ mặt sau nếu OCR có. Không lấy ngày sinh hay ngày hết hạn làm ngày cấp.
5. Bắt buộc cố đọc Person*_NoiCap từ mặt sau nếu OCR có. Nếu thấy "CỤC TRƯỞNG CỤC CẢNH SÁT..." thì trả
   "Cục Cảnh sát quản lý hành chính về trật tự xã hội". Nếu thẻ căn cước mới ghi "BỘ CÔNG AN" thì trả "Bộ Công an".
6. Person*_NoiCuTru là địa chỉ trên CCCD, object {quocGia,tinh,xa,diaChi}; diaChi không lặp xã/huyện/tỉnh.
</person_extraction>

<health_document_extraction>
1. GiayKham_* chỉ lấy từ Giấy khám sức khỏe, không lấy từ Đơn đề nghị.
2. Nếu Giấy khám sức khỏe có người trùng DonDeNghi_ChuCoSoHoTen hoặc trùng số định danh, vẫn trả GiayKham_* riêng; Python sẽ gộp sau.
3. GiayKham_KetLuan chỉ trả kết luận sức khỏe đọc chắc chắn như "sức khỏe loại II"; không suy diễn bệnh/mức độ nếu tài liệu không ghi.
4. GiamDinh_* chỉ lấy từ tài liệu giám định y khoa thật sự. Không tự tạo GiamDinh_MucDo từ Giấy khám sức khỏe.
</health_document_extraction>

<address_rules>
1. Với địa chỉ object: quocGia mặc định "Việt Nam" nếu là địa chỉ trong nước; tinh là tỉnh/thành phố; xa là xã/phường/thị trấn nếu đọc được.
2. diaChi chỉ giữ số nhà/tổ/thôn/bản/khu/xóm/đường, không lặp xã/huyện/tỉnh.
3. Nếu địa chỉ chỉ có một chuỗi dài, vẫn cố tách tỉnh và xã từ cuối chuỗi; bỏ cấp huyện cũ nếu xuất hiện giữa xã và tỉnh.
</address_rules>

<role_boundary>
1. LLM không cần quyết định người nộp là ai hay chủ hồ sơ là ai. Python sẽ so sánh Person* với formContext của UI.
2. Không đổi tên DonDeNghi_* thành Person* và không suy role từ thứ tự upload.
3. Nếu chủ cơ sở trong đơn khác CCCD người nộp, vẫn trả đầy đủ DonDeNghi_* và Person*; không tự ép hai người thành một.
</role_boundary>

<output_examples>
Đúng:
{"fields":{"DonDeNghi_ChuCoSoHoTen":"BÙI THỊ LAN","DonDeNghi_TenCoSo":"Quán lẩu lòng Ngọc Lan","DonDeNghi_DienThoai":"0984126036","Person1_HoTen":"VŨ THỊ DUYÊN","Person1_SoDinhDanh":"012168002390","GiayKham_HoTen":"BÙI THỊ LAN","GiayKham_NgaySinh":"02/09/1975"}}

Sai:
{"fields":{"data[ownerFullname]":"BÙI THỊ LAN","DonDeNghi_ChuCoSoHoTen":"VŨ THỊ DUYÊN"}}
Lý do sai: trả field UI data[...] và lấy người nộp làm chủ cơ sở.
</output_examples>"""

