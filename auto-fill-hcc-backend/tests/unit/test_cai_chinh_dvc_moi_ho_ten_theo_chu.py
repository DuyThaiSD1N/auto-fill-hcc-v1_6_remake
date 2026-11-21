"""Thanh tra định danh cải chính: họ tên đếm nguồn theo CHỮ đang tranh chấp, không theo nguyên tên."""

from app.pipelines._shared.thanh_tra.ho_so import Case, Finding
from app.pipelines.cai_chinh_dvc_moi.thanh_tra import dinh_danh as dd

_UNIT = next(unit for unit in dd.UNITS if unit.key == "ho_ten")


def _sources(*names):
    out = {}
    for page_no, name in enumerate(names):
        finding = Finding(dd.INSPECTOR, _UNIT, {"NguoiThayDoi_HoTen": name}, "", 1)
        out.setdefault(dd._unit_key(_UNIT, finding.values), []).append((page_no, finding))
    return out


def test_trang_lech_dau_o_chu_khac_van_tinh_cho_chu_dang_tranh_chap():
    # Thẻ đọc lệch dấu ở chữ đệm ("BÀ") nhưng chữ đang tranh chấp ghi như A → nguồn của A.
    sources = _sources("NGUYỄN BÁ VINH", "NGUYỄN BÀ VINH", "Nguyễn Bá Vĩnh", "Nguyễn Bá Vĩnh")
    case = Case([], "", {}, {})
    assert dd._name_word_support(sources, _UNIT, case, "Nguyễn Bá Vinh", "Nguyễn Bá Vĩnh") == (2, 2)


def test_ten_khac_so_chu_thi_dem_nguyen_ten():
    case = Case([], "", {}, {})
    assert dd._name_word_support(_sources("Nguyễn Văn An"), _UNIT, case, "Nguyễn An", "Nguyễn Văn An") is None
