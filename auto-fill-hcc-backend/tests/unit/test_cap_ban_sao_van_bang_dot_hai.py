"""Cấp bản sao văn bằng từ sổ gốc: Phần I trước khi tích "Người nộp là chủ hồ sơ", ô mặc định + thanh tra / điền đợt 2."""

import asyncio

from app.pipelines._shared.thanh_tra.ho_so import Case, Finding
from app.pipelines.cap_ban_sao_van_bang_so_goc import thanh_tra
from app.pipelines.cap_ban_sao_van_bang_so_goc.process import mapper
from app.pipelines.cap_ban_sao_van_bang_so_goc.thanh_tra import dinh_danh
from app.procedures.registry import get_procedure

# Dữ liệu bịa.
_CHU = {
    "VanBang_HoTen": "TRẦN VĂN MẪU",
    "VanBang_SoGiayTo": "001203001234",
    "ChuHoSo_HoTen": "TRẦN VĂN MẪU",
    "ChuHoSo_SoGiayTo": "001203001234",
    "ChuHoSo_ThuongTru": {"tinh": "Lào Cai", "xa": "Mẫu Sơn", "diaChi": "Thôn Mẫu"},
    "VanBang_DienThoai": "0912000111",
}
_TAI_KHOAN = {"applicantFullname": "Trần Văn Mẫu", "applicantIdentityNumber": "001203001234"}


def _map(values, form_context=None):
    out, _ = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], {"formContext": form_context or {}})
    return out


def test_registry_bat_dot_hai_formio():
    assert get_procedure("cap-ban-sao-van-bang-so-goc")["secondPass"] == "formio"
    assert [i.key for i in thanh_tra.INSPECTORS] == ["dinh_danh"]


def test_tich_nguoi_nop_la_chu_ghi_dia_chi_dien_thoai_phan_i_truoc():
    out = _map(_CHU, _TAI_KHOAN)
    got = {f["name"]: f["value"] for f in out}
    names = [f["name"] for f in out]
    assert got["data[isOwnerDossier]"] is True
    assert got["data[province]"] == "Tỉnh Lào Cai" and got["data[address]"] == "Thôn Mẫu"
    assert got["data[phoneNumber]"] == "0912000111"
    assert names.index("data[isOwnerDossier]") > names.index("data[phoneNumber]")
    # Họ tên / số / ngày sinh Phần I vẫn để VNeID đổ.
    for name in ("data[fullname]", "data[identityNumber]", "data[birthday]"):
        assert name not in got


def test_so_ban_sao_mac_dinh_to_vang_va_co_quan_cap_khong_ro_tinh_de_trong():
    got = {f["name"]: f for f in _map(_CHU)}
    assert got["data[requestQty]"]["value"] == "1" and got["data[requestQty]"]["default"] is True
    assert "data[do]" not in got
    got = {f["name"]: f for f in _map(dict(_CHU, Phieu_SoLuongBanSao="02", Phieu_KinhGui="Sở Giáo dục và Đào tạo Mẫu"))}
    assert got["data[requestQty]"]["value"] == "02" and "default" not in got["data[requestQty]"]
    assert got["data[do]"]["value"] == "Sở Giáo dục và Đào tạo Mẫu"


def test_dinh_danh_chi_sua_chinh_ta_cung_nguoi():
    case = Case([], "", {"VanBang_HoTen": "Lê Thị Hồng Nhy", "VanBang_SoGiayTo": "001186001234",
                         "VanBang_NgaySinh": "15/07/1980"}, {})
    assert not dinh_danh.check(dinh_danh.HO_TEN, {"VanBang_HoTen": "LÊ THỊ HỒNG NHUNG"}, case)
    assert dinh_danh.check(dinh_danh.HO_TEN, {"VanBang_HoTen": "Lê Thị Hồng Mai"}, case)  # người khác
    assert dinh_danh.check(dinh_danh.HO_TEN, {"VanBang_HoTen": "Phạm Văn Khác"}, case)
    assert not dinh_danh.check(dinh_danh.SO, {"VanBang_SoGiayTo": "001180001234"}, case)
    assert dinh_danh.check(dinh_danh.SO, {"VanBang_SoGiayTo": "079099888777"}, case)
    assert not dinh_danh.check(dinh_danh.NGAY_SINH, {"VanBang_NgaySinh": "12/07/1980"}, case)
    # Lượt trích bỏ trống tên văn bằng: form mang tên trên căn cước → so với tên đó (LLM hay chép thiếu chữ cuối).
    case = Case([], "", {"ChuHoSo_HoTen": "Nguyễn Thị Mẫu Ny"}, {})
    assert dinh_danh.check(dinh_danh.HO_TEN, {"VanBang_HoTen": "NGUYỄN THỊ MẪU"}, case)


def test_dinh_danh_dem_trang_giay_in_ke_ca_mrz(monkeypatch):
    text = ("───── Trang 1/3 ─────\nTên tôi là: Lê Thị Hồng Nhy\n"
            "───── Trang 2/3 ─────\nHọ và tên: LÊ THỊ HỒNG NHUNG\n"
            "───── Trang 3/3 ─────\nIDVNM0801234567001180001234<<1\n8007124F3007125VNM<<<<<<<<<<<6\nLE<<THI<HONG<NHUNG<<<<<<<<<<<<")
    case = Case([{"text": text}], "", {"VanBang_HoTen": "Lê Thị Hồng Nhy"}, {})
    assert dinh_danh.support(dinh_danh.HO_TEN.fields[0], "LÊ THỊ HỒNG NHUNG", case) == 2
    assert dinh_danh.support(dinh_danh.HO_TEN.fields[0], "Lê Thị Hồng Nhy", case) == 1

    async def fake(inspector, case, title):
        return [Finding(inspector, dinh_danh.HO_TEN, {"VanBang_HoTen": "LÊ THỊ HỒNG NHUNG"}, "Họ và tên: LÊ THỊ HỒNG NHUNG", 1)]

    monkeypatch.setattr(dinh_danh.engine, "llm_findings", fake)
    found = asyncio.run(dinh_danh.find(dinh_danh.INSPECTOR, case, "thử"))
    assert found[0].backed is True

