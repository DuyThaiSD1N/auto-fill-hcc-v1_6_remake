"""Phân loại tệp lúc upload cho thủ tục chứng thực bản sao.

CHỈ có tác dụng ở bước Thông tin chủ hồ sơ, khi checklist có HAI ô: căn cước của chủ hồ sơ
(dùng để trợ lý điền form) và giấy tờ cần chứng thực. Ở bước Thành phần hồ sơ checklist chỉ
còn một ô, mà engine chung thoát sớm khi chỉ có một ô — nên bản extension cũ (không bao giờ
có ô thứ hai) không hề đi qua file này, không tốn thêm một lượt OCR hay LLM nào.

Bài toán riêng ở đây: **không phải cứ là căn cước thì thuộc chủ hồ sơ**. Công dân hoàn toàn có
thể mang căn cước của người khác đi chứng thực bản sao — đó là giấy cần chứng thực, không phải
giấy để điền form. Nên việc phân loại phải neo vào họ tên + số định danh mà CỔNG đang hiển thị
ở khối "Thông tin định danh".
"""
import json
import re
import unicodedata

from app.upload_session.llm_classifier import ClassificationSpec


PROCEDURE_KEYS = frozenset({"chung-thuc-ban-sao"})
_OWNER_KEY = "cccd_chu_ho_so"
_AUTHORIZATION_KEY = "giay_uy_quyen"
_ALLOWED_KEYS = frozenset({_OWNER_KEY, _AUTHORIZATION_KEY, "khac"})

_SYSTEM_PROMPT = """
Bạn là bộ phân loại giấy tờ cho thủ tục chứng thực bản sao từ bản chính.
Mỗi yêu cầu chỉ chứa OCR của ĐÚNG MỘT tệp. Chỉ phân loại tệp đó, không suy diễn từ tài liệu
khác và không trả danh sách.

Yêu cầu còn kèm khối "owner" là thông tin chủ hồ sơ đang hiển thị trên cổng dịch vụ công.

Chọn đúng một doc_key:
- cccd_chu_ho_so: tệp là THẺ căn cước công dân/CMND/hộ chiếu, VÀ giấy tờ đó là của ĐÚNG người
  trong khối "owner". Khớp theo SỐ ĐỊNH DANH nếu OCR đọc được số; không đọc được số thì mới
  khớp theo HỌ TÊN. Mặt trước và mặt sau của chính người đó đều thuộc nhóm này.
- giay_uy_quyen: GIẤY/VĂN BẢN/HỢP ĐỒNG ỦY QUYỀN, VÀ **bên ĐƯỢC ủy quyền** (bên B, bên nhận ủy
  quyền) là ĐÚNG người trong khối "owner". Khớp theo số giấy tờ của bên B nếu đọc được; không
  đọc được thì mới khớp theo họ tên bên B.
- khac: MỌI tệp còn lại. Bao gồm cả THẺ CĂN CƯỚC CỦA NGƯỜI KHÁC — công dân có quyền mang căn
  cước của người khác đi chứng thực bản sao, đó là giấy cần chứng thực chứ không phải giấy
  dùng để điền thông tin chủ hồ sơ.
- unknown: OCR trống, quá thiếu để xác định an toàn, HOẶC là giấy ủy quyền mà bên được ủy
  quyền KHÔNG phải người trong khối "owner". Giấy ủy quyền của cặp người khác thì không dùng
  để điền được, mà cũng không phải giấy đem đi chứng thực — trả unknown để người thật xem lại,
  tuyệt đối không xếp vào khac.

Quy tắc bắt buộc:
- Khối "owner" rỗng (không có cả họ tên lẫn số định danh) thì TUYỆT ĐỐI không chọn
  cccd_chu_ho_so cũng không chọn giay_uy_quyen — chọn khac.
- Ô giay_uy_quyen chỉ tồn tại khi checklist có nó. Checklist không có thì giấy ủy quyền đúng
  người cũng chọn khac.
- Chỉ dùng OCR_TEXT làm bằng chứng. Không dùng tên file, không dùng thứ tự file.
- Không chọn cccd_chu_ho_so chỉ vì tài liệu có 12 chữ số hoặc nhắc tới "căn cước": tờ khai,
  giấy ủy quyền, bằng cấp, sổ hộ khẩu đều có thể ghi số căn cước của chủ hồ sơ.
- Họ tên khớp nghĩa là trùng người, chấp nhận khác dấu và khác hoa thường. Trùng một phần
  (chỉ trùng họ, hoặc chỉ trùng tên) KHÔNG phải là khớp.

Chỉ trả JSON object đúng schema, không giải thích:
{"doc_key":"khac"}
""".strip()


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _compact(text: str, limit: int = 5000) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    return compact[:limit] + "..." if len(compact) > limit else compact


def _build_user_prompt(_file_name: str, text: str) -> str:
    # Không truyền tên file để tên file không trở thành bằng chứng hoặc prompt injection.
    return json.dumps({"ocrText": _compact(text)}, ensure_ascii=False)


def _build_user_prompt_with_context(_file_name: str, text: str, context: dict) -> str:
    owner = (context or {}).get("owner") or {}
    return json.dumps({
        "owner": {
            "fullName": str(owner.get("fullName") or "").strip(),
            "identityNumber": str(owner.get("identityNumber") or "").strip(),
        },
        "ocrText": _compact(text),
    }, ensure_ascii=False)


def fallback_to_slot(
    text: str,
    required_docs: list[dict],
    existing_files: list[dict],
    hint_doc_key: str | None,
) -> tuple[str | None, str | None, str]:
    """LLM lỗi hoặc trả unknown → về "giấy tờ cần chứng thực".

    Cố ý KHÔNG dùng `route_to_slot` chung: luật đó suy vai căn cước theo TIỀN TỐ KHÓA, mà khóa
    ở đây bắt đầu bằng "cccd" nên mọi thẻ căn cước sẽ bị hút vào ô chủ hồ sơ — đúng cái sai
    mà file này sinh ra để tránh. Đoán sai vào ô chủ hồ sơ làm tệp biến mất khỏi hồ sơ chứng
    thực; đoán "khac" thì cùng lắm là đính thừa, công dân nhìn thấy và bỏ được.
    """
    _ = existing_files
    keys = {item.get("key") for item in required_docs}
    # Giấy ủy quyền mà LLM không chốt được → KHÔNG dồn vào "giấy cần chứng thực". Ở đây chỉ
    # đọc được chữ, không kiểm được bên được ủy quyền có đúng người đang nộp hay không; đoán
    # sai là đem giấy ủy quyền của người khác đi chứng thực. Để trống loại cho người thật xem.
    folded = _fold(text)
    if any(marker in folded for marker in (
        "giay uy quyen", "van ban uy quyen", "hop dong uy quyen", "ben uy quyen",
    )):
        return None, None, "giấy ủy quyền chưa xác minh được đúng người"
    # Ô công dân tự chọn trên điện thoại vẫn được tôn trọng — đó là ý người thật, không phải đoán.
    if hint_doc_key and hint_doc_key in keys:
        return hint_doc_key, None, "fallback theo mục công dân đã chọn"
    if "khac" in keys:
        return "khac", None, "fallback vào giấy tờ cần chứng thực"
    return None, None, "chưa nhận ra loại giấy tờ"


SPEC = ClassificationSpec(
    system_prompt=_SYSTEM_PROMPT,
    allowed_keys=_ALLOWED_KEYS,
    build_user_prompt=_build_user_prompt,
    build_user_prompt_with_context=_build_user_prompt_with_context,
)
