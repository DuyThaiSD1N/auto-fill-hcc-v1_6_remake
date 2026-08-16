"""Procedure-specific compact prompt rules for social pension adjustment."""

EXTRA_RULES = """MỤC TIÊU:
Trích dữ liệu cho thủ tục "Thực hiện, điều chỉnh, thôi hưởng trợ cấp hưu trí xã hội".
Output CHỈ có tối đa HAI chủ thể nghiệp vụ:
1. ChuHoSo_* = người đề nghị/người đang hưởng trợ cấp tại mục I Mẫu số 01.
2. NguoiNop_* = người thực sự nộp hồ sơ, chỉ khi khớp mỏ neo người nộp do UI cung cấp.
Không tạo Person1_*, Person2_*, VanBan_*, NguoiDaiDien_* hoặc một nhóm người thứ ba.

MẪU HỢP LỆ:
- Chỉ dùng "Mẫu số 01" có nội dung đề nghị hưởng, nhận tại nơi cư trú mới, thay đổi thông tin
  hoặc thôi hưởng trợ cấp hưu trí xã hội.
- Nếu OCR ghi rõ "Mẫu số 02", không dùng tài liệu đó làm nguồn cho hai chủ thể.

XÁC ĐỊNH CHỦ HỒ SƠ:
- Khi có Mẫu số 01, ChuHoSo_* BẮT BUỘC là người ở mục I "Thông tin người đề nghị trợ cấp
  hưu trí xã hội"/"Thông tin người đang hưởng trợ cấp hưu trí xã hội".
- Mục II "Thông tin người giám hộ, người được ủy quyền" KHÔNG BAO GIỜ là ChuHoSo_*.
- Người tiếp nhận, người ký xác nhận, cán bộ, người làm chứng hoặc tên chỉ xuất hiện ở cuối
  văn bản không phải chủ hồ sơ.
- Phải trả mọi field đọc chắc chắn của chủ hồ sơ, kể cả khi không xác định được người nộp.

XÁC ĐỊNH NGƯỜI NỘP HỒ SƠ:
- Python đối chiếu mỏ neo UI với OCR trước và chèn <requester_context>:
  + result="no_document_match" hoặc "missing_ui_anchor": BẮT BUỘC không trả NguoiNop_*.
  + result="document_match": chỉ tài liệu OCR được đánh số trong context mới có thể chứa người nộp.
- Context chỉ nêu KẾT QUẢ KHỚP và số thứ tự tài liệu, không phải nguồn dữ liệu. Mọi field NguoiNop_*
  vẫn phải đọc từ đúng khối người trong OCR; không tạo field chỉ vì context báo có tài liệu khớp.
- Khi context có <matched_requester_ocr section="II">, Python đã xác nhận mục II này khớp tên + CCCD
  người nộp trên UI: BẮT BUỘC trả tất cả NguoiNop_* đọc được trong block, không được bỏ cả nhóm.
- Ưu tiên kiểm tra người tại mục II Mẫu số 01. Nếu người này khớp UI thì hợp nhất vào NguoiNop_*.
  Nếu không khớp thì bỏ qua mục II, không trả người đó dưới tên field khác.
- Một CCCD riêng khác chủ hồ sơ chỉ được đưa vào NguoiNop_* khi nó khớp mỏ neo UI.
- Nếu mỏ neo UI khớp chính ChuHoSo_* thì đây là trường hợp tự nộp: CHỈ trả ChuHoSo_*,
  KHÔNG lặp lại cùng người vào NguoiNop_*.
- Nếu context báo không tài liệu nào khớp UI, hoặc UI không có mỏ neo, bỏ trống toàn bộ NguoiNop_*.
  Tuyệt đối không chọn theo thứ tự upload, tên file, chữ ký, quan hệ vợ/chồng/con/cháu hay suy đoán.

MA TRẬN CÁC TRƯỜNG HỢP:
A. Mẫu 01 có mục I; UI khớp mục I:
   - Trả ChuHoSo_* đầy đủ; không trả NguoiNop_* (tự nộp).
B. Mẫu 01 có mục I và mục II; UI khớp mục II:
   - Trả ChuHoSo_* từ mục I; trả NguoiNop_* từ mục II; tối đa đúng hai chủ thể.
C. Mẫu 01 có mục I và mục II; UI không khớp mục II cũng không khớp mục I:
   - Vẫn trả ChuHoSo_*; không trả NguoiNop_*.
D. Mẫu 01 có mục I, không có mục II; có CCCD khác chủ hồ sơ khớp UI:
   - Trả ChuHoSo_* và NguoiNop_* từ CCCD khớp.
E. Chỉ có một CCCD, không có Mẫu 01:
   - Nếu CCCD khớp UI, coi là tự nộp và trả vào ChuHoSo_*; không nhân đôi NguoiNop_*.
F. Có nhiều CCCD nhưng không có Mẫu 01:
   - Có thể xác định NguoiNop_* bằng mỏ neo UI, nhưng không được đoán CCCD còn lại là chủ hồ sơ.
   - Chỉ trả ChuHoSo_* nếu tài liệu khác ghi rõ người đề nghị/người đang hưởng.

HỢP NHẤT CÙNG MỘT CHỦ THỂ:
- Trước hết ghép Mẫu số 01 với CCCD theo số định danh chính xác.
- Riêng CHỦ HỒ SƠ: nếu số định danh hoặc ngày sinh giữa mục I và CCCD bị lệch, nhưng trong toàn bộ
  hồ sơ chỉ có đúng MỘT CCCD có họ tên IN TRÊN MẶT TRƯỚC khớp chính xác họ tên người mục I sau khi
  chuẩn hóa hoa/thường và dấu, vẫn xác định đó là CCCD của ChuHoSo. Khi đó BẮT BUỘC lấy HoTen,
  NgaySinh, SoDinhDanh, GioiTinh, QuocTich, NgayCap và NoiCap từ CCCD; Nơi cư trú và điện thoại vẫn
  theo quy tắc ưu tiên mục I bên dưới. Không dùng tên MRZ sai OCR làm mỏ neo thay cho tên in trên thẻ.
- Nếu có từ hai CCCD trở lên cùng khớp tên chủ hồ sơ, hoặc tên chỉ gần giống/không khớp chính xác,
  không ghép theo tên và không tự chọn một thẻ. Không ghép hai người chỉ vì địa chỉ hoặc quan hệ giống nhau.
- Họ tên, ngày sinh, giới tính, số định danh, ngày cấp, nơi cấp, quốc tịch:
  ưu tiên CCCD khớp chủ thể vì đây là nguồn định danh chính thức.
- Nơi cư trú/địa chỉ liên hệ và số điện thoại:
  + ChuHoSo_*: nếu mục I có "Nơi cư trú" hoặc "Địa chỉ liên lạc" thì BẮT BUỘC dùng địa chỉ mục I,
    KHÔNG dùng địa chỉ CCCD và KHÔNG trộn từng thành phần với CCCD. CCCD chỉ bổ sung khi cả hai dòng
    địa chỉ tại mục I đều trống.
  + NguoiNop_*: ưu tiên đúng mục II. CCCD người nộp chỉ bổ sung khi mục II thiếu field tương ứng.
- Mỗi thông tin chỉ xuất hiện một lần dưới đúng nhóm chủ thể sau khi hợp nhất.
- Field của NguoiNop_* chỉ được lấy trong đúng mục II chứa người nộp hoặc CCCD riêng khớp người nộp.
  Dù mục I/CCCD chủ hồ sơ có giới tính, nơi cấp hoặc quốc tịch, KHÔNG được sao các field đó sang NguoiNop_*.
- Field của ChuHoSo_* chỉ được lấy trong đúng mục I hoặc CCCD khớp chủ hồ sơ; không lấy từ mục II.

QUY TẮC TỪNG FIELD:
- HoTen: giữ đúng chính tả nguồn ưu tiên; không tự sửa một người thành người khác.
- NgaySinh/NgayCap: chuẩn hóa dd/mm/yyyy khi OCR ghi rõ ngày. Chấp nhận nguồn viết d/m/yyyy và
  thêm số 0 khi chuẩn hóa. Không đảo ngày/tháng, không biến chuỗi mơ hồ hoặc sai tháng thành ngày hợp lệ.
- GioiTinh: chỉ "Nam"/"Nữ" khi tài liệu ghi rõ. Không suy từ họ tên, quan hệ hay giới tính thường gặp.
- SoDinhDanh: chỉ giữ chữ số của CMND/CCCD/số định danh; có thể dùng MRZ để xác nhận.
- NoiCap: chỉ lấy câu cơ quan cấp hiện diện trong OCR. Không có nơi cấp thì bỏ trống, kể cả khi có ngày cấp.
  Phân biệt theo LOẠI THẺ và DÒNG CƠ QUAN CẤP, không chọn chữ trên con dấu/logo:
  + Thẻ có tiêu đề "CĂN CƯỚC CÔNG DÂN" và mặt sau có dòng "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ
    HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI" → BẮT BUỘC trả "Cục Cảnh sát quản lý hành chính về trật tự xã hội".
    Nếu cùng ảnh có chữ "BỘ CÔNG AN" ở con dấu/logo thì phải bỏ qua chữ đó, không được trả Bộ Công an.
  + Chỉ thẻ "CĂN CƯỚC" mẫu mới, không có chữ "CÔNG DÂN" trong tiêu đề và ghi cơ quan Bộ Công an,
    mới trả "Bộ Công an".
- DienThoai: chỉ lấy số điện thoại nằm trong đúng mục của chủ thể; không dùng số người kia.
- QuocTich: chỉ trả khi giấy tờ ghi rõ.
- NoiCuTru trả object {quocGia,tinh,xa,diaChi}; xa chỉ là tên xã/phường/thị trấn, không chứa tiền tố;
  diaChi chỉ là số nhà/khu/xóm/thôn/bản/tổ, không lặp xã/huyện/tỉnh.
  Với câu theo dạng "chi tiết, xã/phường ..., tỉnh ...": phần sau nhãn xã/phường → xa; phần sau nhãn
  tỉnh → tinh; phần đứng trước xã/phường → diaChi. Không thay xã/tỉnh này bằng nơi thường trú trên CCCD.
  Khi địa chỉ có cấp huyện, bỏ cấp huyện: cuối là tỉnh; ngay trước tỉnh nếu là huyện/quận/thị xã/
  thành phố thuộc tỉnh thì bỏ; phần trước nữa là xã; phần còn lại là diaChi.

CẤM SUY ĐOÁN:
- Không tạo field không có bằng chứng trong OCR.
- Không mặc định giới tính hoặc nơi cấp.
- Không dùng dữ liệu của chủ hồ sơ để lấp field người nộp, và ngược lại.
- Không trả field UI như data[fullname], data[ownerFullname], data[isOwnerDossierCheck], email, fax, ghi chú."""
