"""Màn chào thứ tự mới: chọn THỦ TỤC trước, chọn nơi ở lượt xác nhận.

Nơi làm thủ tục gần như luôn đúng sẵn theo tài khoản quầy, nên bắt công dân soát nó TRƯỚC khi
biết làm thủ tục gì là bắt đọc một thứ chưa liên quan.

Gác bằng `supportsProcedureFirst`: bản extension trên chợ giữ NGUYÊN màn chào cũ (card chọn
nơi ở trên, danh sách thủ tục ở dưới).
"""
import pytest

from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import flow
from app.channels.handfree.chat.flow import Intent

NEW_CLIENT = {"supportsProcedureFirst": True}
OLD_CLIENT = {"supportsRating": True}


def _conv(caps):
    return {
        "_id": "t-greet", "state": "greet", "history": [], "milestones": [],
        "client_capabilities": dict(caps),
        "location": {"province": "Thành phố Đà Nẵng", "ward": "Phường Hải Châu"},
    }


def _kinds(reply):
    return [card.get("kind") for card in reply.cards]


def test_man_chao_moi_chi_co_danh_sach_thu_tuc():
    r = flow._handle_greet(_conv(NEW_CLIENT), Intent("text", ""))
    assert _kinds(r) == ["service_list"]
    assert "nơi làm thủ tục" not in r.display_md, (
        "màn chào không còn card chọn nơi thì câu chào cũng không được chỉ xuống nó"
    )


def test_man_chao_cu_giu_nguyen_thu_tu_noi_truoc():
    r = flow._handle_greet(_conv(OLD_CLIENT), Intent("text", ""))
    assert _kinds(r) == ["location_picker", "service_list"]
    assert r.display_md == vi.GREET["md"], "bản trên chợ phải nhận đúng nguyên văn câu cũ"


def test_chon_thu_tuc_xong_moi_hien_noi_de_chinh():
    conv = _conv(NEW_CLIENT)
    r = flow._to_confirm_procedure(conv, "chung-thuc-ban-sao")
    assert _kinds(r) == ["location_picker"]
    assert "Chứng thực bản sao" in r.display_md
    # Nút Đúng rồi chính là "Đồng ý"; Chọn thủ tục khác đưa về lại danh sách thủ tục.
    assert [chip["send"] for chip in r.chips] == [
        "__action:goto_login", "__action:new_procedure",
    ]


def test_client_cu_khong_nhan_card_chon_noi_o_buoc_xac_nhan():
    conv = _conv(OLD_CLIENT)
    r = flow._to_confirm_procedure(conv, "chung-thuc-ban-sao")
    assert not r.cards
    assert r.display_md == vi.CONFIRM_PROCEDURE["md"].format(
        procedure="Chứng thực bản sao",
        ward="Phường Hải Châu",
        province="Thành phố Đà Nẵng",
    )


def test_chua_chon_noi_thi_van_hien_card_de_chon():
    """Tài khoản chưa gắn tỉnh/xã: card vẫn phải ra để công dân chọn, không được chặn lối."""
    conv = _conv(NEW_CLIENT)
    conv["location"] = {}
    r = flow._to_confirm_procedure(conv, "chung-thuc-ban-sao")
    assert _kinds(r) == ["location_picker"]


def test_chon_thu_tuc_khac_quay_lai_danh_sach():
    conv = _conv(NEW_CLIENT)
    flow._to_confirm_procedure(conv, "chung-thuc-ban-sao")
    conv["state"] = "greet"
    r = flow._handle_greet(conv, Intent("text", ""))
    assert _kinds(r) == ["service_list"]




def test_nut_chot_man_chao_to_va_doc_la_dong_y():
    """Nút này chốt cả thủ tục lẫn nơi làm → phải nổi bật như các nút chuyển bước, và đọc
    "Đồng ý" thay vì "Đúng rồi" (nó xác nhận một khối thông tin, không phải trả lời câu hỏi)."""
    conv = _conv(NEW_CLIENT)
    r = flow._to_confirm_procedure(conv, "chung-thuc-ban-sao")
    confirm = r.chips[0]
    assert confirm["label"] == "Đồng ý"
    assert confirm["cta"] is True and confirm["solid"] is True
    # Nút phụ giữ nguyên dạng chip thường, không được nổi bật ngang nút chốt.
    assert not r.chips[1].get("cta")


def test_nhan_dong_y_co_ban_mong():
    from app.channels.handfree.chat import script_mong as mong

    assert mong.CHIP_HMONG.get("Đồng ý"), "thiếu bản Mông là chip mất dòng dịch"


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
