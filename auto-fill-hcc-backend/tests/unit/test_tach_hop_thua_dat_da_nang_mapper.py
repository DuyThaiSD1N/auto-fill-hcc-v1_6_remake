"""Unit test mapper tách/hợp thửa Đà Nẵng: 2 vai Chủ hồ sơ (ownerFullname) / Người nộp (data[...])."""

from app.pipelines.tach_hop_thua_dat_da_nang.process import mapper


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _run(vals: dict):
    fields, warnings = mapper.enrich(_flds(vals), {})
    return {f["name"]: f["value"] for f in fields}, warnings


def test_tu_nop_owner_bang_nguoi_nop_tich_va_ghep_noi_dung():
    d, w = _run({
        "ChuHoSo_LoaiChuThe": "Cá nhân",
        "ChuHoSo_HoTen": "NGUYỄN VĂN HOÀNG",
        "NguoiNop_HoTen": "NGUYỄN VĂN HOÀNG",
        "NguoiNop_SoDinhDanh": "027060001118",
        "NguoiNop_NgaySinh": "10/05/1980",
        "NguoiNop_DiaChi": {"tinh": "Bắc Ninh", "xa": "Phường Song Liễu", "diaChi": "Thôn 1"},
    })
    assert d["data[isOwnerDossier]"] is True
    assert d["data[ownerFullname]"] == "NGUYỄN VĂN HOÀNG"
    assert d["data[fullname]"] == "NGUYỄN VĂN HOÀNG"
    assert d["data[identityNumber]"] == "027060001118"
    assert d["data[province]"] == "Tỉnh Bắc Ninh"
    assert d["data[district]"] == "Phường Song Liễu"
    assert d["data[chonDoiTuong]"] == "Cá nhân"
    assert d["data[noidungyeucaugiaiquyet]"] == "NGUYỄN VĂN HOÀNG ĐỀ NGHỊ GIẢI QUYẾT Tách thửa đất hoặc hợp thửa đất"
    assert not w


def test_noi_dung_yeu_cau_giu_nguyen_van_va_xuong_dong():
    noi_dung = (
        "Tách thửa đất số 16 tờ bản đồ số 118 diện tích 216 m²; loại đất: ODT, địa chỉ thửa đất: Phường "
        "Song Liễu, tỉnh Bắc Ninh, Giấy chứng nhận: AA 07859035, số vào sổ cấp GCN: CN 9138, ngày cấp GCN: "
        "04/05/2026 thành 02 thửa:\n"
        "- Thửa thứ 1: Ông Nguyễn Văn Ánh, thửa 16-1, diện tích: 110,7 m², loại đất: ODT\n"
        "- Thửa thứ 2: Ông Nguyễn Văn Trình, thửa 16-2, diện tích: 105,3 m², loại đất: ODT"
    )
    d, _ = _run({
        "ChuHoSo_HoTen": "NGUYỄN VĂN HOÀNG",
        "NguoiNop_HoTen": "NGUYỄN VĂN HOÀNG",
        "NoiDungYeuCau": noi_dung,
    })
    out = d["data[noidungyeucaugiaiquyet]"]
    # Dùng NGUYÊN VĂN đầy đủ, KHÔNG ghép câu khung, GIỮ đủ chi tiết + xuống dòng danh sách thửa con.
    assert "ĐỀ NGHỊ GIẢI QUYẾT" not in out
    assert "AA 07859035" in out and "CN 9138" in out and "04/05/2026" in out
    assert "- Thửa thứ 1: Ông Nguyễn Văn Ánh" in out
    assert "- Thửa thứ 2: Ông Nguyễn Văn Trình" in out
    assert out.count("\n") == 2  # giữ 2 dấu xuống dòng (3 dòng)


def test_noi_dung_trong_thi_fallback_cau_khung():
    d, _ = _run({
        "ChuHoSo_HoTen": "NGUYỄN VĂN HOÀNG",
        "NguoiNop_HoTen": "NGUYỄN VĂN HOÀNG",
    })
    assert d["data[noidungyeucaugiaiquyet]"] == "NGUYỄN VĂN HOÀNG ĐỀ NGHỊ GIẢI QUYẾT Tách thửa đất hoặc hợp thửa đất"


def test_uy_quyen_owner_khac_nguoi_nop_bo_tich_dien_ca_hai():
    d, w = _run({
        "ChuHoSo_HoTen": "NGUYỄN VĂN HOÀNG",
        "NguoiNop_HoTen": "NHÂM ĐẮC ĐẠT",
        "NguoiNop_SoDinhDanh": "034203010212",
        "NguoiNop_NgaySinh": "03/12/2003",
        "NguoiNop_DiaChi": {"tinh": "Đà Nẵng", "xa": "Phường Hòa Cường Bắc", "diaChi": "Số 5 Lê Lợi"},
    })
    assert d["data[isOwnerDossier]"] is False
    # Chủ hồ sơ ≠ người nộp: điền cả hai, không lẫn.
    assert d["data[ownerFullname]"] == "NGUYỄN VĂN HOÀNG"
    assert d["data[fullname]"] == "NHÂM ĐẮC ĐẠT"
    assert d["data[identityNumber]"] == "034203010212"
    assert d["data[province]"] == "Thành phố Đà Nẵng"
    assert d["data[noidungyeucaugiaiquyet]"].startswith("NGUYỄN VĂN HOÀNG ĐỀ NGHỊ GIẢI QUYẾT")
    assert not w


def test_tu_nop_lay_dia_chi_chu_ho_so_khi_thieu_dia_chi_nguoi_nop():
    # Tự nộp, LLM chỉ trích được ChuHoSo_DiaChi (không có NguoiNop_DiaChi) → vẫn điền địa chỉ.
    d, _ = _run({
        "ChuHoSo_HoTen": "NGUYỄN VĂN HOÀNG",
        "ChuHoSo_DiaChi": {"tinh": "Bắc Ninh", "xa": "Song Liễu", "diaChi": ""},
        "NguoiNop_HoTen": "NGUYỄN VĂN HOÀNG",
        "NguoiNop_SoDinhDanh": "027060001118",
    })
    assert d["data[isOwnerDossier]"] is True
    assert d["data[province]"] == "Tỉnh Bắc Ninh"
    assert d["data[district]"] == "Song Liễu"


def test_uy_quyen_khong_lay_dia_chi_chu_ho_so_cho_nguoi_nop():
    # Ủy quyền: người nộp KHÔNG có địa chỉ riêng → KHÔNG được mượn địa chỉ chủ đất.
    d, _ = _run({
        "ChuHoSo_HoTen": "NGUYỄN VĂN HOÀNG",
        "ChuHoSo_DiaChi": {"tinh": "Bắc Ninh", "xa": "Song Liễu", "diaChi": "Thôn 1"},
        "NguoiNop_HoTen": "NHÂM ĐẮC ĐẠT",
        "NguoiNop_SoDinhDanh": "034203010212",
    })
    assert d["data[isOwnerDossier]"] is False
    assert d["data[fullname]"] == "NHÂM ĐẮC ĐẠT"
    # KHÔNG mượn địa chỉ Bắc Ninh của chủ đất cho người nộp.
    assert "data[province]" not in d
    assert "data[district]" not in d


def test_chu_ho_so_to_chuc_tu_nop_phat_organization():
    # Tổ chức tự nộp (nộp = chủ) → tick + organization + chonDoiTuong Tổ chức.
    d, _ = _run({
        "ChuHoSo_LoaiChuThe": "Tổ chức",
        "ChuHoSo_HoTen": "CÔNG TY TNHH ABC",
        "NguoiNop_HoTen": "CÔNG TY TNHH ABC",
    })
    assert d["data[ownerFullname]"] == "CÔNG TY TNHH ABC"
    assert d["data[organization]"] == "CÔNG TY TNHH ABC"
    assert d["data[isOwnerDossier]"] is True
    assert d["data[chonDoiTuong]"] == "Tổ chức"


def test_chu_to_chuc_uy_quyen_ca_nhan_chondoituong_theo_nguoi_nop():
    # Chủ tổ chức ủy quyền cá nhân nộp → organization (chủ) vẫn phát; chonDoiTuong theo NGƯỜI NỘP = Cá nhân.
    d, _ = _run({
        "ChuHoSo_LoaiChuThe": "Tổ chức",
        "ChuHoSo_HoTen": "CÔNG TY TNHH ABC",
        "NguoiNop_HoTen": "TRẦN VĂN B",
        "NguoiNop_LoaiDoiTuong": "Cá nhân",
        "NguoiNop_SoDinhDanh": "040080000123",
    })
    assert d["data[organization]"] == "CÔNG TY TNHH ABC"
    assert d["data[isOwnerDossier]"] is False
    assert d["data[fullname]"] == "TRẦN VĂN B"
    assert d["data[chonDoiTuong]"] == "Cá nhân"


def test_thieu_chu_ho_so_tra_canh_bao():
    d, w = _run({"NguoiNop_HoTen": "AI ĐÓ"})
    assert w and "chủ hồ sơ" in w[0].lower()


def test_dia_chi_chi_co_tinh_bi_bo_qua_chong_doan():
    # Chỉ có tỉnh, thiếu xã + số nhà → nghi LLM suy từ thửa đất → bỏ cả cụm địa chỉ.
    d, _ = _run({
        "ChuHoSo_HoTen": "LÊ VĂN C",
        "NguoiNop_HoTen": "LÊ VĂN C",
        "NguoiNop_DiaChi": {"tinh": "Đà Nẵng", "xa": "", "diaChi": ""},
    })
    assert "data[province]" not in d
    assert "data[district]" not in d
