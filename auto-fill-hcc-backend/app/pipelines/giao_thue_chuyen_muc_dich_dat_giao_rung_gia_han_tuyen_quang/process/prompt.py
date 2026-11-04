EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ gồm: Đơn đề nghị giao đất/cho thuê đất/chuyển mục đích sử dụng đất (Mẫu số 01) hoặc đơn gia hạn (Mẫu số
   04); Giấy chứng nhận đã cấp; giấy ủy quyền kèm lời chứng thực (nếu nộp thay); CCCD (nếu có). Một file có thể gộp
   nhiều giấy — đọc hết các trang trước khi chốt vai.
2. Ba vai, tách tuyệt đối:
   - CHỦ HỒ SƠ: người đề nghị đứng ĐẦU trên Đơn (= người ủy quyền đứng đầu trên giấy ủy quyền = người đứng đầu ở mục 1
     Giấy chứng nhận).
   - NGƯỜI ĐỒNG SỬ DỤNG: người kê khai cùng chủ hồ sơ ("Cùng vợ bà …", "Và vợ: Bà …"). Không phải chủ hồ sơ, không
     phải người nộp.
   - NGƯỜI NỘP (NguoiNop_*): CHỈ khi có giấy ủy quyền — là BÊN ĐƯỢC ỦY QUYỀN. Không có giấy ủy quyền thì bỏ toàn bộ
     NguoiNop_*. Công chứng viên, cán bộ chứng thực, người tiếp nhận hồ sơ không giữ vai nào.
   Không lấy tài khoản dịch vụ công đang đăng nhập cho vai nào (cổng tự điền sẵn ngày sinh, giới tính của chủ tài khoản).
3. LỜI CHỨNG THỰC cuối giấy ủy quyền liệt kê từng người kèm "Sinh ngày", "Số CCCD … do … cấp ngày …": đây là nguồn
   hợp lệ cho ngày sinh, ngày cấp, nơi cấp của ĐÚNG người theo số thứ tự/họ tên.
4. Mọi thuộc tính đi theo ĐÚNG người (khớp họ tên, số CCCD). Không mượn của người khác; thà bỏ trống còn hơn ghép chéo.
</source_and_role_rules>

<missing_and_normalization_rules>
5. Chỉ trả ngày khi đủ ngày-tháng-năm. "Sinh năm: 1985" hoặc dòng "Sinh ngày: 1985" chỉ có năm → bỏ field, không bịa.
6. Số CCCD bỏ dấu cách, dấu chấm ("0360 6701 2107" -> "036067012107"). Ngày cấp, nơi cấp đi CÙNG dòng với số đó.
7. Giới tính chỉ từ CCCD, danh xưng Ông/Bà gắn với chính người đó, hoặc vai vợ (Nữ)/chồng (Nam). Không suy từ tên.
8. Địa chỉ trả object {quocGia,tinh,xa,chiTietDuoiXa}; bỏ cấp huyện cũ; giữ thôn/xóm/số nhà trong chiTietDuoiXa. Ví dụ
   "Thôn Đông, xã Hòa Bình, tỉnh Ninh Bình" -> tinh="Ninh Bình", xa="Hòa Bình", chiTietDuoiXa="Thôn Đông".
9. ThuaDat_DiaChi là địa điểm thửa đất, KHÔNG phải nơi cư trú (dù hay trùng nhau).
10. Don_NoiDungDeNghi chép nguyên văn phần đề nghị (diện tích, loại đất chuyển từ/sang hoặc giao/thuê/gia hạn); không
   lấy phần "Diện tích và mục đích sử dụng hiện tại", không thay bằng tiêu đề thủ tục.
11. GCN_*: số phát hành giữ nguyên chữ cái và dấu cách như in ("AA 07474008"); số vào sổ là dòng "Số vào sổ cấp Giấy
   chứng nhận"; ngày cấp và cơ quan cấp lấy ở chỗ ký cấp hoặc như Đơn dẫn lại. Cơ quan cấp viết thường như câu văn, KHÔNG
   chép nguyên chữ IN HOA của dòng ký ("VĂN PHÒNG ĐĂNG KÝ ĐẤT ĐAI TỈNH X" -> "Văn phòng đăng ký đất đai tỉnh X").
12. Chỉ trả các key trong schema, không trả tên control UI data[...]. Field không có chứng cứ thì bỏ, không bịa.
</missing_and_normalization_rules>
""".strip()
