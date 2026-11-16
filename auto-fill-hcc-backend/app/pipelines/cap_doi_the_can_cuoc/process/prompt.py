"""Luật riêng của thủ tục Cấp đổi thẻ căn cước cho compact agent."""

from app.pipelines.cap_doi_the_can_cuoc.process.schema import REASONS

_REASON_LINES = "\n".join(f"  - {label}" for label, _ in REASONS)

EXTRA_RULES = f"""Đầu vào thường gồm:
1. Phiếu đề nghị giải quyết thủ tục về căn cước (Mẫu DC02) — nguồn chính: "Kính gửi (1)", mục I người đề nghị (người
   cần cấp đổi), mục II người đại diện thực hiện thủ tục (nếu có), mục III.7 nội dung cụ thể, mục IV địa chỉ nhận kết quả.
2. Phiếu thu nhận thông tin căn cước (Mẫu CC01): số thuê bao di động, thư điện tử, bảng mục 20 (cha, mẹ, vợ, chồng,
   người đại diện), đơn vị lập.
3. Thẻ Căn cước công dân / thẻ căn cước đang sử dụng — đối chiếu họ tên, ngày sinh, giới tính, số định danh.
4. Bìa hồ sơ (nếu có): cơ quan tiếp nhận, lý do cấp đổi, hình thức nhận kết quả.

<critical_rules>
- NguoiCanCap_* là người ở mục I DC02 (chủ thể được cấp đổi thẻ), đối chiếu thẻ CCCD và CC01 của CHÍNH người đó.
- NguoiDaiDien_* CHỈ lấy từ mục II DC02. Mục II để trống / chấm chấm → mọi NguoiDaiDien_* bỏ trống; KHÔNG lấy cha, mẹ ở
  bảng mục 20 CC01 điền vào đây.
- Số điện thoại / email ở mục II DC02 là của người đại diện, KHÔNG dùng cho NguoiCanCap_*.
- LyDoCap phải chép NGUYÊN VĂN một nhãn trong danh sách:
{_REASON_LINES}
  Thẻ hết hạn vì công dân đến tuổi đổi thẻ → nhãn "đủ … tuổi" tương ứng (14, 25, 40, 60).
- Không bịa thông tin còn thiếu. Ô để trống, chấm chấm ("……") hoặc gạch ngang là KHÔNG có dữ liệu.
</critical_rules>

<field_rules>
- Số định danh 12 chữ số: ghép liền, bỏ khoảng trắng. Số CMND 9 số KHÔNG phải số định danh.
- Ngày sinh dd/mm/yyyy.
- Cơ quan tiếp nhận và địa chỉ nhận kết quả theo địa giới MỚI (giấy ghi cả địa giới cũ như "Thành phố …, Huyện …" của
  thẻ CCCD cũ thì theo DC02 / CC01).
- NhanKetQua_DiaChiChiTiet CHỈ phần dưới cấp xã (vd "Số 8, tổ dân phố số 3"), bỏ tên xã/phường, tỉnh.
</field_rules>"""
