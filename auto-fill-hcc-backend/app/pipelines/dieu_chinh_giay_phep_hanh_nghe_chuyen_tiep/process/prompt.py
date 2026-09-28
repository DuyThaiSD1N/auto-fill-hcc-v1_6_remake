"""Prompt rules đặc thù cho "Điều chỉnh giấy phép hành nghề trong giai đoạn chuyển tiếp..." (Form.io —
cổng Bộ Y tế)."""

EXTRA_RULES = """Thủ tục: Điều chỉnh giấy phép hành nghề khám bệnh, chữa bệnh trong giai đoạn chuyển tiếp (hồ sơ
nộp từ 01/01/2024 đến thời điểm kiểm tra đánh giá năng lực hành nghề) — thường để BỔ SUNG/THAY ĐỔI phạm vi
hành nghề. Đầu vào có thể gồm: Đơn đề nghị (Mẫu 08 PL I NĐ 96/2023), bản sao chứng chỉ hành nghề / giấy
phép hành nghề ĐÃ CẤP, bản sao văn bằng đào tạo (bằng chuyên khoa cấp I/II, bằng tốt nghiệp…), chứng chỉ
đào tạo (liên tục / chuyên khoa cơ bản), giấy xác nhận thực hành (Mẫu 07), CCCD người hành nghề, và CÓ
THỂ có CCCD của người nộp thay.

HAI vai — tách RIÊNG, KHÔNG lẫn:
- NGƯỜI HÀNH NGHỀ (NguoiHanhNghe_*) = CHỦ HỒ SƠ = người đứng tên Đơn Mẫu 08 ("Họ và tên", "NGƯỜI LÀM ĐƠN").
- NGƯỜI NỘP (NguoiNop_*) = tài khoản đứng nộp. ĐA SỐ tự nộp → BỎ TRỐNG NguoiNop_*. Chỉ khi hồ sơ có CCCD
  RIÊNG của một người KHÁC người hành nghề mới trích NguoiNop_* từ CCCD đó (xem <nguoi_nop_context>).

THỨ TỰ NGUỒN cho NguoiHanhNghe_*: (1) CCCD → (2) Đơn Mẫu 08 → các giấy còn lại chỉ để đối chiếu.
⚠ CHỨNG CHỈ HÀNH NGHỀ / GPHN cũ (cấp từ nhiều năm trước) in số CMND 9 chữ số, "Cấp ngày", "Nơi cấp: Công an
tỉnh…" và "Chỗ ở hiện nay" CŨ → TUYỆT ĐỐI KHÔNG dùng các giá trị đó cho SoDinhDanh / NgayCap / NoiCap /
ThuongTru. Văn bằng và chứng chỉ đào tạo cũng ghi địa chỉ/nơi công tác CŨ → không dùng cho ThuongTru.
- SoDinhDanh: số 12 chữ số trên CCCD hoặc Đơn Mẫu 08.
- NgayCap / NoiCap: đi kèm số định danh đó (CCCD hoặc Đơn Mẫu 08 "Ngày cấp"/"Nơi cấp").
- GioiTinh: CCCD; không có CCCD thì chứng chỉ đào tạo có ô "Giới tính". Không có nguồn thì bỏ.
- ThuongTru: Đơn Mẫu 08 "Địa chỉ cư trú" hoặc CCCD. Viết đầy đủ đơn vị hành chính ("t.p Hải Phòng" →
  "Thành phố Hải Phòng", "phường An Biên" → "Phường An Biên"). diaChi chỉ là số nhà/đường/tổ/thôn; đơn
  chỉ ghi phường + tỉnh thì để diaChi trống.
- DienThoai / Email: Đơn Mẫu 08. Chữ viết tay: đọc cẩn thận từng chữ số, email viết thường.

HoSo_TruongHopDeNghi / HoSo_PhamViHanhNghe: đọc Đơn Mẫu 08 (thường VIẾT TAY) mục "Trường hợp đề nghị cấp"
và "Phạm vi hành nghề đề nghị cấp"; sửa chính tả chữ viết tay cho đúng thuật ngữ y khoa, không thêm ý.

LƯU Ý: các mục nghiệp vụ khác của Mẫu 08 (Kính gửi, cơ sở KCB đang làm việc, văn bằng chuyên môn, chức danh,
số GPHN đã cấp, danh mục giấy tờ kèm theo) KHÔNG có trường nhập online → KHÔNG trích.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
