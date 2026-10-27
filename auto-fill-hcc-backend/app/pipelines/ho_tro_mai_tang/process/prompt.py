"""Quy tắc trích xuất cho thủ tục hỗ trợ mai táng: người chết là chủ hồ sơ trên cổng."""

EXTRA_RULES = """MỤC TIÊU:
Output CHỈ có tối đa BA nhóm người:
1. NguoiMat_* = NGƯỜI CHẾT được tổ chức mai táng. Đây là CHỦ HỒ SƠ trên cổng.
2. ChuHoSo_* = cá nhân/hộ gia đình/thân nhân ĐỨNG RA MAI TÁNG (chỉ là ứng viên người nộp, KHÔNG phải
   chủ hồ sơ trên cổng dù tên nhóm là ChuHoSo).
3. NguoiNop_* = người thực sự nộp hồ sơ, chỉ khi tài liệu của người này đã khớp mỏ neo UI.
Không tạo Person1_*, Person2_*, ToKhai_* hoặc nhóm người thứ tư.

NGƯỜI CHẾT (NguoiMat_*):
- Nguồn: mục I "Thông tin người chết" (Mẫu số 04) hoặc mục 2 "Thông tin người chết được tổ chức mai táng"
  (Mẫu số 02, Mẫu số 03) của tờ khai; khối chính "Họ, chữ đệm, tên" trên Trích lục khai tử/Giấy báo tử.
- Họ tên, ngày sinh, giới tính, số định danh, ngày cấp, nơi cấp của người chết ưu tiên Trích lục khai
  tử/giấy tờ định danh của chính người chết; ngày cấp/nơi cấp in ở mục người chết của tờ khai cũng là
  của người chết.
- NguoiMat_NoiCuTru lấy dòng "Nơi cư trú"/"Hộ khẩu thường trú" của người chết trên tờ khai, tuyệt đối
  không lấy "Nơi chết" hay "Nơi đăng ký khai tử".
- Không đưa người khai, người đề nghị, người đi khai tử, người đứng ra mai táng vào NguoiMat_*; không
  đưa người chết vào ChuHoSo_* hoặc NguoiNop_*.

NGƯỜI ĐỨNG RA MAI TÁNG (ChuHoSo_*):
- Nhận diện tờ khai bằng tiêu đề "TỜ KHAI ĐỀ NGHỊ HỖ TRỢ CHI PHÍ MAI TÁNG" kèm "Mẫu số 04", "Mẫu số 02"
  hoặc "Mẫu số 03".
- Mẫu số 04: ChuHoSo_* BẮT BUỘC lấy tại mục II, phần 2 "Trường hợp hộ gia đình, cá nhân đứng ra mai táng":
  + Họ và tên (Chủ hộ hoặc người đại diện) -> ChuHoSo_HoTen.
  + Ngày/tháng/năm sinh -> ChuHoSo_NgaySinh.
  + Giấy CMND/CCCD số -> ChuHoSo_SoDinhDanh.
  + Cấp ngày, Nơi cấp -> ChuHoSo_NgayCap, ChuHoSo_NoiCap.
  + Hộ khẩu thường trú/Nơi ở -> ChuHoSo_NoiCuTru.
  + Số điện thoại -> ChuHoSo_DienThoai.
- Mẫu số 02/03: mục 3.1 "Trường hợp cá nhân, thân nhân đứng ra tổ chức mai táng" là nguồn chính của
  ChuHoSo_*; mục 1 "Thông tin người đề nghị (người khai)" là cùng người, chỉ bổ sung khi mục 3.1 trống.
- Không lấy cơ quan/tổ chức (mục II.1 Mẫu số 04, mục 3.2 Mẫu số 02/03), cán bộ tiếp nhận, người ký xác
  nhận hoặc chủ tịch UBND.
- Phải trả mọi field đọc chắc chắn của NguoiMat_* và ChuHoSo_*, kể cả khi không xác định được người nộp.
- Khi có <owner_ocr>, đây là phạm vi bắt buộc cho ChuHoSo_*; không lấy giá trị nào từ khối người chết để
  thay thế hoặc bổ sung ChuHoSo_*.

NGƯỜI NỘP HỒ SƠ:
- Python đối chiếu tên/số định danh UI với OCR và chèn <requester_context>.
- result="owner_match": người nộp chính là người đứng ra mai táng. CHỈ trả ChuHoSo_*, không lặp cùng
  người vào NguoiNop_*.
- result="document_match": chỉ tài liệu nằm trong <matched_requester_ocr> mới được dùng cho NguoiNop_*.
- result="no_document_match" hoặc "missing_ui_anchor": BẮT BUỘC bỏ trống toàn bộ NguoiNop_*;
  vẫn phải trích NguoiMat_* và ChuHoSo_* bình thường.
- Context chỉ khoanh vùng tài liệu; mọi giá trị vẫn phải có bằng chứng trong OCR, không sao chép dữ liệu từ UI.
- Không chọn người nộp theo thứ tự upload, tên file, chữ ký, quan hệ con/vợ/chồng hoặc suy đoán.

HỢP NHẤT GIẤY TỜ CÙNG NGƯỜI:
- Nếu có CCCD/CMND riêng khớp chính xác số định danh hoặc họ tên của ChuHoSo/NguoiMat, hợp nhất vào đúng nhóm đó.
- Họ tên, ngày sinh, giới tính, số định danh, ngày cấp, nơi cấp và quốc tịch ưu tiên CCCD đúng người.
- Nơi cư trú và số điện thoại người đứng ra mai táng ưu tiên tờ khai; CCCD chỉ bổ sung khi tờ khai trống.
- Mỗi nhóm chỉ lấy từ đúng một người; không trộn dữ liệu người chết, người đứng ra mai táng, người nộp với nhau.

QUY TẮC FIELD:
- Ngày sinh/ngày cấp chuẩn hóa dd/mm/yyyy khi OCR ghi rõ; không đảo ngày/tháng hoặc sửa ngày mơ hồ.
- Số định danh chỉ giữ chữ số.
- Giới tính chỉ "Nam"/"Nữ" khi tài liệu ghi rõ; không suy từ tên hay quan hệ.
- Nơi cấp phải đọc từ đúng giấy tờ. CCCD cũ có dòng "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH
  VỀ TRẬT TỰ XÃ HỘI" thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; không lấy chữ
  "BỘ CÔNG AN" trên logo/dấu. Chỉ thẻ CĂN CƯỚC mẫu mới ghi cơ quan Bộ Công an mới trả "Bộ Công an".
- Địa chỉ trả object {quocGia,tinh,xa,chiTietDuoiXa}; bỏ cấp huyện/quận; chiTietDuoiXa chỉ giữ số nhà/tổ/thôn/xóm/bản,
  không lặp xã/huyện/tỉnh.
- Không trả field UI như data[fullname], data[ownerFullname], data[isOwnerDossierCheck], email, fax, ghi chú.
- Không tạo field không có bằng chứng OCR."""
