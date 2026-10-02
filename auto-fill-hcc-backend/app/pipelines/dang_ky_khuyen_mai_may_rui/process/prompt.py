"""Prompt rules đặc thù cho "Đăng ký hoạt động khuyến mại mang tính may rủi trên địa bàn 01 tỉnh" (Bộ Công
Thương)."""

EXTRA_RULES = """<critical_rules>
1. Chỉ trả field nguồn trong schema. KHÔNG trả field UI dạng data[...].
2. Nguồn chính là "ĐĂNG KÝ THỰC HIỆN KHUYẾN MẠI" (Mẫu số 02 ĐP) của thương nhân; "THỂ LỆ CHƯƠNG TRÌNH KHUYẾN
   MẠI" (Mẫu số 03 ĐP) chỉ bổ khuyết mục Đơn không ghi. Có thể kèm CCCD người đi nộp, mẫu phiếu bốc thăm,
   giấy chứng nhận chất lượng hàng hóa, ảnh giải thưởng — các giấy này KHÔNG cung cấp field nào trừ CCCD.
3. Bản scan hay XẾP LẪN TRANG: phần cuối Mẫu 02 (mục 8 Tổng giá trị giải thưởng, cam kết, chữ ký) có thể
   nằm trong tệp Thể lệ và phần giữa Thể lệ (mục 8.1 → 11) nằm trong tệp Đăng ký. Đọc theo NỘI DUNG mục,
   không theo tên tệp.
4. KHÔNG bịa, KHÔNG tự bù. Chữ số bị che/cắt thì chép đúng phần đọc được. Không chắc thì bỏ field.
</critical_rules>

<vai_tro>
- ThuongNhan_* = thương nhân thực hiện khuyến mại (hộ kinh doanh / doanh nghiệp) ở phần đầu Mẫu 02: Tên
  thương nhân, Địa chỉ trụ sở chính, Điện thoại, Fax, Email, Mã số thuế, Số căn cước (nếu in), Người liên hệ.
- NguoiNop_* CHỈ lấy từ thẻ CCCD/căn cước. Hồ sơ không có thẻ → bỏ toàn bộ NguoiNop_*. Người liên hệ, người
  ký Đơn, họ tên khách hàng in trên phiếu bốc thăm KHÔNG phải NguoiNop.
- Hai số điện thoại trên Đơn là của HAI chủ thể: dòng thông tin thương nhân → ThuongNhan_DienThoai; dòng
  "Người liên hệ" → ThuongNhan_DienThoaiLienHe (kể cả khi trùng số).
- Chữ trên CON DẤU (tên cửa hàng, địa chỉ cũ trước sáp nhập, ĐT, MST) không thay cho dòng tương ứng trên
  Đơn; chỉ dùng MST trên dấu khi Đơn không ghi mã số thuế.
</vai_tro>

<chuong_trinh>
- Thời gian khuyến mại: CTKM_TuNgay/CTKM_DenNgay lấy từ mục "Thời gian khuyến mại"; thời gian xác định trúng
  thưởng, trao thưởng, ngày lập Đơn KHÔNG phải thời gian khuyến mại.
- Mẫu 02 và Thể lệ đánh số mục KHÁC nhau (Mẫu 02: 3 = hàng được KM, 4 = hàng dùng để KM; Thể lệ: 2 = hàng
  được KM, 7 = cơ cấu giải thưởng) → khớp theo TÊN mục, không theo số mục.
- Mục 9 "Tên của các thương nhân cùng thực hiện" và các mục 8.1 → 11 của thể lệ KHÔNG có field → bỏ qua.
</chuong_trinh>

<reminder>Chỉ trả JSON field nguồn hợp lệ. Mẫu 02 là nguồn chính, Thể lệ bổ khuyết; không lấy chữ trên con dấu
thay dòng trên Đơn; điện thoại thương nhân khác điện thoại người liên hệ; NguoiNop chỉ từ thẻ CCCD.</reminder>"""
