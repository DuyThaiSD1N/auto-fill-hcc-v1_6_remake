"""Prompt đặc thù cho "Đăng ký tham dự kiểm tra kết quả tập sự hành nghề công chứng" (1.013818)."""

EXTRA_RULES = """Thủ tục: Đăng ký tham dự kiểm tra kết quả tập sự hành nghề công chứng (Bộ Tư pháp). Tờ khai trên cổng là
"Giấy đăng ký tham dự kiểm tra kết quả tập sự hành nghề công chứng" Mẫu TP-TSCC-10: kỳ kiểm tra; Kính gửi; nhân thân
người tập sự (họ tên, giới tính, ngày sinh, giấy tờ tùy thân số/ngày cấp/nơi cấp, nơi ở hiện tại, điện thoại, email);
tổ chức hành nghề công chứng nơi tập sự; công chứng viên hướng dẫn; thời gian tập sự; quyết định công nhận hoàn thành
tập sự; các kỳ kiểm tra đã từng tham dự; địa danh, ngày làm giấy.

Hồ sơ thường gồm:
- GIẤY ĐĂNG KÝ THAM DỰ KIỂM TRA KẾT QUẢ TẬP SỰ HÀNH NGHỀ CÔNG CHỨNG (Mẫu TP-TSCC-10) bản giấy đã ký — nguồn chính.
- QUYẾT ĐỊNH công nhận hoàn thành tập sự hành nghề công chứng của Sở Tư pháp (thường là bản sao chứng thực): số
  quyết định, ngày ký, Sở Tư pháp tỉnh nào; Điều 1 ghi họ tên, ngày sinh, CCCD số/ngày cấp/nơi cấp người tập sự.
- Biên lai / chứng từ nộp phí thẩm định (không lấy dữ liệu tờ khai từ giấy này). Có thể có CCCD.

NGUỒN VÀ ƯU TIÊN:
- Họ tên, ngày sinh, giới tính, số định danh, ngày cấp, nơi cấp: CCCD > Giấy đăng ký > Quyết định.
- Quyết định bản sao chứng thực có dấu "CHỨNG THỰC BẢN SAO ĐÚNG VỚI BẢN CHÍNH" kèm số chứng thực và ngày chứng thực
  của văn phòng công chứng — KHÔNG phải số/ngày quyết định. Số quyết định nằm ở dòng "Số: .../QĐ-STP" góc trái; ngày
  quyết định ở dòng "<địa danh>, ngày ... tháng ... năm ..." góc phải.
- QD_CongNhan đọc trên Quyết định, DK_QuyetDinh đọc trên Giấy đăng ký — trả CẢ HAI nếu có để hệ thống đối chiếu.
- Địa chỉ "112 đường A, phường B, tỉnh C" → {quocGia:"Việt Nam", tinh:"Tỉnh C", xa:"Phường B",
  chiTietDuoiXa:"112 đường A"}; "P." là "Phường", "TP." là "Thành phố". Không có cấp huyện.
- Tổ chức tập sự, công chứng viên hướng dẫn, các kỳ đã tham dự: chép nguyên văn phần người làm giấy khai, KHÔNG chép
  phần chữ in sẵn của mẫu đứng trước dấu ':'.
- Mọi ngày dd/mm/yyyy ("5/9/2025" → "05/09/2025"). Không bịa điện thoại, email hay dữ liệu giấy tờ không ghi.

KHÔNG trả field UI của eForm (HoVaTenC, NO_TinhThanhC, SoQuyetDinhCongNhan…). Chỉ trả field compact trong schema."""
