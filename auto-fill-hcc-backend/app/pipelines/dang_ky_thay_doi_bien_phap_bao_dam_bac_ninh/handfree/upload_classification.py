"""Phân loại tệp lúc upload (checklist handfree) cho thủ tục Đăng ký thay đổi biện pháp bảo đảm bằng quyền sử dụng
đất, tài sản gắn liền với đất — tỉnh Bắc Ninh (1.011442).

Chỉ là lớp xếp tệp vào checklist khi công dân tải ảnh/scan. Điền phiếu và định tuyến thành phần hồ sơ trên cổng vẫn do
``process`` / ``attach`` quyết định từ toàn bộ OCR (tệp gộp cả bộ vẫn được chia theo trang ở bước đính kèm).
"""
import json
import re
import unicodedata

from app.upload_session.llm_classifier import ClassificationSpec


PROCEDURE_KEYS = frozenset({"dang-ky-thay-doi-bien-phap-bao-dam-bac-ninh"})
_ALLOWED_KEYS = frozenset({"don", "van_ban_sua_doi", "gcn", "gioi_thieu", "khac"})

_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho thủ tục Đăng ký thay đổi biện pháp bảo đảm bằng quyền sử dụng
đất, tài sản gắn liền với đất (đăng ký thay đổi thế chấp đất đai).
Mỗi yêu cầu chỉ chứa OCR của ĐÚNG MỘT tệp. Chỉ phân loại tệp đó, không suy diễn từ
tài liệu khác và không trả danh sách.

Chọn đúng một doc_key theo GIẤY ĐẦU TIÊN của tệp:
- don: PHIẾU YÊU CẦU ĐĂNG KÝ THAY ĐỔI nội dung biện pháp bảo đảm (Mẫu số 02a). Tệp scan chung cả
  bộ mà Phiếu đứng đầu vẫn là don.
- van_ban_sua_doi: HỢP ĐỒNG / văn bản SỬA ĐỔI, BỔ SUNG hợp đồng thế chấp, văn bản chuyển giao
  quyền đòi nợ, công văn / quyết định làm căn cứ thay đổi (đổi tên, sáp nhập, chấm dứt hoạt động
  của bên nhận bảo đảm).
- gcn: GIẤY CHỨNG NHẬN quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất (sổ đỏ / sổ
  hồng), kể cả trang bổ sung Giấy chứng nhận.
- gioi_thieu: GIẤY GIỚI THIỆU / giấy ủy quyền / văn bản ủy quyền cử người đi nộp hồ sơ.
- khac: giấy tờ liên quan còn lại — hợp đồng thế chấp gốc, căn cước, giấy chứng nhận đăng ký
  doanh nghiệp, giấy tờ khác.
- unknown: OCR trống hoặc quá thiếu để xác định an toàn.

Phân loại theo TIÊU ĐỀ và BẢN CHẤT của tài liệu. Phiếu yêu cầu vẫn là don dù bên trong ghi số
Giấy chứng nhận hay số hợp đồng. Chỉ dùng OCR_TEXT làm bằng chứng; không dùng tên file.
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
    head = folded[:600]
    keys = {item.get("key") for item in required_docs}
    repeatable = {item.get("key") for item in required_docs if item.get("repeatable")}
    sides = {item.get("key"): int(item.get("sides") or 1) for item in required_docs}
    counts = {key: sum(1 for item in existing_files if item.get("doc_key") == key) for key in keys}

    def free(key: str) -> bool:
        return key in keys and (key in repeatable or counts.get(key, 0) < sides.get(key, 1))

    if ("phieu yeu cau dang ky thay doi" in head or "mau so 02a" in head) and free("don"):
        return "don", None, "fallback theo tiêu đề Phiếu yêu cầu đăng ký thay đổi 02a"
    if (("hop dong sua doi" in head and "bo sung" in head) or "chuyen giao quyen doi no" in head
            or "quyet dinh" in head) and free("van_ban_sua_doi"):
        return "van_ban_sua_doi", None, "fallback theo văn bản sửa đổi / căn cứ thay đổi"
    if ("giay chung nhan quyen su dung dat" in head or "trang bo sung giay chung nhan" in head
            or ("quyen su dung dat" in folded and "so vao so" in folded)) and free("gcn"):
        return "gcn", None, "fallback theo Giấy chứng nhận QSDĐ"
    if any(m in head for m in ("giay gioi thieu", "giay uy quyen", "van ban uy quyen")) and free("gioi_thieu"):
        return "gioi_thieu", None, "fallback theo giấy giới thiệu / ủy quyền"
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
