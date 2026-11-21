"""Thanh tra kết hôn có yếu tố nước ngoài: họ tên theo MRZ hộ chiếu, số lần kết hôn theo hàng tờ khai, điền đợt 2."""

import asyncio

from app.pipelines._shared.thanh_tra.ho_so import Case
from app.pipelines.ket_hon_nuoc_ngoai.process.runner import run
from app.pipelines.ket_hon_nuoc_ngoai.thanh_tra import dinh_danh, tinh_trang
from app.pipelines.ket_hon_nuoc_ngoai.thanh_tra.chu_the import SIDES
from app.procedures.registry import get_procedure
from app.second_pass import service as second_pass

_PASSPORT = (
    "PASSPORT\nSurname: KIM\nGiven names: ABCDE\n"
    "PMKORKIM<<ABCDE<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\nM000000000KOR0001011M3001011<<<<<<<<<<<<<<00\n"
)


def _find(values, text):
    case = Case([{"name": "ho_chieu.pdf", "text": text}], "", values, {})
    return asyncio.run(dinh_danh.find(dinh_danh.INSPECTOR, case, ""))


def test_ten_lech_mot_chu_theo_mrz_khi_trang_in_ghi_dung():
    found = _find({"Nam_HoTen": "KIN ABCDE"}, _PASSPORT)
    assert [f.values for f in found] == [{"Nam_HoTen": "KIM ABCDE"}]


def test_chu_lech_khong_co_tren_trang_in_thi_giu_nguyen():
    text = _PASSPORT.replace("Surname: KIM\n", "")
    assert _find({"Nam_HoTen": "KIN ABCDE"}, text) == []


def test_khong_doi_thu_tu_chi_theo_mrz():
    assert _find({"Nam_HoTen": "ABCDE KIM"}, _PASSPORT) == []


def test_quoc_tich_nuoc_ngoai_thu_tu_ten_viet_theo_giay_tieng_viet():
    # Hộ chiếu nước ngoài: họ TRAN, "Given names" ghi tên trước đệm (AN VAN); giấy nước ngoài ghi AN VAN TRAN.
    text = ("PMUSATRAN<<AN<VAN<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\nFull name: AN VAN TRAN\n"
            "1. Họ và tên (viết chữ in hoa): TRẦN VĂN AN\n")
    found = _find({"Nam_HoTen": "AN VAN TRAN", "Nam_QuocTich": "Mỹ"}, text)
    assert [f.values for f in found] == [{"Nam_HoTen": "TRAN VAN AN"}]
    assert _find({"Nam_HoTen": "AN VAN TRAN", "Nam_QuocTich": "Việt Nam"}, text) == []


def test_ten_khac_han_hoac_da_dung_thi_khong_de_xuat():
    assert _find({"Nam_HoTen": "PARK XYZ"}, _PASSPORT) == []
    assert _find({"Nam_HoTen": "KIM, ABCDE"}, _PASSPORT) == []
    # Dòng MRZ đọc hỏng không đè được tên đã khớp một dòng MRZ khác.
    assert _find({"Nam_HoTen": "KIM ABCDE"}, _PASSPORT + "PMKORIM<<ABCDE<<<<<<<<<\n") == []


def test_khong_co_ten_tren_giay_to_thi_khong_them():
    assert _find({"ToKhaiNam_HoTen": "KIN ABCDE"}, _PASSPORT) == []


_TO_KHAI = (
    "TỜ KHAI ĐĂNG KÝ KẾT HÔN\n| Thông tin | Bên nữ | Bên nam |\n|---|---|---|\n"
    "| Họ, chữ đệm, tên | NGUYỄN THỊ A | KIM ABCDE |\n| Kết hôn lần thứ mấy | 2 | 1 |\n"
    "Chúng tôi cam đoan những lời khai trên đây là đúng sự thật\n"
)


def test_so_lan_ket_hon_theo_dung_cot_to_khai():
    case = Case([{"name": "to_khai.pdf", "text": _TO_KHAI}], "", {"Nu_SoLanKetHon": "", "Nam_SoLanKetHon": "1"}, {})
    nu, nam = SIDES[1], SIDES[0]
    assert tinh_trang._count_finding(nu, case).values == {"Nu_SoLanKetHon": "2"}
    assert tinh_trang._count_finding(nam, case) is None


def test_ket_hon_nuoc_ngoai_bat_dien_dot_hai_form_cu():
    assert second_pass.capability(get_procedure("ket-hon-nuoc-ngoai")) == "secondPassLegacy"


def test_runner_tra_luot_dot_hai_khi_extension_khai(monkeypatch):
    async def fake_run(files_by_role, **kwargs):
        builder = kwargs.get("context_builder")
        if builder:
            await builder([{"name": "to_khai.pdf", "text": _TO_KHAI}], {})
        return {"fields": [{"name": "Nam_HoTen", "value": "KIM ABCDE"}]}

    monkeypatch.setattr("app.pipelines.ket_hon_nuoc_ngoai.process.runner.runner.run", fake_run)
    assert callable(asyncio.run(run({"": []}, {"_secondPass": True})).get("_second_pass"))
    assert "_second_pass" not in asyncio.run(run({"": []}, {}))


_US_PASSPORT = (
    "PASSPORT\nPMUSATRAN<<VAN<AN<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n"
    "Họ và tên (viết chữ in hoa): TRAN VAN AN\nPrinted name: Tran VAN An\n"
)


def test_quoc_tich_nuoc_ngoai_ten_khong_dau_theo_ho_chieu():
    text = _US_PASSPORT + "| Họ, chữ đệm, tên | Trần Văn An | KIM ABCDE |\n"
    found = _find({"Nu_HoTen": "Trần Văn An", "Nu_QuocTich": "Mỹ"}, text)
    assert [f.values for f in found] == [{"Nu_HoTen": "TRAN VAN AN"}]


def test_ten_co_dau_giu_nguyen_khi_quoc_tich_viet_nam_hoac_giay_ghi_co_dau_nhieu_hon():
    assert _find({"Nu_HoTen": "Trần Văn An", "Nu_QuocTich": "Việt Nam"}, _US_PASSPORT) == []
    text = _US_PASSPORT + "Trần Văn An\nTrần Văn An\nTRẦN VĂN AN\n"
    assert _find({"Nu_HoTen": "Trần Văn An", "Nu_QuocTich": "Mỹ"}, text) == []
