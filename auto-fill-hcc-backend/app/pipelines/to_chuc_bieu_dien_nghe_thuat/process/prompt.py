EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ của MỘT tổ chức đề nghị (công ty, đơn vị nghệ thuật). Giấy tờ: Văn bản đề nghị tổ chức biểu diễn nghệ
   thuật (Mẫu số 02, NĐ 144/2020/NĐ-CP — "Kính gửi: Sở Văn hóa…", các mục đánh số 1–6) là nguồn chính; Kịch bản
   / nội dung chi tiết chương trình (bảng thời gian – hoạt động – tiết mục); có thể có Giấy chứng nhận đăng ký
   doanh nghiệp, giấy tiếp nhận/chấp thuận địa điểm, CCCD của người đi nộp.
2. DonVi_* là TỔ CHỨC đề nghị. "Người chịu trách nhiệm chính nội dung" (giám đốc…) và người ký là CÁ NHÂN: tên,
   chức vụ, số CCCD, địa chỉ của họ KHÔNG phải của tổ chức. Người đi nộp trên CCCD cũng không phải tổ chức.
3. Địa điểm biểu diễn, địa điểm duyệt chương trình, địa chỉ nơi tiếp nhận địa điểm KHÔNG phải trụ sở tổ chức.
   Nơi lập văn bản ("Thành phố …, ngày … tháng … năm …") không phải địa điểm tổ chức.
</source_and_role_rules>

<content_rules>
4. DeNghi_* CHỈ lấy trên Văn bản đề nghị, đúng mục đánh số; KichBan_* CHỈ lấy trên Kịch bản. Hai giấy ghi lệch
   nhau (ngày, địa điểm, dấu câu của tên chương trình) thì trả CẢ HAI đúng như từng giấy ghi, không sửa cho khớp.
5. Thời gian chép NGUYÊN VĂN, giữ cả giờ và MỌI ngày ("ngày 05, 06 tháng 12 năm 2026" → giữ cả 05 và 06), giữ
   cả lỗi gõ dính chữ. Không tự đổi sang dd/mm/yyyy.
6. Mục 6 ghi "(Không có)" thì chép đúng "(Không có)"; dòng không có trên giấy thì bỏ field.
7. Mã số trên con dấu chạy vòng quanh dấu, hay bị chữ đè: chép đúng chữ số đọc được, thiếu số thì để thiếu,
   KHÔNG bù. Số điện thoại/email: chỉ trả khi thật sự đọc thấy của TỔ CHỨC, KHÔNG bịa.
</content_rules>

<reminder>Có Văn bản đề nghị thì BẮT BUỘC trả DeNghi_TenChuongTrinh, DeNghi_ThoiGian, DeNghi_DiaDiem,
DeNghi_NguoiChiuTrachNhiem, DeNghi_TaiLieuKemTheo — đừng dừng sau khi trả xong DonVi_*.</reminder>
""".strip()
