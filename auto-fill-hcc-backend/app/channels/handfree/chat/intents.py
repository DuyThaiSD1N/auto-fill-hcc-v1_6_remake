"""Hiểu ý định người dân trong ngữ cảnh state hiện tại (docs/03a §3).

Mọi ý định nói/gõ tự do đều do **LLM** quyết (cach_noi/: lớp 1 cách nói + độ chắc → lớp kiểm tất định chỉ hạ độ chắc →
lớp 2 theo họ cổng), KHÔNG dùng lưới từ khóa, không có từ điển trước LLM. Chỉ 2 thứ giữ tất định vì là giao thức/đã chắc chắn: lệnh máy
`__action:*`/`__event:*` (chip/watcher) và số điện thoại.

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

from app.channels.handfree.chat import procedure_picker
from app.channels.handfree.procedure_registry import is_visible_in_province, procedure_code, public_list
from app.services.llm.client import chat as llm_chat  # cach_noi/ gọi qua intents.llm_chat: một chỗ patch cho test

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
    # Hộp thoại "Chọn trường hợp giải quyết" (cổng Bộ Xây dựng): nói SỐ THỨ TỰ → mae_pick_N; nói TÊN lựa chọn → nút
    # của thẻ (flow._card_voice_items). Flow chỉ áp khi đang hỏi đúng một ô (nơi xử lý HOẶC trường hợp).
    "choose_mae_dialog": [
        {"kind": "action", "value": f"mae_pick_{n}",
         "desc": f"nói SỐ THỨ TỰ của lựa chọn (số {n}, cái thứ {word}) trong danh sách đang hỏi; nói TÊN lựa chọn "
                 f"thì chọn NÚT có tên đó, không dùng hành động này"}
        for n, word in ((1, "nhất"), (2, "hai"), (3, "ba"), (4, "tư"), (5, "năm"), (6, "sáu"))
    ],
    # Màn chào: câu chỉ xin bắt đầu (nói ở màn bắt đầu rồi chuyển vào chat) → mời chọn / nói tên thủ tục,
    # không báo "chưa nhận ra thủ tục".
    "greet": [
        {"kind": "action", "value": "start_only",
         "desc": "chỉ muốn bắt đầu / bắt đầu làm thủ tục / làm hồ sơ mà CHƯA nêu tên hay mô tả thủ tục nào"},
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
        # Thành lập hộ kinh doanh bằng hỏi đáp (chat/hkd_tro_ly): lời nói thay cho nút "không có tờ khai".
        {"kind": "action", "value": "consent_no_docs", "only": "hkd",
         "desc": "KHÔNG CÓ tờ khai / giấy tờ và muốn làm cùng trợ lý — trợ lý hỏi, công dân khai bằng lời (đây là "
                 "ĐỒNG Ý cho xử lý thông tin, KHÔNG phải từ chối)"},
    ],
    "ask_doc_method": [
        {"kind": "action", "value": "hkd_no_docs", "only": "hkd",
         "desc": "KHÔNG CÓ tờ khai / giấy tờ, muốn trợ lý hỏi để khai bằng lời"},
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
        # Hộp chọn tệp chỉ mở được bằng cú bấm thật → lời nói chỉ được mời bấm nút (flow).
        {"kind": "action", "value": "pick_files_by_hand",
         "desc": "muốn chọn / thêm / tải tệp từ máy tính (mở cửa sổ chọn tệp) — KHÔNG phải yêu cầu đính kèm"},
    ],
    "owner_waiting_next": [
        {"kind": "action", "value": "retry_owner_fill",
         "desc": "yêu cầu điền lại thông tin chủ hồ sơ, ví dụ 'điền đi', 'điền lại', 'thử lại'"},
        {"kind": "action", "value": "add_documents",
         "desc": "muốn xem, thêm, xóa hoặc chụp lại giấy tờ rồi điền lại thông tin chủ hồ sơ (điều chỉnh giấy tờ)"},
    ],
    "filling": [
        {"kind": "action", "value": "request_attach",
         "desc": "muốn đính kèm/chuyển sang đính kèm ngay khi vẫn đang ở trang kê khai"},
    ],
    "reviewing": [
        {"kind": "action", "value": "step_back", "only": "step_back",
         "desc": "muốn QUAY LẠI BƯỚC / TRANG TRƯỚC trên cổng (bấm nút Quay lại của cổng), vd đang ở thành phần hồ sơ muốn "
                 "về kê khai, tờ khai để sửa — không phải quay lại ô trước"},
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
        {"kind": "action", "value": "step_back", "only": "step_back",
         "desc": "muốn QUAY LẠI BƯỚC / TRANG TRƯỚC trên cổng (bấm nút Quay lại của cổng), vd đang ở thành phần hồ sơ muốn "
                 "về kê khai, tờ khai để sửa — không phải quay lại ô trước"},
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
        {"kind": "action", "value": "step_back", "only": "step_back",
         "desc": "muốn QUAY LẠI BƯỚC / TRANG TRƯỚC trên cổng (bấm nút Quay lại của cổng), vd đang ở thành phần hồ sơ muốn "
                 "về kê khai, tờ khai để sửa — không phải quay lại ô trước"},
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
     "desc": "muốn bỏ thủ tục đang làm, chọn thủ tục khác mà CHƯA nêu tên thủ tục mới (nêu tên → kind procedure). "
             "KHÔNG phải câu xin sang bước tiếp theo / bước nhận kết quả của hồ sơ đang làm"},
    {"kind": "action", "value": "repeat",
     "desc": "CHƯA NGHE RÕ / chưa hiểu câu trợ lý vừa nói và muốn trợ lý NÓI LẠI (\"sao cơ\", \"gì cơ\", \"hả\", "
             "\"nói lại đi\", \"em nói gì\", \"nhắc lại\") — không hỏi thêm thông tin gì mới"},
]

# ── Chuyển bước wizard bằng lời ──
# Câu xin chuyển bước trên cổng ("sang bước nhận kết quả", "bước tiếp theo đi"). Phải tất định: LLM từng
# xếp "sang bước nhận kết quả" vào new_procedure → reset cả hồ sơ đang làm. Bắt buộc có chữ "bước"/"tiếp
# theo" — "nhận kết quả qua bưu điện" ở bước 4 là chọn cách nhận, không phải chuyển bước.
_NEXT_STEP_RE = re.compile(
    r"(?:^|\s)(?:buoc tiep|tiep theo|buoc sau|buoc nhan ket qua"
    r"|(?:sang|qua|chuyen|toi|den|tiep)\s+(?:sang\s+|qua\s+)?buoc)(?:\s|$)"
)
# "Gửi hồ sơ / nộp hồ sơ / gửi đi" ở bước Thông tin nhận kết quả (flow chỉ nhắc công dân tự bấm).
_SUBMIT_RE = re.compile(r"(?:^|\s)(?:gui|nop)\s+(?:ho so|di|luon|nhe|giup)(?:\s|$)")
# Không tính "đừng": bỏ dấu thành "dung", trùng "đúng".
_STEP_NEGATION_RE = re.compile(r"(?:^|\s)(?:khong|chua|khoan|thoi)(?:\s|$)")
_STEP_MAX_WORDS = 12


def _step_words(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", fold(str(text or ""))))


def asks_next_step(text: str) -> bool:
    said = _step_words(text)
    if not said or len(said.split()) > _STEP_MAX_WORDS:
        return False
    return bool(_NEXT_STEP_RE.search(said)) and not _STEP_NEGATION_RE.search(said)


def asks_submit(text: str) -> bool:
    said = _step_words(text)
    if not said or len(said.split()) > _STEP_MAX_WORDS:
        return False
    return bool(_SUBMIT_RE.search(said)) and not _STEP_NEGATION_RE.search(said)


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
                parsed = json.loads(raw)
            except (ValueError, TypeError):
                parsed = raw
            payload = parsed if isinstance(parsed, dict) else {"value": parsed}
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
    # Chỉ câu nói RÕ đăng xuất / thoát. Lời đáp chung ("ok", "xong rồi", "đúng rồi", "có") không phải chọn đăng xuất —
    # bảng chính sách hỏi lại hai lựa chọn.
    if any(k in t for k in ("dang xuat", "thoat tai khoan", "log out", "logout", "thoat ra", "ket thuc phien")):
        return "logout_citizen"
    return None


def _state_entries(state: str, conv: dict | None) -> list[dict]:
    """Ý định của state; mục "only": "hkd" (lối vào không giấy tờ) chỉ mở khi luồng hỏi đáp hộ kinh doanh bật lối đó,
    "only": "step_back" (quay lại bước trước) chỉ khi extension bấm được nút Quay lại của wizard tư pháp."""
    entries = _STATE_INTENTS.get(state, [])
    on = {"": True, "hkd": False, "step_back": False}
    if conv and any(e.get("only") for e in entries):
        from app.channels.handfree.chat import hkd_tro_ly, step_back
        from app.channels.handfree.procedure_registry import get_procedure
        proc = get_procedure(conv.get("procedure_key") or "")
        on["hkd"] = any(e.get("only") == "hkd" for e in entries) and hkd_tro_ly.no_docs_on(conv, proc)
        on["step_back"] = step_back.enabled(conv, proc)
    return _GLOBAL_INTENTS + [e for e in entries if on.get(e.get("only") or "", False)]


def _free_text_unknown() -> Intent:
    # Đánh dấu "câu gõ/nói không nhận ra" để màn chào nói "chưa nhận ra" thay vì chào lại.
    return Intent("unknown", payload={"free_text": True})


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
    """Câu tự do → Intent qua các lớp (cach_noi/): lớp 1 cách nói + độ chắc → kiểm → lớp 2 theo họ cổng; ≤ 2 lượt LLM."""
    from app.channels.handfree.chat import cach_noi

    return await cach_noi.classify(text, state, conv)


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
    # Một mã có thể có nhiều bản tỉnh (1.013978: Khánh Hòa + Tuyên Quang, mỗi bản khóa tỉnh riêng) → ưu tiên bản
    # tài khoản được làm; lấy khớp đầu tiên của cả danh sách thì tài khoản Tuyên Quang dính bản Khánh Hòa và bị
    # báo "chỉ làm được ở Khánh Hòa". Bản riêng của đúng tỉnh tài khoản đứng trước bản dùng chung cả nước. Không bản
    # nào mở cho tỉnh này mới rơi về khớp đầu (flow báo khóa tỉnh).
    code_match = _CODE_ONLY_RE.match(fold(text))
    if code_match:
        account_slug = str((conv.get("auth_user") or {}).get("province_slug") or "")
        matches = [p for p in public_list() if procedure_code(p) == code_match.group(1)]
        allowed = [p for p in matches if is_visible_in_province(p, account_slug)]
        allowed.sort(key=lambda p: account_slug not in (p.get("provinceOnly") or []))
        if allowed or matches:
            return Intent("pick_procedure", (allowed or matches)[0]["key"])

    # (2) Màn chào / vừa gợi ý thủ tục: gần như mọi câu là chọn thủ tục → agent chọn thủ tục trước,
    # chỉ câu không nói về thủ tục mới sang bộ phân loại (1 lượt LLM cho trường hợp thường gặp).
    if state == "greet" or conv.get("procedure_candidates"):
        picked = await _pick_procedure(text, conv)
        if picked is not None:
            return picked
        intent = await _classify(text, state, conv)
        return _free_text_unknown() if intent.kind == "procedure" else intent

    # (3) Các bước khác: bộ phân loại trước; nhắc tới thủ tục mới hỏi agent chọn thủ tục, sửa nơi
    # làm / đối tượng mới hỏi agent nơi làm.
    intent = await _classify(text, state, conv)
    if intent.kind == "procedure":
        return _with_meta(await _pick_procedure(text, conv) or _free_text_unknown(), intent)
    if intent.kind == "action" and intent.value == "change_place":
        return _with_meta(await _pick_place(text, conv), intent)
    if intent.kind == "action" and intent.value == "new_procedure" and (intent.payload or {}).get("cach_noi") == "huy":
        # "không, tôi muốn làm khai tử": câu bỏ thủ tục có nêu tên thủ tục mới → chọn thẳng thủ tục đó thay vì chỉ huỷ.
        picked = await _pick_procedure(text, conv)
        if picked is not None and picked.kind == "pick_procedure":
            return _with_meta(picked, intent)
    return intent


def _with_meta(picked: Intent, source: Intent) -> Intent:
    """Agent chọn thủ tục / nơi làm là lượt LLM thứ hai: giữ nhãn cách nói của lớp 1 và cộng lượt để đo."""
    meta = {k: v for k, v in (source.payload or {}).items() if k in ("_voice", "cach_noi", "do_chac", "y_chinh", "ms")}
    if meta:
        meta["llm_calls"] = int((source.payload or {}).get("llm_calls") or 0) + 1
    picked.payload = {**meta, **(picked.payload or {})}
    return picked


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
