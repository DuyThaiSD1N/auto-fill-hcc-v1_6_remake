"""Unit test mapper "Xóa đăng ký biện pháp bảo đảm" (Đà Nẵng).

Kiểm: 2 vai (bên bảo đảm tổ chức / người ủy quyền), ghép SỐ GCN vào nội dung, remap, ngày-sinh-năm-đơn-lẻ."""

from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_da_nang.process.mapper import enrich


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _map(vals: dict) -> dict:
    fields, _ = enrich(_flds(vals), {})
    return {f["name"]: f["value"] for f in fields}


def test_to_chuc_uy_quyen():
    # Bên bảo đảm = Công ty (chủ hồ sơ tổ chức); người nộp = người được ủy quyền (cá nhân).
    out = _map({
        "ChuHoSo_LoaiChuThe": "Tổ chức",
        "ChuHoSo_HoTen": "Công ty TNHH Thương mại và Đầu tư Richico",
        "NguoiNop_HoTen": "PHẠM THỊ HẰNG",
        "NguoiNop_SoDinhDanh": "036180020439",
        "NguoiNop_GioiTinh": "Nữ",
        "GCN_So": "BA 685616",
    })
    assert out["data[ownerFullname]"] == "Công ty TNHH Thương mại và Đầu tư Richico"
    assert out["data[organization]"] == "Công ty TNHH Thương mại và Đầu tư Richico"
    assert out["data[isOwnerDossier]"] is False
    assert out["data[fullname]"] == "PHẠM THỊ HẰNG"
    assert out["data[chonDoiTuong]"] == "Cá nhân"
    assert "BA 685616" in out["data[noidungyeucaugiaiquyet]"]
    assert out["data[noidungyeucaugiaiquyet]"].startswith("Xóa đăng ký biện pháp bảo đảm đối với Giấy chứng nhận số BA 685616")


def test_gcn_va_noi_dung_yeu_cau():
    out = _map({
        "ChuHoSo_HoTen": "NGUYỄN VĂN A", "NguoiNop_HoTen": "NGUYỄN VĂN A",
        "GCN_So": "BA 685616",
        "NoiDungYeuCau": "Xóa thế chấp theo hợp đồng số 01/2020 tại Ngân hàng TMCP X, chi nhánh Đà Nẵng",
    })
    nd = out["data[noidungyeucaugiaiquyet]"]
    assert "BA 685616" in nd and "hợp đồng số 01/2020" in nd


def test_noi_dung_trong_fallback():
    out = _map({"ChuHoSo_HoTen": "NGUYỄN VĂN A", "NguoiNop_HoTen": "NGUYỄN VĂN A"})
    assert out["data[noidungyeucaugiaiquyet]"].startswith("NGUYỄN VĂN A ĐỀ NGHỊ GIẢI QUYẾT")


def test_tu_nop_ca_nhan():
    out = _map({
        "ChuHoSo_HoTen": "NGUYỄN VĂN A", "NguoiNop_HoTen": "NGUYỄN VĂN A",
        "NguoiNop_SoDinhDanh": "049074001234",
    })
    assert out["data[isOwnerDossier]"] is True
    assert out["data[chonDoiTuong]"] == "Cá nhân"


def test_remap_dia_chi():
    out = _map({
        "ChuHoSo_HoTen": "A", "NguoiNop_HoTen": "A",
        "ChuHoSo_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Phước Ninh", "diaChi": "12 Bạch Đằng"},
    })
    assert out["data[province]"] == "Thành phố Đà Nẵng"
    assert out["data[district]"] == "Phường Hải Châu"  # Phước Ninh (cũ) → Hải Châu


def test_ngay_sinh_chi_co_nam_bo_trong():
    out = _map({"ChuHoSo_HoTen": "A", "NguoiNop_HoTen": "A", "NguoiNop_NgaySinh": "1987"})
    assert "data[birthday]" not in out


def test_thieu_chu_ho_so_warning():
    fields, warnings = enrich(_flds({"NguoiNop_HoTen": "PHẠM THỊ HẰNG"}), {})
    assert any("chủ hồ sơ" in w.lower() for w in warnings)
