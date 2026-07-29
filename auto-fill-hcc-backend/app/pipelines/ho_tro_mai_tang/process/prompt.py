"""Procedure-specific compact prompt rules for "Hỗ trợ mai táng"."""

EXTRA_RULES = """Đầu vào gồm CCCD/CMND (1 hoặc 2 người) và CÓ THỂ kèm TỜ KHAI đề nghị hỗ trợ chi phí
mai táng (Mẫu số 04). Có tờ khai thì trả thêm nhóm ToKhai_ChuHo* (xem mục dưới).

NGUỒN DỮ LIỆU:
- Tự gộp mặt trước và mặt sau của cùng một CCCD thành cùng một người theo số định danh/MRZ/họ tên.
- Nếu upload chỉ có một CCCD hoặc chỉ đọc được một người: trả nhóm Person1_*; không tạo Person2_*.
- Nếu có hai CCCD khác nhau: trả Person1_* và Person2_*. Không cần phân loại người nộp/chủ hồ sơ trong LLM;
  Python sẽ so với thông tin đang có trên form để xác định.
- Mỗi nhóm Person* phải lấy trọn từ đúng một CCCD/CMND, không trộn dữ liệu giữa hai người.

TỜ KHAI ĐỀ NGHỊ HỖ TRỢ CHI PHÍ MAI TÁNG (Mẫu số 04) — nhóm ToKhai_ChuHo*:
- Nhận diện: tiêu đề "TỜ KHAI ĐỀ NGHỊ HỖ TRỢ CHI PHÍ MAI TÁNG", có "Mẫu số 04", chia 2 mục lớn
  "I. THÔNG TIN NGƯỜI CHẾT..." và "II. THÔNG TIN CƠ QUAN, TỔ CHỨC, HỘ GIA ĐÌNH, CÁ NHÂN ĐỨNG RA MAI TÁNG".
- CHỦ HỒ SƠ (người/hộ đứng ra mai táng) nằm ở MỤC II, phần 2 "Trường hợp hộ gia đình, cá nhân đứng ra
  mai táng": a) Họ và tên (Chủ hộ hoặc người đại diện) → ToKhai_ChuHoTen; Ngày/tháng/năm sinh →
  ToKhai_ChuHoNamSinh; Giấy CMND/CCCD số → ToKhai_ChuHoSoGiayTo; cấp ngày → ToKhai_ChuHoNgayCap;
  Nơi cấp → ToKhai_ChuHoNoiCap; Hộ khẩu thường trú/Nơi ở → ToKhai_ChuHoNoiCuTru (object 2 cấp).
- TUYỆT ĐỐI KHÔNG lấy ToKhai_ChuHo* từ MỤC I (đó là NGƯỜI CHẾT — không điền vào biểu mẫu này) hay từ
  mục II.1 (cơ quan, tổ chức). Nếu mục II.2 để trống thì bỏ trống toàn bộ ToKhai_ChuHo*.
- Không trích thông tin người chết (mục I) thành bất kỳ field nào.
- BẮT BUỘC cố đọc Person*_NgayCap cho từng CCCD đã nhận diện. Ngày cấp nằm ở mặt sau ngay sau/gần nhãn
  "Ngày, tháng, năm / Date, month, year". Không lấy ngày sinh, không lấy ngày hết hạn "Có giá trị đến",
  không suy từ MRZ. Chỉ bỏ trống nếu thật sự không có mặt sau hoặc OCR không có ngày cấp.
- BẮT BUỘC cố đọc Person*_NoiCap từ mặt sau CCCD. Nơi cấp nằm ngay sau/gần dòng
  "Ngày, tháng, năm / Date, month, year"; nếu OCR thấy "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH
  VỀ TRẬT TỰ XÃ HỘI" thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội". Nếu là thẻ CĂN CƯỚC mới (tiêu đề "CĂN CƯỚC"/"IDENTITY CARD", thường cấp từ 01/7/2024) ghi "BỘ CÔNG AN"/"MINISTRY OF PUBLIC SECURITY" thì trả "Bộ Công an"; KHÔNG mặc định "Cục Cảnh sát..." cho thẻ này.
- Với Person*_NoiCuTru, nếu OCR có xã/phường/thị trấn thì trả thêm key "xa"; "diaChi" chỉ giữ phần chi tiết
  nhỏ nhất như số nhà/khu/xóm/thôn/bản/tổ dân phố, không lặp xã/huyện/tỉnh.
  Ví dụ "Nơi thường trú: Khu 2, Hoàng Cương, Thanh Ba, Phú Thọ" thì trả
  {"tinh":"Phú Thọ","xa":"Hoàng Cương","diaChi":"Khu 2"} (BỎ huyện "Thanh Ba").
  ĐẾM TỪ CUỐI: cuối = tỉnh; phần NGAY TRƯỚC tỉnh nếu là CẤP HUYỆN (huyện/quận/thị xã/thành phố thuộc tỉnh)
  thì BỎ HẲN; phần trước đó = xã. Tên xã/phường vùng cao CÓ THỂ bắt đầu bằng "Bản"/"Nậm"/"Mường"/"Pa" —
  KHÔNG coi là chi tiết chỉ vì bắt đầu bằng "Bản", VỊ TRÍ (áp chót, trước cấp huyện/tỉnh) mới quyết định là
  xã. BẮT BUỘC điền xa, KHÔNG dồn xã + huyện vào diaChi.
- Quốc tịch chỉ trả nếu giấy tờ ghi rõ hoặc khác Việt Nam; Python sẽ mặc định Việt Nam.
- Không trả field UI/default như data[fullname], data[ownerFullname], data[isOwnerDossierCheck],
  số điện thoại, email, fax, ghi chú, hoặc bất kỳ trường biểu mẫu nào.
- Không suy đoán vai trò từ tên file như "chồng/vợ" hay thứ tự upload."""
