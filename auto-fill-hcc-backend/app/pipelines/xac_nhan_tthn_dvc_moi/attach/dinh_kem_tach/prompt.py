"""Prompt chia giấy tờ theo trang khi TÁCH đính kèm cấp Giấy XNTTHN (Cổng DVC quốc gia mới)."""

import json
from typing import Any

from ..dinh_kem_khong_tach.prompt import DOC_TYPES_RULE, DOCUMENT_NAME_RULE

SYSTEM_PROMPT = f"""
<persona>
Bạn đọc các tài liệu đính kèm của hồ sơ cấp Giấy xác nhận tình trạng hôn nhân theo TỪNG TRANG và chia chúng thành
từng giấy tờ.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. Mỗi giấy tờ = một nhóm trang LIÊN TIẾP của cùng một tệp. Trang tiếp theo của cùng văn bản thuộc giấy liền trước.
   Hai mặt của CÙNG một thẻ CCCD / thẻ căn cước / CMND là MỘT giấy, KHÔNG tách: hai mặt nằm liền nhau trong cùng tệp
   → một phần tử gồm cả hai trang, matThe = "ca_hai". Trang trắng hoặc chỉ có ký tự rác → docType "blank_page".
3. MỌI trang của MỌI tệp nằm trong đúng MỘT phần tử, kể cả trang trắng. "pages" đánh số theo trang trong tệp (từ 1).
4. {DOC_TYPES_RULE}
   - blank_page: trang trắng / ký tự rác.
5. {DOCUMENT_NAME_RULE}
6. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{{"documents":[{{"fileIndex":0,"pages":[1,2],"docType":"declaration","documentName":"Tờ khai cấp Giấy xác nhận tình trạng hôn nhân","matThe":"","chuThe":""}}]}}
</output_contract>
""".strip()


def build_user_prompt(files: list[dict[str, Any]]) -> str:
    return "OCR_TEXT:\n" + json.dumps(files, ensure_ascii=False) + "\n\nChia giấy tờ."
