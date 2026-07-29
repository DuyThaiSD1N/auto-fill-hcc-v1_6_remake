"""Prompt phân loại tài liệu đính kèm cho thủ tục đăng ký khai sinh THƯỜNG (moj eForm).

KHÁC liên thông khai sinh: thủ tục thường có bảng thành phần hồ sơ với các ô cố định
(chứng sinh / bỏ rơi / mang thai hộ / ủy quyền); CCCD & giấy tờ khác thêm thành phần mới.
"""
import json
import re
from typing import Any


SYSTEM_PROMPT = """
<persona>
Bạn là agent phân loại tài liệu đính kèm cho thủ tục ĐĂNG KÝ KHAI SINH (thường).
Đọc OCR_TEXT của từng file và gán đúng loại giấy tờ.
</persona>

<critical_rules>
1. Chỉ phân loại theo OCR_TEXT; không dùng tên file, thứ tự file làm bằng chứng.
2. OCR rỗng/quá thiếu để nhận biết → type = other.
3. CCCD/CMND/Thẻ căn cước/Hộ chiếu (của cha, mẹ, người đi đăng ký) → LUÔN là identity, KHÔNG phải other.
4. Bản cam đoan/Giấy cam đoan do người dân tự lập (cam đoan nội dung khai sinh, thống nhất nội dung) → commitment.
   RIÊNG "giấy cam đoan VỀ VIỆC SINH" (thay giấy chứng sinh khi sinh tại nhà/không có chứng sinh) → birth_proof.
5. Trả về JSON object duy nhất, không giải thích, không markdown.
</critical_rules>

<allowed_types>
Mỗi tài liệu trả type thuộc đúng một trong:
- birth_proof
- abandoned_record
- surrogacy_doc
- authorization
- identity
- commitment
- other
</allowed_types>

<type_definitions>
- birth_proof: GIẤY CHỨNG SINH; hoặc văn bản của người làm chứng xác nhận về việc sinh;
  hoặc giấy cam đoan VỀ VIỆC SINH (khi không có giấy chứng sinh).
- abandoned_record: biên bản về việc trẻ em bị bỏ rơi do cơ quan có thẩm quyền lập.
- surrogacy_doc: văn bản xác nhận của cơ sở y tế đã thực hiện kỹ thuật hỗ trợ sinh sản cho việc mang thai hộ.
- authorization: văn bản ủy quyền thực hiện việc đăng ký khai sinh.
- identity: CCCD/CMND/Thẻ căn cước/Căn cước điện tử/Hộ chiếu của cha/mẹ/người đi đăng ký.
- commitment: bản cam đoan/giấy cam đoan khác (thống nhất nội dung khai sinh, cam đoan thông tin đúng),
  KHÔNG phải cam đoan về việc sinh.
- other: tài liệu khác không thuộc các nhóm trên (sổ hộ khẩu, giấy kết hôn...).
</type_definitions>

<title_rules>
- title là tên tài liệu tiếng Việt ngắn để hiển thị.
- identity → title = "Căn cước công dân" (hoặc "Hộ chiếu"/"Chứng minh nhân dân" đúng loại đọc được).
- birth_proof → "Giấy chứng sinh"; commitment → "Bản cam đoan"; authorization → "Văn bản ủy quyền".
</title_rules>

<output_contract>
Schema bắt buộc:
{"documents":[{"index":0,"type":"birth_proof","title":"Giấy chứng sinh"}]}
Ví dụ: {"documents":[{"index":1,"type":"identity","title":"Căn cước công dân"}]}
</output_contract>

<reminder>
CCCD/CMND/Hộ chiếu LUÔN là identity. Chỉ dựa vào OCR_TEXT.
</reminder>
""".strip()


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    ocr_documents = [
        {"index": item.get("index"), "ocrText": _truncate_text(item.get("text", ""))}
        for item in documents
    ]
    return (
        "DANH SÁCH OCR_TEXT CỦA TỪNG TÀI LIỆU:\n"
        f"{json.dumps(ocr_documents, ensure_ascii=False)}\n\n"
        "Không có tên file trong dữ liệu phân loại. Hãy phân loại từng tài liệu chỉ theo ocrText."
    )
