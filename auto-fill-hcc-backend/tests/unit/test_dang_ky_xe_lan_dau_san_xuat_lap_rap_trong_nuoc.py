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
    # Bước "Đính kèm" = ba ô ảnh đầu trang (user 24/11/2026), như xe nhập khẩu 1.013066.
    assert registry.get_attach_pipeline(KEY) is not None
    proc = registry.get_procedure(KEY)
    assert proc["hasAttachmentStep"] is True and proc["supportsSplitDocuments"] is True and proc["mode"] == "agent"
    assert proc["detect"]["urlScope"] == ["dichvucong.bocongan.gov.vn"]
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.012575" and "ma-thu-tuc-public=56952" in link["url"]
    public = next(p for p in with_ke_khai_detect_urls([proc]) if p["key"] == KEY)
    assert link["url"] in public["detect"]["urlIncludes"]


# ── Trợ lý người dân (handfree) ──
from app.channels.handfree.chat import flow  # noqa: E402
from app.channels.handfree.chat import script_vi as vi  # noqa: E402
from app.channels.handfree.chat.intents import Intent  # noqa: E402

# Bản trợ lý biết gắn ô ảnh đầu trang ở bước đính kèm (supportsBcaPagePhotos) mới được dẫn vào thủ tục này (24/11).
CAPS = {"supportsBcaDangKyXe": True, "supportsBcaPagePhotos": True}


def test_tro_ly_cung_key_url_detect_hien_moi_tinh_va_chi_xin_giay_o_trang_nhap_thong_tin():
    from app.channels.handfree import procedure_registry as hf

    proc = hf.get_procedure(KEY)
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert proc["keKhaiUrl"] == link["url"] and proc["detect"] == registry.get_procedure(KEY)["detect"]
    assert proc["requiresCapability"] == "supportsBcaPagePhotos" and proc["hasAttachmentStep"] is True
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
CASE_CAPS = {**CAPS, "supportsLaiChauFeeStep": True, "supportsBcaCaseStep": True}
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
    # Đọc được ô Loại xe (bắt buộc, chưa chọn) → thẻ chọn + mời chọn Loại xe; user 24/11: chưa chọn đủ thì ẩn nút cam
    # Đồng ý và tiếp tục, câu đuôi báo chọn đủ nút mới hiện.
    r = _turn(conv, "action", "lc_result_report", {"groups": [LOAI_XE], "prepared": []})
    rows = r.cards[0]["rows"]
    assert [row["label"] for row in rows] == ["Loại xe"]
    assert [o["label"] for o in rows[0]["options"]] == ["Ô tô", "Xe mô tô"]
    trail = r.actions[0]["md"]
    assert "**Loại xe**" in trail and trail.endswith(vi.LC_CASE_WAIT["md"])
    assert not r.chips
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
    # Cổng hiện thêm ô bắt buộc còn trống (ảnh 24/11: chọn Ô tô xong còn Loại biển số) → vẫn ẩn nút.
    assert not r.chips
    # Đủ ô → câu hướng dẫn bấm Đồng ý và tiếp tục + hiện nút cam; bấm nút cam → trợ lý bấm nút cổng.
    groups[2]["value"] = "Đăng ký lần đầu"
    r = _turn(conv, "action", "lc_result_report", {"groups": groups, "prepared": []})
    assert "Thông tin người" in r.actions[0]["md"] and vi.LC_CASE_WAIT["md"] not in r.actions[0]["md"]
    assert r.chips == [lai_chau.next_chip()]
    assert _turn(conv, "action", "lc_next").actions == [{"type": "lc_next"}]
    # Nói "bước tiếp theo" ở trang này cũng bấm Đồng ý và tiếp tục.
    assert flow.next_step_by_voice(conv, "bước tiếp theo", {"lcStep": 1}).value == "lc_next"
    # Sang trang nhập thông tin: luồng chung xin giấy tờ như cũ; các bước sau không có nút Lai Châu.
    _turn(conv, "event", "page_status", {"loggedIn": True, "formKind": "standard", "lcStep": 0})
    assert conv["state"] in ("ask_doc_method", "consent")
    assert lai_chau.voice_intent(conv, "bước tiếp theo", {"lcStep": 0}) is None
    reply = flow.Reply("x", "x")
    assert lai_chau.fill_report_reply(conv, proc, reply) is reply and not reply.chips


PC08 = ["PC08-Điểm ĐK Đường Láng", "PC08-Điểm ĐK Thái Hà", "PC08-Điểm ĐK Hà Đông"]
CONG_AN_XA = [f"Công an {x}" for x in ("Xã Hương Sơn", "Xã Hồng Sơn", "Phường Yên Sở", "Phường Hoàng Liệt",
                                         "Phường Láng", "Phường Ngọc Hà", "Phường Ba Đình", "Xã Ba Đình")]
DIEM_DANG_KY = {"name": "diemDangKy", "present": True, "value": "", "options": PC08 + CONG_AN_XA, "fixed": False,
                "label": "Điểm đăng ký", "required": True}


def _diem_row(r):
    return next(row for row in r.cards[0]["rows"] if row["name"] == "diemDangKy")


def test_tro_ly_diem_dang_ky_chi_bay_pc08_va_cong_an_xa_phuong_cua_tai_khoan():
    """User 24/11: ô Điểm đăng ký chỉ hiện các điểm PC08 + một nút đăng ký tại Công an xã/phường của tài khoản."""
    import json

    from app.channels.handfree.chat import lai_chau

    conv = _case_conv()
    conv["auth_user"] = {"id": "u1", "tinh": "Thành phố Hà Nội", "xa": "Phường Ba Đình"}
    _turn(conv, "event", "page_status", {"loggedIn": True, "formKind": "", "lcStep": 1})
    loai_xe = {**LOAI_XE, "value": "Xe mô tô"}
    r = _turn(conv, "action", "lc_result_report", {"groups": [loai_xe, DIEM_DANG_KY], "prepared": []})
    row = _diem_row(r)
    assert [o["label"] for o in row["options"]] == [*PC08, "Đăng ký tại Công an Phường Ba Đình"]
    assert not r.chips
    # Bấm nút xã/phường → extension chọn đúng lựa chọn của cổng (không kèm chữ "Đăng ký tại").
    picked = json.loads(row["options"][-1]["send"].split("lc_result_pick:", 1)[1])
    r = _turn(conv, "action", "lc_result_pick", picked)
    assert r.actions[0]["type"] == "lc_result_set" and r.actions[0]["value"] == "Công an Phường Ba Đình"
    # Cổng đã chọn → nút xã/phường sáng, đủ ô nên hiện nút cam.
    chosen = {**DIEM_DANG_KY, "value": "Công an Phường Ba Đình"}
    r = _turn(conv, "action", "lc_result_report", {
        "groups": [loai_xe, chosen], "changed": {"name": "diemDangKy", "value": "Công an Phường Ba Đình", "ok": True}})
    assert [o["selected"] for o in _diem_row(r)["options"]] == [False, False, False, True]
    assert r.chips == [lai_chau.next_chip()]
    # Công dân tự chọn xã khác trên trang → thẻ hiện thêm đúng xã đang chọn.
    other = {**DIEM_DANG_KY, "value": "Công an Phường Láng"}
    r = _turn(conv, "action", "lc_result_report", {"groups": [loai_xe, other], "prepared": []})
    assert [o["label"] for o in _diem_row(r)["options"]][-2:] == ["Đăng ký tại Công an Phường Ba Đình",
                                                                 "Công an Phường Láng"]

    # Tài khoản chỉ ghi tên xã trùng cả phường lẫn xã → không đoán; tài khoản thiếu xã thì theo nơi làm thủ tục.
    conv["auth_user"]["xa"] = "Ba Đình"
    conv["location"]["ward"] = "Phường Ngọc Hà"
    r = _turn(conv, "action", "lc_result_report", {"groups": [loai_xe, DIEM_DANG_KY], "prepared": []})
    assert [o["label"] for o in _diem_row(r)["options"]][-1] == "Đăng ký tại Công an Phường Ngọc Hà"
    # Ảnh 24/11: tài khoản Khánh Hòa, cổng liệt kê xã của Hà Nội (thường trú của công dân) → vẫn đúng 4 nút; nút xã/phường
    # bấm thì nói rõ không có trong danh sách, gửi lại thẻ (sidebar khoá nút khi bấm), không chọn gì trên cổng.
    conv["auth_user"]["xa"], conv["location"]["ward"] = "Phường Nam Nha Trang", "Phường Nam Nha Trang"
    r = _turn(conv, "action", "lc_result_report", {"groups": [loai_xe, DIEM_DANG_KY], "prepared": []})
    row = _diem_row(r)
    assert [o["label"] for o in row["options"]] == [*PC08, vi.LC_WARD_POINT_ANY]
    card = r.cards
    picked = json.loads(row["options"][-1]["send"].split("lc_result_pick:", 1)[1])
    r = _turn(conv, "action", "lc_result_pick", picked)
    assert "**Công an Phường Nam Nha Trang**" in r.display_md and "trực tiếp trên trang" in r.display_md
    assert not r.actions and r.cards == card and not r.chips
    # Tài khoản không ghi xã nào → câu riêng.
    conv["auth_user"]["xa"], conv["location"]["ward"] = "", ""
    _turn(conv, "action", "lc_result_report", {"groups": [loai_xe, DIEM_DANG_KY], "prepared": []})
    assert "chưa ghi xã/phường" in _turn(conv, "action", "lc_result_pick", picked).display_md
    # Danh sách không có điểm PC08 (cổng khác) → giữ danh sách cũ.
    plain = {**DIEM_DANG_KY, "options": CONG_AN_XA}
    r = _turn(conv, "action", "lc_result_report", {"groups": [loai_xe, plain], "prepared": []})
    assert [o["label"] for o in _diem_row(r)["options"]] == CONG_AN_XA


def test_tro_ly_ban_cu_chua_co_co_trang_chon_truong_hop_thi_giu_luong_cu():
    from app.channels.handfree.chat import lai_chau
    from app.channels.handfree import procedure_registry as hf

    conv = _case_conv({**CAPS, "supportsLaiChauFeeStep": True})
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
    # Ô bắt buộc trống mà chưa đọc được lựa chọn cũng tính là chưa chọn → ẩn nút, chọn trên trang xong mới hiện.
    assert r.actions[0]["md"].endswith(vi.LC_CASE_WAIT["md"]) and not r.chips
    # Có danh sách → mời chọn trên thẻ.
    groups[3] = {**groups[3], "options": ["Đội CSGT số 1", "Công an phường Từ Liêm"], "fixed": False}
    r = _turn(conv, "action", "lc_result_report", {"groups": groups, "prepared": []})
    assert "Công dân chọn **Điểm đăng ký**" in r.actions[0]["md"] and not r.chips
    # Bấm Đồng ý và tiếp tục (nói "tiếp tục") mà cổng chặn → báo lời chặn + đọc lại thẻ (không làm sẵn gì), không kèm nút
    # bấm lại: lượt đọc lại tự hiện nút khi đủ ô.
    r = _turn(conv, "action", "lc_step_report", {"clicked": True, "message": "Còn trống: Điểm đăng ký"})
    assert "Còn trống: Điểm đăng ký" in r.display_md and not r.chips
    assert r.actions == [{"type": "lc_result_scan", "groups": [{"name": "*"}], "prepare": False}]
    # Ô trên trang đổi sau lượt đọc (cổng tải chậm / công dân tự chọn) → đọc lại.
    assert _turn(conv, "action", "lc_case_changed").actions == r.actions
    # Đã rời trang chọn trường hợp → im.
    _turn(conv, "event", "page_status", {"loggedIn": True, "formKind": "standard", "lcStep": 0})
    assert not _turn(conv, "action", "lc_case_changed").actions


# ── Ba ô ảnh đầu trang (user 24/11/2026): Ảnh phương tiện + hai mặt chứng từ nguồn gốc (Phiếu kiểm tra chất lượng xuất
# xưởng) — khuôn xe nhập khẩu 1.013066. ──
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


PHIEU_P1 = ("CÔNG TY TNHH XE MÁY MẪU\nPHIẾU KIỂM TRA CHẤT LƯỢNG XUẤT XƯỞNG\nDùng cho xe mô tô, xe gắn máy\n"
            "Số seri phiếu: AB 0000001\nNhãn hiệu: HIEUXE  Số loại: MX1")
PHIEU_P2 = ("THÔNG SỐ KỸ THUẬT\nKhối lượng bản thân: 98 kg\nKích thước bao: 1850 x 680 x 1080 mm\n"
            "Chiều dài cơ sở: 1250 mm\nDung tích xi lanh: 109 cm3\nCông suất lớn nhất: 6,4 kW")
GIAY_KHAI = ("GIẤY KHAI ĐĂNG KÝ XE (Mẫu ĐKX10)\nTên chủ xe: NGUYỄN VĂN AN\nSố seri Phiếu kiểm tra chất lượng xuất "
             "xưởng: AB 0000001\nDung tích xi lanh, công suất lớn nhất, khối lượng bản thân, kích thước")
CCCD_TEXT = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM CĂN CƯỚC CÔNG DÂN Số định danh cá nhân Họ, chữ đệm và tên khai sinh " * 2


def _run_with_photos(monkeypatch, files, texts, options=None):
    import asyncio

    from app.pipelines._shared.compact_agent import runner as compact_runner
    from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process import runner as xe_runner
    from app.services import ocr

    async def fake_ocr(ocr_files, **_kwargs):
        return [{"name": f["name"], "text": texts.get(f["name"], "")} for f in ocr_files]

    async def fake_run(files_by_role, **kwargs):
        await kwargs["ocr_fn"](compact_runner.flatten(files_by_role))
        return {"fields": [{"name": k, "value": v} for k, v in HO_SO.items()]}

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(compact_runner, "run", fake_run)
    return asyncio.run(xe_runner.run({"": files}, dict(options or {})))


def test_runner_gan_anh_phuong_tien_va_hai_mat_phieu_xuat_xuong_vao_o_dau_trang(monkeypatch):
    import base64

    files = [
        {"name": "giay_khai.png", "type": "image/png", "dataUrl": _data_url("image/png", _photo((240, 240, 240)))},
        {"name": "phieu_xuat_xuong.pdf", "type": "application/pdf", "dataUrl": _data_url("application/pdf", _pdf(2))},
        {"name": "IMG_0001.png", "type": "image/png", "dataUrl": _data_url("image/png", _photo())},
    ]
    texts = {"giay_khai.png": GIAY_KHAI,
             "phieu_xuat_xuong.pdf": f"───── Trang 1/2 ─────\n{PHIEU_P1}\n───── Trang 2/2 ─────\n{PHIEU_P2}"}
    res = _run_with_photos(monkeypatch, files, texts)
    photos = res["fields"][:3]
    assert [f["name"] for f in photos] == ["AnhPhuongTien", "AnhNguonGocMatTruoc", "AnhNguonGocMatSau"]
    assert [f["match"] for f in photos] == ["anh phuong tien", "nguon goc mat truoc", "nguon goc mat sau"]
    assert {f["comp"] for f in photos} == {"bca-photo"}
    # Giấy khai có nhắc "phiếu kiểm tra chất lượng xuất xưởng" + thông số xe nhưng KHÔNG lấy làm chứng từ nguồn gốc.
    assert [f["sourceFileName"] for f in photos] == ["IMG_0001.png", "phieu_xuat_xuong.pdf", "phieu_xuat_xuong.pdf"]
    for field in photos:
        jpeg = base64.b64decode(field["value"]["dataUrl"].split(",", 1)[1])
        assert jpeg[:2] == b"\xff\xd8" and len(jpeg) < 2_000_000  # cổng chỉ nhận .jpg / .png dưới 2 MB
    note = next(e for e in res["errors"] if e.startswith("Đã gắn ảnh"))
    assert "trang 1 của 'phieu_xuat_xuong.pdf' → ô Ảnh chứng từ nguồn gốc mặt trước" in note
    assert "trang 2 của 'phieu_xuat_xuong.pdf' → ô Ảnh chứng từ nguồn gốc mặt sau" in note
    assert "Phiếu kiểm tra chất lượng xuất xưởng" in note and "nhập khẩu" not in note
    # Câu Tra cứu thôi nhắc tự tải ảnh.
    assert mapper.TRA_CUU_NO_PHOTO_WARNING in res["errors"] and mapper.TRA_CUU_WARNING not in res["errors"]
    assert not any(e.startswith("Chưa có ảnh") for e in res["errors"])


def test_runner_phieu_chup_roi_hai_mat_va_thieu_anh_xe_thi_bao_o_phai_tai_tay(monkeypatch):
    from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process import runner as nk_runner
    from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process import runner as xe_runner

    page = xe_runner.phieu_xuat_xuong_page
    assert page(PHIEU_P1) and page(PHIEU_P2)
    assert not page(GIAY_KHAI) and not page(CCCD_TEXT) and not page("HÓA ĐƠN GIÁ TRỊ GIA TĂNG\nDung tích xi lanh")
    # Hai mặt phiếu chụp rời (mỗi mặt một tệp ảnh): mặt sau không có tiêu đề vẫn nhận nhờ bảng thông số kỹ thuật.
    pages = {0: [PHIEU_P1], 1: ["Ảnh xe"], 2: [PHIEU_P2]}
    assert nk_runner.find_origin_pages(pages, skip={1}, is_origin=page) == [(0, 0), (2, 0)]
    # Tệp gộp: trang 1 phiếu, trang 2 thẻ căn cước → KHÔNG lấy trang căn cước làm mặt sau; không có ảnh xe.
    files = [{"name": "ho_so.pdf", "type": "application/pdf", "dataUrl": _data_url("application/pdf", _pdf(2))}]
    texts = {"ho_so.pdf": f"───── Trang 1/2 ─────\n{PHIEU_P1}\n───── Trang 2/2 ─────\n{CCCD_TEXT}"}
    res = _run_with_photos(monkeypatch, files, texts)
    assert [f["name"] for f in res["fields"] if f.get("comp") == "bca-photo"] == ["AnhNguonGocMatTruoc"]
    missing = next(e for e in res["errors"] if e.startswith("Chưa có ảnh"))
    assert "Ảnh phương tiện" in missing and "Ảnh chứng từ nguồn gốc mặt sau" in missing and "mặt trước" not in missing
    assert "Phiếu kiểm tra chất lượng xuất xưởng" in missing


def test_tro_ly_luot_dien_khong_gan_anh_buoc_dinh_kem_tach_hay_khong_cung_ke_hoach(monkeypatch):
    import asyncio

    from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.attach import plan
    from app.process.schemas import FileItem

    files = [
        {"name": "phieu_xuat_xuong.pdf", "type": "application/pdf", "dataUrl": _data_url("application/pdf", _pdf(2))},
        {"name": "IMG_0001.png", "type": "image/png", "dataUrl": _data_url("image/png", _photo())},
    ]
    texts = {"phieu_xuat_xuong.pdf": f"───── Trang 1/2 ─────\n{PHIEU_P1}\n───── Trang 2/2 ─────\n{PHIEU_P2}"}
    # Lượt điền của trợ lý (pagePhotosAtAttach): không gắn ảnh, câu Tra cứu không nhắc tự tải ảnh.
    res = _run_with_photos(monkeypatch, files, texts, {"pagePhotosAtAttach": True})
    assert not [f for f in res["fields"] if f.get("comp") == "bca-photo"]
    assert mapper.TRA_CUU_NO_PHOTO_WARNING in res["errors"]
    assert not any(e.startswith(("Đã gắn ảnh", "Chưa có ảnh")) for e in res["errors"])

    # Bước đính kèm: kế hoạch không có mục bảng, chỉ ba ô ảnh; bật / tắt / client cũ "Tách giấy tờ" ra cùng kết quả.
    items = [FileItem(name=f["name"], type=f["type"], dataUrl=f["dataUrl"], role="") for f in files]
    results = [asyncio.run(plan(items, {"splitDocuments": split})) for split in (True, False, None)]
    for result in results:
        assert result["attachments"] == [] and result["nothingToAttach"] is True
        assert [f["name"] for f in result["pageFields"]] == ["AnhPhuongTien", "AnhNguonGocMatTruoc", "AnhNguonGocMatSau"]
        assert [f["sourceFileName"] for f in result["pageFields"]] == [
            "IMG_0001.png", "phieu_xuat_xuong.pdf", "phieu_xuat_xuong.pdf"]
        assert result["errors"] == []
    assert results[0]["pageFields"][1]["value"] == results[1]["pageFields"][1]["value"]
    # Thiếu ảnh xe → nói rõ ô nào, mời "đính kèm lại", tên đúng chứng từ của thủ tục này.
    only_phieu = asyncio.run(plan(items[:1], {}))
    assert [f["name"] for f in only_phieu["pageFields"]] == ["AnhNguonGocMatTruoc", "AnhNguonGocMatSau"]
    assert any("Ảnh phương tiện" in e and "đính kèm lại" in e and "xuất xưởng" in e for e in only_phieu["errors"])


def test_tro_ly_thanh_phan_ho_so_co_anh_xe_va_hai_mat_phieu_buoc_dinh_kem_la_o_anh_dau_trang():
    from app.channels.handfree import procedure_registry as hf
    from app.channels.handfree.chat import field_review
    from app.upload_session import classify

    proc = hf.get_procedure(KEY)
    sibling = hf.get_procedure("dang-ky-xe-lan-dau-nhap-khau")
    for field in ("requiresCapability", "hasAttachmentStep", "bcaPagePhotos", "askBeforeAttach", "docsAdjustRefill",
                  "supportsSplitDocuments", "laiChauFeeStep"):
        assert proc.get(field) == sibling.get(field), field
    assert field_review.bca_nth(proc) and flow._bca_nth(proc)
    docs = proc["requiredDocs"]
    slot = next(d for d in docs if d["key"] == "anh_phuong_tien")
    assert not slot.get("optional") and slot["sides"] == 1
    assert "2 mặt" in next(d for d in docs if d["key"] == "phieu_xuat_xuong")["name"]
    assert "Ảnh chụp phương tiện" in proc["uploadHint"]
    files = [{"name": "IMG_0002.png", "type": "image/png", "dataUrl": _data_url("image/png", _photo())},
             {"name": "cccd.png", "type": "image/png", "dataUrl": _data_url("image/png", _photo((240, 240, 240)))}]
    assert classify._vehicle_photo_indexes(files, [{"text": ""}, {"text": CCCD_TEXT}], docs, None) == {0}
    # Câu hỏi trước khi đính / báo đính xong dùng chung với xe nhập khẩu → không nói "nhập khẩu", "hải quan".
    for text in (vi.REVIEW_ATTACHMENT_PAGE_PHOTOS_BCA["md"], vi.ATTACH_DONE_PAGE_PHOTOS_BCA["md"]):
        assert "nhập khẩu" not in text and "hải quan" not in text
