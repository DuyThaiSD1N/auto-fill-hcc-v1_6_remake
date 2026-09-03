"""Unit test mapper "Giao đất, cho thuê đất, chuyển mục đích SDĐ..." (Đà Nẵng).

Kiểm: HAI vai (tự nộp / ủy quyền / thiếu chủ hồ sơ), panel THỬA ĐẤT (Số thửa/Số tờ/địa chỉ thửa), nội
dung yêu cầu đa dòng + fallback, không lẫn địa chỉ người ↔ thửa đất."""

from app.pipelines.giao_thue_chuyen_muc_dich_dat_da_nang.process.mapper import enrich


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _map(vals: dict) -> dict:
    fields, _ = enrich(_flds(vals), {})
    return {f["name"]: f["value"] for f in fields}


_PARCEL = {
    "ThuaDat_SoThua": "thửa đất số 308",
    "ThuaDat_SoTo": "tờ bản đồ số 103",
    "ThuaDat_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu", "diaChi": "50A Nguyễn Chí Thanh"},
}


def test_tu_nop_tick_va_dien_1_vai():
    vals = {
        "ChuHoSo_LoaiChuThe": "Cá nhân",
        "ChuHoSo_HoTen": "LÊ THỊ THÚY KIỀU",
        "NguoiNop_HoTen": "LÊ THỊ THÚY KIỀU",
        "NguoiNop_SoDinhDanh": "048149001928",
        "NguoiNop_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu", "diaChi": "88 Quang Trung"},
        **_PARCEL,
    }
    out = _map(vals)
    assert out["data[ownerFullname]"] == "LÊ THỊ THÚY KIỀU"
    assert out["data[isOwnerDossier]"] is True
    assert out["data[fullname]"] == "LÊ THỊ THÚY KIỀU"
    assert out["data[chonDoiTuong]"] == "Cá nhân"
    # địa chỉ NGƯỜI (không phải thửa đất)
    assert out["data[province]"] == "Thành phố Đà Nẵng"
    assert out["data[district]"] == "Phường Hải Châu"
    assert out["data[address]"] == "88 Quang Trung"


def test_uy_quyen_bo_tich_dien_2_vai_khong_lan():
    vals = {
        "ChuHoSo_HoTen": "LÊ THỊ THÚY KIỀU",
        "NguoiNop_HoTen": "VÕ HOÀI SƠN",
        "NguoiNop_NgaySinh": "12/11/1984",
        "NguoiNop_GioiTinh": "Nam",
        "NguoiNop_SoDinhDanh": "048084007873",
        "NguoiNop_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu", "diaChi": "12 Lê Lợi"},
        **_PARCEL,
    }
    out = _map(vals)
    assert out["data[ownerFullname]"] == "LÊ THỊ THÚY KIỀU"
    assert out["data[isOwnerDossier]"] is False
    assert out["data[fullname]"] == "VÕ HOÀI SƠN"
    assert out["data[identityNumber]"] == "048084007873"
    assert out["data[gender]"] == "Nam"


def test_panel_thua_dat():
    out = _map({"ChuHoSo_HoTen": "NGUYỄN VĂN A", "NguoiNop_HoTen": "NGUYỄN VĂN A", **_PARCEL})
    # Số thửa/Số tờ đã bỏ chữ dẫn.
    assert out["data[SoThuaDat]"] == "308"
    assert out["data[SoToBanDo]"] == "103"
    assert out["data[province2]"] == "Thành phố Đà Nẵng"
    assert out["data[district2]"] == "Phường Hải Châu"
    assert out["data[diaChiThuaDat]"] == "50A Nguyễn Chí Thanh"
    assert out["data[nation2]"] == "Việt Nam"


def test_thua_dat_chi_phuong_tinh_van_dien():
    # Thửa đất chỉ ghi tới cấp phường + tỉnh (không số nhà) → KHÔNG bị drop như địa chỉ người.
    out = _map({
        "ChuHoSo_HoTen": "NGUYỄN VĂN A", "NguoiNop_HoTen": "NGUYỄN VĂN A",
        "ThuaDat_DiaChi": {"tinh": "Tỉnh Bắc Ninh", "xa": "Phường Song Liễu", "diaChi": ""},
    })
    assert out["data[province2]"] == "Tỉnh Bắc Ninh"
    assert out["data[district2]"] == "Phường Song Liễu"
    assert "data[diaChiThuaDat]" not in out  # không có chi tiết → bỏ trống, không bịa


def test_noi_dung_yeu_cau_da_dong():
    noi_dung = "Chuyển 41,3 m² đất trồng cây lâu năm (CLN) sang đất ở\n- Thửa số 308, tờ bản đồ 103"
    out = _map({"ChuHoSo_HoTen": "LÊ THỊ THÚY KIỀU", "NguoiNop_HoTen": "LÊ THỊ THÚY KIỀU",
                "NoiDungYeuCau": noi_dung})
    assert out["data[noidungyeucaugiaiquyet]"] == noi_dung  # giữ nguyên xuống dòng


def test_noi_dung_trong_thi_fallback_cau_khung():
    out = _map({"ChuHoSo_HoTen": "LÊ THỊ THÚY KIỀU", "NguoiNop_HoTen": "LÊ THỊ THÚY KIỀU"})
    assert out["data[noidungyeucaugiaiquyet]"].startswith("LÊ THỊ THÚY KIỀU ĐỀ NGHỊ GIẢI QUYẾT")


def test_tu_nop_dia_chi_lay_tu_chu_ho_so_khi_nguoi_nop_thieu():
    out = _map({
        "ChuHoSo_HoTen": "NGUYỄN VĂN A", "NguoiNop_HoTen": "NGUYỄN VĂN A",
        "ChuHoSo_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hòa Cường", "diaChi": "5 Núi Thành"},
    })
    assert out["data[province]"] == "Thành phố Đà Nẵng"
    assert out["data[district]"] == "Phường Hòa Cường"
    assert out["data[address]"] == "5 Núi Thành"


def test_chu_ho_so_to_chuc():
    out = _map({
        "ChuHoSo_LoaiChuThe": "Tổ chức",
        "ChuHoSo_HoTen": "Công ty TNHH ABC",
        "NguoiNop_HoTen": "TRẦN VĂN B",
        "NguoiNop_SoDinhDanh": "049084001234",
        "NguoiNop_MaSoThue": "0401234567",
    })
    assert out["data[ownerFullname]"] == "Công ty TNHH ABC"
    assert out["data[organization]"] == "Công ty TNHH ABC"
    # ủy quyền (người nộp cá nhân khác chủ tổ chức)
    assert out["data[isOwnerDossier]"] is False
    assert out["data[chonDoiTuong]"] == "Cá nhân"


def test_thieu_chu_ho_so_van_giu_nguoi_nop():
    fields, warnings = enrich(_flds({"NguoiNop_HoTen": "VÕ HOÀI SƠN", "NguoiNop_SoDinhDanh": "048084007873"}), {})
    names = {f["name"] for f in fields}
    assert "data[fullname]" in names
    assert any("chủ hồ sơ" in w.lower() for w in warnings)
