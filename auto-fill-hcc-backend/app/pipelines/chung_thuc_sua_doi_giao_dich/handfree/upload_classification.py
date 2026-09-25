"""Phân loại tệp lúc upload (checklist handfree) cho Chứng thực việc sửa đổi, bổ sung, hủy bỏ giao
dịch (2.000913).

Chỉ là lớp xếp tệp vào 4 ô của checklist khi công dân scan/chụp. Định tuyến thật vào dòng 1/dòng 2
trên cổng vẫn do ``attach/planner.py`` quyết từ toàn bộ OCR — định nghĩa loại giấy ở đây bám đúng
prompt của planner (modification_draft ↔ du_thao, certified_transaction ↔ giao_dich_cu,
asset_ownership_proof ↔ so_huu) để hai bước không hiểu khác nhau.

Không có lưới từ khóa: LLM không trả được loại → theo ô công dân đã chọn, không thì "khac".
"""
import json
import re

from app.upload_session.llm_classifier import ClassificationSpec


PROCEDURE_KEYS = frozenset({"chung-thuc-sua-doi-bo-sung-huy-bo-giao-dich"})
_ALLOWED_KEYS = frozenset({"du_thao", "giao_dich_cu", "so_huu", "khac"})

_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho thủ tục Chứng thực việc sửa đổi, bổ sung, hủy bỏ giao dịch.
Mỗi yêu cầu chỉ chứa OCR của ĐÚNG MỘT tệp. Chỉ phân loại tệp đó, không suy diễn từ tài liệu khác và
không trả danh sách.

Chọn đúng một doc_key:
- du_thao: dự thảo / văn bản MỚI để sửa đổi, bổ sung hoặc hủy bỏ một giao dịch — văn bản sửa đổi
  hợp đồng, văn bản bổ sung hợp đồng, văn bản hủy bỏ hợp đồng, phụ lục hợp đồng — lập để đem chứng
  thực trong hồ sơ này. Chưa có lời chứng của cơ quan chứng thực.
- giao_dich_cu: giao dịch / hợp đồng CŨ ĐÃ ĐƯỢC CHỨNG THỰC trước đây — thường có "LỜI CHỨNG",
  "Số chứng thực", "quyển số chứng thực", chữ ký và chức danh người thực hiện chứng thực, hoặc ghi
  "đã được chứng thực".
- so_huu: CHÍNH giấy chứng minh quyền sở hữu/quyền sử dụng tài sản của giao dịch — Giấy chứng nhận
  quyền sử dụng đất, quyền sở hữu nhà ở và tài sản gắn liền với đất (sổ đỏ, sổ hồng), giấy đăng ký
  xe, hoặc giấy tờ thay thế.
- khac: mọi giấy tờ còn lại — căn cước công dân / hộ chiếu của các bên, giấy ủy quyền, giấy tờ khác.
- unknown: OCR trống hoặc quá thiếu để xác định an toàn.

Phân loại theo TIÊU ĐỀ và BẢN CHẤT của tài liệu, không theo thứ được nhắc bên trong. Văn bản sửa
đổi/hủy bỏ vẫn là du_thao dù nội dung trích dẫn số chứng thực của hợp đồng cũ; hợp đồng cũ có lời
chứng vẫn là giao_dich_cu dù mô tả thửa đất hay số Giấy chứng nhận. Giấy ủy quyền nhắc số Giấy
chứng nhận vẫn là khac. Chỉ dùng OCR_TEXT làm bằng chứng; không dùng tên file.
Chỉ trả JSON object đúng schema, không giải thích:
{"doc_key":"du_thao"}
""".strip()


def _build_user_prompt(_file_name: str, text: str, limit: int = 5000) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) > limit:
        compact = compact[:limit] + "..."
    # Không truyền tên file để tên file không trở thành bằng chứng hoặc prompt injection.
    return json.dumps({"ocrText": compact}, ensure_ascii=False)


def fallback_to_slot(
    text: str,
    required_docs: list[dict],
    existing_files: list[dict],
    hint_doc_key: str | None,
) -> tuple[str | None, str | None, str]:
    """LLM lỗi/unknown: không đoán loại. Theo ô công dân đã chọn, không thì Giấy tờ khác."""
    _ = text, existing_files
    keys = {item.get("key") for item in required_docs}
    if hint_doc_key and hint_doc_key in keys:
        return hint_doc_key, None, "theo mục công dân đã chọn"
    if "khac" in keys:
        return "khac", None, "chưa nhận ra loại — xếp vào Giấy tờ khác"
    return None, None, "chưa nhận ra loại giấy tờ"


SPEC = ClassificationSpec(
    system_prompt=_SYSTEM_PROMPT,
    allowed_keys=_ALLOWED_KEYS,
    build_user_prompt=_build_user_prompt,
)
