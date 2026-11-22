"""Khai sinh kết hợp nhận cha, mẹ, con: thanh tra định danh + địa chỉ và bản vá điền đợt 2 theo biến thể form."""
from app.pipelines._shared.thanh_tra.ho_so import Case, Result
from app.pipelines.khai_sinh_ket_hop_nhan_cmc.process import mapper
from app.pipelines.khai_sinh_ket_hop_nhan_cmc.thanh_tra import dia_chi, dinh_danh, dot_hai, trang
from app.procedures.registry import get_procedure

_SO_ME = "001195000001"
_GCS = """GIẤY CHỨNG SINH
Họ, chữ đệm, tên khai sinh của mẹ: LÊ THỊ THỦY AN
Số ĐDCN/ Hộ chiếu: 001195000001
"""
_CCCD_ME = f"""CĂN CƯỚC CÔNG DÂN
Citizen Identity Card
Số / No.: {_SO_ME}
Họ và tên / Full name:
LÊ THỊ THỦY AN
Nơi thường trú / Place of residence: 12 Lê Văn
Lợi, Phường Một, Thành phố Hai
"""
_TO_KHAI = """TỜ KHAI ĐĂNG KÝ NHẬN CHA, MẸ, CON
Họ, chữ đệm, tên người yêu cầu: Lê Thị Thùy An
Nơi cư trú: 12 Lê Văn Lới - Phường Ba
"""


def _docs():
    return [{"name": "gcs.pdf", "text": _GCS}, {"name": "cccd.pdf", "text": _CCCD_ME},
            {"name": "to_khai.pdf", "text": _TO_KHAI}]


def test_ho_ten_me_lech_dau_theo_so_trang_giay_in():
    values = {"Mother_FullName": "Lê Thị Thùy An", "Mother_IdNumber": _SO_ME}
    found = {f.unit.key: f for f in dinh_danh.findings_from(Case(_docs(), "", values, {}))}
    assert found["me.ho_ten"].values == {"Mother_FullName": "LÊ THỊ THỦY AN"}


def test_nguoi_yeu_cau_trung_so_me_thi_bao_toa_cung_mot_nguoi():
    values = {"Mother_FullName": "Lê Thị Thùy An", "Mother_IdNumber": _SO_ME,
              "Requester_FullName": "Lê Thị Thùy An", "Requester_IdNumber": _SO_ME}
    found = {f.unit.key: f for f in dinh_danh.findings_from(Case(_docs(), "", values, {}))}
    assert found["nyc.ho_ten"].values == {"Requester_FullName": "LÊ THỊ THỦY AN"}
    assert any("cùng số định danh với mẹ của trẻ" in line for line in found["nyc.ho_ten"].evidence)


def test_ho_ten_da_dung_khong_co_phat_hien():
    values = {"Mother_FullName": "Lê Thị Thủy An", "Mother_IdNumber": _SO_ME}
    assert not dinh_danh.findings_from(Case(_docs(), "", values, {}))


def test_ten_duong_theo_cccd_cua_chinh_nguoi_do():
    pages = trang.pages(_docs())
    assert dia_chi.street_fix("12 Lê Văn Lới", _SO_ME, pages)["diaChi"] == "12 Lê Văn Lợi"
    assert dia_chi.street_fix("12 Lê Văn Lới", "001195000009", pages) is None
    assert dia_chi.street_fix("15 Lê Văn Lới", _SO_ME, pages) is None
    assert dia_chi.street_fix("Thôn Lê Văn Lới", _SO_ME, pages) is None


async def _patch(monkeypatch, variant):
    raw = [{"name": "Mother_FullName", "value": "Lê Thị Thùy An"}, {"name": "Mother_IdNumber", "value": _SO_ME},
           {"name": "Requester_FullName", "value": "Lê Thị Thùy An"}, {"name": "Requester_IdNumber", "value": _SO_ME}]

    async def review(documents, values, options):
        return Result({**values, "Mother_FullName": "LÊ THỊ THỦY AN", "Requester_FullName": "LÊ THỊ THỦY AN"}, [], {})

    monkeypatch.setattr(dot_hai, "review", review)
    base = mapper.enrich([dict(f) for f in raw], variant, {})
    return {f["name"]: f for f in (await dot_hai.patch(_docs(), raw, base, {}, variant))["fields"]}


async def test_dot_hai_form_khai_sinh_va_ho_ten_me(monkeypatch):
    out = await _patch(monkeypatch, mapper.BIRTH_VARIANT)
    assert out["HoTenMeKS"]["value"] == "LÊ THỊ THỦY AN" and out["HoTenMeKS"]["by"] == "dinh_danh"


async def test_dot_hai_form_nhan_cha_me_con_va_ho_ten_nguoi_yeu_cau(monkeypatch):
    out = await _patch(monkeypatch, mapper.RECOGNITION_VARIANT)
    assert out["HoVaTenC"]["value"] == "LÊ THỊ THỦY AN" and out["HoVaTenC"]["by"] == "dinh_danh"


def test_registry_bat_dien_dot_hai_form_cu():
    assert get_procedure("khai-sinh-ket-hop-nhan-cha-me-con")["secondPass"] == "legacy"
