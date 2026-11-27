"""Prompt rules cho Khánh Hòa - xác nhận điều kiện diện tích nhà ở để đăng ký thường trú (1.013314, cổng DVC Khánh Hòa)."""

EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ (cổng DVC Khánh Hòa; người đề nghị có thể đang cư trú ở tỉnh khác) thường gồm: Tờ khai xác nhận tình trạng chỗ ở
   hợp pháp, diện tích nhà ở tối thiểu để đăng ký thường trú, đăng ký tạm trú (Mẫu số 02, NĐ 58/2026/NĐ-CP), CCCD của
   người đề nghị; có thể kèm Giấy chứng nhận / hợp đồng thuê, mượn, ở nhờ của chỗ ở, giấy ủy quyền khi nộp thay.
2. CHỦ HỒ SƠ là NGƯỜI ĐỀ NGHỊ ở mục "I. THÔNG TIN NGƯỜI ĐỀ NGHỊ" của Tờ khai (cũng là người ký "Người đề nghị"). Chủ
   nhà, người đứng tên Giấy chứng nhận, bên cho thuê / cho mượn / cho ở nhờ trên hợp đồng KHÔNG phải chủ hồ sơ, cũng KHÔNG
   phải người nộp thay — không trộn tên, số giấy tờ, ngày sinh, địa chỉ của họ vào ChuHoSo_* hay NguoiNopThay.
3. NguoiNopThay CHỈ khi có giấy ủy quyền (bên được ủy quyền) hoặc CCCD của một người khác người đề nghị; không có thì bỏ.
4. Mọi thuộc tính số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ phải đi theo đúng người.
</source_and_role_rules>

<identity_rules>
5. Thứ tự ưu tiên thông tin nhân thân: CCCD/thẻ căn cước đúng người -> Tờ khai Mẫu 02.
6. Ngày cấp / nơi cấp CHỈ lấy trên chính thẻ CCCD/căn cước; không có thẻ thì bỏ trống. Ngày sinh chỉ trả khi đủ
   ngày-tháng-năm. Giới tính chỉ lấy từ mục "Giới tính" trên CCCD.
7. Số CCCD bỏ khoảng trắng/dấu chấm/gạch, chỉ giữ chữ số. Tờ khai Mẫu 02 không có mục điện thoại/email: không có nguồn
   thì bỏ trống, không bịa.
</identity_rules>

<address_rules>
8. Địa chỉ trả object {quocGia,tinh,xa,chiTietDuoiXa}; không đưa huyện vào xa hoặc chiTietDuoiXa, không lặp tỉnh/xã trong
   chiTietDuoiXa; giữ đủ số nhà/ngõ/đường/tổ dân phố/thôn trong chiTietDuoiXa.
9. ChuHoSo_ThuongTru là NƠI CƯ TRÚ HIỆN TẠI (CCCD / Tờ khai mục I.4). ChoO_DiaChi là CHỖ Ở HỢP PHÁP đề nghị xác nhận
   (Tờ khai mục II.1) — hai địa chỉ khác nhau, không chép chéo.
10. Tờ khai chỉ ghi số nhà/đường ở mục II.1 mà KHÔNG ghi phường/tỉnh → xa lấy theo "Kính gửi: Ủy ban nhân dân <phường/xã>"
    của chính Tờ khai; tinh để trống nếu không giấy nào ghi.
11. CCCD cấp trước sắp xếp đơn vị hành chính còn ghi huyện/xã CŨ mà Tờ khai ghi đơn vị mới → theo Tờ khai; chỉ có CCCD thì
    trả đúng nguyên văn (hệ thống tự quy đổi).
</address_rules>

<content_rules>
12. ToKhai_TinhTrangChoO, ToKhai_SoNguoiThueMuon, ToKhai_DienTichThueMuon chép NGUYÊN VĂN chữ người dân viết ở mục III của
    Tờ khai; dòng chỉ có dấu chấm/để trống thì bỏ field. Không lấy phần "XÁC NHẬN CỦA UBND" và chú thích cuối Tờ khai.
13. Chỉ trả các key trong schema, không trả tên control UI data[...]. Field không có nguồn ghi rõ thì bỏ trống, thà thiếu
    còn hơn sai.
</content_rules>
""".strip()
