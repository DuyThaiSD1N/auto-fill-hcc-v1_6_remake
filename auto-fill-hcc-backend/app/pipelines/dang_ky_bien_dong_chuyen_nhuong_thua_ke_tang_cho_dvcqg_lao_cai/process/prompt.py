"""Luật prompt riêng cho thủ tục 1.013831 (Lào Cai) — đăng ký biến động chuyển nhượng, thừa kế, tặng cho.

Nghiệp vụ và bộ fact trùng 1.115668 → dùng lại luật của pipeline đó, chỉ thêm phần riêng của 1.013831.
"""

from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process.prompt import EXTRA_RULES as _RULES_115668

_RULES_1013831 = """Mã thủ tục trên cổng: 1.013831.H38. Đơn đăng ký biến động của thủ tục này là "Mẫu số 18 ban hành
kèm theo Nghị định số 151/2025/NĐ-CP" — CÙNG loại đơn với "Mẫu số 24" nhắc bên dưới. Trên Mẫu số 18 các mục
đánh số khác: 1.1 Tên (= mục 1.a), 1.2 Giấy tờ nhân thân/pháp nhân (= 1.b), 1.3 Địa chỉ (= 1.c), 1.4–1.6 là
người sử dụng đất THỨ HAI (vợ/chồng cùng đứng tên — KHÔNG phải chủ hồ sơ), 1.7 Điện thoại liên hệ (= 1.d).

MỘT HỒ SƠ CÓ THỂ GỒM NHIỀU THỬA / NHIỀU GIẤY CHỨNG NHẬN: mỗi thửa một Đơn, một Tờ khai lệ phí trước bạ, một
Tờ khai thuế TNCN, nhưng CÙNG bên nhận → chủ hồ sơ vẫn là MỘT người. Hai Đơn của cùng người có thể ghi địa chỉ
lệch nhau (một đơn ghi tên tỉnh CŨ trước sáp nhập, vd "tỉnh Yên Bái"): ưu tiên địa chỉ trên hợp đồng công
chứng; với Đơn thì chọn bản ghi đơn vị hành chính hiện hành.

TỜ KHAI THUẾ (01/LPTB, 03/BĐS-TNCN):
- ToKhaiThue_* là của NGƯỜI NỘP THUẾ = bên nhận chuyển nhượng. Tờ khai TNCN mục I là NGƯỜI CHUYỂN NHƯỢNG
  (bên bán) — không lấy họ tên/số/điện thoại ở mục I.
- Họ tên trên tờ khai thường VIẾT TAY, dễ đọc lệch dấu ("Cương"/"Cường"). Họ tên chủ hồ sơ lấy theo hợp đồng
  công chứng/giấy ủy quyền/Đơn (đánh máy hoặc in hoa), KHÔNG theo chữ viết tay của tờ khai.
- Người ký "UQ <họ tên>" ở cuối Đơn/tờ khai, hoặc ghi ở mục "[05] Tổ chức, cá nhân khai, nộp thuế thay" là
  NGƯỜI ĐƯỢC ỦY QUYỀN đi nộp, KHÔNG phải chủ hồ sơ.

GIẤY ỦY QUYỀN công chứng: bên ủy quyền thường gồm CẢ bên chuyển nhượng lẫn bên nhận ("chúng tôi gồm có …");
người đứng sau "Bằng giấy này chúng tôi ủy quyền cho:" là NguoiDuocUyQuyen. Người làm chứng, công chứng viên
trong lời chứng không giữ vai nào.
"""

EXTRA_RULES = _RULES_1013831 + "\n\n" + _RULES_115668
