"""Hai lớp agent hiểu câu trả lời của công dân trong trợ lý thành lập hộ kinh doanh: ĐIỀU PHỐI (hiểu muốn gì, mục nào
có thông tin — kể cả mục ở khối đã lưu / khối chưa tới) → CHUYÊN MÔN (một lượt đọc giá trị mọi mục được giao) → code
kiểm (hoi_dap.check). Tách hẳn khỏi hai agent của vòng bổ sung tờ khai hộ tịch (field_review/v2): mục, dạng giá trị và
luật của hộ kinh doanh khác hẳn, gộp chung làm prompt nặng.

Việc kinh doanh (bán gì, mở quán gì) không qua chuyên môn mà giao agent ngành nghề (hkd_tro_ly/nganh_nghe.py).
Agent điều phối lỗi → understand ném lỗi, bên gọi lùi về cách hiểu một lượt cũ (hoi_dap.interpret).
"""
import logging
from dataclasses import dataclass, field as dc_field

from app.channels.handfree.chat.hkd_tro_ly.agents import coordinator, specialist

logger = logging.getLogger(__name__)

# Bật hai lớp cho trợ lý hộ kinh doanh (tắt = quay về một lượt LLM hoi_dap.interpret).
ENABLED = True


@dataclass
class Understood:
    """Cùng các trường với hoi_dap.Parsed (action, values, bad_digits, nganh_text) để luồng ghi / điền / lưu khối giữ
    nguyên, thêm: câu hỏi lại, mục đích muốn sửa, mục bỏ qua, mục đang làm rõ."""
    action: str                                   # tra_loi | dong_y | bo_qua | tam_dung | nhac_lai | khong_ro |
    values: dict = dc_field(default_factory=dict)  # hoi_ro | di_toi | lenh_khac
    bad_digits: dict = dc_field(default_factory=dict)
    nganh_text: str = ""
    question: str = ""
    goal: str = ""
    asking_key: str = ""     # mục chuyên môn còn thiếu / mơ hồ → mạch làm rõ


async def understand(catalog: list[dict], current: dict, thread: list[str], conv: dict, text: str) -> Understood:
    decision = await coordinator.decide(catalog, current, thread, conv, text)
    kind = decision.kind
    if kind == "dong_y" and not current.get("confirm"):
        slot = next((c for c in catalog if c.get("key") == current.get("key")), None)
        if slot and slot.get("kind") == "yesno":
            # Đồng ý chỉ có nghĩa "lưu khối" ở bảng tóm tắt; đang hỏi mục có/không thì "đúng rồi" là câu trả lời của
            # mục đó — giao agent chuyên môn đọc giá trị thay vì rơi về "chưa nghe rõ".
            decision.targets, kind = [slot], "tra_loi"
    if kind in {"dong_y", "bo_qua", "tam_dung", "nhac_lai", "lenh_khac"}:
        return Understood(kind)
    if kind == "hoi_ro":
        return Understood("hoi_ro", question=decision.question)
    if kind == "di_toi":
        return Understood("di_toi", question=decision.question, goal=decision.goal.get("key") or "")
    if kind == "nganh":
        return Understood("tra_loi", nganh_text=decision.nganh_text)
    outcomes = await specialist.solve(decision.targets, current, text, thread, conv)
    out = Understood("tra_loi", nganh_text=decision.nganh_text)
    for o in outcomes:
        key = o.slot["key"]
        if o.kind == "ok":
            out.values[key] = o.value
        elif o.bad_digits:
            out.bad_digits[key] = o.bad_digits
        elif o.kind == "ask" and not out.asking_key:
            out.asking_key, out.question = key, o.question
        elif o.kind == "skip" and key == current.get("key"):
            out.action = "bo_qua"  # công dân nói không có mục đang hỏi; mục khác nghe được trong câu vẫn ghi
    if not out.values and not out.bad_digits and not out.asking_key and not out.nganh_text and out.action != "bo_qua":
        out.action = "khong_ro"  # chuyên môn không đọc được gì cho mục nào
    return out
