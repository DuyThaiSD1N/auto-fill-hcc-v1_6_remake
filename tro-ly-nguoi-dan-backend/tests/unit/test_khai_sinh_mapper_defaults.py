"""Regression tests for the interlinked birth-registration controls."""

from app.pipelines.khai_sinh_lien_thong.process.mapper import enrich


def _fields(**values):
    return [{"name": name, "value": value} for name, value in values.items()]


def _by_name(fields):
    return {field["name"]: field for field in fields}


def test_khong_co_ct01_mac_dinh_vneid_va_bo_cho_muc_dang_ky_thuong_tru():
    out = _by_name(enrich(_fields(
        Gcs_HoTenCon="Nguyễn Văn Bé",
        CccdNam_HoTen="Nguyễn Văn Bố",
        CccdNam_SoDinhDanh="012345678901",
    )))

    assert out["LoaiXacNhanVNeID"] == {
        "name": "LoaiXacNhanVNeID", "comp": "radio", "value": "2", "default": True,
    }
    assert out["DkttIsTtBo"]["value"] is True
    assert out["DkttIsTtMe"]["value"] is False
    assert out["LoaiThanNhanXacNhan"]["value"] == "1"
    assert out["LoaiChuSoHuuChoO"]["value"] == "1"
    for name in (
        "DkttIsTtBo", "DkttIsTtMe", "LoaiThanNhanXacNhan", "LoaiChuSoHuuChoO",
    ):
        assert out[name]["default"] is True


def test_ct01_khop_me_giu_nhan_dien_me_khong_fallback_sang_bo():
    out = _by_name(enrich(_fields(
        Gcs_HoTenCon="Nguyễn Văn Bé",
        CccdNam_HoTen="Nguyễn Văn Bố",
        CccdNam_SoDinhDanh="012345678901",
        CccdNu_HoTen="Trần Thị Mẹ",
        CccdNu_SoDinhDanh="098765432109",
        Ct01_ChuHoHoTen="Trần Thị Mẹ",
        Ct01_ChuHoSoDinhDanh="098765432109",
    )))

    assert out["LoaiXacNhanVNeID"]["value"] == "1"
    assert out["DkttIsTtMe"]["value"] is True
    assert "DkttIsTtBo" not in out
    assert out["LoaiThanNhanXacNhan"]["value"] == "2"
    assert out["LoaiChuSoHuuChoO"]["value"] == "2"


def test_ct01_chu_ho_nguoi_khac_khong_tu_dong_chon_bo():
    out = _by_name(enrich(_fields(
        Gcs_HoTenCon="Nguyễn Văn Bé",
        CccdNam_HoTen="Nguyễn Văn Bố",
        CccdNam_SoDinhDanh="012345678901",
        CccdNu_HoTen="Trần Thị Mẹ",
        CccdNu_SoDinhDanh="098765432109",
        Ct01_ChuHoHoTen="Lê Văn Chủ Hộ",
        Ct01_ChuHoSoDinhDanh="011111111111",
        Ct01_QuanHeVoiChuHo="Cháu nội",
    )))

    assert out["DkttChuHo"]["value"] == "Lê Văn Chủ Hộ"
    assert out["DkttChuhoSoGiayTo"]["value"] == "011111111111"
    assert out["DkttMaQuanHe"]["value"] == "Cháu nội"
    assert "LoaiThanNhanXacNhan" not in out
    assert "LoaiChuSoHuuChoO" not in out
