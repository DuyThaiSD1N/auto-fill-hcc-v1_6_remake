"""Đăng ký xe lần đầu toàn trình — xe sản xuất, lắp ráp trong nước 1.012575 (Cổng DVC Bộ Công an): mapper ô form +
nối registry / link kê khai."""
from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process import mapper
from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

KEY = "dang-ky-xe-lan-dau-san-xuat-lap-rap-trong-nuoc"
# Hồ sơ mẫu bịa: chủ xe tự làm thủ tục, xe mô tô hai bánh, nhận kết quả qua bưu chính.
HO_SO = {
    "Cccd_HoTen": "NGUYỄN VĂN AN", "Cccd_SoDinhDanh": "0010 9000 0001", "Cccd_NgaySinh": "1/2/1990",
    "Cccd_GioiTinh": "Nam", "Cccd_QuocTich": "Việt Nam", "Cccd_NgayCap": "10/03/2024", "Cccd_NoiCap": "BỘ CÔNG AN",
    "Cccd_NoiCuTru": {"tinh": "Lai Châu", "xa": "Phường Đoàn Kết", "chiTietDuoiXa": "Số 1, Tổ 1"},
    "ToKhai_TenChuXe": "Nguyễn Văn An",
    "ToKhai_DiaChi": {"tinh": "tỉnh Lai Châu", "xa": "phường Tân Phong", "chiTietDuoiXa": "Số 9, tổ dân phố số 3"},
    "ToKhai_DienThoai": "0912.345.678", "ToKhai_MaDinhDanh": "001090000001", "ToKhai_LoaiGiayTo": "Thẻ căn cước",
    "ToKhai_CoQuanCap": "Bộ Công an", "ToKhai_NgayCap": "10/03/2024", "ToKhai_NguoiLamThuTuc": "NGUYỄN VĂN AN",
    "ToKhai_MaChungTuLptb": "11200000000001", "ToKhai_SoSeriPhieu": "AB 0000001",
    "Xe_LoaiXe": "Xe mô tô hai bánh", "Xe_NhanHieu": "HIEUXE", "Xe_SoLoai": "HX110", "Xe_MauSon": "Xanh - Đen",
    "Xe_SoKhung": "RLHX110AA0000001", "Xe_SoMay": "HX110E-0000001", "Xe_NamSanXuat": "2026", "Xe_DungTich": "109,5 cm³",
    "Xe_CongSuat": "6,4 kW / 7.500 vòng/phút", "Xe_KhoiLuongBanThan": "98 kg", "Xe_KhoiLuongToanBo": "228",
    "Xe_SoChoNgoi": "2", "Xe_SoChoDung": "………", "Xe_KichThuocBao": "1.910 × 690 × 1.070 mm",
    "Xe_ChieuDaiCoSo": "1.230 mm", "Xe_CoLop": "70/90-17 / 80/90-17", "Xe_LoaiNhienLieu": "Xăng",
    "Pkt_SoSeri": "Số seri phiếu: AB 0000001", "Pkt_TenCoSoSanXuat": "CÔNG TY TNHH XE MÁY HIEUXE",
    "Pkt_DiaChiCoSoSanXuat": "Lô A1, Khu công nghiệp B, xã C, thành phố Hà Nội", "Pkt_NgayXuatXuong": "1/9/2026",
    "HoaDon_Loai": "HÓA ĐƠN GIÁ TRỊ GIA TĂNG (Bản thể hiện của hóa đơn điện tử)", "HoaDon_KyHieu": "C26TAA",
    "HoaDon_MauSo": "1", "HoaDon_So": "00000012", "HoaDon_Ngay": "05/11/2026",
    "HoaDon_TenHangHoa": "Xe mô tô hai bánh nhãn hiệu HIEUXE, số loại HX110", "HoaDon_DonViBan": "CÔNG TY TNHH BÁN XE D",
    "HoaDon_MstNguoiBan": "6200000001", "HoaDon_DiaChiNguoiBan": "Số 2, đường E, phường Tân Phong, tỉnh Lai Châu",
    "HoaDon_TenDonViMua": "……………", "HoaDon_HoTenNguoiMua": "Nguyễn Văn An", "HoaDon_MstNguoiMua": "001090000001",
    "HoaDon_DiaChiNguoiMua": "Số 9, tổ dân phố số 3, phường Tân Phong, tỉnh Lai Châu",
    "HoaDon_TienThue": "2.200.000", "HoaDon_TongCong": "29.700.000 đồng",
    "HoaDon_TongCongBangChu": "hai mươi chín triệu bảy trăm nghìn đồng.",
    "Lptb_MaHoSo": "112 0000 0000 001", "Lptb_NgayThongBao": "05/11/2026", "Lptb_CoQuanThue": "Thuế tỉnh Lai Châu",
    "Lptb_TenNguoiNop": "Nguyễn Văn An", "Lptb_MstNguoiNop": "001090000001",
    "Lptb_DiaChiNguoiNop": "Số 9, tổ dân phố số 3, phường Tân Phong, tỉnh Lai Châu", "Lptb_LoaiTaiSan": "Xe máy",
    "Lptb_GiaTriTinh": "29.700.000", "Lptb_SoTien": "594.000", "Lptb_SoTienBangChu": "Năm trăm chín mươi tư nghìn đồng",
    "Gnt_MaHoSo": "11200000000001", "Gnt_NgayThongBao": "05/11/2026", "Gnt_CoQuanQuanLyThu": "Thuế tỉnh Lai Châu",
    "HoSo_HinhThucNhanKetQua": "Qua dịch vụ bưu chính công ích",
}


def _enrich(values: dict, options=None):
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def _by(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_ho_so_day_du_dien_tra_cuu_chu_xe_lptb_hoa_don_xe_va_nhan_ket_qua():
    out, warnings = _enrich(HO_SO)
    by = _by(out)
    names = [f["name"] for f in out]
    # Phần B: hai ô tra cứu đứng đầu.
    assert names[:2] == ["CongDan__fsSeriChatLuongXuatXuong", "CongDan__fsTraCuMaHsLPTB"]
    assert by["CongDan__fsSeriChatLuongXuatXuong"] == "AB 0000001"
    assert by["CongDan__fsTraCuMaHsLPTB"] == "11200000000001"
    # Phần I: ô readonly CSDL dân cư KHÔNG phát; ô cho sửa lấy từ thẻ.
    assert not {"CongDan_soCmnd", "CongDan_tenCongDan", "CongDan__fsnamSinh", "CongDan__fsBCAHKTTTinh",
                "CongDan__fsBCAHKTTXa", "CongDan__fsBCAHKTTDCChiTiet", "CongDan__fsRadioLoaiXe",
                "CongDan__fstracuuKieuNhap", "CongDan__fsmaXacNhan"} & set(by)
    assert by["CongDan__fs_BCAGioiTinhCd"] == "Nam"
    assert by["CongDan__fsLoaiGiayToChuXe"] == "Căn cước công dân"
    assert by["CongDan__fsngayCapCmnd"] == "10/03/2024" and by["CongDan__fsnoiCapCmnd"] == "Bộ Công an"
    assert by["CongDan__fsQuocTichChuXe"] == "Việt Nam"
    assert by["CongDan_diDong"] == "0912345678" and "CongDan_email" not in by
    # Phần III.
    assert by["CongDan__fsMaHsLPTBDienTu"] == "11200000000001"
    assert by["CongDan__fsNgayCapLPTB"] == "05/11/2026" and by["CongDan__fsCoQuanCapLPTB"] == "Thuế tỉnh Lai Châu"
    assert by["CongDan__fsCMNDNguoiNopThueLPTB"] == "001090000001"
    assert by["CongDan__fsTenNguoiNopThue"] == "NGUYỄN VĂN AN"
    assert by["CongDan__fsLoaiXe"] == "Xe máy" and by["CongDan__fsDungTich"] == "109,5 cm3"
    assert by["CongDan__fsCongSuat"] == "6,4 kW"
    assert by["CongDan__fsSoTienLPTB"] == "594.000 đồng" and by["CongDan__fsGiaTriTinhLPTB"] == "29.700.000 đồng"
    assert "CongDan__fsCanCuMienThuLPTB" not in by
    # Phần IV.
    assert by["CongDan__fsLoaiHoaDon"] == "Hóa đơn giá trị gia tăng"
    assert by["CongDan__fsSoHoaDon"] == "00000012" and by["CongDan__fsHDDTNgayCap"] == "05/11/2026"
    assert "CongDan__fsDonViNguoiMua" not in by
    assert by["CongDan__fsHoTenNguoiMua"] == "NGUYỄN VĂN AN"
    assert by["CongDan__fsTongCongTienThanhToanBangChu"] == "Hai mươi chín triệu bảy trăm nghìn đồng"
    # Phần V: ô có đơn vị trong nhãn chỉ nhận số.
    assert by["CongDan__fsSoSeriKTCLXX"] == "AB 0000001" and by["CongDan__fsDkNgayXuatXuong"] == "01/09/2026"
    assert by["CongDan__fsLoaiXeDK"] == "Xe mô tô hai bánh"
    assert by["CongDan__fsDungTichXiLanhDK"] == "109,5" and by["CongDan__fsCongSuatDK"] == "6,4"
    assert by["CongDan__fsTrongLuongBanThanDK"] == "98" and by["CongDan__fsSoChoNgoiDK"] == "02"
    assert by["CongDan__fsTrongLuongToanBoDK"] == "228 kg" and by["CongDan__fsNuocSanXuatDK"] == "Việt Nam"
    assert "CongDan__fsSoChoDungDK" not in by and "CongDan__fsSoMay2DK" not in by
    # Phần VII: bưu chính → "Qua bưu điện, tại nhà"; người nhận = chủ xe, địa chỉ theo Giấy khai (không theo thẻ cũ).
    assert by["CongDan__fsHinhThucNhanKQ"] == "Qua bưu điện, tại nhà"
    assert by["CongDan__fsTenNguoiNhanKQ"] == "NGUYỄN VĂN AN"
    assert by["CongDan__fsTinhNhanKQ"] == "Tỉnh Lai Châu" and by["CongDan__fsXaNhanKQ"] == "Phường Tân Phong"
    assert by["CongDan__fsDiaChiChiTietNhanKQ"] == "Số 9, tổ dân phố số 3"
    assert names.index("CongDan__fsTinhNhanKQ") < names.index("CongDan__fsXaNhanKQ")
    # Mọi ô phát ra đều có trong bảng ô form.
    assert all(f["comp"] == UI_COMP_BY_NAME[f["name"]] for f in out)
    assert any("Email" in w for w in warnings) and warnings[-1] == mapper.TRA_CUU_WARNING


def test_the_cua_nguoi_khac_bo_ca_bo_cccd():
    out, _ = _enrich({**HO_SO, "Cccd_HoTen": "TRẦN THỊ BÌNH", "Cccd_GioiTinh": "Nữ", "Cccd_NgayCap": "01/01/2023"})
    by = _by(out)
    assert "CongDan__fs_BCAGioiTinhCd" not in by
    assert by["CongDan__fsngayCapCmnd"] == "10/03/2024"  # Giấy khai
    assert by["CongDan__fsCMNDNguoiNopThueLPTB"] == "001090000001"


def test_thieu_phieu_va_thong_bao_lay_ma_tu_giay_khai_giay_nop_tien():
    values = {k: v for k, v in HO_SO.items() if not k.startswith(("Pkt_", "Lptb_"))}
    by = _by(_enrich(values)[0])
    assert by["CongDan__fsSeriChatLuongXuatXuong"] == "AB 0000001"
    assert by["CongDan__fsTraCuMaHsLPTB"] == "11200000000001"
    assert by["CongDan__fsNgayCapLPTB"] == "05/11/2026"
    assert by["CongDan__fsGiaTriTinhLPTB"] == "29.700.000 đồng"  # tổng tiền hóa đơn

    values = {k: v for k, v in values.items() if not k.startswith(("Gnt_", "ToKhai_MaChungTu", "ToKhai_SoSeri"))}
    out, warnings = _enrich(values)
    assert "CongDan__fsTraCuMaHsLPTB" not in _by(out)
    assert any("Số seri phiếu KTCLXX" in w and "Mã hồ sơ LPTB" in w for w in warnings)


def test_hinh_thuc_nhan_ket_qua_va_nguoi_lam_thu_tuc_khac():
    pick = lambda text: _by(_enrich({**HO_SO, "HoSo_HinhThucNhanKetQua": text})[0]).get(  # noqa: E731
        "CongDan__fsHinhThucNhanKQ")
    assert pick("Trực tiếp tại Công an phường") == "Đến cơ quan giải quyết để nhận kết quả"
    assert pick("Nhận kết quả trực tuyến") == "Nhận kết quả qua mạng"
    out, warnings = _enrich({k: v for k, v in HO_SO.items() if k != "HoSo_HinhThucNhanKetQua"})
    assert "CongDan__fsHinhThucNhanKQ" not in _by(out)
    assert any("hình thức nhận kết quả" in w for w in warnings)
    # Người làm thủ tục khác chủ xe: không lấy SĐT người làm thủ tục, có cảnh báo.
    values = {**HO_SO, "ToKhai_DienThoai": "", "ToKhai_NguoiLamThuTuc": "Lê Văn Cường",
              "ToKhai_DienThoaiNguoiLamThuTuc": "0987000000"}
    out, warnings = _enrich(values)
    assert "CongDan_diDong" not in _by(out)
    assert any("người làm thủ tục khác chủ xe" in w for w in warnings)


def test_registry_link_va_detect():
    assert {"Pkt_SoSeri", "Lptb_MaHoSo", "Xe_SoKhung"} <= ALLOWED
    assert registry.get_pipeline(KEY) is not None
    assert registry.get_attach_pipeline(KEY) is None
    proc = registry.get_procedure(KEY)
    assert proc["hasAttachmentStep"] is False and proc["mode"] == "agent"
    assert proc["detect"]["urlScope"] == ["dichvucong.bocongan.gov.vn"]
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.012575" and "ma-thu-tuc-public=56952" in link["url"]
    public = next(p for p in with_ke_khai_detect_urls([proc]) if p["key"] == KEY)
    assert link["url"] in public["detect"]["urlIncludes"]


# ── Trợ lý người dân (handfree) ──
from app.channels.handfree.chat import flow  # noqa: E402
from app.channels.handfree.chat.intents import Intent  # noqa: E402

CAPS = {"supportsBcaDangKyXe": True}


def test_tro_ly_cung_key_url_detect_hien_moi_tinh_va_chi_xin_giay_o_trang_nhap_thong_tin():
    from app.channels.handfree import procedure_registry as hf

    proc = hf.get_procedure(KEY)
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert proc["keKhaiUrl"] == link["url"] and proc["detect"] == registry.get_procedure(KEY)["detect"]
    assert proc["requiresCapability"] == "supportsBcaDangKyXe" and proc["hasAttachmentStep"] is False
    assert hf.get_pipeline(KEY) is registry.get_pipeline(KEY)
    for slug in ("khanhhoa", "laichau", "bacninh", "quangninh", ""):
        assert KEY in {p["key"] for p in hf.public_list_for(slug)}, slug

    # Bản trợ lý chưa khai cờ: không dẫn vào cổng (kẹt ở trang chọn trường hợp).
    conv = {"state": "greet", "procedure_key": None, "location": {}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert "chưa hỗ trợ" in r.display_md and not r.actions
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": dict(CAPS),
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Phường Tân Phong"}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert conv["state"] == "guide_login" and r.actions[0]["url"] == link["url"]
    # Trang chọn trường hợp: extension báo formKind rỗng → chưa xin giấy tờ.
    flow._handle_guide_login(conv, Intent("event", "page_status", {"loggedIn": True, "formKind": ""}))
    assert conv["state"] == "guide_login"
    # Trang nhập thông tin: form kê khai → xin giấy tờ.
    flow._handle_guide_login(conv, Intent("event", "page_status", {"loggedIn": True, "formKind": "standard"}))
    assert conv["state"] in ("ask_doc_method", "consent")


# ── Trợ lý: trang "Chọn trường hợp hồ sơ" (Loại xe…) — thẻ chọn + nút "Đồng ý và tiếp tục" (luồng trang 1 Lai Châu) ──
CASE_CAPS = {"supportsBcaDangKyXe": True, "supportsLaiChauFeeStep": True, "supportsBcaCaseStep": True}
LOAI_XE = {"name": "maLoaiXe", "present": True, "value": "", "options": ["Ô tô", "Xe mô tô"], "fixed": False,
           "label": "Loại xe", "required": True}


def _case_conv(caps=None):
    conv = {"_id": "c1", "state": "greet", "procedure_key": None, "client_capabilities": dict(caps or CASE_CAPS),
            "location": {"province": "Tỉnh Khánh Hòa", "province_slug": "khanhhoa", "ward": "Phường Ba Ngòi"}}
    flow._to_confirm_procedure(conv, KEY)
    flow._start_guide_login(conv)
    return conv


def _turn(conv, kind, value, payload=None):
    import asyncio

    return asyncio.run(flow._handle_turn_inner(conv, Intent(kind, value, payload or {})))


def test_tro_ly_trang_chon_truong_hop_doc_o_tu_do_va_hien_the_chon():
    from app.channels.handfree.chat import lai_chau
    from app.channels.handfree import procedure_registry as hf

    proc = hf.get_procedure(KEY)
    assert proc["laiChauFeeStep"] == {"capability": "supportsBcaCaseStep", "caseOnly": True, "caseGroups": "auto"}
    conv = _case_conv()
    # Sang trang chọn trường hợp (lcStep 1): trợ lý đọc mọi ô chọn đang hiện, không xin giấy tờ.
    r = _turn(conv, "event", "page_status", {"loggedIn": True, "formKind": "", "lcStep": 1})
    assert "Chọn trường hợp hồ sơ" in r.display_md
    assert r.actions == [{"type": "lc_result_scan", "groups": [{"name": "*"}]}] and conv["state"] == "guide_login"
    # Đọc được ô Loại xe (bắt buộc, chưa chọn) → thẻ chọn + mời chọn Loại xe + nút cam Đồng ý và tiếp tục.
    r = _turn(conv, "action", "lc_result_report", {"groups": [LOAI_XE], "prepared": []})
    rows = r.cards[0]["rows"]
    assert [row["label"] for row in rows] == ["Loại xe"]
    assert [o["label"] for o in rows[0]["options"]] == ["Ô tô", "Xe mô tô"]
    trail = r.actions[0]["md"]
    assert "**Loại xe**" in trail and "Đồng ý và tiếp tục" in trail
    assert r.chips == [lai_chau.next_chip()]
    # Bấm "Xe mô tô" trên thẻ → extension chọn ô đó (tự dò lại ô sau khi chọn).
    r = _turn(conv, "action", "lc_result_pick", {"name": "maLoaiXe", "value": "Xe mô tô"})
    assert r.actions == [{"type": "lc_result_set", "name": "maLoaiXe", "value": "Xe mô tô", "groups": [{"name": "*"}]}]
    # Cổng hiện thêm ô: ô một lựa chọn trợ lý chọn sẵn, ô "Trường hợp đăng ký" còn phải chọn.
    groups = [{**LOAI_XE, "value": "Xe mô tô"},
              {"name": "maCoQuan", "present": True, "value": "Phòng CSGT", "options": ["Phòng CSGT"], "label":
               "Cơ quan giải quyết", "required": True},
              {"name": "maTruongHop", "present": True, "value": "", "options": ["Đăng ký lần đầu", "Tạm thời"],
               "label": "Trường hợp đăng ký", "required": True}]
    r = _turn(conv, "action", "lc_result_report", {"groups": groups, "prepared": ["auto:maCoQuan"],
                                                    "changed": {"name": "maLoaiXe", "value": "Xe mô tô", "ok": True}})
    assert [row["label"] for row in r.cards[0]["rows"]] == ["Loại xe", "Cơ quan giải quyết", "Trường hợp đăng ký"]
    assert "chọn sẵn" in r.display_md and "**Trường hợp đăng ký**" in r.actions[0]["md"]
    assert "**Loại xe**" not in r.actions[0]["md"]
    # Đủ ô → câu hướng dẫn bấm Đồng ý và tiếp tục; bấm nút cam → trợ lý bấm nút cổng.
    groups[2]["value"] = "Đăng ký lần đầu"
    r = _turn(conv, "action", "lc_result_report", {"groups": groups, "prepared": []})
    assert "Thông tin người" in r.actions[0]["md"]
    assert _turn(conv, "action", "lc_next").actions == [{"type": "lc_next"}]
    # Nói "bước tiếp theo" ở trang này cũng bấm Đồng ý và tiếp tục.
    assert flow.next_step_by_voice(conv, "bước tiếp theo", {"lcStep": 1}).value == "lc_next"
    # Sang trang nhập thông tin: luồng chung xin giấy tờ như cũ; các bước sau không có nút Lai Châu.
    _turn(conv, "event", "page_status", {"loggedIn": True, "formKind": "standard", "lcStep": 0})
    assert conv["state"] in ("ask_doc_method", "consent")
    assert lai_chau.voice_intent(conv, "bước tiếp theo", {"lcStep": 0}) is None
    reply = flow.Reply("x", "x")
    assert lai_chau.fill_report_reply(conv, proc, reply) is reply and not reply.chips


def test_tro_ly_ban_cu_chua_co_co_trang_chon_truong_hop_thi_giu_luong_cu():
    from app.channels.handfree.chat import lai_chau
    from app.channels.handfree import procedure_registry as hf

    conv = _case_conv({"supportsBcaDangKyXe": True, "supportsLaiChauFeeStep": True})
    assert not lai_chau.enabled(conv, hf.get_procedure(KEY))
    r = _turn(conv, "event", "page_status", {"loggedIn": True, "formKind": "", "lcStep": 1})
    assert not any(a.get("type") == "lc_result_scan" for a in r.actions) and conv["state"] == "guide_login"


def test_tro_ly_trang_chon_truong_hop_cong_hien_them_o_va_chan_nut_tiep_tuc():
    conv = _case_conv()
    _turn(conv, "event", "page_status", {"loggedIn": True, "formKind": "", "lcStep": 1})
    # Ảnh 17/11: chọn Xe máy → cổng hiện Loại biển số (radio), Điểm đăng ký theo địa chỉ, Tỉnh/Thành phố (khoá), Điểm
    # đăng ký (select2 nạp khi mở; không đọc được thì nhắc chọn tay).
    groups = [{**LOAI_XE, "value": "Xe máy"},
              {"name": "loaiBienSo", "present": True, "value": "Biển số định danh đã được cấp/Cấp mới",
               "options": ["Biển số định danh đã được cấp/Cấp mới", "Biển số trúng đấu giá"], "fixed": False,
               "label": "Loại biển số", "required": True},
              {"name": "tinh", "present": True, "value": "Công an Thành phố Hà Nội", "options": [], "fixed": True,
               "label": "Tỉnh/Thành phố", "required": True},
              {"name": "diemDangKy", "present": True, "value": "", "options": [], "fixed": True,
               "label": "Điểm đăng ký", "required": True}]
    r = _turn(conv, "action", "lc_result_report", {"groups": groups, "prepared": []})
    rows = {row["name"]: row for row in r.cards[0]["rows"]}
    assert [o["label"] for o in rows["loaiBienSo"]["options"]] == groups[1]["options"]
    assert rows["tinh"]["fixed"] and rows["tinh"]["value"] == "Công an Thành phố Hà Nội"
    assert "**Điểm đăng ký**" in r.actions[0]["md"] and "chọn trực tiếp trên trang" in r.actions[0]["md"]
    # Có danh sách → mời chọn trên thẻ.
    groups[3] = {**groups[3], "options": ["Đội CSGT số 1", "Công an phường Từ Liêm"], "fixed": False}
    r = _turn(conv, "action", "lc_result_report", {"groups": groups, "prepared": []})
    assert "Công dân chọn **Điểm đăng ký**" in r.actions[0]["md"]
    # Bấm Đồng ý và tiếp tục mà cổng chặn → báo lời chặn + đọc lại thẻ (không làm sẵn gì).
    r = _turn(conv, "action", "lc_step_report", {"clicked": True, "message": "Còn trống: Điểm đăng ký"})
    assert "Còn trống: Điểm đăng ký" in r.display_md
    assert r.actions == [{"type": "lc_result_scan", "groups": [{"name": "*"}], "prepare": False}]
    # Ô trên trang đổi sau lượt đọc (cổng tải chậm / công dân tự chọn) → đọc lại.
    assert _turn(conv, "action", "lc_case_changed").actions == r.actions
    # Đã rời trang chọn trường hợp → im.
    _turn(conv, "event", "page_status", {"loggedIn": True, "formKind": "standard", "lcStep": 0})
    assert not _turn(conv, "action", "lc_case_changed").actions
