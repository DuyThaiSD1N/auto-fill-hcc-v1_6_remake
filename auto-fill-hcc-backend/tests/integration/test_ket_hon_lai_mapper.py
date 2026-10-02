"""Map compact facts của đăng ký lại kết hôn → field UI (dữ liệu mẫu từ spec)."""

from app.pipelines.ket_hon_lai.process import mapper, schema
from app.pipelines.ket_hon_lai.process.prompt import EXTRA_RULES

_VO = {  # bên nữ
    "CccdNu_HoTen": "MÁ THỊ SỐ",
    "CccdNu_SoDinhDanh": "012189003303",
    "CccdNu_NgaySinh": "01/01/1989",
    "CccdNu_NgayCap": "16/03/2026",
    "CccdNu_NoiCap": "BỘ CÔNG AN / MINISTRY OF PUBLIC SECURITY",
    "CccdNu_DanToc": "H'Mông",
    "CccdNu_NoiCuTru_TrongNuoc": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Đoàn Kết",
                                  "diaChi": "Tổ dân phố Cư Nhà La"},
}
_CHONG = {  # bên nam
    "CccdNam_HoTen": "SÙNG A CỦ",
    "CccdNam_SoDinhDanh": "012086005221",
    "CccdNam_NgaySinh": "01/01/1986",
    "CccdNam_NgayCap": "06/01/2026",
    "CccdNam_NoiCap": "Bộ Công an",
    "CccdNam_DanToc": "H'Mông",
    "CccdNam_NoiCuTru_TrongNuoc": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Đoàn Kết",
                                   "diaChi": "Tổ dân phố Cư Nhà La"},
}
_HOSO = {
    "KetHonCu_So": "40/2026",
    "KetHonCu_QuyenSo": "01/2026",
    "KetHonCu_NgayDangKy": "01/04/2026",
    "KetHonCu_TinhDangKy": "Lai Châu",
    "KetHonCu_XaDangKy": "Phường Đoàn Kết",
}


def _fields(*dicts):
    merged = {}
    for d in dicts:
        merged.update(d)
    return [{"name": k, "value": v} for k, v in merged.items()]


def _by_name(out):
    return {f["name"]: f for f in out}


def test_map_full_case():
    out = _by_name(mapper.enrich(_fields(_VO, _CHONG, _HOSO)))

    # Bên nữ (vợ)
    assert out["HoTenBenNu"]["value"] == "MÁ THỊ SỐ"
    assert out["SoDinhDanh_BenNu"]["value"] == "012189003303"
    assert out["SoGiayToDinhDanh_BenNu"]["value"] == "012189003303"
    assert out["LoaiGiayToDinhDanh_BenNu"]["value"] == "Căn cước công dân"
    assert out["NgaySinhBenNu"]["value"] == "01/01/1989"
    assert out["NgayCapDD_BenNu"]["value"] == "16/03/2026"
    assert out["NoiCapDD_BenNu"]["value"] == "Bộ Công an"        # bỏ đuôi tiếng Anh
    assert out["DanTocBenNu"]["value"] == "Mông (Hmông)"          # H'Mông -> option đúng
    assert out["QuocTichBenNu"]["value"] == "Việt Nam"
    assert out["LoaiCuTru_BenNu"]["value"] == "Thường trú"
    assert out["NoiCuTru_BenNu"]["value"] == "1"
    assert out["NoiCuTru_BenNu_TrongNuoc"]["value"]["xa"] == "Phường Đoàn Kết"
    assert out["NoiCuTru_BenNu_TrongNuoc"]["value"]["diaChi"] == "Tổ dân phố Cư Nhà La"

    # Bên nam (chồng)
    assert out["HoTenBenNam"]["value"] == "SÙNG A CỦ"
    assert out["SoDinhDanh_BenNam"]["value"] == "012086005221"
    assert out["NoiCapDD_BenNam"]["value"] == "Bộ Công an"

    # Mặc định vàng: tình trạng hôn nhân + số lần kết hôn
    for side in ("BenNu", "BenNam"):
        assert out[f"SoLanKetHon_{side}"]["value"] == "1"
        assert out[f"SoLanKetHon_{side}"].get("default") is True
        assert out[f"SoLanKetHon_{side}"]["comp"] == "x-input-number"
        assert out[f"LoaiTinhTrangHonNhan_{side}"]["value"] == "Hiện tại đang có vợ/chồng"
        assert out[f"LoaiTinhTrangHonNhan_{side}"].get("default") is True

    # Hồ sơ gốc (đăng ký lại)
    assert out["loaiDangKy"]["value"] == "Đăng ký lại"
    assert out["loaiDangKy"].get("default") is True
    assert out["soDangKyTruocDay"]["value"] == "40/2026"
    assert out["quyenDangKyTruocDay"]["value"] == "01/2026"
    assert out["quyenDangKyTruocDay"].get("default") is None
    assert out["ngayDangKyTruocDay"]["value"] == "01/04/2026"
    assert out["noiDangKyTruocDay_filter"]["value"] == "Lai Châu"       # tỉnh (lọc)
    assert out["noiDangKyTruocDay"]["value"] == "Phường Đoàn Kết"        # xã/phường chuẩn

    # Đề nghị cấp bản sao mặc định Có + 1 bản (vàng)
    assert out["CapBanSao"]["value"] == "Có"
    assert out["CapBanSao"].get("default") is True
    assert out["SoLuong"]["value"] == "1"
    assert out["SoLuong"]["comp"] == "raw"
    assert out["SoLuong"].get("default") is True


def test_missing_wife_cccd_falls_back_to_marriage_cert():
    """Thiếu CCCD vợ → LLM đã lấy CccdNu_* từ giấy CN kết hôn; mapper vẫn map đủ bên nữ."""
    out = _by_name(mapper.enrich(_fields(_CHONG, _HOSO,
                                         {"CccdNu_HoTen": "MÁ THỊ SỐ", "CccdNu_NgaySinh": "01/01/1989"})))
    assert out["HoTenBenNu"]["value"] == "MÁ THỊ SỐ"
    assert out["NgaySinhBenNu"]["value"] == "01/01/1989"
    assert out["HoTenBenNam"]["value"] == "SÙNG A CỦ"


def test_old_marriage_metadata_does_not_infer_number_or_book_from_birth_certificate():
    """Số/ngày giấy khai sinh không được lọt sang dữ liệu kết hôn cũ; quyển số không được tự tính."""
    out = _by_name(mapper.enrich(_fields(
        _VO,
        _CHONG,
        {
            # Các key cũ mô phỏng dữ liệu từng bị lấy nhầm từ giấy khai sinh.
            "HoTich_So": "804/2012",
            "HoTich_NgayDangKy": "27/11/2012",
            "HoTich_TinhDangKy": "Lai Châu",
            "HoTich_XaDangKy": "Thị trấn Tam Đường",
            # Giấy chứng nhận kết hôn cũ ghi rõ ngày/nơi đăng ký trước đây.
            "KetHonCu_NgayDangKy": "11/09/1995",
            "KetHonCu_TinhDangKy": "Thái Bình",
            "KetHonCu_XaDangKy": "Xã Bình Long",
        },
    )))

    assert "soDangKyTruocDay" not in out
    assert "quyenDangKyTruocDay" not in out
    assert out["ngayDangKyTruocDay"]["value"] == "11/09/1995"
    assert out["noiDangKyTruocDay_filter"]["value"] == "Thái Bình"
    assert out["noiDangKyTruocDay"]["value"] == "Xã Bình Long"


def test_old_marriage_schema_uses_specific_fields_and_restricts_sources():
    expected = {
        "KetHonCu_So",
        "KetHonCu_QuyenSo",
        "KetHonCu_NgayDangKy",
        "KetHonCu_TinhDangKy",
        "KetHonCu_XaDangKy",
    }
    assert expected <= schema.ALLOWED
    assert not {"HoTich_So", "HoTich_NgayDangKy", "HoTich_TinhDangKy", "HoTich_XaDangKy"} & schema.ALLOWED
    assert "TỜ KHAI ĐĂNG KÝ LẠI KẾT HÔN" in EXTRA_RULES
    assert "GIẤY CHỨNG NHẬN KẾT HÔN cũ" in EXTRA_RULES
    assert "Ưu tiên theo TỪNG FIELD: giá trị ghi rõ trên GIẤY CHỨNG NHẬN KẾT HÔN cũ" in EXTRA_RULES
    assert "TUYỆT ĐỐI không lấy" in EXTRA_RULES
    assert "KHÔNG tự tính từ số" in EXTRA_RULES
