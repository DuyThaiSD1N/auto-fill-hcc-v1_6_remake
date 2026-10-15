"""Hiểu ý định người dân trong ngữ cảnh state hiện tại (docs/03a §3).

Mọi ý định nói/gõ tự do đều do **LLM** quyết, KHÔNG dùng khớp từ khóa. Chỉ 2 thứ giữ tất định
vì là giao thức/đã chắc chắn: lệnh máy `__action:*`/`__event:*` (chip/watcher) và số điện thoại.

Hai agent LLM tách riêng:
  - agent CHỌN THỦ TỤC (procedure_picker/) — mang danh sách thủ tục của tỉnh, đọc vài lượt hội
    thoại, trả key / gợi ý 2–3 thủ tục khi câu mơ hồ;
  - bộ PHÂN LOẠI Ý ĐỊNH (file này) — hành động của bước đang làm, không mang danh sách thủ tục.
Màn chào (hoặc ngay sau khi trợ lý vừa gợi ý thủ tục) gọi agent chọn thủ tục trước; các bước khác
gọi bộ phân loại trước, chỉ khi nó thấy người dân nhắc tới một thủ tục mới gọi agent chọn thủ tục.
LLM lỗi/không chắc → Intent("unknown"); flow hiện lại card cho người dân tự chọn.

Flow KHÔNG gọi LLM trực tiếp — mọi suy đoán gói gọn ở đây (router gọi `resolve`).
"""
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

from app.channels.handfree.chat import procedure_picker, store
from app.channels.handfree.procedure_registry import get_procedure, procedure_code, public_list
from app.services.llm.client import chat as llm_chat

_CODE_ONLY_RE = re.compile(r"^(?:ma\s*(?:so\s*)?(?:thu\s*tuc\s*)?[:\s]*)?([12]\.\d{6})[.\s]*$")

logger = logging.getLogger(__name__)


@dataclass
class Intent:
    kind: str                      # action | event | pick_procedure | pick_doc_method |
                                   # confirm | deny | provide_phone | ask_question | unknown
    value: str = ""               # action name / event name / procedure_key / doc method...
    payload: dict = field(default_factory=dict)


def fold(s: str) -> str:
    """Bỏ dấu + thường hoá + gộp khoảng trắng — chuẩn khớp text toàn dự án."""
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", s.replace("Đ", "D").replace("đ", "d")).strip().lower()


# "profile" (Lấy dữ liệu đã lưu) tạm ẨN khỏi UI + LLM (xem _doc_options_card). Để bật lại: thêm
# "profile" vào set này + mô tả tương ứng vào _DOC_METHOD_DESC.
_DOC_METHODS = {"qr", "scan"}

# Mô tả các cách cung cấp giấy tờ cho LLM. BẮT BUỘC vì tên value trần (qr/scan) khiến LLM đoán mò:
# "chụp bằng điện thoại" bị hiểu "chụp"≈"scan" → chọn nhầm scan. Thứ tự KHỚP card
# (_doc_options_card: qr, scan) nên "cách 1/2" cũng suy ra được.
_DOC_METHOD_DESC: dict[str, str] = {
    "qr": 'dùng ĐIỆN THOẠI chụp/gửi ảnh giấy tờ (quét mã QR). Câu như "chụp bằng điện thoại", '
          '"chụp ảnh", "quét mã", "dùng điện thoại", "cách 1", "cái đầu".',
    "scan": 'dùng MÁY TÍNH tại quầy: đã có sẵn ảnh/PDF/tệp trong máy hoặc scan bản cứng rồi chọn '
            'tệp. Câu như "scan tại quầy", "tải tệp lên", "chọn file trong máy", "upload", "cách 2".',
}


def _doc_method_block() -> str:
    return "\n" + "\n".join(f'    · "{k}" = {v}' for k, v in _DOC_METHOD_DESC.items())

# ── Bảng ý định NÓI/GÕ theo state — nguồn CHÂN LÝ cho value + mô tả (LLM dịch câu về value).
# LLM chỉ được trả value liệt kê ở đây; parse xong validate lại, không cho bịa lệnh.
# delete_data CỐ TÌNH vắng mặt: lệnh xóa dữ liệu chỉ đi qua chip bấm tường minh.
_STATE_INTENTS: dict[str, list[dict]] = {
    # Mỗi thủ tục khai "trường hợp giải quyết" riêng trong registry (variants.options) nên danh
    # sách này là HỢP của mọi biến thể đang dùng; flow còn validate lại theo đúng thủ tục hiện
    # tại nên value của thủ tục khác lọt vào cũng bị loại. Đường chính vẫn là bấm chip (tất định).
    "choose_variant": [
        {"kind": "action", "value": "variant_cap_moi",
         "desc": "muốn CẤP MỚI giấy phép (chưa có giấy phép, xin cấp lần đầu)"},
        {"kind": "action", "value": "variant_cap_lai",
         "desc": "muốn CẤP LẠI giấy phép (đã có nhưng bị mất, hư hỏng, hết hạn hoặc đổi thông tin)"},
        {"kind": "action", "value": "variant_nha_o_rieng_le",
         "desc": "xin phép xây NHÀ Ở RIÊNG LẺ của hộ gia đình, cá nhân"},
        {"kind": "action", "value": "variant_cong_trinh",
         "desc": "xin phép xây CÔNG TRÌNH cấp III, cấp IV (không phải nhà ở riêng lẻ)"},
    ],
    # Sửa nơi làm / đối tượng bằng lời: agent nơi làm (place_picker/) lấy tỉnh, xã, đối tượng ra
    # rồi flow áp như chọn trên card. "Không phải + nơi khác" là SỬA, không phải từ chối thủ tục.
    "confirm_procedure": [
        {"kind": "action", "value": "change_place",
         "desc": "muốn ĐỔI nơi làm thủ tục (tỉnh/thành phố, phường/xã) hoặc ĐỔI người/đối tượng thực "
                 "hiện (làm cho bản thân, cho người khác, được người khác ủy quyền, doanh nghiệp ủy "
                 "quyền, đại diện cơ quan) — kể cả câu mở đầu bằng \"không phải\" rồi nêu nơi/người khác"},
    ],
    # Hộp thoại "Chọn trường hợp giải quyết" (cổng Bộ Xây dựng): lựa chọn đọc từ cổng nên chỉ
    # nhận SỐ THỨ TỰ; flow chỉ áp khi đang hỏi đúng một ô (nơi xử lý HOẶC trường hợp).
    "choose_mae_dialog": [
        {"kind": "action", "value": f"mae_pick_{n}",
         "desc": f"chọn lựa chọn số {n} (thứ {word}) trong danh sách đang hỏi"}
        for n, word in ((1, "nhất"), (2, "hai"), (3, "ba"), (4, "tư"), (5, "năm"), (6, "sáu"))
    ],
    "guide_login": [
        {"kind": "event", "value": "sso_success",
         "desc": "báo đã đăng nhập xong / đã vào được trang kê khai"},
    ],
    "consent": [
        {"kind": "action", "value": "consent_decline",
         "desc": "KHÔNG đồng ý cho xử lý dữ liệu / muốn tự nhập tay"},
        {"kind": "action", "value": "consent_agree",
         "desc": "đồng ý cho Trợ lý đọc giấy tờ và tự động điền (khẳng định tường minh)"},
    ],
    "qr_waiting": [
        {"kind": "action", "value": "reshow_qr",
         "desc": "không quét được mã / muốn hiện lại mã QR"},
        {"kind": "action", "value": "docs_done",
         "desc": "không muốn quét hoặc thêm tệp nữa, muốn dùng các tệp hiện có để điền/đính kèm lại ngay"},
        {"kind": "event", "value": "docs_complete",
         "desc": "báo đã chụp/gửi đủ giấy tờ, hoặc giục xử lý/điền luôn"},
    ],
    "collecting_docs": [
        {"kind": "action", "value": "docs_done",
         "desc": "đã điều chỉnh xong, không muốn thêm tệp nữa và muốn điền/đính kèm lại ngay"},
        {"kind": "event", "value": "docs_complete",
         "desc": "báo đã chụp/gửi đủ giấy tờ, hoặc giục đọc/xử lý/điền form; KHÔNG phải yêu cầu đính kèm"},
        {"kind": "action", "value": "request_attach",
         "desc": "muốn đính kèm/chuyển sang phần đính kèm khi trang hiện tại vẫn là kê khai"},
        {"kind": "action", "value": "reshow_qr",
         "desc": "muốn chụp lại / hiện lại mã QR"},
    ],
    "owner_waiting_next": [
        {"kind": "action", "value": "retry_owner_fill",
         "desc": "yêu cầu điền lại thông tin chủ hồ sơ, ví dụ 'điền đi', 'điền lại', 'thử lại'"},
    ],
    "filling": [
        {"kind": "action", "value": "request_attach",
         "desc": "muốn đính kèm/chuyển sang đính kèm ngay khi vẫn đang ở trang kê khai"},
    ],
    "reviewing": [
        {"kind": "action", "value": "confirm_review",
         "desc": "xác nhận rõ đã rà soát và form đã đúng/chuẩn, cho đính kèm giấy tờ"},
        {"kind": "action", "value": "request_attach",
         "desc": "chỉ yêu cầu đính kèm/chuyển sang đính kèm, chưa nói đã rà soát form"},
        {"kind": "action", "value": "refill",
         "desc": "chê form điền sai, muốn điền lại"},
        {"kind": "action", "value": "add_documents",
         "desc": "muốn xem, thêm hoặc xóa giấy tờ rồi điền lại tờ khai"},
    ],
    "attaching": [
        {"kind": "action", "value": "request_attach",
         "desc": "giục đính kèm giấy tờ hoặc hỏi chuyển qua phần đính kèm"},
        {"kind": "action", "value": "refill",
         "desc": "muốn quay lại điền lại thông tin kê khai/form/tờ khai"},
        {"kind": "action", "value": "add_documents",
         "desc": "đang còn ở trang kê khai và muốn điều chỉnh giấy tờ trước khi điền lại"},
    ],
    "choosing_attach_mode": [
        {"kind": "action", "value": "attach_mode_merge",
         "desc": "muốn đưa tất cả tài liệu vào cùng một hồ sơ"},
        {"kind": "action", "value": "attach_mode_split",
         "desc": "muốn mỗi tài liệu là một hồ sơ riêng / tách thành nhiều hồ sơ"},
    ],
    "done": [
        # save_profile tạm ẨN cùng option "Lấy dữ liệu đã lưu" (nút Lưu hồ sơ đã gỡ khỏi done).
        # KHÔNG có "đã nộp" bằng lời: event submitted chấm mốc NỘP HỒ SƠ cho thống kê, một câu "nộp
        # đi" bị hiểu nhầm là đếm sai. Mốc nộp chỉ lấy từ cú bấm nút nộp / trang thành công của cổng.
        {"kind": "action", "value": "add_documents",
         "desc": "muốn bổ sung, thêm hoặc xóa bớt giấy tờ trước khi nộp hồ sơ"},
    ],
}

# Lệnh dùng được ở MỌI state.
_GLOBAL_INTENTS: list[dict] = [
    {"kind": "action", "value": "new_procedure",
     "desc": "muốn bỏ thủ tục đang làm, chọn thủ tục khác mà CHƯA nêu tên thủ tục mới (nêu tên → kind procedure)"},
]


def _resolve_machine(message: str) -> Intent | None:
    """Nhánh TẤT ĐỊNH: lệnh máy (chip/watcher) + số điện thoại. None nếu là câu tự do (→ LLM)."""
    text = str(message or "").strip()

    # Lệnh máy từ chip/card/watcher — bỏ qua mọi suy đoán.
    if text.startswith("__event:"):
        # __event:<name>[:<chi tiết>] — chi tiết là JSON object thì thành payload
        # (page_status, agency_selected...), còn lại (vd thông điệp lỗi) vào payload.value.
        rest = text[len("__event:"):]
        name, _, detail = rest.partition(":")
        payload: dict = {}
        if detail:
            if detail.lstrip().startswith("{"):
                try:
                    parsed = json.loads(detail)
                    payload = parsed if isinstance(parsed, dict) else {"value": detail}
                except (ValueError, TypeError):
                    payload = {"value": detail}
            else:
                payload = {"value": detail}
        return Intent("event", name, payload)
    if text.startswith("__action:"):
        rest = text[len("__action:"):]
        name, _, raw = rest.partition(":")
        payload = {}
        if raw:
            try:
                payload = json.loads(raw)
            except (ValueError, TypeError):
                payload = {"value": raw}
        return Intent("action", name, payload)

    # Số điện thoại đọc/gõ (done: đăng ký thông báo; ask_doc_method: tra profile) — regex trích,
    # không cần LLM.
    cleaned = re.sub(r"[\s.\-()]", "", text)
    m = re.search(r"(?<!\d)(?:\+84|0)\d{9,10}(?!\d)", cleaned)
    if m:
        return Intent("provide_phone", m.group(0))

    return None


def resolve_deterministic(message: str, state: str | None = None) -> Intent | None:
    """Nhánh TẤT ĐỊNH duy nhất còn lại: lệnh máy + số điện thoại (state không còn ảnh hưởng).
    Câu tự do → None (router gọi `resolve` để LLM phân loại)."""
    return _resolve_machine(message)


def resolve_logout_choice(message: str) -> str | None:
    """Khi ĐANG hỏi "đăng xuất / nộp thêm hồ sơ" (2 nút sau đánh giá): công dân NÓI/GÕ câu tương
    đương thì nhận diện tất định, trả "logout_citizen" / "continue_dossiers" / None.

    Cần vì chế độ rảnh tay gửi GIỌNG NÓI dạng text tự do — LLM hay trả unknown → trợ lý báo "chưa
    nhận rõ yêu cầu" dù công dân đã nói "đăng xuất". CHỈ gọi khi đang chờ lựa chọn nên "có" đứng một
    mình cũng hiểu là đồng ý đăng xuất; "không"/"nộp thêm" là ở lại nộp tiếp."""
    t = fold(message)
    if not t:
        return None
    # Phủ định / nộp thêm — kiểm TRƯỚC vì "không đăng xuất" cũng chứa "dang xuat".
    if any(k in t for k in (
        "nop them", "khong", "chua", "o lai", "tiep tuc", "lam tiep", "con ho so", "them ho so", "van lam",
    )):
        return "continue_dossiers"
    # Đồng ý đăng xuất / kết thúc.
    if any(k in t for k in (
        "dang xuat", "dang xuat tai khoan", "thoat", "log out", "logout", "ket thuc", "xong roi", "roi di",
        "dong y", "dung vay", "dung roi",
    )):
        return "logout_citizen"
    # "Có"/"ừ"/"vâng" đứng một mình = đồng ý (đang trả lời đúng câu hỏi đăng xuất).
    if t in ("co", "co a", "co.", "u", "um", "vang", "vang a", "ok, dang xuat", "ok"):
        return "logout_citizen"
    return None


# ── Trả lời MỘT ô của tờ khai (vòng bổ sung ô trống, flow.field_review_question) ──
# Câu công dân nói lúc này là GIÁ TRỊ của ô, nên không đi qua bộ phân loại ý định chung. Đường
# tất định đi trước (trùng hẳn một lựa chọn, ngày viết bằng số); còn lại để LLM chuẩn hoá rồi
# KIỂM LẠI: ô chọn phải ra đúng một lựa chọn có trên cổng, ô ngày phải ra ngày có thật.

# Danh sách dài hơn (Quốc gia ~250 nước) chỉ đưa vài ví dụ cho LLM; khớp tên do bước kiểm lại lo.
_FIELD_OPTIONS_FOR_LLM = 120
_PLACE_PREFIX_RE = re.compile(r"^(?:tinh|thanh pho|phuong|xa|thi tran|dac khu|quan|huyen)\s+")
# Chỉ dùng khi LLM lỗi: không có nó thì câu "bỏ qua" bị điền thẳng vào ô chữ.
_FIELD_FALLBACK_SKIP = {"bo qua", "bo qua o nay", "khong co", "khong biet", "de trong", "qua"}
_FIELD_FALLBACK_STOP = {"dung", "dung lai", "thoi", "dung bo sung", "khong hoi nua"}

_FIELD_ANSWER_SYSTEM = """Bạn giúp trợ lý điền tờ khai hành chính. Trợ lý vừa hỏi công dân MỘT ô trên tờ khai:
- Ô: {label}
- Loại ô: {kind}{options}

Đọc câu trả lời của công dân và trả DUY NHẤT một JSON:
{{"action": "<answer|skip|back|stop|unclear>", "value": "<giá trị>"}}

- answer: công dân nói giá trị cho ô này → value là giá trị đã chuẩn hoá:
  + ô ngày: "dd/mm/yyyy" (vd "mười lăm tháng ba năm một chín chín mươi" → "15/03/1990"); ô năm: "yyyy";
  + ô chọn: chép NGUYÊN VĂN đúng một lựa chọn trong danh sách, gần nghĩa nhất với câu; không lựa
    chọn nào khớp → unclear;
  + ô chữ: đúng nội dung công dân nói, bỏ lời đệm ("dạ", "là", "ghi là", "của tôi là"); họ tên và
    địa danh viết hoa chữ cái đầu mỗi từ; số giấy tờ, số điện thoại viết liền các chữ số.
- skip: muốn bỏ qua ô này, không có, không biết, để trống.
- back: muốn sửa lại ô vừa điền ngay trước đó.
- stop: muốn dừng hỏi, tự điền tiếp, hoặc chuyển sang việc khác.
- unclear: không hiểu được câu.

Câu có thể đến từ NHẬN GIỌNG NÓI: không dấu, sai chính tả, số đọc thành chữ, nghe nhầm âm gần
giống — hiểu theo nghĩa gần nhất. Chỉ trả JSON, không giải thích."""


def _strip_answer(text: str) -> str:
    """Bỏ khoảng trắng, ngoặc kép và dấu câu nhận giọng nói hay gắn vào cuối câu."""
    return re.sub(r"^[\s\"'“”«»]+|[\s\"'“”«».,!?…;:]+$", "", str(text or ""))


def match_field_option(value: str, options: list[str]) -> str | None:
    """Khớp tất định một câu với danh sách lựa chọn của ô; mơ hồ (nhiều lựa chọn) → None.

    Thứ tự: trùng hẳn (bỏ dấu) → trùng khi bỏ tiền tố hành chính ("hiệp hòa" ↔ "Phường Hiệp
    Hòa") → câu nằm trọn trong đúng MỘT lựa chọn. "Nam" trùng hẳn lựa chọn "Nam" nên không
    bị coi là mơ hồ với "Việt Nam".
    """
    want = fold(_strip_answer(value))
    if not want:
        return None
    folded = [(option, fold(option)) for option in options or [] if str(option or "").strip()]
    for option, text in folded:
        if text == want:
            return option
    bare_want = _PLACE_PREFIX_RE.sub("", want)
    bare = [option for option, text in folded if _PLACE_PREFIX_RE.sub("", text) == bare_want]
    if len(bare) == 1:
        return bare[0]
    if len(bare_want) >= 3:
        pattern = re.compile(rf"(?:^|\W){re.escape(bare_want)}(?:\W|$)")
        inside = [option for option, text in folded if pattern.search(text)]
        if len(inside) == 1:
            return inside[0]
    return None


def normalize_field_date(value: str, year_only: bool = False) -> str | None:
    """Ngày viết bằng số → "dd/mm/yyyy" (ô năm → "yyyy"); ngày không có thật → None."""
    numbers = re.findall(r"\d+", str(value or ""))
    if year_only:
        years = [n for n in numbers if len(n) == 4 and 1900 <= int(n) <= 2100]
        return years[-1] if years else None
    if len(numbers) < 3 or len(numbers[2]) != 4:
        return None
    day, month, year = (int(n) for n in numbers[:3])
    try:
        date(year, month, day)
    except ValueError:
        return None
    return f"{day:02d}/{month:02d}/{year}"


def _field_answer(field: dict, value: str, heard: str) -> Intent:
    """Kiểm lại giá trị theo loại ô; không hợp lệ → hỏi lại chứ không điền bừa."""
    kind = str(field.get("kind") or "text")
    options = [str(o) for o in field.get("options") or []]
    if kind in ("select", "radio") and options:
        picked = match_field_option(value, options)
        if not picked:
            return Intent("action", "field_review_unclear", {"heard": heard, "reason": "no_option"})
        return Intent("action", "field_review_answer", {"value": picked, "heard": heard})
    if kind == "date":
        normalized = normalize_field_date(value, bool(field.get("yearOnly")))
        if not normalized:
            return Intent("action", "field_review_unclear", {"heard": heard})
        return Intent("action", "field_review_answer", {"value": normalized, "heard": heard})
    cleaned = _strip_answer(value)
    if not cleaned:
        return Intent("action", "field_review_unclear", {"heard": heard})
    return Intent("action", "field_review_answer", {"value": cleaned[:300], "heard": heard})


def _field_kind_desc(field: dict) -> str:
    kind = str(field.get("kind") or "text")
    if kind == "date":
        return "ô năm" if field.get("yearOnly") else "ô ngày (ngày/tháng/năm)"
    if kind in ("select", "radio"):
        return "ô chọn một lựa chọn trong danh sách"
    return "ô chữ"


def _field_options_block(field: dict) -> str:
    options = [str(o) for o in field.get("options") or [] if str(o or "").strip()]
    if not options:
        return ""
    if len(options) <= _FIELD_OPTIONS_FOR_LLM:
        return "\n- Danh sách lựa chọn:\n" + "\n".join(f"  + {o}" for o in options)
    return (f"\n- Danh sách dài {len(options)} lựa chọn (vd: {', '.join(options[:20])}…): "
            "ghi đúng tên công dân nói, có dấu.")


async def resolve_field_answer(text: str, field: dict, *, can_go_back: bool = False) -> Intent:
    """Câu công dân trả lời ô đang hỏi → field_review_answer / _skip / _back / _stop / _unclear."""
    heard = str(text or "").strip()[:300]
    kind = str(field.get("kind") or "text")
    options = [str(o) for o in field.get("options") or []]
    # Đường tất định: chọn đúng tên một lựa chọn, hoặc đọc ngày bằng số — không tốn lượt LLM.
    if kind in ("select", "radio") and match_field_option(heard, options):
        return _field_answer(field, heard, heard)
    if kind == "date" and normalize_field_date(heard, bool(field.get("yearOnly"))):
        return _field_answer(field, heard, heard)
    label = str(field.get("label") or "")
    if field.get("section"):
        label = f"{label} (mục {field['section']})"
    try:
        raw = await llm_chat(
            [
                {"role": "system", "content": _FIELD_ANSWER_SYSTEM.format(
                    label=label, kind=_field_kind_desc(field), options=_field_options_block(field))},
                {"role": "user", "content": heard},
            ],
            temperature=0.0,
            max_tokens=120,
        )
        m = re.search(r"\{[\s\S]*\}", raw or "")
        data = json.loads(m.group(0)) if m else {}
        action = str(data.get("action") or "unclear")
        if action == "answer":
            return _field_answer(field, str(data.get("value") or ""), heard)
        if action == "back" and not can_go_back:
            return Intent("action", "field_review_unclear", {"heard": heard})
        if action in ("skip", "back", "stop"):
            return Intent("action", f"field_review_{action}", {"heard": heard})
        return Intent("action", "field_review_unclear", {"heard": heard})
    except Exception as e:  # noqa: BLE001 — LLM là best-effort, vòng bổ sung phải sống tiếp
        logger.warning("[intents] LLM hiểu câu trả lời ô lỗi: %s", e)
    folded = fold(_strip_answer(heard))
    if folded in _FIELD_FALLBACK_SKIP:
        return Intent("action", "field_review_skip", {"heard": heard})
    if folded in _FIELD_FALLBACK_STOP:
        return Intent("action", "field_review_stop", {"heard": heard})
    return _field_answer(field, heard, heard)


def _state_action_block(state: str) -> str:
    entries = _GLOBAL_INTENTS + _STATE_INTENTS.get(state, [])
    if not entries:
        return ' (bước này không có state_action nào → đừng dùng kind "state_action")'
    return "\n" + "\n".join(f'  + "{e["value"]}": người dân {e["desc"]}' for e in entries)


_LLM_SYSTEM = """Bạn là bộ phân loại ý định cho trợ lý thủ tục hành chính công Việt Nam.
Người dân đang ở bước "{state}". Đọc câu MỚI NHẤT của họ (các lượt trước chỉ là ngữ cảnh) và trả
DUY NHẤT một JSON:
{{"kind": "<button|procedure|pick_doc_method|state_action|confirm|deny|ask_question|unknown>", "value": "<xem dưới>"}}

- button: câu của người dân làm ĐÚNG việc của một NÚT ĐANG HIỆN trên màn hình (nói thay cho bấm
  nút) → value = SỐ của nút đó trong danh sách NÚT ĐANG HIỆN. Ưu tiên button hơn mọi kind khác khi
  câu khớp rõ một nút; không khớp rõ nút nào → xét các kind dưới.{buttons}

- procedure: người dân muốn LÀM hoặc ĐỔI SANG một thủ tục hành chính (nêu tên hoặc mô tả thủ tục,
  kể cả nói tắt, sai chính tả) → value = "" (một agent khác sẽ xác định đúng thủ tục). Chỉ dùng
  khi câu thể hiện MUỐN LÀM thủ tục; hỏi thông tin về thủ tục → ask_question.
- pick_doc_method: khi người dân CHỌN hoặc ĐỔI cách cung cấp giấy tờ — kể cả đang ở bước chụp/quét QR
  mà muốn ĐỔI sang cách kia (vd đang QR nói "scan đi", đang scan nói "chụp bằng điện thoại") →
  value là MỘT trong:{doc_methods}
  CHÚ Ý QUAN TRỌNG: "chụp"/"chụp ảnh"/"chụp bằng điện thoại"/"dùng điện thoại" LUÔN là "qr"
  (KHÔNG phải "scan" — dù chữ "chụp" nghĩa gần "quét"). "scan"/"tải tệp"/"chọn file" mới là "scan".
- state_action: hành động của bước hiện tại → value là MỘT trong:{state_actions}
  Tại bước collecting_docs/filling/reviewing/attaching: câu chỉ nói "đính kèm đi", "chuyển qua
  đính kèm" mà CHƯA xác nhận đã rà soát form → request_attach; KHÔNG coi là docs_complete.
  Chỉ dùng confirm_review khi người dân nói rõ form đã đúng/đã rà soát xong/chuẩn rồi.
- confirm / deny: đồng ý / từ chối câu trợ lý vừa hỏi → value = "". Câu trả lời có/không mà màn
  hình đang có NÚT tương ứng (vd "không cần chứng thực" ↔ nút "Không chứng thực") → dùng button.
  Ở bước confirm_procedure: "không phải" rồi nêu NƠI hoặc NGƯỜI khác → state_action change_place,
  KHÔNG phải deny; deny chỉ khi công dân không muốn làm THỦ TỤC này.
  Ở bước consent: "đồng ý", "đồng ý tất cả", "đồng ý hết", "chọn tất cả" là ĐỒNG Ý cho xử lý dữ
  liệu (consent_agree / nút đồng ý).
- ask_question: hỏi thông tin (lệ phí, thời gian, giấy tờ cần...) → value = câu hỏi rút gọn.
- unknown: không xếp được → value = "".

Câu có thể đến từ NHẬN GIỌNG NÓI: có thể không dấu, sai chính tả, nghe nhầm âm gần giống — hiểu
theo nghĩa gần nhất.

LƯU Ý: câu có "chưa"/"không"/"chưa được" là PHỦ ĐỊNH — KHÔNG coi là hành động đã-xong
(vd "chưa đăng nhập được" KHÔNG phải sso_success). Chỉ trả JSON, không giải thích.

Câu của người dân CÓ THỂ là TIẾNG MÔNG (Hmong, chữ RPA — vd "kuv xav cuv npe yug me nyuam" =
tôi muốn đăng ký khai sinh → procedure; "thaij duab xov tooj" = chụp bằng điện thoại → "qr";
"pom zoo"/"yog" = đồng ý; "tsis yog"/"tsis pom zoo" = từ chối). Hiểu nghĩa rồi phân loại y như câu
tiếng Việt."""

_CLASSIFIER_HISTORY_TURNS = 4


def _free_text_unknown() -> Intent:
    # Đánh dấu "câu gõ/nói không nhận ra" để màn chào nói "chưa nhận ra" thay vì chào lại.
    return Intent("unknown", payload={"free_text": True})


# ── Trả lời câu hỏi lại "thủ tục A hay B?" ──
# Công dân thường chỉ nói PHẦN RIÊNG của tên ("liên thông", "đối tượng bảo trợ") hoặc thứ tự ("cái thứ
# hai"). Nhận tất định những câu chắc chắn; còn lại để agent chọn thủ tục ghép với gợi ý như cũ.
_CANDIDATE_MAX_WORDS = 15          # câu dài thường kể chuyện, để LLM hiểu
_ORDINAL_MAX_WORDS = 6             # "tôi là con thứ hai trong nhà" không phải chọn thứ tự
_CANDIDATE_NEGATION_RE = re.compile(r"(?:^|\s)(?:khong|chua|thoi)(?:\s|$)")
_CANDIDATE_FILLER = {"thu", "tuc", "cho", "va", "cua", "lam", "cai"}
_ORDINAL_RE = [
    (0, re.compile(r"(?:^|\s)(?:thu nhat|thu 1|so 1|dau tien|cai dau|cai truoc)(?:\s|$)")),
    (1, re.compile(r"(?:^|\s)(?:thu hai|thu 2|so 2)(?:\s|$)")),
    (2, re.compile(r"(?:^|\s)(?:thu ba|thu 3|so 3)(?:\s|$)")),
    (-1, re.compile(r"(?:^|\s)(?:cuoi|cuoi cung|cai sau|sau cung)(?:\s|$)")),
]


def _name_words(proc: dict) -> list[str]:
    name = proc.get("shortLabel") or proc.get("label") or ""
    return [w for w in re.findall(r"[a-z0-9]+", fold(name)) if w not in _CANDIDATE_FILLER]


def match_candidate_procedure(text: str, candidates: list[dict]) -> str:
    """Câu trả lời cho câu hỏi lại → key thủ tục, hoặc "" khi chưa chắc (để LLM xử).

    Thứ tự: nói đủ cả tên một thủ tục ("đăng ký khai sinh" ⊂ chỉ bản đơn lẻ, vì bản liên thông còn
    chữ "liên thông") → nói phần riêng của tên ("liên thông") → nói thứ tự ("cái thứ hai"). Câu có
    phủ định ("không phải liên thông") luôn để LLM hiểu.
    """
    said = fold(_strip_answer(text))
    words = said.split()
    if not words or len(words) > _CANDIDATE_MAX_WORDS or len(candidates) < 2:
        return ""
    if _CANDIDATE_NEGATION_RE.search(said):
        return ""
    said_words = set(re.findall(r"[a-z0-9]+", said))
    names = [_name_words(p) for p in candidates]
    full = [p["key"] for p, name in zip(candidates, names) if name and set(name) <= said_words]
    if len(full) == 1:
        return full[0]
    hits = []
    for i, (proc, name) in enumerate(zip(candidates, names)):
        others = {w for j, other in enumerate(names) if j != i for w in other}
        own = set(name) - others
        if own and len(own & said_words) >= min(2, len(own)):
            hits.append(proc["key"])
    if len(hits) == 1:
        return hits[0]
    if not hits and len(words) <= _ORDINAL_MAX_WORDS:
        for index, pattern in _ORDINAL_RE:
            if pattern.search(said) and -len(candidates) <= index < len(candidates):
                return candidates[index]["key"]
    return ""


async def _pick_procedure(text: str, conv: dict) -> Intent | None:
    """Agent chọn thủ tục → Intent. None = câu không nói về thủ tục nào."""
    res = await procedure_picker.pick(text, conv)
    if res.result == "pick":
        return Intent("pick_procedure", res.key)
    if res.result == "ask_about":
        return Intent("ask_question", text, {"procedure_key": res.key} if res.key else {})
    if res.result == "unclear":
        return Intent("procedure_unclear", "", {"candidates": list(res.candidates)})
    if res.result == "error":
        return _free_text_unknown()
    return None


def voice_buttons(conv: dict, state: str) -> list[dict]:
    """Các nút của lượt trợ lý gần nhất mà câu nói được phép thay (flow.voice_options lưu)."""
    stored = conv.get("voice_options") or {}
    if stored.get("state") != state:
        return []
    return [item for item in stored.get("items") or [] if isinstance(item, dict) and item.get("send")]


def _buttons_block(buttons: list[dict]) -> str:
    if not buttons:
        return '\n  (bước này không có nút nào → đừng dùng kind "button")'
    lines = []
    for n, b in enumerate(buttons, 1):
        desc = f" — {b['desc']}" if b.get("desc") else ""
        lines.append(f"    [{n}] {b.get('label') or ''}{desc}")
    return "\n  NÚT ĐANG HIỆN:\n" + "\n".join(lines)


def _as_index(value) -> int:
    try:
        return int(str(value).strip().strip("[]"))
    except (TypeError, ValueError):
        return 0


def _button_intent(button: dict) -> Intent | None:
    """Nút được chọn bằng lời → đúng lệnh máy của nút đó (đi qua cùng code như khi bấm)."""
    intent = _resolve_machine(str(button.get("send") or ""))
    if intent is None or intent.kind not in ("action", "event"):
        return None
    if button.get("phase") and isinstance(intent.payload, dict):
        intent.payload.setdefault("phase", button["phase"])
    # Đánh dấu để flow biết lượt này do LỜI NÓI chọn nút: nút cần extension gom dữ liệu trên
    # trang (ownerFields, ngữ cảnh trang) thì nhờ extension bấm hộ thay vì chạy thẳng.
    intent.payload = {**(intent.payload or {}), "_voice_button": str(button.get("send") or "")}
    return intent


async def _classify(text: str, state: str, conv: dict) -> Intent:
    """Bộ phân loại ý định của bước đang làm (1 lượt LLM, không mang danh sách thủ tục)."""
    buttons = voice_buttons(conv, state)
    try:
        raw = await llm_chat(
            [
                {"role": "system", "content": _LLM_SYSTEM.format(
                    state=state, state_actions=_state_action_block(state),
                    doc_methods=_doc_method_block(), buttons=_buttons_block(buttons))},
                *store.recent_dialogue(conv, _CLASSIFIER_HISTORY_TURNS),
                {"role": "user", "content": text[:500]},
            ],
            temperature=0.0,
            max_tokens=120,
        )
        m = re.search(r"\{[\s\S]*\}", raw or "")
        data = json.loads(m.group(0)) if m else {}
        kind = str(data.get("kind", "unknown"))
        value = str(data.get("value", ""))
        state_values = {e["value"] for e in _GLOBAL_INTENTS + _STATE_INTENTS.get(state, [])}
        if kind in state_values:
            # Model nhỏ đôi khi ghi thẳng tên hành động vào "kind" ({"kind":"confirm_review"}).
            kind, value = "state_action", kind

        if kind == "button":
            n = _as_index(value)
            button = buttons[n - 1] if 1 <= n <= len(buttons) else None
            picked = _button_intent(button) if button else None
            return picked or _free_text_unknown()
        if kind == "procedure":
            return Intent("procedure")
        if kind == "pick_doc_method":
            return Intent("pick_doc_method", value) if value in _DOC_METHODS else _free_text_unknown()
        if kind == "state_action":
            # Chỉ chấp nhận value có trong bảng của state — không cho bịa lệnh.
            entry = next((e for e in _GLOBAL_INTENTS + _STATE_INTENTS.get(state, [])
                          if e["value"] == value), None)
            return Intent(entry["kind"], entry["value"]) if entry else _free_text_unknown()
        if kind == "confirm":
            return Intent("confirm")
        if kind == "deny":
            return Intent("deny")
        if kind == "ask_question":
            return Intent("ask_question", value or text)
    except Exception as e:  # noqa: BLE001 — LLM là best-effort, flow phải sống tiếp
        logger.warning("[intents] LLM phân loại lỗi: %s", e)

    return _free_text_unknown()


async def resolve(message: str, state: str, conv: dict | None = None) -> Intent:
    # (1) Lệnh máy + số điện thoại: tất định tuyệt đối, không đụng LLM.
    machine = _resolve_machine(message)
    if machine is not None:
        return machine

    text = str(message or "").strip()
    if not text:
        return Intent("unknown")
    conv = conv or {}

    # Gõ/nói đúng MÃ TTHC (vd "1.013225", "mã 1.013225") → chọn thẳng thủ tục, không qua LLM.
    code_match = _CODE_ONLY_RE.match(fold(text))
    if code_match:
        for procedure in public_list():
            if procedure_code(procedure) == code_match.group(1):
                return Intent("pick_procedure", procedure["key"])

    # (2) Màn chào / vừa gợi ý thủ tục: gần như mọi câu là chọn thủ tục → agent chọn thủ tục trước,
    # chỉ câu không nói về thủ tục mới sang bộ phân loại (1 lượt LLM cho trường hợp thường gặp).
    if state == "greet" or conv.get("procedure_candidates"):
        shown = [p for k in conv.get("procedure_candidates") or [] if (p := get_procedure(str(k)))]
        matched = match_candidate_procedure(text, shown)
        if matched:
            return Intent("pick_procedure", matched)
        picked = await _pick_procedure(text, conv)
        if picked is not None:
            return picked
        intent = await _classify(text, state, conv)
        return _free_text_unknown() if intent.kind == "procedure" else intent

    # (3) Các bước khác: bộ phân loại trước; nhắc tới thủ tục mới hỏi agent chọn thủ tục, sửa nơi
    # làm / đối tượng mới hỏi agent nơi làm.
    intent = await _classify(text, state, conv)
    if intent.kind == "procedure":
        return await _pick_procedure(text, conv) or _free_text_unknown()
    if intent.kind == "action" and intent.value == "change_place":
        return await _pick_place(text, conv)
    return intent


async def _pick_place(text: str, conv: dict) -> Intent:
    """Agent nơi làm & đối tượng → Intent("action", "set_place") cho flow áp như chọn trên card."""
    # Import muộn: flow và place_picker đều import intents ở đầu file.
    from app.channels.handfree.chat import flow, place_picker
    from app.channels.handfree.procedure_registry import get_procedure

    proc = get_procedure(conv.get("procedure_key") or "") or {}
    subjects = flow.execution_subject_options(proc)
    res = await place_picker.pick(text, conv, procedure=proc.get("shortLabel") or proc.get("label") or "",
                                  subjects=subjects)
    if res.error:
        return _free_text_unknown()
    return Intent("action", "set_place", {
        "province_slug": res.province_slug, "ward": res.ward,
        "ward_candidates": list(res.ward_candidates), "subject": res.subject,
    })
