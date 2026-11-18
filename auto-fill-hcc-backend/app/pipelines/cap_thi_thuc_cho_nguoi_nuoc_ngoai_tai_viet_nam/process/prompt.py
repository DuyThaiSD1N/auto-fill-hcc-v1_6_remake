"""Luật prompt riêng cho thủ tục 1.001194 — Cấp thị thực cho người nước ngoài tại Việt Nam (thực hiện tại cấp tỉnh)."""

EXTRA_RULES = """Hồ sơ đề nghị cấp thị thực cho MỘT người nước ngoài đang tạm trú ở Việt Nam, thường gồm: Tờ khai đề nghị cấp thị thực, gia hạn tạm trú (Mẫu NA5, song ngữ Việt – Anh, mục I Người đề nghị / II Cơ quan, tổ chức hoặc thân nhân mời, bảo lãnh / III Nội dung đề nghị / IV Những điều cần trình bày thêm); hộ chiếu của người nước ngoài (trang nhân thân có dòng MRZ "P<…", trang dấu kiểm chứng nhập cảnh Việt Nam); giấy tờ chứng minh lý do (giấy chứng nhận kết hôn, giấy phép lao động …); thẻ căn cước của người bảo lãnh (công dân Việt Nam). Có khi trang đầu là bìa "HỒ SƠ THỦ TỤC HÀNH CHÍNH" + danh mục thành phần hồ sơ — KHÔNG đọc field nào từ trang bìa. Mỗi field có tiền tố theo giấy (ToKhai_, HoChieu_, KetHon_, Cccd_): CHỈ đọc field từ đúng giấy đó, giấy nào không có trong hồ sơ thì bỏ hết field của nó.

TỜ KHAI NA5 (ToKhai_*):
- Đọc đúng mục theo số thứ tự in trên tờ khai; phần chữ nghiêng tiếng Anh dưới mỗi nhãn là bản dịch nhãn, KHÔNG phải giá trị.
- Mục I là của NGƯỜI ĐỀ NGHỊ (người nước ngoài), mục II là của CƠ QUAN / THÂN NHÂN BẢO LÃNH: không lẫn hai bên.
- Mục I.10 / II.2 "Điện thoại liên hệ/Email" ghi chung một dòng "<số> / <email>": tách phần số vào *_DienThoai, phần có @ vào *_Email.
- Dòng để trống (chỉ có nhãn, chấm chấm, "…/…/…") → bỏ field, không ghi "Không" hay "Trống".
- Ô được đánh dấu: ☒ / X / ✓ là được chọn, ☐ là không chọn.

HỘ CHIẾU (HoChieu_*): chỉ đọc hộ chiếu của chính người đề nghị (người nước ngoài). Dòng MRZ dùng để kiểm số hộ chiếu, mã quốc gia, ngày sinh, giới tính, ngày hết hạn (MRZ ghi yymmdd). Dấu kiểm chứng nhập cảnh (ARRIVAL / NHẬP CẢNH) cho HoChieu_NhapCanh_*; "Diện / Status" trên dấu là loại thị thực, KHÔNG phải mục đích nhập cảnh.

GIẤY CHỨNG NHẬN KẾT HÔN (KetHon_*): bảng hai cột Người chồng / Người vợ — đọc riêng từng cột, không đổi bên. Phần "CHỨNG THỰC BẢN SAO" không dùng cho field nào.

CCCD (Cccd_*): chỉ đọc thẻ căn cước của người BẢO LÃNH (công dân Việt Nam).

Không bịa thông tin thiếu; không chắc thì bỏ field. Không trả field UI như CongDan__fs*."""
