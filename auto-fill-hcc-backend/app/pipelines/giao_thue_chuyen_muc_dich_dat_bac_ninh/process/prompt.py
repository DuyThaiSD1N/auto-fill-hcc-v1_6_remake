
"""Quy tắc compact prompt cho "[Bắc Ninh] Giao/thuê/chuyển mục đích SDĐ" (Đơn Mẫu 01/02)."""

EXTRA_RULES = """Đầu vào chính là ĐƠN đề nghị (giao đất / cho thuê đất / chuyển mục đích sử dụng đất /
gia hạn) do công dân tự khai — Mẫu số 01 hoặc 02. Có thể kèm CCCD và Giấy chứng nhận QSDĐ.

NGUỒN & CÁCH LẤY:
- Hầu hết field lấy NGUYÊN VĂN từ các mục đánh số trên đơn: 1. Người đề nghị, 2. Địa chỉ/trụ sở,
  3. Địa chỉ liên hệ, 4. Địa điểm thửa đất, 5. Diện tích đất, 6. Diện tích rừng, 7. Mục đích,
  8. Thời hạn. Không suy diễn, không bịa; mục trống thì bỏ field.
- Don_LoaiDon là dòng tiêu đề IN HOA "ĐƠN ĐỀ NGHỊ ..." (vd "ĐƠN ĐỀ NGHỊ CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT").
- Don_KinhGui lấy sau "Kính gửi:"; bỏ ký hiệu chú thích "(2)" ở cuối.
- Don_SoDienThoai: mục 3 ghi "điện thoại, fax, email" — ưu tiên lấy SỐ ĐIỆN THOẠI.

- QUAN TRỌNG — NGOẠI LỆ quy tắc địa chỉ chung (quy tắc 5): các field Don_DiaChiTruSo và
  Don_DiaDiemThuaDat PHẢI là CHUỖI (string) MỘT DÒNG, chép nguyên văn, GIỮ ĐỦ tổ dân phố/thôn +
  phường/xã + tỉnh (và số thửa/tờ bản đồ nếu có với địa điểm thửa đất). TUYỆT ĐỐI KHÔNG trả object,
  KHÔNG bỏ phường/xã.

- Cccd_SoDinhDanh: số CCCD/định danh người đề nghị, lấy từ CCCD hoặc dòng "CCCD số/Số:" trên đơn.

KHÔNG trả field UI dạng "element_...", "nhanTaiNha...", "1. Người đề nghị"; chỉ trả field nguồn
trong schema. Diện tích giữ nguyên cách ghi số của đơn (vd "402,0").

Ví dụ output ĐÚNG:
```json
{"fields":{"Don_LoaiDon":"ĐƠN ĐỀ NGHỊ CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT","Don_KinhGui":"Chủ tịch UBND phường Song Liễu","Don_NguoiDeNghi":"Nguyễn Ngọc Truyền","Don_DiaChiTruSo":"Tổ dân phố Tứ Cờ, phường Song Liễu, tỉnh Bắc Ninh","Don_SoDienThoai":"0981988972","Don_DiaDiemThuaDat":"TDP Tứ Cờ, phường Song Liễu, tỉnh Bắc Ninh (thửa 135, tờ BĐ 97)","Don_DienTichDat":"402,0","Don_MucDich":"Đất ở tại đô thị (ODT)","Don_ThoiHan":"Lâu dài","Cccd_SoDinhDanh":"027072000825"}}
```"""
