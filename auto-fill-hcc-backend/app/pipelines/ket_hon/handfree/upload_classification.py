"""Cấu hình phân loại tệp lúc upload riêng cho thủ tục đăng ký kết hôn."""
import json
import re

from app.upload_session.llm_classifier import ClassificationSpec


PROCEDURE_KEYS = frozenset({"ket-hon"})
_ALLOWED_KEYS = frozenset({"cccd_nam", "cccd_nu", "to_khai", "khac"})

_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho thủ tục đăng ký kết hôn.
Mỗi yêu cầu chỉ chứa OCR của ĐÚNG MỘT tệp. Chỉ phân loại tệp đó, không suy diễn từ
tài liệu khác và không trả danh sách.

Chọn đúng một doc_key:
- cccd_nam: căn cước/CCCD/CMND/căn cước điện tử của bên nam. Xác định bằng giới tính
  Nam/Male hoặc ký hiệu giới tính M trong vùng MRZ của chính giấy tờ.
- cccd_nu: căn cước/CCCD/CMND/căn cước điện tử của bên nữ. Xác định bằng giới tính
  Nữ/Female hoặc ký hiệu giới tính F trong vùng MRZ của chính giấy tờ.
- to_khai: Tờ khai đăng ký kết hôn.
- khac: giấy xác nhận tình trạng hôn nhân, quyết định/bản án ly hôn, bản cam đoan,
  hộ chiếu, giấy tờ chứng minh tình trạng hôn nhân hoặc giấy tờ liên quan khác.
- unknown: OCR quá thiếu để xác định an toàn.

Phân loại theo tiêu đề và bản chất tài liệu. Tờ khai hoặc giấy xác nhận có thể chứa số
căn cước của một người nhưng không vì thế mà phân loại thành căn cước. OCR là nguồn
chính; chỉ tham khảo tên tệp khi OCR không đủ. Không suy đoán nam/nữ theo tên người.

Chỉ trả JSON object đúng schema, không giải thích:
{"doc_key":"cccd_nam"}
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
