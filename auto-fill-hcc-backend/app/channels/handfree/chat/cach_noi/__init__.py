"""Hiểu câu nói / gõ tự do bằng LLM theo lớp, ngân sách tối đa 2 lượt LLM một câu.

    lớp 1  cách nói + độ chắc + việc (cụm từ trích từ câu) + ý chính, kiêm chọn nút / lệnh khi rõ   → 1 lượt
    kiểm   tất định, KHÔNG gán nhãn: chỉ HẠ độ chắc khi nhãn hành động mà không trỏ được vào chữ nào trong câu,
           khi câu lẫn nhiễu, khi câu quá ngắn để chọn nút                                          → 0 lượt
    lớp 2  chọn nút / lệnh theo họ cổng, chỉ khi lớp 1 ra "tra_loi" chưa chắc                        → 2 lượt
    bảng chính sách (policy.py) quyết định câu trả lời theo (bước × cách nói × độ chắc × bộ đếm) — không LLM.

Không có lớp từ điển trước LLM: tiếng ồn qua ASR thành chữ thật ("ừ", "đồng", "à giờ thì") trông y hệt lời đáp
ngắn, một tập đóng không phân biệt được hai thứ đó. Độ chắc quyết định hành động:
    cao  → làm (bấm nút / chạy lệnh; lệnh xoá vẫn hỏi xác nhận như cũ)
    vừa  → không bấm: tra_loi sang lớp 2 kiểm lại; đi tiếp / quay lại → hỏi "có phải … không?" kèm nút;
           xác nhận / từ chối → coi như chưa rõ (hỏi lại)
    thấp → chưa rõ, hỏi lại theo 3 nấc của bảng chính sách

Kết quả vẫn là `Intent` của flow để các handler không đổi; mọi Intent sinh từ câu tự do mang payload
{"_voice": True, "cach_noi", "do_chac", "llm_calls", "y_chinh", "nhieu"} để flow / policy / trace biết nguồn.
Nhãn có việc theo bước (đi tiếp, quay lại, làm lại chưa rõ loại, không biết, ngoài luồng) trả `Intent("cach_noi",
<nhãn>)`; nhãn "không ra việc" (vô nghĩa, không rõ, LLM lỗi) trả `Intent("unknown")` như hợp đồng cũ (reroute của vòng
hỏi ô coi là không có lệnh) — payload "cach_noi" cho policy leo thang 3 nấc.
"""
import logging
import re
import time

from app.channels.handfree.chat import intents, store
from app.channels.handfree.chat.cach_noi import ho_luong, lop1, lop2
from app.channels.handfree.chat.intents import Intent, fold

logger = logging.getLogger(__name__)

KIND = "cach_noi"           # Intent.kind cho nhãn chỉ-chính-sách
KHONG_RO = "khong_ro"       # tra_loi mà hai lớp đều không chọn được nút / lệnh, hoặc độ chắc thấp
LOI = "loi"                 # LLM lỗi / không parse được
_HISTORY_TURNS = 4
# Lệnh của bước mang nghĩa "làm lại / xoá việc đã làm" — lớp 1 ra lam_lai kèm một trong các lệnh này thì chạy như lệnh
# (flow hỏi xác nhận vì có _voice); không kèm → policy hỏi làm lại việc gì.
LENH_LAM_LAI = frozenset({"refill", "add_documents", "docs_done", "pick_files_by_hand", "retry_owner_fill",
                          "business_refill", "reshow_qr"})
# Nút "đi tiếp" của từng bước, theo thứ tự ưu tiên khi nhiều nút cùng hiện (policy dùng chung).
FORWARD_SENDS = ("__action:field_review_confirm", "__action:field_review_preview", "__action:field_review_owner_next",
                 "__action:guided_next", "__action:lt_next", "__action:lt_agency", "__action:bxd_next",
                 "__action:bn_next", "__action:tpm_attach", "__action:goto_login", "__action:docs_done",
                 "__event:docs_complete")
# Nút / lệnh làm lại (xoá việc đã làm) — không bao giờ là "đi tiếp".
LAM_LAI_SENDS = frozenset({"__action:refill", "__action:add_documents", "__action:pick_files_again",
                           "__action:retry_owner_fill", "__action:business_refill", "__action:new_procedure"})
# Nhãn mà hệ thống sẽ LÀM một việc trên trang → phải trỏ được vào chữ trong câu ("viec") mới được coi là chắc.
NHAN_HANH_DONG = frozenset({lop1.TRA_LOI, lop1.DI_TIEP, lop1.LAM_LAI, lop1.HUY, lop1.QUAY_LAI})
# Nhãn chỉ-chính-sách KHÔNG phải lệnh: vòng hỏi ô gặp chúng thì hỏi lại trong vòng, không dừng vòng.
_KHONG_PHAI_LENH = frozenset({lop1.KHONG_BIET, lop1.NGOAI_LUONG, lop1.XA_GIAO})
# Câu ≤ chừng này tiếng mà lớp 1 bảo là chọn nút: chỉ một hai tiếng trùng chữ với nút chưa đủ để bấm, lớp 2 kiểm lại.
MAX_TIENG_NGAN = 2
_TOKEN = re.compile(r"[a-z0-9]+")


def forward_button(buttons: list[dict]) -> dict | None:
    for send in FORWARD_SENDS:
        for item in buttons:
            if item.get("send") == send:
                return item
    for item in buttons:
        if (item.get("chip") or {}).get("cta") and item.get("send") not in LAM_LAI_SENDS:
            return item
    return None


def la_lenh(intent: Intent) -> bool:
    """Intent từ câu tự do có phải một VIỆC thật để vòng hỏi ô dừng lại mà làm không. Không rõ / lời đáp trống / nhãn
    chỉ-chính-sách không phải việc / độ chắc chưa cao → False: vòng hỏi tự hỏi lại, không bấm gì."""
    if intent.kind in ("unknown", "procedure_unclear", "confirm", "deny"):
        return False
    if intent.kind == KIND and intent.value in _KHONG_PHAI_LENH:
        return False
    payload = intent.payload or {}
    return not payload.get("_voice") or payload.get("do_chac") == "cao"


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(fold(text))


def _meta(kq: lop1.KetQua | None, calls: int, t0: float, label: str = "") -> dict:
    return {"_voice": True, "cach_noi": label or (kq.cach_noi if kq else LOI),
            "do_chac": kq.do_chac if kq else "thap", "y_chinh": kq.y_chinh if kq else "",
            "nhieu": bool(kq.nhieu) if kq else False,
            "llm_calls": calls, "ms": int((time.perf_counter() - t0) * 1000)}


def khong_ra_viec(label: str, meta: dict) -> Intent:
    return Intent("unknown", payload={**meta, "cach_noi": label, "free_text": True})


def _with(intent: Intent, meta: dict) -> Intent:
    intent.payload = {**(intent.payload or {}), **meta}
    return intent


def _last_bot_text(conv: dict) -> str:
    for item in reversed(conv.get("history") or []):
        if item.get("role") == "bot" and str(item.get("text") or "").strip():
            return str(item["text"])
    return ""


def kiem(kq: lop1.KetQua, text: str) -> lop1.KetQua:
    """Lớp kiểm tất định: không đổi nhãn, chỉ hạ độ chắc xuống "vua" khi kết quả của lớp 1 không tự đứng được.
    - nhãn hành động mà "viec" rỗng hoặc không có chữ nào trong câu (LLM suy ra việc, không phải nghe thấy);
    - câu lẫn nhiễu ("nhieu");
    - chọn nút từ câu ≤ MAX_TIENG_NGAN tiếng (trùng chữ với nút chưa phải là gọi tên nút)."""
    if kq.cach_noi == lop1.TRA_LOI and kq.lenh == "new_procedure":
        kq.cach_noi = lop1.HUY
    if kq.do_chac != "cao":
        return kq
    toks = _tokens(text)
    if kq.cach_noi in NHAN_HANH_DONG and kq.viec is not None:
        viec = set(_tokens(kq.viec))
        if not viec or not (viec & set(toks)):
            kq.do_chac = "vua"
    if kq.nhieu or (kq.cach_noi == lop1.TRA_LOI and len(toks) <= MAX_TIENG_NGAN):
        kq.do_chac = "vua"
    return kq


async def classify(text: str, state: str, conv: dict) -> Intent:
    """Câu tự do (không phải lệnh máy) → Intent. Thay cho bộ phân loại một prompt cũ."""
    t0 = time.perf_counter()
    buttons = intents.voice_buttons(conv, state)
    entries = intents._state_entries(state, conv)
    lenh_values = {e["value"] for e in entries}

    from app.channels.handfree.procedure_registry import get_procedure
    proc = get_procedure(conv.get("procedure_key") or "") or {}
    ho = ho_luong.ho(proc)
    history = store.recent_dialogue(conv, _HISTORY_TURNS)
    cau_tro_ly = _last_bot_text(conv)

    kq = await lop1.run(text, state, conv, ho=ho, buttons=buttons, entries=entries, history=history,
                        cau_tro_ly=cau_tro_ly)
    calls = 1
    if kq is None:
        return khong_ra_viec(LOI, _meta(None, calls, t0))
    kq = kiem(kq, text)
    meta = _meta(kq, calls, t0)
    cao, thap = kq.do_chac == "cao", kq.do_chac == "thap"

    # Nhãn không làm gì trên trang: trả như nhãn, độ chắc chỉ để ghi vết.
    if kq.cach_noi == lop1.VO_NGHIA:
        return khong_ra_viec(lop1.VO_NGHIA, meta)
    if kq.cach_noi == lop1.HOI_NGUOC:
        return Intent("ask_question", kq.y_chinh or text, meta)
    if kq.cach_noi == lop1.NHAC_LAI:
        return Intent("action", "repeat", meta)
    if kq.cach_noi in _KHONG_PHAI_LENH:
        return Intent(KIND, kq.cach_noi, meta)
    if kq.cach_noi == lop1.THU_TUC:
        return Intent("procedure", payload=meta)   # intents.resolve gọi agent chọn thủ tục (lượt 2)
    # Từ đây là nhãn kéo theo một việc: độ chắc thấp → chưa rõ, hỏi lại.
    if thap:
        return khong_ra_viec(KHONG_RO, meta)
    if kq.cach_noi == lop1.CACH_GUI:
        return Intent("pick_doc_method", kq.cach_gui, meta) if kq.cach_gui else khong_ra_viec(KHONG_RO, meta)
    if kq.cach_noi == lop1.XAC_NHAN:
        return Intent("confirm", payload=meta) if cao else khong_ra_viec(KHONG_RO, meta)
    if kq.cach_noi == lop1.TU_CHOI:
        return Intent("deny", payload=meta) if cao else khong_ra_viec(KHONG_RO, meta)
    if kq.cach_noi == lop1.HUY:
        # Bỏ hồ sơ là việc nặng nhất: chỉ nhận khi chắc (flow còn hỏi xác nhận khi hồ sơ đã bắt đầu); nghe chưa chắc
        # ("ừ ừ thôi nhé" lẫn cuộc gọi điện) → chưa rõ, không hỏi "bỏ hồ sơ?" vu vơ.
        return Intent("action", "new_procedure", meta) if cao else khong_ra_viec(KHONG_RO, meta)
    if kq.cach_noi == lop1.LAM_LAI:
        # Lệnh / nút làm lại luôn qua xác nhận bằng lời ở flow → độ chắc vừa vẫn được nêu ra để công dân Có / Không.
        if kq.lenh in LENH_LAM_LAI and kq.lenh in lenh_values:
            return Intent(_entry(entries, kq.lenh)["kind"], kq.lenh, meta)
        if kq.nut and _button_is_lam_lai(buttons[kq.nut - 1]):
            picked = intents._button_intent(buttons[kq.nut - 1])
            if picked is not None:
                return _with(picked, meta)
        return Intent(KIND, lop1.LAM_LAI, meta)
    if kq.cach_noi == lop1.DI_TIEP:
        if cao:
            item = forward_button(buttons)
            picked = intents._button_intent(item) if item else None
            if picked is not None:
                return _with(picked, meta)   # nút đi tiếp đang hiện chính là việc "đi tiếp" của bước
        return Intent(KIND, lop1.DI_TIEP, meta)   # policy: cao → việc đi tiếp của bước; vừa → hỏi "có phải…?"
    if kq.cach_noi == lop1.QUAY_LAI:
        return Intent(KIND, lop1.QUAY_LAI, meta)

    # tra_loi: lớp 1 đã chọn và chắc → xong một lượt.
    if cao:
        picked = _pick(buttons, entries, kq.nut, kq.lenh)
        if picked is not None:
            return _with(picked, meta)
    if not buttons and not entries:
        return khong_ra_viec(KHONG_RO, meta)
    chon = await lop2.run(kq.y_chinh or text, state, ho=ho, buttons=buttons, entries=entries, history=history,
                          cau_tro_ly=cau_tro_ly, conv=conv)
    meta = _meta(kq, 2, t0)
    n_tieng = len(_tokens(text))
    if n_tieng == 1 or (chon.lenh and n_tieng <= MAX_TIENG_NGAN):
        # Một tiếng lẻ ("đồng", "xem") không đủ để chọn gì; hai tiếng rời chưa đủ để ra một LỆNH của bước (nút hai
        # tiếng như "đồng ý", "xem trước" thì còn so được nhãn).
        chon = lop2.LuaChon()
    picked = None if chon.khong_ro else _pick(buttons, entries, chon.nut, chon.lenh)
    return _with(picked, meta) if picked is not None else khong_ra_viec(KHONG_RO, meta)


def _entry(entries: list[dict], value: str) -> dict:
    return next(e for e in entries if e["value"] == value)


def _pick(buttons: list[dict], entries: list[dict], nut: int, lenh: str) -> Intent | None:
    if nut and 1 <= nut <= len(buttons):
        return intents._button_intent(buttons[nut - 1])
    if lenh:
        entry = next((e for e in entries if e["value"] == lenh), None)
        if entry:
            return Intent(entry["kind"], entry["value"])
    return None


def _button_is_lam_lai(button: dict) -> bool:
    send = str(button.get("send") or "")
    return any(send == f"__action:{v}" or send.startswith(f"__action:{v}:") for v in LENH_LAM_LAI)
