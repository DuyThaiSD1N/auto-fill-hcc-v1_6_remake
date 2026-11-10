"""Thủ tục an toàn thực phẩm (Bộ Y tế) trên DVCQG: nộp Sở Y tế hay UBND xã theo tài khoản.

Cả hai cấp cùng tiếp nhận nên kết quả ra nhiều thẻ, thẻ đầu là cấp Sở → luôn chốt thẻ theo chữ. Cấp nộp
(agencyLevelByAccount): HCC tỉnh → Sở (chỉ chọn Tỉnh, gạt sang "Sở"); tài khoản khác có xã → UBND xã đó;
chưa có xã → Sở.

Bản trên chợ chỉ biết bấm thẻ đầu → BE gác bằng `supportsAgencyCard`, thiếu cờ thì KHÔNG bắn lệnh.
"""
import pytest

from app.channels.handfree.chat import flow
from app.channels.handfree.chat.flow import Intent
from app.channels.handfree.procedure_registry import get_procedure

KEY = "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham"
SO_CARD = "Cơ quan thực hiện: Sở Y tế"
XA_CARD = "Cơ quan thực hiện: UBND"
NEW_CLIENT = {"supportsAgencyCard": True}
OLD_CLIENT = {"supportsRating": True}
LOC = {"province": "Tỉnh Lai Châu", "ward": "Phường Tân Phong"}
AGENCY_PAGE = {"agencyBlock": True}


def _conv(caps, key=KEY, role="province", loc=LOC):
    return {
        "_id": "t-card", "state": "guide_login", "history": [], "milestones": [],
        "procedure_key": key, "client_capabilities": dict(caps), "location": dict(loc),
        "auth_user": {"id": "u1", "role": role},
    }


def _on_agency_page(conv):
    r = flow._handle_guide_login(conv, Intent("event", "page_status", dict(AGENCY_PAGE)))
    return r


def test_entry_khai_hai_cap_va_khong_chot_cung_cap_nao():
    proc = get_procedure(KEY)
    pension = get_procedure("dieu-chinh-huu-tri-xa-hoi")
    assert proc["needsAgencySelect"] is True
    levels = proc["agencyLevelByAccount"]
    assert levels["so"] == {"agencyProvinceOnly": True, "agencySoFirst": True, "agencyCardIncludes": SO_CARD}
    assert levels["xa"]["agencyCardIncludes"] == XA_CARD and not levels["xa"]["agencySoFirst"]
    for key in ("agencyProvinceOnly", "agencySoFirst", "agencyCardIncludes"):
        assert key not in proc, f"{key} phải nằm trong nhánh cấp, không chốt cứng"
    assert "maePortal" not in proc
    assert proc["wizard"] == pension["wizard"]
    assert "agencyCardIncludes" not in pension, "hưu trí vẫn bấm thẻ đầu như cũ"
    # Một dòng đính kèm gom mọi loại giấy → planner dồn hết vào đó.
    assert proc["hideRepeatableHint"] is True
    assert proc["requiredDocs"][-1]["key"] == "khac"


def test_tai_khoan_tinh_nop_so_du_dang_chon_xa():
    r = _on_agency_page(_conv(NEW_CLIENT, role="province"))
    assert r.actions == [{
        "type": "select_agency", "province": "Tỉnh Lai Châu",
        "ward": "", "soMode": True, "cardIncludes": SO_CARD,
    }]


@pytest.mark.parametrize("role", ["commune", "user", ""])
def test_tai_khoan_co_xa_nop_ubnd_xa(role):
    r = _on_agency_page(_conv(NEW_CLIENT, role=role))
    assert len(r.actions) == 1
    action = r.actions[0]
    assert action["type"] == "select_agency" and action["ward"], "phải chọn cả xã"
    assert "soMode" not in action
    assert action["cardIncludes"] == XA_CARD


@pytest.mark.parametrize("role", ["commune", "user"])
def test_chua_co_xa_thi_nop_so(role):
    r = _on_agency_page(_conv(NEW_CLIENT, role=role, loc={"province": "Tỉnh Lai Châu", "ward": ""}))
    assert r.actions == [{
        "type": "select_agency", "province": "Tỉnh Lai Châu",
        "ward": "", "soMode": True, "cardIncludes": SO_CARD,
    }]


def test_client_cu_khong_nhan_lenh_ma_duoc_dan_bam_dung_the():
    conv = _conv(OLD_CLIENT, role="province")
    r = _on_agency_page(conv)
    assert r.actions == [], "engine cũ không thể xác nhận thẻ theo cấu hình"
    assert SO_CARD in r.display_md and "Nộp trực tuyến" in r.display_md
    # Watcher báo lại trang y hệt → không đọc lại câu dặn.
    again = _on_agency_page(conv)
    assert not again.display_md and not again.actions


def test_thu_tuc_khong_khai_the_giu_nguyen_the_dau():
    conv = _conv(NEW_CLIENT, key="dieu-chinh-huu-tri-xa-hoi")
    r = _on_agency_page(conv)
    assert len(r.actions) == 1 and "cardIncludes" not in r.actions[0]


@pytest.mark.parametrize(("role", "card"), [("province", SO_CARD), ("commune", XA_CARD)])
def test_khong_thay_the_dung_thi_dan_bam_dung_the_theo_cap(role, card):
    conv = _conv(NEW_CLIENT, role=role)
    r = flow._handle_guide_login(
        conv, Intent("event", "agency_card_missing", {"value": "Không thấy thẻ"}))
    assert card in r.display_md
    assert "thẻ đầu tiên" in r.display_md


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
