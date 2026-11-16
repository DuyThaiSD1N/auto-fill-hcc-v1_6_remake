"""Luật cấp cơ quan tiếp nhận (Sở hay UBND xã) và API link kê khai trải sẵn nhánh cho Auto Fill bản cũ."""
import asyncio

import pytest

from app.procedures import router as procedures_router
from app.procedures.agency_level import agency_level, with_agency_level

KEY = "cap-gcn-attp-co-so-kinh-doanh-dich-vu-an-uong-byt"


@pytest.mark.parametrize(("role", "ward", "level"), [
    ("province", "Xã A", "so"),
    ("province", "", "so"),
    ("commune", "Xã A", "xa"),
    ("commune", "", "so"),
    ("user", "Xã A", "xa"),
    ("user", "", "so"),
    ("", "  ", "so"),
])
def test_luat_cap_co_quan(role, ward, level):
    assert agency_level(role, ward) == level


def test_thu_tuc_khong_khai_cap_giu_nguyen():
    item = {"key": "x", "selectSo": True}
    assert with_agency_level(item, "commune", "Xã A") is item


def _link(user, key=KEY):
    links = asyncio.run(procedures_router.ke_khai_links(user))["links"]
    return next(link for link in links if link["key"] == key)


@pytest.mark.parametrize(("user", "select_so", "card"), [
    (None, True, "Cơ quan thực hiện: Sở Y tế"),
    ({"role": "province", "tinh": "Tỉnh Lai Châu", "xa": ""}, True, "Cơ quan thực hiện: Sở Y tế"),
    ({"role": "commune", "tinh": "Tỉnh Lai Châu", "xa": "Phường Tân Phong"}, False, "Cơ quan thực hiện: UBND"),
    ({"role": "user", "tinh": "", "xa": ""}, True, "Cơ quan thực hiện: Sở Y tế"),
])
def test_api_trai_nhanh_theo_tai_khoan_cho_extension_cu(user, select_so, card):
    link = _link(user)
    assert link["selectSo"] is select_so
    assert link["submitCardIncludes"] == card
    # Bản mới vẫn nhận đủ hai nhánh để chọn lại theo xã chọn tay trên popup.
    assert set(link["agencyLevelByAccount"]) == {"xa", "so"}


# Lào Cai, thủ tục cấp Sở trên DVCQG: tick "Sở" xong danh sách ra thẻ Sở NN&MT + 18 thẻ "Chi nhánh VPĐKĐĐ khu vực …".
# HCC tỉnh → thẻ Sở; tài khoản xã → thẻ chi nhánh quản lý xã đó (QĐ 2748/QĐ-UBND ngày 31/12/2025 của UBND tỉnh).
LAO_CAI_SO = "Sở Nông nghiệp và Môi trường tỉnh Lào Cai"
LAO_CAI_KEYS = (
    "xoa-dang-ky-bien-phap-bao-dam-lao-cai", "giao-dat-cho-thue-dat-lao-cai",
    "dieu-chinh-quyet-dinh-giao-dat-cho-thue-dat-lao-cai", "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-lao-cai",
    "dang-ky-bien-dong-dat-dai-lao-cai", "chuyen-muc-dich-su-dung-dat-lao-cai",
    "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep-lao-cai", "dang-ky-bien-dong-chuyen-nhuong-thua-ke-tang-cho-dvcqg-lao-cai",
    "dang-ky-bien-dong-doi-ten-nguoi-su-dung-dat-lao-cai", "dinh-chinh-gcn-da-cap-dvcqg-lao-cai",
)


# Tư pháp: chỉ "Cấp bản sao Trích lục hộ tịch, bản sao Giấy khai sinh" phân luồng theo tài khoản (người dùng chốt
# 16/11/2026) — HCC tỉnh / không có xã → Sở Tư pháp, tài khoản có xã → chọn Phường/Xã như cũ. Thủ tục tư pháp khác
# chọn cơ quan như trước, không theo nhánh.
TU_PHAP_SO = "Cơ quan thực hiện: Sở Tư pháp"
TU_PHAP_KEY = "trich-luc-ks"
TU_PHAP_KHAC = ("khai-sinh-dang-ky-thuong", "ket-hon", "xac-nhan-tinh-trang-hon-nhan", "khai-tu",
                "chung-thuc-ban-sao", "chung-thuc-giao-dich-tai-san", "cap-ban-sao-so-goc",
                "bau-to-truong-to-hoa-giai", "yeu-cau-tro-giup-phap-ly")
_TINH = {"role": "province", "tinh": "Tỉnh Lào Cai", "xa": ""}


@pytest.mark.parametrize(("user", "level"), [
    ({"role": "province", "tinh": "Tỉnh Lào Cai", "xa": ""}, "so"),
    ({"role": "province", "tinh": "Tỉnh Lào Cai", "xa": "Phường Yên Bái"}, "so"),
    ({"role": "commune", "tinh": "Tỉnh Lào Cai", "xa": ""}, "so"),
    ({"role": "commune", "tinh": "Tỉnh Lào Cai", "xa": "Phường Yên Bái"}, "xa"),
])
def test_trich_luc_tinh_vao_so_tu_phap_xa_giu_nhu_cu(user, level):
    link = _link(user, TU_PHAP_KEY)
    if level == "so":
        assert link["selectSo"] is True and link["submitCardIncludes"] == TU_PHAP_SO
    else:
        assert "selectSo" not in link and "submitCardIncludes" not in link


def test_tu_phap_khac_khong_phan_luong_theo_tai_khoan():
    from app.procedures.ke_khai_links import KE_KHAI_LINKS

    by_key = {link["key"]: link for link in KE_KHAI_LINKS}
    for key in (*TU_PHAP_KHAC, "cong-nhan-hoa-giai-vien"):
        assert "agencyLevelByAccount" not in by_key[key], key
    # Tài khoản tỉnh vẫn chọn cơ quan như trước (không bị gạt sang Sở Tư pháp).
    for key in TU_PHAP_KHAC[:7]:
        link = _link(_TINH, key)
        assert link.get("submitCardIncludes") != TU_PHAP_SO, key
        assert "selectSo" not in link, key


def test_tro_ly_chi_trich_luc_gat_so_va_bam_the_so_tu_phap():
    from app.channels.handfree.procedure_registry import get_procedure

    proc = get_procedure(TU_PHAP_KEY)
    so = with_agency_level(proc, "province", "")
    assert so["agencyProvinceOnly"] is True and so["agencySoFirst"] is True
    assert so["agencyCardIncludes"] == TU_PHAP_SO
    xa = with_agency_level(proc, "commune", "Phường Yên Bái")
    assert not xa.get("agencyProvinceOnly") and not xa.get("agencySoFirst") and not xa.get("agencyCardIncludes")
    for key in TU_PHAP_KHAC[:7]:
        other = get_procedure(key)
        assert "agencyLevelByAccount" not in other, key
        assert not with_agency_level(other, "province", "").get("agencyCardIncludes"), key
    # Hòa giải chỉ cấp xã; trợ giúp pháp lý vốn nộp Sở với mọi tài khoản → giữ như trước.
    hoa_giai = get_procedure("bau-to-truong-to-hoa-giai")
    assert not with_agency_level(hoa_giai, "province", "").get("agencySoFirst")
    tro_giup = get_procedure("yeu-cau-tro-giup-phap-ly")
    assert with_agency_level(tro_giup, "commune", "Phường Yên Bái")["agencySoFirst"] is True
    assert not with_agency_level(tro_giup, "province", "").get("agencyCardIncludes")

def _fold(value: str) -> str:
    """Bản Python của fold() trong extension content/agency-select.js (so chuỗi thẻ)."""
    import re
    import unicodedata

    text = str(value or "").replace("đ", "d").replace("Đ", "D")
    text = "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def test_lao_cai_bang_chi_nhanh_phu_du_99_xa_va_giong_nhau_o_10_thu_tuc():
    from app.procedures.ke_khai_links import KE_KHAI_LINKS

    by_key = {link["key"]: link for link in KE_KHAI_LINKS}
    tables = [by_key[key]["agencyLevelByAccount"]["xa"]["submitCardIncludesByWard"] for key in LAO_CAI_KEYS]
    assert all(table == tables[0] for table in tables)
    wards = set(_lao_cai_wards())
    assert set(tables[0]) == wards and len(wards) == 99
    assert len(set(tables[0].values())) == 18
    for key in LAO_CAI_KEYS:
        link = by_key[key]
        assert link["selectSo"] is True and link["provinceOnlyAgency"] is True, key
        assert link["submitCardIncludes"] == LAO_CAI_SO, key
        assert link["agencyLevelByAccount"]["so"] == {"submitCardIncludesByWard": {}}, key


def _lao_cai_wards():
    import json
    from pathlib import Path

    data = json.loads((Path(procedures_router.__file__).parents[1] / "locations" / "data" / "vn_provinces_wards.json")
                      .read_text(encoding="utf-8"))
    province = next(p for p in data["provinces"] if p["code_name"] == "lao_cai")
    return [w["full_name"] for w in province["wards"]]


@pytest.mark.parametrize(("user", "card"), [
    ({"role": "province", "tinh": "Tỉnh Lào Cai", "xa": "Phường Cam Đường"}, LAO_CAI_SO),
    ({"role": "province", "tinh": "Tỉnh Lào Cai", "xa": ""}, LAO_CAI_SO),
    ({"role": "commune", "tinh": "Tỉnh Lào Cai", "xa": "Xã Mường Lai"}, "khu vực Lục Yên"),
    ({"role": "commune", "tinh": "Tỉnh Lào Cai", "xa": "Phường Cam Đường"}, "khu vực Lào Cai - Cam Đường"),
    ({"role": "commune", "tinh": "Tỉnh Lào Cai", "xa": "Xã Khánh Hoà"}, "khu vực Lục Yên"),
    ({"role": "commune", "tinh": "Tỉnh Lào Cai", "xa": "Xã Sín Chéng"}, "khu vực Si Ma Cai"),
])
def test_lao_cai_tinh_vao_so_xa_vao_chi_nhanh_vpdkdd(user, card):
    for key in LAO_CAI_KEYS:
        link = _link(user, key)
        assert link["selectSo"] is True, key
        # Cùng cách popup.js:submitCardIncludesFor chọn: xã có trong bảng thì lấy bảng, không thì submitCardIncludes.
        chosen = (link.get("submitCardIncludesByWard") or {}).get(user["xa"]) or link["submitCardIncludes"]
        assert chosen == card, key


def test_lao_cai_chuoi_the_khop_ten_chi_nhanh_tren_cong():
    """Cổng ghi tên chi nhánh hai kiểu (đủ chữ / viết tắt VPĐKĐĐ, tỉnh viết thường) — fold vẫn khớp."""
    the = {
        "khu vực Lào Cai - Cam Đường": "Cơ quan thực hiện: Chi nhánh văn phòng đăng ký đất đai khu vực Lào Cai - Cam Đường",
        "khu vực Lục Yên": "Cơ quan thực hiện: Chi nhánh VPĐKĐĐ khu vực Lục Yên",
        LAO_CAI_SO: "Cơ quan thực hiện: Sở Nông nghiệp và Môi trường tỉnh lào Cai",
    }
    for wanted, card in the.items():
        assert _fold(wanted) in _fold(card)
    # Thẻ Sở không bị chuỗi chi nhánh nào bắt nhầm (và ngược lại).
    from app.procedures.ke_khai_links import KE_KHAI_LINKS

    table = next(link for link in KE_KHAI_LINKS if link["key"] == LAO_CAI_KEYS[0])["agencyLevelByAccount"]["xa"]
    chi_nhanh = set(table["submitCardIncludesByWard"].values())
    for wanted in chi_nhanh:
        assert _fold(wanted) not in _fold(the[LAO_CAI_SO])
        assert _fold(LAO_CAI_SO) not in _fold(f"Cơ quan thực hiện: Chi nhánh VPĐKĐĐ {wanted}")
        # Chuỗi của chi nhánh này không lọt vào thẻ chi nhánh khác (vd "Yên Bái" / "Yên Bình", "Văn Yên" / "Bảo Yên").
        for other in chi_nhanh - {wanted}:
            assert _fold(wanted) not in _fold(f"Cơ quan thực hiện: Chi nhánh VPĐKĐĐ {other}"), (wanted, other)
