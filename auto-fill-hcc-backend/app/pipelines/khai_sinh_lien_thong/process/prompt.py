"""Procedure-specific compact prompt rules for "Đăng ký khai sinh liên thông"."""

EXTRA_RULES = """
Đầu vào gồm CCCD/CMND của CHA, CCCD/CMND của MẸ, GIẤY CHỨNG SINH của con, và CÓ THỂ có GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ.

# ═══ A. NGUYÊN TẮC NGUỒN & ƯU TIÊN (CHUNG) ═══
- ƯU TIÊN NGUỒN: nếu CÓ CCCD của cha/mẹ thì dùng CCCD; chỉ dùng giấy chứng nhận kết hôn (hoặc giấy chứng sinh/cam đoan) để suy THÔNG TIN CÁ NHÂN cha/mẹ (họ tên, ngày sinh, dân tộc, nơi cư trú...) KHI KHÔNG có CCCD tương ứng. Vẫn cố đọc đủ cả hai khi có.
- LƯU Ý PHÂN BIỆT: quy tắc ưu tiên trên CHỈ áp cho THÔNG TIN CÁ NHÂN cha/mẹ. Các trường SỐ/NGÀY/NƠI CẤP của chính GIẤY CHỨNG NHẬN KẾT HÔN (GcnKetHon_*) là DỮ LIỆU CỦA FORM → LUÔN phải trích khi hồ sơ CÓ giấy kết hôn, BẤT KỂ cha/mẹ đã có CCCD hay chưa (xem mục G). Đừng bỏ qua giấy kết hôn chỉ vì đã có CCCD.
- Mỗi nhóm CccdNam_*/CccdNu_* phải lấy TRỌN từ MỘT CCCD, KHÔNG trộn tên từ giấy chứng sinh với số định danh từ CCCD (ngoại lệ: dân tộc — xem mục E — và các fallback nêu ở mục C/D).
- KHÔNG lấy thông tin người lớn trên CCCD để điền Gcs_* (thông tin con); và ngược lại KHÔNG lấy thông tin con để điền CccdNam_*/CccdNu_*.
- Tên cha/mẹ ghi trên GIẤY CHỨNG SINH chỉ dùng để ĐỐI CHIẾU chọn đúng CCCD, KHÔNG trả ra output khi người đó ĐÃ có CCCD hoặc giấy kết hôn: CccdNam_HoTen/CccdNu_HoTen luôn là tên trên CCCD, kể cả khi khác tên trên giấy chứng sinh. NGOẠI LỆ cho MẸ: xem mục D.

# ═══ B. THÔNG TIN CON (Gcs_*) ═══
## B1. Nguồn thông tin con
- Gcs_* lấy từ GIẤY CHỨNG SINH. Trẻ sơ sinh KHÔNG có CCCD/CMND.
- Khi KHÔNG có giấy chứng sinh thì lấy Gcs_* từ GIẤY CAM ĐOAN (sinh con tại nhà/ngoài cơ sở y tế) — tiêu đề "GIẤY CAM ĐOAN", có dòng "Quan hệ với người được khai sinh" và "dự định đặt tên". Trích từ giấy cam đoan:
  + Gcs_HoTenCon = tên ở "và dự định đặt tên là: <tên>".
  + Gcs_NgaySinhCon = NGÀY SINH CON ở cụm "Vào hồi ... giờ ... phút, ngày <D> tháng <M> năm <Y>" → dd/mm/yyyy. ĐÂY LÀ NGÀY SINH CON, TUYỆT ĐỐI KHÔNG lấy ngày làm giấy/ngày cam đoan (dòng "Hôm nay, ngày ...").
  + Gcs_GioiTinhCon = ô được ĐÁNH DẤU ở "có sinh ra 1 bé Trai [ ] Gái [ ]": Trai→"Nam", Gái→"Nữ" (ô có "[x]"/"[X]"/dấu tích).
  + Gcs_NoiSinh = nơi ở "Tại bản: <chi tiết>, xã <X>, tỉnh <Y>" → object {tinh,xa,diaChi} (tách như địa chỉ, xem mục F).

## B2. Họ tên con (Gcs_HoTenCon) trên giấy chứng sinh
- Gcs_HoTenCon = HỌ TÊN ĐẦY ĐỦ của ĐỨA TRẺ (người được khai sinh), lấy ở trường "Dự định đặt tên con là". Hiểu cấu trúc giấy chứng sinh để định vị đúng:
  + Phần ĐẦU là khối THÔNG TIN NGƯỜI MẸ: "Họ và tên mẹ/NND", năm sinh, số định danh/CCCD, nơi đăng ký thường trú, dân tộc của mẹ.
  + Phần SAU là khối THÔNG TIN CA SINH của con: giới tính của con, số con trong lần sinh, "Dự định đặt tên con là", "Cân nặng: ... kg", người đỡ đẻ, người ghi phiếu.
  + OCR có thể XÁO TRỘN vị trí, nhưng chỉ trả tên khi có một giá trị họ tên riêng biệt được gắn rõ với nhãn "Dự định đặt tên con là" trong khối ca sinh. Không tự tìm một tên người khác để bù vào field này.
  + Nếu sau nhãn là rỗng, "/", "\\", "-", "_", chỉ có dấu chấm/gạch, hoặc ghi "chưa đặt tên"/"chưa có tên" → trẻ CHƯA CÓ TÊN: BỎ HẲN Gcs_HoTenCon.
  + TUYỆT ĐỐI KHÔNG lấy tên ở KHỐI CHỮ KÝ CUỐI giấy (kèm chức danh "BSCKII", "Phó trưởng khoa", "Đại diện cơ sở KBCB", "Người đỡ đẻ", "Thân nhân của trẻ", "Người ghi phiếu").
  + Tên con là MỘT NGƯỜI KHÁC với mẹ → TUYỆT ĐỐI không trả trùng "Họ và tên mẹ/NND". Nếu ứng viên trùng tên mẹ thì BỎ Gcs_HoTenCon, KHÔNG tìm tên khác để thay thế.
  + CCCD và GIẤY RA VIỆN trong hồ sơ là giấy tờ của người lớn/người mẹ; tên người bệnh hoặc tên trên CCCD KHÔNG BAO GIỜ là tên con.
  + Đây là họ tên người (2-4 từ), KHÔNG phải tên dân tộc (Giáy, Kinh, Mông, Thái, Tày, Nùng, Dao...), KHÔNG phải tên người đỡ đẻ/người ghi phiếu/thủ trưởng CSYT, KHÔNG phải "Họ tên cha".
  + Không tìm được họ tên con riêng biệt (khác mẹ) → ĐỂ TRỐNG, tuyệt đối không copy tên mẹ.

## B3. Dân tộc con (Gcs_DanTocCon)
- Giấy chứng sinh KHÔNG có dân tộc của CON — dòng "Dân tộc" nằm trong KHỐI MẸ là dân tộc của MẸ (→ CccdNu_DanToc), KHÔNG phải của con. Để TRỐNG Gcs_DanTocCon (trừ khi giấy ghi rõ dân tộc riêng của con).

## B4. Nơi sinh (Gcs_NoiSinh)
- Gcs_NoiSinh BẮT BUỘC khi có GIẤY CHỨNG SINH — TUYỆT ĐỐI KHÔNG bỏ trống. Lấy từ dòng "Tại:" trên giấy chứng sinh:
  + diaChi = TÊN ĐẦY ĐỦ cơ sở y tế/bệnh viện (bệnh viện tuyến tỉnh thì KÈM tên tỉnh, vd "Bệnh viện đa khoa tỉnh Lai Châu"). KHÔNG kèm xã/huyện.
  + tinh = tỉnh của cơ sở: suy từ tên bệnh viện tuyến tỉnh, HOẶC lấy theo tỉnh ở "Nơi cư trú" của mẹ ghi TRÊN CHÍNH giấy chứng sinh.
  + xa = phường/xã nơi cơ sở đặt trụ sở nếu xác định được.
  + Dù chỉ đọc được TÊN cơ sở (thiếu tỉnh/xã), VẪN phải trả Gcs_NoiSinh với ít nhất diaChi + tinh — không được để trống cả object.
  + Gcs_NoiSinh KHÔNG áp dụng quy tắc tách địa chỉ ở mục F — diaChi là tên cơ sở y tế.
  + Nếu hồ sơ CÓ TỜ KHAI ĐĂNG KÝ KHAI SINH: trích THÊM field RIÊNG Tk_NoiSinh = dòng "Nơi sinh" trên tờ khai (object {tinh,xa,diaChi}), lấy NGUYÊN VĂN (kể cả số nhà/đường/phố). Nơi sinh điền vào form ƯU TIÊN Tk_NoiSinh (tờ khai); chỉ khi KHÔNG có tờ khai mới dùng Gcs_NoiSinh (giấy chứng sinh). Trích cả hai khi có, hệ thống tự chọn ưu tiên.
- Xã/phường nơi sinh chỉ trả khi OCR/tờ khai xác định đúng địa bàn của cơ sở. Không dùng xã/phường
  đã biết của một bệnh viện thuộc tỉnh khác; nếu chỉ biết tên bệnh viện và tỉnh thì để xa trống.
- Tk_QueQuanCon = QUÊ QUÁN của CON lấy ở dòng "Quê quán" trong TỜ KHAI ĐĂNG KÝ KHAI SINH (nếu hồ sơ có tờ khai). Tách địa chỉ theo mục F. Đây là quê quán của ĐỨA TRẺ, KHÔNG phải nơi cư trú/quê quán của cha mẹ. Không có tờ khai hoặc tờ khai không ghi quê quán → để TRỐNG.

# ═══ C. THÔNG TIN CHA (CccdNam_*) ═══
- CccdNam_* ưu tiên lấy từ giấy tờ CĂN CƯỚC/CMND có giới tính "Nam" (dân tộc: xem mục E). NẾU KHÔNG CÓ CCCD/CMND nào của cha thì LẤY THÔNG TIN CHA TỪ block "chồng"/"bên nam" của GIẤY CHỨNG NHẬN KẾT HÔN: họ tên (CccdNam_HoTen), ngày sinh (CccdNam_NgaySinh), dân tộc (CccdNam_DanToc), quốc tịch (CccdNam_QuocTich), nơi cư trú (CccdNam_NoiCuTru), số định danh (CccdNam_SoDinhDanh — lấy ở "Giấy tờ tùy thân: Thẻ căn cước số ...").
- CccdNam_QueQuan lấy từ mục "Quê quán"/"Place of origin" của người cha(nam) nếu OCR đọc được; nếu không có thì bỏ qua.
- CccdNam_NoiCuTru (và CccdNu_NoiCuTru) lấy từ mục "Nơi thường trú"/"Place of residence" (tách địa chỉ theo mục F).
- Với CHA, giấy chứng sinh thường không có thông tin cha → KHÔNG lấy CccdNam_HoTen từ giấy chứng sinh.

# ═══ D. THÔNG TIN MẸ (CccdNu_*) — theo thứ tự ưu tiên nguồn ═══
- (1) Ưu tiên CCCD/CMND có giới tính "Nữ" (dân tộc: xem mục E).
- (2) KHÔNG có CCCD mẹ → lấy từ block "vợ"/"bên nữ" của GIẤY CHỨNG NHẬN KẾT HÔN (đối chiếu tên/số định danh khớp với mẹ trên giấy chứng sinh): họ tên, ngày sinh, dân tộc, quốc tịch, nơi cư trú, số định danh. Nếu ngày sinh mẹ trên giấy kết hôn không đọc được, có thể lấy NĂM SINH mẹ ở giấy chứng sinh.
- (3) KHÔNG có CCCD mẹ VÀ giấy kết hôn không đọc được bên vợ → LẤY TRỌN THÔNG TIN MẸ TỪ GIẤY CHỨNG SINH (khối "Họ, chữ đệm, tên khai sinh của mẹ"): CccdNu_HoTen = tên mẹ trên giấy chứng sinh; CccdNu_SoDinhDanh = "Số ĐDCN/Hộ chiếu" của mẹ; CccdNu_NgaySinh = ngày/năm sinh mẹ; CccdNu_DanToc = dân tộc mẹ (Giấy chứng sinh là NGUỒN HỢP LỆ cho mẹ khi không có CCCD/giấy kết hôn — KHÔNG được bỏ trống mẹ nếu giấy chứng sinh có các thông tin này.)
- RIÊNG nơi cư trú của MẸ (CccdNu_NoiCuTru) có THỨ TỰ ƯU TIÊN NGUỒN RIÊNG (khác các trường khác của mẹ):
  (i) GIẤY CHỨNG NHẬN KẾT HÔN (block "vợ") — ưu tiên CAO NHẤT;
  (ii) rồi tới GIẤY CHỨNG SINH (dòng "Nơi cư trú" trong khối mẹ);
  (iii) sau cùng mới tới CCCD của mẹ.
  diaChi của mẹ KHÔNG BAO GIỜ là tên phường/xã (TUYỆT ĐỐI không đặt diaChi = "Phường ..."/"Xã ..." trùng với xa); diaChi chỉ là bản/tổ dân phố/thôn/xóm/số nhà. Nếu nguồn chỉ ghi "Phường X, tỉnh Y" (không có chi tiết) thì diaChi để TRỐNG.
- (4) GIẤY CAM ĐOAN do MẸ viết ("Quan hệ với người được khai sinh: Mẹ đẻ") — khi chưa có CCCD mẹ, lấy CccdNu_* từ đây: CccdNu_HoTen ("Tên tôi là"), CccdNu_SoDinhDanh ("CCCD số"), CccdNu_NgaySinh ("Sinh năm/ngày"), CccdNu_DanToc ("Dân tộc"), CccdNu_NoiCuTru ("Thường trú tại"). Ưu tiên CCCD nếu có.

# ═══ E. DÂN TỘC CHA/MẸ (CccdNam_DanToc = CHA, CccdNu_DanToc = MẸ) ═══
- Thẻ CCCD/Căn cước gắn chip (mẫu mới) thường KHÔNG in dân tộc → PHẢI lấy dân tộc từ giấy tờ khác CÓ ghi, đối chiếu ĐÚNG NGƯỜI theo họ tên/số định danh. BẮT BUỘC điền dân tộc cho CẢ cha VÀ mẹ nếu bất kỳ giấy nào ghi — KỂ CẢ khi người đó ĐÃ CÓ CCCD (ĐỪNG vì cha/mẹ đã có CCCD mà bỏ qua dân tộc của họ).
- THỨ TỰ ƯU TIÊN NGUỒN dân tộc (áp cho CẢ cha và mẹ):
  + (1) TỜ KHAI ĐĂNG KÝ KHAI SINH: dòng "Dân tộc" trong khối "người cha" → CccdNam_DanToc; khối "người mẹ" → CccdNu_DanToc.
  + (2) GIẤY CHỨNG NHẬN KẾT HÔN: dân tộc mục "chồng"/"bên nam" → dân tộc CHA (CccdNam_DanToc); mục "vợ"/"bên nữ" → dân tộc MẸ (CccdNu_DanToc). BẮT BUỘC lấy KỂ CẢ khi cha/mẹ đã có CCCD — vd giấy kết hôn ghi "chồng ... Dân tộc: Mông" thì CccdNam_DanToc = "Mông" dù cha đã có thẻ CCCD.
  + (3) GIẤY CHỨNG SINH: dòng "Dân tộc: ..." trong KHỐI MẸ (ngay dưới "Họ tên khai sinh của mẹ") → CccdNu_DanToc (chỉ có dân tộc mẹ). BẮT BUỘC lấy kể cả khi mẹ đã có CCCD.
  + Có thể lấy từ giấy tờ khác miễn đối chiếu tên đúng cha/mẹ ứng với dân tộc đó.
- TUYỆT ĐỐI không lấy dân tộc người này gán cho người khác (vd dân tộc con/mẹ KHÔNG gán cho cha).
- KHÔNG giấy tờ nào ghi rõ dân tộc của người đó → ĐỂ TRỐNG (không bịa, không mặc định "Kinh"). Nhưng nếu CÓ THÔNG TIN thì BẮT BUỘC ghi rõ dân tộc của CẢ cha và mẹ.
- CHUẨN HÓA tên dân tộc về đúng danh mục (sửa lỗi/biến thể OCR): Kinh, Mông, Thái, Dao, Giáy, Tày, Nùng, Mường, Hà Nhì, Lự, Lào, Khơ Mú, Hoa, Sán Chay, Sán Dìu, Cống, Mảng, La Hủ, Si La, Hmông... Ví dụ OCR "Giây"/"Záy" → "Giáy"; "Hmông"/"H'Mông"/"H Mông" → "Mông"; "Kinnh" → "Kinh".

# ═══ F. TÁCH ĐỊA CHỈ (CccdNam_NoiCuTru, CccdNu_NoiCuTru, CccdNam_QueQuan — object {tinh,xa,diaChi}) ═══
Địa chỉ hành chính 2 cấp XÃ/PHƯỜNG/THỊ TRẤN → TỈNH/THÀNH PHỐ:
- xa = TÊN xã/phường/thị trấn, CHỈ lấy TÊN — KHÔNG kèm tiền tố loại đơn vị (Xã/Phường/Thị trấn). Vd: "Xã Tả Lèng" → xa="Tả Lèng". tinh = tên tỉnh/thành phố.
- diaChi = phần CHI TIẾT đứng TRƯỚC xã/phường: tổ, tổ dân phố, bản, thôn, xóm, khu, số nhà, đường. TUYỆT ĐỐI KHÔNG đưa tên phường/xã/thị trấn (hay huyện/tỉnh) vào diaChi. Không có phần chi tiết → diaChi để TRỐNG.
- ĐẾM TỪ CUỐI khi địa chỉ liệt kê không nhãn (dạng cũ 3 cấp "[chi tiết], xã, HUYỆN, tỉnh"): cuối = tỉnh; phần NGAY TRƯỚC tỉnh nếu là CẤP HUYỆN (huyện/quận/thị xã/thành phố thuộc tỉnh) thì BỎ HẲN; phần trước đó = xã. Tên xã/phường vùng cao CÓ THỂ bắt đầu bằng "Bản"/"Nậm"/"Mường"/"Pa" — KHÔNG coi là chi tiết chỉ vì bắt đầu bằng "Bản", VỊ TRÍ (áp chót, trước cấp huyện/tỉnh) mới quyết định là xã.
- XÃ LUÔN BẮT BUỘC: KHÔNG được bỏ trống xa khi giấy tờ CÓ thông tin phường/xã. Nếu chỉ đọc được "chi tiết" và "tỉnh" mà thiếu xã, phải soát lại — phần đứng NGAY TRƯỚC tỉnh (bỏ cấp huyện nếu có) chính là xã. KHÔNG dồn xã + huyện vào diaChi.
- ƯU TIÊN NGUỒN 2 CẤP: nếu cùng người mà một giấy ghi kiểu CŨ 3 cấp (xã, HUYỆN, tỉnh) còn giấy khác ghi 2 cấp (xã → tỉnh, KHÔNG huyện — đơn vị hành chính HIỆN HÀNH) thì DÙNG bản 2 cấp, kể cả khi tên xã hai bản khác nhau do sáp nhập. Vd generic: giấy kết hôn ghi "xã B, tỉnh C" (2 cấp), CCCD ghi "xã A, huyện Y, tỉnh C" (3 cấp) → chọn "xã B, tỉnh C".
- RIÊNG Gcs_NoiSinh KHÔNG áp dụng mục F (xem B4).
## LƯU Ý QUAN TRỌNG
- ĐỊA CHỈ MỘT NGƯỜI PHẢI LẤY TRỌN TỪ MỘT GIẤY: diaChi, xa, tinh của CÙNG một người phải CÙNG đến từ MỘT giấy. TUYỆT ĐỐI KHÔNG ghép diaChi (bản/tổ/thôn/số nhà) của giấy này với xa của giấy khác — nếu hai giấy ghi HAI ĐỊA CHỈ KHÁC NHAU (xã khác nhau) mà ghép như vậy sẽ tạo ra địa chỉ KHÔNG CÓ THẬT.
- BÙ TRƯỜNG THIẾU (CHỈ khi CÙNG một địa chỉ): nếu một giấy THIẾU xã nhưng giấy khác của CHÍNH người đó ghi rõ xã của CÙNG nơi đó (cùng phần chi tiết/tỉnh) thì ĐƯỢC lấy xã bù vào. Chỉ bù khi chắc chắn là CÙNG một địa chỉ; KHÔNG bù khi hai giấy là hai nơi khác nhau.
- KHI HAI GIẤY MÂU THUẪN (ghi XÃ KHÁC NHAU cho cùng người): chọn TRỌN địa chỉ từ MỘT nguồn theo ưu tiên — nơi cư trú MẸ: giấy CHỨNG NHẬN KẾT HÔN (block vợ) > giấy CHỨNG SINH > CCCD (xem mục D); nơi cư trú CHA: ưu tiên CCCD, rồi tới giấy kết hôn (block chồng). Lấy trọn diaChi+xa+tinh từ nguồn được ưu tiên đó, không trộn với nguồn kia.

# ═══ G. GIẤY CHỨNG NHẬN KẾT HÔN (GcnKetHon_*) ═══
- GcnKetHon_* CHỈ lấy từ tài liệu là GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ.
- BẮT BUỘC: HỄ CÓ giấy chứng nhận kết hôn trong hồ sơ → PHẢI trích ĐỦ GcnKetHon_So, GcnKetHon_QuyenSo, GcnKetHon_NgayCap, GcnKetHon_NoiCap. Đây là SỐ/NGÀY/NƠI CẤP CỦA CHÍNH TỜ GIẤY (dữ liệu của FORM), KHÔNG phải "thông tin cha/mẹ" → TUYỆT ĐỐI KHÔNG bỏ qua giấy kết hôn chỉ vì cha/mẹ đã có CCCD. Trường nào OCR THỰC SỰ không đọc được thì bỏ, KHÔNG bịa.
- GcnKetHon_So lấy ở dòng "Số:" NGAY ĐẦU tài liệu, dạng "<số>/<năm>" (vd "119/2026") HOẶC chỉ "<số>" (vd "140"). LƯU Ý OCR hay MẤT DẤU: "Số" có thể hiện thành "Só"/"So" — vẫn phải nhận đúng.
- GcnKetHon_QuyenSo lấy ở dòng "Quyển số:" (vd "01/2013").
- GcnKetHon_NgayCap lấy từ "Ngày, tháng, năm đăng ký"/"Ngày cấp" (vd "01/02/2025"); GcnKetHon_NoiCap lấy từ "Nơi đăng ký kết hôn" (tên cơ quan, vd "UBND...").
- TUYỆT ĐỐI KHÔNG lấy số/ngày của GIẤY CHỨNG SINH hay giấy tờ khác để điền GcnKetHon_*. Số giấy chứng sinh thường chứa "GCS" (vd "01327.GCS.12096.25") — KHÔNG phải số giấy CN kết hôn, không được dùng. Không tìm thấy đúng số → để trống.

# ═══ H. LIÊN HỆ ═══
- LienHe_SoDienThoai: CỐ GẮNG đọc số điện thoại liên hệ trong giấy tờ (vd dòng "Số điện thoại:..." trong văn bản/đơn). Trả số di động VN 10 số bắt đầu bằng "0"; sửa lỗi OCR phổ biến (S→5, O→0); nếu thiếu số 0 đứng đầu thì thêm vào. Không bịa nếu không đọc được.

# ═══ H2. ĐỀ NGHỊ CẤP BẢN SAO ═══
- CopyRequest_Quantity CHỈ lấy từ mục "Đề nghị cấp bản sao"/"Số lượng ... bản" trên tài liệu có đúng
  tiêu đề "TỜ KHAI ĐĂNG KÝ KHAI SINH".
- Chỉ trả khi tờ khai ghi SỐ LƯỢNG BẢN SAO THẬT, là số nguyên dương. Bỏ dấu chấm/gạch/ô trống quanh số
  và bỏ số 0 đứng đầu (vd "...5......bản" -> "5", "02 bản" -> "2").
- Nếu tờ khai không nói gì về số lượng bản sao, hoặc mục số lượng để trống, thì BỎ field
  CopyRequest_Quantity. TUYỆT ĐỐI không tự mặc định 1.

# ═══ J. TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ (CT01) — Ct01_* ═══
- CHỈ trích khi hồ sơ CÓ tài liệu tiêu đề "TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ" (mẫu CT01). Không có → để TRỐNG toàn bộ Ct01_*.
- Đây là thông tin CHỦ HỘ nơi trẻ đăng ký thường trú, KHÁC người kê khai:
  + Ct01_ChuHoHoTen = mục 7 "Họ, chữ đệm và tên chủ hộ". TUYỆT ĐỐI KHÔNG lấy mục 1 "Họ, chữ đệm và tên" (đó là NGƯỜI ĐƯỢC KHAI SINH/người kê khai).
  + Ct01_ChuHoSoDinhDanh = mục 9 "Số định danh cá nhân của chủ hộ" (12 số). KHÔNG nhầm với mục 4 (số định danh người kê khai).
  + Ct01_QuanHeVoiChuHo = mục 8 "Mối quan hệ với chủ hộ" (vd "Con đẻ", "Cháu ngoại", "Cháu nội").

# ═══ I. KHÔNG TRẢ (field cấm) ═══
- Không trả field mặc định hoặc field UI như Ho, ChaHo, MeHo, MaQuocTich, LoaiCuTru, NycQuanHe,
  CapBanSao, BanSaoSoLuong.
"""
