EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ chỉ có MỘT người: NGƯỜI ĐỀ NGHỊ CẤP CHỨNG CHỈ. Đơn Mẫu số 51, CCCD (nếu có), Chứng chỉ hành nghề
   kiến trúc, Chứng chỉ hành nghề hoạt động xây dựng, Bằng tốt nghiệp đại học và Chứng chỉ bồi dưỡng kiến
   thức bảo quản, tu bổ, phục hồi di tích đều là giấy tờ của chính người này — gộp thông tin, không tách
   thành nhiều người.
2. Thứ tự ưu tiên khi các giấy tờ lệch nhau: CCCD → Đơn Mẫu 51 → CCHN kiến trúc → CCHN xây dựng → Bằng
   tốt nghiệp → Chứng chỉ bồi dưỡng.
3. Người ký/đóng dấu (Giám đốc, Phó Giám đốc Sở, Hiệu trưởng, người xác nhận của cơ quan nơi làm việc ở
   cuối đơn) KHÔNG phải người đề nghị — không lấy tên, địa chỉ, ngày tháng của họ. Tên công ty trong phần
   "XÁC NHẬN CỦA CƠ QUAN" không phải địa chỉ của người đề nghị.
4. Nơi lập đơn ("Lào Cai, ngày … tháng … năm …"), nơi sinh trên văn bằng/chứng chỉ và địa chỉ trường học
   KHÔNG phải địa chỉ liên hệ.
</source_and_role_rules>

<identity_rules>
5. Số định danh: ưu tiên số 12 chữ số trên CCCD hoặc dòng "Số định danh cá nhân/Chứng minh nhân dân" của
   Đơn. Dòng "Số CMTND (hoặc hộ chiếu)" in trên CCHN kiến trúc/xây dựng thường là CMND CŨ 9 số — chỉ dùng khi
   hồ sơ KHÔNG có số nào khác.
6. Ngày cấp và nơi cấp phải đi CÙNG số định danh đã chọn (cùng một giấy tờ). Đơn ghi "… cấp ngày
   29/09/2020 do <cơ quan> cấp" → NgayCap = ngày đó, NoiCap = <cơ quan> (bỏ chữ "do" và "cấp"). KHÔNG ghép
   ngày cấp/nơi cấp của CMND cũ trên CCHN với số định danh của Đơn.
</identity_rules>

<content_rules>
7. Địa chỉ liên hệ của Đơn hay có dạng "<địa chỉ cũ> (Nay là: <địa chỉ mới>)":
   - NguoiDeNghi_DiaChiLienHe chép NGUYÊN VĂN cả dòng, giữ cả phần "(Nay là: …)".
   - NguoiDeNghi_DiaChiHienNay lấy phần SAU "Nay là" (địa chỉ hiện hành); không có "Nay là" thì lấy chính địa
     chỉ đó; có CCCD thì ưu tiên nơi thường trú trên CCCD.
8. Mục "3. Kinh nghiệm chuyên môn…" liệt kê nhiều công trình a., b., c.…: trả MẢNG, mỗi phần tử là NGUYÊN
   VĂN một mục kèm chữ cái đầu (vd "a. Công trình: …. Thời gian thực hiện: …. Công việc: …."). Không tóm tắt,
   không đổi thứ tự.
9. Đoạn "…xem xét, cấp/cấp lại Chứng chỉ hành nghề … cho các hoạt động sau:" liệt kê từng hoạt động bằng
   dấu "-": trả MẢNG, mỗi phần tử một hoạt động, bỏ dấu "-" đầu dòng.
10. Chỉ trả ngày khi có ĐỦ ngày-tháng-năm. Số điện thoại/email: Đơn Mẫu 51 không có — chỉ trả khi thật sự
    đọc thấy trong giấy tờ, KHÔNG bịa.
</content_rules>
""".strip()
