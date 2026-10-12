"""Kết hôn có yếu tố nước ngoài: nhóm nhân thân Nam_*/Nu_* và tên quốc gia theo danh mục cổng."""
from app.pipelines.ket_hon_nuoc_ngoai.process import mapper
from app.pipelines.ket_hon_nuoc_ngoai.process.schema import ALLOWED

_NU_NUOC_NGOAI = {
    "Nu_HoTen": "TRAN THI A",
    "Nu_SoDinhDanh": "A00000001",
    "Nu_NgaySinh": "01/01/2000",
    "Nu_QuocTich": "Mỹ",
    "Nu_TenGiayTo": "Hộ chiếu",
    "Nu_NoiCuTru": {"quocGia": "Mỹ", "tinh": "", "xa": "", "diaChi": "1 Main St, TX"},
}


def _values(values: dict) -> dict:
    out = mapper.enrich([{"name": k, "value": v} for k, v in values.items()])
    return {f["name"]: f["value"] for f in out}


def test_ten_nhom_khong_mang_nghia_cccd():
    assert not [name for name in ALLOWED if name.startswith("Cccd")]
    assert {"Nam_HoTen", "Nu_HoTen", "ToKhaiNu_HoTen"} <= ALLOWED


def test_my_doi_thanh_hoa_ky_ca_quoc_tich_lan_noi_cu_tru():
    out = _values(_NU_NUOC_NGOAI)
    assert out["HoTenBenNu"] == "TRAN THI A"
    assert out["QuocTichBenNu"] == "Hoa Kỳ"
    assert out["NoiCuTru_BenNu"] == "2"
    assert out["NoiCuTru_BenNu_NuocNgoai"]["quocGia"] == "Hoa Kỳ"


def test_ten_nuoc_khong_co_trong_bang_giu_nguyen_khong_khop_mot_phan():
    out = _values({**_NU_NUOC_NGOAI, "Nu_QuocTich": "Ukraine",
                   "Nu_NoiCuTru": {"quocGia": "Ukraine", "diaChi": "Kyiv"}})
    assert out["QuocTichBenNu"] == "Ukraine"
    assert out["NoiCuTru_BenNu_NuocNgoai"]["quocGia"] == "Ukraine"
