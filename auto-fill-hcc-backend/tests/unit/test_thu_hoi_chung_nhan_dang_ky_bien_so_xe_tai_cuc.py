"""Thu hồi chứng nhận đăng ký xe, biển số xe tại Cục 2.000311 (Cổng DVC Bộ Công an): mapper ô form theo file
mapping "Mapping_Thu_hoi_CNDK_BSX" (cùng mẫu 2.001485; chủ xe tự nộp / người khai hộ) + nối registry / link kê khai / trợ lý."""
from app.pipelines.thu_hoi_chung_nhan_dang_ky_bien_so_xe_tai_cuc.process import mapper
from app.pipelines.thu_hoi_chung_nhan_dang_ky_bien_so_xe_tai_cuc.process.schema import (
    ALLOWED,
    LY_DO_THU_HOI,
    UI_COMP_BY_NAME,
)
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

KEY = "thu-hoi-chung-nhan-dang-ky-bien-so-xe-tai-cuc"
CAP_TINH = "thu-hoi-chung-nhan-dang-ky-bien-so-xe-cap-tinh"
SIBLING = "dang-ky-sang-ten-di-chuyen-xe-cap-tinh"
# Hồ sơ mẫu bịa theo bộ giấy của file mapping: Giấy ĐKX (chụp mất đầu số khung, không thấy số máy) + hợp đồng mua bán
# có lời chứng (bên bán hai vợ chồng) + thẻ căn cước của chủ xe và của bên mua.
HO_SO = {
    "Dkx_TenChuXe": "TRẦN VĂN BÌNH", "Dkx_BienSo": "00A-000.00", "Dkx_MauBien": "(T)", "Dkx_LoaiXe": "Ô tô con",
    "Dkx_NhanHieu": "Hyundai", "Dkx_SoLoai": "ACCENT1.", "Dkx_SoKhung": "0CD0E000001", "Dkx_DungTich": "1368",
    "Dkx_SoChoNgoi": "5",
    "Hdmb_TenVanBan": "HỢP ĐỒNG MUA BÁN XE Ô TÔ",
    "Hdmb_BenBanHoTen": "TRẦN VĂN BÌNH", "Hdmb_BenBanSoCccd": "001080000009", "Hdmb_BenBanNgaySinh": "1/2/1980",
    "Hdmb_BenBanNgayCapCccd": "11/03/2021", "Hdmb_BenBanNoiCapCccd": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "Hdmb_BenBanDiaChi": {"tinh": "tỉnh Lai Châu", "xa": "phường Tân Phong", "chiTietDuoiXa": "Tổ 1"},
    "Hdmb_BenMuaHoTen": "NGUYỄN VĂN AN", "Hdmb_BenMuaSoCccd": "001090000001", "Hdmb_BenMuaNgayCapCccd": "09/05/2021",
    "Hdmb_BenMuaNoiCapCccd": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "Hdmb_BenMuaDiaChi": {"tinh": "tỉnh Lai Châu", "xa": "xã Pắc Ta", "chiTietDuoiXa": "Bản Một"},
    "Hdmb_BienSo": "00A-000.00", "Hdmb_LoaiXe": "Ô tô con", "Hdmb_NhanHieu": "HYUNDAI", "Hdmb_SoLoai": "ACCENT1",
    "Hdmb_SoKhung": "MK2AB00CD0E000001", "Hdmb_SoMay": "G4AB000001", "Hdmb_DungTich": "1368 cm3",
    "Hdmb_SoChoNgoi": "5",
    "Cccd_HoTen": "TRẦN VĂN BÌNH", "Cccd_SoDinhDanh": "0010 8000 0009", "Cccd_NgaySinh": "01/02/1980",
    "Cccd_QuocTich": "Việt Nam", "Cccd_NgayCap": "11/3/2021",
    "Cccd_NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    "Cccd_NoiCuTru": {"tinh": "Lai Châu", "xa": "Phường Tân Phong", "chiTietDuoiXa": "Tổ 1"},
    "CccdChuMoi_HoTen": "NGUYỄN VĂN AN", "CccdChuMoi_SoDinhDanh": "001090000001",
}
# Cổng tích sẵn "Người nộp hồ sơ là chủ xe" và khoá ô chủ xe theo tài khoản; Auto Fill / trợ lý gửi qua formContext.
OWNER_ACCOUNT = {"formContext": {"applicantFullname": "TRẦN VĂN BÌNH", "applicantIdentityNumber": "001080000009"}}
BUYER_ACCOUNT = {"formContext": {"applicantFullname": "NGUYỄN VĂN AN", "applicantIdentityNumber": "001090000001"}}
OTHER_ACCOUNT = {"formContext": {"applicantFullname": "LÊ VĂN CƯỜNG", "applicantIdentityNumber": "001095000003"}}


def _enrich(values: dict, options=None):
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def _by(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_chu_xe_tu_nop_dien_tra_cuu_chu_xe_chu_moi_va_thong_tin_xe_theo_mapping():
    assert set(HO_SO) <= ALLOWED
    out, warnings = _enrich(HO_SO, OWNER_ACCOUNT)
    by = _by(out)
    names = [f["name"] for f in out]
    # Phần I + khối tra cứu đứng đầu, Ô tô / Xe máy trước (đổi ô này cổng xoá dữ liệu tra cứu).
    assert names[:7] == ["CongDan__fsLaChuXe", "CongDan__fsRadioLoaiXe", "CongDan__fstracuuBienSo",
                         "CongDan__fstracuuMauBien", "CongDan__fstracuuSoMay", "CongDan__fstracuuSoKhung",
                         "CongDan__fslyDoThuHoi"]
    assert by["CongDan__fsLaChuXe"] is True and "CongDan__fsLaNguoiKhaiHo" not in by
    # Biển số nhập liền; "(T)" sau nhãn biển số = nền trắng; số khung Giấy ĐKX bị cắt → lấy bản đủ của hợp đồng.
    assert by["CongDan__fsRadioLoaiXe"] == "Ô tô" and by["CongDan__fstracuuBienSo"] == "00A00000"
    assert by["CongDan__fstracuuMauBien"] == "Nền màu trắng, chữ và số màu đen"
    assert by["CongDan__fstracuuSoKhung"] == "MK2AB00CD0E000001" and by["CongDan__fstracuuSoMay"] == "G4AB000001"
    assert by["CongDan__fslyDoThuHoi"] == "Chuyển quyền sở hữu"
    # Chủ xe tự nộp: ô khoá theo tài khoản, captcha, điểm đăng ký, ô ẩn, khối người làm thủ tục KHÔNG phát.
    assert not {"CongDan_soCmnd", "CongDan_tenCongDan", "CongDan__fsnamSinh", "CongDan__fsmaXacNhan",
                "CongDan_btnTracuuTTXe", "CongDan__fsDDKTenDiemDK", "CongDan__fsMaDiemDangKyXe",
                "CongDan__fsBCAHKTTHuyen", "CongDan__fsBCATamTruTinh", "CongDan__fsBCANoiOHienTai",
                "CongDan__fsLoaiXe", "CongDan__fsDanhDauSeri"} & set(by)
    assert not [n for n in by if "NDUQ" in n]
    # Phần III theo thẻ chủ xe (ngày cấp in trên thẻ, không để ngày cập nhật cổng đổ sẵn).
    assert by["CongDan__fsLoaiGiayToChuXe"] == "Căn cước công dân" and by["CongDan__fsngayCapCmnd"] == "11/03/2021"
    assert by["CongDan__fsnoiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert by["CongDan__fsQuocTichChuXe"] == "Việt Nam"
    assert by["CongDan__fsBCAHKTTTinh"] == "Tỉnh Lai Châu" and by["CongDan__fsBCAHKTTXa"] == "Phường Tân Phong"
    assert by["CongDan__fsBCAHKTTDCChiTiet"] == "Tổ 1"
    assert names.index("CongDan__fsBCAHKTTTinh") < names.index("CongDan__fsBCAHKTTXa")
    assert next(f for f in out if f["name"] == "CongDan__fsBCAHKTTXa")["waitMs"] == 8000
    # Giấy tờ không có SĐT chủ xe (SĐT văn phòng công chứng không lấy) → không phát, cảnh báo.
    assert "CongDan_diDong" not in by and any("số điện thoại chủ xe" in w for w in warnings)
    # Phần V: chủ xe mới = bên mua, địa chỉ một ô ghi đủ theo địa giới mới.
    assert by["CongDan__fsChuMoiHoTen"] == "NGUYỄN VĂN AN" and by["CongDan__fsChuMoiMaDinhDanh"] == "001090000001"
    assert by["CongDan__fsChuMoiDiaChi"] == "Bản Một, Xã Pắc Ta, Tỉnh Lai Châu"
    assert any("Thông tin chủ xe mới" in w and "Số điện thoại" in w and "Họ và tên" not in w for w in warnings)
    # Phần VI theo Giấy ĐKX → hợp đồng; Loại xe (JS tự gán) không phát; thiếu Năm sản xuất → cảnh báo.
    assert by["CongDan__fsnhanHieu"] == "HYUNDAI" and by["CongDan__fssoLoai"] == "ACCENT1"
    assert by["CongDan__fsSoMay1"] == "G4AB000001" and by["CongDan__fsSoKhung"] == "MK2AB00CD0E000001"
    assert by["CongDan__fsDungTich"] == "1368" and by["CongDan__fsSoChoNgoi"] == "5"
    assert not {"CongDan__fsNamSanXuat", "CongDan__fstrongTai", "CongDan__fsSoChoDung"} & set(by)
    assert any("Năm sản xuất" in w for w in warnings)
    # Nhận kết quả: người nhận = chủ xe, Tỉnh trước Xã; hình thức không ghi → chọn tay.
    assert "CongDan__fsHinhThucNhanKQ" not in by and any("hình thức nhận kết quả" in w for w in warnings)
    assert by["CongDan__fsTenNguoiNhanKQ"] == "TRẦN VĂN BÌNH"
    assert by["CongDan__fsTinhNhanKQ"] == "Tỉnh Lai Châu" and by["CongDan__fsXaNhanKQ"] == "Phường Tân Phong"
    assert all(f["comp"] == UI_COMP_BY_NAME[f["name"]] for f in out)
    assert mapper.NO_ACCOUNT_WARNING not in warnings and warnings[-1] == mapper.TRA_CUU_WARNING
    assert not any("Không đọc được" in w or "Số khung chỉ đọc được" in w for w in warnings)
    # Giấy khai thu hồi có SĐT / email → phát, ô của chủ tài khoản giữ giá trị cổng.
    by_out = _enrich({**HO_SO, "ToKhai_DienThoai": "0912.345.678", "ToKhai_Email": "tranbinh,80@gmail,com",
                      "Dkx_NamSanXuat": "Sản xuất năm 2019"}, OWNER_ACCOUNT)[0]
    by = _by(by_out)
    assert by["CongDan_diDong"] == "0912345678" and by["CongDan_email"] == "tranbinh.80@gmail.com"
    assert by["CongDan__fsSoDienThoaiNguoiNhan"] == "0912345678" and by["CongDan__fsNamSanXuat"] == "2019"
    assert next(f for f in by_out if f["name"] == "CongDan_diDong")["keepPortalValue"] is True


def test_tai_khoan_la_ben_mua_thi_tich_khai_ho_va_dien_o_chu_xe():
    out, warnings = _enrich(HO_SO, BUYER_ACCOUNT)
    by = _by(out)
    assert out[0]["name"] == "CongDan__fsLaNguoiKhaiHo" and "CongDan__fsLaChuXe" not in by
    # Ô chủ xe cổng mở khi khai hộ → nhập theo giấy của chủ xe (bên bán), không theo tài khoản.
    assert by["CongDan_soCmnd"] == "001080000009" and by["CongDan_tenCongDan"] == "TRẦN VĂN BÌNH"
    assert by["CongDan__fsnamSinh"] == "01/02/1980"
    # Khối người làm thủ tục = tài khoản (bên mua), ngày cấp / cơ quan cấp theo hợp đồng.
    assert by["CongDan__fsNDUQHoTen"] == "NGUYỄN VĂN AN" and by["CongDan__fsNDUQMaDinhDanh"] == "001090000001"
    assert by["CongDan__fsNDUQLoaiGiayTo"] == "Căn cước công dân" and by["CongDan__fsNDUQNgayCap"] == "09/05/2021"
    assert by["CongDan__fsNDUQCoQuanCap"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert any("bên mua" in w for w in warnings) and not any("văn bản ủy quyền" in w for w in warnings)
    assert any("còn thiếu Số điện thoại" in w for w in warnings)
    names = [f["name"] for f in out]
    assert names.index("CongDan_tenCongDan") < names.index("CongDan__fsNDUQHoTen")
    # Khai hộ: ô liên hệ của tài khoản là khối người làm thủ tục, không phải ô của chủ xe.
    out = _enrich({**HO_SO, "ToKhai_DienThoai": "0912345678"}, BUYER_ACCOUNT)[0]
    assert not next(f for f in out if f["name"] == "CongDan_diDong").get("keepPortalValue")


def test_nguoi_khac_lam_thay_co_giay_uy_quyen_va_khong_doc_duoc_tai_khoan():
    values = {**HO_SO, "UyQuyen_BenUyQuyenHoTen": "Trần Văn Bình", "UyQuyen_HoTen": "Lê Văn Cường",
              "UyQuyen_SoDinhDanh": "001095000003", "UyQuyen_DienThoai": "0987654321",
              "CccdNduq_HoTen": "LÊ VĂN CƯỜNG", "CccdNduq_SoDinhDanh": "001095000003", "CccdNduq_NgayCap": "15/8/2024",
              "CccdNduq_NoiCap": "BỘ CÔNG AN"}
    assert set(values) <= ALLOWED
    out, warnings = _enrich(values, OTHER_ACCOUNT)
    by = _by(out)
    assert by["CongDan__fsLaNguoiKhaiHo"] is True
    assert by["CongDan__fsNDUQHoTen"] == "LÊ VĂN CƯỜNG" and by["CongDan__fsNDUQNgayCap"] == "15/08/2024"
    assert by["CongDan__fsNDUQCoQuanCap"] == "Bộ Công an" and by["CongDan__fsDiDongNDUQ"] == "0987654321"
    assert next(f for f in out if f["name"] == "CongDan__fsDiDongNDUQ")["keepPortalValue"] is True
    assert any("văn bản ủy quyền" in w for w in warnings) and not any("còn thiếu" in w and "Cơ quan" in w
                                                                       for w in warnings)
    # Không đọc được tài khoản: có giấy ủy quyền → khai hộ theo giấy; không có → chủ xe tự nộp + cảnh báo.
    by = _by(_enrich(values)[0])
    assert by["CongDan__fsLaNguoiKhaiHo"] is True and by["CongDan__fsNDUQHoTen"] == "LÊ VĂN CƯỜNG"
    out, warnings = _enrich(HO_SO)
    assert _by(out)["CongDan__fsLaChuXe"] is True and mapper.NO_ACCOUNT_WARNING in warnings
    # Tài khoản OCR lệch số mà trùng tên vẫn là chủ xe.
    near = {"formContext": {"applicantFullname": "Trần Văn Bình", "applicantIdentityNumber": "001080000007"}}
    assert _by(_enrich(HO_SO, near)[0])["CongDan__fsLaChuXe"] is True


def test_the_can_cuoc_xep_nham_vai_va_ben_ban_khac_chu_xe():
    # Chỉ có thẻ của bên mua mà LLM trả vào Cccd_* → xếp lại sang chủ xe mới; chủ xe lấy theo hợp đồng (bên bán).
    values = {k: v for k, v in HO_SO.items() if not k.startswith(("Cccd_", "CccdChuMoi_"))}
    values.update({"Cccd_HoTen": "NGUYỄN VĂN AN", "Cccd_SoDinhDanh": "001090000001",
                   "Cccd_NoiCuTru": {"tinh": "Lai Châu", "xa": "Xã Pắc Ta", "chiTietDuoiXa": "Bản Hai"}})
    by = _by(_enrich(values, OWNER_ACCOUNT)[0])
    assert by["CongDan__fsBCAHKTTXa"] == "Phường Tân Phong" and by["CongDan__fsngayCapCmnd"] == "11/03/2021"
    assert by["CongDan__fsChuMoiDiaChi"] == "Bản Hai, Xã Pắc Ta, Tỉnh Lai Châu"
    # Thẻ của vợ cùng đứng bên bán không phải thẻ chủ xe.
    values.update({"Cccd_HoTen": "LÊ THỊ HOA", "Cccd_SoDinhDanh": "001185000002", "Cccd_NgayCap": "01/01/2024"})
    by = _by(_enrich(values, OWNER_ACCOUNT)[0])
    assert by["CongDan__fsngayCapCmnd"] == "11/03/2021" and by["CongDan__fsTenNguoiNhanKQ"] == "TRẦN VĂN BÌNH"
    # Bên bán khác người đứng tên Giấy ĐKX → không lấy thông tin bên bán cho chủ xe, cảnh báo.
    values = {**HO_SO, "Hdmb_BenBanHoTen": "PHẠM VĂN DŨNG", "Hdmb_BenBanSoCccd": "001075000004"}
    values = {k: v for k, v in values.items() if not k.startswith("Cccd_")}
    out, warnings = _enrich(values, OWNER_ACCOUNT)
    by = _by(out)
    assert "CongDan__fsngayCapCmnd" not in by and "CongDan__fsBCAHKTTTinh" not in by
    assert by["CongDan__fsTenNguoiNhanKQ"] == "TRẦN VĂN BÌNH" and any("PHẠM VĂN DŨNG" in w for w in warnings)


def test_ly_do_thu_hoi_mau_bien_bien_so_va_so_khung():
    reason = mapper._reason
    assert reason("Chuyển quyền sở hữu") == LY_DO_THU_HOI["chuyen_quyen"]
    assert reason("Bán xe cho người khác") == LY_DO_THU_HOI["chuyen_quyen"]
    assert reason("Sang tên kèm theo biển trúng đấu giá") == LY_DO_THU_HOI["sang_ten_dau_gia"]
    assert reason("Di chuyển đi tỉnh khác") == LY_DO_THU_HOI["di_chuyen"]
    assert reason("Xe bị hỏng không sử dụng được") == LY_DO_THU_HOI["hong"]
    assert reason("Xe hết niên hạn sử dụng") == LY_DO_THU_HOI["nien_han"]
    assert reason("Xe bị mất cắp") == LY_DO_THU_HOI["mat_cap"]
    assert reason("Xe tạm nhập tái xuất") == LY_DO_THU_HOI["mien_thue"]
    assert reason("Không có") is None and reason(None) is None
    assert mapper._plate("Biển số: 25b1 - 000.01") == "25B100001" and mapper._plate("(T)") is None
    assert mapper._plate_color_dkx("T") == "Nền màu trắng, chữ và số màu đen"
    assert mapper._plate_color_dkx("(V)") == "Nền màu vàng, chữ và số màu đen"
    assert mapper._plate_color_dkx("Nền màu xanh, chữ và số màu trắng") == "Nền màu xanh, chữ và số màu trắng"
    assert mapper._plate_color_dkx("Trắng (màu sơn)") == "Nền màu trắng, chữ và số màu đen"
    assert mapper._plate_color_dkx(None) is None
    assert mapper._vin("…0CD0E000001", "MK2AB00CD0E000001") == ("MK2AB00CD0E000001", False)
    assert mapper._vin("MK2AB00CD0E000001", "MK2AB00CD0E999999") == ("MK2AB00CD0E000001", True)
    # Giấy khai thu hồi ghi lý do không cần chủ mới → không cảnh báo khối chủ xe mới; xe máy biển vàng.
    values = {"Dkx_TenChuXe": "TRẦN VĂN BÌNH", "Dkx_BienSo": "25B1-000.01", "Dkx_MauBien": "Nền vàng chữ đen",
              "Dkx_LoaiXe": "Xe mô tô hai bánh", "Dkx_SoKhung": "RLH000000000001", "Dkx_SoMay": "JF00E0000001",
              "ToKhai_LyDoThuHoi": "Xe hỏng không sử dụng được", "HoSo_HinhThucNhanKetQua": "Qua bưu điện"}
    out, warnings = _enrich(values, OWNER_ACCOUNT)
    by = _by(out)
    assert by["CongDan__fsRadioLoaiXe"] == "Xe máy" and by["CongDan__fslyDoThuHoi"] == LY_DO_THU_HOI["hong"]
    assert by["CongDan__fstracuuMauBien"] == "Nền màu vàng, chữ và số màu đen"
    assert by["CongDan__fsHinhThucNhanKQ"] == "Qua bưu điện, tại nhà"
    assert not [n for n in by if "ChuMoi" in n] and not any("chủ xe mới" in w for w in warnings)
    # Di chuyển bắt buộc khối chủ xe mới mà giấy tờ không có → cảnh báo đủ bốn ô.
    warnings = _enrich({**values, "ToKhai_LyDoThuHoi": "Di chuyển"}, OWNER_ACCOUNT)[1]
    assert any("Họ và tên" in w and "Mã định danh" in w and "Số điện thoại" in w for w in warnings)
    # Thiếu ô tra cứu / không rõ lý do → cảnh báo; số khung ô tô chỉ có phần bị cắt → nhắc đối chiếu.
    values = {"Dkx_TenChuXe": "TRẦN VĂN BÌNH", "Dkx_LoaiXe": "Ô tô con", "Dkx_SoKhung": "0CD0E000001",
              "Dkx_BienSo": "00A-000.00", "Dkx_MauBien": "T"}
    out, warnings = _enrich(values, OWNER_ACCOUNT)
    assert "CongDan__fslyDoThuHoi" not in _by(out) and any("Lý do thu hồi" in w for w in warnings)
    assert any("Số khung chỉ đọc được 11 ký tự" in w for w in warnings)
    warnings = _enrich({"Dkx_TenChuXe": "TRẦN VĂN BÌNH"}, OWNER_ACCOUNT)[1]
    assert any("Ô tô / Xe máy" in w and "Biển số" in w and "Màu biển" in w and "Số khung" in w for w in warnings)


def test_runner_tra_canh_bao(monkeypatch):
    import asyncio

    from app.pipelines._shared.compact_agent import runner as compact_runner
    from app.pipelines.thu_hoi_chung_nhan_dang_ky_bien_so_xe_tai_cuc.process import runner as xe_runner

    async def fake_run(*_args, **_kwargs):
        return {"fields": [{"name": k, "value": v} for k, v in HO_SO.items()]}

    monkeypatch.setattr(compact_runner, "run", fake_run)
    res = asyncio.run(xe_runner.run({}, BUYER_ACCOUNT))
    assert _by(res["fields"])["CongDan__fsLaNguoiKhaiHo"] is True and "blocked" not in res
    assert res["errors"][-1] == mapper.TRA_CUU_WARNING


def test_registry_link_va_detect():
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is None
    proc = registry.get_procedure(KEY)
    assert proc["hasAttachmentStep"] is False and proc["mode"] == "agent" and proc["collectFormContext"] is True
    assert proc["detect"]["urlScope"] == ["dichvucong.bocongan.gov.vn"] and proc["detect"]["codeOnPage"] is True
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "2.000311" and link["url"].endswith("tthc?matt=26125")
    assert link["directSubmit"] is True and link["bcaSubmit"] is True and link["label"] == proc["label"]
    public = next(p for p in with_ke_khai_detect_urls([proc]) if p["key"] == KEY)
    assert link["url"] in public["detect"]["urlIncludes"] and "matthc=2.000311" in public["detect"]["urlIncludes"]
    # Nhãn "Lý do thu hồi" + tiêu đề Phần V "THÔNG TIN CHÙ XE MỚI" (cổng viết sai dấu; extension so khớp bỏ dấu).
    from app.pipelines._shared import fold

    page = fold("Lý do thu hồi … THÔNG TIN CHÙ XE MỚI ( nếu có )")
    assert all(fold(p) in page for p in proc["detect"]["textIncludes"])
    # Trang sang tên (chú thích Phần I) không chứa đủ cụm của thu hồi và ngược lại.
    sang_ten = registry.get_procedure(SIBLING)["detect"]["textIncludes"]
    assert not all(p in "trước khi sang tên bắt buộc phải thu hồi" for p in proc["detect"]["textIncludes"])
    assert not all(fold(p) in page for p in sang_ten)


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
    for field in ("requiresCapability", "hasAttachmentStep", "flowProfile", "bcaPortal", "agencyDirectSubmit",
                  "provinceOnly"):
        assert proc.get(field) == sibling.get(field), field
    # Không tự chọn Cơ quan giải quyết theo tỉnh như bản cấp tỉnh: khuôn trang chọn trường hợp như xe nhập khẩu.
    assert proc["laiChauFeeStep"] == hf.get_procedure("dang-ky-xe-lan-dau-nhap-khau")["laiChauFeeStep"]
    assert "caseAgencyByProvince" not in proc["laiChauFeeStep"]
    assert hf.get_pipeline(KEY) is registry.get_pipeline(KEY)
    for slug in ("khanhhoa", "laichau", "bacninh", "quangninh", ""):
        assert KEY in {p["key"] for p in hf.public_list_for(slug)}, slug
    assert any("Cục CSGT" in hint for hint in picker.PROCEDURE_HINTS[KEY])
    assert script_mong.PROCEDURE_HMONG[KEY]

    conv = {"state": "greet", "procedure_key": None, "client_capabilities": dict(CAPS),
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Phường Tân Phong"}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert conv["state"] == "guide_login" and r.actions[0]["url"] == proc["keKhaiUrl"]


def test_pipeline_rieng_khong_dung_chung_ban_cap_tinh():
    """User 20/11/2026: "làm ra 2 folder mới, không dùng chung" — không module nào import pipeline thu hồi cấp tỉnh, và
    registry trỏ đúng pipeline của thư mục này."""
    import pathlib

    from app.pipelines.thu_hoi_chung_nhan_dang_ky_bien_so_xe_tai_cuc.process import run

    folder = pathlib.Path(mapper.__file__).resolve().parents[1]
    assert folder.name == "thu_hoi_chung_nhan_dang_ky_bien_so_xe_tai_cuc"
    for path in folder.rglob("*.py"):
        assert "thu_hoi_chung_nhan_dang_ky_bien_so_xe_cap_tinh" not in path.read_text(encoding="utf-8"), path
    assert registry.get_pipeline(KEY) is run
    assert registry.get_pipeline(KEY) is not registry.get_pipeline(CAP_TINH)
    # Cùng mẫu kê khai → cùng ô form và cùng detect với bản cấp tỉnh.
    from app.pipelines.thu_hoi_chung_nhan_dang_ky_bien_so_xe_cap_tinh.process import schema as cap_tinh_schema

    assert UI_COMP_BY_NAME == cap_tinh_schema.UI_COMP_BY_NAME and ALLOWED == cap_tinh_schema.ALLOWED
    assert registry.get_procedure(KEY)["detect"] == registry.get_procedure(CAP_TINH)["detect"]
