"""Luật prompt riêng cho thủ tục 1.003460 — Cấp thẻ tạm trú cho người nước ngoài tại Việt Nam (Công an cấp tỉnh)."""

EXTRA_RULES = """Hồ sơ đề nghị cấp THẺ TẠM TRÚ cho MỘT người nước ngoài đang ở Việt Nam, thường gồm: Văn bản đề nghị cấp thẻ tạm trú của cơ quan, tổ chức (Mẫu NA6) hoặc của cá nhân bảo lãnh (Mẫu NA7); Tờ khai đề nghị cấp thẻ tạm trú (Mẫu NA8, song ngữ "INFORMATION FORM FOR A TEMPORARY RESIDENT CARD", mục 1–12); hộ chiếu của người nước ngoài (trang nhân thân có MRZ "P<…", trang THỊ THỰC VIỆT NAM, dấu kiểm chứng nhập cảnh); giấy tờ chứng minh thuộc diện xem xét cấp thẻ (giấy phép lao động / WORK PERMIT …); có khi trang đầu là bìa "HỒ SƠ THỦ TỤC HÀNH CHÍNH" + danh mục thành phần hồ sơ. Mỗi field có tiền tố theo giấy (ToKhai_, VanBan_, HoChieu_, GPLD_, Bia_, Cccd_): CHỈ đọc field từ đúng giấy đó, giấy nào không có trong hồ sơ thì bỏ hết field của nó.

TỜ KHAI NA8 (ToKhai_*): đọc đúng mục theo số thứ tự in trên tờ khai; phần chữ nghiêng tiếng Anh dưới mỗi nhãn là bản dịch nhãn, KHÔNG phải giá trị. Mục 11 "Điện thoại liên hệ/Email" ghi chung một dòng "<số> / <email>": tách phần số vào ToKhai_DienThoai, phần có @ vào ToKhai_Email. Ô được đánh dấu: ☒ / X / ✓ là được chọn, ☐ là không chọn. Dòng để trống / chấm chấm → bỏ field.

VĂN BẢN ĐỀ NGHỊ NA6 / NA7 (VanBan_*): tên cơ quan, "Trụ sở tại", "Điện thoại", "Số:" ở góc trái; ngày ký ở góc phải; bảng danh sách người nước ngoài được đề nghị. "Kính gửi" là cơ quan tiếp nhận — KHÔNG dùng cho field nào.

HỘ CHIẾU (HoChieu_*): chỉ đọc hộ chiếu của chính người nước ngoài. MRZ dùng để kiểm số hộ chiếu, mã quốc gia, ngày sinh, giới tính, ngày hết hạn (MRZ ghi yymmdd). Trang thị thực cho HoChieu_ThiThuc_KyHieu; dấu kiểm chứng nhập cảnh (ARRIVAL) cho HoChieu_NhapCanh_* và HoChieu_TamTruDen.

GIẤY PHÉP LAO ĐỘNG (GPLD_*): giấy "GIẤY PHÉP LAO ĐỘNG / WORK PERMIT" của chính người nước ngoài.

TRANG BÌA (Bia_*): chỉ đọc Bia_KyHieuThe và Bia_MaSoDoanhNghiep; mọi field khác KHÔNG đọc từ trang bìa / danh mục.

CCCD (Cccd_*): chỉ khi hồ sơ có thẻ căn cước của công dân Việt Nam (người đăng nhập / người bảo lãnh).

Không bịa thông tin thiếu; không chắc thì bỏ field. Không trả field UI như CongDan__fs*."""
