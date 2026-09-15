"""Unit test mapper "[Đà Nẵng] Đăng ký biến động QSDĐ (chuyển nhượng/thừa kế/tặng cho...)" (#75).

Reproduce mẫu live 05/09/2026 (chủ hồ sơ TỔ CHỨC ủy quyền cá nhân nộp) + các fix:
- điền Mã định danh tổ chức, doanh nghiệp (data[taxCode]) từ chủ hồ sơ;
- SĐT + địa chỉ lấy của CHỦ HỒ SƠ;
- Nội dung yêu cầu giải quyết LẤY TỪ ĐƠN (không mặc định);
- KHÔNG bịa Nơi cấp CCCD khi giấy tờ không ghi.
"""

from app.pipelines.dang_ky_bien_dong_dat_dai_da_nang.process import mapper


def _fields(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _map(d: dict) -> dict:
    out, _ = mapper.enrich(_fields(d))
    return {f["name"]: f["value"] for f in out}


def test_uy_quyen_to_chuc_sample():
    """Chủ hồ sơ = công ty (ủy quyền cá nhân nộp): điền mã số DN + SĐT/địa chỉ chủ hồ sơ + nội dung từ đơn."""
    got = _map({
        "ChuHoSo_LoaiChuThe": "Tổ chức",
        "ChuHoSo_HoTen": "CÔNG TY CỔ PHẦN BẢO QUẢN PRO",
        "ChuHoSo_SoDinhDanh": "2500691905",
        "ChuHoSo_DiaChi": {"quocGia": "Việt Nam", "tinh": "Phú Thọ", "xa": "Bình Nguyên", "diaChi": "Khu Đồng Mố"},
        "ChuHoSo_DienThoai": "0934862336",
        "NoiDungBienDong": "Nhận chuyển nhượng",
        "NguoiNop_LoaiDoiTuong": "Cá nhân",
        "NguoiNop_HoTen": "LÊ VĂN DUY",
        "NguoiNop_NgaySinh": "16/09/2001",
        "NguoiNop_GioiTinh": "Nam",
        "NguoiNop_SoDinhDanh": "048201000144",
        "NguoiNop_DiaChi": {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Hòa Cường", "diaChi": ""},
        # KHÔNG có NguoiNop_NoiCap (giấy ủy quyền không ghi nơi cấp).
    })
    # Chủ hồ sơ tổ chức.
    assert got["data[ownerFullname]"] == "CÔNG TY CỔ PHẦN BẢO QUẢN PRO"
    assert got["data[organization]"] == "CÔNG TY CỔ PHẦN BẢO QUẢN PRO"
    # FIX #1: Mã định danh tổ chức, doanh nghiệp.
    assert got["data[taxCode]"] == "2500691905"
    # FIX #3: SĐT lấy của chủ hồ sơ.
    assert got["data[phoneNumber]"] == "0934862336"
    # FIX #4: địa chỉ lấy của chủ hồ sơ (Phú Thọ), KHÔNG phải người nộp (Đà Nẵng).
    assert got["data[province]"] == "Tỉnh Phú Thọ"
    assert got["data[district]"] == "Bình Nguyên"
    assert got["data[address]"] == "Khu Đồng Mố"
    # FIX #5: Nội dung yêu cầu = nội dung biến động trong đơn, không phải câu ghép mặc định.
    assert got["data[noidungyeucaugiaiquyet]"] == "Nhận chuyển nhượng"
    assert "ĐỀ NGHỊ GIẢI QUYẾT" not in got["data[noidungyeucaugiaiquyet]"]
    # Ủy quyền: bỏ tích + nhân thân là người nộp.
    assert got["data[isOwnerDossier]"] is False
    assert got["data[fullname]"] == "LÊ VĂN DUY"
    assert got["data[identityNumber]"] == "048201000144"
    assert got["data[chonDoiTuong]"] == "Cá nhân"
    # FIX #2: KHÔNG bịa nơi cấp khi giấy tờ không ghi.
    assert "data[identityAgency]" not in got


def test_khong_bia_noi_cap_khi_thieu():
    got = _map({
        "ChuHoSo_LoaiChuThe": "Cá nhân",
        "ChuHoSo_HoTen": "NGUYỄN VĂN A",
        "NguoiNop_HoTen": "NGUYỄN VĂN A",
        "NguoiNop_SoDinhDanh": "048201000144",
        # không có NguoiNop_NoiCap
    })
    assert "data[identityAgency]" not in got
    # Tự nộp → tích.
    assert got["data[isOwnerDossier]"] is True


def test_noi_cap_giu_khi_co():
    got = _map({
        "ChuHoSo_LoaiChuThe": "Cá nhân",
        "ChuHoSo_HoTen": "NGUYỄN VĂN A",
        "NguoiNop_HoTen": "NGUYỄN VĂN A",
        "NguoiNop_SoDinhDanh": "048201000144",
        "NguoiNop_NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    })
    assert "data[identityAgency]" in got


def test_to_chuc_khong_uy_quyen_de_trong_nhan_than_nguoi_nop():
    """Mẫu live 05/09/2026 (Hòa Cầm): chủ hồ sơ TỔ CHỨC, KHÔNG có ủy quyền kèm CCCD → để trống nhân thân
    người nộp (không ghép chéo danh tính người đại diện pháp luật). Vẫn điền chủ hồ sơ + mã số DN + liên hệ.
    """
    # LLM sau khi sửa prompt để TRỐNG NguoiNop_* (không lấy Lê Hồng Nhu/Lê Xuân Vũ).
    got = _map({
        "ChuHoSo_LoaiChuThe": "Tổ chức",
        "ChuHoSo_HoTen": "CÔNG TY CỔ PHẦN ĐẦU TƯ KHU CÔNG NGHIỆP HOÀ CẦM",
        "ChuHoSo_SoDinhDanh": "0400572788",
        "ChuHoSo_DiaChi": {"tinh": "Đà Nẵng", "xa": "Cẩm Lệ", "diaChi": "Đường số 01, khu công nghiệp Hòa Cầm"},
        "ChuHoSo_DienThoai": "0914109669",
        "NoiDungBienDong": "Nhận chuyển nhượng",
    })
    # Chủ hồ sơ + mã số DN + liên hệ vẫn điền.
    assert got["data[organization]"] == "CÔNG TY CỔ PHẦN ĐẦU TƯ KHU CÔNG NGHIỆP HOÀ CẦM"
    assert got["data[taxCode]"] == "0400572788"
    assert got["data[phoneNumber]"] == "0914109669"
    assert got["data[province]"] == "Thành phố Đà Nẵng"
    assert got["data[noidungyeucaugiaiquyet]"] == "Nhận chuyển nhượng"
    # KHÔNG điền nhân thân người nộp.
    assert "data[fullname]" not in got
    assert "data[identityNumber]" not in got
    assert "data[birthday]" not in got
    assert "data[identityAgency]" not in got
    assert "data[chonDoiTuong]" not in got
    # Không tick "chủ hồ sơ cũng là người nộp".
    assert got["data[isOwnerDossier]"] is False


def test_to_chuc_co_uy_quyen_van_dien_ca_hai():
    """Tổ chức CÓ ủy quyền cá nhân (có CCCD) → vẫn điền cả 2 vai (không rơi vào nhánh để trống)."""
    got = _map({
        "ChuHoSo_LoaiChuThe": "Tổ chức",
        "ChuHoSo_HoTen": "CÔNG TY CỔ PHẦN X",
        "ChuHoSo_SoDinhDanh": "0400000001",
        "NoiDungBienDong": "Nhận chuyển nhượng",
        "NguoiNop_LoaiDoiTuong": "Cá nhân",
        "NguoiNop_HoTen": "LÊ VĂN DUY",
        "NguoiNop_SoDinhDanh": "048201000144",
        "NguoiNop_NgaySinh": "16/09/2001",
    })
    assert got["data[isOwnerDossier]"] is False
    assert got["data[fullname]"] == "LÊ VĂN DUY"
    assert got["data[identityNumber]"] == "048201000144"
    assert got["data[taxCode]"] == "0400000001"


def test_tu_nop_ca_nhan_dia_chi_va_sdt_chu_ho_so():
    """Tự nộp cá nhân: địa chỉ/SĐT lấy chính chủ hồ sơ (owner==nộp)."""
    got = _map({
        "ChuHoSo_LoaiChuThe": "Cá nhân",
        "ChuHoSo_HoTen": "TRẦN THỊ B",
        "ChuHoSo_DienThoai": "0905123456",
        "ChuHoSo_DiaChi": {"tinh": "Đà Nẵng", "xa": "Hòa Cường", "diaChi": "12 Trần Văn Dư"},
        "NoiDungBienDong": "Nhận tặng cho",
        "NguoiNop_HoTen": "TRẦN THỊ B",
        "NguoiNop_SoDinhDanh": "048301000999",
    })
    assert got["data[isOwnerDossier]"] is True
    assert got["data[phoneNumber]"] == "0905123456"
    assert got["data[province]"] == "Thành phố Đà Nẵng"
    assert got["data[noidungyeucaugiaiquyet]"] == "Nhận tặng cho"
    # cá nhân → không có mã định danh tổ chức.
    assert "data[taxCode]" not in got
