EXTRA_RULES = """
<source_and_role_rules>
1. Tách tuyệt đối hai vai:
   - CHỦ HỒ SƠ là người sử dụng đất/người có quyền đề nghị đính chính. Ưu tiên người đứng đầu phần I
     Đơn Mẫu 18 -> BÊN ỦY QUYỀN -> người đứng tên chính trên Giấy chứng nhận.
   - NGƯỜI NỘP là BÊN ĐƯỢC ỦY QUYỀN nếu có văn bản ủy quyền. Không lấy bên ủy quyền, người phối
     ngẫu/đồng sở hữu, công chứng viên, người chứng thực hoặc người ký xác nhận làm người nộp.
   - Không có văn bản ủy quyền thì trả NguoiNop_* bằng đúng thông tin ChuHoSo_*.
2. Nếu văn bản ủy quyền có nhiều BÊN ỦY QUYỀN, lấy người tương ứng người đứng đầu/chính trong phần I
   Đơn Mẫu 18 làm chủ hồ sơ; không trộn số giấy tờ, ngày cấp, địa chỉ của các đồng sở hữu.
3. Nếu Đơn Mẫu 18 do người được ủy quyền ký/viết, không vì chữ ký đó mà đổi người được ủy quyền thành
   chủ hồ sơ.
4. Số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ và điện thoại phải theo đúng từng người. Có CCCD
   riêng của đúng người thì ưu tiên CCCD cho định danh; địa chỉ áp dụng thứ tự nguồn ở mục 8.
</source_and_role_rules>

<missing_and_normalization_rules>
5. Chỉ trả ngày sinh/ngày cấp khi đủ ngày-tháng-năm. Chỉ có năm sinh thì bỏ field, không tự đặt 01/01.
6. Chỉ suy giới tính từ danh xưng trực tiếp: Ông=Nam, Bà=Nữ; không suy từ tên.
7. Số CCCD/CMND bỏ khoảng trắng, dấu chấm, dấu gạch, chỉ giữ chữ số. Số điện thoại chỉ trả khi tài
   liệu ghi cho đúng vai.
8. Địa chỉ CHỦ HỒ SƠ ưu tiên: mục I.c) "Địa chỉ" trên Đơn Mẫu 18 -> CCCD đúng người -> địa chỉ BÊN
   ỦY QUYỀN -> GCN. Giữ đủ thôn/xóm/tổ/số nhà trong diaChi; địa chỉ GCN rút gọn không được ghi đè.
   Có ủy quyền thì NguoiNop_NoiCuTru lấy của BÊN ĐƯỢC ỦY QUYỀN. Không có ủy quyền thì sao chép
   nguyên vẹn ChuHoSo_NoiCuTru, kể cả diaChi.
9. Don_NoiDungDeNghi lấy NGUYÊN VĂN phần người dân viết sau nhãn mục II/2 "Nội dung biến động" và
   DỪNG TRƯỚC mục III/3 "Giấy tờ liên quan" của Đơn Mẫu 18. Nếu chính nội dung viết tay có số
   CCCD/CMND để mô tả việc đính chính thì phải giữ số đó. Không lấy tiêu đề thủ tục thay nội dung đơn.
10. Chỉ trả key trong schema, không trả control UI data[...]. Bỏ field không có chứng cứ, không cảnh báo.
</missing_and_normalization_rules>
""".strip()
