"""Hộp thoại "Chọn trường hợp giải quyết" (cổng Bộ Xây dựng): câu hỏi liệt kê tên GỌN các lựa chọn (nhãn cổng rất dài,
thẻ vẫn hiện nguyên văn), và công dân nói TÊN lựa chọn ("nhà ở riêng lẻ") là chọn được như bấm thẻ."""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import flow, store
from app.channels.handfree.chat.intents import Intent

KEY = "cap-giay-phep-xay-dung-moi-nha-o-rieng-le"
CONG_TRINH = ("(10 ngày làm việc) Cấp giấy phép xây dựng mới đối với công trình cấp III, cấp IV (Công trình không "
              "theo tuyến/Theo tuyến trong đô thị/Tín ngưỡng, tôn giáo/Tượng đài, tranh hoành tráng/Dự án)")
NHA_O = "(7 ngày làm việc) Cấp giấy phép xây dựng mới đối với nhà ở riêng lẻ"


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    monkeypatch.setattr(flow.conv_store, "save", AsyncMock())


def _conv():
    conv = store.new_conversation()
    conv.update({"procedure_key": KEY, "state": "guide_login", "client_capabilities": {"supportsMaeDialogChoice": True},
                 "auth_user": {"id": "u1"},
                 "mae_dialog_options": {"agency": {"options": ["UBND Phường A"], "current": "UBND Phường A"},
                                        "process": {"options": [CONG_TRINH, NHA_O], "current": CONG_TRINH}}})
    return conv


def test_ten_gon_bo_phan_trong_ngoac_va_phan_mo_dau_giong_nhau():
    assert flow._mae_dialog_short_labels([CONG_TRINH, NHA_O]) == ["công trình cấp III, cấp IV", "nhà ở riêng lẻ"]
    assert flow._mae_dialog_short_labels(["UBND Phường A"]) == ["UBND Phường A"]


def test_ten_gon_bo_ca_phan_duoi_giong_nhau():
    tail = " - Cấp điều chỉnh giấy phép xây dựng đối với công trình cấp III, cấp IV"
    labels = ["Đối với nhà ở riêng lẻ" + tail, "Đối với công trình" + tail + " (Dự án)"]
    assert flow._mae_dialog_short_labels(labels) == ["nhà ở riêng lẻ", "công trình"]


def test_cau_hoi_chi_liet_ke_ten_gon_the_van_nguyen_van():
    conv = _conv()
    reply = flow._to_choose_mae_dialog(conv)
    assert "**công trình cấp III, cấp IV** · **nhà ở riêng lẻ**" in reply.display_md
    assert "Tượng đài" not in reply.display_md and "Tượng đài" not in reply.tts_text
    assert "công trình cấp III, cấp IV, hoặc nhà ở riêng lẻ" in reply.tts_text
    (card,) = reply.cards
    assert [o["label"] for o in card["groups"][0]["options"]] == [CONG_TRINH, NHA_O]


async def test_noi_ten_lua_chon_la_chon_dung_lua_chon_do():
    conv = _conv()
    reply = flow._to_choose_mae_dialog(conv)
    flow.update_voice_options(conv, reply)
    items = conv["voice_options"]["items"]
    nha_o = next(i for i in items if i["label"] == "nhà ở riêng lẻ")
    assert nha_o["send"] == '__action:set_mae_dialog:{"process": 1}' and nha_o["desc"] == NHA_O
    # Lời nói chọn nút → cùng lệnh như bấm thẻ (payload mang chỉ số lựa chọn).
    picked = await flow.handle_turn(conv, Intent("action", "set_mae_dialog",
                                                 {"process": 1, "_voice_button": nha_o["send"]}))
    action = next(a for a in picked.actions if a["type"] == "fill_mae_agency")
    assert action["processExact"] == NHA_O
    assert "trường hợp **nhà ở riêng lẻ**" in picked.display_md
    assert conv["mae_dialog_choice_labels"]["process"] == NHA_O


def test_hoi_hai_o_cung_luc_thi_chi_chon_tren_the():
    conv = _conv()
    conv["mae_dialog_options"]["agency"] = {"options": ["UBND Phường A", "UBND Phường B"], "current": ""}
    card = flow._mae_dialog_card(conv)
    assert flow._card_voice_items(card) == []


async def test_dang_bam_dong_y_ma_trang_chua_doc_duoc_lua_chon_thi_khong_hoi_lai_truong_hop():
    conv = _conv()
    conv["state"] = "choose_mae_dialog"
    await flow.handle_turn(conv, Intent("action", "set_mae_dialog", {"process": 1}))
    # FE đang mở ô chọn để điền → lần đọc trang này không lấy được lựa chọn của hộp thoại.
    reply = await flow.handle_turn(conv, Intent("event", "page_status", {"maeAgencyBlock": True}))
    assert conv["state"] != "choose_variant"
    assert not reply.chips and not reply.actions and not reply.display_md
