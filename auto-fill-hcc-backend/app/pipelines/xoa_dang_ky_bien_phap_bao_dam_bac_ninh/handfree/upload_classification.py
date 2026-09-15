"""Phân loại tệp lúc upload (checklist handfree) cho thủ tục Xóa đăng ký biện pháp bảo đảm
bằng quyền sử dụng đất, tài sản gắn liền với đất — tỉnh Bắc Ninh (1.011443).

Chỉ là lớp xếp tệp vào checklist khi công dân tải ảnh/scan. Phân loại để điền phiếu và
định tuyến thành phần hồ sơ trên cổng Bắc Ninh vẫn do ``attach/planner.py`` quyết định từ
toàn bộ OCR.
"""
import json
import re
import unicodedata

from app.upload_session.llm_classifier import ClassificationSpec


PROCEDURE_KEYS = frozenset({"xoa-dang-ky-bien-phap-bao-dam-bac-ninh"})
_ALLOWED_KEYS = frozenset({"don", "gcn", "hop_dong", "cccd", "khac"})

_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho thủ tục Xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng
đất, tài sản gắn liền với đất (xóa thế chấp đất đai).
Mỗi yêu cầu chỉ chứa OCR của ĐÚNG MỘT tệp. Chỉ phân loại tệp đó, không suy diễn từ
tài liệu khác và không trả danh sách.

Chọn đúng một doc_key:
- don: PHIẾU YÊU CẦU XÓA đăng ký biện pháp bảo đảm (Mẫu số 03a). Tiêu đề có "PHIẾU YÊU CẦU
  XÓA ĐĂNG KÝ" và nhắc "biện pháp bảo đảm"; thường có xác nhận/con dấu của bên nhận bảo đảm
  (ngân hàng) đồng ý xóa thế chấp.
- gcn: GIẤY CHỨNG NHẬN quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất (sổ đỏ /
  sổ hồng). Có số phát hành, số vào sổ cấp GCN, thông tin thửa đất, tờ bản đồ; có thể kèm
  trang mục IV "Những thay đổi sau khi cấp".
- hop_dong: HỢP ĐỒNG thế chấp / văn bản thanh lý, giải chấp giữa bên thế chấp và ngân hàng.
- cccd: ảnh hoặc bản scan THẺ căn cước/CCCD/CMND/hộ chiếu. Mặt trước và mặt sau đều thuộc
  cccd; mặt sau có thể chỉ có đặc điểm nhận dạng, nơi cấp, chip hoặc dòng MRZ IDVNM.
- khac: giấy tờ liên quan còn lại — giấy giới thiệu, văn bản ủy quyền, giấy tờ khác.
- unknown: OCR trống hoặc quá thiếu để xác định an toàn.

Phân loại theo TIÊU ĐỀ và BẢN CHẤT của tài liệu. Phiếu yêu cầu vẫn là don dù bên trong ghi
số Giấy chứng nhận hoặc số căn cước. TUYỆT ĐỐI không phân loại thành cccd chỉ vì tài liệu
nhắc đến "CCCD" hoặc có 12 chữ số. Chỉ dùng OCR_TEXT làm bằng chứng; không dùng tên file.
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

    # Phiếu yêu cầu xét trước: bên trong nhắc cả GCN, hợp đồng lẫn số căn cước.
    if ("phieu yeu cau xoa" in folded or "mau so 03a" in folded
            or ("phieu yeu cau" in folded and "xoa" in folded and "bien phap bao dam" in folded)) \
            and free("don"):
        return "don", None, "fallback theo tiêu đề Phiếu yêu cầu xóa 03a"

    if ("giay chung nhan quyen su dung dat" in folded
            or ("quyen su dung dat" in folded and "so vao so" in folded)) and free("gcn"):
        return "gcn", None, "fallback theo Giấy chứng nhận QSDĐ"

    if ("hop dong the chap" in folded or "hop dong bao dam" in folded
            or "thanh ly hop dong" in folded or ("giai chap" in folded)) and free("hop_dong"):
        return "hop_dong", None, "fallback theo hợp đồng/giải chấp"

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

    if any(marker in folded for marker in (
        "giay gioi thieu", "van ban uy quyen", "giay uy quyen",
    )) and free("khac"):
        return "khac", None, "fallback theo giấy tờ kèm theo"

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
