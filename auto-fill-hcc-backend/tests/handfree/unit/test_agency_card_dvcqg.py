"""Thủ tục an toàn thực phẩm chọn radio Sở và thẻ Sở Y tế trên DVCQG.

"Cấp giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm … Bộ Y tế" chọn Tỉnh, chuyển radio
"Phường/Xã" sang "Sở", rồi chọn thẻ "Cơ quan thực hiện: Sở Y tế".

Bản trên chợ chỉ biết bấm thẻ đầu → BE gác bằng `supportsAgencyCard`, thiếu cờ thì KHÔNG bắn lệnh.
"""
import pytest

from app.channels.handfree.chat import flow
from app.channels.handfree.chat.flow import Intent
from app.channels.handfree.procedure_registry import get_procedure

KEY = "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham"
CARD = "Cơ quan thực hiện: Sở Y tế"
NEW_CLIENT = {"supportsAgencyCard": True}
OLD_CLIENT = {"supportsRating": True}
LOC = {"province": "Tỉnh Lai Châu", "ward": "Phường Tân Phong"}
AGENCY_PAGE = {"agencyBlock": True}


def _conv(caps, key=KEY):
    return {
        "_id": "t-card", "state": "guide_login", "history": [], "milestones": [],
        "procedure_key": key, "client_capabilities": dict(caps), "location": dict(LOC),
    }


def _on_agency_page(conv):
    proc = get_procedure(conv["procedure_key"]) or {}
    return flow._guide_login_on_page(conv, proc, dict(LOC), dict(AGENCY_PAGE))


def test_entry_giong_huu_tri_chi_khac_the_ket_qua():
    proc = get_procedure(KEY)
    pension = get_procedure("dieu-chinh-huu-tri-xa-hoi")
    assert proc["needsAgencySelect"] is True
    assert proc["agencyProvinceOnly"] is True
    assert proc["agencySoFirst"] is True
    assert "maePortal" not in proc
    assert proc["wizard"] == pension["wizard"]
    assert proc["agencyCardIncludes"] == CARD
    assert "agencyCardIncludes" not in pension, "hưu trí vẫn bấm thẻ đầu như cũ"
    # Một dòng đính kèm gom mọi loại giấy → planner dồn hết vào đó.
    assert proc["hideRepeatableHint"] is True
    assert proc["requiredDocs"][-1]["key"] == "khac"


def test_client_moi_bam_dung_the_theo_chu():
    r = _on_agency_page(_conv(NEW_CLIENT))
    assert r.actions == [{
        "type": "select_agency", "province": "Tỉnh Lai Châu",
        "ward": "", "soMode": True, "cardIncludes": CARD,
    }]


def test_client_cu_khong_nhan_lenh_ma_duoc_dan_bam_dung_the():
    conv = _conv(OLD_CLIENT)
    r = _on_agency_page(conv)
    assert r.actions == [], "engine cũ không thể xác nhận thẻ Sở Y tế theo cấu hình"
    assert CARD in r.display_md and "Nộp trực tuyến" in r.display_md
    # Watcher báo lại trang y hệt → không đọc lại câu dặn.
    again = _on_agency_page(conv)
    assert not again.display_md and not again.actions


def test_thu_tuc_khong_khai_the_giu_nguyen_the_dau():
    conv = _conv(NEW_CLIENT, key="dieu-chinh-huu-tri-xa-hoi")
    r = _on_agency_page(conv)
    assert len(r.actions) == 1 and "cardIncludes" not in r.actions[0]


def test_khong_thay_the_dung_thi_dan_bam_dung_the_khong_phai_chon_lai_xa():
    conv = _conv(NEW_CLIENT)
    r = flow._handle_guide_login(
        conv, Intent("event", "agency_card_missing", {"value": "Không thấy thẻ"}))
    assert CARD in r.display_md
    assert "thẻ đầu tiên" in r.display_md


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
