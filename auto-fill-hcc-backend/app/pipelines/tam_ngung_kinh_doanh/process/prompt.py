"""Quy tắc đọc hồ sơ tạm ngừng kinh doanh hộ kinh doanh."""

EXTRA_RULES = """
Bạn đang trích xuất hồ sơ "Tạm ngừng kinh doanh hộ kinh doanh".

PHÂN BIỆT NGUỒN:
- Giấy đề nghị đăng ký tạm ngừng kinh doanh (Mẫu số 3) là thành phần hồ sơ CHÍNH: tên/mã HKD, thời
  gian tạm ngừng ("kể từ ngày ... đến hết ngày ..."), lý do tạm ngừng (nếu có), và người ký ở cuối
  giấy (chủ hộ tự ký hoặc người được ủy quyền — dòng "Tôi là (ghi họ, tên bằng chữ in hoa)").
- Giấy chứng nhận đăng ký hộ kinh doanh (GCN ĐKHKD) là nguồn trạng thái hiện tại: tên, mã HKD, chủ
  hộ, nơi ở hiện tại và thông tin liên hệ.
- CCCD/căn cước vật lý là nguồn nhân thân CHUẨN NHẤT (cổng đối chiếu CSDLQG về dân cư từ CCCD, các
  ô họ tên/ngày sinh/giới tính/số định danh trên cổng chỉ readonly theo CCCD) — không tự kết luận
  mọi CCCD là người nộp, chỉ dùng để bù/kiểm chứng nhân thân đã xác định qua Giấy đề nghị.

QUY TẮC BẮT BUỘC:
1. HoKinhDoanh_MaSo:
   ⛔ ANTI-PATTERN — SAI TUYỆT ĐỐI:
     Số định danh cá nhân / CCCD / CMND (xuất hiện cạnh nhãn "Số/No", "Số định danh",
     "Số CMND" trên thẻ căn cước hoặc trong tờ khai cá nhân) KHÔNG BAO GIỜ là mã số
     hộ kinh doanh — dù số đó đứng ở đâu trong hồ sơ.
     Nếu hồ sơ KHÔNG có tài liệu kinh doanh ghi nhãn "Mã số hộ kinh doanh" / "MST" / "Số đăng ký"
     → HoKinhDoanh_MaSo = "" (TRỐNG hoàn toàn, không điền bất cứ con số nào).
   ✅ Nguồn HỢP LỆ DUY NHẤT:
     * Giấy đề nghị đăng ký tạm ngừng kinh doanh hoặc GCN ĐKHKD có NHÃN RÕ "Mã số hộ kinh doanh" / "MST".
     * Giấy đề nghị đăng ký hộ kinh doanh nếu có in mã số.
   Bỏ khoảng trắng/dấu chấm/dấu gạch ngang khi lấy mã.
2. HienTai_Ten: giữ đầy đủ tên hiện tại. Không tự thêm/bỏ tiền tố "HỘ KINH DOANH".
3. TamNgung_TuNgay/TamNgung_DenNgay: chỉ lấy từ dòng "Thời gian tạm ngừng kinh doanh: kể từ ngày
   dd/mm/yyyy đến hết ngày dd/mm/yyyy" trên Giấy đề nghị. TamNgung_TuNgay = mốc sau "kể
   từ ngày", TamNgung_DenNgay = mốc sau "đến hết ngày". Không suy đoán nếu chỉ có một mốc thời gian;
   thời hạn tối đa 1 năm theo quy định nhưng KHÔNG tự tính DenNgay khi giấy không ghi rõ.
4. TamNgung_LyDo: một câu ngắn phù hợp để nhập form nếu Giấy đề nghị có ghi lý do; không bịa khi trống.
5. ChuHo lấy mục thông tin chủ hộ trên GCN. Với địa chỉ, form hỏi nơi ở hiện tại nên ưu tiên dòng
   "Nơi ở hiện tại", không lấy dòng "Nơi thường trú" nếu hai dòng khác nhau.
6. NguoiNop chỉ lấy người ký ở cuối Giấy đề nghị (dòng "Tôi là ... (ghi họ, tên bằng chữ in hoa)" —
   có thể là "CHỦ HỘ KINH DOANH" tự ký hoặc người được ủy quyền có căn cứ). Có thể bổ sung
   nhân thân còn thiếu từ ChuHo/CCCD khi khớp đồng thời họ tên hoặc số định danh.
   - ĐỊA CHỈ NguoiNop: Sau khi xác định người nộp (qua họ tên hoặc số định danh), TÌM trong Cccd_DanhSach
     xem có thẻ CCCD nào khớp với người đó không. Nếu có → BẮT BUỘC lấy diaChi từ "Nơi thường trú"
     trên thẻ CCCD đó điền vào NguoiNop.diaChi.
   - KHÔNG lấy địa chỉ từ Quê quán, từ GCN hay từ phần chủ hộ cho NguoiNop khi đã có CCCD khớp.
7. Cccd_DanhSach là field BẮT BUỘC khi hồ sơ có thẻ căn cước vật lý. Với MỖI file/khối OCR có
   "CĂN CƯỚC CÔNG DÂN" hoặc "Citizen Identity Card", phải trả đúng một object gồm tối thiểu
   hoTen, soDinhDanh và diaChi đọc từ "Nơi thường trú/Place of residence". Không được bỏ qua
   thẻ chỉ vì người trên thẻ khác người ký Giấy đề nghị.
   ⚠️ ĐỊA CHỈ TỪ CCCD - QUY TẮC BẮT BUỘC:
   - PHẢI lấy từ "Nơi thường trú / Place of residence" trên CCCD
   - TUYỆT ĐỐI KHÔNG lấy từ "Quê quán / Place of origin"
8. 📄 GIẤY ỦY QUYỀN — NGUỒN NHÂN THÂN CỦA NGƯỜI NỘP THAY:
  + Nhận diện qua tiêu đề "GIẤY ỦY QUYỀN"/"VĂN BẢN ỦY QUYỀN" và hai mục "Bên ủy quyền" / "Bên được ủy quyền".
  + "Bên ủy quyền" (người giao việc, thường là chủ hộ) → UyQuyen_NguoiUyQuyen_HoTen, UyQuyen_NguoiUyQuyen_SoDinhDanh.
  + "Bên được ủy quyền" (NGƯỜI ĐI NỘP HỒ SƠ THAY) → UyQuyen_NguoiDuocUyQuyen_HoTen, _SoDinhDanh,
    _GioiTinh, _NgaySinh, _DienThoai, _DiaChi. Trả UyQuyen_CoGiayUyQuyen = true.
  + Người nộp thay RẤT HAY chỉ xuất hiện trong giấy ủy quyền, hồ sơ KHÔNG kèm CCCD của họ.
    Khi đó VẪN PHẢI điền đủ nhóm UyQuyen_NguoiDuocUyQuyen_* từ chính giấy ủy quyền.
  + Nếu hồ sơ CÓ CCCD của bên được ủy quyền: ưu tiên nhân thân + "Nơi thường trú" trên THẺ;
    giấy ủy quyền chỉ bù các field thẻ không có (vd số điện thoại).
  + ⛔ KHÔNG đưa người chỉ có trong giấy ủy quyền vào Cccd_DanhSach — danh sách đó CHỈ dành cho thẻ
    căn cước vật lý. Nhân thân của họ đi qua nhóm UyQuyen_* .
  + UyQuyen_NguoiDuocUyQuyen_DiaChi tách chuẩn {quocGia,tinh,xa,diaChi} và BỎ cấp huyện.
  + KHÔNG suy ai đang nộp hồ sơ từ giấy ủy quyền — hệ thống tự đối chiếu nhân thân này với tài khoản
    đăng nhập trên cổng (khớp số định danh hoặc họ tên) y như cách đối chiếu CCCD.
9. Địa chỉ object luôn là {quocGia,tinh,xa,diaChi}; diaChi không lặp tỉnh/xã. Ngày theo dd/mm/yyyy.

Không trả tên field UI ctl00$C$...; chỉ trả field compact trong schema.
"""
