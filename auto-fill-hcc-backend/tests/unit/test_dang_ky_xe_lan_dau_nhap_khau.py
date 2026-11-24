"""Đăng ký xe lần đầu toàn trình — xe nhập khẩu 1.013066 (Cổng DVC Bộ Công an): mapper ô form theo file mapping
"Mapping_DK_xe_lan_dau_nhap_khau_1.013066" + nối registry / link kê khai / trợ lý."""
from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process import mapper
from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

KEY = "dang-ky-xe-lan-dau-nhap-khau"
SIBLING = "dang-ky-xe-lan-dau-san-xuat-lap-rap-trong-nuoc"
# Hồ sơ mẫu bịa theo bộ giấy của file mapping: GCN thu hồi + hợp đồng mua bán + dữ liệu LPTB + thẻ của chủ xe mới.
HO_SO = {
    "Cccd_HoTen": "NGUYỄN VĂN AN", "Cccd_SoDinhDanh": "0010 9000 0001", "Cccd_GioiTinh": "Nam",
    "Cccd_QuocTich": "Việt Nam", "Cccd_NgayCap": "6/4/2021",
    "Cccd_NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    "Cccd_NoiCuTru": {"tinh": "Lai Châu", "xa": "Xã Pắc Ta", "chiTietDuoiXa": "Bản Một"},
    "GcnThuHoi_ChuXe": "TRẦN VĂN BÌNH", "GcnThuHoi_DiaChiChuXe": "Bản Hai, Pa Tần, Lai Châu",
    "GcnThuHoi_ChuMoiHoTen": "NGUYỄN VĂN AN", "GcnThuHoi_ChuMoiMaDinhDanh": "001090000001",
    "GcnThuHoi_ChuMoiDienThoai": "00000000000",
    "GcnThuHoi_ChuMoiDiaChi": {"tinh": "Tỉnh Lai Châu", "xa": "Xã Pắc Ta", "chiTietDuoiXa": "BẢN MỘT"},
    "Hdmb_SoCongChung": "0001/2026/CCGD", "Hdmb_NgayKy": "4/11/2026",
    "Hdmb_MoTaXe": "chiếc xe ô tô mang nhãn hiệu: HIEUXE, số loại MX GLP, mang biển số đăng ký: 00A-000.00",
    "Hdmb_GiaMuaBan": "100.000.000", "Hdmb_GiaBangChu": "Một trăm triệu đồng chẵn",
    "Hdmb_BenBanHoTen": "TRẦN VĂN BÌNH", "Hdmb_BenBanDiaChi": "Bản Hai, xã Pa Tần, tỉnh Lai Châu.",
    "Hdmb_BenMuaHoTen": "NGUYỄN VĂN AN", "Hdmb_BenMuaDanhXung": "Ông", "Hdmb_BenMuaSoCccd": "001090000001",
    "Hdmb_BenMuaNgayCapCccd": "06/04/2021",
    "Hdmb_BenMuaNoiCapCccd": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    "Hdmb_BenMuaDiaChi": {"tinh": "tỉnh Lai Châu", "xa": "xã Pắc Ta", "chiTietDuoiXa": "Bản Một"},
    "Lptb_MaHoSo": "11200000000001", "Lptb_NgayNop": "10/11/2026", "Lptb_CoQuanThue": "Thuế cơ sở 2 tỉnh Lai Châu",
    "Lptb_TenNguoiNop": "Nguyễn Văn An", "Lptb_MaDinhDanh": "001090000001", "Lptb_DienThoai": "0912 345 678",
    "Lptb_DiaChi": "Bản Một, Xã Pắc Ta, Tỉnh Lai Châu", "Lptb_NhanHieu": "HIEUXE", "Lptb_SoLoai": "MX GLP (AB12CDEF)",
    "Lptb_NamSanXuat": "2022", "Lptb_SoMay": "4A00KBA0001", "Lptb_SoKhung": "MK2000000000001",
    "Lptb_DungTich": "1500 cm³", "Lptb_TrongTai": "0 kg", "Lptb_SoChoNgoi": "7", "Lptb_GiaTriTinh": "282000000",
    "Lptb_SoTien": "5640000",
    "Xe_LoaiXe": "Ô tô con", "Xe_NhanHieu": "HIEUXE", "Xe_SoLoai": "MX GLP", "Xe_MauSon": "Xám, Bạc",
    "Xe_SoKhung": "MK2000000000001", "Xe_SoMay": "4A00KBA0001", "Xe_NamSanXuat": "2022", "Xe_DungTich": "1499",
    "Xe_SoChoNgoi": "7", "Xe_SoChoDung": "……", "Xe_CongSuat": "………",
}


def _enrich(values: dict, options=None):
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def _by(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_ho_so_theo_mapping_dien_tra_cuu_chu_xe_lptb_hoa_don_theo_hop_dong_va_xe():
    assert set(HO_SO) <= ALLOWED
    out, warnings = _enrich(HO_SO)
    by = _by(out)
    names = [f["name"] for f in out]
    # Khối tra cứu đứng đầu: Ô tô / xe máy, Số khung, Mã hồ sơ LPTB.
    assert names[:3] == ["CongDan__fsRadioLoaiXe", "CongDan__fstracuuSoKhung", "CongDan__fsTraCuMaHsLPTB"]
    assert by["CongDan__fsRadioLoaiXe"] == "Ô tô" and by["CongDan__fstracuuSoKhung"] == "MK2000000000001"
    assert by["CongDan__fsTraCuMaHsLPTB"] == "11200000000001"
    # Phần I: ô readonly CSDL dân cư / ô khoá / captcha KHÔNG phát.
    assert not {"CongDan_soCmnd", "CongDan_tenCongDan", "CongDan__fsnamSinh", "CongDan__fsBCAHKTTTinh",
                "CongDan__fsBCAHKTTXa", "CongDan__fsBCAHKTTDCChiTiet", "CongDan__fsBCANoiOHienTaiTinh",
                "CongDan__fstracuuKieuNhap", "CongDan__fsmaXacNhan", "CongDan__fsSeriChatLuongXuatXuong",
                "CongDan__fsSoSeriKTCLXX", "CongDan__fsDDKLoaiDiaChiDKX", "CongDan__fsDiaChiDangKyXe"} & set(by)
    assert by["CongDan__fs_BCAGioiTinhCd"] == "Nam" and by["CongDan__fsLoaiGiayToChuXe"] == "Căn cước công dân"
    assert by["CongDan__fsngayCapCmnd"] == "06/04/2021"
    assert by["CongDan__fsnoiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert by["CongDan__fsQuocTichChuXe"] == "Việt Nam"
    # SĐT theo giấy LPTB (GCN thu hồi ghi dãy 0 giả); email không có → cảnh báo. Ô của chủ tài khoản giữ giá trị cổng.
    assert by["CongDan_diDong"] == "0912345678" and "CongDan_email" not in by
    assert next(f for f in out if f["name"] == "CongDan_diDong")["keepPortalValue"] is True
    # Phần III đúng như giấy LPTB in: số loại kèm mã, dung tích 1500, tiền chỉ chữ số, bằng chữ tự đọc.
    assert by["CongDan__fsMaHsLPTBDienTu"] == "11200000000001" and by["CongDan__fsNgayCapLPTB"] == "10/11/2026"
    assert by["CongDan__fsCoQuanCapLPTB"] == "Thuế cơ sở 2 tỉnh Lai Châu"
    assert by["CongDan__fsCMNDNguoiNopThueLPTB"] == "001090000001"
    assert by["CongDan__fsTenNguoiNopThue"] == "Nguyễn Văn An" and by["CongDan__fsSDTNguoiNopThue"] == "0912345678"
    assert by["CongDan__fsDiaChiNguoiNopThue"] == "Bản Một, Xã Pắc Ta, Tỉnh Lai Châu"
    assert by["CongDan__fsLoaiXe"] == "Ô tô con" and by["CongDan__fssoLoai"] == "MX GLP (AB12CDEF)"
    assert by["CongDan__fsDungTich"] == "1500 cm³" and "CongDan__fsCongSuat" not in by
    assert by["CongDan__fsSoTienLPTB"] == "5640000" and by["CongDan__fsGiaTriTinhLPTB"] == "282000000"
    assert by["CongDan__fsSoTienBangChuLPTB"] == "Năm triệu sáu trăm bốn mươi nghìn đồng"
    assert "CongDan__fsMSTnguoiNopThueLPTB" not in by and "CongDan__fsCanCuMienThuLPTB" not in by
    # Phần IV: không có hóa đơn → tương đương theo hợp đồng mua bán (mapping), có cảnh báo.
    assert by["CongDan__fsSoHoaDon"] == "0001/2026/CCGD" and by["CongDan__fsHDDTNgayCap"] == "04/11/2026"
    assert by["CongDan__fsTenHangHoa"].startswith("chiếc xe ô tô mang nhãn hiệu: HIEUXE")
    assert by["CongDan__fsDonViBanHang"] == "TRẦN VĂN BÌNH"
    assert by["CongDan__fsDiaChiNguoiBan"] == "Bản Hai, xã Pa Tần, tỉnh Lai Châu"
    assert by["CongDan__fsHoTenNguoiMua"] == "NGUYỄN VĂN AN" and by["CongDan__fsMSTNguoiMua"] == "001090000001"
    assert by["CongDan__fsDiaChiNguoiMua"] == "Bản Một, Xã Pắc Ta, Tỉnh Lai Châu"
    assert by["CongDan__fsTongCongTienThanhToan"] == "100.000.000 đồng"
    assert by["CongDan__fsTongCongTienThanhToanBangChu"] == "Một trăm triệu đồng chẵn"
    assert not {"CongDan__fsLoaiHoaDon", "CongDan__fsKyHieu", "CongDan__fsHDDTMauSoHoaDon", "CongDan__fsMSTNguoiBan",
                "CongDan__fsTienthue"} & set(by)
    assert mapper.HOA_DON_THEO_HOP_DONG_WARNING in warnings
    # Phần V theo giấy đăng ký (GCN thu hồi): số loại không mã, dung tích 1499, màu sơn theo hợp đồng.
    assert by["CongDan__fsnhanHieuDK"] == "HIEUXE" and by["CongDan__fsSoLoaiDK"] == "MX GLP"
    assert by["CongDan__fsMauSonDK"] == "Xám, Bạc" and by["CongDan__fsDungTichXiLanhDK"] == "1499"
    assert by["CongDan__fsSoKhungDK"] == "MK2000000000001" and by["CongDan__fsSoMay1DK"] == "4A00KBA0001"
    assert by["CongDan__fsLoaiXeDK"] == "Ô tô con" and by["CongDan__fsTrongTaiDK"] == "0"
    assert by["CongDan__fsSoChoNgoiDK"] == "7" and "CongDan__fsSoChoDungDK" not in by
    assert not {"CongDan__fsSoMay2DK", "CongDan__fsCoQuanHaiQuanDK", "CongDan__fsCongSuatDK"} & set(by)
    # Phần VII: người nhận = chủ xe, địa chỉ theo hợp đồng (địa giới mới); Tỉnh trước Xã.
    assert "CongDan__fsHinhThucNhanKQ" not in by
    assert by["CongDan__fsTenNguoiNhanKQ"] == "NGUYỄN VĂN AN" and by["CongDan__fsSoDienThoaiNguoiNhan"] == "0912345678"
    assert by["CongDan__fsTinhNhanKQ"] == "Tỉnh Lai Châu" and by["CongDan__fsXaNhanKQ"] == "Xã Pắc Ta"
    assert by["CongDan__fsDiaChiChiTietNhanKQ"] == "Bản Một"
    assert names.index("CongDan__fsTinhNhanKQ") < names.index("CongDan__fsXaNhanKQ")
    assert all(f["comp"] == UI_COMP_BY_NAME[f["name"]] for f in out)
    # Cảnh báo: GCN thu hồi (xe đã đăng ký), dung tích lệch, thiếu công suất ô tô, email, hình thức nhận KQ.
    assert mapper.GCN_THU_HOI_WARNING in warnings
    assert any("1500 cm³" in w and "1499 cm³" in w for w in warnings)
    assert any("Công suất" in w for w in warnings) and any("Email" in w for w in warnings)
    assert any("hình thức nhận kết quả" in w for w in warnings) and warnings[-1] == mapper.TRA_CUU_WARNING


def test_hoa_don_that_va_to_khai_hai_quan_xe_may_nhan_buu_dien():
    values = {k: v for k, v in HO_SO.items() if not k.startswith(("GcnThuHoi_", "Hdmb_"))}
    values.update({
        "Xe_LoaiXe": "Xe mô tô hai bánh", "Xe_CongSuat": "8,5 kW", "Lptb_DungTich": "1499",
        "HoaDon_Loai": "HÓA ĐƠN GIÁ TRỊ GIA TĂNG (Bản thể hiện của hóa đơn điện tử)", "HoaDon_KyHieu": "C26TAA",
        "HoaDon_MauSo": "1", "HoaDon_So": "00000012", "HoaDon_Ngay": "05/11/2026",
        "HoaDon_TenHangHoa": "Xe mô tô HIEUXE MX, Số khung: MK2000000000001", "HoaDon_DonViBan": "CÔNG TY TNHH XE D",
        "HoaDon_MstNguoiBan": "6200000001", "HoaDon_HoTenNguoiMua": "Nguyễn Văn An",
        "HoaDon_MstNguoiMua": "001090000001", "HoaDon_TongCong": "80.000.000",
        "ToKhaiHq_SoToKhai": "10500000001", "ToKhaiHq_NgayDangKy": "1/9/2026",
        "ToKhaiHq_CoQuanHaiQuan": "Chi cục Hải quan cửa khẩu cảng X", "ToKhaiHq_TenNguoiNhapKhau": "CÔNG TY TNHH XE D",
        "ToKhaiHq_DiaChiNguoiNhapKhau": "Số 2, đường E, Hà Nội", "ToKhaiHq_XuatXu": "Nhật Bản",
        "ToKhai_Email": "an.nguyen@gmail,com", "HoSo_HinhThucNhanKetQua": "Qua dịch vụ bưu chính công ích",
    })
    out, warnings = _enrich(values)
    by = _by(out)
    assert by["CongDan__fsRadioLoaiXe"] == "Xe máy"  # "mô tô" gấp dấu chứa "o to" — không được ra "Ô tô"
    assert by["CongDan__fsLoaiHoaDon"] == "Hóa đơn giá trị gia tăng" and by["CongDan__fsSoHoaDon"] == "00000012"
    assert by["CongDan__fsHoTenNguoiMua"] == "NGUYỄN VĂN AN" and by["CongDan__fsMSTNguoiBan"] == "6200000001"
    assert by["CongDan__fsTongCongTienThanhToan"] == "80.000.000 đồng"
    assert by["CongDan__fsSoMay2DK"] == "10500000001" and by["CongDan__fsDkNgayXuatXuong"] == "01/09/2026"
    assert by["CongDan__fsCoQuanHaiQuanDK"] == "Chi cục Hải quan cửa khẩu cảng X"
    assert by["CongDan__fsTenDonViSanXuat"] == "CÔNG TY TNHH XE D" and by["CongDan__fsNuocSanXuatDK"] == "Nhật Bản"
    assert by["CongDan__fsCongSuat"] == "8,5 kW" and by["CongDan__fsCongSuatDK"] == "8,5"
    assert by["CongDan_email"] == "an.nguyen@gmail.com"
    assert by["CongDan__fsHinhThucNhanKQ"] == "Qua bưu điện, tại nhà"
    # Địa chỉ nhận KQ: không có giấy địa giới mới → theo thẻ.
    assert by["CongDan__fsXaNhanKQ"] == "Xã Pắc Ta" and by["CongDan__fsDiaChiChiTietNhanKQ"] == "Bản Một"
    assert mapper.HOA_DON_THEO_HOP_DONG_WARNING not in warnings and mapper.GCN_THU_HOI_WARNING not in warnings
    assert not any("cm³" in w for w in warnings) and not any("Email" in w for w in warnings)


def test_the_cua_ben_ban_bo_ca_bo_cccd_va_thieu_ma_tra_cuu():
    values = {**HO_SO, "Cccd_HoTen": "TRẦN VĂN BÌNH", "Cccd_SoDinhDanh": "001080000009", "Cccd_NgayCap": "01/01/2023"}
    by = _by(_enrich(values)[0])
    assert by["CongDan__fsngayCapCmnd"] == "06/04/2021"  # theo hợp đồng (bên mua), không theo thẻ bên bán
    assert by["CongDan__fsCMNDNguoiNopThueLPTB"] == "001090000001" and "CongDan__fsQuocTichChuXe" not in by
    assert by["CongDan__fsTenNguoiNhanKQ"] == "NGUYỄN VĂN AN"

    values = {k: v for k, v in HO_SO.items() if k not in ("Lptb_MaHoSo", "Xe_SoKhung", "Lptb_SoKhung")}
    out, warnings = _enrich(values)
    assert not {"CongDan__fstracuuSoKhung", "CongDan__fsTraCuMaHsLPTB"} & set(_by(out))
    assert any("Số khung" in w and "Mã hồ sơ LPTB" in w for w in warnings)
    # Chỉ có SĐT giả của GCN thu hồi → bỏ, không điền dãy 0.
    out, _ = _enrich({k: v for k, v in HO_SO.items() if k != "Lptb_DienThoai"})
    assert "CongDan_diDong" not in _by(out) and "CongDan__fsSDTNguoiNopThue" not in _by(out)
    assert mapper._money_words("1000005") == "Một triệu không trăm linh năm đồng"


# Phần I cổng khoá theo tài khoản VNeID; Auto Fill / trợ lý gửi hai ô readonly qua options.formContext.
OTHER_ACCOUNT = {"formContext": {"applicantFullname": "LÊ THỊ HOA", "applicantIdentityNumber": "001204000777"}}


def test_tai_khoan_vneid_khac_chu_xe_thi_chan_khong_dien():
    # User 20/11/2026: ảnh chạy thật trợ lý điền giấy tờ của người khác vào hồ sơ của chủ tài khoản.
    out, warnings = _enrich(HO_SO, OTHER_ACCOUNT)
    assert out == [] and len(warnings) == 1 and "LÊ THỊ HOA" in warnings[0] and "NGUYỄN VĂN AN" in warnings[0]
    values = {k: v for k, v in HO_SO.items()}
    blocked = mapper.account_block(values, OTHER_ACCOUNT)
    assert blocked["code"] == "account_mismatch" and blocked["accountName"] == "LÊ THỊ HOA"
    assert blocked["documentName"] == "NGUYỄN VĂN AN"
    # Thẻ của bên bán bị bỏ: chủ xe vẫn là bên mua → tài khoản bên bán cũng bị chặn.
    seller = {"formContext": {"applicantFullname": "TRẦN VĂN BÌNH", "applicantIdentityNumber": "001080000009"}}
    assert mapper.account_block({**HO_SO, "Cccd_HoTen": "TRẦN VĂN BÌNH", "Cccd_SoDinhDanh": "001080000009"}, seller)
    # Chỉ đọc được họ tên tài khoản → so họ tên.
    assert _enrich(HO_SO, {"formContext": {"applicantFullname": "Lê Thị Hoa"}})[0] == []


def test_tai_khoan_vneid_dung_chu_xe_thi_dien_binh_thuong():
    for context in (
        {"applicantFullname": "NGUYỄN VĂN AN", "applicantIdentityNumber": "001090000001"},
        {"applicantFullname": "Nguyễn Văn An", "applicantIdentityNumber": "001090000007"},  # OCR lệch số, tên trùng
        {"applicantIdentityNumber": "001090000001"},
        {"applicantFullname": "nguyễn văn an"},
    ):
        out, warnings = _enrich(HO_SO, {"formContext": context})
        assert out and mapper.account_block(dict(HO_SO), {"formContext": context}) is None, context
        assert mapper.NO_ACCOUNT_WARNING not in warnings
    # Không đọc được ô Phần I (extension cũ / trang chưa nạp) → vẫn điền, kèm cảnh báo đối chiếu.
    out, warnings = _enrich(HO_SO, {"formContext": {"applicantFullname": "", "applicantIdentityNumber": ""}})
    assert out and mapper.NO_ACCOUNT_WARNING in warnings
    # Giấy không ghi chủ xe → không có gì để so, không chặn.
    assert mapper.account_block({"Xe_SoKhung": "MK2000000000001"}, OTHER_ACCOUNT) is None


def test_runner_gan_blocked(monkeypatch):
    import asyncio

    from app.pipelines._shared.compact_agent import runner as compact_runner
    from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process import runner as xe_runner

    async def fake_run(*_args, **_kwargs):
        return {"fields": [{"name": k, "value": v} for k, v in HO_SO.items()]}

    monkeypatch.setattr(compact_runner, "run", fake_run)
    res = asyncio.run(xe_runner.run({}, OTHER_ACCOUNT))
    assert res["fields"] == [] and res["blocked"]["documentName"] == "NGUYỄN VĂN AN"
    res = asyncio.run(xe_runner.run({}, {}))
    assert res["fields"] and "blocked" not in res


# ── Ba ô ảnh đầu trang (user 24/11/2026): Ảnh phương tiện + hai mặt chứng từ nguồn gốc (tờ khai hàng hóa nhập khẩu) ──
def _data_url(mime: str, data: bytes) -> str:
    import base64

    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def _photo(color=(30, 90, 160)) -> bytes:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (900, 600), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _pdf(pages: int) -> bytes:
    import fitz

    with fitz.open() as doc:
        for number in range(pages):
            doc.new_page().insert_text((72, 72), f"Trang {number + 1}")
        return doc.tobytes()


CUSTOMS_P1 = "TỜ KHAI HÀNG HÓA NHẬP KHẨU (THÔNG QUAN)\nSố tờ khai: 100000000001 Mã loại hình: A11\nChi cục Hải quan cửa khẩu"
CUSTOMS_P2 = "TỜ KHAI HÀNG HÓA NHẬP KHẨU (THÔNG QUAN)\nSố tờ khai: 100000000001 Trang 2/2\nMô tả hàng hóa: ô tô con"
CCCD_TEXT = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM CĂN CƯỚC CÔNG DÂN Số định danh cá nhân Họ, chữ đệm và tên khai sinh " * 2


def _run_with_photos(monkeypatch, files, texts):
    import asyncio

    from app.pipelines._shared.compact_agent import runner as compact_runner
    from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process import runner as xe_runner
    from app.services import ocr

    async def fake_ocr(ocr_files, **_kwargs):
        return [{"text": texts.get(f["name"], "")} for f in ocr_files]

    async def fake_run(files_by_role, **kwargs):
        await kwargs["ocr_fn"](compact_runner.flatten(files_by_role))
        return {"fields": [{"name": k, "value": v} for k, v in HO_SO.items()]}

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(compact_runner, "run", fake_run)
    return asyncio.run(xe_runner.run({"": files}, {}))


def test_runner_gan_anh_phuong_tien_va_hai_mat_to_khai_hai_quan_vao_o_dau_trang(monkeypatch):
    import base64

    from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process import runner as xe_runner

    files = [
        {"name": "cccd.png", "type": "image/png", "dataUrl": _data_url("image/png", _photo((240, 240, 240)))},
        {"name": "to_khai_hai_quan.pdf", "type": "application/pdf", "dataUrl": _data_url("application/pdf", _pdf(2))},
        {"name": "IMG_0001.png", "type": "image/png", "dataUrl": _data_url("image/png", _photo())},
    ]
    texts = {"cccd.png": CCCD_TEXT,
             "to_khai_hai_quan.pdf": f"───── Trang 1/2 ─────\n{CUSTOMS_P1}\n───── Trang 2/2 ─────\n{CUSTOMS_P2}"}
    res = _run_with_photos(monkeypatch, files, texts)
    photos = res["fields"][:3]
    assert [f["name"] for f in photos] == ["AnhPhuongTien", "AnhNguonGocMatTruoc", "AnhNguonGocMatSau"]
    assert [f["match"] for f in photos] == ["anh phuong tien", "nguon goc mat truoc", "nguon goc mat sau"]
    assert {f["comp"] for f in photos} == {"bca-photo"}
    assert [f["sourceFileName"] for f in photos] == ["IMG_0001.png", "to_khai_hai_quan.pdf", "to_khai_hai_quan.pdf"]
    for field in photos:
        assert field["value"]["type"] == "image/jpeg" and field["value"]["dataUrl"].startswith("data:image/jpeg;base64,")
        jpeg = base64.b64decode(field["value"]["dataUrl"].split(",", 1)[1])
        assert jpeg[:2] == b"\xff\xd8" and len(jpeg) < 2_000_000  # cổng chỉ nhận dưới 2 MB
    note = next(e for e in res["errors"] if e.startswith("Đã gắn ảnh"))
    assert "'IMG_0001.png' → ô Ảnh phương tiện" in note
    assert "trang 1 của 'to_khai_hai_quan.pdf' → ô Ảnh chứng từ nguồn gốc mặt trước" in note
    assert "trang 2 của 'to_khai_hai_quan.pdf' → ô Ảnh chứng từ nguồn gốc mặt sau" in note
    # Câu Tra cứu thôi nhắc tự tải ảnh; không còn câu "Chưa có ảnh".
    assert mapper.TRA_CUU_NO_PHOTO_WARNING in res["errors"] and mapper.TRA_CUU_WARNING not in res["errors"]
    assert not any(e.startswith("Chưa có ảnh") for e in res["errors"])
    # Hai ảnh tờ khai chụp rời (mỗi mặt một tệp ảnh) → mặt trước / mặt sau theo thứ tự tệp.
    pages = {0: [CUSTOMS_P1], 1: ["Ảnh xe"], 2: [CUSTOMS_P2]}
    assert xe_runner.find_origin_pages(pages, skip={1}) == [(0, 0), (2, 0)]


def test_runner_thieu_anh_xe_va_to_khai_mot_trang_thi_bao_o_phai_tai_tay(monkeypatch):
    from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process import runner as xe_runner

    # Tệp gộp: trang 1 tờ khai hải quan, trang 2 là thẻ căn cước → KHÔNG lấy trang căn cước làm mặt sau.
    files = [{"name": "ho_so.pdf", "type": "application/pdf", "dataUrl": _data_url("application/pdf", _pdf(2))}]
    texts = {"ho_so.pdf": f"───── Trang 1/2 ─────\n{CUSTOMS_P1}\n───── Trang 2/2 ─────\n{CCCD_TEXT}"}
    res = _run_with_photos(monkeypatch, files, texts)
    assert [f["name"] for f in res["fields"] if f.get("comp") == "bca-photo"] == ["AnhNguonGocMatTruoc"]
    missing = next(e for e in res["errors"] if e.startswith("Chưa có ảnh"))
    assert "Ảnh phương tiện" in missing and "Ảnh chứng từ nguồn gốc mặt sau" in missing
    assert "mặt trước" not in missing
    # Mặt sau scan không lặp tiêu đề → trang liền sau trong cùng tệp.
    assert xe_runner.find_origin_pages({0: [CUSTOMS_P1, "Mô tả hàng hóa: ô tô con, số khung"]}) == [(0, 0), (0, 1)]
    # Giấy tờ chụp (nhiều chữ) không phải ảnh xe; tên tệp "anh xe" nới ngưỡng chữ.
    photo = {"name": "a.png", "type": "image/png", "dataUrl": _data_url("image/png", _photo())}
    assert xe_runner.find_vehicle_photo([photo], {0: CCCD_TEXT}) is None
    assert xe_runner.find_vehicle_photo([photo], {0: "51A 12345 TOYOTA"}) == 0
    assert xe_runner.find_vehicle_photo([{**photo, "name": "anh_xe.png"}], {0: "x" * 150}) == 0


def test_tro_ly_nhan_anh_xe_vao_o_anh_phuong_tien_va_ghi_ro_to_khai_hai_quan_hai_mat():
    from app.channels.handfree import procedure_registry as hf
    from app.upload_session import classify

    docs = hf.get_procedure(KEY)["requiredDocs"]
    slot = next(d for d in docs if d["key"] == "anh_phuong_tien")
    assert not slot.get("optional") and slot["sides"] == 1
    assert "2 mặt" in next(d for d in docs if d["key"] == "to_khai_hai_quan")["name"]
    files = [{"name": "IMG_0002.png", "type": "image/png", "dataUrl": _data_url("image/png", _photo())},
             {"name": "cccd.png", "type": "image/png", "dataUrl": _data_url("image/png", _photo((240, 240, 240)))}]
    ocr_results = [{"text": ""}, {"text": CCCD_TEXT}]
    assert classify._vehicle_photo_indexes(files, ocr_results, docs, None) == {0}
    # Thủ tục không có ô ảnh phương tiện / công dân chụp theo dòng khác → không đụng.
    assert classify._vehicle_photo_indexes(files, ocr_results, [d for d in docs if d["key"] != "anh_phuong_tien"],
                                           None) == set()
    assert classify._vehicle_photo_indexes(files, ocr_results, docs, "cccd") == set()


def test_registry_link_va_detect_thang_ban_lap_rap_trong_nuoc():
    # User 24/11: có bước đính kèm = ba ô ảnh đầu trang kê khai (attach/planner.py), tách hay không ra cùng kế hoạch.
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    proc = registry.get_procedure(KEY)
    assert proc["hasAttachmentStep"] is True and proc["supportsSplitDocuments"] is True and proc["mode"] == "agent"
    # Auto Fill gom mốc tài khoản (CongDan_tenCongDan / CongDan_soCmnd) cho thủ tục này.
    assert proc["collectFormContext"] is True
    assert proc["detect"]["urlScope"] == ["dichvucong.bocongan.gov.vn"] and proc["detect"]["codeOnPage"] is True
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.013066" and link["url"].endswith("tthc?matt=58712")
    assert link["directSubmit"] is True and link["bcaSubmit"] is True
    public = next(p for p in with_ke_khai_detect_urls([proc]) if p["key"] == KEY)
    assert link["url"] in public["detect"]["urlIncludes"] and "matthc=1.013066" in public["detect"]["urlIncludes"]
    # Trang xe nhập khẩu có ô "Xe nhập khẩu" liệt kê cả option "Xe sản xuất, lắp ráp trong nước": popup chọn bộ cụm có
    # TỔNG độ dài lớn nhất → cụm của thủ tục này phải dài hơn của 1.012575; trang xe trong nước không có "đối với xe
    # nhập khẩu".
    def score(key):
        return sum(len(p) for p in registry.get_procedure(key)["detect"]["textIncludes"])
    assert score(KEY) > score(SIBLING)
    assert "đối với xe nhập khẩu" in proc["detect"]["textIncludes"]


# ── Trợ lý người dân (handfree) ──
from app.channels.handfree.chat import flow  # noqa: E402

# Bản trợ lý biết gắn ô ảnh đầu trang ở bước đính kèm (supportsBcaPagePhotos) mới được dẫn vào thủ tục này.
CAPS = {"supportsBcaDangKyXe": True, "supportsBcaPagePhotos": True}


def test_tro_ly_cung_key_mo_thang_trang_chon_truong_hop_hien_moi_tinh():
    from app.channels.handfree import procedure_registry as hf
    from app.channels.handfree.chat import script_mong
    from app.channels.handfree.chat.procedure_picker import prompt as picker

    proc, sibling = hf.get_procedure(KEY), hf.get_procedure(SIBLING)
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    # Nút "Nộp hồ sơ" trên trang thủ tục (link Auto Fill) trỏ trang chọn trường hợp cùng số matt.
    assert proc["keKhaiUrl"].endswith("chon-truong-hop-ho-so?ma-thu-tuc-public=" + link["url"].rsplit("=", 1)[1])
    assert proc["detect"] == registry.get_procedure(KEY)["detect"]
    for field in ("laiChauFeeStep", "flowProfile", "bcaPortal",
                  "agencyDirectSubmit", "provinceOnly"):
        assert proc.get(field) == sibling.get(field), field
    assert hf.get_pipeline(KEY) is registry.get_pipeline(KEY)
    for slug in ("khanhhoa", "laichau", "bacninh", "quangninh", ""):
        assert KEY in {p["key"] for p in hf.public_list_for(slug)}, slug
    assert "đăng ký xe nhập khẩu" in picker.PROCEDURE_HINTS[KEY]
    assert script_mong.PROCEDURE_HMONG[KEY]

    conv = {"state": "greet", "procedure_key": None, "client_capabilities": dict(CAPS),
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Phường Tân Phong"}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert conv["state"] == "guide_login" and r.actions[0]["url"] == proc["keKhaiUrl"]


def test_tro_ly_bi_chan_tai_khoan_gui_lai_giay_to_co_chon_cach_gui_nhu_tu_phap():
    """User 20/11/2026: sau câu "Giấy tờ chưa đúng người", "Gửi lại giấy tờ" chỉ hiện lại QR → phải về bước CHỌN cách
    gửi (Chụp bằng điện thoại / Scan tại quầy) như "📷 Gửi lại giấy tờ" của tư pháp; thêm "Điều chỉnh giấy tờ"."""
    import asyncio

    from app.channels.handfree.chat.intents import Intent

    def turn(conv, kind, value, payload=None):
        return asyncio.run(flow._handle_turn_inner(conv, Intent(kind, value, payload or {})))

    def blocked_conv():
        conv = {"_id": "c-xe-nk", "state": "greet", "procedure_key": None, "client_capabilities": dict(CAPS),
                "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Phường Tân Phong"}}
        flow._to_confirm_procedure(conv, KEY)
        flow._start_guide_login(conv)
        blocked = mapper.account_block(dict(HO_SO), OTHER_ACCOUNT)
        conv.update({"state": "filling", "consent": {"accepted": True}, "docs_target": "declaration",
                     "upload_session_id": "", "doc_method": "qr", "pipeline_status": "error",
                     "pipeline_blocked": blocked, "pipeline_error": blocked["message"][:300]})
        return conv

    conv = blocked_conv()
    r = turn(conv, "event", "pipeline_error")
    assert "chưa đúng người" in r.display_md and conv["state"] == "collecting_docs"
    assert [c["send"] for c in r.chips] == ["__action:resend_docs", "__action:add_documents", "__event:docs_complete"]
    assert r.chips[0]["label"] == "📷 Gửi lại giấy tờ" and r.chips[0]["solid"] is True
    # Gửi lại giấy tờ: bỏ phiên + kết quả chặn cũ, về bước chọn cách gửi kèm danh sách giấy.
    r = turn(conv, "action", "resend_docs")
    assert conv["state"] == "ask_doc_method" and conv["upload_session_id"] is None and conv["doc_method"] is None
    assert conv["pipeline_blocked"] == {} and conv["pipeline_status"] == ""
    assert r.cards and r.cards[0]["kind"] == "doc_options" and set(r.cards[0]["options"]) == {"qr", "scan"}
    assert "bằng cách nào" in r.display_md and "Lệ phí trước bạ" in r.display_md
    # Điều chỉnh giấy tờ: mở lại danh sách (thẻ chọn cách gửi + nút hoàn tất điền lại tờ khai).
    conv = blocked_conv()
    turn(conv, "event", "pipeline_error")
    r = turn(conv, "action", "add_documents")
    assert conv["state"] == "ask_doc_method" and conv["supplementing_documents"] is True
    assert conv["documents_adjustment_target"] == "declaration"
    assert r.cards and r.cards[0]["kind"] == "doc_options"
    # Lỗi đọc giấy thường: "Gửi lại giấy tờ" cũng về bước chọn cách gửi (thay "Chụp lại giấy tờ" chỉ hiện QR).
    conv = blocked_conv()
    conv.update({"pipeline_blocked": {}, "pipeline_error": "Phiên không còn file nào."})
    r = turn(conv, "event", "pipeline_error")
    assert [c["send"] for c in r.chips] == ["__event:docs_complete", "__action:resend_docs"]


def test_so_khung_lech_mot_ky_tu_giua_cac_giay_lay_ban_du_17_ky_tu():
    # Chạy thử 20/11: OCR rơi một ký tự số khung ở một giấy (lượt thì giấy đăng ký, lượt thì giấy LPTB).
    vin, short = "MR0BA3CDXT0012345", "MR0BA3CDX0012345"
    for reg, lptb in ((short, vin), (vin, short)):
        out, warnings = _enrich({**HO_SO, "Xe_SoKhung": reg, "Lptb_SoKhung": lptb})
        by = _by(out)
        assert by["CongDan__fstracuuSoKhung"] == by["CongDan__fsSoKhungDK"] == by["CongDan__fsSoKhung"] == vin
        assert any("Số khung trên giấy tờ không khớp" in w for w in warnings)
    # Không bản nào đủ 17 ký tự (xe máy đời cũ) → giữ thứ tự ưu tiên: Phần V theo giấy đăng ký, Phần III theo LPTB.
    by = _by(_enrich({**HO_SO, "Xe_SoKhung": "AB12345", "Lptb_SoKhung": "AB1234"})[0])
    assert by["CongDan__fsSoKhungDK"] == "AB12345" and by["CongDan__fsSoKhung"] == "AB1234"
    assert mapper._vin_pick(None, vin) == vin and mapper._vin_pick(None, None) is None


# ── Trợ lý (user 24/11/2026): điền → báo số ô trống → "Đính kèm giấy tờ" gắn ba ô ảnh ĐẦU trang kê khai (trang không có
# bảng Thành phần hồ sơ) → "Đồng ý và tiếp tục" → thẳng trang Xác nhận → Nộp hồ sơ. Khuôn thị thực 1.001194. ──
FLOW_CAPS = {**CAPS, "supportsLaiChauFeeStep": True, "supportsBcaCaseStep": True, "supportsFieldReview": True,
             "supportsBcaNthReview": True, "supportsBcaNthSubmit": True, "supportsPageBoundDocsComplete": True}
KE_KHAI = {"pageContextCaptured": True, "formKind": "standard", "attachmentTarget": False,
           "attachmentComponentCount": 0, "bcaKeKhaiForm": True}
PHOTO_PLAN = [{"target": "bca-photo", "fileIndex": 2, "fileName": "IMG_0001.png", "documentName": "Ảnh phương tiện",
               "componentName": "Ảnh phương tiện", "slotName": "Ảnh phương tiện", "fieldName": "AnhPhuongTien",
               "match": "anh phuong tien", "photoFid": "f-photo-1", "photoName": "anh_phuong_tien.jpg",
               "photoType": "image/jpeg"}]


def _flow_text(r) -> str:
    return r.display_md + " " + " ".join(a.get("md", "") for a in r.actions if a.get("type") == "trail_message")


def test_tro_ly_ban_cu_chua_gan_duoc_o_anh_o_buoc_dinh_kem_thi_khong_dan_vao():
    from app.channels.handfree import procedure_registry as hf
    from app.channels.handfree.chat.router import _clean_client_capabilities

    proc = hf.get_procedure(KEY)
    assert proc["requiresCapability"] == "supportsBcaPagePhotos"
    assert _clean_client_capabilities({"supportsBcaPagePhotos": True})["supportsBcaPagePhotos"] is True
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": {"supportsBcaDangKyXe": True},
            "location": {}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert conv["state"] != "guide_login" and not r.actions
    assert "__action:new_procedure" in [c["send"] for c in r.chips]


def test_tro_ly_dien_bao_o_trong_dinh_kem_anh_cung_trang_roi_dong_y_va_tiep_tuc_sang_xac_nhan(monkeypatch):
    import asyncio

    from app.channels.handfree import procedure_registry as hf
    from app.channels.handfree.chat import field_review, lai_chau, pipeline_runner
    from app.channels.handfree.chat.intents import Intent

    proc = hf.get_procedure(KEY)
    assert proc["bcaPagePhotos"] is True and proc["askBeforeAttach"] is True and proc["docsAdjustRefill"] is True
    assert proc["hasAttachmentStep"] is True and proc["supportsSplitDocuments"] is True
    assert field_review.bca_nth(proc) and flow._bca_nth(proc)

    calls = []

    async def progress(_sid):
        return {"received": 5, "total": 5, "files_count": 5}

    async def save(_conv):
        return None

    monkeypatch.setattr(pipeline_runner, "run_process", lambda *a: calls.append("process"))
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a: calls.append("attach"))
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)
    monkeypatch.setattr(flow.upload_service, "progress_of", progress)
    monkeypatch.setattr(flow.conv_store, "save", save)

    def turn(conv, kind, value, payload=None):
        return asyncio.run(flow._handle_turn_inner(conv, Intent(kind, value, payload or {})))

    conv = {"_id": "t-xe-nk", "state": "collecting_docs", "history": [], "procedure_key": KEY,
            "upload_session_id": "s1", "docs_target": "declaration", "client_capabilities": dict(FLOW_CAPS)}
    # 1) "Đã đưa đủ giấy tờ" trên trang kê khai → ĐIỀN (không có bảng đính kèm nào để nhầm sang bước đính).
    assert flow._resolve_docs_target(proc, KE_KHAI, {}) == "declaration"
    asyncio.run(flow._docs_complete(conv, KE_KHAI))
    assert conv["state"] == "filling" and calls == ["process"] and conv["auto_attach_after_fill"] is True
    assert field_review.fill_action_extra(conv, proc) is not None  # lệnh điền xin extension tô + đếm ô

    # 2) Điền xong, form còn ô trống → báo số ô bắt buộc / không bắt buộc còn trống + nút Bổ sung; DỪNG hỏi đính kèm,
    #    nút "Đính kèm giấy tờ" gắn ảnh ngay trang này — không bảo "sang Thành phần hồ sơ".
    calls.clear()
    conv["pipeline_status"] = "fields_ready"
    r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {
        "filled": 48, "notFound": [], "review": {"filled": 48, "optional": 20, "required": 9}})))
    text = _flow_text(r)
    assert conv["state"] == "reviewing" and calls == [] and not conv.get("attachment_plan_started")
    assert "🟥 **9** ô bắt buộc còn trống" in text and "🟧 **20** ô không bắt buộc còn trống" in text
    assert "đầu trang" in text and "Thành phần hồ sơ" not in text and "Mình đang ở trang" not in text
    sends = [c["send"] for c in r.chips]
    assert "__action:confirm_review" in sends and "__action:field_review_start" in sends
    assert lai_chau.NEXT_SEND not in sends

    # 3) Bấm "Đính kèm giấy tờ" → lập kế hoạch NGAY trên trang kê khai (không bấm "Đồng ý và tiếp tục" hộ, không chờ).
    r = turn(conv, "action", "confirm_review")
    assert calls == ["attach"] and conv["state"] == "attaching" and conv["attachment_plan_started"] is True
    assert not any(a.get("type") == "lc_next" for a in r.actions) and "Mình đang ở trang" not in r.display_md
    assert flow._attachment_page_reached(conv, proc, KE_KHAI) is True

    # 4) Kế hoạch về (chỉ ô ảnh) → phát lệnh đính, kèm lệnh đếm lại ô của form sau khi gắn.
    conv.update(attach_plan=PHOTO_PLAN, pipeline_status="attach_ready", attach_errors=[])
    r = asyncio.run(flow._handle_attaching(conv, Intent("event", "attach_ready")))
    action = next(a for a in r.actions if a.get("type") == "attach_plan")
    assert action["attachments"][0]["target"] == "bca-photo" and isinstance(action.get("fieldReview"), dict)
    assert "IMG_0001.png" in r.display_md and "Ảnh phương tiện" in r.display_md

    # 5) Gắn xong mà form còn ô bắt buộc trống → chưa có "Đồng ý và tiếp tục", có Bổ sung + Điền lại tờ khai.
    r = asyncio.run(flow._handle_attaching(conv, Intent("action", "attach_report", {
        "attached": 3, "skipped": 0, "errors": [], "dispatch_id": action.get("dispatch_id") or "",
        "review": {"filled": 51, "optional": 20, "required": 2}})))
    assert conv["state"] == "done" and "Đã gắn **3 ảnh**" in r.display_md and "đầu trang" in r.display_md
    sends = [c["send"] for c in r.chips]
    assert not [c for c in r.chips if c.get("cta")] and "__action:field_review_start" in sends
    assert "__action:refill" in sends and "2 ô bắt buộc" in _flow_text(r)
    # Công dân tự gõ đủ trên trang → hiện nút cam "Đồng ý và tiếp tục".
    r = turn(conv, "event", "field_review_status", {"stats": {"filled": 53, "optional": 20, "required": 0}})
    assert [c for c in r.chips if c.get("cta")] == [lai_chau.next_chip()]

    # 6) Bấm nút → trợ lý bấm "Đồng ý và tiếp tục"; cổng sang thẳng trang Xác nhận → dặn nhập mã, tích ô, nút Nộp hồ sơ.
    assert turn(conv, "action", "lc_next").actions == [{"type": "lc_next"}]
    r = turn(conv, "event", "page_status", {"loggedIn": True, "formKind": "", "bcaConfirmPage": True,
                                            "bcaKeKhaiForm": False})
    assert "**Mã xác nhận**" in r.display_md and r.chips == [flow._bca_nth_submit_chip()]


def test_tro_ly_luot_dien_khong_gan_anh_buoc_dinh_kem_moi_gan(monkeypatch):
    import asyncio

    import app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process.runner as xe_runner
    from app.pipelines._shared.compact_agent import runner as compact_runner
    from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.attach import plan
    from app.process.schemas import FileItem
    from app.services import ocr

    files = [
        {"name": "to_khai_hai_quan.pdf", "type": "application/pdf", "dataUrl": _data_url("application/pdf", _pdf(2))},
        {"name": "IMG_0001.png", "type": "image/png", "dataUrl": _data_url("image/png", _photo())},
    ]
    texts = {"to_khai_hai_quan.pdf": f"───── Trang 1/2 ─────\n{CUSTOMS_P1}\n───── Trang 2/2 ─────\n{CUSTOMS_P2}"}

    async def fake_ocr(ocr_files, **_kwargs):
        return [{"name": f["name"], "text": texts.get(f["name"], "")} for f in ocr_files]

    async def fake_run(files_by_role, **kwargs):
        await kwargs["ocr_fn"](compact_runner.flatten(files_by_role))
        return {"fields": [{"name": k, "value": v} for k, v in HO_SO.items()]}

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(compact_runner, "run", fake_run)
    # Lượt điền của trợ lý (pagePhotosAtAttach): không gắn ảnh, câu Tra cứu không nhắc tự tải ảnh.
    res = asyncio.run(xe_runner.run({"": files}, {"pagePhotosAtAttach": True}))
    assert not [f for f in res["fields"] if f.get("comp") == "bca-photo"]
    assert mapper.TRA_CUU_NO_PHOTO_WARNING in res["errors"] and mapper.TRA_CUU_WARNING not in res["errors"]
    assert not any(e.startswith(("Đã gắn ảnh", "Chưa có ảnh")) for e in res["errors"])

    # Bước đính kèm: kế hoạch không có mục bảng, chỉ ba ô ảnh; bật hay tắt "Tách giấy tờ" ra cùng kết quả.
    items = [FileItem(name=f["name"], type=f["type"], dataUrl=f["dataUrl"], role="") for f in files]
    results = [asyncio.run(plan(items, {"splitDocuments": split})) for split in (True, False, None)]
    for result in results:
        assert result["attachments"] == [] and result["nothingToAttach"] is True
        assert [f["name"] for f in result["pageFields"]] == ["AnhPhuongTien", "AnhNguonGocMatTruoc", "AnhNguonGocMatSau"]
        assert [f["label"] for f in result["pageFields"]] == [
            "Ảnh phương tiện", "Ảnh chứng từ nguồn gốc mặt trước", "Ảnh chứng từ nguồn gốc mặt sau"]
        assert result["errors"] == []  # lúc lập kế hoạch ảnh chưa gắn → không nói "Đã gắn"
    assert results[0]["pageFields"][0]["value"] == results[1]["pageFields"][0]["value"]
    # Thiếu ảnh xe → nói rõ ô nào, mời "đính kèm lại".
    only_customs = asyncio.run(plan(items[:1], {}))
    assert [f["name"] for f in only_customs["pageFields"]] == ["AnhNguonGocMatTruoc", "AnhNguonGocMatSau"]
    assert any("Ảnh phương tiện" in e and "đính kèm lại" in e for e in only_customs["errors"])


def test_tro_ly_anh_o_dau_trang_luu_vao_phien_thanh_muc_ke_hoach(monkeypatch):
    import asyncio
    import base64

    from app.channels.handfree.chat import pipeline_runner

    saved, registered = {}, []
    monkeypatch.setattr(pipeline_runner.up_store, "new_file_id", lambda name: f"fid-{name}")
    monkeypatch.setattr(pipeline_runner.up_store, "save_file_bytes", lambda sid, fid, raw: saved.update({fid: raw}))

    async def set_shrunk(sid, metas):
        registered.extend(metas)

    monkeypatch.setattr(pipeline_runner.up_store, "set_shrunk_files", set_shrunk)
    jpeg = b"\xff\xd8jpeg"
    field = {"name": "AnhPhuongTien", "comp": "bca-photo", "match": "anh phuong tien", "label": "Ảnh phương tiện",
             "value": {"name": "anh_phuong_tien.jpg", "type": "image/jpeg",
                       "dataUrl": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()},
             "sourceFileName": "IMG_0001.png"}
    raw_files = [{"name": "cccd.png"}, {"name": "IMG_0001.png"}]
    items, metas = pipeline_runner._store_page_photos("s1", raw_files, ["fid-cccd", "fid-img"], [field, {"comp": "x"}])
    assert saved == {"fid-anh_phuong_tien.jpg": jpeg}
    assert items == [{"target": "bca-photo", "fileIndex": 1, "fileName": "IMG_0001.png",
                      "documentName": "Ảnh phương tiện", "componentName": "Ảnh phương tiện",
                      "slotName": "Ảnh phương tiện", "fieldName": "AnhPhuongTien", "match": "anh phuong tien",
                      "photoFid": "fid-anh_phuong_tien.jpg", "photoName": "anh_phuong_tien.jpg",
                      "photoType": "image/jpeg"}]
    assert "dataUrl" not in str(items)  # kế hoạch / trace không mang base64
    assert metas == [{"fid": "fid-anh_phuong_tien.jpg", "name": "anh_phuong_tien.jpg", "type": "image/jpeg",
                      "size": len(jpeg), "source_fid": "fid-img"}]
    # Đăng ký cùng lượt với bản nén (set_shrunk_files thay nguyên danh sách) → extension tải được theo fid.
    assert asyncio.run(pipeline_runner._store_shrunk_files("s1", ["fid-cccd", "fid-img"], None, metas)) is None
    assert registered == metas
    # Dòng kế hoạch nói đúng tệp gốc → ô ảnh.
    assert flow._attachment_plan_line(items[0]) == "- **IMG_0001.png** → Ảnh phương tiện"
