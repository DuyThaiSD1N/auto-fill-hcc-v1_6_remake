"""Prompt đặc thù cho "Thủ tục yêu cầu trợ giúp pháp lý" (2.000829).

Bố cục bám eForm thật "ĐƠN YÊU CẦU TRỢ GIÚP PHÁP LÝ" (tokhaidientu.moj.gov.vn, mẫu id 1899); danh sách diện lấy
từ chính option của cổng (schema.DIEN_OPTIONS) để LLM chọn đúng nhãn thay vì diễn giải.
"""

from app.pipelines.yeu_cau_tro_giup_phap_ly.process.schema import DIEN_OPTIONS, HINH_THUC_OPTIONS

_DIEN_LIST = "\n".join(f"  - {label}" for label in DIEN_OPTIONS.values())
_HINH_THUC_LIST = ", ".join(f"'{label}'" for label in HINH_THUC_OPTIONS)

EXTRA_RULES = f"""Thủ tục: Yêu cầu trợ giúp pháp lý (Bộ Tư pháp). Tờ khai trên cổng gồm:
  Kính gửi (tổ chức thực hiện trợ giúp pháp lý);
  phần "thông tin dành cho NGƯỜI ĐƯỢC TRỢ GIÚP pháp lý": họ tên, ngày sinh, giới tính, loại + số giấy tờ định
    danh, địa chỉ liên hệ (chi tiết + Tỉnh + Phường/xã — KHÔNG có cấp huyện), điện thoại, diện;
  phần "thông tin dành cho NGƯỜI YÊU CẦU trợ giúp pháp lý": họ tên, giấy tờ định danh, địa chỉ liên hệ, điện
    thoại, mối quan hệ với người được trợ giúp;
  nội dung vụ việc: tóm tắt yêu cầu, hình thức trợ giúp ({_HINH_THUC_LIST}), tài liệu gửi kèm.
Tờ khai KHÔNG có ô ngày cấp/nơi cấp giấy tờ — vẫn trả Ndd_NgayCap/Ndd_NoiCap để hệ thống chọn đúng loại thẻ.

Hồ sơ thường gồm:
- Văn bản chứng minh diện. Hay gặp nhất là "THÔNG BÁO VỀ TRỢ GIÚP PHÁP LÝ" (Mẫu số 03, TTLT 29/2025) của cơ
  quan tiến hành tố tụng (Cơ quan Cảnh sát điều tra, Viện kiểm sát, Tòa án) gửi Trung tâm Trợ giúp pháp lý
  Nhà nước; cũng có thể là giấy chứng nhận hộ nghèo/cận nghèo, giấy xác nhận khuyết tật, thẻ người có công…
- CCCD/căn cước của người được trợ giúp pháp lý (có thể thiếu).
- Đôi khi có ĐƠN YÊU CẦU TRỢ GIÚP PHÁP LÝ bản giấy (Mẫu 02-TP-TGPL).

PHÂN BIỆT VAI — theo TIÊU ĐỀ PHẦN, không theo số mục (đơn giấy các phiên bản đánh số I/II khác nhau):
1. NGƯỜI ĐƯỢC TRỢ GIÚP (Ndd_*) = người mà Thông báo đề nghị cử người trợ giúp ("… cho Người bị buộc tội: …",
   khối "Họ và tên / Ngày tháng năm sinh / Nơi thường trú / Nơi cư trú / Thẻ CCCD" ngay dưới câu đề nghị)
   = phần "dành cho người được trợ giúp pháp lý" của Đơn.
2. Điều tra viên/Kiểm sát viên/Thẩm phán ký Thông báo, cơ quan ở "Nơi nhận", người ghi sổ công văn đến KHÔNG
   phải người được trợ giúp cũng KHÔNG phải người yêu cầu. Không lấy tên, chức vụ, cấp bậc của họ.
3. NGƯỜI YÊU CẦU (Nyc_*) chỉ lấy từ phần "dành cho người yêu cầu trợ giúp pháp lý" của Đơn bản giấy. Không
   có Đơn thì bỏ toàn bộ Nyc_*: cổng tự điền người yêu cầu theo tài khoản đăng nhập. Cơ quan tố tụng gửi
   Thông báo KHÔNG phải người yêu cầu.

NGUỒN VÀ ƯU TIÊN:
- Họ tên, ngày sinh, giới tính, số định danh: CCCD > Thông báo > Đơn. Họ tên đúng dấu tiếng Việt.
- Giới tính trên Thông báo/Đơn là ô được tích (☑/✓/x) cạnh "Nam"/"Nữ"; ô trống (☐/□) không tính.
- Ngày cấp, nơi cấp: chép đúng giấy ghi ("cấp ngày 18 tháng 6 năm 2023" → "18/06/2023"); không suy nơi cấp.
- Ndd_DiaChiLienHe là nơi ĐANG Ở (Thông báo "Nơi cư trú" — có thể là trại tạm giam, trường giáo dưỡng), KHÁC
  Ndd_ThuongTru (Thông báo "Nơi thường trú" / CCCD). Địa chỉ "Thôn A, xã B, tỉnh C" →
  {{quocGia:"Việt Nam", tinh:"Tỉnh C", xa:"Xã B", diaChi:"Thôn A"}}; "TP." là "Thành phố"; tên cơ sở (trại
  giam, trường giáo dưỡng) đi vào diaChi cùng thôn/xóm.
- Ndd_Dien chọn đúng MỘT nhãn trong <dien_options>:
  + "Người bị buộc tội/bị can/bị cáo từ 16 tuổi đến dưới 18 tuổi" → "…là người bị buộc tội"; người bị hại,
    người làm chứng, người bị tố giác, bị kiến nghị khởi tố, bị giữ khẩn cấp, phạm nhân 16–18 tuổi chọn đúng
    vai tương ứng.
  + "Người bị buộc tội thuộc hộ cận nghèo" chỉ khi vừa bị buộc tội vừa thuộc hộ cận nghèo.
  + "Trẻ em" chỉ khi giấy tờ ghi trẻ em / dưới 16 tuổi. "Không thuộc diện" chỉ khi giấy tờ ghi đúng như vậy.
  + Không khớp nhãn nào → chép nguyên văn dòng diện; giấy tờ không nói diện → bỏ field, KHÔNG tự suy theo tuổi.
- YeuCau_ToChucTGPL lấy dòng "Kính gửi" (hoặc "Đề nghị … cử người") của Thông báo/Đơn, chép nguyên văn; không có
  thì bỏ, không tự đặt tên Trung tâm.
- YeuCau_GiaiDoan chỉ gồm các ô ĐƯỢC TÍCH. Ô vuông trống không lấy.
- Mọi ngày dd/mm/yyyy. Không bịa số điện thoại, quan hệ, hình thức hay dữ liệu giấy tờ không ghi.

<dien_options>
{_DIEN_LIST}
</dien_options>

KHÔNG trả field UI của eForm (NguoiDuocTGPL_*, HoVaTenC…). Chỉ trả field compact trong schema."""
