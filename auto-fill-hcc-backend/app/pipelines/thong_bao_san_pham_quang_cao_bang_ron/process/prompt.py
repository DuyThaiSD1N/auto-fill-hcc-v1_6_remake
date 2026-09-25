"""Prompt rules đặc thù cho "Thủ tục tiếp nhận hồ sơ thông báo sản phẩm quảng cáo trên bảng quảng cáo,
băng-rôn" (Bộ VHTTDL — cổng liz)."""

EXTRA_RULES = """<critical_rules>
1. Chỉ trả field nguồn trong schema. KHÔNG trả field UI.
2. Hồ sơ gồm: Thông báo sản phẩm quảng cáo trên bảng quảng cáo, băng-rôn (Mẫu số 01 — tờ khai chính),
   Giấy chứng nhận đăng ký doanh nghiệp, ma-két, bản phối cảnh, giấy tờ hợp chuẩn/hợp quy, có thể có
   thông báo khuyến mại. Chỉ lấy dữ liệu từ ĐÚNG giấy tờ mô tả trong field.
3. KHÔNG bịa, KHÔNG bù. Tờ khai hay để trống ngày hoặc bị che bớt chữ số (điện thoại, mã số, CCCD):
   chép đúng phần đọc được; trống thì bỏ field.
</critical_rules>

<vai_tro>
- DoanhNghiep_* = doanh nghiệp đứng tên thông báo quảng cáo. Ưu tiên Giấy chứng nhận đăng ký doanh
  nghiệp; thiếu mới lấy mục 1 của tờ khai.
- "Người chịu trách nhiệm" (giám đốc) trên tờ khai là CÁ NHÂN: số CCCD, địa chỉ thường trú, số điện thoại
  của người này KHÔNG phải của doanh nghiệp.
- Nội dung, ma-két, thông báo khuyến mại hay nhắc tên doanh nghiệp/địa điểm KHÁC (thương hiệu được quảng
  cáo, địa điểm kinh doanh) — đó không phải doanh nghiệp đứng tên.
</vai_tro>

<thoi_gian>
ThongBao_TuNgay / ThongBao_DenNgay CHỈ lấy ở mục 4 của tờ khai. "Thời gian khuyến mại" của thông báo
khuyến mại và ngày ghi trên ma-két là thời gian KHÁC, không dùng.
</thoi_gian>

<reminder>Chỉ trả JSON field nguồn hợp lệ. Doanh nghiệp ≠ người chịu trách nhiệm; không bù chữ số bị che;
thời gian thực hiện chỉ lấy ở mục 4 tờ khai.</reminder>"""
