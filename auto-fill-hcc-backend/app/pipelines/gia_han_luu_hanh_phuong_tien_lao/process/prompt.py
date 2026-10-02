"""Prompt rules đặc thù cho "Gia hạn thời gian lưu hành tại Việt Nam cho phương tiện của Lào" (Form.io — Bộ Xây
dựng)."""

EXTRA_RULES = """Thủ tục: Gia hạn thời gian lưu hành tại Việt Nam cho phương tiện của Lào. Đầu vào thường gồm: Giấy
đề nghị gia hạn (Mẫu số 07), Giấy phép liên vận quốc tế Lào – Việt Nam (bìa, trang thông tin xe, trang
"Record" có dấu xuất/nhập cảnh), có thể có báo giá / giấy tờ chứng minh lý do (xe hỏng…), CCCD.

CHỈ MỘT NGƯỜI đứng đơn = NGƯỜI XIN GIA HẠN trên Mẫu 07 (cá nhân). Trích NguoiNop_* từ Mẫu 07 + CCCD của
chính người này:
- Ngày sinh / giới tính / số CCCD / ngày cấp / nơi cấp CHỈ lấy từ thẻ CCCD; hồ sơ không có thẻ thì BỎ.
- ⚠ CHỦ XE là doanh nghiệp Lào (tên chữ Lào trên giấy phép liên vận) — KHÔNG phải người nộp. Người ký báo
  giá / cán bộ hải quan / người ký giấy phép cũng KHÔNG phải người nộp.
- ⚠ Số giấy phép liên vận, số khung, số máy, mã số thuế của gara KHÔNG phải số CCCD.

ĐỀ NGHỊ (DeNghi_*): lấy trên Mẫu 07; chỉ biển số và ngày nhập cảnh được lấy thêm từ giấy phép liên vận.
- DeNghi_SoNgayGiaHan, DeNghi_TuNgay, DeNghi_DenNgay: chép đúng trên đơn, KHÔNG tự tính.
- DeNghi_ThoiGianNhapCanh: dấu NHẬP CẢNH vào Việt Nam có ngày LỚN NHẤT trên mọi trang Record (so đủ ngày,
  tháng, năm); không phân biệt được dấu nhập hay xuất cảnh thì BỎ.
- DeNghi_BienSo: ký hiệu chữ + 4–5 chữ số, chép nguyên văn (giữ chữ Lào). Dãy số dài in gần nhãn
  "Registration Number" là mã tem, KHÔNG phải biển số → lấy biển số ở Mẫu 07 hoặc báo giá sửa xe.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
