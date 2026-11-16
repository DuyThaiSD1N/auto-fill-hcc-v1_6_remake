"""Luật riêng của thủ tục Cấp lại thẻ căn cước cho compact agent."""

from app.pipelines.cap_lai_the_can_cuoc.process.schema import REASONS

_REASON_LINES = "\n".join(f"  - {label}" for label, _ in REASONS)

EXTRA_RULES = f"""Đầu vào thường gồm:
1. Phiếu đề nghị giải quyết thủ tục về căn cước (Mẫu DC02) — nguồn chính: "Kính gửi (1)", mục I người đề nghị (người
   cần cấp lại), mục II người đại diện thực hiện thủ tục (nếu có), mục III.7 nội dung cụ thể, mục IV địa chỉ nhận kết quả.
2. Phiếu thu nhận thông tin căn cước (Mẫu CC01): số thuê bao di động, thư điện tử, bảng mục 20 (cha, mẹ, vợ, chồng,
   người đại diện), loại cấp, đơn vị lập.
3. Bìa hồ sơ (nếu có): cơ quan tiếp nhận, lý do cấp lại, hình thức nhận kết quả.
Thẻ cũ đã mất / hỏng nên thường KHÔNG có ảnh thẻ; nhân thân lấy theo DC02 mục I và CC01.

<critical_rules>
- NguoiCanCap_* là người ở mục I DC02 (chủ thể được cấp lại thẻ), đối chiếu CC01 của CHÍNH người đó.
- NguoiDaiDien_* CHỈ lấy từ mục II DC02. Mục II để trống / chấm chấm → mọi NguoiDaiDien_* bỏ trống; KHÔNG lấy cha, mẹ ở
  bảng mục 20 CC01 điền vào đây.
- Số điện thoại / email ở mục II DC02 là của người đại diện, KHÔNG dùng cho NguoiCanCap_*.
- LyDoCap phải chép NGUYÊN VĂN một nhãn trong danh sách:
{_REASON_LINES}
  Thẻ bị mất / đánh rơi / thất lạc → nhãn "do mất thẻ căn cước"; thẻ hỏng, gãy, mờ chíp → nhãn "bị hư hỏng".
- Không bịa thông tin còn thiếu. Ô để trống, chấm chấm ("……") hoặc gạch ngang là KHÔNG có dữ liệu.
</critical_rules>

<field_rules>
- Số định danh 12 chữ số: ghép liền, bỏ khoảng trắng. Số CMND 9 số (CC01 mục 6) KHÔNG phải số định danh.
- Ngày sinh dd/mm/yyyy.
- Cơ quan tiếp nhận và địa chỉ nhận kết quả theo địa giới MỚI.
- NhanKetQua_DiaChiChiTiet CHỈ phần dưới cấp xã (vd "Số 8, tổ dân phố số 3"), bỏ tên xã/phường, tỉnh.
</field_rules>"""
