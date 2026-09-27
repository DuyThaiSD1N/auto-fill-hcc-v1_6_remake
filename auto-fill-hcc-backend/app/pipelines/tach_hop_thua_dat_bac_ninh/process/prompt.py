"""Quy tắc compact prompt "[Bắc Ninh] Tách thửa đất/hợp thửa đất" (Đơn Mẫu số 22)."""

EXTRA_RULES = """Đầu vào gồm: CCCD chủ đất, Đơn đề nghị tách/hợp thửa (Mẫu 22), Giấy chứng nhận QSDĐ
(sổ đỏ) và Bản vẽ tách thửa (Mẫu 22a). Chỉ trích thông tin CHỦ ĐẤT (người sử dụng đất đứng đơn),
KHÔNG lấy người được ủy quyền/nộp thay.

TRỌNG TÂM là nhánh TÁCH THỬA: thửa đất GỐC (số thửa, tờ bản đồ, diện tích, loại đất, địa chỉ thửa,
GCN, ngày cấp) + diện tích các THỬA MỚI sau tách. KHÔNG cần trích nhánh hợp thửa.

NGUỒN & CÁCH LẤY:
- Cccd_HoTen/Cccd_SoDinhDanh: từ CCCD chủ đất hoặc mục 1.1/1.2 của đơn (đơn mẫu cũ ghi 1.a/1.b).
- Nguoi_DienThoai: mục 1.4 "Điện thoại liên hệ" của đơn; bỏ nếu không ghi.
- Thua_So/Thua_ToBanDo/Thua_DienTich/Thua_LoaiDat/Thua_DiaChi/Gcn_SoVaoSo/Gcn_NgayCap: ưu tiên GCN
  (sổ đỏ) — nguồn gốc chính xác nhất; đối chiếu với đơn/bản vẽ.
- Thua_DiaChi là ĐỊA CHỈ THỬA ĐẤT (vị trí lô đất), KHÁC Nguoi_DiaChiThuongTru (nơi ở của chủ) — đừng lẫn.
- ThuaMoi_DienTich1/2, ThuaMoi_LoaiDat1/2: diện tích và loại đất từng thửa mới sau khi tách (mục "Thửa
  thứ nhất/thứ hai" của đơn hoặc bản vẽ). ThuaMoi_SoThua: số trong cụm "thành … thửa" (vd "02").
  Tách từ 3 thửa trở lên: thửa thứ ba trở đi gộp vào ThuaMoi_Khac, KHÔNG dồn vào ThuaMoi_DienTich2.
- Don_LyDo/Don_DeNghiCapGCN: chép nguyên văn mục 3/5 của đơn (bỏ nếu trống). Mục 5 thường có dạng
  "5. Đề nghị cấp Giấy chứng nhận: Không thay đổi người sử dụng đất (ghi có hoặc không thay đổi…)" →
  Don_DeNghiCapGCN = "Không thay đổi người sử dụng đất" (bỏ chú thích trong ngoặc).
- Don_GiayToKem: chỉ các giấy tờ KHÁC ở mục 4, KHÔNG chép dòng in sẵn "Giấy chứng nhận và Bản vẽ tách
  thửa đất, hợp thửa đất các thửa đất nêu trên" (cổng đã in sẵn dòng đó).

- QUAN TRỌNG — NGOẠI LỆ quy tắc địa chỉ chung (quy tắc 5): Nguoi_DiaChiThuongTru và Thua_DiaChi PHẢI
  là CHUỖI (string) MỘT DÒNG, giữ ĐỦ thôn/tổ dân phố + phường/xã + tỉnh. KHÔNG trả object, KHÔNG bỏ xã.

KHÔNG trả field UI ("element_...", "11Ten", "nhanTaiNha..."); chỉ trả field nguồn trong schema.
Không bịa; thiếu thì bỏ field. Diện tích giữ nguyên cách ghi số (vd "2644,2").

Ví dụ output ĐÚNG:
```json
{"fields":{"Cccd_HoTen":"Nguyễn Văn A","Cccd_SoDinhDanh":"027070010408","Nguoi_DiaChiThuongTru":"Thôn Rô, xã Sơn Đồng, thành phố Hà Nội","Don_KinhGui":"Chi nhánh Văn phòng đăng ký đất đai Tân Uyên","Thua_So":"9","Thua_ToBanDo":"250","Thua_DienTich":"2644,2","Thua_LoaiDat":"Đất ở tại đô thị (ODT)","Thua_DiaChi":"xã Tân Uyên, tỉnh Lai Châu","Gcn_SoVaoSo":"AA 05419774, số vào sổ CX 714","Gcn_NgayCap":"12/05/2010","ThuaMoi_SoThua":"02","ThuaMoi_DienTich1":"1322,1","ThuaMoi_LoaiDat1":"ODT","ThuaMoi_DienTich2":"1322,1","ThuaMoi_LoaiDat2":"ODT","Don_LyDo":"Để chuyển nhượng một phần"}}
```"""
