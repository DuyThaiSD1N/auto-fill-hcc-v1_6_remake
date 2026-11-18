"""Luật prompt riêng cho thủ tục 2.001428 — Đăng ký mẫu con dấu mới (thực hiện tại cấp tỉnh)."""

EXTRA_RULES = """Hồ sơ đăng ký mẫu con dấu mới của cơ quan, tổ chức, thường gồm: Văn bản đề nghị đăng ký mẫu con dấu (Mẫu số 03, có các mục 1–6); Quyết định thành lập / cho phép hoạt động của cơ quan, tổ chức; văn bản của cơ quan có thẩm quyền đồng ý cho khắc dấu (vd công văn của Ban Tổ chức cấp ủy cấp trên); có khi kèm thẻ căn cước/CCCD của người đi nộp. Mỗi field có tiền tố theo giấy (Cccd_, VanBan_, QuyetDinh_, CongVan_): CHỈ đọc field từ đúng giấy đó, giấy nào không có trong hồ sơ thì bỏ hết field của nó.

VĂN BẢN ĐỀ NGHỊ (VanBan_*):
- Đọc đúng mục theo số thứ tự: mục 1 là cơ quan, tổ chức đề nghị; mục 2 người đứng đầu; mục 3 cơ quan quản lý trực tiếp (KHÔNG dùng cho field nào); mục 4 danh sách nhiều con dấu (bỏ qua); mục 5 nội dung đề nghị + lý do + tài liệu kèm theo; mục 6 người được giới thiệu/ủy quyền nộp hồ sơ.
- Dòng để trống (chỉ có nhãn, dấu ":" rồi hết, hoặc chấm chấm) → bỏ field, không ghi "Không" hay "Trống".
- Người đứng đầu (mục 2) và người nộp (mục 6) thường là một người nhưng vẫn đọc riêng từng mục theo đúng mục.

QUYẾT ĐỊNH (QuyetDinh_*) và CÔNG VĂN (CongVan_*): văn bản có chữ "QUYẾT ĐỊNH" ở giữa trang là quyết định; văn bản có dòng "V/v ..." dưới số văn bản là công văn. Văn bản đề nghị cũng có dòng "V/v đề nghị đăng ký mẫu con dấu" nhưng KHÔNG phải công văn đồng ý khắc dấu → không đọc CongVan_* từ văn bản đề nghị.

CCCD (Cccd_*): chỉ đọc thẻ của người được giới thiệu nộp hồ sơ (họ tên trùng mục 6, hoặc mục 2 khi không có mục 6). Thẻ của người khác → bỏ hết Cccd_*.

Không bịa thông tin thiếu; không chắc thì bỏ field. Không trả field UI như CongDan__fs*."""
