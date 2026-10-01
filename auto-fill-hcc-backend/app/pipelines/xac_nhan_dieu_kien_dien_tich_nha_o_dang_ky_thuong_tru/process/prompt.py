EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ thường gồm: Tờ khai xác nhận tình trạng chỗ ở hợp pháp, diện tích nhà ở tối thiểu để đăng ký
   thường trú, đăng ký tạm trú (Mẫu số 02), Giấy chứng nhận quyền sử dụng đất/quyền sở hữu nhà ở của chỗ ở,
   có thể kèm CCCD và hợp đồng thuê/mượn/ở nhờ.
2. CHỦ HỒ SƠ là NGƯỜI ĐỀ NGHỊ ở mục "I. THÔNG TIN NGƯỜI ĐỀ NGHỊ" của Tờ khai Mẫu 02 (cũng là người ký ở
   "Người đề nghị"). Không có Tờ khai thì lấy người sử dụng đất/chủ sở hữu ĐẦU TIÊN trên Giấy chứng nhận.
   Người thứ hai trở đi trên Giấy chứng nhận (vợ/chồng đồng sử dụng) chỉ là đồng sử dụng, KHÔNG trộn số
   giấy tờ, ngày sinh, địa chỉ của họ vào chủ hồ sơ.
3. NGƯỜI NỘP là BÊN ĐƯỢC ỦY QUYỀN nếu hồ sơ có văn bản ủy quyền; không có thì NguoiNop_* = ChuHoSo_*.
4. Mọi thuộc tính số giấy tờ, ngày cấp, nơi cấp, ngày sinh, địa chỉ phải đi theo đúng người.
</source_and_role_rules>

<identity_rules>
5. Thứ tự ưu tiên thông tin nhân thân: CCCD/thẻ căn cước đúng người -> Tờ khai Mẫu 02 -> Giấy chứng nhận.
6. Giấy chứng nhận cấp nhiều năm trước ghi "CMND số" 9 chữ số, "Cấp ngày", "Nơi cấp" của CMND CŨ: đó là giấy
   tờ khác, TUYỆT ĐỐI không dùng làm số định danh, ngày cấp hay nơi cấp. Số định danh lấy 12 số ở Tờ khai
   mục I.3 hoặc trên CCCD; ngày cấp/nơi cấp CHỈ lấy trên chính thẻ CCCD/căn cước. Không có thẻ thì bỏ trống.
7. Ngày sinh chỉ trả khi có đủ ngày-tháng-năm; Giấy chứng nhận chỉ ghi "Sinh năm" -> không bịa 01/01.
8. Giới tính chỉ lấy từ mục "Giới tính" trên CCCD hoặc danh xưng gắn trực tiếp với người đó ("Ông"=Nam,
   "Bà"=Nữ); không suy từ tên.
9. Số CCCD bỏ khoảng trắng/dấu chấm/gạch, chỉ giữ chữ số. Tờ khai Mẫu 02 không có mục điện thoại/email:
   không có nguồn thì bỏ trống, không bịa.
</identity_rules>

<address_rules>
10. Địa chỉ trả object {quocGia,tinh,xa,diaChi}; không đưa huyện vào xa hoặc diaChi, không lặp tỉnh/xã
    trong diaChi; giữ đủ số nhà/ngõ/đường/tổ dân phố/thôn trong diaChi.
11. Tờ khai Mẫu 02 hay chỉ ghi "<số nhà> <đường>, Tổ dân phố ..." ở mục I.4 và II.1 mà KHÔNG ghi phường/tỉnh.
    Khi đó xa lấy theo cơ quan tiếp nhận ở dòng "Kính gửi: UBND <phường/xã>" (hoặc tên UBND ở góc trái
    trên) của chính Tờ khai — đây là UBND nơi có chỗ ở; tinh để trống nếu không giấy tờ nào ghi.
12. Giấy chứng nhận cấp TRƯỚC sắp xếp đơn vị hành chính có thể ghi phường/huyện/tỉnh CŨ: Tờ khai hoặc CCCD
    ghi khác thì theo giấy tờ MỚI; chỉ có Giấy chứng nhận thì vẫn trả đúng nguyên văn (hệ thống tự quy đổi).
13. ChoO_DiaChi là địa chỉ CHỖ Ở HỢP PHÁP đề nghị xác nhận (Tờ khai mục II.1 -> "Địa chỉ thửa đất" trên Giấy
    chứng nhận). ThuaDat_So/ThuaDat_ToBanDo lấy trên Giấy chứng nhận của đúng chỗ ở đó.
</address_rules>

<content_rules>
14. ToKhai_TinhTrangChoO, ToKhai_SoNguoiThueMuon, ToKhai_DienTichThueMuon chép NGUYÊN VĂN chữ người dân viết ở
    mục III của Tờ khai; dòng chỉ có dấu chấm/để trống thì bỏ field. Không lấy phần "XÁC NHẬN CỦA UBND".
15. Chỉ trả các key trong schema, không trả tên control UI data[...]. Field không có nguồn ghi rõ thì bỏ trống,
    thà thiếu còn hơn sai.
</content_rules>
""".strip()
