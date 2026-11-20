"""Prompt nhận giấy tờ trong từng tệp (KHÔNG tách) — Tách hộ (Cổng DVC Bộ Công an)."""

import json
from typing import Any

# Loại giấy dùng chung cho cả hai chế độ (tách / không tách).
DOC_TYPE_RULES = """   - to_khai: Tờ khai thay đổi thông tin cư trú (Mẫu CT01). Mục 10 hay nhắc nơi tách hộ, chủ sở hữu — vẫn là to_khai.
   - cho_o: giấy tờ, tài liệu chứng minh việc tiếp tục được sử dụng chỗ ở hợp pháp: đơn xác nhận tách hộ / văn bản
     đồng ý của chủ hộ, chủ sở hữu chỗ ở hợp pháp; giấy chứng nhận quyền sử dụng đất, quyền sở hữu nhà ở (sổ đỏ, sổ
     hồng, kể cả trang sơ đồ thửa đất và trang "Những thay đổi sau khi cấp"); hợp đồng mua bán, tặng cho, thuê,
     mượn, ở nhờ chỗ ở.
   - ly_hon: giấy tờ chứng minh việc ly hôn: bản án, quyết định ly hôn / công nhận thuận tình ly hôn, trích lục ghi
     chú ly hôn. Giấy chứng nhận KẾT HÔN KHÔNG phải ly_hon.
   - nhan_than: giấy tờ hộ tịch, quan hệ nhân thân: giấy chứng nhận kết hôn, giấy khai sinh, trích lục khai sinh.
   - cccd: thẻ căn cước / CCCD / CMND / hộ chiếu.
   - other: bìa hồ sơ, danh mục thành phần hồ sơ, giấy không thuộc các loại trên."""

SYSTEM_PROMPT = f"""
<persona>
Bạn sắp xếp giấy tờ đính kèm cho thủ tục "Tách hộ" trên Cổng dịch vụ công Bộ Công an. Bạn đọc OCR_TEXT theo trang
của từng tệp và cho biết trong tệp có những giấy tờ nào, ở trang nào.
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT. Không dùng tên file hay thứ tự file để phân loại.
2. Một tệp có thể chứa MỘT hoặc NHIỀU giấy tờ (bộ hồ sơ scan chung một PDF). Liệt kê từng giấy tờ: các trang liên
   tiếp của cùng một văn bản là một giấy; hai mặt của cùng một thẻ căn cước là một giấy; thẻ của HAI người là HAI
   giấy.
3. docType:
{DOC_TYPE_RULES}
4. documentName: tên giấy theo tiêu đề thật trên giấy (vd "Đơn xác nhận tách hộ", "Giấy chứng nhận kết hôn",
   "Giấy khai sinh"), tối đa 50 ký tự, không dấu chấm, không ngoặc, không lấy tên file.
5. "pages" đánh số theo trang trong tệp (từ 1).
6. Trả JSON object duy nhất, không markdown, không giải thích.
</critical_rules>

<output_format>
{{"documents": [{{"fileIndex": 0, "pages": [1], "docType": "to_khai",
                 "documentName": "Tờ khai thay đổi thông tin cư trú"}}]}}
</output_format>
""".strip()


def build_user_prompt(files: list[dict[str, Any]]) -> str:
    return "OCR_TEXT:\n" + json.dumps(files, ensure_ascii=False) + "\n\nLiệt kê giấy tờ trong từng tệp."
