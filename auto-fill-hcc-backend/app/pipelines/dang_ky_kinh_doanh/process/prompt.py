"""Procedure-specific rules for household business registration extraction."""

EXTRA_RULES = """
Bạn đang trích xuất dữ liệu cho thủ tục Đăng ký kinh doanh hộ kinh doanh.

NGUỒN DỮ LIỆU VÀ SUY LUẬN:
- Tài liệu chính thường là "Giấy đề nghị đăng ký hộ kinh doanh". OCR của giấy này là nguồn ưu tiên.
- Nếu có CCCD thì dùng để bổ sung/kiểm chứng thông tin cá nhân của chủ hộ hoặc người nộp hồ sơ.
- TỜ KHAI RÚT GỌN — nhiều "Giấy đề nghị đăng ký hộ kinh doanh" chỉ ghi HỌ TÊN + SỐ ĐỊNH DANH của chủ hộ,
  THIẾU nơi ở/thường trú, ngày sinh, giới tính. Khi đó BẮT BUỘC đối chiếu CCCD đính kèm (khớp họ tên/số định
  danh với chủ hộ) rồi LẤY BỔ SUNG các trường còn thiếu TỪ CCCD:
  + ChuHo_DiaChi = "Nơi thường trú" trên CCCD (TUYỆT ĐỐI KHÔNG lấy "Quê quán"; KHÔNG lấy địa chỉ TRỤ SỞ hộ
    kinh doanh — nơi ở của chủ hộ THƯỜNG KHÁC trụ sở kinh doanh).
  + ChuHo_NgaySinh = ngày sinh trên CCCD; ChuHo_GioiTinh = giới tính trên CCCD.
  + ChuHo_HoTen/ChuHo_SoDinhDanh: ưu tiên giấy đề nghị; thiếu thì lấy CCCD.
  Nếu người nộp hồ sơ = chủ hộ (trùng tên/số định danh) thì NguoiNop_HoTen/NguoiNop_NgaySinh/NguoiNop_SoDinhDanh/
  NguoiNop_DiaChi lấy tương tự từ CCCD.
- TÁCH "Nơi thường trú" trên CCCD (thường 3 cấp CŨ: "[chi tiết], xã, HUYỆN, tỉnh") — ĐẾM TỪ CUỐI: cuối = tỉnh;
  ngay trước tỉnh nếu là CẤP HUYỆN (huyện/quận/thị xã/thành phố thuộc tỉnh) thì BỎ HẲN; phần trước đó = xã;
  phần đầu = diaChi. Vd "Xóm 2, Gia Thắng, Gia Viễn, Ninh Bình" → diaChi="Xóm 2", xa="Gia Thắng",
  tinh="Ninh Bình" (BỎ huyện Gia Viễn).
- Không bịa thông tin. Field nào OCR không đủ chắc chắn thì bỏ qua.
- Nếu một người vừa là chủ hộ vừa là người ký/người nộp hồ sơ, có thể trả cả ChuHo_* và NguoiNop_* bằng cùng dữ liệu.
- Nếu giấy chỉ có một địa chỉ cá nhân và không tách rõ trụ sở/chủ hộ/người nộp, ưu tiên gán địa chỉ đó cho chủ hộ; chỉ gán trụ sở khi OCR nằm gần nhãn "Địa chỉ trụ sở hộ kinh doanh".

QUY TẮC TRÍCH XUẤT:
- HinhThucDangKy: nếu là hồ sơ thành lập mới thì trả "Thành lập mới hộ kinh doanh".
- HoKinhDoanh_Ten: LẤY ĐÚNG từ dòng "1. Tên hộ kinh doanh (ghi bằng chữ in hoa): HỘ KINH DOANH ___" — phần tên đứng NGAY SAU cụm "HỘ KINH DOANH". OCR hay tách rời ký tự bằng dấu cách (vd "H Ộ KINH DOAN H", "X U E") → hãy ghép lại thành từ hoàn chỉnh.
  + Tên hộ kinh doanh là DANH TỪ RIÊNG/thương hiệu (vd "MIXUE", "XUE") hoặc tên người (vd "VŨ THÀNH CHUNG"), KHÔNG phải mô tả hàng hóa/dịch vụ.
  + TUYỆT ĐỐI KHÔNG lấy ngành nghề kinh doanh làm tên: "Bán lẻ thực phẩm", "Dịch vụ đồ uống", "Dịch vụ ăn uống", "Bán buôn/Bán lẻ ..." là NGÀNH NGHỀ (mục 3), KHÔNG phải tên hộ kinh doanh.
  + Nếu sau "HỘ KINH DOANH" không có tên riêng rõ ràng (bị mờ/cụt), thì tên hộ kinh doanh thường chính là TÊN CHỦ HỘ — trả HoKinhDoanh_Ten bằng họ tên chủ hộ (ChuHo_HoTen) viết IN HOA.
  + Bỏ nhãn "Tên hộ kinh doanh:" và cụm "HỘ KINH DOANH" ở đầu nếu có; chỉ giữ phần tên thật.
- Địa chỉ object luôn có dạng {quocGia,tinh,xa,diaChi}; diaChi chỉ là số nhà/tổ/xóm/thôn/đường hoặc phần chi tiết còn lại, không lặp tỉnh/xã.
- ĐỊA CHỈ DẠNG THỬA ĐẤT: nếu diaChi chỉ vị trí thửa đất/bản đồ thì CHUẨN HÓA về đúng khuôn
  "Thửa đất số <N>, tờ bản đồ số <M>". OCR chữ viết tay hay đọc nhiễu các cụm này ("Phía/Thừa đất",
  "tổ bản đồ", "bàn đổ"...) → chỉ giữ 2 con số rồi dựng lại theo khuôn chuẩn, bỏ mọi chữ nhiễu.
  Ví dụ "Phía đất số 5, tổ bản đồ số 11" -> "Thửa đất số 5, tờ bản đồ số 11".
- CHỌN diaChi CHÍNH XÁC NHẤT khi có nhiều dòng "Số nhà, đường phố/tổ/xóm/ấp/thôn" na ná nhau:
  + Cùng một người, địa chỉ ở "Địa chỉ thường trú" và "Địa chỉ liên lạc" thường là CÙNG MỘT NƠI; hãy chọn bản đọc được ĐẦY ĐỦ và RÕ NGHĨA nhất.
  + Ưu tiên bản có đủ "Tổ <số>"/số nhà; loại bỏ bản bị cụt (kết thúc bằng "Tổ" mà thiếu số) hoặc nhiễu vô nghĩa (vd "S.CN 300 Tổ" là OCR lỗi của "SN 300 Tổ 11").
  + Ví dụ: giữa "S.CN 300 Tổ" (cụt, vô nghĩa) và "SN 300 Tổ 11" (đầy đủ) → chọn "SN 300 Tổ 11".
- Tỉnh/xã:
  + tinh trả tên tỉnh/thành phố như giấy, nhưng không cần tự thêm tiền tố nếu giấy không có.
  + xa CHỈ trả phần tên riêng của phường/xã/đặc khu, KHÔNG kèm tiền tố "Phường", "P.", "P", "Xã",
    "Thị trấn", "Đặc khu".
    Ví dụ: "Xã Nam Ban Lâm Hà" -> xa="Nam Ban Lâm Hà".
- Thue_DiaChiNhanThongBao (địa chỉ nhận thông báo thuế): SO SÁNH THEO NGỮ NGHĨA với địa chỉ trụ sở hộ kinh doanh (TruSo_DiaChi).
  + Nếu là CÙNG MỘT NƠI — kể cả khi viết hơi khác, thiếu/thừa chữ, sai chính tả hay nhiễu do OCR (vd "Tổ 11 Đoàn Kết" ≈ "Số 11, P. Đoàn Kết") — thì ĐỂ TRỐNG field này (hệ thống sẽ tự chọn "Giống địa chỉ trụ sở chính").
  + Trên giấy, mục 5.1 thường ghi "chỉ kê khai nếu khác địa chỉ trụ sở": nếu mục này bỏ trống thì coi như GIỐNG, để trống field.
  + CHỈ điền Thue_DiaChiNhanThongBao khi đó RÕ RÀNG là một địa điểm KHÁC. Khi phân vân thì cứ điền (an toàn hơn).
  + Thue_DienThoai/Thue_Email vẫn trả bình thường nếu đọc được, không phụ thuộc địa chỉ giống hay khác.
- Email chỉ trả khi có phần tên trước dấu @. Nếu OCR chỉ thấy "@gmail.com" hoặc domain không có tên người dùng thì bỏ trống.
- Email viết tay hay bị OCR chèn DẤU CHẤM NHIỄU vào phần trước @ (do nét chữ đè lên dòng gạch chấm "......").
  BỎ HẾT dấu chấm ở phần trước @, giữ nguyên phần domain sau @ (email cá nhân trên form gần như luôn gmail,
  dấu chấm không có ý nghĩa). Ví dụ "tai.nguyen@gmail.com" -> "tainguyen@gmail.com".
- Số điện thoại VN là 10 chữ số bắt đầu bằng "0". Nếu số xuất hiện ở nhiều chỗ, chọn bản đầy đủ 10 số có "0" đứng đầu; nếu bản đọc được thiếu "0" đứng đầu (vd "974455009") thì THÊM "0" vào trước (-> "0974455009"). Sửa lỗi OCR phổ biến: S->5, O->0; bỏ dấu cách trong dãy số.
- NGÀNH NGHỀ (mục 3, thường là BẢNG "STT | Tên ngành | Mã ngành | Ngành nghề kinh doanh chính"):
  BẮT BUỘC liệt kê ĐẦY ĐỦ MỌI dòng CÓ TÊN NGÀNH vào NganhNghe_DanhSach, mỗi dòng 1 object {ma, ten, chinh}.
  + Cột "Mã ngành" trên tờ khai (nhất là viết tay) THƯỜNG ĐỂ TRỐNG → khi đó ma="" và VẪN PHẢI trả ten.
    TUYỆT ĐỐI KHÔNG được bỏ trống NganhNghe_DanhSach chỉ vì thiếu mã ngành.
  + Bỏ các dòng trống (không có tên ngành). Giữ nguyên thứ tự xuất hiện.
  + Nếu cột "Ngành nghề kinh doanh chính" đánh dấu ở dòng nào thì chinh=true cho dòng đó (và NganhNghe_TenChinh = tên đó).
- Vốn kinh doanh: trả số tiền bằng chữ số đơn vị đồng. Nếu OCR có cả số và chữ, ưu tiên số ghi ở ô vốn; nếu chỉ có chữ thì chuyển thành số khi chắc chắn.
- Ngày tháng chuẩn dd/mm/yyyy khi có đủ ngày-tháng-năm; nếu giấy chỉ có tháng/năm hoặc năm thì giữ đúng mức chi tiết đọc được.
- Ngày sinh: CHỈ điền ngày khi đọc được số ngày hợp lệ (01-31). Nếu ô ngày trống/mờ/chỉ thấy "0" (vd OCR "Sinh ngày: 0 / 7 1989") thì trả "mm/yyyy" (vd "07/1989") và TUYỆT ĐỐI KHÔNG đoán/bịa số ngày.
- Giới tính chỉ trả "Nam" hoặc "Nữ".

KHÔNG trả tên field UI kiểu ctl00$C$...; chỉ trả các field compact trong schema."""
