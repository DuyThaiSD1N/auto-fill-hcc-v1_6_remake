"""Luật riêng của thủ tục Cấp thẻ căn cước cho người dưới 14 tuổi cho compact agent."""

EXTRA_RULES = """Đầu vào thường gồm:
1. Phiếu thu nhận thông tin căn cước (Mẫu CC01) của trẻ: mục 1–5 nhân thân trẻ, mục 13 nơi thường trú, bảng mục 20
   (cha, mẹ, người đại diện hợp pháp), mục 23 đơn vị lập, người ký "NGƯỜI ĐẠI DIỆN HỢP PHÁP".
2. Phiếu thu thập thông tin dân cư (Mẫu DC01): đầu phiếu Tỉnh/thành phố + Xã/phường, mục 1–5 nhân thân trẻ, bảng mục 14
   người thân, mục 17 nơi thường trú, người ký "NGƯỜI KÊ KHAI/NGƯỜI KÊ KHAI HỘ".
3. Giấy khai sinh (bản sao) của trẻ — họ tên, ngày sinh, giới tính trẻ; họ tên cha, mẹ.
4. Thẻ căn cước của người đại diện hợp pháp (cha/mẹ) — đối chiếu họ tên, số định danh người kê khai.
5. Bìa hồ sơ (nếu có): người được cấp thẻ, người đại diện hợp pháp, cơ quan tiếp nhận, hình thức nhận kết quả.

<critical_rules>
- NguoiCanCap_* là TRẺ dưới 14 tuổi (chủ thể được cấp thẻ). Trẻ chưa có thẻ căn cước: KHÔNG lấy họ tên, ngày sinh, số
  định danh trên thẻ căn cước nộp kèm (thẻ đó của cha/mẹ) điền vào NguoiCanCap_*.
- NguoiDaiDien_* là cha/mẹ/người đại diện hợp pháp kê khai thay. Số CMND 9 số (cột "Số CMND 09 số", "Chứng minh nhân
  dân số") KHÔNG phải số định danh.
- NguoiDaiDien_QuanHe ghi "Mẹ – người đại diện hợp pháp" → trả "Mẹ"; "Cha – người đại diện hợp pháp" → "Cha". Chỉ
  trả "Người đại diện hợp pháp" khi người kê khai không phải cha, mẹ (vd người giám hộ).
- Cha_* / Me_* chép đủ cả họ tên lẫn số định danh của cha, mẹ ở bảng người thân CC01 / DC01 (và Giấy khai sinh), kể cả
  khi người kê khai chỉ là một trong hai người.
- Không bịa thông tin còn thiếu. Ô để trống, chấm chấm ("……") hoặc gạch ngang là KHÔNG có dữ liệu.
</critical_rules>

<field_rules>
- Số định danh 12 chữ số: ghép liền, bỏ khoảng trắng.
- Ngày sinh dd/mm/yyyy.
- Cơ quan tiếp nhận và địa chỉ nhận kết quả theo địa giới MỚI (Giấy khai sinh / thẻ căn cước ghi địa giới cũ như
  "thành phố …, huyện …" thì theo CC01 / DC01 / bìa hồ sơ).
- NhanKetQua_DiaChiChiTiet CHỈ phần dưới cấp xã (vd "Số 8, tổ dân phố số 3"), bỏ tên xã/phường, tỉnh.
</field_rules>"""
