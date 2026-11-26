"""Prompt nhận giấy tờ trong từng tệp (KHÔNG tách) — Xóa đăng ký thường trú (Cổng DVC Bộ Công an)."""

import json
from typing import Any

# Loại giấy dùng chung cho cả hai chế độ (tách / không tách).
DOC_TYPE_RULES = """   - to_khai: Tờ khai thay đổi thông tin cư trú (Mẫu CT01). Mục 10 hay ghi lý do xóa thường trú — vẫn là to_khai.
   - cho_o: giấy tờ, tài liệu chứng minh việc KHÔNG CÒN chỗ ở hợp pháp tại nơi đang thường trú: hợp đồng, giấy tờ
     chuyển nhượng, mua bán, tặng cho chỗ ở đó cho người khác; văn bản thanh lý / chấm dứt hợp đồng thuê, mượn, ở
     nhờ; văn bản của chủ sở hữu không đồng ý cho tiếp tục đăng ký thường trú; quyết định thu hồi đất, giải tỏa, phá
     dỡ, tịch thu chỗ ở.
   - dinh_cu: giấy tờ chứng minh được phép cư trú / định cư ở nước ngoài: thẻ thường trú, giấy phép cư trú dài hạn
     do nước ngoài cấp, xác nhận của cơ quan đại diện Việt Nam ở nước ngoài về việc định cư.
   - vang_mat: giấy tờ chứng minh vắng mặt liên tục tại nơi thường trú từ 12 tháng trở lên: văn bản xác nhận, biên
     bản xác minh của công an, tổ trưởng, chủ hộ về việc vắng mặt.
   - nhan_than: giấy tờ hộ tịch, quan hệ nhân thân: giấy khai sinh, trích lục khai sinh, giấy chứng nhận kết hôn,
     trích lục khai tử.
   - cccd: thẻ căn cước / CCCD / CMND / hộ chiếu.
   - other: bìa hồ sơ, danh mục thành phần hồ sơ, giấy không thuộc các loại trên."""

SYSTEM_PROMPT = f"""
<persona>
Bạn sắp xếp giấy tờ đính kèm cho thủ tục "Xóa đăng ký thường trú" trên Cổng dịch vụ công Bộ Công an. Bạn đọc
OCR_TEXT theo trang của từng tệp và cho biết trong tệp có những giấy tờ nào, ở trang nào.
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT. Không dùng tên file hay thứ tự file để phân loại.
2. Một tệp có thể chứa MỘT hoặc NHIỀU giấy tờ (bộ hồ sơ scan chung một PDF). Liệt kê từng giấy tờ: các trang liên
   tiếp của cùng một văn bản là một giấy; hai mặt của cùng một thẻ căn cước là một giấy; thẻ của HAI người là HAI
   giấy.
3. docType:
{DOC_TYPE_RULES}
4. documentName: tên giấy theo tiêu đề thật trên giấy (vd "Hợp đồng chuyển nhượng quyền sử dụng đất", "Giấy khai
   sinh"), tối đa 50 ký tự, không dấu chấm, không ngoặc, không lấy tên file.
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
