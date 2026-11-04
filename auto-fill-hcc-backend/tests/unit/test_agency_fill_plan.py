"""Kế hoạch điền hộ khối "Chọn cơ quan thực hiện" — dùng CHUNG hai kênh.

Handfree phát qua action fill_agency_plan; Auto Fill (no handfree) nạp qua /api/v1/procedures
rồi hiện nút "Chọn cơ quan thực hiện". Hai registry khai riêng nhưng phải trỏ về cùng một
nguồn: chép thành hai bản là sớm muộn sửa một bên, bên kia lặng lẽ giữ giá trị cũ — mà sai ở
đây thì hồ sơ nộp lên SAI CƠ QUAN, không ai phát hiện tới lúc bị trả lại.
"""
import pytest

from app.channels.handfree.procedure_registry import PROCEDURES as HANDFREE
from app.procedures import agency_plans
from app.procedures.registry import PROCEDURES as CORE

_KEY = "khai-sinh-dang-ky"
# Engine fill-angular của CẢ HAI bản extension hiểu đúng bấy nhiêu comp (đã đối chiếu source).
_COMPS = {"select", "diachi", "checkbox", "radio-bylabel", "raw", "date", "ngaysinh", "text"}


def _entry(procedures):
    return next(p for p in procedures if p["key"] == _KEY)


def test_hai_kenh_dung_cung_mot_ke_hoach():
    assert _entry(CORE)["agencyFillPlan"] == _entry(HANDFREE)["agencyFillPlan"]
    assert _entry(CORE)["agencyFillPlan"] == agency_plans.LIEN_THONG_KHAI_SINH


def test_extension_no_handfree_nhan_duoc_ke_hoach():
    """public_list() trả thẳng PROCEDURES — thiếu khoá này là nút không bao giờ hiện."""
    from app.procedures.registry import public_list

    assert _entry(public_list())["agencyFillPlan"]


@pytest.mark.parametrize("step", agency_plans.LIEN_THONG_KHAI_SINH)
def test_moi_buoc_dung_hop_dong_fields(step):
    assert set(step) == {"name", "comp", "value"}, step
    assert step["comp"] in _COMPS, f"engine không hiểu comp '{step['comp']}'"


def test_dien_dung_sau_o_can_cham_tay():
    """Khoá danh sách ô. Thêm ô readonly (Cơ quan thực hiện, tên cơ quan BHXH…) là ghi đè lên
    giá trị cổng vừa tự suy; thêm khối thường trú là đè lên phần "Cùng địa bàn" tự mirror."""
    assert [s["name"] for s in agency_plans.LIEN_THONG_KHAI_SINH] == [
        "IsNuocNgoai", "CqdkksDiaChi", "DkksTruongHop",
        "CqdkttIsDkks", "DkttTruongHop", "IsCapTheCanCuoc",
    ]


def test_tick_cap_the_can_cuoc():
    """Yêu cầu nghiệp vụ: mặc định tích "Cấp thẻ căn cước" cho trẻ."""
    step = next(s for s in agency_plans.LIEN_THONG_KHAI_SINH if s["name"] == "IsCapTheCanCuoc")
    assert step["comp"] == "checkbox" and step["value"] is True


def test_cho_trong_dia_ban_dung_dung_ten_placeholder():
    """Hai kênh đều tự thay {province}/{ward}; đổi tên chỗ trống ở đây mà quên sửa bên kia là
    ô Tỉnh nhận nguyên chuỗi "{province}"."""
    diachi = next(s for s in agency_plans.LIEN_THONG_KHAI_SINH if s["comp"] == "diachi")
    assert diachi["value"] == {"tinh": "{province}", "xa": "{ward}"}


def test_khong_con_cho_trong_nao_khac():
    """Chỗ trống lạ sẽ không được thay và đi thẳng vào ô trên cổng."""
    import json
    import re

    found = set(re.findall(r"\{(\w+)\}", json.dumps(agency_plans.LIEN_THONG_KHAI_SINH,
                                                    ensure_ascii=False)))
    assert found <= {"province", "ward"}, f"chỗ trống chưa ai thay: {found - {'province', 'ward'}}"


# ── Chặng cổng tỉnh Quảng Ninh (provincePortalFlow) — trợ lý dùng CHUNG cấu hình ke_khai_links với Auto Fill ──
_QN_LOC = {"province": "Tỉnh Quảng Ninh", "province_slug": "quangninh", "ward": "Phường Hạ Long"}


def _qn_conv(provincial=True):
    from app.channels.handfree.chat import store

    conv = store.new_conversation(location=dict(_QN_LOC))
    if provincial:
        conv["client_capabilities"] = {"supportsProvincePortal": True, "supportsAgencyCard": True}
    return conv


def _handfree(key):
    return next(p for p in HANDFREE if p["key"] == key)


def test_quang_ninh_cung_cau_hinh_cong_tinh_voi_auto_fill():
    """Thủ tục có provincePortalFlow ở ke_khai_links: trợ lý dùng đúng bản đó (dòng, chi nhánh VPĐK), không chép tay."""
    from app.procedures.ke_khai_links import KE_KHAI_LINKS

    links = {l["code"]: l for l in KE_KHAI_LINKS if l["label"].startswith("Quảng Ninh - ")}
    qn = [p for p in HANDFREE if p.get("provinceOnly") == ["quangninh"]]
    assert len(qn) == 14
    for proc in qn:
        link = links[proc["code"]]
        assert proc["keKhaiUrl"] == link["url"], proc["key"]
        assert proc["provincePortalFlow"]["host"] == "dichvucong.quangninh.gov.vn", proc["key"]
        if link.get("provincePortalFlow"):
            assert proc["provincePortalFlow"] == link["provincePortalFlow"], proc["key"]
        assert bool(proc.get("agencyProvinceOnly")) == bool(link.get("provinceOnlyAgency")), proc["key"]
        assert proc.get("agencyCardIncludes", "") == link.get("submitCardIncludes", ""), proc["key"]
        assert proc.get("agencyWard", "") == link.get("agencyWard", ""), proc["key"]


def test_quang_ninh_bam_dung_dong_bang_thu_tuc_mot_lan():
    from app.channels.handfree.chat import flow

    proc = flow.get_procedure("dang-ky-bien-dong-doi-ten-quang-ninh-mien-nui-hai-dao")
    conv = _qn_conv()
    ctx = {"provinceRows": 3, "loggedIn": True}
    r = flow._guide_login_on_page(conv, proc, conv["location"], ctx)  # noqa: SLF001
    assert r.actions == [{"type": "pick_province_row", "rowIncludes": "Miền núi, hải đảo", "rowIndex": 2}]
    # Watcher báo lại giữa lúc cổng đang dựng modal → không bấm lần hai (mở hai hồ sơ).
    again = flow._guide_login_on_page(conv, proc, conv["location"], ctx)  # noqa: SLF001
    assert again.actions == [] and not again.display_md


def test_quang_ninh_extension_cu_dan_bam_tay_khong_xac_nhan_ho():
    """Extension chưa biết chọn cơ quan theo tên: bấm Xác nhận lúc này là nộp vào cơ quan cổng để sẵn."""
    from app.channels.handfree.chat import flow

    proc = flow.get_procedure("tach-hop-thua-dat-quang-ninh-mien-nui-hai-dao")
    conv = _qn_conv(provincial=False)
    r = flow._guide_login_on_page(conv, proc, conv["location"], {"provinceRows": 6})  # noqa: SLF001
    assert not r.actions and "dòng thứ 4" in r.display_md
    r = flow._guide_login_on_page(conv, proc, conv["location"], {"infoModal": True})  # noqa: SLF001
    assert not r.actions and "Chi nhánh Văn phòng đăng ký đất đai số 12 Cô Tô" in r.display_md


def test_quang_ninh_modal_chon_chi_nhanh_theo_ten_va_dien_o_trong():
    from app.channels.handfree.chat import flow

    proc = flow.get_procedure("xoa-dang-ky-bien-phap-bao-dam-quang-ninh")
    conv = _qn_conv()
    r = flow._guide_login_on_page(conv, proc, conv["location"], {"infoModal": True})  # noqa: SLF001
    action = r.actions[0]
    assert action["type"] == "confirm_info_modal"
    assert action["infoFields"] == [{"value": "Chi nhánh Văn phòng đăng ký đất đai số 12 Cô Tô"}]
    assert action["fillEmpty"] is True


def test_quang_ninh_dang_nhap_rieng_cong_tinh():
    from app.channels.handfree.chat import flow

    proc = flow.get_procedure("dang-ky-bien-phap-bao-dam-quang-ninh")
    conv = _qn_conv()
    r = flow._guide_login_on_page(  # noqa: SLF001
        conv, proc, conv["location"], {"provinceLoginDialog": True, "loginPage": True, "provinceRows": 2})
    assert "thành phố Quảng Ninh" in r.display_md and "Đăng nhập bằng VNeID" in r.display_md
    assert r.actions == [{"type": "collapse_after_tts"}]


# ── Gạt "Sở" xong chọn đúng cơ quan theo tỉnh (soAgencyByProvince) — cùng bảng ke_khai_links với Auto Fill ──
_ATTP_CT = "cap-gcn-attp-cong-thuong"
_CHI_CUC_ATTP = "Chi cục An toàn thực phẩm thành phố"
_DN_LOC = {"province": "Thành phố Đà Nẵng", "province_slug": "danang", "ward": "Phường Hải Châu"}


def _so_conv(loc, so_agency=True):
    from app.channels.handfree.chat import store

    conv = store.new_conversation(location=dict(loc))
    conv["procedure_key"] = _ATTP_CT
    conv["client_capabilities"] = {"supportsSoAgency": True} if so_agency else {"supportsAgencyCard": True}
    return conv


def test_attp_cong_thuong_da_nang_cung_bang_voi_auto_fill():
    from app.procedures.ke_khai_links import KE_KHAI_LINKS

    link = next(l for l in KE_KHAI_LINKS if l.get("code") == "2.000591")
    assert link["key"] == _ATTP_CT and link["selectSo"] is True
    assert link["soAgencyByProvince"] == {"danang": _CHI_CUC_ATTP}
    assert _handfree(_ATTP_CT)["agencySoByProvince"] == link["soAgencyByProvince"]
    # Bản cấp lại (2.000535) không khai → giữ Sở cổng điền sẵn.
    assert "agencySoByProvince" not in _handfree("cap-lai-giay-chung-nhan-du-dieu-kien-an-toan-thuc-pham")


def test_attp_cong_thuong_da_nang_gat_so_roi_chon_chi_cuc():
    from app.channels.handfree.chat import flow

    conv = _so_conv(_DN_LOC)
    proc = flow.get_procedure(_ATTP_CT)
    r = flow._guide_login_on_page(conv, proc, conv["location"], {"agencyBlock": True})  # noqa: SLF001
    assert r.actions == [{"type": "select_agency", "province": "Thành phố Đà Nẵng", "ward": "",
                          "soMode": True, "soAgency": _CHI_CUC_ATTP}]
    # Câu dặn khi chọn hỏng / màn đăng nhập đọc đúng tên cơ quan, không phải "Sở Công Thương".
    assert flow._agency_ward_display(proc, conv["location"]) == _CHI_CUC_ATTP  # noqa: SLF001


def test_attp_cong_thuong_tinh_khac_giu_so_dien_san():
    from app.channels.handfree.chat import flow

    conv = _so_conv({"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Phường Tân Phong"})
    proc = flow.get_procedure(_ATTP_CT)
    r = flow._guide_login_on_page(conv, proc, conv["location"], {"agencyBlock": True})  # noqa: SLF001
    assert r.actions == [{"type": "select_agency", "province": "Tỉnh Lai Châu", "ward": "", "soMode": True}]
    assert flow._agency_ward_display(proc, conv["location"]) == "Sở Công Thương"  # noqa: SLF001


def test_attp_cong_thuong_da_nang_extension_cu_dan_chon_tay():
    """Engine cũ chỉ gạt "Sở" rồi nộp vào Sở cổng điền sẵn → không bắn lệnh, dặn chọn Chi cục."""
    from app.channels.handfree.chat import flow

    conv = _so_conv(_DN_LOC, so_agency=False)
    proc = flow.get_procedure(_ATTP_CT)
    r = flow._guide_login_on_page(conv, proc, conv["location"], {"agencyBlock": True})  # noqa: SLF001
    assert r.actions == [] and _CHI_CUC_ATTP in r.display_md and "Sở" in r.display_md
    again = flow._guide_login_on_page(conv, proc, conv["location"], {"agencyBlock": True})  # noqa: SLF001
    assert again.actions == [] and not again.display_md


def test_quang_ninh_xa_co_dinh_dac_khu_co_to():
    """agencyWard (ke_khai_links): DVCQG chọn Đặc khu Cô Tô thay vì xã của tài khoản."""
    from app.channels.handfree.chat import flow

    proc = flow.get_procedure("dang-ky-cap-gcn-toan-bo-dien-tich-dang-su-dung-quang-ninh")
    conv = _qn_conv()
    r = flow._guide_login_on_page(conv, proc, conv["location"], {"agencyBlock": True})  # noqa: SLF001
    assert r.actions[0]["type"] == "select_agency"
    assert r.actions[0]["ward"] == "Đặc khu Cô Tô"
