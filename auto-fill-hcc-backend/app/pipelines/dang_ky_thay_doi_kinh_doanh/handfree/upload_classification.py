"""Phân loại tệp lúc upload (checklist handfree) cho thủ tục Thay đổi nội dung ĐK hộ kinh doanh.

Chỉ là lớp xếp tệp vào checklist khi công dân tải ảnh. Phân loại thành phần hồ sơ trên
HkdOnline vẫn do ``attach/planner.py`` quyết định từ toàn bộ OCR.
"""
import json
import re
import unicodedata

from app.upload_session.llm_classifier import ClassificationSpec


PROCEDURE_KEYS = frozenset({"dang-ky-thay-doi-noi-dung-ho-kinh-doanh"})
_ALLOWED_KEYS = frozenset({"thong_bao", "gcn_cu", "cccd", "uy_quyen", "bien_ban", "khac"})

_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho thủ tục Đăng ký thay đổi nội dung đăng ký hộ kinh doanh.
Mỗi yêu cầu chỉ chứa OCR của ĐÚNG MỘT tệp. Chỉ phân loại tệp đó, không suy diễn từ
tài liệu khác và không trả danh sách.

Chọn đúng một doc_key:
- thong_bao: THÔNG BÁO thay đổi nội dung đăng ký hộ kinh doanh (mẫu thông báo, có mục nội
  dung đăng ký thay đổi: tên/địa chỉ/ngành nghề/chủ hộ/vốn...).
- gcn_cu: GIẤY CHỨNG NHẬN đăng ký hộ kinh doanh đã cấp — tiêu đề "GIẤY CHỨNG NHẬN ĐĂNG KÝ
  HỘ KINH DOANH", có mã số hộ kinh doanh, cơ quan đăng ký cấp.
- cccd: ảnh hoặc bản scan THẺ căn cước/CCCD/CMND/hộ chiếu. Mặt trước và mặt sau đều thuộc
  cccd; mặt sau có thể chỉ có đặc điểm nhận dạng, nơi cấp, chip hoặc dòng MRZ IDVNM.
- uy_quyen: văn bản/giấy ủy quyền cho người khác nộp hồ sơ hoặc làm chủ hộ.
- bien_ban: biên bản họp thành viên hộ gia đình.
- khac: giấy tờ liên quan còn lại (hợp đồng mua bán/tặng cho, văn bản thừa kế...).
- unknown: OCR trống hoặc quá thiếu để xác định an toàn.

Phân loại theo TIÊU ĐỀ và BẢN CHẤT của tài liệu. Thông báo thay đổi vẫn là thong_bao dù
bên trong ghi mã số hộ kinh doanh hoặc số căn cước. TUYỆT ĐỐI không phân loại thành cccd
chỉ vì tài liệu nhắc đến "CCCD" hoặc có 12 chữ số. Chỉ dùng OCR_TEXT làm bằng chứng;
không dùng tên file. Chỉ trả JSON object đúng schema, không giải thích:
{"doc_key":"thong_bao"}
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

    # Thông báo xét trước GCN: thông báo nhắc mã số hộ KD y như GCN nhưng có chữ "thông báo
    # thay đổi"; GCN cũ nhắc "đăng ký hộ kinh doanh" nhưng không có "thay đổi".
    if "thong bao thay doi" in folded and free("thong_bao"):
        return "thong_bao", None, "fallback theo tiêu đề thông báo thay đổi"

    if "giay chung nhan dang ky ho kinh doanh" in folded and free("gcn_cu"):
        return "gcn_cu", None, "fallback theo giấy chứng nhận đã cấp"

    if "bien ban hop" in folded and free("bien_ban"):
        return "bien_ban", None, "fallback theo biên bản họp"

    if "uy quyen" in folded and free("uy_quyen"):
        return "uy_quyen", None, "fallback theo văn bản ủy quyền"

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
