EXTRA_RULES = """
<source_and_role_rules>
1. Tách tuyệt đối hai vai:
   - CHỦ HỒ SƠ là người sử dụng đất/người đề nghị chính trong Đơn Mẫu 04. Ưu tiên nguồn: Đơn Mẫu 04 -> BÊN ỦY QUYỀN -> người đứng tên chính trên Giấy chứng nhận.
   - NGƯỜI NỘP là BÊN ĐƯỢC ỦY QUYỀN nếu hồ sơ có văn bản ủy quyền. Không lấy bên ủy quyền, người phối ngẫu/đồng sở hữu, người chứng thực, người ký xác nhận làm người nộp.
   - Nếu hoàn toàn không có văn bản ủy quyền thì trả NguoiNop_* bằng đúng thông tin ChuHoSo_*.
2. Khi một giấy tờ có nhiều người đứng tên, người xuất hiện đầu tiên/chính trong phần người đề nghị của Đơn Mẫu 04 là chủ hồ sơ; người còn lại chỉ là đồng sở hữu, không tự đổi vai.
3. Mọi thuộc tính số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ, điện thoại phải đi theo đúng người. Có CCCD riêng của đúng người thì ưu tiên CCCD cho thông tin định danh; riêng ĐỊA CHỈ phải áp dụng quy tắc nguồn chi tiết tại mục 7 dưới đây.
</source_and_role_rules>

<missing_and_normalization_rules>
4. Chỉ trả ngày sinh/ngày cấp khi có đủ ngày-tháng-năm. Chỉ có năm sinh thì bỏ field; tuyệt đối không bịa 01/01.
5. Chỉ suy giới tính từ danh xưng trực tiếp: "Ông" = "Nam", "Bà" = "Nữ". Không suy từ tên.
6. Số CCCD/CMND bỏ khoảng trắng, dấu chấm, dấu gạch; chỉ giữ chữ số. Số điện thoại chỉ trả khi tài liệu ghi cho đúng vai.
7. QUY TẮC ĐỊA CHỈ BẮT BUỘC:
   - Trong Đơn đề nghị/Mẫu 04, dòng đánh số "2. Địa chỉ:" ngay sau mục "1. Người đề nghị" là địa chỉ thường trú/nơi cư trú của CHỦ HỒ SƠ. KHÔNG coi dòng này là địa chỉ liên hệ.
   - Ưu tiên nguồn cho ChuHoSo_NoiCuTru: dòng "2. Địa chỉ:" trên Đơn -> địa chỉ đầy đủ trên giấy tờ định danh -> GCN. Nếu Đơn có đủ thôn/xóm/số nhà thì bắt buộc giữ phần đó trong diaChi; địa chỉ GCN chỉ có xã/tỉnh không được ghi đè làm diaChi rỗng.
   - Dòng "3. Địa chỉ liên hệ:" là thông tin liên hệ riêng, không được dùng để thay thế dòng 2 khi dòng 2 đã có.
   - Không có văn bản ủy quyền thì NguoiNop_NoiCuTru phải giống NGUYÊN VẸN ChuHoSo_NoiCuTru, kể cả diaChi. Có ủy quyền thì lấy nơi cư trú của BÊN ĐƯỢC ỦY QUYỀN.
   - Địa chỉ trả object {quocGia,tinh,xa,diaChi}; không đưa huyện vào xa hoặc diaChi, không lặp tỉnh/xã trong diaChi.
8. Don_NoiDungDeNghi chỉ lấy nội dung thực tế tại mục 5 của Đơn Mẫu 04. Không lấy tiêu đề thủ tục thay nội dung đơn.
9. Chỉ trả các key trong schema, không trả tên control UI data[...]. Bỏ field không có chứng cứ, không cảnh báo.
</missing_and_normalization_rules>
""".strip()
