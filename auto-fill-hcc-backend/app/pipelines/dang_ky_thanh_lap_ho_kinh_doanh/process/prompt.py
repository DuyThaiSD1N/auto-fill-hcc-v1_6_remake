"""Luật trích "Đăng ký thành lập hộ kinh doanh" (1.001612) trên Cổng DVC quốc gia mới.

Dùng nguyên luật đọc của bản HkdOnline (cùng Giấy đề nghị Mẫu số 1) rồi thêm phần biểu mẫu mới cần riêng.
"""

from app.pipelines.dang_ky_kinh_doanh.process.prompt import EXTRA_RULES as _HKD_RULES

EXTRA_RULES = _HKD_RULES + """

BỔ SUNG CHO BIỂU MẪU CỔNG DỊCH VỤ CÔNG QUỐC GIA (vẫn giữ mọi luật ở trên):
- Biểu mẫu tách riêng HAI địa chỉ cá nhân của chủ hộ, nên NGOÀI ChuHo_DiaChi còn trả:
  + ChuHo_NoiThuongTru: khối "Nơi thường trú" ở phần thông tin chủ hộ của Giấy đề nghị (3 dòng số nhà / xã / tỉnh).
    Giấy để trống khối này thì lấy dòng "Nơi thường trú"/"Nơi cư trú" trên CCCD của CHÍNH chủ hộ.
  + ChuHo_NoiOHienTai: khối "Nơi ở hiện tại" của chủ hộ trên Giấy đề nghị; để trống → bỏ (không chép thường trú sang).
  + ChuHo_DanToc, ChuHo_QuocTich: dòng "Dân tộc", "Quốc tịch" của chủ hộ (Giấy đề nghị, giấy ủy quyền mục Bên ủy quyền).
- Giấy ủy quyền nộp hồ sơ có ghi "Thư điện tử" / "Nơi ở hiện tại" của BÊN ĐƯỢC ỦY QUYỀN → UyQuyen_NguoiDuocUyQuyen_Email,
  UyQuyen_NguoiDuocUyQuyen_NoiOHienTai (dòng chỉ có dấu chấm "……" là để trống → bỏ). UyQuyen_NguoiDuocUyQuyen_DiaChi
  vẫn là "Nơi thường trú" của bên được ủy quyền.
- ChuTheThanhLap: mục 6 "Chủ thể thành lập hộ kinh doanh" — "Cá nhân" hoặc "Các thành viên hộ gia đình" theo ô đánh dấu
  (☒, X); ô không đánh dấu thì không chọn.
- TruSo_KhongKinhDoanhTaiTruSo: true CHỈ khi ô "Không kinh doanh tại trụ sở" ở mục 2 được đánh dấu; ô "☐" trống → bỏ.
- ThanhVien_DanhSach: CHỈ khi mục 6 chọn "Các thành viên hộ gia đình" — đọc bảng mục 7 "Thông tin về các thành viên hộ
  gia đình", mỗi dòng có họ tên một object (giữ cả dòng chủ hộ), đúng cột: họ tên, ngày sinh, số định danh cá nhân,
  giới tính, quốc tịch, dân tộc, nơi thường trú, nơi ở hiện tại; ô trống → bỏ khoá đó. Không lấy cột "Chữ ký".
"""
