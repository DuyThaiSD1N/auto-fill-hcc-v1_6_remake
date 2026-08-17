"""Hiểu ý định người dân trong ngữ cảnh state hiện tại (docs/03a §3).

Chọn thủ tục + mọi ý định nói/gõ tự do đều do **LLM** quyết (đưa cả danh sách thủ tục
kèm nhãn/mô tả → LLM trả đúng key), KHÔNG dùng khớp từ khóa. Chỉ 2 thứ giữ tất định vì
là giao thức/đã chắc chắn: lệnh máy `__action:*`/`__event:*` (chip/watcher) và số điện thoại.
LLM lỗi/không chắc → Intent("unknown"); flow hiện lại card cho người dân tự chọn.

Flow KHÔNG gọi LLM trực tiếp — mọi suy đoán gói gọn ở đây (router gọi `resolve`).
"""
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field

from app.procedures.registry import public_list
from app.services.llm.client import chat as llm_chat

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


# Gợi ý cách người dân hay gọi từng thủ tục — CHỈ dùng làm ngữ cảnh cho LLM (không phải bộ
# khớp keyword). Giúp LLM chọn đúng key cho các cách nói dân dã ("lấy vợ nước ngoài"...).
_PROCEDURE_HINTS: dict[str, list[str]] = {
    "khai-sinh-dang-ky": ["khai sinh cho con", "làm giấy khai sinh"],
    "ket-hon": ["đăng ký kết hôn trong nước", "cưới"],
    "khai-tu": ["làm giấy khai tử", "giấy chứng tử", "giấy báo tử"],
    "ket-hon-nuoc-ngoai": ["kết hôn với người nước ngoài", "lấy chồng/vợ nước ngoài",
                           "chồng/vợ là người nước ngoài"],
    "dang-ky-lai-ket-hon": ["đăng ký lại kết hôn", "làm lại giấy kết hôn", "mất giấy kết hôn"],
    "dang-ky-nhan-cha-me-con": ["nhận cha/mẹ/con", "cha nhận con", "con nhận cha/mẹ"],
    "dang-ky-giam-ho": ["đăng ký giám hộ"],
    "trich-luc-ks": ["cấp bản sao giấy khai sinh", "bản sao trích lục hộ tịch"],
    "xac-nhan-tinh-trang-hon-nhan": ["xác nhận độc thân", "xác nhận tình trạng hôn nhân"],
}

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
        {"kind": "event", "value": "docs_complete",
         "desc": "báo đã chụp/gửi đủ giấy tờ, hoặc giục xử lý/điền luôn"},
    ],
    "collecting_docs": [
        {"kind": "event", "value": "docs_complete",
         "desc": "báo đã chụp/gửi đủ giấy tờ, hoặc giục xử lý/điền form luôn"},
        {"kind": "action", "value": "reshow_qr",
         "desc": "muốn chụp lại / hiện lại mã QR"},
    ],
    "reviewing": [
        {"kind": "action", "value": "confirm_review",
         "desc": "xác nhận form đã đúng, cho đính kèm giấy tờ"},
        {"kind": "action", "value": "refill",
         "desc": "chê form điền sai, muốn điền lại"},
    ],
    "done": [
        # save_profile tạm ẨN cùng option "Lấy dữ liệu đã lưu" (nút Lưu hồ sơ đã gỡ khỏi done).
        {"kind": "event", "value": "submitted",
         "desc": "báo đã bấm nộp hồ sơ xong trên trang"},
    ],
}

# Lệnh dùng được ở MỌI state.
_GLOBAL_INTENTS: list[dict] = [
    {"kind": "action", "value": "new_procedure",
     "desc": "muốn bỏ thủ tục đang làm, chọn thủ tục khác"},
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


def _procedure_catalog() -> str:
    """Danh sách thủ tục (key | nhãn | mô tả | cách gọi) đưa vào prompt LLM chọn thủ tục."""
    lines = []
    for p in public_list():
        label = p.get("label") or p.get("shortLabel") or p["key"]
        parts = [label]
        if p.get("subtitle"):
            parts.append(str(p["subtitle"]))
        hints = _PROCEDURE_HINTS.get(p["key"], [])
        if hints:
            parts.append("còn gọi: " + "; ".join(hints))
        lines.append(f'  + "{p["key"]}" = ' + " — ".join(parts))
    return "\n".join(lines)


def _state_action_block(state: str) -> str:
    entries = _GLOBAL_INTENTS + _STATE_INTENTS.get(state, [])
    if not entries:
        return ' (bước này không có state_action nào → đừng dùng kind "state_action")'
    return "\n" + "\n".join(f'  + "{e["value"]}": người dân {e["desc"]}' for e in entries)


_LLM_SYSTEM = """Bạn là bộ phân loại ý định cho trợ lý thủ tục hành chính công Việt Nam.
Người dân đang ở bước "{state}". Đọc câu của họ và trả DUY NHẤT một JSON:
{{"kind": "<pick_procedure|pick_doc_method|state_action|confirm|deny|ask_question|unknown>", "value": "<xem dưới>", "procedure": "<key, chỉ cho ask_question>"}}

- pick_procedure: người dân muốn LÀM một thủ tục → value = ĐÚNG MỘT key trong DANH SÁCH THỦ TỤC.
  PHÂN BIỆT KỸ các thủ tục gần giống nhau theo mô tả: đăng ký kết hôn (trong nước) vs kết hôn
  CÓ YẾU TỐ NƯỚC NGOÀI vs ĐĂNG KÝ LẠI kết hôn; khai sinh vs cấp bản sao/trích lục khai sinh...
  Chỉ chọn khi câu thể hiện MUỐN LÀM thủ tục. Không chắc thuộc key nào → kind="unknown".
- pick_doc_method: khi người dân CHỌN hoặc ĐỔI cách cung cấp giấy tờ — kể cả đang ở bước chụp/quét QR
  mà muốn ĐỔI sang cách kia (vd đang QR nói "scan đi", đang scan nói "chụp bằng điện thoại") →
  value là MỘT trong:{doc_methods}
  CHÚ Ý QUAN TRỌNG: "chụp"/"chụp ảnh"/"chụp bằng điện thoại"/"dùng điện thoại" LUÔN là "qr"
  (KHÔNG phải "scan" — dù chữ "chụp" nghĩa gần "quét"). "scan"/"tải tệp"/"chọn file" mới là "scan".
- state_action: hành động của bước hiện tại → value là MỘT trong:{state_actions}
- confirm / deny: đồng ý / từ chối câu bot vừa hỏi → value = "".
- ask_question: hỏi thông tin (lệ phí, thời gian, giấy tờ cần...) → value = câu hỏi rút gọn;
  nếu hỏi về một thủ tục cụ thể thì thêm "procedure" = key của thủ tục đó.
- unknown: không xếp được → value = "".

DANH SÁCH THỦ TỤC (dùng cho pick_procedure và trường procedure):
{procedures}

LƯU Ý: câu có "chưa"/"không"/"chưa được" là PHỦ ĐỊNH — KHÔNG coi là hành động đã-xong
(vd "chưa đăng nhập được" KHÔNG phải sso_success). Chỉ trả JSON, không giải thích."""


async def resolve(message: str, state: str) -> Intent:
    # (1) Lệnh máy + số điện thoại: tất định tuyệt đối, không đụng LLM.
    machine = _resolve_machine(message)
    if machine is not None:
        return machine

    text = str(message or "").strip()
    if not text:
        return Intent("unknown")

    proc_keys = {p["key"] for p in public_list()}
    # (2) Mọi câu tự do → LLM phân loại (1 lượt). Lỗi/không chắc → unknown (flow hiện lại card).
    try:
        raw = await llm_chat(
            [
                {"role": "system", "content": _LLM_SYSTEM.format(
                    state=state, state_actions=_state_action_block(state),
                    doc_methods=_doc_method_block(), procedures=_procedure_catalog())},
                {"role": "user", "content": text[:500]},
            ],
            temperature=0.0,
            max_tokens=120,
        )
        m = re.search(r"\{[\s\S]*\}", raw or "")
        data = json.loads(m.group(0)) if m else {}
        kind = str(data.get("kind", "unknown"))
        value = str(data.get("value", ""))

        if kind == "pick_procedure":
            # Key phải có thật — LLM không được bịa; không hợp lệ → unknown → card.
            return Intent("pick_procedure", value) if value in proc_keys else Intent("unknown")
        if kind == "pick_doc_method":
            return Intent("pick_doc_method", value) if value in _DOC_METHODS else Intent("unknown")
        if kind == "state_action":
            # Chỉ chấp nhận value có trong bảng của state — không cho bịa lệnh.
            entry = next((e for e in _GLOBAL_INTENTS + _STATE_INTENTS.get(state, [])
                          if e["value"] == value), None)
            return Intent(entry["kind"], entry["value"]) if entry else Intent("unknown")
        if kind == "confirm":
            return Intent("confirm")
        if kind == "deny":
            return Intent("deny")
        if kind == "ask_question":
            proc = str(data.get("procedure", ""))
            payload = {"procedure_key": proc} if proc in proc_keys else {}
            return Intent("ask_question", value or text, payload)
    except Exception as e:  # noqa: BLE001 — LLM là best-effort, flow phải sống tiếp
        logger.warning("[intents] LLM phân loại lỗi: %s", e)

    return Intent("unknown")
