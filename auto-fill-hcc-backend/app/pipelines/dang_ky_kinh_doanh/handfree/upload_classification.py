"""Phân loại tệp realtime cho thủ tục thành lập hộ kinh doanh.

Đây chỉ là lớp xếp tệp vào checklist lúc công dân tải ảnh. Phân loại thành phần hồ sơ
trên HkdOnline vẫn do ``attach/planner.py`` quyết định từ toàn bộ OCR của hồ sơ.
"""
import json
import re

from app.upload_session.llm_classifier import ClassificationSpec


PROCEDURE_KEYS = frozenset({"dang-ky-kinh-doanh"})
_ALLOWED_KEYS = frozenset({"giay_de_nghi", "cccd", "uy_quyen", "bien_ban", "khac"})

_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho thủ tục Đăng ký thành lập hộ kinh doanh.
Mỗi yêu cầu chỉ chứa OCR của đúng MỘT tệp. Chọn đúng một doc_key:
- giay_de_nghi: Giấy đề nghị đăng ký hộ kinh doanh hoặc mẫu kê khai thành lập hộ kinh doanh.
- cccd: Căn cước, CCCD, CMND, hộ chiếu hoặc giấy tờ pháp lý của cá nhân.
- uy_quyen: Văn bản/giấy ủy quyền của thành viên hộ gia đình cho một người làm chủ hộ hoặc nộp hồ sơ.
- bien_ban: Biên bản họp thành viên hộ gia đình về việc thành lập hộ kinh doanh.
- khac: giấy tờ liên quan khác.
- unknown: OCR quá thiếu để xác định an toàn.

Phân loại theo tiêu đề và bản chất tài liệu. Giấy đề nghị, giấy ủy quyền hoặc biên bản
có thể chứa số căn cước nhưng không vì thế mà phân loại thành cccd. OCR là nguồn chính;
chỉ tham khảo tên tệp khi OCR không đủ. Chỉ trả JSON object, không giải thích:
{"doc_key":"giay_de_nghi"}
""".strip()


def _build_user_prompt(file_name: str, text: str, limit: int = 5000) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) > limit:
        compact = compact[:limit] + "..."
    return json.dumps(
        {"fileName": file_name or "file", "ocrText": compact},
        ensure_ascii=False,
    )


SPEC = ClassificationSpec(
    system_prompt=_SYSTEM_PROMPT,
    allowed_keys=_ALLOWED_KEYS,
    build_user_prompt=_build_user_prompt,
)
