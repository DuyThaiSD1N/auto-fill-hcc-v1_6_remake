EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ thường là vài PDF scan gộp: Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 19, bản cũ Mẫu số 15)
   kèm tờ khai lệ phí trước bạ (Mẫu 01/LPTB) và tờ khai thuế thu nhập cá nhân (Mẫu 03/BĐS-TNCN); giấy tờ nguồn gốc
   đất (hợp đồng/giấy chuyển nhượng, đơn xin làm nhà cũ, giấy viết tay, giấy khai sinh); phiếu đo đạc, bản mô tả
   ranh giới, mảnh trích đo. Đọc hết các trang trước khi chốt vai.
2. Tách tuyệt đối hai vai:
   - CHỦ HỒ SƠ là NGƯỜI SỬ DỤNG ĐẤT/chủ sở hữu tài sản đứng Đơn Mẫu số 19, mục "1. Người sử dụng đất, chủ sở hữu
     tài sản gắn liền với đất, người quản lý đất". Thiếu đơn thì lấy người nộp thuế trên tờ khai lệ phí trước bạ
     ([04]), rồi người NHẬN chuyển nhượng/nhận thừa kế, quà tặng trên tờ khai thuế TNCN (mục II [11.2]).
   - NguoiNop_* CHỈ trả khi hồ sơ có văn bản ủy quyền hoặc "Văn bản về việc đại diện theo quy định của pháp luật
     về dân sự": lấy BÊN ĐƯỢC ỦY QUYỀN. Không có văn bản đó thì bỏ toàn bộ NguoiNop_*.
   - KHÔNG lấy làm chủ hồ sơ hay người nộp: bên CHUYỂN nhượng/tặng cho trong hợp đồng, giấy chuyển nhượng, tờ
     khai thuế mục I ([04.2]); người sử dụng đất liền kề ký bản mô tả ranh giới; cán bộ đo đạc, người dẫn đạc, cán
     bộ địa chính; người làm chứng; cán bộ ký số; cha mẹ/người đi khai sinh trong giấy khai sinh; tài khoản dịch vụ
     công đang đăng nhập (cổng tự điền sẵn ngày sinh, giới tính của chủ tài khoản — đó KHÔNG phải chứng cứ).
3. Mọi thuộc tính số giấy tờ, ngày cấp, nơi cấp, ngày sinh, giới tính, địa chỉ, điện thoại phải đi theo đúng người
   (khớp họ tên, năm sinh và/hoặc số định danh). Giấy khai sinh CỦA CHỦ HỒ SƠ (người được khai sinh trùng tên, trùng
   ngày sinh) là nguồn ngày sinh và giới tính của chính người đó; phần khai về cha, mẹ là của người khác.
</source_and_role_rules>

<missing_and_normalization_rules>
4. Đơn Mẫu số 19 hay viết ngày sinh LIỀN sau họ tên ("<Họ tên> SN: dd/mm/yyyy"): tách phần "SN"/"sinh năm"
   ra khỏi ChuHoSo_HoTen, đưa ngày vào ChuHoSo_NgaySinh. Chỉ trả ngày sinh/ngày cấp khi có đủ ngày-tháng-năm;
   hợp đồng cũ chỉ ghi "Sinh năm" thì không dùng làm ngày sinh, tuyệt đối không bịa 01/01.
5. Số CCCD/CMND/định danh và số điện thoại bỏ khoảng trắng, dấu chấm, dấu gạch; chỉ giữ chữ số. Chữ viết tay
   hay bị OCR đọc lẫn: đối chiếu cùng một số ở Đơn, tờ khai lệ phí trước bạ, tờ khai thuế TNCN và lấy số
   khớp ở nhiều giấy tờ nhất.
6. NGÀY CẤP, NƠI CẤP là của GIẤY TỜ TÙY THÂN đúng người, cùng giấy với số. Hồ sơ không có CCCD/căn cước thì bỏ
   NgayCap và NoiCap, KHÔNG lấy ngày lập đơn, ngày đo đạc, ngày ký hợp đồng hay ngày ký số thay vào.
7. Giới tính chỉ từ mục "Giới tính" trên CCCD/giấy khai sinh của chính người đó, hoặc danh xưng Ông/Bà gắn với
   chính người đó. Không suy từ tên. Giấy khai sinh có "Họ và tên" trùng chủ hồ sơ (thường nằm giữa xấp giấy tờ
   nguồn gốc đất) -> "Giới tính" trên đó là của chủ hồ sơ; hợp đồng ghi "Bà <tên chủ hồ sơ>" -> Nữ, "Ông …" -> Nam.
8. QUY TẮC NƠI CƯ TRÚ (ChuHoSo_NoiCuTru, NguoiNop_NoiCuTru):
   - Ưu tiên "Nơi thường trú" trên CCCD đúng người, rồi mục "1c) Địa chỉ" của Đơn Mẫu số 19, rồi chỉ tiêu
     [08]–[10] tờ khai lệ phí trước bạ, rồi tờ khai thuế.
   - Phiếu xác nhận kết quả đo đạc, mảnh trích đo, hợp đồng chuyển nhượng lập nhiều năm trước thường còn ghi
     thôn/xã/thành phố TRƯỚC sắp xếp đơn vị hành chính, hoặc nơi thường trú lúc ký hợp đồng. Hễ Đơn đã ghi địa
     chỉ thì theo Đơn.
   - Dòng địa chỉ trên Đơn hay viết liền, viết tắt "TDP" (tổ dân phố), "p." (phường), "x." (xã): cụm CUỐI là
     tỉnh, cụm ngay trước là phường/xã (ghi đủ "Phường …"/"Xã …"), phần còn lại cho vào chiTietDuoiXa.
   - Không đưa huyện/thành phố thuộc tỉnh cũ vào xa hay chiTietDuoiXa, không lặp tỉnh/xã trong chiTietDuoiXa.
9. QUY TẮC THỬA ĐẤT (ThuaDat_DiaChi, ThuaDat_SoThua, ThuaDat_SoTo) — tách hẳn với nơi cư trú:
   - Phường/xã và chi tiết lấy ở mục "2. Thửa đất đăng ký – b) Địa chỉ" của Đơn; thiếu thì "1.2. Địa chỉ thửa
     đất" tờ khai lệ phí trước bạ, [20.3]–[20.5] tờ khai thuế TNCN, rồi phiếu đo đạc/mảnh trích đo. Ghi chú tên
     cũ trong ngoặc (vd "(… cũ)") không đưa vào chiTietDuoiXa.
   - Đơn mục 2b thường không ghi tỉnh: lấy tỉnh của thửa đất ở tờ khai lệ phí trước bạ 1.2.3, tờ khai thuế
     [20.5], phiếu đo đạc hoặc tiêu đề mảnh trích đo ("TỈNH …").
   - Số thửa/số tờ là của thửa ĐANG đăng ký (Đơn, tờ khai, phiếu đo đạc, mảnh trích đo thường trùng nhau).
     Hợp đồng chuyển nhượng cũ có thể ghi số thửa/số tờ theo bản đồ CŨ — không dùng khi các giấy tờ mới hơn
     ghi số khác.
10. Don_NoiDungDeNghi chỉ gồm các ý ở mục "4. Đề nghị của người sử dụng đất, chủ sở hữu tài sản gắn liền với
   đất" có ô ĐÃ ĐÁNH DẤU (dấu tích viết tay hoặc ☑). Ô "□" để trống là KHÔNG đề nghị. Chép nguyên văn câu
   đề nghị, nối bằng "; ".
11. Trước khi trả, soát lại: hồ sơ có nguồn thì PHẢI có đủ ChuHoSo_HoTen, ChuHoSo_NgaySinh, ChuHoSo_GioiTinh,
   ChuHoSo_SoDinhDanh, ChuHoSo_NoiCuTru (Đơn mục 1c luôn có địa chỉ), ChuHoSo_DienThoai, Don_NoiDungDeNghi,
   ThuaDat_DiaChi, ThuaDat_SoThua, ThuaDat_SoTo — field nào còn thiếu thì đọc lại đúng mục đó rồi mới trả.
12. Chỉ trả các key trong schema, không trả tên control UI data[...]. Bỏ field không có chứng cứ, thà thiếu
   còn hơn sai.
</missing_and_normalization_rules>
""".strip()
