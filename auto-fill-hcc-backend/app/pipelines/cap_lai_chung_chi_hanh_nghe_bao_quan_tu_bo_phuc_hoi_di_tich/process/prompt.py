EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ chỉ có MỘT người: NGƯỜI ĐỀ NGHỊ CẤP LẠI CHỨNG CHỈ. Đơn đề nghị cấp lại (Mẫu số 51), Chứng chỉ hành nghề
   bảo quản, tu bổ, phục hồi di tích ĐÃ CẤP (chứng chỉ cũ), CCCD (nếu có), bằng tốt nghiệp, chứng chỉ bồi dưỡng,
   Chứng chỉ hành nghề hoạt động xây dựng/kiến trúc đều là giấy tờ của chính người này — gộp thông tin, không tách
   thành nhiều người.
2. Thứ tự ưu tiên mặc định: CCCD → Đơn → Chứng chỉ đã cấp → Bằng tốt nghiệp → Chứng chỉ bồi dưỡng → CCHN xây
   dựng. Ngoại lệ: địa chỉ liên hệ, điện thoại, trình độ chuyên môn, kinh nghiệm lấy ĐƠN trước; số và ngày cấp
   của chứng chỉ cũ lấy CHỨNG CHỈ ĐÃ CẤP trước rồi mới tới đoạn "Lý do cấp lại" của Đơn.
3. Người ký/đóng dấu (Giám đốc, Phó Giám đốc Sở, Hiệu trưởng, công chứng viên, người ký số của Sở) KHÔNG phải
   người đề nghị — không lấy tên, địa chỉ, ngày tháng của họ.
4. Nơi lập đơn ("<Tỉnh>, ngày … tháng … năm …"), nơi sinh trên văn bằng và địa chỉ trường học KHÔNG phải địa chỉ
   liên hệ. Địa chỉ thường trú in trên chứng chỉ cũ là địa chỉ CŨ — chỉ dùng khi Đơn và CCCD đều không có.
</source_and_role_rules>

<identity_rules>
5. Số định danh: ưu tiên số 12 chữ số trên CCCD hoặc dòng "Căn cước công dân: số …" của Đơn. Số CMND cũ 9 số in
   trên chứng chỉ đã cấp / CCHN xây dựng chỉ dùng khi hồ sơ KHÔNG có số nào khác.
6. Ngày cấp và nơi cấp phải đi CÙNG số định danh đã chọn (cùng một giấy tờ). Đơn ghi "… số 001090012345, cấp
   ngày 01/02/2022 tại Cục QLHC về TTXH" → NgayCap = 01/02/2022, NoiCap = "Cục QLHC về TTXH" (bỏ chữ "tại"/"do",
   "cấp"). KHÔNG ghép ngày/nơi cấp của CMND cũ trên chứng chỉ với số định danh của Đơn.
</identity_rules>

<content_rules>
7. NguoiDeNghi_DiaChiLienHe chép NGUYÊN VĂN dòng "Địa chỉ liên hệ" của Đơn (giữ cả phần "(Nay là: …)" nếu có).
   NguoiDeNghi_DiaChiHienNay tách từ chính địa chỉ đó (phần sau "Nay là" nếu có); Đơn không ghi thì lấy nơi
   thường trú trên CCCD.
8. NguoiDeNghi_TrinhDoChuyenMon: mục "2. Trình độ chuyên môn" của Đơn, mỗi dòng "+ …" là MỘT phần tử của MẢNG,
   chép NGUYÊN VĂN cả dấu "+" đầu dòng. Không tóm tắt.
9. NguoiDeNghi_KinhNghiem: mục "3. Kinh nghiệm chuyên môn…" của Đơn, trả MẢNG theo đúng thứ tự trên đơn:
   - mỗi dòng gạch đầu dòng ("- Thời gian có kinh nghiệm nghề nghiệp: …", "- Đơn vị công tác: …", "- Quá trình
     hoạt động chuyên môn …:") là một phần tử nguyên văn;
   - mỗi HÀNG của bảng quá trình công tác là một phần tử, các cột nối bằng " | " theo thứ tự cột trên đơn, mở đầu
     bằng số thứ tự (vd "01. Tháng 03/2024 | Công ty Mẫu A | Thi công tu bổ đình Mẫu | Ban quản lý di tích Mẫu");
   - đơn liệt kê kiểu a., b., c. thì mỗi mục một phần tử, giữ chữ cái đầu.
   Bảng tràn sang trang sau vẫn là cùng một bảng — lấy ĐỦ mọi hàng.
10. Don_LyDoCapLai: đoạn sau "Lý do cấp lại" của Đơn, chép NGUYÊN VĂN, bỏ dấu "+"/"-" đầu dòng.
11. Don_HoatDongDeNghi: các hoạt động liệt kê sau "…cấp lại Chứng chỉ hành nghề … cho các hoạt động sau:", MẢNG,
    mỗi phần tử một hoạt động, bỏ dấu "+"/"-" đầu dòng.
12. ChungChiCu_*: lấy trên CHỨNG CHỈ ĐÃ CẤP (giấy do Sở Văn hóa… cấp, có "Số chứng chỉ", "Được phép hành nghề",
    "Chứng chỉ có giá trị … đến ngày"). Ngày cấp = dòng "<Tỉnh>, ngày …" ký cấp, KHÔNG phải ngày cấp CMND in trên
    chứng chỉ. Không thấy chứng chỉ thì lấy số/ngày nêu trong "Lý do cấp lại" của Đơn.
13. Chỉ trả ngày khi có ĐỦ ngày-tháng-năm; chữ số bị mờ/che không đọc chắc thì BỎ field, KHÔNG đoán. Số điện
    thoại/email chỉ trả khi thật sự đọc thấy, KHÔNG bịa.
</content_rules>
""".strip()
