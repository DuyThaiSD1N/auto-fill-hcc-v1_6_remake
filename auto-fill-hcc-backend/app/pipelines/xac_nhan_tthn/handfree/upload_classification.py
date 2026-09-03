"""Cấu hình phân loại tệp lúc upload cho thủ tục xác nhận tình trạng hôn nhân."""
import json
import re
import unicodedata

from app.upload_session.llm_classifier import ClassificationSpec


PROCEDURE_KEYS = frozenset({"xac-nhan-tinh-trang-hon-nhan"})
_ALLOWED_KEYS = frozenset({"cccd", "to_khai", "chung_minh_tthn", "khac"})

_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho thủ tục cấp Giấy xác nhận tình trạng hôn nhân.
Mỗi yêu cầu chỉ chứa OCR của ĐÚNG MỘT tệp. Chỉ phân loại tệp đó, không suy diễn từ
tài liệu khác và không trả danh sách.

Chọn đúng một doc_key:
- cccd: ảnh hoặc bản scan THẺ căn cước/CCCD/CMND. Mặt trước và mặt sau đều thuộc
  cccd; mặt sau có thể chỉ có đặc điểm nhận dạng, nơi cấp, chip hoặc dòng MRZ IDVNM.
- to_khai: Tờ khai cấp Giấy xác nhận tình trạng hôn nhân.
- chung_minh_tthn: giấy tờ trực tiếp chứng minh tình trạng hôn nhân, gồm bản án/quyết
  định ly hôn, quyết định hủy kết hôn, trích lục ghi chú ly hôn, giấy chứng tử hoặc
  trích lục khai tử của vợ/chồng, giấy chứng nhận/trích lục kết hôn, hoặc Giấy xác
  nhận tình trạng hôn nhân đã cấp trước đó.
- khac: các giấy tờ liên quan còn lại như văn bản ủy quyền, giấy tờ cư trú, đơn trình
  bày, bản cam đoan hoặc tài liệu không thuộc ba nhóm trên.
- unknown: OCR trống hoặc quá thiếu để xác định an toàn.

Phân loại theo TIÊU ĐỀ và BẢN CHẤT của tài liệu. Tờ khai, quyết định, giấy chứng nhận
hoặc trích lục vẫn giữ đúng loại của nó dù nội dung có ghi số CCCD. TUYỆT ĐỐI không
phân loại thành cccd chỉ vì tài liệu nhắc đến "CCCD", "căn cước" hoặc có 12 chữ số.
OCR là nguồn chính; chỉ tham khảo tên tệp khi OCR không đủ.

Nếu tài liệu đọc rõ nhưng không thuộc cccd, to_khai hoặc chung_minh_tthn thì chọn khac.
Chỉ trả JSON object đúng schema, không giải thích:
{"doc_key":"cccd"}
""".strip()


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _build_user_prompt(file_name: str, text: str, limit: int = 5000) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) > limit:
        compact = compact[:limit] + "..."
    return json.dumps(
        {"fileName": file_name or "file", "ocrText": compact},
        ensure_ascii=False,
    )


def fallback_to_slot(
    text: str,
    required_docs: list[dict],
    existing_files: list[dict],
    hint_doc_key: str | None,
) -> tuple[str | None, str | None, str]:
    """Fallback riêng khi LLM lỗi/unknown; luôn giữ tài liệu liên quan trong checklist."""
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

    # Xét tờ khai trước: tờ khai thường chứa cả số CCCD và phần khai tình trạng hôn nhân.
    if "to khai" in folded and "tinh trang hon nhan" in folded and free("to_khai"):
        return "to_khai", None, "fallback theo tiêu đề tờ khai"

    evidence_markers = (
        "quyet dinh ly hon", "ban an ly hon", "thuan tinh ly hon", "huy viec ket hon",
        "trich luc ghi chu ly hon", "giay chung tu", "trich luc khai tu", "giay bao tu",
        "giay chung nhan ket hon", "trich luc ket hon", "giay xac nhan tinh trang hon nhan",
    )
    if any(marker in folded for marker in evidence_markers):
        if free("chung_minh_tthn"):
            return "chung_minh_tthn", None, "fallback theo giấy tờ chứng minh tình trạng hôn nhân"
        # Tương thích phiên đã tạo trước khi có key chung_minh_tthn.
        if free("khac"):
            return "khac", None, "fallback giấy tờ chứng minh vào nhóm cũ"

    # Không tin cụm "CCCD số..." đứng riêng: tờ khai/ủy quyền/chứng cứ đều có thể nhắc
    # số căn cước. Chỉ nhận khi có marker mạnh hoặc cụm trường đặc trưng của chính thẻ.
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
        return "khac", None, "fallback vào Các giấy tờ khác liên quan"
    return None, None, "chưa nhận ra loại giấy tờ"


SPEC = ClassificationSpec(
    system_prompt=_SYSTEM_PROMPT,
    allowed_keys=_ALLOWED_KEYS,
    build_user_prompt=_build_user_prompt,
)
