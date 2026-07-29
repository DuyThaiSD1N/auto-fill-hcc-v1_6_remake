"""Procedure-specific compact prompt rules for "Đăng ký kết hôn"."""

EXTRA_RULES = """
Đầu vào gồm giấy tờ của hai người đăng ký kết hôn (CCCD/CMND, tờ khai và giấy tờ liên quan),
có thể không được gắn role chồng/vợ.

NGUỒN DỮ LIỆU:
- Tự phân biệt hai CCCD bằng trường giới tính trên chính giấy tờ: Nam -> nhóm CccdNam_*, Nữ -> nhóm CccdNu_*.
- CccdNam_* CHỈ lấy từ giấy tờ có tiêu đề CĂN CƯỚC/CMND và giới tính "Nam".
- CccdNu_* CHỈ lấy từ giấy tờ có tiêu đề CĂN CƯỚC/CMND và giới tính "Nữ".
- Không phân biệt nam/nữ theo tên file, thứ tự upload, hoặc suy đoán từ họ tên.
- BẮT BUỘC cố đọc CccdNam_NoiCap/CccdNu_NoiCap (cơ quan cấp) trên CCCD/Căn cước, trả ĐÚNG cơ quan ghi trên thẻ:
  + Thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", thường cấp từ 01/7/2024): cơ quan cấp ghi
    "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" -> trả "Bộ Công an".
  + Thẻ CĂN CƯỚC CÔNG DÂN gắn chip cũ: nếu thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ
    XÃ HỘI" -> trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
  + TUYỆT ĐỐI không mặc định "Cục Cảnh sát..." cho thẻ Căn cước mới do Bộ Công an cấp.
- NGUỒN NƠI CƯ TRÚ — PHẢI TRÍCH RIÊNG TỪNG NGUỒN, KHÔNG TỰ CHỌN NGUỒN:
  + ToKhaiNam_NoiCuTru_TrongNuoc / ToKhaiNu_NoiCuTru_TrongNuoc CHỈ lấy từ hàng "Nơi cư trú" ở đúng
    cột Bên nam/Bên nữ của TỜ KHAI ĐĂNG KÝ KẾT HÔN. Đối chiếu đúng cột theo tiêu đề, họ tên và/hoặc số định danh.
  + CccdNam_NoiCuTru_TrongNuoc / CccdNu_NoiCuTru_TrongNuoc CHỈ lấy nơi cư trú in trên CCCD/CMND của chính người đó.
  + Nếu có cả tờ khai và CCCD thì BẮT BUỘC trả CẢ HAI field nguồn tương ứng; mapper sẽ tự ưu tiên tờ khai.
  + Không lấy địa chỉ từ giấy xác nhận tình trạng hôn nhân, giấy phép lái xe, bản cam đoan hoặc giấy tờ phụ
    gán vào bất kỳ field nơi cư trú nào nêu trên.
- TÁCH ĐỊA CHỈ (mọi field *_NoiCuTru_TrongNuoc — object {quocGia,tinh,xa,diaChi}):
  + xa = TÊN xã/phường/thị trấn, CHỈ lấy TÊN (bỏ tiền tố Xã/Phường/Thị trấn); tinh = tỉnh/thành phố;
    diaChi = phần chi tiết đứng TRƯỚC xã (tổ/tổ dân phố/thôn/xóm/bản/số nhà/đường). KHÔNG đưa tên xã/huyện/tỉnh vào diaChi.
  + Khi địa chỉ trên tờ khai có nhãn rõ "Xã ..." hoặc "Phường ..." thì đơn vị mang nhãn đó BẮT BUỘC là xa;
    các thành phần "Thôn ...", "Tổ ...", "Khu phố ..." đứng trước vẫn thuộc diaChi, không được chọn chúng làm xa.
  + XÃ BẮT BUỘC khi giấy có phường/xã. ĐẾM TỪ CUỐI khi liệt kê không nhãn ("[chi tiết], xã, HUYỆN, tỉnh"):
    cuối = tỉnh; phần NGAY TRƯỚC tỉnh nếu là CẤP HUYỆN (huyện/quận/thị xã/thành phố thuộc tỉnh) thì BỎ HẲN;
    phần trước đó = xã. Tên xã vùng cao có thể bắt đầu "Bản"/"Nậm"/"Mường"/"Pa" — vị trí (áp chót) mới quyết định là xã.
- QUỐC TỊCH (CccdNam_QuocTich, CccdNu_QuocTich): CHỈ điền khi giấy tờ KHÔNG phải Việt Nam.
  + Suy từ tiêu đề quốc gia: "CỘNG HOÀ NHÂN DÂN TRUNG HOA" → "Trung Quốc"; "CỘNG HOÀ DÂN CHỦ NHÂN DÂN LÀO" → "Lào"; "VƯƠNG QUỐC CAMPUCHIA" → "Campuchia".
  + Hoặc nhãn "Quốc tịch:" nếu ghi rõ trên giấy tờ.
  + CCCD/Căn cước Việt Nam → BỎ QUA field này (Python tự mặc định "Việt Nam").
  + quocGia trong object địa chỉ cũng phải khớp quốc tịch: người Trung Quốc → quocGia="Trung Quốc".
- DÂN TỘC (CccdNam_DanToc = dân tộc BÊN NAM, CccdNu_DanToc = dân tộc BÊN NỮ): CCCD/Căn cước gắn chip
  thường KHÔNG ghi dân tộc → hãy tìm dân tộc trong CÁC GIẤY TỜ KHÁC có ghi (TỜ KHAI ĐĂNG KÝ KẾT HÔN,
  bản cam đoan, giấy tờ hộ tịch khác), ĐỐI CHIẾU ĐÚNG NGƯỜI:
  + TỜ KHAI ĐĂNG KÝ KẾT HÔN THƯỜNG có hàng "Dân tộc" ghi cho CẢ HAI cột (bên nam VÀ bên nữ). Khi đó BẮT BUỘC
    trả ĐỦ CẢ HAI: CccdNam_DanToc VÀ CccdNu_DanToc — KHÔNG được bỏ sót bên nào, KỂ CẢ khi hai bên GIỐNG hệt
  + Bảng tờ khai có thể xếp cột theo THỨ TỰ BẤT KỲ (nhiều tờ ghi cột "Bên nữ" TRƯỚC cột "Bên nam"). Xác định cột
    nào là nam/nữ theo TIÊU ĐỀ cột ("Bên nam"/"Bên nữ") hoặc theo hàng Họ tên, TUYỆT ĐỐI không mặc định nam đứng trước.
  + Đối chiếu theo HỌ TÊN và/hoặc SỐ ĐỊNH DANH để biết dân tộc đó là của bên nam hay bên nữ; gán dân tộc
    cho ĐÚNG người đó. TUYỆT ĐỐI không lấy dân tộc của người này gán cho người kia.
  + Nếu KHÔNG giấy tờ nào ghi rõ dân tộc của người đó → ĐỂ TRỐNG (KHÔNG bịa, KHÔNG mặc định "Kinh" hay
    bất kỳ dân tộc nào). Chỉ điền khi PHÁT HIỆN được.
  + VÍ DỤ: nếu CHỈ tờ khai của BÊN NỮ ghi dân tộc, còn bên nam không giấy nào ghi → CHỈ trả CccdNu_DanToc,
    ĐỂ TRỐNG CccdNam_DanToc (TUYỆT ĐỐI KHÔNG copy dân tộc bên nữ sang bên nam và ngược lại).
  + Lưu ý option trên form: dân tộc H'Mông" (gồm các cách"H'Mông"/"H Mông"/"Hmông") PHẢI trả là
    "Mông (Hmông)"
  + Còn dân tộc Mông thì ghi "Mông"
  + Dân tộc phổ biến:
    Kinh, Mông, Dao, Giáy, Thái, Tày, Nùng, Hà Nhì, Lự, Lào, Khơ Mú, Mường...
- Quốc tịch chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam; mặc định Việt Nam.
- SỐ LẦN KẾT HÔN: nếu tờ khai/giấy tờ có mục "Kết hôn lần thứ mấy" (hoặc "Số lần kết hôn") ghi số cho từng bên
  thì trả CccdNam_SoLanKetHon (cột BÊN NAM) và CccdNu_SoLanKetHon (cột BÊN NỮ) là SỐ NGUYÊN (vd "1", "2", "3").
  Đối chiếu ĐÚNG CỘT nam/nữ theo tiêu đề bảng. KHÔNG có mục này → bỏ qua, KHÔNG mặc định.
- CẤP BẢN SAO — CHỈ đọc từ mục "Đề nghị cấp bản sao" trên tài liệu có đúng tiêu đề
  "TỜ KHAI ĐĂNG KÝ KẾT HÔN"; không lấy yêu cầu/số lượng bản sao từ giấy tờ khác:
  + Tích/chọn Có -> CopyRequest_WantsCopy = "Có"; tích/chọn Không -> "Không".
  + CopyRequest_Quantity = số lượng bản sao dương ghi thật trên chính tờ khai, bỏ số 0 đứng đầu
    (ví dụ "02 bản" -> "2").
  + Nếu có số lượng dương thì BẮT BUỘC trả CopyRequest_WantsCopy = "Có", kể cả OCR không thể hiện rõ
    ô Có hay Không được tích. Số lượng dương là bằng chứng người khai có đề nghị cấp bản sao.
  + Không có dấu chọn và không có số lượng thì bỏ cả hai field. TUYỆT ĐỐI không mặc định "Có"
    và không mặc định số lượng.
- Không trả field UI/default như HoTenBenNam, HoTenBenNu, LoaiGiayToDinhDanh_*, SoGiayToDinhDanh_*,
  LoaiCuTru_*, NoiCuTru_*, SoLanKetHon_BenNam/BenNu, tình trạng hôn nhân, loại đăng ký,
  CapBanSao, SoLuong.
- Họ tên/số định danh/ngày sinh/ngày-nơi cấp của mỗi nhóm CccdNam_*/CccdNu_* phải lấy trọn từ
  đúng MỘT CCCD, không trộn giữa hai người. RIÊNG dân tộc được phép lấy từ giấy tờ khác theo quy tắc DÂN TỘC;
  nơi cư trú phải tách riêng từng nguồn theo quy tắc NGUỒN NƠI CƯ TRÚ ở trên."""
