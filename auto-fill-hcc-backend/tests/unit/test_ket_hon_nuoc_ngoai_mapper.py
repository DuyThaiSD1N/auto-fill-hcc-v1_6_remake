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


def test_ket_hon_lan_dau_khong_nhan_ly_hon_cua_ben_kia():
    # Tờ khai ghi bên nam kết hôn lần thứ nhất nhưng LLM chép quyết định ly hôn của bên nữ sang.
    ly_hon = {"BanAnLyHon_So": "01/2024/QĐCNTTLH", "BanAnLyHon_Ngay": "01/02/2024",
              "BanAnLyHon_CoQuan": "Tòa án nhân dân thành phố X"}
    out = _values({
        "Nam_HoTen": "NGUYEN VAN B", "Nam_SoDinhDanh": "A00000002", "Nam_QuocTich": "Hoa Kỳ",
        "Nam_SoLanKetHon": 1, "Nam_TinhTrangHonNhan": "ly_hon",
        **{f"Nam_{k}": v for k, v in ly_hon.items()},
        **_NU_NUOC_NGOAI, "Nu_SoLanKetHon": 2, "Nu_TinhTrangHonNhan": "ly_hon",
        **{f"Nu_{k}": v for k, v in ly_hon.items()},
    })
    assert out["SoLanKetHon_BenNam"] == "1"
    assert out["LoaiTinhTrangHonNhan_BenNam"] == mapper._MARITAL_STATUS["chua_ket_hon"]
    assert "TTHN_LyHonBenNam" not in out
    assert out["LoaiTinhTrangHonNhan_BenNu"] == mapper._MARITAL_STATUS["ly_hon"]
    assert out["TTHN_LyHonBenNu"]["soBanAnQuyetDinhLyHon"] == "01/2024/QĐCNTTLH"


def test_ten_nhom_khong_mang_nghia_cccd():
    assert not [name for name in ALLOWED if name.startswith("Cccd")]
    assert {"Nam_HoTen", "Nu_HoTen", "ToKhaiNu_HoTen"} <= ALLOWED


def test_my_doi_thanh_hoa_ky_ca_quoc_tich_lan_noi_cu_tru():
    out = _values(_NU_NUOC_NGOAI)
    assert out["HoTenBenNu"] == "TRAN THI A"
    assert out["QuocTichBenNu"] == "Hoa Kỳ"
    assert out["NoiCuTru_BenNu"] == "2"
    assert out["NoiCuTru_BenNu_NuocNgoai"]["quocGia"] == "Hoa Kỳ"


def test_ho_chieu_nuoc_ngoai_chon_option_ho_chieu_khong_mo_o_ten_giay_to():
    out = _values(_NU_NUOC_NGOAI)
    assert out["LoaiGiayToDinhDanh_BenNu"] == "Hộ chiếu"
    assert "TenGiayTo_BenNu" not in out


def test_thieu_ten_giay_to_thi_nhan_ho_chieu_theo_dong_giay_to_tren_to_khai():
    values = {k: v for k, v in _NU_NUOC_NGOAI.items() if k != "Nu_TenGiayTo"}
    out = _values({**values, "ToKhaiNu_SoGiayTo": "Hộ chiếu số: A00000001 do Hoa Kỳ cấp"})
    assert out["LoaiGiayToDinhDanh_BenNu"] == "Hộ chiếu"


def test_giay_to_nuoc_ngoai_khac_van_chon_giay_to_khac_kem_ten():
    out = _values({**_NU_NUOC_NGOAI, "Nu_TenGiayTo": "Chứng minh thư"})
    assert out["LoaiGiayToDinhDanh_BenNu"] == mapper.FOREIGN_DOC_TYPE
    assert out["TenGiayTo_BenNu"] == "Chứng minh thư"


def test_nguoi_nuoc_ngoai_dan_toc_chon_khac_va_ghi_nguyen_van_theo_to_khai():
    # Agent bỏ trống Nu_DanToc, chỉ còn cột tờ khai ghi "Hoa" (trùng tên dân tộc VN).
    out = _values({**_NU_NUOC_NGOAI, "ToKhaiNu_DanToc": "Hoa"})
    assert out["DanTocBenNu"] == mapper.DAN_TOC_KHAC
    assert out["NhapDanTocBenNuKhac"] == "Hoa"
    names = list(out)
    assert names.index("NhapDanTocBenNuKhac") == names.index("DanTocBenNu") + 1


def test_ten_nuoc_khong_co_trong_bang_giu_nguyen_khong_khop_mot_phan():
    out = _values({**_NU_NUOC_NGOAI, "Nu_QuocTich": "Ukraine",
                   "Nu_NoiCuTru": {"quocGia": "Ukraine", "diaChi": "Kyiv"}})
    assert out["QuocTichBenNu"] == "Ukraine"
    assert out["NoiCuTru_BenNu_NuocNgoai"]["quocGia"] == "Ukraine"
