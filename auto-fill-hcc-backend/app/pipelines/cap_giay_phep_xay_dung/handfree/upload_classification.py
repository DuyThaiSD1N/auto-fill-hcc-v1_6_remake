"""Phân loại tệp lúc upload (checklist handfree) cho thủ tục Cấp giấy phép xây dựng mới.

Chỉ là lớp xếp tệp vào checklist khi công dân tải lên. Đính thành phần hồ sơ trên cổng
Bộ Xây dựng vẫn do ``attach/planner.py`` quyết định từ toàn bộ OCR.

Công dân hay nộp BẢN SCAN GỘP nhiều giấy trong một PDF (đơn + cam kết + sổ đỏ + chứng chỉ…,
hoặc cả bộ bản vẽ). Một tệp chỉ vào được một dòng, nên xếp theo TRANG ĐẦU của tệp.
"""
import json
import re
import unicodedata

from app.upload_session.llm_classifier import ClassificationSpec


PROCEDURE_KEYS = frozenset({"cap-giay-phep-xay-dung-moi-nha-o-rieng-le"})
_ALLOWED_KEYS = frozenset({"don", "gcn", "ban_ve", "cccd", "khac"})

_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho thủ tục Cấp giấy phép xây dựng mới (nhà ở riêng lẻ,
công trình cấp III, cấp IV). Mỗi yêu cầu chỉ chứa OCR của ĐÚNG MỘT tệp. Tệp có thể là bản
scan GỘP nhiều giấy tờ; khi đó phân loại theo giấy tờ ở TRANG ĐẦU (Trang 1) của tệp.

Chọn đúng một doc_key:
- don: ĐƠN ĐỀ NGHỊ CẤP GIẤY PHÉP XÂY DỰNG (Mẫu số 01), có thông tin chủ đầu tư, địa điểm
  xây dựng, nội dung đề nghị cấp phép. Phía sau đơn có kèm giấy cam kết, sổ đỏ, chứng chỉ…
  vẫn là don nếu trang đầu là đơn.
- gcn: GIẤY CHỨNG NHẬN quyền sử dụng đất / quyền sở hữu nhà ở và tài sản gắn liền với đất
  (sổ đỏ, sổ hồng) hoặc giấy tờ khác về quyền sử dụng đất (quyết định giao đất, hợp đồng
  chuyển nhượng…).
- ban_ve: BẢN VẼ / HỒ SƠ THIẾT KẾ xin phép xây dựng: trang bìa "HỒ SƠ XIN PHÉP XÂY DỰNG",
  "HỒ SƠ THIẾT KẾ", mặt bằng, mặt cắt, mặt đứng, móng, kết cấu, cấp thoát nước, điện, khung
  tên bản vẽ, tỷ lệ 1/100… Chứng chỉ hành nghề / chứng chỉ năng lực hoạt động xây dựng của
  đơn vị, cá nhân thiết kế cũng là ban_ve.
- cccd: ảnh hoặc bản scan THẺ căn cước/CCCD/CMND/hộ chiếu. Mặt trước và mặt sau đều thuộc
  cccd; mặt sau có thể chỉ có đặc điểm nhận dạng, nơi cấp, chip hoặc dòng MRZ IDVNM.
- khac: giấy tờ liên quan còn lại (văn bản ủy quyền, giấy đăng ký doanh nghiệp…).
- unknown: OCR trống hoặc quá thiếu để xác định an toàn.

Phân loại theo TIÊU ĐỀ và BẢN CHẤT của giấy tờ ở trang đầu. Bản vẽ OCR thường lộn xộn, có
chữ rác giống tên cơ quan công an — không vì thế mà chọn cccd. TUYỆT ĐỐI không phân loại
thành cccd chỉ vì tài liệu nhắc đến "CCCD" hoặc có 12 chữ số. Chỉ dùng OCR_TEXT làm bằng
chứng; không dùng tên file.
Chỉ trả JSON object đúng schema, không giải thích:
{"doc_key":"don"}
""".strip()

# Dấu ngăn trang của OCR Tiếng Nói: "───── Trang 2/16 ─────".
_PAGE_BREAK = re.compile(r"─+\s*Trang\s+\d+\s*/\s*\d+\s*─+")


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _first_page(text: str) -> str:
    pages = [p for p in _PAGE_BREAK.split(text or "") if p.strip()]
    return pages[0] if pages else ""


def _build_user_prompt(_file_name: str, text: str, limit: int = 5000) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) > limit:
        compact = compact[:limit] + "..."
    # Không truyền tên file để tên file không trở thành bằng chứng hoặc prompt injection.
    return json.dumps({"ocrText": compact}, ensure_ascii=False)


def _guess(folded: str) -> str | None:
    """Đoán loại giấy theo tiêu đề; thứ tự quan trọng vì đơn nhắc tới cả đất lẫn thiết kế."""
    if "de nghi cap giay phep xay dung" in folded:
        return "don"
    if any(m in folded for m in ("ho so xin phep xay dung", "ho so thiet ke",
                                 "ban ve xin phep", "ban ve xin cap phep")):
        return "ban_ve"
    if "giay chung nhan" in folded and "quyen su dung dat" in folded:
        return "gcn"
    strong_identity = any(m in folded for m in (
        "citizen identity", "identity card", "idvnm", "dac diem nhan dang",
        "giay chung minh nhan dan",
    ))
    card_fields = (
        ("so dinh danh ca nhan" in folded or "personal identification number" in folded)
        and ("ho va ten" in folded or "full name" in folded)
        and ("ngay sinh" in folded or "date of birth" in folded)
    )
    if strong_identity or ("can cuoc" in folded and card_fields):
        return "cccd"
    if any(m in folded for m in ("mat bang", "mat cat", "mat dung", "chung chi hanh nghe",
                                 "chung chi nang luc")):
        return "ban_ve"
    return None


def fallback_to_slot(
    text: str,
    required_docs: list[dict],
    existing_files: list[dict],
    hint_doc_key: str | None,
) -> tuple[str | None, str | None, str]:
    """Fallback tất định khi LLM lỗi/unknown; giữ mọi tệp liên quan trong checklist."""
    keys = {item.get("key") for item in required_docs}
    repeatable = {item.get("key") for item in required_docs if item.get("repeatable")}
    sides = {item.get("key"): int(item.get("sides") or 1) for item in required_docs}
    counts = {
        key: sum(1 for item in existing_files if item.get("doc_key") == key)
        for key in keys
    }

    def free(key: str) -> bool:
        return key in keys and (key in repeatable or counts.get(key, 0) < sides.get(key, 1))

    # Trang đầu trước: bản scan gộp có đủ loại giấy, chỉ trang đầu cho biết tệp là gì.
    doc_key = _guess(_fold(_first_page(text))) or _guess(_fold(text))
    if doc_key and free(doc_key):
        return doc_key, None, "fallback theo tiêu đề trang đầu"

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
