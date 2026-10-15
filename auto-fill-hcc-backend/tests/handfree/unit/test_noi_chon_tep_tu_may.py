"""Nói "chọn thêm tệp từ máy": trình duyệt chỉ mở cửa sổ chọn tệp khi bấm thật → mời bấm nút ngay dưới."""
from app.channels.handfree.chat import flow, store
from app.channels.handfree.chat.intents import Intent, _STATE_INTENTS


def _conv(method="scan"):
    conv = store.new_conversation()
    conv.update({"state": "collecting_docs", "procedure_key": "ket-hon", "doc_method": method,
                 "upload_session_id": "s1"})
    return conv


def test_buoc_nhan_giay_to_co_y_dinh_chon_tep_tu_may():
    assert "pick_files_by_hand" in {i["value"] for i in _STATE_INTENTS["collecting_docs"]}


async def test_noi_chon_them_tep_thi_moi_bam_nut_ngay_duoi():
    r = await flow.handle_turn(_conv(), Intent("action", "pick_files_by_hand"))
    assert "bấm tay" in r.display_md and "Chọn thêm tệp từ máy" in r.display_md
    assert r.chips == [{"label": "📁 Chọn thêm tệp từ máy", "send": "__action:pick_files_again", "solid": True}]
    assert "Kê khai" not in r.display_md
