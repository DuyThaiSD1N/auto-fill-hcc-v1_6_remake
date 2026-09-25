"""Phân loại tệp lúc upload (checklist handfree) cho Chứng thực văn bản phân chia di sản (2.001406).

Chỉ là lớp xếp tệp vào 3 ô của checklist khi công dân scan/chụp. Định tuyến thật vào dòng 1/dòng 2
trên cổng vẫn do ``attach/planner.py`` quyết từ toàn bộ OCR — định nghĩa loại giấy ở đây bám đúng
prompt của planner (division_draft ↔ du_thao, asset_ownership_proof ↔ so_huu) để hai bước không
hiểu khác nhau.

Không có lưới từ khóa: LLM không trả được loại → theo ô công dân đã chọn, không thì "khac".
"""
import json
import re

from app.upload_session.llm_classifier import ClassificationSpec


PROCEDURE_KEYS = frozenset({"chung-thuc-phan-chia-di-san"})
_ALLOWED_KEYS = frozenset({"so_huu", "du_thao", "khac"})

_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho thủ tục Chứng thực văn bản thỏa thuận phân chia di sản (di sản là
động sản, quyền sử dụng đất, nhà ở).
Mỗi yêu cầu chỉ chứa OCR của ĐÚNG MỘT tệp. Chỉ phân loại tệp đó, không suy diễn từ tài liệu khác và
không trả danh sách.

Chọn đúng một doc_key:
- du_thao: dự thảo hoặc văn bản THỎA THUẬN PHÂN CHIA DI SẢN (thừa kế) mà các người thừa kế lập để
  đem chứng thực. Tiêu đề chính có "PHÂN CHIA DI SẢN"; nội dung nêu người để lại di sản, những người
  thừa kế và phần mỗi người được nhận.
- so_huu: CHÍNH giấy chứng minh quyền sở hữu/quyền sử dụng tài sản là di sản — Giấy chứng nhận quyền
  sử dụng đất, quyền sở hữu nhà ở và tài sản gắn liền với đất (sổ đỏ, sổ hồng), giấy đăng ký xe,
  hoặc giấy tờ thay thế có giá trị tương đương.
- khac: mọi giấy tờ còn lại — giấy chứng tử / trích lục khai tử, căn cước công dân, giấy khai sinh
  hay giấy chứng nhận kết hôn chứng minh quan hệ thừa kế, giấy ủy quyền, phiếu đo đạc, giấy tờ khác.
- unknown: OCR trống hoặc quá thiếu để xác định an toàn.

Phân loại theo TIÊU ĐỀ và BẢN CHẤT của tài liệu, không theo thứ được nhắc bên trong. Văn bản phân
chia di sản vẫn là du_thao dù nội dung liệt kê số Giấy chứng nhận, thửa đất, giấy chứng tử hay số
căn cước của những người thừa kế. Giấy ủy quyền nhắc số Giấy chứng nhận vẫn là khac, không phải
so_huu. Chỉ dùng OCR_TEXT làm bằng chứng; không dùng tên file.
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
