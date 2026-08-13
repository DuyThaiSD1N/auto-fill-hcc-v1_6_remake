"""Procedure-specific rules for household business registration extraction."""

EXTRA_RULES = """
Bạn đang trích xuất dữ liệu cho thủ tục Đăng ký kinh doanh hộ kinh doanh.

NGUỒN DỮ LIỆU VÀ SUY LUẬN:
- Tài liệu chính là "Giấy đề nghị đăng ký hộ kinh doanh". Với thông tin đã kê khai trên giấy này, phải lấy theo giấy này trước.

- ĐỊA CHỈ CÁ NHÂN TRÊN GIẤY ĐỀ NGHỊ:
  + Chỉ đọc trong phần thông tin cá nhân của chủ hộ, từ đầu tờ khai đến trước dòng "Đăng ký hộ kinh doanh do tôi là chủ hộ...".
  + ChuHo_DiaChi: ưu tiên mục "Nơi ở hiện tại" ở giấy đăng ký kinh doanh. Nếu mục này không có, trắng hoặc không đọc được thì lấy mục "Nơi thường trú".
  + Khi đọc một khối địa chỉ cá nhân, ghép đúng 3 dòng: dòng "Số nhà/phòng.../tổ/xóm/ấp/thôn" -> diaChi;
    dòng "Xã/Phường/Đặc khu" -> xa; dòng "Tỉnh/Thành phố trực thuộc trung ương" -> tinh.
  + Không lấy địa chỉ tại mục "2. Trụ sở của hộ kinh doanh" cho ChuHo_DiaChi.
  + Ví dụ: nếu Giấy đề nghị có "Nơi ở hiện tại" đọc được, còn CCCD ghi một nơi cư trú khác, thì ChuHo_DiaChi phải lấy theo "Nơi ở hiện tại" trên Giấy đề nghị.
  + NguoiNop_DiaChi: CHỈ lấy khi người nộp chính là chủ hộ. Nếu người nộp chính là chủ hộ thì dùng cùng địa chỉ cá nhân đã chọn cho ChuHo_DiaChi.
    CHỈ lấy NguoiNop_DiaChi từ GIẤY ĐỀ NGHỊ — KHÔNG lấy từ giấy ủy quyền, KHÔNG lấy từ CCCD.
  + Nếu người nộp KHÁC chủ hộ (người được ủy quyền): TUYỆT ĐỐI KHÔNG trả NguoiNop_DiaChi.
    Nhân thân + địa chỉ của người nộp thay đi qua nhóm field UyQuyen_NguoiDuocUyQuyen_* ở dưới.
  + THỨ TỰ ƯU TIÊN: CHỈ lấy NguoiNop_DiaChi khi người nộp LÀ chủ hộ → dùng địa chỉ trên giấy đề nghị (ChuHo_DiaChi).
    Người nộp KHÁC chủ hộ → KHÔNG lấy NguoiNop_DiaChi.

- 🪪 Cccd_DanhSach — NHÂN THÂN ĐỌC TỪ THẺ CĂN CƯỚC (BẮT BUỘC khi hồ sơ có ảnh/bản scan thẻ):
  + Với MỖI thẻ ("CĂN CƯỚC", "CĂN CƯỚC CÔNG DÂN", "Citizen Identity Card", "CHỨNG MINH NHÂN DÂN")
    trả đúng MỘT object {hoTen, gioiTinh, ngaySinh, soDinhDanh, diaChi}.
  + Mặt trước và mặt sau của CÙNG một thẻ là MỘT người → gộp thành một object, không tách đôi.
  + Hồ sơ nộp thay thường có CCCD của chủ hộ VÀ CCCD của người đi nộp: phải trả ĐỦ MỌI thẻ đọc được,
    không bỏ thẻ nào, kể cả khi trùng thông tin với chủ hộ.
  + diaChi đọc ở "Nơi thường trú/Place of residence", dạng {quocGia,tinh,xa,diaChi} và BỎ cấp huyện:
    ví dụ "Thôn Nam Hiệp 2, Ka Đô, Đơn Dương, Lâm Đồng" → diaChi="Thôn Nam Hiệp 2", xa="Ka Đô",
    tinh="Lâm Đồng" (Đơn Dương là huyện, bỏ).
  + KHÔNG suy vai trò (chủ hộ hay người nộp) từ thứ tự file hay tên file — hệ thống tự đối chiếu với
    tài khoản đang nộp trên cổng.
  + Dữ liệu trong Cccd_DanhSach KHÔNG được dùng thay cho ChuHo_DiaChi / TruSo_DiaChi / NguoiNop_DiaChi
    (các field đó chỉ lấy từ Giấy đề nghị).
  + Giấy ủy quyền (nếu có) CHỈ dùng để biết hồ sơ nộp thay; KHÔNG lấy nhân thân/địa chỉ từ giấy đó.

- ⚠️ PHÁT HIỆN NHIỀU CCCD/GIẤY TỜ TÙY THÂN TRONG HỒ SƠ:

  **HasMultipleCCCD**: Đếm số CCCD/CMND/giấy tùy thân trong hồ sơ.
  - Nếu CHỈ có 1 CCCD → trả HasMultipleCCCD = false
  - Nếu có 2+ CCCD → trả HasMultipleCCCD = true
  
  **⚠️ QUY TẮC BẮT BUỘC KHI CÓ 2+ CCCD:**
  Khi phát hiện HasMultipleCCCD = true, BẮT BUỘC phải:
  1. Xác định CCCD nào là của CHỦ HỘ (so với giấy đề nghị)
  2. Xác định CCCD còn lại là của ai
  3. Nếu CCCD còn lại KHÁC chủ hộ (khác cả số và tên) → ĐIỀN ĐẦY ĐỦ các field UyQuyen_*
  4. KHÔNG ĐƯỢC bỏ trống các field UyQuyen_* khi đã xác định có người ủy quyền
  
  **KHI CÓ 2+ CCCD - LOGIC XÁC ĐỊNH CHỦ HỘ VÀ NGƯỜI ỦY QUYỀN:**
  
  + **BƯỚC 1 - XÁC ĐỊNH AI LÀ CHỦ HỘ:**
    Ưu tiên xác định theo GIẤY ĐỀ NGHỊ ĐĂNG KÝ HỘ KINH DOANH:
    - Đọc họ tên và số CCCD của CHỦ HỘ từ phần đầu giấy đề nghị (phần "Tôi là...")
    - So sánh với CÁC CCCD trong hồ sơ:
      * CCCD nào có SỐ ĐỊNH DANH KHỚP với số CCCD trên giấy đề nghị → ĐÓ LÀ CHỦ HỘ
      * Nếu không khớp số, so sánh HỌ TÊN: CCCD nào khớp tên trên giấy đề nghị → ĐÓ LÀ CHỦ HỘ
    - CCCD còn lại → là NGƯỜI ĐƯỢC ỦY QUYỀN (người đi nộp hồ sơ thay)
  
  + **BƯỚC 2 - ĐIỀN THÔNG TIN CHỦ HỘ:**
    - Lấy từ CCCD của CHỦ HỘ (đã xác định ở bước 1):
      * ChuHo_HoTen, ChuHo_SoDinhDanh, ChuHo_GioiTinh, ChuHo_NgaySinh
      * ChuHo_DiaChi: ƯU TIÊN địa chỉ "Nơi ở hiện tại" trên GIẤY ĐỀ NGHỊ, nếu không có thì lấy từ CCCD
  
  + **BƯỚC 3 - ĐIỀN THÔNG TIN NGƯỜI ỦY QUYỀN:**
    - Nếu CCCD còn lại có CẢ số định danh VÀ họ tên KHÁC với chủ hộ:
      → ĐÓ LÀ NGƯỜI ĐƯỢC ỦY QUYỀN
      → BẮT BUỘC điền ĐẦY ĐỦ:
        * UyQuyen_NguoiDuocUyQuyen_HoTen (từ CCCD người ủy quyền)
        * UyQuyen_NguoiDuocUyQuyen_SoDinhDanh (từ CCCD người ủy quyền)
        * UyQuyen_NguoiDuocUyQuyen_GioiTinh (từ CCCD người ủy quyền)
        * UyQuyen_NguoiDuocUyQuyen_NgaySinh (từ CCCD người ủy quyền)
        * UyQuyen_NguoiDuocUyQuyen_DiaChi (từ CCCD người ủy quyền - lấy "Nơi thường trú")
        * UyQuyen_NguoiUyQuyen_HoTen = tên CHỦ HỘ (từ giấy đề nghị)
        * UyQuyen_NguoiUyQuyen_SoDinhDanh = số CCCD CHỦ HỘ (từ giấy đề nghị)
        * UyQuyen_CoGiayUyQuyen = true (nếu có giấy ủy quyền văn bản) hoặc false (chỉ có 2 CCCD)
    
    - Nếu CCCD còn lại có số CCCD KHỚP HOẶC họ tên KHỚP với CHỦ HỘ:
      → Coi như CÙNG NGƯỜI (chủ hộ có 2 CCCD cũ/mới, hoặc chủ hộ tự nộp)
      → KHÔNG điền các field UyQuyen_*
      → Trả UyQuyen_CoGiayUyQuyen = false
  
  + **LƯU Ý QUAN TRỌNG:**
    - So sánh HỌ TÊN phải chuẩn hóa (bỏ dấu, chữ thường, bỏ khoảng trắng thừa)
    - Ví dụ: "NGUYỄN VĂN A" = "Nguyen Van A" = "nguyễn văn a"
    - PHẢI điền ĐẦY ĐỦ thông tin người ủy quyền, KHÔNG được bỏ field nào
  
  + **VÍ DỤ CỤ THỂ VỚI SỐ CCCD THẬT:**
    
    **Ví dụ: Giấy đề nghị của Lê Văn Sơn + CCCD của Nguyễn Duy Thái (người ủy quyền)**
    
    INPUT HỒ SƠ:
    - Giấy đề nghị: "Tôi là LÊ VĂN SƠN... Số định danh: 042093011745... Nơi ở hiện tại: Số 150 đường 2/4, thôn Thạnh Nghĩa, Đơn Dương, Lâm Đồng"
    - CCCD: Số 001204018566, tên "NGUYỄN DUY THÁI", sinh 11/08/2004, Nam, nơi thường trú "TDP 13 Nhân Mỹ Mỹ Đình 1, Nam Từ Liêm, Hà Nội"
    
    PHÂN TÍCH:
    1. Đọc giấy đề nghị → Chủ hộ là "LÊ VĂN SƠN" (042093011745)
    2. So sánh CCCD với chủ hộ:
       - CCCD 001204018566 "NGUYỄN DUY THÁI" ≠ 042093011745 "LÊ VĂN SƠN"
       - Số CCCD KHÁC và Tên KHÁC → ĐÂY LÀ NGƯỜI ỦY QUYỀN
    3. Điền thông tin ủy quyền
    
    OUTPUT BẮT BUỘC:
    {
      "HasMultipleCCCD": true,
      "ChuHo_HoTen": "LÊ VĂN SƠN",
      "ChuHo_SoDinhDanh": "042093011745",
      "ChuHo_DiaChi": {
        "quocGia": "Việt Nam",
        "tinh": "Lâm Đồng",
        "xa": "Đơn Dương",
        "diaChi": "Số 150 đường 2/4, thôn Thạnh Nghĩa"
      },
      "UyQuyen_CoGiayUyQuyen": false,
      "UyQuyen_NguoiUyQuyen_HoTen": "LÊ VĂN SƠN",
      "UyQuyen_NguoiUyQuyen_SoDinhDanh": "042093011745",
      "UyQuyen_NguoiDuocUyQuyen_HoTen": "NGUYỄN DUY THÁI",
      "UyQuyen_NguoiDuocUyQuyen_SoDinhDanh": "001204018566",
      "UyQuyen_NguoiDuocUyQuyen_GioiTinh": "Nam",
      "UyQuyen_NguoiDuocUyQuyen_NgaySinh": "11/08/2004",
      "UyQuyen_NguoiDuocUyQuyen_DiaChi": {
        "quocGia": "Việt Nam",
        "tinh": "Hà Nội",
        "xa": "Mỹ Đình 1",
        "diaChi": "TDP 13 Nhân Mỹ"
      }
    }
- PHÂN BIỆT 3 LOẠI ĐỊA CHỈ:
  + ChuHo_DiaChi/NguoiNop_DiaChi = địa chỉ cá nhân.
  + TruSo_DiaChi = địa chỉ ở mục "2. Trụ sở của hộ kinh doanh".
  + Thue_DiaChiNhanThongBao = địa chỉ ở mục 5.1 "Địa chỉ nhận thông báo thuế", chỉ điền khi khác trụ sở.
  Không thay thế qua lại giữa các loại địa chỉ này.
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
  + tinh LUÔN trả tên TỈNH/THÀNH PHỐ TRỰC THUỘC TRUNG ƯƠNG (cấp tỉnh), KHÔNG trả tên thành phố/thị xã thuộc tỉnh.
    Ví dụ: "TP Đà Lạt", "Thành phố Đà Lạt", "Đà Lạt" → tinh="Lâm Đồng" (vì Đà Lạt thuộc tỉnh Lâm Đồng).
    "TP Bảo Lộc", "Bảo Lộc" → tinh="Lâm Đồng".
    "TP Buôn Ma Thuột" → tinh="Đắk Lắk".
    "TP Phan Thiết" → tinh="Bình Thuận".
    "TP Tam Kỳ" → tinh="Quảng Nam".
    Các thành phố trực thuộc trung ương (Hà Nội, TP HCM, Đà Nẵng, Cần Thơ, Hải Phòng, Huế) vẫn trả đúng tên đó.
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
- CHỈ có 3 nhóm liên hệ cần trích từ hồ sơ:
  + TruSo_DienThoai/TruSo_Email: mục "2. Trụ sở của hộ kinh doanh".
  + ChuHo_DienThoai/ChuHo_Email: phần thông tin cá nhân của chủ hộ.
  + Thue_DienThoai/Thue_Email: mục 5.1 địa chỉ nhận thông báo thuế.
  KHÔNG lấy liên hệ người nộp thay cho trụ sở, chủ hộ hoặc thuế.
- NGÀNH NGHỀ (mục 3, thường là BẢNG "STT | Tên ngành | Mã ngành | Ngành nghề kinh doanh chính"):
  BẮT BUỘC liệt kê ĐẦY ĐỦ MỌI dòng CÓ TÊN NGÀNH vào NganhNghe_DanhSach, mỗi dòng 1 object {ma, ten, chinh}.
  + Mã ngành là dãy đúng 4 chữ số LIỀN NHAU, không có dấu cách/dấu chấm/dấu gạch. Ví dụ OCR thấy "56 10"
    hoặc "56.10" thì trả ma="5610".
  + Cột "Mã ngành" trên tờ khai (nhất là viết tay) THƯỜNG ĐỂ TRỐNG → khi đó ma="" và VẪN PHẢI trả ten.
    TUYỆT ĐỐI KHÔNG được bỏ trống NganhNghe_DanhSach chỉ vì thiếu mã ngành.
  + Bỏ các dòng trống (không có tên ngành). Giữ nguyên thứ tự xuất hiện.
  + Nếu cột "Ngành nghề kinh doanh chính" đánh dấu ở dòng nào thì chinh=true cho dòng đó (và NganhNghe_TenChinh = tên đó).
- Vốn kinh doanh: trả số tiền bằng chữ số đơn vị đồng. Nếu OCR có cả số và chữ, ưu tiên số ghi ở ô vốn; nếu chỉ có chữ thì chuyển thành số khi chắc chắn.
- THÔNG TIN THUẾ:
  + Thue_SoLaoDong (BẮT BUỘC trích nếu có chữ số): lấy tại mục "Tổng số lao động (dự kiến)". Chỉ cần
    sau cụm này có BẤT KỲ chữ số nào — kể cả 1 chữ số như "2 người", "...4..." — thì LUÔN trả CHỈ chữ
    số đó ("2", "4"). Một chữ số nhỏ VẪN là giá trị hợp lệ, KHÔNG coi là nhiễu. Chỉ bỏ field khi mục đó
    HOÀN TOÀN không có chữ số nào (ô để trống / chỉ có dấu chấm). Không đoán/bịa.
  + Thue_PhuongPhapTinh: lấy tại mục "Phương pháp tính thuế GTGT". Chỉ chọn phương pháp có ô/checkbox được đánh dấu
    (☑, ☒, x, X) ngay trước hoặc cùng dòng: "Phương pháp kê khai" -> trả "Phương pháp kê khai";
    "Phương pháp khoán" -> trả "Phương pháp khoán". Không lấy phương pháp không được đánh dấu.
- Ngày tháng chuẩn dd/mm/yyyy khi có đủ ngày-tháng-năm; nếu giấy chỉ có tháng/năm hoặc năm thì giữ đúng mức chi tiết đọc được.
- Ngày sinh: CHỈ điền ngày khi đọc được số ngày hợp lệ (01-31). Nếu ô ngày trống/mờ/chỉ thấy "0" (vd OCR "Sinh ngày: 0 / 7 1989") thì trả "mm/yyyy" (vd "07/1989") và TUYỆT ĐỐI KHÔNG đoán/bịa số ngày.
- Giới tính chỉ trả "Nam" hoặc "Nữ".

KHÔNG trả tên field UI kiểu ctl00$C$...; chỉ trả các field compact trong schema."""
