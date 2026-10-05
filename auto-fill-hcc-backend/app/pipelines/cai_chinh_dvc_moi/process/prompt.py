"""Quy tắc trích riêng của thủ tục thay đổi, cải chính, bổ sung thông tin hộ tịch (Cổng DVC quốc gia mới)."""

EXTRA_RULES = """<ho_so>
Hồ sơ thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc: tờ khai (nếu có), giấy hộ tịch đã
đăng ký (giấy khai sinh / trích lục khai sinh, kết hôn, khai tử), CCCD/CMND, giấy tờ làm căn cứ (học bạ, bằng
cấp, giấy xác nhận, quyết định...), giấy ủy quyền. Khối người nộp trên cổng khóa theo tài khoản → KHÔNG trích
người nộp.
</ho_so>

<phan_vai>
- Có khối <phan_vai_da_xac_dinh> phía dưới → người có nội dung thay đổi, loại việc và loại giấy tờ hộ tịch theo
  đúng khối đó.
- Không có khối đó (dự phòng): người có nội dung thay đổi = người sau câu "cho người có tên dưới đây" trên tờ
  khai; không có tờ khai thì là người được đăng ký trên giấy hộ tịch chính.
</phan_vai>

<nguoi_thay_doi>
1. Nguồn: khối người có nội dung thay đổi trên TỜ KHAI → giấy hộ tịch của chính người đó → CCCD của chính người
   đó (bù ô còn thiếu; số, ngày cấp, nơi cấp đi NGUYÊN CỤM từ một giấy tờ).
2. Thông tin ĐANG CÓ, không phải thông tin MỚI: họ tên, dân tộc, quốc tịch, giới tính... lấy giá trị hiện ghi
   trong tờ khai / sổ hộ tịch; giá trị mới đề nghị chỉ nằm ở NoiDung. Thẻ CCCD Việt Nam luôn in quốc tịch
   "Việt Nam" → không dùng thẻ để ghi đè quốc tịch tờ khai / giấy hộ tịch.
3. GIẤY KHAI SINH: dòng "Giấy tờ tùy thân" là của NGƯỜI ĐI KHAI SINH → không đưa vào NguoiThayDoi_*.
   Trẻ chỉ có "Số định danh cá nhân" → chỉ trả NguoiThayDoi_SoDinhDanh.
4. NguoiThayDoi_NoiCap chép đúng cơ quan cấp ghi trên giấy; chỉ đổi cách viết của CÙNG cơ quan
   ("Cục CS QLHC về TTXH" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội"). CMND do "CA <tỉnh>" cấp →
   giữ nguyên. Không ghi → bỏ.
5. NguoiThayDoi_NoiCuTru chỉ lấy dòng thuộc chính người đó (khối người có nội dung thay đổi trên tờ khai, CCCD
   của chính họ); dòng nơi cư trú của cha/mẹ trên giấy khai sinh không phải của con. Dòng nơi cư trú trong khối
   người có nội dung thay đổi của tờ khai BẮT BUỘC trả, kể cả khi trùng nơi cư trú người yêu cầu.
   Tách {quocGia,tinh,xa,diaChi}: "[chi tiết], [xã], [huyện], [tỉnh]" đếm từ cuối — cuối là tỉnh, áp cuối là
   cấp huyện (bỏ khỏi xa/diaChi, trả riêng ở khóa "huyen"), cụm trước huyện là xã, còn lại là diaChi.
6. Dân tộc giữ nguyên chữ trên giấy; "Mông" giữ "Mông", biến thể có "H" đứng đầu (Hmông) → "Mông (Hmông)".
</nguoi_thay_doi>

<noi_dung_de_nghi>
7. ViecDangKy theo <viec_dang_ky> đã phân vai; không có thì xét bản chất nội dung + lý do (sai sót → "Cải
   chính"; đổi theo nguyện vọng → "Thay đổi"; ghi thêm thông tin còn trống → "Bổ sung"; "Xác định lại dân tộc"
   CHỈ khi nội dung là dân tộc — quốc tịch/họ tên/ngày sinh không bao giờ là "Xác định lại dân tộc").
   Không đủ căn cứ → bỏ field.
8. NoiDung lấy dòng "Nội dung" của tờ khai (cả thông tin cũ và mới, vd "Cải chính tên từ X thành Y"); LyDo lấy
   dòng "Lý do". Tờ khai không có → bỏ, không tự viết.
   TÁCH NỘI DUNG / LÝ DO: tờ khai viết tay hay bị OCR chèn nhãn "Lý do:" vào GIỮA đoạn nội dung hoặc nối lý do
   vào cuối nội dung ("... lý do - do sai sót ..."). NoiDung CHỈ gồm các thay đổi (thông tin nào, từ giá trị cũ
   thành giá trị mới) — BỎ mọi cụm lý do và nhãn "Lý do:" lạc chỗ; phần lý do đưa vào LyDo.
   Viết lại thành câu có nghĩa: sửa lỗi OCR ở TỪ THÔNG THƯỜNG (vd "Phàn"→"Phần", "tự"→"từ", "Thành"→"thành",
   "tiền thân"→"tùy thân"), nối các thay đổi bằng dấu chấm phẩy; GIỮ NGUYÊN họ tên, số giấy tờ, ngày tháng như
   OCR đọc, không tự sửa tên. LyDo cũng viết thành câu ngắn có nghĩa (bỏ "lý do", gạch đầu dòng).
9. HoSo_*: ưu tiên dòng "Đã đăng ký ... tại <cơ quan> ngày ... số ... quyển số ..." của tờ khai; thiếu thì lấy
   trên CHÍNH giấy hộ tịch cùng loại của người có nội dung thay đổi. Giấy của người khác không phải nguồn.
   HoSo_So: dòng "Số:" sát tiêu đề giấy hộ tịch, giữ nguyên mã/năm. HoSo_QuyenSo chỉ khi "Quyển số" có giá trị
   thật. HoSo_NoiDangKy: nhãn "Nơi đăng ký" hoặc cơ quan ở tiêu đề / khối ký tên của giấy hộ tịch.
   Trang CHỨNG THỰC ("Số chứng thực ... SCT") là sổ chứng thực → không lấy làm HoSo_*.
10. HoSo_LoaiGiayTo CHỈ khi tờ khai ghi rõ giấy tờ / sự kiện đã đăng ký hoặc hồ sơ có chính giấy hộ tịch đó
    của người có nội dung thay đổi; không đoán.
11. SoLuongBanSao: tờ khai "Đề nghị cấp bản sao: Có, <n> bản" → n; đánh dấu "Không" → 0; không ghi → bỏ.
</noi_dung_de_nghi>

<khong_bia>
12. Ngày chỉ trả khi đủ ngày-tháng-năm. Giấy tờ không ghi → bỏ field. Không suy diễn.
</khong_bia>"""
