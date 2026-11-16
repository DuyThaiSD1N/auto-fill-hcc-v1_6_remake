"""Luật prompt riêng cho thủ tục 1.012575 — Đăng ký xe lần đầu toàn trình, xe sản xuất, lắp ráp trong nước."""

EXTRA_RULES = """Hồ sơ đăng ký xe lần đầu (xe sản xuất, lắp ráp trong nước), thường gồm: Giấy khai đăng ký xe (Mẫu ĐKX10/79); Phiếu kiểm tra chất lượng xuất xưởng (Phiếu KTCLXX); Hóa đơn giá trị gia tăng điện tử bán xe; Thông báo nộp lệ phí trước bạ; Giấy nộp tiền vào ngân sách nhà nước (Mẫu C1-02/NS); thẻ căn cước của chủ xe; có khi kèm trang thông tin hồ sơ ghi hình thức nhận kết quả. Mỗi field có tiền tố theo giấy (Cccd_, ToKhai_, Pkt_, HoaDon_, Lptb_, Gnt_, HoSo_): CHỈ đọc field từ đúng giấy đó, giấy nào không có trong hồ sơ thì bỏ hết field của nó.

CHỦ XE:
- Cccd_* chỉ đọc từ thẻ căn cước/CCCD của chủ xe (họ tên trùng "Tên chủ xe" trên Giấy khai). Không lấy thẻ của người khác.
- Thẻ căn cước mẫu mới: ngày cấp ở dòng "Ngày, tháng, năm cấp / Date of issue"; nơi cấp là dòng "BỘ CÔNG AN" in cuối mặt sau dù không có nhãn.
- ToKhai_LoaiGiayTo, ToKhai_CoQuanCap, ToKhai_NgayCap là giấy tờ tùy thân của chủ xe — KHÔNG lấy "Số GPKDVT" / "Cơ quan cấp" / "Ngày cấp" của giấy phép kinh doanh vận tải ở dòng dưới.
- Mã số thuế cá nhân thường trùng số định danh: vẫn đọc riêng từng field theo nhãn của giấy.

ĐẶC ĐIỂM XE (Xe_*): mọi giấy cùng ghi một xe; lấy theo Phiếu KTCLXX trước, rồi Giấy khai, Thông báo LPTB, Hóa đơn. Ô ghi chấm chấm "……" là để trống → bỏ field, không ghi chữ "Trống". Số khung/số máy chép đúng từng ký tự, không thêm khoảng trắng. Xe_DungTich, Xe_CongSuat, Xe_KhoiLuong* chỉ trả SỐ (giữ dấu phẩy thập phân), không kèm đơn vị.

LỆ PHÍ TRƯỚC BẠ / HÓA ĐƠN:
- Lptb_MaHoSo là "Mã hồ sơ" của Thông báo; Gnt_MaHoSo là cột mã hồ sơ của Giấy nộp tiền; ToKhai_MaChungTuLptb là dòng "Mã chứng từ lệ phí trước bạ" — đọc riêng từng giấy.
- Lptb_NgayThongBao là ngày ban hành Thông báo; Gnt_NgayThongBao là cột "Kỳ thuế/Ngày thông báo". KHÔNG lấy "Ngày nộp" của Giấy nộp tiền hay hạn nộp.
- Số tiền chép đúng chữ số như in (giữ dấu chấm phân cách nghìn), không đổi đơn vị.
- HoaDon_So giữ đủ số 0 đầu (vd "00000123").

Không bịa thông tin thiếu; không chắc thì bỏ field. Không trả field UI như CongDan__fs*."""
