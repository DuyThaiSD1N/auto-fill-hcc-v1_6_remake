"""Lớp 2 — LLM theo HỌ LUỒNG: chọn đúng nút / lệnh khi lớp 1 ra "tra_loi" mà chưa chắc.

Chỉ nhận ý chính đã lọc tạp âm (từ lớp 1) + kiến thức của đúng họ cổng (ho_luong). Không chọn được → "khong_ro" để bảng
chính sách hỏi lại kèm nút, không bao giờ đoán bừa.
"""
import json
import logging
import re
from dataclasses import dataclass

from app.channels.handfree.chat.cach_noi import ho_luong
from app.channels.handfree.chat.cach_noi.lop1 import lenh_block, nut_block

logger = logging.getLogger(__name__)


@dataclass
class LuaChon:
    nut: int = 0
    lenh: str = ""
    khong_ro: bool = True


SYSTEM = """<vai_tro>
Bạn là bộ chọn NÚT / LỆNH cho trợ lý thủ tục hành chính trên {ten_ho}. Một bộ khác đã xác định công dân đang muốn làm
một việc cụ thể của bước (ý chính trong <y_chinh>, đã lọc tạp âm). Việc của bạn: chọn ĐÚNG MỘT nút đang hiện hoặc một
lệnh của bước khớp ý đó; không khớp rõ thì trả không rõ — hệ thống sẽ hỏi lại công dân kèm nút, còn chọn sai là bấm thật
một việc công dân không muốn.
</vai_tro>

<cong>
{mo_ta_ho}
</cong>

<buoc_hien_tai>
Bước: {state} — {mo_ta_buoc}
Câu trợ lý vừa nói: {cau_tro_ly}
</buoc_hien_tai>

<nut_dang_hien>{nut_dang_hien}
</nut_dang_hien>

<lenh_cua_buoc>{lenh_cua_buoc}
</lenh_cua_buoc>

<vi_du>
{vi_du}
</vi_du>

<quy_tac>
- Nút / lệnh LÀM LẠI hay XOÁ (điền lại, điều chỉnh giấy tờ, hoàn tất điều chỉnh, chọn lại tệp, làm thủ tục khác) chỉ chọn
  khi ý chính NÓI RÕ đúng việc đó. Ý "đi tiếp / xong rồi / sang bước" KHÔNG BAO GIỜ là các nút này.
- Ý "đi tiếp" → nút đi tiếp của bước (Xem trước, Xác nhận sang…, Xong sang bước…, Sang bước…); không có nút đi tiếp → không rõ.
- Ý sửa MỘT ô / một thông tin → nút bổ sung / sửa ô (field_review_start), không phải điền lại cả tờ khai.
- Ý về GIẤY TỜ (thiếu, thêm, chụp lại, xoá tệp) → điều chỉnh giấy tờ.
- Hai nút đều có thể đúng mà không phân biệt được → không rõ.
- Ý chính chỉ một hai tiếng rời ("xem", "giấy", "tiếp") không phải tên đầy đủ / cách gọi quen của một nút → không rõ.
</quy_tac>

<dau_ra>
Chỉ trả JSON: {{"nut": <số nút hoặc 0>, "lenh": "<tên lệnh hoặc rỗng>", "khong_ro": true|false, "ly_do": "<≤ 12 từ>"}}
</dau_ra>"""

_TEN_HO = {
    ho_luong.TU_PHAP: "cổng tư pháp (wizard 4 bước)",
    ho_luong.TU_PHAP_MOI: "cổng DVC quốc gia nộp một trang",
    ho_luong.LIEN_THONG: "cổng liên thông 6 bước",
    ho_luong.MAE: "cổng iGate (stepper 4 bước)",
    ho_luong.BAC_NINH: "cổng Bắc Ninh (nhiều tab)",
    ho_luong.HKD: "cổng đăng ký hộ kinh doanh",
    ho_luong.CHUNG: "cổng dịch vụ công",
}


def parse(raw: str, buttons_n: int, lenh_values: set[str]) -> LuaChon:
    m = re.search(r"\{[\s\S]*\}", raw or "")
    if not m:
        return LuaChon()
    try:
        data = json.loads(m.group(0))
    except (ValueError, TypeError):
        return LuaChon()
    if not isinstance(data, dict) or data.get("khong_ro") is True:
        return LuaChon()
    try:
        nut = int(str(data.get("nut") or 0).strip("[] "))
    except (TypeError, ValueError):
        nut = 0
    lenh = str(data.get("lenh") or "").strip()
    if 1 <= nut <= buttons_n:
        return LuaChon(nut=nut, khong_ro=False)
    if lenh in lenh_values:
        return LuaChon(lenh=lenh, khong_ro=False)
    return LuaChon()


async def run(y_chinh: str, state: str, *, ho: str, buttons: list[dict], entries: list[dict], history: list[dict],
              cau_tro_ly: str, conv: dict | None = None) -> LuaChon:
    from app.channels.handfree.chat import intents

    system = SYSTEM.format(
        ten_ho=_TEN_HO.get(ho, _TEN_HO[ho_luong.CHUNG]), mo_ta_ho=ho_luong.MO_TA_HO.get(ho, ho_luong.MO_TA_HO[ho_luong.CHUNG]),
        state=state, mo_ta_buoc=ho_luong.mo_ta_buoc(state, conv), cau_tro_ly=(cau_tro_ly or "(chưa có)")[:300],
        nut_dang_hien=nut_block(buttons), lenh_cua_buoc=lenh_block(entries),
        vi_du="\n".join(f"- {line}" for line in ho_luong.VI_DU_HO.get(ho, ho_luong.VI_DU_HO[ho_luong.CHUNG])),
    )
    try:
        raw = await intents.llm_chat(
            [{"role": "system", "content": system}, *history, {"role": "user", "content": y_chinh[:300]}],
            temperature=0.0, max_tokens=120, purpose="cach_noi.lop2",
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("[cach_noi] lớp 2 lỗi: %s", e)
        return LuaChon()
    return parse(raw, len(buttons), {e["value"] for e in entries})
