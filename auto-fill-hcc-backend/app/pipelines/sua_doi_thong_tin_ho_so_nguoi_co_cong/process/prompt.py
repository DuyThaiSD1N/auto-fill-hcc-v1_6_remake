"""Prompt rules đặc thù cho "Sửa đổi, bổ sung thông tin cá nhân trong hồ sơ người có công" (Form.io)."""

EXTRA_RULES = """Thủ tục: Sửa đổi, bổ sung thông tin cá nhân trong hồ sơ người có công. Đầu vào gồm:
CCCD của người khai đơn, Đơn đề nghị theo Mẫu số 26 (Phụ lục I Nghị định 131/2021/NĐ-CP), Bản khai thân
nhân, và có thể có: Giấy khai sinh, Trích lục khai tử của liệt sĩ, Bằng Tổ quốc ghi công, Công văn/Tờ
trình của Sở Nội vụ.

CÓ THỂ CÓ 2 NGƯỜI (KHÔNG lẫn với người có công):
- NGƯỜI KHAI ĐƠN (NguoiKhai_*) = chủ hồ sơ = người đứng đơn đề nghị sửa hồ sơ, ký tên "Người khai". Đây là
  đối tượng chính — trích toàn bộ nhân thân (họ tên/ngày sinh/giới tính/số định danh/ngày-nơi cấp/thường
  trú/quê quán/điện thoại) của NGƯỜI NÀY từ Đơn Mẫu 26 / Bản khai / CCCD của họ.
- NGƯỜI NỘP HỒ SƠ (NguoiNop_*) = người đứng nộp trên cổng. Khi NỘP THAY thì KHÁC người khai, thông tin lấy
  từ CCCD của người nộp. Xem khối <nguoi_nop_context> ở cuối (nếu có) để biết CCCD nào là của người nộp và
  trích NguoiNop_* từ đó. TUYỆT ĐỐI KHÔNG lẫn 2 người. Nếu KHÔNG có <nguoi_nop_context> hoặc không có CCCD
  người nộp riêng → chỉ trích NguoiKhai_*, bỏ trống NguoiNop_*.
- NGƯỜI CÓ CÔNG (liệt sĩ/thương binh — người được SỬA hồ sơ) THƯỜNG ĐÃ MẤT, chỉ nêu TÊN ở nội dung đơn.
  TUYỆT ĐỐI KHÔNG lấy họ tên/ngày sinh/số định danh của người có công vào NguoiKhai_* hay NguoiNop_*. Tên
  người có công chỉ dùng cho Don_TenHoSoNCC.

NGUỒN DỮ LIỆU (NguoiKhai_*):
- Họ tên/ngày sinh/giới tính/số định danh/ngày cấp: ưu tiên CCCD; Đơn Mẫu 26 / Bản khai bổ sung.
- Nơi cấp: CCCD gắn chip không in nhãn "Nơi cấp" riêng → lấy ở Đơn/Bản khai. Chuẩn hóa tên cơ quan.
- NguoiKhai_ThuongTru (nơi ở hiện tại) và NguoiKhai_QueQuan (nơi gốc) là HAI địa chỉ KHÁC nhau — đừng
  gán trùng. Nơi thường trú ưu tiên Đơn Mẫu 26/Bản khai (địa giới MỚI sau sáp nhập); quê quán giữ tên
  địa danh gốc theo CCCD/giấy tờ. Tách object {tinh,xa,diaChi}; diaChi CHỈ chi tiết (số nhà/đường/tổ/
  thôn), KHÔNG kèm tên phường/xã/huyện/tỉnh.

NỘI DUNG ĐƠN (về việc sửa hồ sơ người có công):
- Don_KinhGui: nơi nhận (thường Sở Nội vụ Tỉnh/TP) — chép nguyên văn.
- Don_TenHoSoNCC: tên hồ sơ người có công cần sửa, ghép "Hồ sơ <loại NCC> <họ tên người có công>"
  (vd "Hồ sơ liệt sĩ Huỳnh Kim Khoa").
- Don_ThuocDienNCC: người khai thuộc diện / quan hệ với người có công (vd "Con đẻ của liệt sĩ …").
- Don_ThongTinHienTai (thông tin ĐANG GHI, có thể sai) và Don_ThongTinDeNghiSua (thông tin ĐÚNG đề nghị
  sửa). Nội dung này xuất hiện Ở NHIỀU GIẤY: TỜ TRÌNH (mục "Nội dung thông tin đính chính": a. Thông tin
  đang ghi trong hồ sơ / b. Thông tin đề nghị đính chính), ĐƠN Mẫu 26 ("Thông tin đang ghi" / "Thông tin
  đề nghị sửa đổi, bổ sung"), và CÔNG VĂN Sở Nội vụ.
  + CHỌN NGUỒN ĐẦY ĐỦ & RÕ NHẤT; ƯU TIÊN bản ghi ĐỦ NGÀY/THÁNG/NĂM hơn bản chỉ có
    NĂM ("1954") — thường Tờ trình đầy đủ hơn Đơn. TUYỆT ĐỐI không rút gọn ngày tháng về mỗi năm.
  + ĐỐI CHIẾU CHÉO cùng một người giữa các giấy để sửa lỗi OCR: nếu 1 giấy đọc sai tên/năm của một dòng
  + Don_ThongTinHienTai = danh sách mục "a./đang ghi" (giá trị CŨ). 
<THÔNG TIN ĐỀ NGHỊ SỬA>
trả ra trường `Don_ThongTinDeNghiSua`
Nội dung này là mục "b./đề nghị"; nếu ghi dạng "X đính chính thành Y" thì lấy VẾ SAU (Y, giá trị MỚI, đủ ngày tháng)
  + Giữ ĐỦ danh sách (mỗi người 1 dòng), KHÔNG tóm tắt, KHÔNG hoán đổi hai nội dung này cho nhau.
## TUYỆT ĐỐI LẤY TẤT CẢ THÔNG TIN, Không cắt ngắn, không rút gọn
</THÔNG TIN ĐỀ NGHỊ SỬA>


KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
