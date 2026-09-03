"""Cấu hình phân loại tệp lúc upload cho thủ tục đăng ký lại khai tử."""
import json
import re
import unicodedata

from app.upload_session.llm_classifier import ClassificationSpec


PROCEDURE_KEYS = frozenset({"khai-tu-dang-ky-lai"})
_ALLOWED_KEYS = frozenset({"cccd", "to_khai", "bao_tu", "khac"})

_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho thủ tục đăng ký lại khai tử.
Mỗi yêu cầu chỉ chứa OCR của ĐÚNG MỘT tệp. Chỉ phân loại tệp đó, không suy diễn từ
tài liệu khác và không trả danh sách.

Chọn đúng một doc_key:
- cccd: chính thẻ căn cước/CCCD/CMND, hộ chiếu hoặc giấy tờ tùy thân của người yêu
  cầu hay người đã chết. Mặt trước, mặt sau và trang thông tin hộ chiếu đều thuộc cccd.
- to_khai: Tờ khai đăng ký lại khai tử bản giấy.
- bao_tu: Giấy chứng tử, trích lục khai tử, Giấy báo tử hoặc giấy tờ trực tiếp chứng
  minh sự kiện chết, gồm văn bản xác nhận việc chết/tử vong, quyết định tuyên bố một
  người đã chết và chứng cứ hợp lệ về thời điểm/sự kiện chết khi không còn giấy cũ.
- khac: giấy tờ liên quan còn lại như văn bản ủy quyền, giấy tờ cư trú, giấy khai sinh,
  đơn trình bày hoặc tài liệu không thuộc ba nhóm trên.
- unknown: OCR trống hoặc quá thiếu để xác định an toàn.

Phân loại theo TIÊU ĐỀ và BẢN CHẤT của tài liệu. Tờ khai vẫn là to_khai dù bên trong
nhắc đến Giấy chứng tử, trích lục khai tử hoặc số CCCD. Giấy chứng tử và giấy chứng
minh sự kiện chết vẫn là bao_tu dù ghi giấy tờ tùy thân của người liên quan. TUYỆT ĐỐI
không chọn cccd chỉ vì tài liệu nhắc đến "CCCD", "căn cước", "hộ chiếu" hoặc có dãy
số định danh. Giấy khai sinh/giấy chứng sinh không chứng minh sự kiện chết và phải là khac.
Chỉ dùng OCR_TEXT làm bằng chứng; không dùng tên file hoặc thứ tự file.

Nếu tài liệu đọc rõ nhưng không thuộc cccd, to_khai hoặc bao_tu thì chọn khac.
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
    # Tên file không phải bằng chứng; mỗi prompt chỉ mang OCR của đúng một tệp.
    return json.dumps({"ocrText": compact}, ensure_ascii=False)


def fallback_to_slot(
    text: str,
    required_docs: list[dict],
    existing_files: list[dict],
    hint_doc_key: str | None,
) -> tuple[str | None, str | None, str]:
    """Fallback riêng khi LLM lỗi/unknown; vẫn giữ tệp trong checklist phù hợp."""
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

    # Tờ khai xét trước vì nội dung thường chép lại số CCCD và thông tin giấy chứng tử.
    if "to khai" in folded and "dang ky lai khai tu" in folded and free("to_khai"):
        return "to_khai", None, "fallback theo tiêu đề tờ khai đăng ký lại khai tử"

    death_markers = (
        "giay chung tu", "trich luc khai tu", "giay bao tu", "giay xac nhan tu vong",
        "xac nhan viec chet", "xac nhan su kien chet", "tuyen bo mot nguoi da chet",
        "tuyen bo da chet", "bia mo", "lang mo", "tu tran", "ta the",
    )
    if any(marker in folded for marker in death_markers) and free("bao_tu"):
        return "bao_tu", None, "fallback theo giấy tờ chứng minh sự kiện chết"

    strong_identity = any(marker in folded for marker in (
        "citizen identity", "identity card", "idvnm", "dac diem nhan dang",
        "giay chung minh nhan dan",
    ))
    identity_fields = (
        ("so dinh danh ca nhan" in folded or "personal identification number" in folded)
        and ("ho va ten" in folded or "full name" in folded)
        and ("ngay sinh" in folded or "date of birth" in folded)
    )
    passport = (
        ("passport" in folded or "ho chieu" in folded)
        and ("quoc tich" in folded or "nationality" in folded)
        and ("ngay sinh" in folded or "date of birth" in folded)
    )
    if (strong_identity or ("can cuoc" in folded and identity_fields) or passport) and free("cccd"):
        return "cccd", None, "fallback theo giấy tờ tùy thân"

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
