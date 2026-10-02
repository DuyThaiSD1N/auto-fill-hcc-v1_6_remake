"""Quy tắc compact prompt cho "[Bắc Ninh] Đăng ký đất đai, cấp GCN lần đầu" (Đơn Mẫu 15)."""

EXTRA_RULES = """Đầu vào chính là ĐƠN đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15) do công
dân tự khai, kèm CCCD người đề nghị. Có thể có thêm Giấy chứng nhận kết hôn, Mẫu 15a, phiếu thu tiền,
hợp đồng ủy quyền — nhưng CHỈ trích thông tin của người đề nghị và thửa đất.

NGUỒN & CÁCH LẤY:
- Cccd_* lấy từ CCCD người đề nghị (hoặc mục 1 tờ khai). Người đề nghị = NGƯỜI SỬ DỤNG ĐẤT đứng đơn,
  KHÔNG phải người được ủy quyền/nộp thay.
- BẮT BUỘC cố đọc Cccd_NgayCap/Cccd_NoiCap từ mặt sau CCCD.
- Các field thửa đất (Dat_*) lấy NGUYÊN VĂN từ mục 2 của tờ khai (địa chỉ, diện tích, sử dụng
  chung/riêng, mục đích, từ thời điểm, thời hạn, nguồn gốc). Mục trống thì bỏ field.
- Dat_DienTich giữ nguyên cách ghi (vd "152,0 m²"). Dat_MucDich vd "Đất ở". Dat_ThoiHan vd "Lâu dài".
- Dat_ThuaSo / Dat_ToBanDo lấy ở dòng "a) Thửa đất số: ...; 2.2. Tờ bản đồ số: ..." của ĐƠN, chỉ
  phần số (vd "68", "3"). Đơn để trống thì lấy ở Phiếu xác nhận kết quả đo đạc/trích đo/trích lục
  của cùng thửa đất. Dat_DienTich cũng vậy: đơn để trống thì lấy diện tích trên phiếu đo đạc.
- Ô CHỈ CÓ dấu chấm/dấu "…" hoặc chỉ còn đơn vị in sẵn (".... m²", "… tầng") là ô TRỐNG → bỏ field,
  KHÔNG trả "m²", "…", "....".
- Nha_* (mục 3 Nhà ở, công trình xây dựng) CHỈ trả khi người dân thật sự kê khai; mục 3 để trống thì
  bỏ hết Nha_*.
- Don_Email: hộp thư điện tử ở mục 1.d; trống thì bỏ.

- QUAN TRỌNG — NGOẠI LỆ quy tắc địa chỉ chung (quy tắc 5): Don_DiaChi và Dat_DiaChi PHẢI là CHUỖI
  (string) MỘT DÒNG, chép nguyên văn, GIỮ ĐỦ tổ dân phố/thôn + phường/xã + tỉnh. KHÔNG trả object,
  KHÔNG bỏ phường/xã.

- Dat_NguonGoc: lấy TOÀN BỘ nội dung mục "e) Nguồn gốc sử dụng đất(9)" từ sau "(9):" đến trước mục
  "g)", GỒM MỌI CÂU (nguồn gốc, phiếu thu, đồng chủ sử dụng, quá trình sử dụng ổn định, xây nhà năm
  2022...). TUYỆT ĐỐI KHÔNG rút gọn/cắt bớt — đây là 1 ô văn bản dài.
- Don_KemTheo1/2/3: lấy từ mục "5. Những giấy tờ nộp kèm theo(19)" — các dòng "(1) ...", "(2) ...",
  "(3) ..." NGUYÊN VĂN (vd "Mẫu số 15a...", "02 Phiếu thu tiền (Bản photo)", "Căn cước công dân (Bản
  sao)"). ĐÂY KHÔNG phải nơi gửi/họ tên/số CCCD.
- Don_KinhGui lấy sau "Kính gửi:"; Don_NoiKhai là địa danh ở cuối đơn (vd "Song Liễu").

KHÔNG trả field UI dạng "element_...", "nhanTaiNha...", "a) Họ và tên"; chỉ trả field nguồn trong
schema. Không bịa; tài liệu/mục không có thì bỏ field.

Ví dụ output ĐÚNG:
```json
{"fields":{"Cccd_HoTen":"NGUYỄN VĂN AN","Cccd_SoDinhDanh":"001090012345","Cccd_NgayCap":"10/01/2022","Cccd_NoiCap":"Cục Cảnh sát quản lý hành chính về trật tự xã hội","Don_KinhGui":"UBND phường Hòa Bình, tỉnh Bắc Ninh","Don_DiaChi":"Tổ dân phố Số 1, phường Hòa Bình, tỉnh Bắc Ninh","Don_DienThoai":"0900.000.111","Dat_ThuaSo":"125","Dat_ToBanDo":"7","Dat_DiaChi":"Tổ dân phố Số 1, phường Hòa Bình, tỉnh Bắc Ninh","Dat_DienTich":"150,0 m²","Dat_MucDich":"Đất ở","Dat_TuThoiDiem":"01/01/2005","Dat_ThoiHan":"Lâu dài","Dat_NguonGoc":"Giao đất ở"}}
```"""
