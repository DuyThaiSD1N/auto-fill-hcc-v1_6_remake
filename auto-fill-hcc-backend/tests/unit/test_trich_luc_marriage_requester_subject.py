"""Trích lục kết hôn: người đăng nhập VNeID có tên trên giấy thì chính họ là người được đăng ký.

Giấy kết hôn có HAI chủ thể. Agent mặc định lấy bên nam, nên khi người vợ tự đăng nhập xin trích lục
của chính cuộc hôn nhân mình, mục II ra tên chồng và ô "(5) Quan hệ" bị tick "Vợ" thay vì "Bản thân".
"""

from app.pipelines.trich_luc.process.mapper import enrich

_VO = "NGUYỄN THỊ OANH"
_VO_ID = "022170000913"
_CHONG = "PHÙNG VĂN TRƯỜNG"
_CHONG_ID = "031073003230"

_CTX = {"formContext": {"applicantFullname": _VO, "applicantIdentityNumber": _VO_ID}}


def _by_name(fields: list[dict]) -> dict[str, dict]:
    return {field["name"]: field for field in fields}


def _giay_ket_hon(subject: str = "chong") -> list[dict]:
    """Kết quả agent trả về: mặc định lấy CHỒNG làm người được đăng ký, vợ nằm ở người thân."""
    chu_the = {
        "chong": {
            "ten": _CHONG, "id": _CHONG_ID, "ngaySinh": "1973", "gioiTinh": "Nam",
            "cuTru": {"quocGia": "Việt Nam", "tinh": "Hải Phòng", "xa": "Thái Sơn", "diaChi": ""},
            "than": {"quanHe": "vợ", "hoTen": _VO, "soGiayTo": _VO_ID},
        },
        "vo": {
            "ten": _VO, "id": _VO_ID, "ngaySinh": "1970", "gioiTinh": "Nữ",
            "cuTru": {"quocGia": "Việt Nam", "tinh": "Quảng Ninh", "xa": "Cô Tô", "diaChi": ""},
            "than": {"quanHe": "chồng", "hoTen": _CHONG, "soGiayTo": _CHONG_ID},
        },
    }[subject]
    return [
        {"name": "HoTich_LoaiSuKien", "value": "marriage"},
        {"name": "HoTich_TenGiayTo", "value": "Giấy chứng nhận kết hôn"},
        {"name": "HoTich_HoTenNguoiDuocDangKy", "value": chu_the["ten"]},
        {"name": "HoTich_NgaySinh", "value": chu_the["ngaySinh"]},
        {"name": "HoTich_GioiTinh", "value": chu_the["gioiTinh"]},
        {"name": "HoTich_DanToc", "value": "Kinh"},
        {"name": "HoTich_QuocTich", "value": "Việt Nam"},
        {"name": "HoTich_SoDinhDanh", "value": chu_the["id"]},
        {"name": "HoTich_SoGiayToTuyThan", "value": chu_the["id"]},
        {"name": "HoTich_NgayCapGiayToTuyThan", "value": "24/04/2021"},
        {"name": "HoTich_NoiCuTru", "value": chu_the["cuTru"]},
        {"name": "HoTich_NguoiThan", "value": [chu_the["than"]]},
        {"name": "HoTich_So", "value": "87/1999"},
        {"name": "HoTich_NgayDangKy", "value": "21/04/1999"},
    ]


def _nguoi_yeu_cau_la_vo() -> list[dict]:
    return [
        {"name": "Nyc_HoTen", "value": _VO},
        {"name": "Nyc_SoDinhDanh", "value": _VO_ID},
        {"name": "Nyc_NgaySinh", "value": "1970"},
        {"name": "Nyc_GioiTinh", "value": "Nữ"},
        {"name": "Nyc_NgayCap", "value": "24/04/2021"},
        {"name": "Nyc_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
        {"name": "Nyc_NoiCuTru", "value": {"quocGia": "Việt Nam", "tinh": "Quảng Ninh", "xa": "Cô Tô", "diaChi": ""}},
    ]


def test_nguoi_dang_nhap_la_vo_thi_thanh_nguoi_duoc_dang_ky():
    result = _by_name(enrich(_giay_ket_hon("chong") + _nguoi_yeu_cau_la_vo(), _CTX))

    assert result["NDK_HoVaTen"]["value"] == _VO
    assert result["NDK_SoDinhDanh"]["value"] == _VO_ID
    assert result["NDK_NgaySinh"]["value"] == "1970"
    assert result["NDK_GioiTinh"]["value"] == "Nữ"
    assert result["NYC_QuanHe"]["value"] == "Bản thân"


def test_khong_giu_lai_nhan_than_cua_nguoi_kia_khi_doi_vai():
    result = _by_name(enrich(_giay_ket_hon("chong") + _nguoi_yeu_cau_la_vo(), _CTX))

    # Dân tộc chỉ đọc được của người chồng → phải bỏ, không đội sang cho vợ.
    assert "NDK_DanToc" not in result
    assert result["NDK_NoiCuTru_TrongNuoc"]["value"]["tinh"] == "Quảng Ninh"


def test_agent_da_chon_dung_nguoi_thi_giu_nguyen():
    """Agent theo prompt mới đã lấy chính người đăng nhập → không đảo lần nữa."""
    result = _by_name(enrich(_giay_ket_hon("vo") + _nguoi_yeu_cau_la_vo(), _CTX))

    assert result["NDK_HoVaTen"]["value"] == _VO
    assert result["NDK_DanToc"]["value"] == "Kinh"  # dữ liệu agent đọc được vẫn còn nguyên
    assert result["NYC_QuanHe"]["value"] == "Bản thân"


def test_nguoi_dang_nhap_khong_co_ten_tren_giay_thi_giu_ben_nam():
    ctx = {"formContext": {"applicantFullname": "LÊ VĂN BA", "applicantIdentityNumber": "001199000111"}}
    fields = _giay_ket_hon("chong") + [
        {"name": "Nyc_HoTen", "value": "LÊ VĂN BA"},
        {"name": "Nyc_SoDinhDanh", "value": "001199000111"},
    ]

    result = _by_name(enrich(fields, ctx))

    # Con/cháu đi xin hộ: mục II vẫn là bên nam như mặc định, quan hệ không thể là "Bản thân".
    assert result["NDK_HoVaTen"]["value"] == _CHONG
    assert result["NYC_QuanHe"]["value"] != "Bản thân"


def test_to_khai_neu_ten_nguoi_duoc_cap_thi_theo_to_khai():
    """Tờ khai là lời khai chính chủ: nêu tên ai thì mục II là người đó, không đảo theo tài khoản."""
    fields = _giay_ket_hon("chong") + _nguoi_yeu_cau_la_vo() + [
        {"name": "TkNyc_HoTen", "value": _VO},
        {"name": "ToKhai_LoaiSuKien", "value": "marriage"},
        {"name": "ToKhai_TenGiayTo", "value": "Giấy chứng nhận kết hôn"},
        {"name": "ToKhai_HoTenNguoiDuocCap", "value": _CHONG},
    ]

    result = _by_name(enrich(fields, _CTX))

    assert result["NDK_HoVaTen"]["value"] == _CHONG
