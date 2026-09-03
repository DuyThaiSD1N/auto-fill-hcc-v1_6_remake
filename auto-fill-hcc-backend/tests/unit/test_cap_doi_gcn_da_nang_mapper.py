"""Unit test mapper "Cấp đổi Giấy chứng nhận QSDĐ..." (Đà Nẵng).

Kiểm: đồng sở hữu vợ+chồng (ghép 2 tên, không nhầm ủy quyền), ủy quyền thật, ghép SỐ GCN vào nội dung yêu
cầu (form không có ô số GCN), remap phường sáp nhập."""

from app.pipelines.cap_doi_gcn_da_nang.process.mapper import enrich


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _map(vals: dict) -> dict:
    fields, _ = enrich(_flds(vals), {})
    return {f["name"]: f["value"] for f in fields}


def test_dong_so_huu_vo_chong_tu_nop():
    # GCN đồng sở hữu "Ông X và Bà Y"; người nộp là 1 trong 2 → TỰ NỘP (không phải ủy quyền).
    out = _map({
        "ChuHoSo_HoTen": "NGUYỄN XUYÊN và LÊ THỊ THANH VÂN",
        "NguoiNop_HoTen": "NGUYỄN XUYÊN",
        "NguoiNop_SoDinhDanh": "048074001234",
        "GCN_So": "BA 685616 (số vào sổ CH 00131)",
    })
    assert out["data[ownerFullname]"] == "NGUYỄN XUYÊN và LÊ THỊ THANH VÂN"
    assert out["data[isOwnerDossier]"] is True
    assert out["data[fullname]"] == "NGUYỄN XUYÊN"
    assert out["data[chonDoiTuong]"] == "Cá nhân"
    assert "BA 685616" in out["data[noidungyeucaugiaiquyet]"]


def test_gcn_so_ghep_vao_noi_dung_va_ly_do():
    out = _map({
        "ChuHoSo_HoTen": "NGUYỄN XUYÊN", "NguoiNop_HoTen": "NGUYỄN XUYÊN",
        "GCN_So": "BA 685616", "NoiDungBienDong": "Cấp đổi do Giấy chứng nhận cũ bị rách, hư hỏng",
    })
    nd = out["data[noidungyeucaugiaiquyet]"]
    assert "Cấp đổi Giấy chứng nhận số BA 685616" in nd
    assert "rách" in nd


def test_noi_dung_da_co_so_gcn_khong_lap():
    out = _map({
        "ChuHoSo_HoTen": "A", "NguoiNop_HoTen": "A",
        "GCN_So": "BA 685616",
        "NoiDungBienDong": "Cấp đổi Giấy chứng nhận số BA 685616 do chỉnh lý diện tích sau đo đạc",
    })
    # không prepend trùng số GCN
    assert out["data[noidungyeucaugiaiquyet]"].count("BA 685616") == 1


def test_noi_dung_trong_fallback():
    out = _map({"ChuHoSo_HoTen": "NGUYỄN XUYÊN", "NguoiNop_HoTen": "NGUYỄN XUYÊN"})
    assert out["data[noidungyeucaugiaiquyet]"].startswith("NGUYỄN XUYÊN ĐỀ NGHỊ GIẢI QUYẾT")


def test_uy_quyen_bo_tich_dien_2_vai():
    # Người nộp KHÁC chủ hồ sơ và KHÔNG nằm trong chuỗi tên chủ hồ sơ → ủy quyền thật.
    out = _map({
        "ChuHoSo_HoTen": "NGUYỄN XUYÊN và LÊ THỊ THANH VÂN",
        "NguoiNop_HoTen": "LƯƠNG HOÀNG TRUNG",
        "NguoiNop_SoDinhDanh": "048074009999",
        "GCN_So": "BA 685616",
    })
    assert out["data[isOwnerDossier]"] is False
    assert out["data[fullname]"] == "LƯƠNG HOÀNG TRUNG"
    assert out["data[identityNumber]"] == "048074009999"


def test_chu_ho_so_to_chuc():
    out = _map({
        "ChuHoSo_LoaiChuThe": "Tổ chức",
        "ChuHoSo_HoTen": "Công ty TNHH MTV Du Lịch Thanh Vân",
        "NguoiNop_HoTen": "LƯƠNG HOÀNG TRUNG",
        "NguoiNop_SoDinhDanh": "048074009999",
        "NguoiNop_MaSoThue": "0401234567",
        "GCN_So": "CH 683592",
    })
    assert out["data[ownerFullname]"] == "Công ty TNHH MTV Du Lịch Thanh Vân"
    assert out["data[organization]"] == "Công ty TNHH MTV Du Lịch Thanh Vân"
    assert out["data[isOwnerDossier]"] is False
    assert out["data[chonDoiTuong]"] == "Cá nhân"


def test_remap_dia_chi_nguoi():
    out = _map({
        "ChuHoSo_HoTen": "NGUYỄN XUYÊN", "NguoiNop_HoTen": "NGUYỄN XUYÊN",
        "ChuHoSo_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Phước Ninh", "diaChi": "12 Bạch Đằng"},
    })
    assert out["data[province]"] == "Thành phố Đà Nẵng"
    assert out["data[district]"] == "Phường Hải Châu"  # Phước Ninh (cũ) → Hải Châu (hiện hành)
    assert out["data[address]"] == "12 Bạch Đằng"


def test_ngay_sinh_chi_co_nam_thi_bo_trong():
    # Giấy ủy quyền/GCN ghi "sinh năm 1987" (không ngày/tháng) → KHÔNG điền ô ngày (tránh flatpickr ra rác).
    out = _map({
        "ChuHoSo_HoTen": "CÔNG TY TNHH MTV DU LỊCH THANH VÂN", "ChuHoSo_LoaiChuThe": "Tổ chức",
        "NguoiNop_HoTen": "LƯƠNG HOÀNG TRUNG", "NguoiNop_NgaySinh": "1987",
        "NguoiNop_SoDinhDanh": "049087017746",
    })
    assert "data[birthday]" not in out
    # ngày cấp đầy đủ vẫn điền bình thường
    out2 = _map({"ChuHoSo_HoTen": "A", "NguoiNop_HoTen": "A", "NguoiNop_NgaySinh": "12/11/1984"})
    assert out2["data[birthday]"] == "12/11/1984"


def test_thieu_chu_ho_so_van_giu_nguoi_nop():
    fields, warnings = enrich(_flds({"NguoiNop_HoTen": "NGUYỄN XUYÊN", "NguoiNop_SoDinhDanh": "048074001234"}), {})
    names = {f["name"] for f in fields}
    assert "data[fullname]" in names
    assert any("chủ hồ sơ" in w.lower() for w in warnings)
