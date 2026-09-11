"""Procedure-specific compact prompt rules for "Đăng ký khai sinh liên thông"."""

EXTRA_RULES = """
Đầu vào gồm CCCD/CMND của CHA, CCCD/CMND của MẸ, GIẤY CHỨNG SINH của con, và CÓ THỂ có GIẤY CHỨNG NHẬN KẾT HÔN của cha mẹ.

# ═══ A. NGUYÊN TẮC NGUỒN & ƯU TIÊN (CHUNG) ═══
- ĐỐI CHIẾU NGUỒN: dùng CCCD/CMND đúng người để neo danh tính bố/mẹ khi có; nguồn chọn cho TỪNG FIELD phải tuân thủ đúng thứ tự riêng tại mục C/D/E. Không áp một thứ tự CCCD-first chung cho cả nhóm vì dân tộc và một số thông tin vai trò nằm trên giấy chứng sinh/tờ khai/giấy kết hôn.
- LƯU Ý PHÂN BIỆT: quy tắc ưu tiên trên CHỈ áp cho THÔNG TIN CÁ NHÂN cha/mẹ. Các trường SỐ/NGÀY/NƠI CẤP của chính GIẤY CHỨNG NHẬN KẾT HÔN (GcnKetHon_*) là DỮ LIỆU CỦA FORM → LUÔN phải trích khi hồ sơ CÓ giấy kết hôn, BẤT KỂ cha/mẹ đã có CCCD hay chưa (xem mục G). Đừng bỏ qua giấy kết hôn chỉ vì đã có CCCD.
- ThongTinBo_* và ThongTinMe_* là nhóm THÔNG TIN THEO VAI TRÒ BỐ/MẸ, KHÔNG phải nhóm dữ liệu chỉ lấy từ CCCD nam/nữ. Phải đối chiếu họ tên/số định danh để mọi giá trị trong từng nhóm thuộc ĐÚNG CÙNG MỘT NGƯỜI; nguồn của từng field tuân theo thứ tự riêng tại mục C/D/E.
- KHÔNG lấy thông tin người lớn trên CCCD để điền Gcs_* (thông tin con); và ngược lại KHÔNG lấy thông tin con để điền ThongTinBo_*/ThongTinMe_*.
- CCCD/CMND là nguồn đối chiếu danh tính mạnh khi có, nhưng không được vì đã có CCCD mà bỏ dân tộc hoặc thông tin vai trò ghi rõ trên tờ khai/giấy chứng sinh/giấy kết hôn. Khi các giấy ghi khác nhau, chọn theo đúng thứ tự nguồn của field tại mục C/D/E; tuyệt đối không ghép dữ liệu của hai người khác nhau.

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
  + Chuẩn hóa giá trị sau nhãn: bỏ khoảng trắng và các ký hiệu ngăn cách "/", "\\", "-", "_", "." ở ĐẦU, rồi lấy TOÀN BỘ họ tên còn lại. Ví dụ dạng "/ NGUYỄN VĂN BÉ" phải trả "NGUYỄN VĂN BÉ"; KHÔNG được thấy ký tự đầu tiên là "/" rồi bỏ field khi phía sau vẫn còn chữ.
  + Chỉ khi TOÀN BỘ phần còn lại sau nhãn là rỗng, chỉ gồm các ký hiệu "/", "\\", "-", "_", ".", hoặc ghi "chưa đặt tên"/"chưa có tên" → trẻ CHƯA CÓ TÊN: BỎ HẲN Gcs_HoTenCon.
  + TUYỆT ĐỐI KHÔNG lấy tên ở KHỐI CHỮ KÝ CUỐI giấy (kèm chức danh "BSCKII", "Phó trưởng khoa", "Đại diện cơ sở KBCB", "Người đỡ đẻ", "Thân nhân của trẻ", "Người ghi phiếu").
  + Tên con là MỘT NGƯỜI KHÁC với mẹ → TUYỆT ĐỐI không trả trùng "Họ và tên mẹ/NND". Nếu ứng viên trùng tên mẹ thì BỎ Gcs_HoTenCon, KHÔNG tìm tên khác để thay thế.
  + CCCD và GIẤY RA VIỆN trong hồ sơ là giấy tờ của người lớn/người mẹ; tên người bệnh hoặc tên trên CCCD KHÔNG BAO GIỜ là tên con.
  + Đây là họ tên người (2-4 từ), KHÔNG phải tên dân tộc (Giáy, Kinh, Mông, Thái, Tày, Nùng, Dao...), KHÔNG phải tên người đỡ đẻ/người ghi phiếu/thủ trưởng CSYT, KHÔNG phải "Họ tên cha".
  + Không tìm được họ tên con riêng biệt (khác mẹ) → ĐỂ TRỐNG, tuyệt đối không copy tên mẹ.

## B3. Dân tộc con (Gcs_DanTocCon)
- Giấy chứng sinh KHÔNG có dân tộc của CON — dòng "Dân tộc" nằm trong KHỐI MẸ là dân tộc của MẸ (→ ThongTinMe_DanToc), KHÔNG phải của con. Để TRỐNG Gcs_DanTocCon (trừ khi giấy ghi rõ dân tộc riêng của con).

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

## B5. Thông tin con từ TỜ KHAI ĐĂNG KÝ KHAI SINH (Tk_*)
Khi hồ sơ CÓ TỜ KHAI ĐĂNG KÝ KHAI SINH (tiêu đề có "TỜ KHAI ĐĂNG KÝ KHAI SINH"), BẮT BUỘC trích thêm các field sau từ khối "NGƯỜI ĐƯỢC KHAI SINH" / "KHAI SINH CHO":
- Tk_HoTenCon = họ tên đầy đủ người được khai sinh (dòng "Họ, chữ đệm và tên khai sinh" hoặc "Tên khai sinh"). Ưu tiên hơn Gcs_HoTenCon khi có.
- Tk_NgaySinhCon = ngày sinh của con , dd/mm/yyyy, trên tờ khai.
- Tk_GioiTinhCon = "Nam" hoặc "Nữ". Ưu tiên hơn Gcs_GioiTinhCon khi có.
- Tk_DanTocCon = dân tộc người được khai sinh (dòng "Dân tộc" trong khối CON — KHÔNG phải dòng "Dân tộc" của cha/mẹ). Ưu tiên hơn suy luận từ cha/mẹ.
Trích cả hai nguồn (Gcs_* và Tk_*) khi có; hệ thống tự chọn ưu tiên Tk_* trước.

# ═══ C. THÔNG TIN BỐ/CHA (ThongTinBo_*) — ƯU TIÊN GIẤY CHỨNG SINH / KẾT HÔN ═══
- THỨ TỰ ƯU TIÊN NGUỒN:
  (1) **GIẤY CHỨNG SINH** (khối "người cha" trên giấy chứng sinh của con hoặc con khác) — ưu tiên cao nhất khi có
  (2) **GIẤY CHỨNG NHẬN KẾT HÔN** (block "chồng"/"bên nam") — ưu tiên cao khi có
  (3) **GIẤY KHAI SINH** (bản sao/trích lục của con khác trong hồ sơ, có khối "người cha") — lấy khi không có nguồn (1)(2)
  (4) CCCD/CMND được đối chiếu là của đúng người bố — chỉ dùng khi các nguồn trên không có
- ThongTinBo_HoTen, ThongTinBo_NgaySinh, ThongTinBo_SoDinhDanh, ThongTinBo_QuocTich, ThongTinBo_NoiCuTru: ưu tiên giấy chứng sinh/kết hôn/khai sinh, sau đó mới xét CCCD/CMND đúng người bố
- ThongTinBo_DanToc: áp dụng rule riêng tại mục E; hai nguồn chính bắt buộc soát là tờ khai đăng ký khai sinh (khối bố đẻ/cha) > giấy chứng nhận kết hôn (khối chồng/bên nam).
- ThongTinBo_QueQuan: lấy từ CCCD cũ (có dòng "Quê quán") nếu có
- ThongTinBo_NoiDangKyKhaiSinh: lấy từ thẻ CĂN CƯỚC mới (dòng "Nơi đăng ký khai sinh") nếu có
- LƯU Ý: Khi hồ sơ có GIẤY KHAI SINH (bản sao) của CON KHÁC (anh/chị/em của đứa trẻ đang khai sinh), giấy này thường có đầy đủ thông tin cha/mẹ trong khối "Họ, chữ đệm, tên người cha" và "Họ, chữ đệm, tên người mẹ" → BẮT BUỘC trích thông tin cha từ đó theo thứ tự nguồn ở trên.

# ═══ D. THÔNG TIN MẸ (ThongTinMe_*) — ƯU TIÊN GIẤY CHỨNG SINH ═══
- THỨ TỰ ƯU TIÊN NGUỒN (đơn giản hóa):
  (1) **GIẤY CHỨNG SINH** (khối thông tin mẹ) — ưu tiên cao nhất, luôn có
  (2) **GIẤY KHAI SINH** (bản sao/trích lục của con khác trong hồ sơ, có khối "người mẹ") — lấy khi không có giấy chứng sinh
  (3) GIẤY CHỨNG NHẬN KẾT HÔN (block "vợ"/"bên nữ") — bổ sung khi các nguồn trên thiếu
  (4) CCCD/CMND được đối chiếu là của đúng người mẹ — chỉ dùng khi các nguồn trên không đủ
- ThongTinMe_HoTen: lấy từ giấy chứng sinh (khối mẹ), sau đó giấy khai sinh, giấy kết hôn, cuối cùng CCCD/CMND đúng người mẹ
- ThongTinMe_SoDinhDanh: lấy từ giấy chứng sinh (Số ĐDCN/Hộ chiếu), sau đó giấy khai sinh, giấy kết hôn, cuối cùng CCCD/CMND đúng người mẹ
- ThongTinMe_NgaySinh: ưu tiên giấy chứng sinh (có thể chỉ năm sinh), sau đó giấy khai sinh, giấy kết hôn, cuối cùng CCCD/CMND đúng người mẹ
- ThongTinMe_DanToc: BẮT BUỘC lấy theo đúng thứ tự: giấy chứng sinh (dòng "Dân tộc" trong khối mẹ) > giấy chứng nhận kết hôn (khối vợ/bên nữ) > tờ khai đăng ký khai sinh (khối người mẹ). Có nguồn ưu tiên cao hơn thì không thay bằng nguồn thấp hơn.
- ThongTinMe_QueQuan: BẮT BUỘC trích độc lập từ dòng "Quê quán / Place of origin:" trên CCCD mẹ, dù giống quê quán bố. Nếu chỉ có huyện và tỉnh thì không được gán tên huyện vào `xa`, nhưng vẫn phải trả field với tối thiểu `tinh`; không được bỏ field.
- ThongTinMe_NoiCuTru: ưu tiên giấy kết hôn > giấy chứng sinh > giấy khai sinh > CCCD

# ═══ E. DÂN TỘC CHA/MẸ (ThongTinBo_DanToc = CHA, ThongTinMe_DanToc = MẸ) ═══
- Thẻ CCCD/Căn cước gắn chip (mẫu mới) thường KHÔNG in dân tộc → PHẢI lấy dân tộc từ giấy tờ khác CÓ ghi, đối chiếu ĐÚNG NGƯỜI theo họ tên/số định danh. BẮT BUỘC điền dân tộc cho CẢ cha VÀ mẹ nếu bất kỳ giấy nào ghi — KỂ CẢ khi người đó ĐÃ CÓ CCCD (ĐỪNG vì cha/mẹ đã có CCCD mà bỏ qua dân tộc của họ).
- RIÊNG DÂN TỘC MẸ (ThongTinMe_DanToc), áp dụng DUY NHẤT thứ tự sau:
  + (1) GIẤY CHỨNG SINH: lấy dòng "Dân tộc: ..." trong KHỐI THÔNG TIN MẸ, nằm cùng cụm với "Họ, chữ đệm, tên khai sinh của mẹ", ngày sinh và số ĐDCN/hộ chiếu của mẹ. Đây là dân tộc MẸ, không phải dân tộc con. Có giá trị ở nguồn này thì PHẢI dùng và dừng xét nguồn thấp hơn.
  + (2) Nếu giấy chứng sinh không ghi/không đọc được dân tộc mẹ, lấy dòng "Dân tộc" trong khối "vợ"/"bên nữ" của GIẤY CHỨNG NHẬN KẾT HÔN. Đối chiếu đúng người mẹ theo họ tên hoặc số định danh.
  + (3) Chỉ khi hai nguồn trên đều không có, lấy dòng "Dân tộc" trong khối "người mẹ" của TỜ KHAI ĐĂNG KÝ KHAI SINH.
  + Khi đọc được một giá trị dân tộc mẹ không rỗng từ đúng khối, BẮT BUỘC trả ThongTinMe_DanToc; KHÔNG được bỏ field vì cách ghi ít gặp, vì chưa chuẩn hóa được tên dân tộc, hoặc vì CCCD của mẹ không in dân tộc.
  + Chỉ bỏ ThongTinMe_DanToc khi CẢ BA nguồn trên đều không ghi hoặc thực sự không đọc được giá trị.
- RIÊNG DÂN TỘC CHA (ThongTinBo_DanToc), ưu tiên bắt buộc hai nguồn chính sau:
  + (1) TỜ KHAI ĐĂNG KÝ KHAI SINH: lấy dòng "Dân tộc" trong KHỐI THÔNG TIN BỐ ĐẺ/CHA/NGƯỜI CHA. Không lấy dòng dân tộc của người được khai sinh hoặc của mẹ.
  + (2) Nếu tờ khai không có hoặc không ghi/không đọc được dân tộc cha, lấy dòng "Dân tộc" trong khối "chồng"/"bên nam" của GIẤY CHỨNG NHẬN KẾT HÔN. Đối chiếu đúng người cha theo họ tên hoặc số định danh.
  + Hễ hồ sơ có một trong hai giấy tờ trên, PHẢI chủ động soát đúng khối cha/chồng. Khi đọc được giá trị dân tộc cha không rỗng thì BẮT BUỘC trả ThongTinBo_DanToc; KHÔNG được bỏ field vì cha đã có CCCD, vì CCCD không in dân tộc, vì tên dân tộc ít gặp hoặc vì chưa chuẩn hóa được tên dân tộc.
  + Chỉ khi CẢ HAI nguồn chính trên đều không có, không ghi hoặc thực sự không đọc được giá trị thì mới xét dòng dân tộc trong khối cha của giấy chứng sinh/giấy khai sinh. Không nguồn nào ghi rõ mới được bỏ ThongTinBo_DanToc.
- TUYỆT ĐỐI không lấy dân tộc người này gán cho người khác (vd dân tộc con/mẹ KHÔNG gán cho cha).
- KHÔNG giấy tờ nào ghi rõ dân tộc của người đó → ĐỂ TRỐNG (không bịa, không mặc định "Kinh"). Nhưng nếu CÓ THÔNG TIN thì BẮT BUỘC ghi rõ dân tộc của CẢ cha và mẹ.
- CHUẨN HÓA tên dân tộc về đúng danh mục (sửa lỗi/biến thể OCR): Kinh, Mông, Thái, Dao, Giáy, Tày, Nùng, Mường, Hà Nhì, Lự, Lào, Khơ Mú, Hoa, Sán Chay, Sán Dìu, Cống, Mảng, La Hủ, Si La, Hmông... Ví dụ OCR "Giây"/"Záy" → "Giáy"; "Hmông"/"H'Mông"/"H Mông" → "Mông"; "Kinnh" → "Kinh"; "Trung"/"Trung Hoa" → "Hoa"; "C ho"/"K ho"/"Kho" → "Cơ Ho".
- **QUAN TRỌNG VỀ DÂN TỘC KHÔNG KHỚP**: Nếu dân tộc OCR đọc được KHÔNG KHỚP với bất kỳ tên chuẩn nào trong danh sách trên (ví dụ: "Cil", "Cill" và các tên dân tộc hiếm/không rõ), BẮT BUỘC phải TRẢ VỀ GIÁ TRỊ GỐC CHÍNH XÁC như OCR đọc được. TUYỆT ĐỐI KHÔNG tự ý suy luận hoặc đổi sang dân tộc khác (như "Kinh"). Ví dụ: OCR đọc "Cil" → trả "Cil" (KHÔNG đổi thành "Kinh" hay bất kỳ tên nào khác).

# ═══ F. TÁCH ĐỊA CHỈ (ThongTinBo_NoiCuTru, ThongTinMe_NoiCuTru, ThongTinBo_QueQuan, ThongTinMe_QueQuan — object {tinh,xa,diaChi}) ═══
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
- Tk_NguoiYeuCau_HoTen: họ tên ở dòng "Họ, chữ đệm, tên người yêu cầu" NGAY ĐẦU TỜ KHAI ĐĂNG KÝ KHAI SINH (cũng là người ký tên cuối tờ khai). TUYỆT ĐỐI KHÔNG lấy tên con/cha/mẹ ở các khối phía dưới, KHÔNG lấy người kê khai/chủ hộ trên CT01. Không có tờ khai đăng ký khai sinh → bỏ field.

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
