"""Luật riêng của thủ tục Cấp thẻ căn cước cho người từ đủ 14 tuổi trở lên cho compact agent."""

EXTRA_RULES = """Đầu vào thường gồm:
1. Phiếu thu nhận thông tin căn cước (Mẫu CC01): mục 1–6 nhân thân người cần cấp, mục 18–19 số điện thoại / thư điện
   tử, bảng mục 20 (cha, mẹ, người đại diện hợp pháp), mục 22 loại cấp, mục 23 đơn vị lập, người ký "NGƯỜI KHAI".
2. Phiếu thu thập thông tin dân cư (Mẫu DC01): đầu phiếu Tỉnh/thành phố + Xã/phường, mục 1–5, 13 nhân thân, bảng mục
   14 người thân, người ký "NGƯỜI KÊ KHAI/NGƯỜI KÊ KHAI HỘ".
3. Giấy khai sinh (bản sao) của người cần cấp — họ tên, ngày sinh, giới tính; họ tên cha, mẹ.
4. Thẻ bảo hiểm y tế (nếu đề nghị tích hợp) — chỉ để đối chiếu họ tên, ngày sinh.
5. Bìa hồ sơ (nếu có): người đề nghị, số định danh, loại cấp, cơ quan tiếp nhận.

<critical_rules>
- NguoiCanCap_* là người từ đủ 14 tuổi được cấp thẻ (mục 1 CC01 / DC01). Mã số thẻ BHYT KHÔNG phải số định danh.
- Số CMND 9 số (cột "Số CMND 09 số", mục 6 CC01, mục 13 DC01) KHÔNG phải số định danh. NguoiCanCap_SoCMND chỉ lấy
  số của CHÍNH người cần cấp, KHÔNG lấy số CMND của cha, mẹ trong bảng người thân.
- NguoiDaiDien_* CHỈ khi người ký "NGƯỜI KHAI" / "NGƯỜI KÊ KHAI HỘ" hoặc "Người đề nghị" bìa hồ sơ là người KHÁC người
  cần cấp. Người cần cấp tự ký → mọi NguoiDaiDien_* bỏ trống; KHÔNG lấy cha, mẹ ở bảng mục 20 CC01 điền vào đây.
- Cha_* / Me_* chép đủ cả họ tên lẫn số định danh của cha, mẹ ở bảng người thân CC01 / DC01 (và Giấy khai sinh).
- Không bịa thông tin còn thiếu. Ô để trống, chấm chấm ("……") hoặc gạch ngang là KHÔNG có dữ liệu.
</critical_rules>

<field_rules>
- Số định danh 12 chữ số: ghép liền, bỏ khoảng trắng.
- Ngày sinh dd/mm/yyyy.
- Cơ quan tiếp nhận theo địa giới MỚI (Giấy khai sinh ghi địa giới cũ như "huyện …" thì theo CC01 / DC01 / bìa hồ sơ).
</field_rules>"""
