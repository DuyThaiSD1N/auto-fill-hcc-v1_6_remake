"""Unit test mapper "Đăng ký đất đai, cấp GCN QSDĐ lần đầu" (Đà Nẵng).

Kiểm: HAI vai (tự nộp / đại diện-ủy quyền / thiếu chủ hồ sơ), panel THỬA ĐẤT (Số thửa/Số tờ/địa chỉ),
nội dung yêu cầu từ Đơn M15 + fallback, không lẫn địa chỉ người ↔ thửa đất."""

from app.pipelines.dang_ky_dat_dai_lan_dau_da_nang.process.mapper import enrich


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _map(vals: dict) -> dict:
    fields, _ = enrich(_flds(vals), {})
    return {f["name"]: f["value"] for f in fields}


_PARCEL = {
    "ThuaDat_SoThua": "thửa đất số 54",
    "ThuaDat_SoTo": "tờ bản đồ số 11",
    "ThuaDat_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Phước Ninh", "diaChi": "K21 Trần Bình Trọng"},
}


def test_tu_nop_tick_va_dien():
    out = _map({
        "ChuHoSo_HoTen": "NGUYỄN THỊ THANH QUYỀN",
        "NguoiNop_HoTen": "NGUYỄN THỊ THANH QUYỀN",
        "NguoiNop_SoDinhDanh": "048187001234",
        "NguoiNop_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Phước Ninh", "diaChi": "K21 Trần Bình Trọng"},
        **_PARCEL,
    })
    assert out["data[ownerFullname]"] == "NGUYỄN THỊ THANH QUYỀN"
    assert out["data[isOwnerDossier]"] is True
    assert out["data[fullname]"] == "NGUYỄN THỊ THANH QUYỀN"
    assert out["data[chonDoiTuong]"] == "Cá nhân"


def test_dai_dien_bo_tich_dien_2_vai():
    # Người được cử đại diện (VB thỏa thuận) đứng tên GCN = chủ hồ sơ; người nộp khác → ủy quyền/đại diện.
    out = _map({
        "ChuHoSo_HoTen": "NGUYỄN THỊ THANH QUYỀN",
        "NguoiNop_HoTen": "TRẦN VĂN ĐẠI DIỆN",
        "NguoiNop_SoDinhDanh": "048084009999",
        "NguoiNop_GioiTinh": "Nam",
        "NguoiNop_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu", "diaChi": "5 Lê Lợi"},
        **_PARCEL,
    })
    assert out["data[isOwnerDossier]"] is False
    assert out["data[ownerFullname]"] == "NGUYỄN THỊ THANH QUYỀN"
    assert out["data[fullname]"] == "TRẦN VĂN ĐẠI DIỆN"
    assert out["data[identityNumber]"] == "048084009999"


def test_panel_thua_dat():
    out = _map({"ChuHoSo_HoTen": "A", "NguoiNop_HoTen": "A", **_PARCEL})
    assert out["data[SoThuaDat]"] == "54"
    assert out["data[SoToBanDo]"] == "11"
    assert out["data[province2]"] == "Thành phố Đà Nẵng"
    # remap_area: "Phường Phước Ninh" (cũ) → "Phường Hải Châu" (hiện hành, khớp SELECT trên form).
    assert out["data[district2]"] == "Phường Hải Châu"
    assert out["data[diaChiThuaDat]"] == "K21 Trần Bình Trọng"
    assert out["data[nation2]"] == "Việt Nam"


def test_thua_dat_chi_phuong_tinh_van_dien():
    out = _map({
        "ChuHoSo_HoTen": "A", "NguoiNop_HoTen": "A",
        "ThuaDat_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Phước Ninh", "diaChi": ""},
    })
    assert out["data[province2]"] == "Thành phố Đà Nẵng"
    assert out["data[district2]"] == "Phường Hải Châu"  # remap tên phường cũ → hiện hành
    assert "data[diaChiThuaDat]" not in out


def test_remap_ten_phuong_cu_ve_hien_hanh():
    # Địa chỉ NGƯỜI đọc từ CCCD/giấy tờ cũ với tên phường trước sáp nhập → chuẩn hóa để khớp SELECT.
    out = _map({
        "ChuHoSo_HoTen": "A", "NguoiNop_HoTen": "A",
        "NguoiNop_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Thạch Thang", "diaChi": "88 Quang Trung"},
        "ThuaDat_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phước Mỹ", "diaChi": "5 An Hải"},
    })
    assert out["data[district]"] == "Phường Hải Châu"     # Thạch Thang (cũ) → Hải Châu
    assert out["data[district2]"] == "Phường An Hải"      # Phước Mỹ (cũ) → An Hải


def test_noi_dung_da_dong():
    nd = "Đề nghị cấp GCN lần đầu cho thửa 54, tờ 11, diện tích 64,7 m², đất ở đô thị\n- Tài sản: nhà ở"
    out = _map({"ChuHoSo_HoTen": "A", "NguoiNop_HoTen": "A", "NoiDungYeuCau": nd})
    assert out["data[noidungyeucaugiaiquyet]"] == nd


def test_noi_dung_trong_fallback():
    out = _map({"ChuHoSo_HoTen": "NGUYỄN THỊ THANH QUYỀN", "NguoiNop_HoTen": "NGUYỄN THỊ THANH QUYỀN"})
    assert out["data[noidungyeucaugiaiquyet]"].startswith("NGUYỄN THỊ THANH QUYỀN ĐỀ NGHỊ GIẢI QUYẾT")


def test_tu_nop_dia_chi_tu_chu_ho_so():
    out = _map({
        "ChuHoSo_HoTen": "A", "NguoiNop_HoTen": "A",
        "ChuHoSo_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Phước Ninh", "diaChi": "K21 Trần Bình Trọng"},
    })
    assert out["data[province]"] == "Thành phố Đà Nẵng"
    assert out["data[district]"] == "Phường Hải Châu"  # remap "Phường Phước Ninh" (cũ) → hiện hành
    assert out["data[address]"] == "K21 Trần Bình Trọng"


def test_tu_nop_dia_chi_uu_tien_giay_to_ho_so_bo_cccd_lech():
    # Tự nộp: ChuHoSo_DiaChi lấy từ đơn/tờ khai (đầy đủ, đúng), NguoiNop_DiaChi vô tình lấy từ CCCD đọc lệch
    # ("Phường Ninh"/số nhà khác) → mapper phải ƯU TIÊN địa chỉ chủ hồ sơ (giấy tờ hồ sơ), KHÔNG dùng CCCD.
    out = _map({
        "ChuHoSo_HoTen": "NGUYỄN THỊ THANH QUYỀN", "NguoiNop_HoTen": "NGUYỄN THỊ THANH QUYỀN",
        "ChuHoSo_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu", "diaChi": "K21/26 Lê Hồng Phong, Tổ 42"},
        "NguoiNop_DiaChi": {"tinh": "Đà Nẵng", "xa": "Phường Ninh", "diaChi": "KP2/5C Lê Hồng Phong, Tổ 14"},
    })
    assert out["data[district]"] == "Phường Hải Châu"
    assert out["data[address]"] == "K21/26 Lê Hồng Phong, Tổ 42"


def test_thieu_chu_ho_so_van_giu_nguoi_nop():
    fields, warnings = enrich(_flds({"NguoiNop_HoTen": "TRẦN VĂN B", "NguoiNop_SoDinhDanh": "048084001111"}), {})
    names = {f["name"] for f in fields}
    assert "data[fullname]" in names
    assert any("chủ hồ sơ" in w.lower() for w in warnings)
