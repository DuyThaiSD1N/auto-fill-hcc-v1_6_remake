EXTRA_RULES = """
<source_and_role_rules>
1. Hồ sơ chỉ có MỘT người: NGƯỜI ĐỀ NGHỊ CẤP LẠI THẺ. Đơn đề nghị (Mẫu số 05; hồ sơ nộp nhầm có thể là
   đơn cấp mới Mẫu số 04/06), CCCD, chứng chỉ nghiệp vụ hướng dẫn du lịch, văn bằng, thẻ hướng dẫn viên du
   lịch cũ (nếu còn) đều là giấy tờ của chính người này — gộp thông tin, không tách thành nhiều người.
2. Thứ tự ưu tiên khi các giấy tờ lệch nhau:
   - Họ tên, ngày sinh, giới tính, số định danh, ngày cấp, nơi cấp CCCD, địa chỉ: CCCD → Đơn → chứng chỉ
     nghiệp vụ → văn bằng → thẻ HDV cũ.
   - Số thẻ, nơi cấp thẻ, ngày cấp thẻ, loại thẻ đã được cấp: mục 'Đã được cấp thẻ hướng dẫn viên du lịch'
     của Đơn Mẫu 05 → thẻ HDV cũ (thẻ cấp lại thường đã mất nên đơn là nguồn chính).
   - Điện thoại, email, lý do cấp lại: CHỈ lấy từ Đơn.
3. HAI BỘ "ngày cấp / nơi cấp" KHÁC NHAU: của CCCD (NguoiDeNghi_NgayCap/NoiCap) và của THẺ HDV cũ
   (TheCu_NgayCap/NoiCap). Không đổ chéo. Chứng chỉ nghiệp vụ in 'Ngày cấp … Nơi cấp …' ngay cạnh số CCCD
   là của CCCD. Ngày HẾT HẠN in trên thẻ, ngày ký chứng chỉ/văn bằng không phải ngày cấp thẻ.
4. Người ký trên chứng chỉ/văn bằng/thẻ (Hiệu trưởng, Giám đốc Sở…) và người thực hiện chứng thực KHÔNG
   phải người đề nghị — không lấy tên, địa chỉ, ngày tháng của họ.
5. Địa danh ở nơi lập đơn ('Thành phố Đà Nẵng, ngày … tháng … năm …'), trên dấu chứng thực hay địa chỉ
   trường học KHÔNG phải địa chỉ của người đề nghị.
</source_and_role_rules>

<masked_and_missing_rules>
6. Bản scan hay bị che/làm mờ một phần (họ tên chỉ còn họ đệm, số định danh chỉ còn vài số đầu, số
   điện thoại cụt, email mất phần tên hộp thư). Chép ĐÚNG phần đọc được; TUYỆT ĐỐI không bù chữ số,
   không bịa phần tên bị che.
7. Chỉ trả ngày khi có ĐỦ ngày-tháng-năm; mất năm thì bỏ field.
8. 'Số hiệu chứng chỉ' (vd dạng 'CMS./HDDLNĐ-…'), 'Số vào sổ', số hiệu văn bằng ('DND.6.…', 'Reg. No.')
   KHÔNG phải số thẻ HDV. Đơn không ghi số thẻ và không có ảnh thẻ cũ thì BỎ TheCu_SoThe, TheCu_NgayCap,
   TheCu_NoiCap.
9. Loại thẻ đã được cấp (TheCu_Loai): ô '□' rỗng là KHÔNG chọn; chỉ trả khi thấy rõ ô được đánh dấu
   (☒, ☑, ✓, x) hoặc chữ in trên thẻ cũ. Tiêu đề đơn cấp MỚI ('Cấp thẻ hướng dẫn viên du lịch nội địa')
   và tên chứng chỉ nghiệp vụ là loại thẻ ĐỀ NGHỊ cấp, không phải thẻ đã được cấp → đưa vào
   Don_LoaiTheDeNghi, KHÔNG đưa vào TheCu_Loai.
10. Dòng 'Hướng dẫn ghi: (1) Quốc tế, nội địa hoặc tại điểm… (2) Tên điểm du lịch…' in sẵn cuối đơn là chú
    thích mẫu, KHÔNG phải giá trị. Dòng chấm để trống thì bỏ field.
</masked_and_missing_rules>

<normalization_rules>
11. Địa chỉ trả về object {quocGia, tinh, xa, diaChi}. Chuỗi viết liền '<số nhà, đường/thôn>, <xã/phường>,
    <tỉnh/thành phố>': cụm CUỐI là tinh, cụm ngay TRƯỚC là xa, phần còn lại cho vào diaChi.
12. Số điện thoại/số định danh chỉ giữ chữ số. Không có trong giấy tờ thì BỎ FIELD.
</normalization_rules>
""".strip()
