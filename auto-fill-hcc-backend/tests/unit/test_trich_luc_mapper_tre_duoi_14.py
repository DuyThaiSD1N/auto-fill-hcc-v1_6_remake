"""Trẻ dưới 14 tuổi: chỉ điền SỐ ĐỊNH DANH, không điền mục giấy tờ tùy thân."""

from datetime import date

from app.pipelines.trich_luc.process import mapper

_ID_DOC_FIELDS = (
    "NDK_LoaiGiayToTuyThan",
    "NDK_SoGiayToTuyThan",
    "NDK_NgayCap",
    "NDK_NoiCap",
)


def _birth_date(years_ago: int) -> str:
    today = date.today()
    # Lùi thêm 1 ngày để không phụ thuộc ngày sinh nhật rơi đúng hôm chạy test.
    born = date(today.year - years_ago, 1, 1)
    return born.strftime("%d/%m/%Y")


def _enrich(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in mapper.enrich(fields)}


def _birth_extract(age: int) -> list[dict]:
    return [
        {"name": "HoTich_LoaiSuKien", "value": "birth"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": "NGUYỄN VĂN BÉ"},
        {"name": "HoTich_NgaySinh", "value": _birth_date(age)},
        {"name": "HoTich_SoDinhDanh", "value": "012345678905"},
    ]


def test_tre_duoi_14_chi_dien_so_dinh_danh():
    result = _enrich(_birth_extract(age=5))

    assert result["NDK_SoDinhDanh"] == "012345678905"
    for name in _ID_DOC_FIELDS:
        assert name not in result


def test_tre_duoi_14_co_the_can_cuoc_nop_kem_thi_van_dien_giay_to():
    # Luật Căn cước 2023 cho phép cấp thẻ cho trẻ dưới 14 tuổi; đã nộp thẻ thì điền như thường.
    result = _enrich(_birth_extract(age=5) + [
        {"name": "ChuThe_HoTen", "value": "NGUYỄN VĂN BÉ"},
        {"name": "ChuThe_SoDinhDanh", "value": "012345678905"},
        {"name": "ChuThe_NgayCap", "value": "20/11/2024"},
        {"name": "ChuThe_NoiCap", "value": "Bộ Công an"},
    ])

    assert result["NDK_SoDinhDanh"] == "012345678905"
    assert result["NDK_SoGiayToTuyThan"] == "012345678905"
    assert result["NDK_NgayCap"] == "20/11/2024"
    assert result["NDK_LoaiGiayToTuyThan"]


def test_nguoi_du_14_tuoi_van_dien_giay_to_nhu_cu():
    result = _enrich(_birth_extract(age=20))

    assert result["NDK_SoDinhDanh"] == "012345678905"
    assert result["NDK_SoGiayToTuyThan"] == "012345678905"


def test_khong_doc_duoc_ngay_sinh_thi_giu_hanh_vi_cu():
    fields = [f for f in _birth_extract(age=5) if f["name"] != "HoTich_NgaySinh"]

    result = _enrich(fields)

    assert result["NDK_SoGiayToTuyThan"] == "012345678905"


def test_chi_co_nam_sinh_van_suy_duoc_tuoi():
    fields = [f for f in _birth_extract(age=5) if f["name"] != "HoTich_NgaySinh"]
    fields.append({"name": "HoTich_NgaySinh", "value": str(date.today().year - 5)})

    result = _enrich(fields)

    assert result["NDK_SoDinhDanh"] == "012345678905"
    assert "NDK_SoGiayToTuyThan" not in result
