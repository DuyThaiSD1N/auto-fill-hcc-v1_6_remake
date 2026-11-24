"""Đăng ký sang tên, di chuyển xe tại Công an cấp tỉnh 2.000076 (Cổng DVC Bộ Công an): mapper ô form theo file mapping
"Mapping_Dang_ky_sang_ten_xe_o_to_BCA" (chủ xe tự nộp / người khai hộ) + nối registry / link kê khai / trợ lý."""
from app.pipelines.dang_ky_sang_ten_di_chuyen_xe_cap_tinh.process import mapper
from app.pipelines.dang_ky_sang_ten_di_chuyen_xe_cap_tinh.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

KEY = "dang-ky-sang-ten-di-chuyen-xe-cap-tinh"
SIBLING = "dang-ky-xe-lan-dau-nhap-khau"
# Hồ sơ mẫu bịa theo bộ giấy của file mapping: GCN thu hồi + hợp đồng mua bán + dữ liệu LPTB + thẻ của chủ xe mới.
HO_SO = {
    "Cccd_HoTen": "NGUYỄN VĂN AN", "Cccd_SoDinhDanh": "0010 9000 0001", "Cccd_NgaySinh": "1/7/1972",
    "Cccd_QuocTich": "Việt Nam", "Cccd_NgayCap": "6/4/2021",
    "Cccd_NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    "Cccd_NoiCuTru": {"tinh": "Lai Châu", "xa": "Xã Pắc Ta", "chiTietDuoiXa": "Bản Một"},
    "GcnThuHoi_LyDo": "Chuyển quyền sở hữu",
    "GcnThuHoi_ChuXe": "TRẦN VĂN BÌNH", "GcnThuHoi_ChuXeMaDinhDanh": "001080000009",
    "GcnThuHoi_ChuXeNgayCap": "04/12/2021", "GcnThuHoi_ChuXeDienThoai": "0911111111",
    "GcnThuHoi_DiaChiChuXe": "Bản Hai, Pa Tần, Lai Châu",
    "GcnThuHoi_ChuMoiHoTen": "NGUYỄN VĂN AN", "GcnThuHoi_ChuMoiMaDinhDanh": "001090000001",
    "GcnThuHoi_ChuMoiDienThoai": "00000000000",
    "GcnThuHoi_ChuMoiDiaChi": {"tinh": "Tỉnh Lai Châu", "xa": "Xã Pắc Ta", "chiTietDuoiXa": "BẢN MỘT"},
    "Hdmb_BenBanHoTen": "TRẦN VĂN BÌNH", "Hdmb_BenMuaHoTen": "NGUYỄN VĂN AN", "Hdmb_BenMuaSoCccd": "001090000001",
    "Hdmb_BenMuaNgaySinh": "01/07/1972", "Hdmb_BenMuaNgayCapCccd": "06/04/2021",
    "Hdmb_BenMuaNoiCapCccd": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "Hdmb_BenMuaDiaChi": {"tinh": "tỉnh Lai Châu", "xa": "xã Pắc Ta", "chiTietDuoiXa": "Bản Một"},
    "Lptb_MaHoSo": "11200000000001", "Lptb_TenNguoiNop": "Nguyễn Văn An", "Lptb_MaDinhDanh": "001090000001",
    "Lptb_DienThoai": "0912 345 678", "Lptb_BienSo": "00A-000.00", "Lptb_SoMay": "4A00KBA0001",
    "Lptb_SoKhung": "MK2000000000001",
    "Xe_BienSo": "00A - 000.00", "Xe_MauBien": "Nền màu trắng, chữ và số màu đen", "Xe_LoaiXe": "Ô tô con",
    "Xe_SoKhung": "mk2000000000001", "Xe_SoMay": "4A00KBA0001",
}
# Phần I cổng khoá theo tài khoản VNeID; Auto Fill / trợ lý gửi hai ô readonly qua options.formContext.
OWNER_ACCOUNT = {"formContext": {"applicantFullname": "NGUYỄN VĂN AN", "applicantIdentityNumber": "001090000001"}}
OTHER_ACCOUNT = {"formContext": {"applicantFullname": "LÊ VĂN CƯỜNG", "applicantIdentityNumber": "001095000003"}}


def _enrich(values: dict, options=None):
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def _by(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_chu_xe_tu_nop_dien_tra_cuu_chu_xe_va_nhan_ket_qua_theo_mapping():
    assert set(HO_SO) <= ALLOWED
    out, warnings = _enrich(HO_SO, OWNER_ACCOUNT)
    by = _by(out)
    names = [f["name"] for f in out]
    # Phần I + khối tra cứu đứng đầu.
    assert names[:8] == ["CongDan__fsLaChuXe", "CongDan__fstracuuLoaiDangKy", "CongDan__fsRadioLoaiXe",
                         "CongDan__fstracuuMauBien", "CongDan__fstracuuBienSo", "CongDan__fstracuuSoKhung",
                         "CongDan__fstracuuSoMay", "CongDan__fsTraCuMaHsLPTB"]
    assert by["CongDan__fsLaChuXe"] is True and "CongDan__fsLaNguoiKhaiHo" not in by
    assert by["CongDan__fstracuuLoaiDangKy"] == "Đăng ký sang tên xe" and by["CongDan__fsRadioLoaiXe"] == "Ô tô"
    assert by["CongDan__fstracuuMauBien"] == "Nền màu trắng, chữ và số màu đen"
    assert by["CongDan__fstracuuBienSo"] == "00A-000.00" and by["CongDan__fstracuuSoKhung"] == "MK2000000000001"
    assert by["CongDan__fstracuuSoMay"] == "4A00KBA0001" and by["CongDan__fsTraCuMaHsLPTB"] == "11200000000001"
    # Chủ xe tự nộp: ô khoá theo tài khoản, captcha, ô readonly sau Tra cứu, khối người làm thủ tục KHÔNG phát.
    assert not {"CongDan_soCmnd", "CongDan_tenCongDan", "CongDan__fsnamSinh", "CongDan__fsmaXacNhan",
                "CongDan__fsChungTuCQSH", "CongDan__fsSoKhung", "CongDan__fsMaHsLPTBDienTu", "CongDan__fsLPTB_soloai",
                "CongDan__fsDDKTenDiemDK", "CongDan__fsBCATamTruTinh", "CongDan__fsBCANoiOHienTai"} & set(by)
    assert not [n for n in by if "NDUQ" in n]
    # Phần III theo thẻ (chủ xe MỚI), địa chỉ theo hợp đồng (địa giới mới); không lấy gì của chủ xe cũ.
    assert by["CongDan__fsLoaiGiayToChuXe"] == "Căn cước công dân" and by["CongDan__fsngayCapCmnd"] == "06/04/2021"
    assert by["CongDan__fsnoiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert by["CongDan__fsQuocTichChuXe"] == "Việt Nam"
    assert by["CongDan__fsBCAHKTTTinh"] == "Tỉnh Lai Châu" and by["CongDan__fsBCAHKTTXa"] == "Xã Pắc Ta"
    assert by["CongDan__fsBCAHKTTDCChiTiet"] == "Bản Một"
    assert names.index("CongDan__fsBCAHKTTTinh") < names.index("CongDan__fsBCAHKTTXa")
    assert next(f for f in out if f["name"] == "CongDan__fsBCAHKTTXa")["waitMs"] == 8000
    # SĐT theo giấy LPTB (GCN thu hồi ghi dãy 0 giả; 0911… là của chủ cũ); ô của chủ tài khoản giữ giá trị cổng.
    assert by["CongDan_diDong"] == "0912345678" and "CongDan_email" not in by
    assert next(f for f in out if f["name"] == "CongDan_diDong")["keepPortalValue"] is True
    # Không có giấy phép kinh doanh vận tải → "Không"; không có giấy trúng đấu giá → không tích.
    assert by["CongDan__fsCoKinhDoanhvanTai"] == "Không kinh doanh vận tải"
    assert not {"CongDan__fsSoGiayPhepKinhDoanh", "CongDan__fs359581_checkbox_1", "CongDan__fsBienSoTrungDauGia"} & set(by)
    # Nhận kết quả: người nhận = chủ xe, Tỉnh trước Xã.
    assert "CongDan__fsHinhThucNhanKQ" not in by
    assert by["CongDan__fsTenNguoiNhanKQ"] == "NGUYỄN VĂN AN" and by["CongDan__fsSoDienThoaiNguoiNhan"] == "0912345678"
    assert by["CongDan__fsTinhNhanKQ"] == "Tỉnh Lai Châu" and by["CongDan__fsXaNhanKQ"] == "Xã Pắc Ta"
    assert by["CongDan__fsDiaChiChiTietNhanKQ"] == "Bản Một"
    assert all(f["comp"] == UI_COMP_BY_NAME[f["name"]] for f in out)
    assert mapper.NO_ACCOUNT_WARNING not in warnings
    assert any("hình thức nhận kết quả" in w for w in warnings) and warnings[-1] == mapper.TRA_CUU_WARNING
    assert not any("Không đọc được" in w for w in warnings)


def test_khong_doc_duoc_tai_khoan_van_dien_kieu_chu_xe_kem_canh_bao():
    out, warnings = _enrich(HO_SO)
    by = _by(out)
    assert by["CongDan__fsLaChuXe"] is True and "CongDan_soCmnd" not in by
    assert mapper.NO_ACCOUNT_WARNING in warnings
    # Thẻ của bên bán bị bỏ: ngày cấp theo hợp đồng (bên mua), quốc tịch suy từ căn cước bên mua.
    values = {**HO_SO, "Cccd_HoTen": "TRẦN VĂN BÌNH", "Cccd_SoDinhDanh": "001080000009", "Cccd_NgayCap": "01/01/2023"}
    by = _by(_enrich(values, OWNER_ACCOUNT)[0])
    assert by["CongDan__fsngayCapCmnd"] == "06/04/2021" and by["CongDan__fsQuocTichChuXe"] == "Việt Nam"
    assert by["CongDan__fsTenNguoiNhanKQ"] == "NGUYỄN VĂN AN"


def test_tai_khoan_khac_chu_xe_thi_tich_khai_ho_va_dien_o_chu_xe():
    values = {**HO_SO, "UyQuyen_BenUyQuyenHoTen": "Nguyễn Văn An", "UyQuyen_HoTen": "Lê Văn Cường",
              "UyQuyen_SoDinhDanh": "001095000003", "UyQuyen_DienThoai": "0987654321",
              "CccdNduq_HoTen": "LÊ VĂN CƯỜNG", "CccdNduq_SoDinhDanh": "001095000003", "CccdNduq_NgayCap": "15/8/2024",
              "CccdNduq_NoiCap": "BỘ CÔNG AN"}
    assert set(values) <= ALLOWED
    out, warnings = _enrich(values, OTHER_ACCOUNT)
    by = _by(out)
    assert out[0]["name"] == "CongDan__fsLaNguoiKhaiHo" and by["CongDan__fsLaNguoiKhaiHo"] is True
    assert "CongDan__fsLaChuXe" not in by
    # Ô chủ xe cổng mở khi khai hộ → nhập theo giấy của chủ xe.
    assert by["CongDan_soCmnd"] == "001090000001" and by["CongDan_tenCongDan"] == "NGUYỄN VĂN AN"
    assert by["CongDan__fsnamSinh"] == "01/07/1972" and by["CongDan_diDong"] == "0912345678"
    # SĐT / email ở đây là của chủ xe trên giấy, không phải của tài khoản → không giữ giá trị cổng.
    assert not any(f.get("keepPortalValue") for f in out)
    # Khối người làm thủ tục: tài khoản + giấy ủy quyền + thẻ của đúng người đó.
    assert by["CongDan__fsNDUQHoTen"] == "LÊ VĂN CƯỜNG" and by["CongDan__fsNDUQMaDinhDanh"] == "001095000003"
    assert by["CongDan__fsNDUQLoaiGiayTo"] == "Căn cước công dân" and by["CongDan__fsNDUQNgayCap"] == "15/08/2024"
    assert by["CongDan__fsNDUQCoQuanCap"] == "Bộ Công an" and by["CongDan__fsDiDongNDUQ"] == "0987654321"
    assert any("người khai hộ" in w for w in warnings) and not any("còn thiếu" in w for w in warnings)
    names = [f["name"] for f in out]
    assert names.index("CongDan_tenCongDan") < names.index("CongDan__fsNDUQHoTen")


def test_khai_ho_khong_co_giay_uy_quyen_va_tai_khoan_la_ben_ban():
    # Người được BÊN BÁN ủy quyền ký hợp đồng không phải người làm thủ tục; thiếu giấy thì báo ô bắt buộc còn thiếu.
    out, warnings = _enrich(HO_SO, OTHER_ACCOUNT)
    by = _by(out)
    assert by["CongDan__fsNDUQHoTen"] == "LÊ VĂN CƯỜNG" and by["CongDan__fsNDUQMaDinhDanh"] == "001095000003"
    assert "CongDan__fsNDUQNgayCap" not in by
    assert any("Cấp ngày" in w and "Cơ quan cấp" in w and "Số điện thoại" in w for w in warnings)
    seller = {"formContext": {"applicantFullname": "TRẦN VĂN BÌNH", "applicantIdentityNumber": "001080000009"}}
    out, warnings = _enrich({**HO_SO, "Cccd_HoTen": "TRẦN VĂN BÌNH", "Cccd_SoDinhDanh": "001080000009"}, seller)
    assert _by(out)["CongDan__fsLaNguoiKhaiHo"] is True and any("chủ xe cũ" in w for w in warnings)
    # Giấy ủy quyền ghi người khác tài khoản → cảnh báo; tài khoản OCR lệch số mà trùng tên vẫn là chủ xe.
    other_uq = {**HO_SO, "UyQuyen_HoTen": "PHẠM THỊ DUNG", "UyQuyen_SoDinhDanh": "001190000004"}
    assert any("PHẠM THỊ DUNG" in w for w in _enrich(other_uq, OTHER_ACCOUNT)[1])
    near = {"formContext": {"applicantFullname": "Nguyễn Văn An", "applicantIdentityNumber": "001090000007"}}
    assert _by(_enrich(HO_SO, near)[0])["CongDan__fsLaChuXe"] is True
    # Không đọc được tài khoản mà hồ sơ có giấy ủy quyền → khai hộ theo giấy.
    by = _by(_enrich({**HO_SO, "UyQuyen_HoTen": "Lê Văn Cường", "UyQuyen_SoDinhDanh": "001095000003"})[0])
    assert by["CongDan__fsLaNguoiKhaiHo"] is True and by["CongDan__fsNDUQHoTen"] == "LÊ VĂN CƯỜNG"


def test_di_chuyen_nguyen_chu_xe_may_bien_vang_kinh_doanh_van_tai_dau_gia():
    values = {
        "Cccd_HoTen": "TRẦN VĂN BÌNH", "Cccd_SoDinhDanh": "001080000009", "Cccd_NgayCap": "01/01/2023",
        "Cccd_NoiCuTru": {"tinh": "Thành phố Hà Nội", "xa": "Phường Ba Đình", "chiTietDuoiXa": "Số 1 phố A"},
        "GcnThuHoi_LyDo": "Di chuyển", "GcnThuHoi_ChuXe": "TRẦN VĂN BÌNH", "GcnThuHoi_ChuXeMaDinhDanh": "001080000009",
        "GcnThuHoi_ChuXeDienThoai": "0911111111", "GcnThuHoi_DiaChiChuXe": "Bản Hai, Pa Tần, Lai Châu",
        "Xe_BienSo": "Biển số: 25b1-000.01", "Xe_MauBien": "Nền màu vàng, chữ và số màu đen",
        "Xe_LoaiXe": "Xe mô tô hai bánh", "Xe_SoKhung": "RLH000000000001", "Xe_SoMay": "JF00E0000001",
        "GpKdvt_SoGiayPhep": "GP-0001", "GpKdvt_NgayCap": "2/3/2025", "GpKdvt_NoiCap": "Sở Xây dựng",
        "DauGia_BienSo": "30K-999.99", "DauGia_SoGiay": "0001/XN", "DauGia_NgayCap": "05/05/2025",
        "DauGia_CoQuanCap": "Cục Cảnh sát giao thông", "HoSo_HinhThucNhanKetQua": "Qua dịch vụ bưu chính công ích",
    }
    assert set(values) <= ALLOWED
    out, warnings = _enrich(values, {"formContext": {"applicantIdentityNumber": "001080000009"}})
    by = _by(out)
    assert by["CongDan__fsLaChuXe"] is True
    assert by["CongDan__fstracuuLoaiDangKy"] == "Đăng ký di chuyển xe" and by["CongDan__fsRadioLoaiXe"] == "Xe máy"
    assert by["CongDan__fstracuuMauBien"] == "Nền màu vàng, chữ và số màu đen"
    assert by["CongDan__fstracuuBienSo"] == "25B1-000.01" and "CongDan__fsTraCuMaHsLPTB" not in by
    # Di chuyển: địa chỉ mới theo thẻ (không theo địa chỉ cũ trên GCN thu hồi), SĐT theo GCN thu hồi.
    assert by["CongDan__fsBCAHKTTTinh"] == "Thành phố Hà Nội" and by["CongDan__fsBCAHKTTDCChiTiet"] == "Số 1 phố A"
    assert by["CongDan_diDong"] == "0911111111" and by["CongDan__fsngayCapCmnd"] == "01/01/2023"
    assert by["CongDan__fsnoiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert by["CongDan__fsCoKinhDoanhvanTai"] == "Có kinh doanh vận tải"
    assert by["CongDan__fsSoGiayPhepKinhDoanh"] == "GP-0001" and by["CongDan__fsngayCapGPKD"] == "02/03/2025"
    assert by["CongDan__fs359581_checkbox_1"] is True and by["CongDan__fsBienSoTrungDauGia"] == "30K-999.99"
    assert by["CongDan__fsSoGiayXnTrungDauGia"] == "0001/XN" and by["CongDan__fsNGayCapBienDauGia"] == "05/05/2025"
    assert by["CongDan__fsHinhThucNhanKQ"] == "Qua bưu điện, tại nhà"
    # Di chuyển không cần mã LPTB; đủ ô tra cứu thì không cảnh báo thiếu.
    assert not any("Không đọc được" in w for w in warnings)


def test_mau_bien_loai_dang_ky_va_thieu_o_tra_cuu():
    assert mapper._plate_color("Nền màu xanh, chữ và số màu trắng") == "Nền màu xanh, chữ và số màu trắng"
    assert mapper._plate_color("NỀN VÀNG CHỮ ĐỎ") == "Nền màu vàng, chữ và số màu đỏ"
    assert mapper._plate_color("Biển trắng") == "Nền màu trắng, chữ và số màu đen"
    assert mapper._plate_color("Xám, Bạc") is None
    assert mapper._registration_kind({"Lptb_MaHoSo": "1"}) == "Đăng ký sang tên xe"
    assert mapper._registration_kind({"GcnThuHoi_LyDo": "Mất đăng ký"}) is None
    values = {k: v for k, v in HO_SO.items() if k not in ("Lptb_MaHoSo", "Xe_SoKhung", "Lptb_SoKhung", "Xe_MauBien")}
    out, warnings = _enrich(values, OWNER_ACCOUNT)
    assert not {"CongDan__fstracuuSoKhung", "CongDan__fsTraCuMaHsLPTB", "CongDan__fstracuuMauBien"} & set(_by(out))
    assert any("Màu biển" in w and "Số khung" in w and "Mã hồ sơ lệ phí trước bạ" in w for w in warnings)
    # Chỉ có SĐT giả của GCN thu hồi → bỏ, cảnh báo nhập tay.
    out, warnings = _enrich({k: v for k, v in HO_SO.items() if k != "Lptb_DienThoai"}, OWNER_ACCOUNT)
    assert "CongDan_diDong" not in _by(out) and any("số điện thoại chủ xe" in w for w in warnings)


def test_runner_tra_canh_bao(monkeypatch):
    import asyncio

    from app.pipelines._shared.compact_agent import runner as compact_runner
    from app.pipelines.dang_ky_sang_ten_di_chuyen_xe_cap_tinh.process import runner as xe_runner

    async def fake_run(*_args, **_kwargs):
        return {"fields": [{"name": k, "value": v} for k, v in HO_SO.items()]}

    monkeypatch.setattr(compact_runner, "run", fake_run)
    res = asyncio.run(xe_runner.run({}, OTHER_ACCOUNT))
    assert _by(res["fields"])["CongDan__fsLaNguoiKhaiHo"] is True and "blocked" not in res
    assert res["errors"][-1] == mapper.TRA_CUU_WARNING


def test_registry_link_va_detect():
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is None
    proc = registry.get_procedure(KEY)
    assert proc["hasAttachmentStep"] is False and proc["mode"] == "agent" and proc["collectFormContext"] is True
    assert proc["detect"]["urlScope"] == ["dichvucong.bocongan.gov.vn"] and proc["detect"]["codeOnPage"] is True
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "2.000076" and link["url"].endswith("tthc?matt=43474")
    assert link["directSubmit"] is True and link["bcaSubmit"] is True and link["label"] == proc["label"]
    public = next(p for p in with_ke_khai_detect_urls([proc]) if p["key"] == KEY)
    assert link["url"] in public["detect"]["urlIncludes"] and "matthc=2.000076" in public["detect"]["urlIncludes"]
    # Dòng chú thích Phần I trên form sang tên; trang đăng ký lần đầu không có "sang tên".
    phrases = proc["detect"]["textIncludes"]
    assert all(p in "trước khi sang tên bắt buộc phải thu hồi" for p in phrases)
    for key in ("dang-ky-xe-lan-dau-san-xuat-lap-rap-trong-nuoc", SIBLING):
        assert not any("sang tên" in p for p in registry.get_procedure(key)["detect"]["textIncludes"])


# ── Trợ lý người dân (handfree) ──
from app.channels.handfree.chat import flow  # noqa: E402

CAPS = {"supportsBcaDangKyXe": True}


def test_tro_ly_cung_key_mo_thang_trang_chon_truong_hop_hien_moi_tinh():
    from app.channels.handfree import procedure_registry as hf
    from app.channels.handfree.chat import script_mong
    from app.channels.handfree.chat.procedure_picker import prompt as picker

    proc, sibling = hf.get_procedure(KEY), hf.get_procedure(SIBLING)
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    # Nút "Nộp hồ sơ" trên trang thủ tục (link Auto Fill) trỏ trang chọn trường hợp cùng số matt.
    assert proc["keKhaiUrl"].endswith("chon-truong-hop-ho-so?ma-thu-tuc-public=" + link["url"].rsplit("=", 1)[1])
    assert proc["detect"] == registry.get_procedure(KEY)["detect"] and proc["label"] == link["label"]
    for field in ("flowProfile", "bcaPortal", "agencyDirectSubmit", "provinceOnly"):
        assert proc.get(field) == sibling.get(field), field
    # Đăng ký xe lần đầu (nhập khẩu + lắp ráp trong nước) có bước gắn ô ảnh đầu trang từ 24/11 (cờ extension riêng);
    # sang tên vẫn KHÔNG đính kèm, cờ extension cũ.
    assert proc["requiresCapability"] == "supportsBcaDangKyXe"
    assert proc["hasAttachmentStep"] is False and "bcaPagePhotos" not in proc
    assert hf.get_pipeline(KEY) is registry.get_pipeline(KEY)
    # Khác xe nhập khẩu: ô "Cơ quan giải quyết hồ sơ" hiện sau khi chọn Loại xe → trợ lý tự chọn theo tỉnh (afterPick).
    assert {k: v for k, v in proc["laiChauFeeStep"].items() if k != "caseAgencyByProvince"} == sibling["laiChauFeeStep"]
    assert proc["laiChauFeeStep"]["caseAgencyByProvince"] == {
        "label": "Cơ quan giải quyết hồ sơ", "prefer": "cong an tinh", "afterPick": True}
    for slug in ("khanhhoa", "laichau", "bacninh", "quangninh", ""):
        assert KEY in {p["key"] for p in hf.public_list_for(slug)}, slug
    assert "sang tên xe" in picker.PROCEDURE_HINTS[KEY]
    assert script_mong.PROCEDURE_HMONG[KEY]

    conv = {"state": "greet", "procedure_key": None, "client_capabilities": dict(CAPS),
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Phường Tân Phong"}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert conv["state"] == "guide_login" and r.actions[0]["url"] == proc["keKhaiUrl"]


def _case_conv(**extra):
    caps = {**CAPS, "supportsLaiChauFeeStep": True, "supportsBcaCaseStep": True}
    conv = {"_id": "c-sang-ten", "state": "greet", "procedure_key": None, "client_capabilities": caps,
            "auth_user": {"tinh": "Tỉnh Khánh Hòa", "province_slug": "khanhhoa"},
            "location": {"province": "Tỉnh Khánh Hòa", "province_slug": "khanhhoa", "ward": "Phường Nam Nha Trang"},
            **extra}
    flow._to_confirm_procedure(conv, KEY)
    flow._start_guide_login(conv)
    return conv


def _turn(conv, kind, value, payload=None):
    import asyncio

    from app.channels.handfree.chat.intents import Intent

    return asyncio.run(flow._handle_turn_inner(conv, Intent(kind, value, payload or {})))


LOAI_XE = {"name": "maLoaiXe", "present": True, "value": "Xe máy", "options": ["Xe máy", "Ô tô"],
           "label": "Loại xe", "required": True}
CO_QUAN = {"name": "maCoQuan", "present": True, "value": "", "label": "Cơ quan giải quyết hồ sơ", "required": True,
           "options": ["Công an thành phố Bắc Ninh", "Công an tỉnh Gia Lai", "Công an tỉnh Khánh Hòa"]}


def test_tro_ly_chon_loai_xe_xong_tu_chon_co_quan_theo_tinh():
    """User 20/11/2026 (ảnh chạy thật): chọn xong Loại xe thì tự chọn Cơ quan giải quyết hồ sơ theo tỉnh."""
    conv = _case_conv()
    # Lượt đọc đầu: ô cơ quan chưa hiện → không gửi presets (extension khỏi chờ 6 giây).
    r = _turn(conv, "event", "page_status", {"loggedIn": True, "formKind": "", "lcStep": 1})
    assert r.actions == [{"type": "lc_result_scan", "groups": [{"name": "*"}]}]
    r = _turn(conv, "action", "lc_result_report", {"groups": [{**LOAI_XE, "value": ""}]})
    assert r.cards and conv["state"] == "guide_login"
    # Công dân chọn Xe máy → cổng hiện ô cơ quan còn trống → đọc lại kèm preset tỉnh Khánh Hòa, chưa hiện thẻ.
    r = _turn(conv, "action", "lc_result_report", {"groups": [LOAI_XE, CO_QUAN],
                                                   "changed": {"name": "maLoaiXe", "value": "Xe máy", "ok": True}})
    assert r.actions == [{"type": "lc_result_scan", "groups": [{"name": "*"}], "prepare": False,
                          "presets": [{"label": "Cơ quan giải quyết hồ sơ", "match": "khanh hoa",
                                       "prefer": "cong an tinh"}]}]
    assert "Đã đổi **Loại xe** sang **Xe máy**" in r.display_md and "đang chọn **Cơ quan giải quyết hồ sơ**" in r.display_md
    assert not r.cards
    # Extension chọn xong → thẻ báo đã chọn sẵn, dòng cơ quan chỉ hiện giá trị, có nút Đồng ý và tiếp tục.
    picked = {**CO_QUAN, "value": "Công an tỉnh Khánh Hòa"}
    r = _turn(conv, "action", "lc_result_report", {"groups": [LOAI_XE, picked], "prepared": ["preset:maCoQuan"]})
    assert "Tôi đã chọn sẵn **Cơ quan giải quyết hồ sơ**: **Công an tỉnh Khánh Hòa**" in r.display_md
    rows = {row["name"]: row for row in r.cards[0]["rows"]}
    assert rows["maCoQuan"]["fixed"] is True and r.chips[-1]["send"] == "__action:lc_next"
    # Không chọn được (tỉnh không khớp đúng một mục) → không đọc lại lặp, để công dân chọn trên thẻ.
    conv = _case_conv()
    _turn(conv, "event", "page_status", {"loggedIn": True, "formKind": "", "lcStep": 1})
    changed = {"name": "maLoaiXe", "value": "Xe máy", "ok": True}
    assert _turn(conv, "action", "lc_result_report", {"groups": [LOAI_XE, CO_QUAN], "changed": changed}).actions
    r = _turn(conv, "action", "lc_result_report", {"groups": [LOAI_XE, CO_QUAN], "prepared": []})
    assert r.cards and all(a.get("type") != "lc_result_scan" for a in r.actions)


def test_tro_ly_khong_xin_phep_khi_van_o_trang_chon_truong_hop():
    """Chạy thật 20/11: chọn Loại xe xong trang báo lcStep 0 + formKind "standard" (chưa có form kê khai) → trợ lý xin
    phép xử lý dữ liệu ngay ở trang chọn trường hợp. Chỉ rời trang khi form kê khai CongDan_* đã hiện."""
    conv = _case_conv()
    _turn(conv, "event", "page_status", {"loggedIn": True, "formKind": "", "lcStep": 1})
    r = _turn(conv, "event", "page_status", {"loggedIn": True, "formKind": "standard", "lcStep": 0,
                                             "bcaKeKhaiForm": False})
    assert conv["state"] == "guide_login" and conv["lai_chau"]["at"] == 1 and not r.cards
    # Trang nhập thông tin thật (ô CongDan_* hiện) → luồng chung xin phép / nhận giấy tờ như cũ.
    _turn(conv, "event", "page_status", {"loggedIn": True, "formKind": "standard", "lcStep": 0, "bcaKeKhaiForm": True})
    assert conv["lai_chau"]["at"] == 0 and conv["state"] in ("consent", "ask_doc_method")
