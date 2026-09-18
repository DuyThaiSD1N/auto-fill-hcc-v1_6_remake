"""Unit test mapper "Cấp điều chỉnh giấy phép xây dựng" (Bộ Xây dựng)."""

from app.pipelines.dieu_chinh_giay_phep_xay_dung.process import mapper


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _run(vals: dict, options: dict | None = None):
    fields, warnings = mapper.enrich(_flds(vals), options or {})
    by = {}
    for f in fields:
        by[f["name"]] = f
    return by, warnings


_CA_NHAN = {
    "ChuDauTu_Loai": "Chủ hộ",
    "ChuHo_HoTen": "Đặng Công Nam - Nguyễn Thị Hòa",
    "ChuHo_SoDinhDanh": "049059000699",
    "ChuHo_DienThoai": "0386811586",
    "Applicant_HoTen": "Đặng Công Nam",
    "Applicant_SoDinhDanh": "049059000699",
    "Applicant_NoiCuTru": {"tinh": "Đà Nẵng", "xa": "Hải Châu", "diaChi": "K143/05 Nguyễn Chí Thanh"},
    "Dat_DiaDiemXayDung": {"tinh": "Đà Nẵng", "xa": "Hòa Cường Bắc", "diaChi": "K143/05 Nguyễn Chí Thanh"},
    "Dat_ThuaDatSo": "158",
    "Dat_ToBanDoSo": "110",
    "Dat_DienTich": "85,80",
    "Dat_SoNha": "K143/05",
    "Dat_DuongPho": "Nguyễn Chí Thanh",
    "GPXD_So": "43/GPXD",
    "CongTrinh_Ten": "Nhà ở riêng lẻ",
    "CongTrinh_ThoiGianDuKienHoanThanh": "06 tháng",
    "DieuChinh_NoiDung": "Điều chỉnh tăng diện tích xây dựng tầng 3 và bổ sung kết cấu mái tôn.",
}


def test_ca_nhan_tu_nop_dien_du_khoi_dieu_chinh():
    d, w = _run(_CA_NHAN)
    assert d["data[chonDoiTuong]"]["value"] == "Cá nhân"
    assert d["data[fullname]"]["value"] == "Đặng Công Nam"
    assert d["data[identityNumber]"]["value"] == "049059000699"
    assert d["data[loaiHinhChuDauTu]"]["value"] == "chuHo"
    assert d["data[tenChuHo]"]["value"] == "Đặng Công Nam - Nguyễn Thị Hòa"
    assert d["data[soDinhDanhChuHo]"]["value"] == "049059000699"
    # Địa điểm xây dựng.
    assert d["data[loDatSo]"]["value"] == "158 (tờ bản đồ số 110)"
    assert d["data[dienTichLoDat]"]["value"] == "85.8"
    assert d["data[soNha]"]["value"] == "K143/05"
    assert d["data[duongPho]"]["value"] == "Nguyễn Chí Thanh"
    # Khối điều chỉnh.
    assert d["data[tenCongTrinh]"]["value"] == "Nhà ở riêng lẻ"
    assert d["data[noiDungDeNghiDieuChinh]"]["value"].startswith("Điều chỉnh tăng diện tích")
    assert d["data[thoiGianDuKienHoanThanh]"]["value"] == "06 tháng"
    assert d["data[tenHoSo]"]["value"] == "Điều chỉnh Giấy phép xây dựng số 43/GPXD"
    assert not w


def test_dom_expect_cho_o_nhan_than_thieu():
    # Ngày cấp/nơi cấp CCCD không có trong hồ sơ → phát dom-expect (FE tô đỏ ô trống).
    d, _ = _run(_CA_NHAN)
    assert d["data[identityDate]"]["comp"] == "dom-expect"
    assert d["data[identityAgency]"]["comp"] == "dom-expect"
    assert d["data[fullname]"]["comp"] == "dom-input"
    # GIỚI TÍNH suy được tất định từ chữ số thứ 4 của CCCD 12 số → vẫn điền.
    assert d["data[gender]"]["value"] == "Nam"
    # NGÀY SINH thì KHÔNG: CCCD chỉ mã hoá NĂM, ghép "01/01/<năm>" là bịa ngày/tháng.
    # Fixture này không có Applicant_NgaySinh → phải tô đỏ để cán bộ tự nhập.
    assert d["data[birthday]"]["comp"] == "dom-expect"
    assert d["data[birthday]"]["value"] == ""


def test_noi_dung_dieu_chinh_giu_xuong_dong():
    noi = "Điều chỉnh:\n- Tăng DTXD tầng 3 thêm 12 m²\n- Bổ sung kết cấu mái tôn"
    d, _ = _run({**_CA_NHAN, "DieuChinh_NoiDung": noi})
    out = d["data[noiDungDeNghiDieuChinh]"]["value"]
    assert out.count("\n") == 2
    assert "- Tăng DTXD tầng 3" in out


def test_thieu_noi_dung_dieu_chinh_tra_canh_bao():
    vals = {k: v for k, v in _CA_NHAN.items() if k != "DieuChinh_NoiDung"}
    d, w = _run(vals)
    assert "data[noiDungDeNghiDieuChinh]" not in d
    assert w and "điều chỉnh" in w[0].lower()


def test_don_vi_thiet_ke_khong_leak_vao_to_chuc_khi_chu_dau_tu_ca_nhan():
    # BẪY: chủ đầu tư là CÁ NHÂN (chủ hộ) nhưng LLM lỡ trích công ty thiết kế vào ToChucNop_* →
    # mapper PHẢI ép Cá nhân + KHÔNG phát khối tổ chức.
    d, _ = _run({
        **_CA_NHAN,
        "ToChucNop_Ten": "CÔNG TY TNHH MTV PCD NGUYỄN HẢI",
        "ToChucNop_MaSoThue": "0401518783",
    })
    assert d["data[chonDoiTuong]"]["value"] == "Cá nhân"
    assert "data[organization]" not in d
    assert "data[taxCode]" not in d


def test_chu_dau_tu_to_chuc_thi_phat_organization_block():
    # Chủ đầu tư THỰC SỰ là tổ chức → chonDoiTuong Tổ chức + khối doanh nghiệp người nộp.
    d, _ = _run({
        "ChuDauTu_Loai": "Chủ đầu tư",
        "ChuDauTu_TenToChuc": "CÔNG TY CỔ PHẦN ĐẦU TƯ ABC",
        "ChuDauTu_MaSoDoanhNghiep": "0401234567",
        "ChuDauTu_NguoiDaiDien": "Trần Văn B",
        "Applicant_HoTen": "Trần Văn B",
        "ToChucNop_Ten": "CÔNG TY CỔ PHẦN ĐẦU TƯ ABC",
        "ToChucNop_MaSoThue": "0401234567",
        "ToChucNop_DiaChi": {"tinh": "Đà Nẵng", "xa": "Hải Châu", "diaChi": "1 Lê Duẩn"},
        "DieuChinh_NoiDung": "Điều chỉnh chiều cao.",
    })
    assert d["data[chonDoiTuong]"]["value"] == "Tổ chức"
    assert d["data[organization]"]["value"] == "CÔNG TY CỔ PHẦN ĐẦU TƯ ABC"
    assert d["data[taxCode]"]["value"] == "0401234567"
    assert d["data[loaiHinhChuDauTu]"]["value"] == "chuDauTu"
    assert d["data[tenChuDauTu]"]["value"] == "CÔNG TY CỔ PHẦN ĐẦU TƯ ABC"


def test_dia_diem_khac_noi_cu_tru():
    # 2 địa chỉ (nơi ở người nộp vs địa điểm công trình) dùng occurrence khác nhau, không đè nhau.
    d, _ = _run(_CA_NHAN)
    provinces = [f for f in mapper.enrich(_flds(_CA_NHAN), {})[0] if f["name"] == "data[province]"]
    assert len(provinces) == 2
    assert provinces[0].get("occurrence") == 0
    assert provinces[1].get("occurrence") == 1


# ---------------------------------------------------------------------------
# Hồ sơ thật (CCCD 026077005820): form bị điền ngày sinh 01/01/1977 trong khi KHÔNG giấy tờ nào ghi
# ngày sinh — mapper tự ghép "01/01/" + năm mã hoá trong CCCD. Cùng lỗi đã vá ở cap_giay_phep_xay_dung.
# ---------------------------------------------------------------------------
_NGUOI_NOP = {"Applicant_HoTen": "Bùi Trọng N.", "Applicant_SoDinhDanh": "026077005820"}


def test_chi_biet_nam_sinh_tu_cccd_thi_khong_bia_ngay_thang():
    by, _ = _run(_NGUOI_NOP)

    assert by["data[birthday]"]["value"] == ""
    assert by["data[birthday]"]["comp"] == "dom-expect"
    # Giới tính thì VẪN suy được: chữ số thứ 4 của CCCD mã hoá giới tính — tất định, không phải đoán.
    assert by["data[gender]"]["value"] == "Nam"


def test_chi_co_nam_sinh_roi_cung_khong_ghep_thanh_ngay():
    by, _ = _run({**_NGUOI_NOP, "Applicant_NamSinh": "1977"})

    assert by["data[birthday]"]["value"] == ""
    assert by["data[birthday]"]["comp"] == "dom-expect"


def test_co_ngay_sinh_day_du_thi_van_dien_binh_thuong():
    by, _ = _run({**_NGUOI_NOP, "Applicant_NgaySinh": "23/05/1977"})

    assert by["data[birthday]"]["value"] == "23/05/1977"


def test_nam_lech_cccd_thi_chi_sua_nam_giu_nguyen_ngay_thang():
    by, _ = _run({**_NGUOI_NOP, "Applicant_NgaySinh": "23/05/1968"})

    assert by["data[birthday]"]["value"] == "23/05/1977"


def test_mapper_khong_con_ghep_01_01_trong_code():
    """Chặn việc ghép lại '01/01/<năm>' — chỉ được phép xuất hiện trong docstring giải thích."""
    import inspect

    src = inspect.getsource(mapper._birthday_from_year)
    body = src.split('"""')[-1]  # phần sau docstring
    assert "01/01/" not in body
