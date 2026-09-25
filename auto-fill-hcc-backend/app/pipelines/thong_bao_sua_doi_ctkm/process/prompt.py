"""Prompt rules đặc thù cho "Thông báo sửa đổi, bổ sung nội dung chương trình khuyến mại" (Bộ Công Thương)."""

EXTRA_RULES = """<critical_rules>
1. Chỉ trả field nguồn trong schema. KHÔNG trả field UI dạng data[...].
2. Nguồn chính là văn bản "THÔNG BÁO SỬA ĐỔI, BỔ SUNG NỘI DUNG CHƯƠNG TRÌNH KHUYẾN MẠI" (Mẫu 06) của
   thương nhân; có thể kèm CCCD của người đi nộp.
3. KHÔNG bịa, KHÔNG tự bù. Văn bản hay bị che/cắt bớt chữ số (điện thoại, fax, mã số thuế, số tài khoản):
   chép đúng phần đọc được, không thêm số. Không chắc thì bỏ field.
</critical_rules>

<vai_tro>
- ThuongNhan_* = thương nhân thực hiện khuyến mại (doanh nghiệp), lấy ở phần đầu Thông báo: Tên thương
  nhân, Địa chỉ trụ sở chính, Điện thoại, Fax, Mã số thuế, Người liên hệ.
- NguoiNop_* CHỈ lấy từ CCCD/thẻ căn cước. Hồ sơ không có CCCD → bỏ toàn bộ NguoiNop_*. Người liên hệ,
  người ký văn bản, giám đốc… KHÔNG phải NguoiNop.
- Hai số điện thoại trên Thông báo là của HAI chủ thể: dòng thông tin thương nhân → ThuongNhan_DienThoai;
  dòng "Người liên hệ" → ThuongNhan_DienThoaiLienHe.
</vai_tro>

<hai_van_ban>
Văn bản NÀY sửa đổi một Thông báo thực hiện khuyến mại GỐC:
- ThongBao_So / ThongBao_NgayLap = số và ngày của chính Thông báo sửa đổi (góc trái "Số: …" và dòng
  "<địa danh>, ngày … tháng … năm …").
- ThongBaoGoc_So / ThongBaoGoc_Ngay = số và ngày trong câu "Căn cứ Thông báo thực hiện khuyến mại số …
  ngày …". KHÔNG đổi chéo hai cặp này.
</hai_van_ban>

<chuong_trinh>
- CTKM_Ten = đúng dòng "Tên chương trình khuyến mại".
- CTKM_NgayBatDauSuaDoi = ngày bắt đầu áp dụng NỘI DUNG SỬA ĐỔI; "Thời gian khuyến mại: từ … đến …" là
  thời gian của CẢ chương trình, KHÔNG dùng cho field này.
- Phần "nội dung chi tiết thể lệ" được sửa (điều kiện, cách thức, giao diện, cơ cấu giải…) KHÔNG có field
  → bỏ qua, không nhét vào CTKM_LyDoDieuChinh.
</chuong_trinh>

<reminder>Chỉ trả JSON field nguồn hợp lệ. Không bù chữ số bị che; phân biệt Thông báo sửa đổi với Thông báo
gốc; điện thoại thương nhân khác điện thoại người liên hệ.</reminder>"""
