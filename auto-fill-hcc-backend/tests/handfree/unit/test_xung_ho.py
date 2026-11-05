"""Trợ lý tự xưng "tôi": đổi ở đầu ra (chat/xung_ho.py), câu thoại gốc trong script_vi và prompt LLM không đổi."""
import pathlib
import re

import pytest

from app.channels.handfree.chat import flow, router, script_vi as vi, xung_ho
from app.channels.handfree.procedure_registry import PROCEDURES


@pytest.mark.parametrize("before, after", [
    ("Dạ, em đang điền, công dân chờ em chút ạ.", "Dạ, tôi đang điền, công dân chờ tôi chút ạ."),
    ("✓ Em đã đính 3 tệp.", "✓ Tôi đã đính 3 tệp."),
    ("**Xin chào công dân!** Em là Trợ lý nhân dân.", "**Xin chào công dân!** Tôi là Trợ lý nhân dân."),
    ("Công dân xem giúp em. Em sẽ hỏi tiếp.", "Công dân xem giúp tôi. Tôi sẽ hỏi tiếp."),
    # Không phải đại từ của trợ lý → giữ nguyên.
    ("Liên thông … cho trẻ em dưới 6 tuổi", None),
    ("Họ tên: Nguyễn Thị Em", None),
    ("Quan hệ: Em ruột", None),
    ("em gái của người mất", None),
    ("anh chị em", None),
    ("anh/chị/em", None),
    ("xem kèm, đem thêm, đệm", None),
])
def test_chi_doi_dai_tu_cua_tro_ly(before, after):
    assert xung_ho.text(before) == (after if after is not None else before)


def test_moi_cau_trong_script_vi_khong_con_em_va_ten_thu_tuc_khong_doi():
    def strings(node):
        if isinstance(node, str):
            yield node
        elif isinstance(node, dict):
            for v in node.values():
                yield from strings(v)
        elif isinstance(node, (list, tuple)):
            for v in node:
                yield from strings(v)

    texts = [s for name, value in vars(vi).items() if name.isupper() for s in strings(value)]
    left = [s for s in texts if re.search(r"(?<!\w)[Ee]m(?!\w)", xung_ho.text(s))]
    assert not left, left[:3]
    for proc in PROCEDURES:
        for key in ("label", "shortLabel", "subtitle"):
            value = proc.get(key)
            if isinstance(value, str):
                assert xung_ho.text(value) == value, (proc["key"], key)


def test_doi_tren_reply_chi_o_khoa_chu_hien_thi():
    r = flow.Reply("Dạ, em đã điền.", "Dạ, em đã điền.")
    r.chips = [{"label": "Em bấm giúp", "send": "__action:em"}]
    r.cards = [{"kind": "attach_files", "failedHint": "Công dân bấm giúp em", "failed": [{"name": "em.jpg"}]}]
    r.actions = [{"type": "trail_message", "md": "Em hỏi tiếp"}, {"type": "fill_fields", "fields": [{"value": "em"}]}]
    xung_ho.reply(r)
    assert r.display_md == "Dạ, tôi đã điền." and r.tts_text == "Dạ, tôi đã điền."
    assert r.chips == [{"label": "Tôi bấm giúp", "send": "__action:em"}], "lệnh gửi BE không đổi"
    assert r.cards[0]["failedHint"] == "Công dân bấm giúp tôi" and r.cards[0]["failed"][0]["name"] == "em.jpg"
    assert r.actions[0]["md"] == "Tôi hỏi tiếp" and r.actions[1]["fields"][0]["value"] == "em", "giá trị ô không đổi"


def test_loi_doc_tieng_mong_khong_doi():
    r = flow.Reply("Em đã điền.", "Kuv tau sau em", tts_lang="hmong")
    xung_ho.reply(r)
    assert r.tts_text == "Kuv tau sau em"


def test_router_doi_truoc_khi_gui_va_luu_lich_su():
    src = pathlib.Path(router.__file__).read_text(encoding="utf-8")
    body = src[src.index("async def assistant_chat("):]
    assert body.index("xung_ho.reply(reply)") < body.index("payload = _serialize(conv, reply)") \
        < body.index('store.push_history(conv, "bot", reply.display_md, "bot")')
