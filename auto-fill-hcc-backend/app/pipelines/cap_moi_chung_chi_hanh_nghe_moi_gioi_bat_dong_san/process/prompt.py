"""Prompt rules đặc thù cho "Cấp mới chứng chỉ hành nghề môi giới bất động sản" (1.012906)."""

EXTRA_RULES = """Thủ tục: Cấp mới chứng chỉ hành nghề môi giới bất động sản (Sở Xây dựng) — Luật Kinh doanh bất động
sản 2023, Nghị định 96/2024/NĐ-CP. Hồ sơ thường gồm: Đơn đăng ký dự thi sát hạch có dán ảnh 4x6 (Phụ lục XXI), bản
sao CCCD / thẻ căn cước, bằng tốt nghiệp THPT trở lên, Giấy chứng nhận hoàn thành khóa đào tạo, bồi dưỡng kiến thức
hành nghề môi giới BĐS, ảnh 4x6. Người dân có thể nộp nhầm ĐƠN XIN CẤP LẠI chứng chỉ — vẫn trích bình thường vì các
mục nhân thân trùng nghĩa, Don_Loai = "cap_lai". Nhiều giấy tờ có thể gộp chung một PDF scan.

NGƯỜI ĐỀ NGHỊ (NguoiDeNghi_*) = người đứng tên đơn (người dán ảnh, ký "Người làm đơn" / "Người đề nghị").
⚠ Ưu tiên CCCD của CHÍNH người này; MRZ mặt sau dùng để kiểm tra chéo (dòng 1 chứa số định danh, dòng 2 YYMMDD ngày
  sinh + giới tính M/F + VNM).
⚠ Ngày cấp CCCD ở mặt sau ("Ngày, tháng, năm / Date, month, year"); "Có giá trị đến / Date of expiry" là ngày hết hạn.
⚠ NguoiDeNghi_NoiSinh: lấy từ CCCD của người đề nghị — CCCD mẫu 2021 dùng dòng "Quê quán / Place of origin", thẻ
  Căn cước mới dùng "Nơi đăng ký khai sinh". Chép nguyên văn cả dòng (vd "Tân Phú, Phú Ninh, Quảng Nam").
⚠ Địa chỉ: CCCD cấp trước 07/2025 ghi đơn vị hành chính CŨ (có quận/huyện); đơn làm sau đó hay ghi phường/xã MỚI.
  NguoiDeNghi_DiaChiThuongTru chép nguyên văn CCCD (không có CCCD thì theo đơn). NguoiDeNghi_ThuongTru lấy tinh/xa
  theo đơn khi đơn ghi phường/xã mới. Vd CCCD "Tổ 3 An Hòa, Cẩm Lệ, Đà Nẵng", đơn "Tổ 3 An Hòa, phường Cẩm Lệ" →
  NguoiDeNghi_DiaChiThuongTru = "Tổ 3 An Hòa, Cẩm Lệ, Đà Nẵng", NguoiDeNghi_ThuongTru = {"tinh":"Thành phố Đà Nẵng",
  "xa":"Phường Cẩm Lệ","diaChi":"Tổ 3 An Hòa"}.
⚠ Mục "Nơi ở hiện nay" KHÔNG phải nơi thường trú.

NGƯỜI NỘP (NguoiNop_*) = tài khoản đăng nhập cổng. CHỈ trích từ thẻ CCCD được chỉ ra trong nguoi_nop_context.
Không có thẻ → BỎ TRỐNG NguoiNop_*. Người nộp chính là người đề nghị thì NguoiNop_* trùng NguoiDeNghi_* (vẫn trích).

TỔ CHỨC (ToChuc_*): chỉ khi hồ sơ có giấy tờ của tổ chức nộp hồ sơ (GCN đăng ký doanh nghiệp, giấy giới thiệu).
Mục "Đơn vị công tác" trên đơn cá nhân KHÔNG phải căn cứ → ToChuc_* bỏ trống, ghi vào NguoiDeNghi_DonViCongTac.

KHÔNG trả field UI dạng data[...]. KHÔNG bịa thông tin còn thiếu; giấy tờ không có thì bỏ field."""
