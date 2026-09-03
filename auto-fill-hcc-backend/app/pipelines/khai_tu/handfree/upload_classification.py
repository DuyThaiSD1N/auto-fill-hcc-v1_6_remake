"""Cấu hình phân loại tệp lúc upload cho thủ tục đăng ký khai tử."""
import json
import re
import unicodedata

from app.upload_session.llm_classifier import ClassificationSpec


PROCEDURE_KEYS = frozenset({"khai-tu"})
_ALLOWED_KEYS = frozenset({"cccd", "bao_tu", "to_khai", "khac"})

_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho thủ tục đăng ký khai tử.
Mỗi yêu cầu chỉ chứa OCR của ĐÚNG MỘT tệp. Chỉ phân loại tệp đó, không suy diễn từ
tài liệu khác và không trả danh sách.

Chọn đúng một doc_key:
- cccd: ảnh hoặc bản scan THẺ căn cước/CCCD/CMND. Mặt trước và mặt sau đều thuộc
  cccd; mặt sau có thể chỉ có đặc điểm nhận dạng, nơi cấp, chip hoặc dòng MRZ IDVNM.
- bao_tu: Giấy báo tử hoặc giấy tờ trực tiếp thay Giấy báo tử, gồm Giấy chứng tử,
  trích lục khai tử, văn bản của cơ quan có thẩm quyền xác nhận việc chết/tử vong,
  hoặc quyết định có hiệu lực tuyên bố một người đã chết.
- to_khai: Tờ khai đăng ký khai tử bản giấy.
- khac: các giấy tờ liên quan còn lại như văn bản ủy quyền, giấy tờ chứng minh nơi
  chết/nơi phát hiện thi thể, giấy tờ cư trú hoặc tài liệu không thuộc ba nhóm trên.
- unknown: OCR trống hoặc quá thiếu để xác định an toàn.

Phân loại theo TIÊU ĐỀ và BẢN CHẤT của tài liệu. Tờ khai vẫn là to_khai dù bên trong
nhắc đến Giấy báo tử, người chết hoặc có số CCCD. Giấy báo tử/giấy thay thế vẫn là
bao_tu dù nội dung có ghi số CCCD của người khai hoặc người chết. TUYỆT ĐỐI không
phân loại thành cccd chỉ vì tài liệu nhắc đến "CCCD", "căn cước" hoặc có 12 chữ số.
Chỉ dùng OCR_TEXT làm bằng chứng; không dùng tên file hoặc thứ tự file.

Nếu tài liệu đọc rõ nhưng không thuộc cccd, bao_tu hoặc to_khai thì chọn khac.
Chỉ trả JSON object đúng schema, không giải thích:
{"doc_key":"bao_tu"}
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
    """Fallback riêng khi LLM lỗi/unknown; giữ mọi tệp liên quan trong checklist."""
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

    # Tờ khai xét trước vì nội dung thường trích lại thông tin Giấy báo tử và số CCCD.
    if "to khai" in folded and "khai tu" in folded and free("to_khai"):
        return "to_khai", None, "fallback theo tiêu đề tờ khai"

    death_notice_markers = (
        "giay bao tu", "giay chung tu", "trich luc khai tu", "giay xac nhan tu vong",
        "xac nhan viec chet", "xac nhan su kien chet", "tuyen bo mot nguoi da chet",
        "tuyen bo da chet",
    )
    if any(marker in folded for marker in death_notice_markers) and free("bao_tu"):
        return "bao_tu", None, "fallback theo giấy báo tử hoặc giấy tờ thay thế"

    # Không tin cụm "CCCD số..." đứng riêng: tờ khai/ủy quyền/giấy báo tử đều có thể
    # nhắc số căn cước. Chỉ nhận marker mạnh hoặc cụm trường đặc trưng của chính thẻ.
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
