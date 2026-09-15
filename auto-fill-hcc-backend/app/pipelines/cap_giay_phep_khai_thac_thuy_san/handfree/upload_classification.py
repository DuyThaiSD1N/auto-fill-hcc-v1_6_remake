"""Phân loại tệp lúc upload (checklist handfree) cho thủ tục Cấp, cấp lại Giấy phép khai thác thủy sản.

Chỉ là lớp xếp tệp vào checklist khi công dân tải ảnh. Phân loại thành phần hồ sơ trên cổng
MAE vẫn do ``attach/planner.py`` quyết định từ toàn bộ OCR (Mẫu 04 vs Mẫu 05).
"""
import json
import re
import unicodedata

from app.upload_session.llm_classifier import ClassificationSpec


PROCEDURE_KEYS = frozenset({"cap-giay-phep-khai-thac-thuy-san"})
_ALLOWED_KEYS = frozenset({"don", "cccd", "giay_phep_cu", "khac"})

_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho thủ tục Cấp, cấp lại Giấy phép khai thác thủy sản.
Mỗi yêu cầu chỉ chứa OCR của ĐÚNG MỘT tệp. Chỉ phân loại tệp đó, không suy diễn từ
tài liệu khác và không trả danh sách.

Chọn đúng một doc_key:
- don: ĐƠN ĐỀ NGHỊ cấp Giấy phép khai thác thủy sản (Mẫu 04.KT) HOẶC đơn đề nghị CẤP LẠI
  (Mẫu 05.KT). Tiêu đề có "ĐƠN ĐỀ NGHỊ", nội dung về chủ tàu, số đăng ký tàu cá, nghề khai
  thác hoặc lý do cấp lại. Cả hai mẫu đều thuộc don.
- giay_phep_cu: tờ GIẤY PHÉP KHAI THÁC THỦY SẢN đã được cấp (KHÔNG phải đơn đề nghị) —
  tiêu đề "GIẤY PHÉP KHAI THÁC THỦY SẢN", có số giấy phép, cơ quan cấp, thời hạn.
- cccd: ảnh hoặc bản scan THẺ căn cước/CCCD/CMND/hộ chiếu. Mặt trước và mặt sau đều thuộc
  cccd; mặt sau có thể chỉ có đặc điểm nhận dạng, nơi cấp, chip hoặc dòng MRZ IDVNM.
- khac: giấy tờ liên quan còn lại (văn bản ủy quyền, giấy chứng nhận an toàn kỹ thuật...).
- unknown: OCR trống hoặc quá thiếu để xác định an toàn.

Phân loại theo TIÊU ĐỀ và BẢN CHẤT của tài liệu. Đơn đề nghị vẫn là don dù bên trong ghi số
căn cước hoặc số giấy phép cũ. TUYỆT ĐỐI không phân loại thành cccd chỉ vì tài liệu nhắc đến
"CCCD" hoặc có 12 chữ số. Chỉ dùng OCR_TEXT làm bằng chứng; không dùng tên file.
Chỉ trả JSON object đúng schema, không giải thích:
{"doc_key":"don"}
""".strip()


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


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
    """Fallback tất định khi LLM lỗi/unknown; giữ mọi tệp liên quan trong checklist."""
    folded = _fold(text)
    keys = {item.get("key") for item in required_docs}
    repeatable = {item.get("key") for item in required_docs if item.get("repeatable")}
    sides = {item.get("key"): int(item.get("sides") or 1) for item in required_docs}
    counts = {
        key: sum(1 for item in existing_files if item.get("doc_key") == key)
        for key in keys
    }

    def free(key: str) -> bool:
        return key in keys and (key in repeatable or counts.get(key, 0) < sides.get(key, 1))

    # Đơn xét trước: đơn cấp lại cũng nhắc "giấy phép khai thác thủy sản" nên nếu để nhánh
    # giấy phép cũ lên đầu sẽ nuốt nhầm đơn.
    if "de nghi" in folded and "giay phep khai thac thuy san" in folded and free("don"):
        return "don", None, "fallback theo tiêu đề đơn đề nghị"

    if "giay phep khai thac thuy san" in folded and "de nghi" not in folded and free("giay_phep_cu"):
        return "giay_phep_cu", None, "fallback theo tờ giấy phép đã cấp"

    strong_identity = any(marker in folded for marker in (
        "citizen identity", "identity card", "idvnm", "dac diem nhan dang",
        "giay chung minh nhan dan",
    ))
    card_fields = (
        ("so dinh danh ca nhan" in folded or "personal identification number" in folded)
        and ("ho va ten" in folded or "full name" in folded)
        and ("ngay sinh" in folded or "date of birth" in folded)
    )
    if (strong_identity or ("can cuoc" in folded and card_fields)) and free("cccd"):
        return "cccd", None, "fallback theo marker thẻ căn cước"

    if hint_doc_key and free(hint_doc_key):
        return hint_doc_key, None, "fallback theo mục công dân đã chọn"
    if free("khac"):
        return "khac", None, "fallback vào Giấy tờ liên quan khác"
    return None, None, "chưa nhận ra loại giấy tờ"


SPEC = ClassificationSpec(
    system_prompt=_SYSTEM_PROMPT,
    allowed_keys=_ALLOWED_KEYS,
    build_user_prompt=_build_user_prompt,
)
