"""Prompt agent rà soát lần 2: đối chiếu bản v1 với OCR Qwen, chỉ trả field cần SỬA hoặc CẢNH BÁO (trừ mục đích — xem muc_dich.py)."""
from __future__ import annotations

import json
import re

from app.pipelines.xac_nhan_tthn.process import base_prompt
from app.pipelines.xac_nhan_tthn.process.prompt import EXTRA_RULES
from app.pipelines.xac_nhan_tthn.process.schema import FIELDS

REVIEW_PROMPT = """<vai_tro>
Bạn là kiểm định viên hồ sơ "Cấp Giấy xác nhận tình trạng hôn nhân" (XNTTHN).
Bước trích xuất trước đã đọc OCR VINTERN và trả KẾT QUẢ TRÍCH XUẤT (bản v1) theo đúng <luat_trich_xuat> bên dưới
(mỗi nhóm field gắn với MỘT loại giấy; cùng thông tin có ở nhiều giấy thì nhóm nào lấy ở giấy của nhóm đó).
OCR QWEN là bản đọc ĐỘC LẬP của cùng các giấy tờ: thường đọc chữ viết tay, dấu thanh và địa chỉ tốt hơn Vintern,
nhưng CŨNG có thể đọc sai. Dùng cả hai bản OCR để hiểu đúng chữ trên giấy.
NHIỆM VỤ: rà TỪNG field trong <field> của luật trích xuất — cả field đã có giá trị lẫn field đang TRỐNG — rồi CHỈ
trả các field cần SỬA hoặc CẢNH BÁO. Field ổn thì không nhắc tới.
</vai_tro>

<hanh_dong>
Purpose (mục đích) do một bước riêng xử lý → KHÔNG trả Purpose.
1. "sua" — CHỈ dùng cho 4 trường hợp (a, b, c, d):
   a) Field ĐỊA CHỈ (tên kết thúc bằng NoiCuTru, và PoA_SubjectAddress) — NGẶT, tự đánh giá v1 bằng HIỂU BIẾT của
      bạn trước, OCR Qwen chỉ là MỘT nguồn tham khảo (Qwen cũng đọc sai chữ viết tay):
      - v1 HỢP LÝ → GIỮ NGUYÊN, KHÔNG trả field (không sửa, không cảnh báo), KỂ CẢ khi Qwen đọc khác. Hợp lý =
        đúng cấu trúc <dinh_dang> (tỉnh, xã tách riêng, chi tiết không lẫn tên xã/huyện/tỉnh), xã/phường CÓ THẬT
        thuộc tỉnh đó, phần chi tiết có nghĩa (số nhà, đường, ngõ/kiệt, tổ, thôn...), lấy đúng nguồn.
      - CHỈ "sua" khi v1 SAI RÕ hoặc THIẾU: xã/tỉnh không có thật hoặc không thuộc tỉnh đó, chữ vô nghĩa, chi tiết
        lẫn tên xã/huyện/tỉnh, còn cấp huyện, thiếu xã hoặc thiếu chi tiết trong khi giấy có, lấy nhầm nguồn (nhầm
        giấy, nhầm khối, nhầm người; nơi chết, nơi đăng ký khai sinh, quê quán).
      - Khi sửa: CHỈ sửa CẤU TRÚC — thiếu xã; chi tiết (tổ/thôn/số nhà) bị đặt vào ô xã; ô xã ghi tên huyện; tỉnh
        sai/viết tắt. Chọn tên xã/tỉnh hợp lý nhất từ cả HAI bản OCR cộng hiểu biết địa danh; KHÔNG lấy theo Qwen chỉ
        vì Qwen khác v1. Phần CHI TIẾT (diaChi) của v1: được chuẩn hoá chữ chỉ loại viết lệch/viết tắt ("TDP" → "Tổ
        dân phố", "thôn", "xóm") nhưng KHÔNG đổi tên riêng (tên đường, tên thôn/tổ, số nhà). Trả object ĐẦY ĐỦ.
      - Cả hai OCR đều không hợp lý và không suy ra chắc được → "canh_bao".
      - NGUỒN theo ĐÚNG mô tả field và <the_va_giay_in> (vd NguoiDuocCap_NoiCuTru lấy THẺ trước). Giấy khác (XNTTHN
        cũ, giấy kết hôn, tờ khai) ghi nơi ở khác không phải lý do sửa.
   b) Field đang TRỐNG mà giấy tờ CÓ thông tin đúng như mô tả field và luật trích xuất (đúng loại giấy, đúng khối,
      đúng người) → điền giá trị đầy đủ, đúng định dạng của field. CHỈ chép chữ VIẾT/IN trên giấy, KHÔNG suy ra
      (dòng trên giấy bỏ trống thì field vẫn trống). Field mà luật bảo để trống (vd NguoiYeuCau_* khi chỉ có một
      người, ToKhai*/ToKhaiYeuCau* khi không có tờ khai, PoA_* khi không có giấy ủy quyền) thì KHÔNG điền.
      ĐẶC BIỆT soát các ô hay bị bỏ sót:
      - SỐ, NGÀY, CƠ QUAN của giấy chứng nhận kết hôn / bản án–quyết định ly hôn / trích lục khai tử (Marriage_*,
        DivorceDecision_*, DeathCert_*): giấy có mà v1 trống thì điền — thiếu một ô là form không suy ra được tình
        trạng hôn nhân.
      - DÂN TỘC của người được cấp: v1 trống cả ToKhai_DanToc, NguoiDuocCap_DanToc lẫn GiayToKhac_DanToc mà một giấy
        ghi dân tộc của CHÍNH người đó → điền đúng field theo nguồn (xem mục dân tộc trong <the_va_giay_in>); không
        lấy dân tộc của vợ/chồng, con, cha mẹ hay người đã mất.
   c) Ô GIẤY HỘ TỊCH (DivorceDecision_*, DeathCert_*, Marriage_*) mà v1 lấy theo dòng tình trạng hôn nhân trên TỜ
      KHAI trong khi hồ sơ CÓ chính văn bản in đó (bản án/quyết định ly hôn, giấy chứng tử/trích lục khai tử, giấy
      chứng nhận kết hôn) ghi khác → "sua" theo văn bản in (số đầy đủ ở nhãn "Số:" đầu văn bản — KHÔNG phải
      "Quyển số", số thụ lý hay số biên lai; ngày ban hành ở
      dòng địa danh + ngày tháng năm, cơ quan ở đầu văn bản). Văn bản in đọc không rõ thì "canh_bao".
      BẮT BUỘC ghi "nguon" = tài liệu chứa văn bản in đó theo tiêu đề "### Tài liệu N" của OCR QWEN (tệp gộp nhiều
      giấy thì thêm trang theo "--- Trang M/..." , vd "Tài liệu 2, trang 3"). Giá trị phải CHÉP từ CHÍNH tài liệu đó —
      KHÔNG lấy từ tờ khai, KHÔNG lấy số/ngày của giấy khác loại (vd số thụ lý, số của quyết định khác). Hồ sơ KHÔNG có
      văn bản in loại đó → KHÔNG "sua", chỉ "canh_bao" nếu thấy lệch.
   d) HỌ TÊN chỉ khác DẤU THANH (huyền, sắc, hỏi, ngã, nặng; cùng mọi chữ cái) mà tên đó nằm trên GIẤY IN / ĐÁNH MÁY (thẻ CCCD/CMND,
      giấy chứng nhận in, sổ hộ khẩu, xác nhận cư trú, tờ khai đánh máy) → "sua" theo cách Qwen đọc (OCR Vintern hay
      làm mất/lẫn dấu ở chữ in, vd mất dấu nặng). Tên VIẾT TAY chỉ khác dấu thanh → KHÔNG trả.
      Khác dấu mũ/móc/trăng (u↔ư, o↔ơ↔ô, a↔ă↔â, e↔ê, d↔đ) là KHÁC CHỮ CÁI → theo mục 2, chỉ cảnh báo.
2. "canh_bao" — field KHÔNG phải địa chỉ, ĐANG CÓ giá trị, nhưng OCR QWEN ở ĐÚNG chỗ đó trên ĐÚNG giấy nguồn
   của field đọc KHÁC NỘI DUNG:
   - họ tên (người được cấp, người yêu cầu, vợ/chồng, người đã mất, người ủy quyền) khác CHỮ CÁI (kể cả u↔ư, o↔ơ,
     d↔đ...) → chỉ cảnh báo, KHÔNG sửa. Chỉ khác dấu thanh thì theo mục 1d, không cảnh báo;
   - ngày tháng, số định danh khác BẤT KỲ chữ số nào; số giấy tờ (số bản án/quyết định/trích lục, vd "12/2020/
     HNGĐ-ST") khác bất kỳ chữ số hoặc chữ cái nào. Ký hiệu bản án/quyết định ly hôn luôn có "HNGĐ" (hôn nhân và gia
     đình); v1 mang ký hiệu khác mà Qwen đọc ra "HNGĐ" → cảnh báo;
   - giá trị lựa chọn khác (giới tính, dân tộc, quốc tịch, tình trạng hôn nhân, quan hệ);
   - cơ quan đăng ký hộ tịch (khai tử, kết hôn, ly hôn) khác nơi.
   Cũng cảnh báo khi giá trị KHÔNG có trên giấy nào (nghi bịa, nghi lấy của người khác), và cảnh báo MỌI field mà
   mục "GỢI Ý TỪ CODE" nêu (đó là lỗi kiểm chắc bằng code, vd số CCCD không khớp năm sinh → cảnh báo cả số định danh
   lẫn ngày sinh), kể cả khi Qwen đọc giống v1; ghi lý do theo gợi ý. KHÔNG sửa giá trị, ghi đúng chữ Qwen đọc vào "qwen".
   VAI NGƯỜI: PoA_Subject* là BÊN ỦY QUYỀN (người cần giấy, mục I giấy ủy quyền); NguoiYeuCau_* là người ĐI NỘP
   (bên được ủy quyền / người thân khai hộ); Marriage_SpouseName là tên NGƯỜI KIA trên giấy kết hôn (vợ/chồng
   của người được cấp), KHÔNG phải tên người được cấp. Trước khi cảnh báo ô của một người, xác nhận chữ Qwen đọc
   là của CHÍNH người đó (cùng số CCCD/ngày sinh trong khối) — giá trị của người kia thì KHÔNG phải lệch.
   KHÔNG cảnh báo khi: Qwen đọc giống v1; giá trị khác nằm ở giấy KHÁC (vd ngày cấp thẻ cũ ghi trong giấy XNTTHN
   cũ); chữ Qwen ở chỗ đó vô nghĩa/rác; nơi cấp CCCD/CMND (Python tự chuẩn hoá); tự suy luận (ngày nghe như ở
   tương lai, thẻ hết hạn...); field đang trống.
3. KHÔNG trả field khi: khớp nội dung; chỉ khác định dạng (6/5/2025 = 06/05/2025, hoa/thường, khoảng trắng, viết
   tắt "UBND" ~ "Ủy ban nhân dân", có/không tiền tố "Xã/Phường/Tỉnh"); hoặc Qwen không đọc ra chỗ đó.
</hanh_dong>


<luat_trich_xuat>
<<EXTRACT_RULES>>
</luat_trich_xuat>

<output>
Trả NGAY một JSON object trong code block, KHÔNG viết phân tích hay suy luận ngoài JSON. Mỗi field tối đa một
dòng; "ly_do" tối đa 15 từ. Không có gì cần sửa/cảnh báo thì "fields": [].
```json
{"fields": [{"name": "<field trong <field>>", "flag": "sua|canh_bao", "value": <giá trị mới khi sua, null khi canh_bao>,
  "qwen": "<chữ Qwen đọc ở chỗ đó, rút gọn>", "nguon": "<Tài liệu N[, trang M] — bắt buộc khi sửa ô giấy hộ tịch>",
  "ly_do": "<ngắn>"}]}
```
</output>"""


def _extract_rules() -> str:
    """Luật trích xuất nguyên văn của thủ tục, bỏ <vai_tro> và <output> (agent rà soát có vai và định dạng riêng)."""
    text = base_prompt.build_system_prompt(FIELDS, EXTRA_RULES)
    text = re.sub(r"<vai_tro>.*?</vai_tro>\s*", "", text, flags=re.S)
    return re.sub(r"\s*<output>.*?</output>", "", text, flags=re.S).strip()


def build_messages(v1: dict, goi_y: str, qwen_text: str, vintern_text: str) -> list[dict]:
    user = ("## KẾT QUẢ TRÍCH XUẤT (bản v1)\n" + json.dumps(v1, ensure_ascii=False, indent=1)
            + "\n\n## GỢI Ý TỪ CODE (kiểm tự động trên v1)\n" + goi_y
            + "\n\n## OCR QWEN\n" + (qwen_text or "(không có)")
            + "\n\n## OCR VINTERN (nguồn bước trích xuất đã dùng)\n" + (vintern_text or "(trống)"))
    return [{"role": "system", "content": REVIEW_PROMPT.replace("<<EXTRACT_RULES>>", _extract_rules())},
            {"role": "user", "content": user}]
