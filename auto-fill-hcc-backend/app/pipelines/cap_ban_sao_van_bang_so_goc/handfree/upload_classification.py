"""Phân loại tệp lúc upload (checklist handfree) cho thủ tục Cấp bản sao văn bằng, chứng chỉ từ sổ gốc.

Chỉ là lớp xếp tệp vào checklist khi công dân tải ảnh. Phân loại thành phần hồ sơ trên cổng
Bộ GD&ĐT vẫn do ``attach/planner.py`` quyết định từ toàn bộ OCR.
"""
import json
import re
import unicodedata

from app.upload_session.llm_classifier import ClassificationSpec


PROCEDURE_KEYS = frozenset({"cap-ban-sao-van-bang-so-goc"})
_ALLOWED_KEYS = frozenset({"don", "cccd", "van_bang", "uy_quyen", "khac"})

_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho thủ tục Cấp bản sao văn bằng, chứng chỉ từ sổ gốc.
Mỗi yêu cầu chỉ chứa OCR của ĐÚNG MỘT tệp. Chỉ phân loại tệp đó, không suy diễn từ
tài liệu khác và không trả danh sách.

Chọn đúng một doc_key:
- don: Phiếu yêu cầu / đơn đề nghị cấp bản sao văn bằng, chứng chỉ (Mẫu BM04). Tiêu đề có
  "PHIẾU YÊU CẦU" hoặc "ĐƠN ĐỀ NGHỊ CẤP BẢN SAO VĂN BẰNG", có mục số lượng bản sao xin cấp.
- van_bang: chính tấm VĂN BẰNG / BẰNG TỐT NGHIỆP / CHỨNG CHỈ (hoặc bản photo của nó) —
  tiêu đề "BẰNG TỐT NGHIỆP", "CHỨNG CHỈ", có xếp loại, năm tốt nghiệp, hiệu trưởng ký.
- cccd: ảnh hoặc bản scan THẺ căn cước/CCCD/CMND/hộ chiếu. Mặt trước và mặt sau đều thuộc
  cccd; mặt sau có thể chỉ có đặc điểm nhận dạng, nơi cấp, chip hoặc dòng MRZ IDVNM.
- uy_quyen: giấy ủy quyền hoặc giấy tờ chứng minh quan hệ (khai sinh, sổ hộ khẩu...) khi
  người khác yêu cầu thay chủ văn bằng.
- khac: giấy tờ liên quan còn lại.
- unknown: OCR trống hoặc quá thiếu để xác định an toàn.

Phân loại theo TIÊU ĐỀ và BẢN CHẤT của tài liệu. Phiếu BM04 vẫn là don dù bên trong ghi tên
văn bằng hoặc số căn cước. TUYỆT ĐỐI không phân loại thành cccd chỉ vì tài liệu nhắc đến
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

    # Phiếu BM04 xét trước: nội dung phiếu nhắc chính văn bằng cần cấp bản sao.
    if ("phieu yeu cau" in folded or "de nghi cap ban sao" in folded) and free("don"):
        return "don", None, "fallback theo tiêu đề phiếu yêu cầu"

    if any(marker in folded for marker in (
        "bang tot nghiep", "chung chi", "van bang", "hieu truong",
    )) and free("van_bang"):
        return "van_bang", None, "fallback theo tấm văn bằng/chứng chỉ"

    if ("uy quyen" in folded or "chung minh quan he" in folded) and free("uy_quyen"):
        return "uy_quyen", None, "fallback theo giấy ủy quyền"

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
