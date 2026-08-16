"""Quy tắc trích xuất hai vai trò cho mai táng người hưởng hưu trí xã hội."""

EXTRA_RULES = """MỤC TIÊU:
Output CHỈ có tối đa HAI chủ thể nghiệp vụ:
1. ChuHoSo_* = cá nhân/hộ gia đình đứng ra mai táng tại mục II.2 Mẫu số 04.
2. NguoiNop_* = người thực sự nộp hồ sơ, chỉ khi tài liệu của người này đã khớp mỏ neo UI.
Không tạo Person1_*, Person2_*, ToKhai_* hoặc nhóm người thứ ba. Người chết không thuộc hai vai trò này.

CHỦ HỒ SƠ TỪ MẪU SỐ 04:
- Nhận diện tờ khai bằng tiêu đề "TỜ KHAI ĐỀ NGHỊ HỖ TRỢ CHI PHÍ MAI TÁNG" và "Mẫu số 04".
- ChuHoSo_* BẮT BUỘC lấy tại mục II, phần 2 "Trường hợp hộ gia đình, cá nhân đứng ra mai táng":
  + Họ và tên (Chủ hộ hoặc người đại diện) -> ChuHoSo_HoTen.
  + Ngày/tháng/năm sinh -> ChuHoSo_NgaySinh.
  + Giấy CMND/CCCD số -> ChuHoSo_SoDinhDanh.
  + Cấp ngày, Nơi cấp -> ChuHoSo_NgayCap, ChuHoSo_NoiCap.
  + Hộ khẩu thường trú/Nơi ở -> ChuHoSo_NoiCuTru.
  + Số điện thoại -> ChuHoSo_DienThoai.
- TUYỆT ĐỐI KHÔNG lấy người chết ở mục I làm ChuHoSo hoặc NguoiNop.
- Không lấy cơ quan/tổ chức tại mục II.1, cán bộ tiếp nhận, người ký xác nhận hoặc chủ tịch UBND.
- Phải trả mọi field chủ hồ sơ đọc chắc chắn, kể cả khi không xác định được người nộp.
- Khi có <owner_ocr>, đây là phạm vi ưu tiên bắt buộc cho ChuHoSo_*; dù toàn văn OCR phía user còn chứa
  người chết, không được lấy bất kỳ giá trị nào từ khối người chết để thay thế hoặc bổ sung chủ hồ sơ.

TRÍCH LỤC KHAI TỬ CHỈ LÀ NGUỒN BỔ SUNG:
- Trên Trích lục khai tử, khối chính "Họ, chữ đệm, tên" là NGƯỜI CHẾT: tuyệt đối không đưa vào hai vai trò.
- Chỉ khối bắt đầu bằng "Họ, chữ đệm, tên người đi khai tử" và dòng giấy tờ ngay sau đó được phép bổ sung
  dữ liệu cho đúng người đi khai tử khi khớp tên/số định danh với chủ hồ sơ hoặc người nộp.
- Không lấy ngày sinh, giới tính, quốc tịch, nơi chết hoặc CCCD của người chết để bổ sung cho người đi khai tử.

NGƯỜI NỘP HỒ SƠ:
- Python đối chiếu tên/số định danh UI với OCR và chèn <requester_context>.
- result="owner_match": người nộp chính là chủ hồ sơ. CHỈ trả ChuHoSo_*, không lặp cùng người vào NguoiNop_*.
- result="document_match": chỉ tài liệu nằm trong <matched_requester_ocr> mới được dùng cho NguoiNop_*.
- result="no_document_match" hoặc "missing_ui_anchor": BẮT BUỘC bỏ trống toàn bộ NguoiNop_*;
  vẫn phải trích ChuHoSo_* bình thường.
- Context chỉ khoanh vùng tài liệu; mọi giá trị vẫn phải có bằng chứng trong OCR, không sao chép dữ liệu từ UI.
- Không chọn người nộp theo thứ tự upload, tên file, chữ ký hoặc quan hệ con trai/con gái/vợ/chồng.

HỢP NHẤT GIẤY TỜ CÙNG NGƯỜI:
- Nếu có CCCD/CMND riêng hoặc khối "người đi khai tử" khớp chính xác số định danh/họ tên của ChuHoSo,
  chỉ dùng nó để bổ sung đúng các field của cùng người.
- Họ tên, ngày sinh, giới tính, số định danh, ngày cấp, nơi cấp và quốc tịch ưu tiên giấy tờ định danh đúng người.
- Nơi cư trú và số điện thoại chủ hồ sơ ưu tiên mục II.2 Mẫu số 04; giấy tờ khác chỉ bổ sung khi tờ khai trống.
- Mỗi nhóm chỉ lấy từ đúng một người; không trộn dữ liệu người chết hoặc người nộp vào chủ hồ sơ.

QUY TẮC FIELD:
- Ngày sinh/ngày cấp chuẩn hóa dd/mm/yyyy khi OCR ghi rõ; không đảo ngày/tháng hoặc sửa ngày mơ hồ.
- Số định danh chỉ giữ chữ số.
- Giới tính chỉ "Nam"/"Nữ" khi tài liệu của chính người đó ghi rõ; không suy từ tên hay quan hệ
  như "Con trai", "Con gái".
- Nơi cấp phải đọc từ đúng giấy tờ. CCCD cũ có dòng "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH
  VỀ TRẬT TỰ XÃ HỘI" thì trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; không lấy chữ
  "BỘ CÔNG AN" trên logo/dấu. Chỉ thẻ CĂN CƯỚC mẫu mới ghi cơ quan Bộ Công an mới trả "Bộ Công an".
- Địa chỉ trả object {quocGia,tinh,xa,diaChi}; bỏ cấp huyện/quận; diaChi chỉ giữ số nhà/tổ/thôn/xóm/bản,
  không lặp xã/huyện/tỉnh.
- Không trả field UI như data[fullname], data[ownerFullname], data[isOwnerDossierCheck], email, fax, ghi chú.
- Không tạo field không có bằng chứng OCR."""
