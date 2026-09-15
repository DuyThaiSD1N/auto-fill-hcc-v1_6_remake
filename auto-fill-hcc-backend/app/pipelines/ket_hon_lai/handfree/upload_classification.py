"""Cấu hình phân loại tệp lúc upload riêng cho thủ tục đăng ký lại kết hôn."""
import json
import re

from app.upload_session.llm_classifier import ClassificationSpec


PROCEDURE_KEYS = frozenset({"dang-ky-lai-ket-hon"})
# Khác đăng ký kết hôn: có thêm ô "ho_tich" (GCN kết hôn cũ) là nguồn số/ngày/nơi đăng ký trước đây.
_ALLOWED_KEYS = frozenset({"cccd_nam", "cccd_nu", "ho_tich", "to_khai", "khac"})

_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho thủ tục đăng ký lại kết hôn.
Mỗi yêu cầu chỉ chứa OCR của ĐÚNG MỘT tệp. Chỉ phân loại tệp đó, không suy diễn từ
tài liệu khác và không trả danh sách.

Chọn đúng một doc_key:
- cccd_nam: căn cước/CCCD/CMND/căn cước điện tử/hộ chiếu của bên nam. Xác định bằng giới tính
  Nam/Male hoặc ký hiệu giới tính M trong vùng MRZ của chính giấy tờ.
- cccd_nu: căn cước/CCCD/CMND/căn cước điện tử/hộ chiếu của bên nữ. Xác định bằng giới tính
  Nữ/Female hoặc ký hiệu giới tính F trong vùng MRZ của chính giấy tờ.
- ho_tich: Giấy chứng nhận kết hôn, trích lục kết hôn hoặc bản sao Giấy chứng nhận kết hôn cũ
  (giấy tờ hộ tịch chứng minh sự kiện kết hôn trước đây).
- to_khai: Tờ khai đăng ký lại kết hôn (biểu mẫu người dân tự kê khai).
- khac: bản cam đoan, quyết định/bản án ly hôn, giấy xác nhận tình trạng hôn nhân hoặc giấy tờ
  liên quan khác không thuộc các loại trên.
- unknown: OCR quá thiếu để xác định an toàn.

Không được nhầm TỜ KHAI đăng ký lại kết hôn với Giấy chứng nhận kết hôn: tờ khai là biểu mẫu
người dân tự kê khai; giấy chứng nhận/trích lục kết hôn là giấy tờ hộ tịch (ho_tich).
Phân loại theo tiêu đề và bản chất tài liệu. Tờ khai hoặc giấy xác nhận có thể chứa số căn cước
của một người nhưng không vì thế mà phân loại thành căn cước. OCR là nguồn chính; chỉ tham khảo
tên tệp khi OCR không đủ. Không suy đoán nam/nữ theo tên người.

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
