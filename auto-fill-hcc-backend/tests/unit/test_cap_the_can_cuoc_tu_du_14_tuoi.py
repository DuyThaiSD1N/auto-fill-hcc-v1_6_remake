"""Cấp thẻ căn cước cho người từ đủ 14 tuổi trở lên 2.000200 / 1.014061 (Cổng DVC Bộ Công an): mapper ô form + nối
registry / link kê khai / trợ lý."""
from app.pipelines.cap_the_can_cuoc_tu_du_14_tuoi.process import mapper
from app.pipelines.cap_the_can_cuoc_tu_du_14_tuoi.process.prompt import EXTRA_RULES
from app.pipelines.cap_the_can_cuoc_tu_du_14_tuoi.process.schema import ALLOWED
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "cap-the-can-cuoc-tu-du-14-tuoi"
# Hồ sơ mẫu bịa: học sinh vừa đủ 14 tuổi tự khai CC01 / DC01, nộp Công an xã, cấp mới.
HO_SO = {
    "CoQuan_Tinh": "tỉnh Lai Châu", "CoQuan_Xa": "Công an xã Mẫu Sơn", "LoaiCap": "Cấp mới",
    "NguoiCanCap_HoTen": "Hoàng Thị Lan", "NguoiCanCap_NgaySinh": "3/9/2012", "NguoiCanCap_GioiTinh": "Nữ",
    "NguoiCanCap_SoDinhDanh": "0123 1200 0001", "NguoiCanCap_SoCMND": "………",
    "NguoiCanCap_SoDienThoai": "………", "NguoiCanCap_Email": "",
    "NguoiDaiDien_HoTen": "", "NguoiDaiDien_SoDinhDanh": "", "NguoiDaiDien_QuanHe": "",
    "Cha_HoTen": "HOÀNG VĂN AN", "Cha_SoDinhDanh": "012085000002",
    "Me_HoTen": "Vàng Thị Mai", "Me_SoDinhDanh": "012187000003",
}


def _enrich(values: dict, options=None) -> list[dict]:
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def _by(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def _field(out: list[dict], name: str) -> dict:
    return next(f for f in out if f["name"] == name)


def test_tu_khai_cap_xa_radio_theo_tai_khoan_va_phan_ii_chi_khi_khai_thay():
    out = _enrich(HO_SO)
    names = [f["name"] for f in out]
    by = _by(out)
    # Phần I khoá theo tài khoản; khối tích hợp BHYT ẩn trên cổng → không phát.
    assert not {"txtFULLNAME_NDN", "txtIDENTIFY_NUMBER_NDN", "chkTichHopBHYT", "txtMaSoBHYT"} & set(by)
    # Radio "Đối tượng kê khai" KHÔNG chốt theo người ký trên giấy: extension so tài khoản Phần I với người cần cấp.
    declarant = _field(out, "radIsNCC")
    assert declarant["comp"] == "bca-declarant" and names[0] == "radIsNCC"
    assert declarant["value"] == {"selfId": "chkIS_NCC", "otherId": "chkIS_NOT_NCC", "otherBlock": "divCheck_NDN",
                                  "accountNameId": "txtFULLNAME_NDN", "accountIdId": "txtIDENTIFY_NUMBER_NDN",
                                  "subject": {"name": "HOÀNG THỊ LAN", "id": "012312000001"}}
    # Khối Phần II vẫn phát sẵn (cha/mẹ đăng nhập khai thay) nhưng chỉ điền khi extension chọn "khai thay".
    assert by["txtFULLNAME_NCC"] == "HOÀNG THỊ LAN" and by["txtBIRTHDATE_NCC"] == "03/09/2012"
    assert by["cboGENDER_ID_NCC"] == "Nữ" and by["txtIDENTIFY_NUMBER_NCC"] == "012312000001"
    for name in ("txtFULLNAME_NCC", "txtBIRTHDATE_NCC", "cboGENDER_ID_NCC", "txtIDENTIFY_NUMBER_NCC",
                 "cboRELATIONSHIP_WITH_NDN"):
        assert _field(out, name)["bcaOtherOnly"] is True, name
    for name in ("cboLyDoCap", "radCapThucHien", "cboORG"):
        assert "bcaOtherOnly" not in _field(out, name), name
    relation = _field(out, "cboRELATIONSHIP_WITH_NDN")
    assert relation["comp"] == "bca-relation" and relation["value"]["fallback"] == "Người đại diện hợp pháp"
    assert relation["value"]["people"] == [
        {"relation": "Mẹ", "name": "VÀNG THỊ MAI", "id": "012187000003"},
        {"relation": "Cha", "name": "HOÀNG VĂN AN", "id": "012085000002"},
    ]
    # SĐT / email giấy chấm chấm → không điền.
    assert "txtPHONE_NUMBER_NDN" not in by and "txtEMAIL_ADDRESS_NDN" not in by
    lydo = _field(out, "cboLyDoCap")
    assert lydo["value"] == "Cấp thẻ căn cước lần đầu" and "default" not in lydo
    assert names.index("cboLyDoCap") < names.index("radCapThucHien") < names.index("cboORG")
    agency = _field(out, "cboORG")
    assert agency["comp"] == "bca-agency" and agency["onlyIfEmpty"] is True and "default" not in agency
    assert agency["value"] == {"province": "Tỉnh Lai Châu", "ward": "Xã Mẫu Sơn", "cityId": "cboORGTinh",
                               "wardId": "cboORGXa", "readySelect": "cboDiaChiTram", "readyPick": True}
    assert by["radCapThucHien"] == "Cấp Xã"


def test_ly_do_cap_lan_dau_hay_chuyen_tu_cmnd():
    reason = lambda **kw: _field(_enrich({**HO_SO, **kw}), "cboLyDoCap")  # noqa: E731
    # Người lớn tuổi có CMND 9 số của chính mình → chuyển từ CMND 9 số.
    got = reason(NguoiCanCap_NgaySinh="12/05/1990", NguoiCanCap_SoCMND="045 123 456", LoaiCap="")
    assert got["value"] == "Cấp thẻ căn cước chuyển từ CMND 9 số" and "default" not in got
    # Sinh 2012 (đủ 14 tuổi khi đã thôi cấp CMND) mà có số 9 chữ số = LLM chép số của cha/mẹ → vẫn lần đầu.
    assert reason(NguoiCanCap_SoCMND="045123456")["value"] == "Cấp thẻ căn cước lần đầu"
    assert reason(LoaiCap="Chuyển từ CMND 12 số")["value"] == "Cấp thẻ căn cước chuyển từ CMND 12 số"
    assert reason(LoaiCap="Cấp từ chứng minh nhân dân")["value"] == "Cấp thẻ căn cước chuyển từ CMND 9 số"
    # Giấy không ghi loại cấp → lần đầu, tô vàng cho cán bộ soát.
    got = reason(LoaiCap="")
    assert got["value"] == "Cấp thẻ căn cước lần đầu" and got["default"] is True


def test_so_dien_thoai_email_phan_i_theo_nguoi_khai_tren_giay():
    by = _by(_enrich({**HO_SO, "NguoiCanCap_SoDienThoai": "0912 000 111", "NguoiCanCap_Email": "Lan.Mau@Example.com"}))
    assert by["txtPHONE_NUMBER_NDN"] == "0912000111" and by["txtEMAIL_ADDRESS_NDN"] == "lan.mau@example.com"
    # Giấy ghi cha khai thay, có số của cha → ưu tiên số người khai thay.
    by = _by(_enrich({**HO_SO, "NguoiCanCap_SoDienThoai": "0912000111", "NguoiDaiDien_HoTen": "Hoàng Văn An",
                      "NguoiDaiDien_QuanHe": "Cha", "NguoiDaiDien_SoDienThoai": "0987 000 222"}))
    assert by["txtPHONE_NUMBER_NDN"] == "0987000222"


def test_so_dinh_danh_trung_cha_me_thi_bo_va_nop_cong_an_tinh():
    by = _by(_enrich({**HO_SO, "NguoiCanCap_SoDinhDanh": "012085000002"}))
    assert "txtIDENTIFY_NUMBER_NCC" not in by and by["radIsNCC"]["subject"] == {"name": "HOÀNG THỊ LAN"}
    # Không đọc được người cần cấp → không phát radio, khối Phần II cũng không.
    by = _by(_enrich({**HO_SO, "NguoiCanCap_HoTen": "", "NguoiCanCap_SoDinhDanh": ""}))
    assert not {"radIsNCC", "txtFULLNAME_NCC", "cboRELATIONSHIP_WITH_NDN"} & set(by)
    by = _by(_enrich({**HO_SO, "CoQuan_Tinh": "Đồng Nai", "CoQuan_Xa": ""}))
    assert by["radCapThucHien"] == "Cấp Tỉnh"
    assert by["cboORG"]["province"] == "Thành phố Đồng Nai" and by["cboORG"]["ward"] == ""


def test_giay_khong_ghi_co_quan_thi_lay_xa_tai_khoan_to_vang():
    values = {k: v for k, v in HO_SO.items() if not k.startswith("CoQuan_")}
    options = mapper.with_account_process_options({}, {"tinh": "Lai Châu", "xa": "Phường Mẫu"}, KEY)
    out = _enrich(values, options)
    assert _field(out, "cboORG")["value"]["ward"] == "Phường Mẫu" and _field(out, "cboORG")["default"] is True
    assert _field(out, "radCapThucHien")["default"] is True
    assert "_accountAgency" not in mapper.with_account_process_options({}, {"tinh": "A", "xa": "B"}, "khac")
    kept = {"_accountAgency": {"tinh": "A", "xa": "B"}}
    assert mapper.with_account_process_options(kept, None, "cap-the-can-cuoc-duoi-14-tuoi") == kept


def test_prompt_va_schema():
    assert "Mã số thẻ BHYT KHÔNG phải số định danh" in EXTRA_RULES and "Số CMND 9 số" in EXTRA_RULES
    assert {"LoaiCap", "NguoiCanCap_SoCMND", "NguoiCanCap_Email", "NguoiDaiDien_Email", "Cha_SoDinhDanh",
            "Me_SoDinhDanh"} <= ALLOWED


def test_registry_va_link_ke_khai():
    assert registry.get_pipeline(KEY) is not None
    assert registry.get_attach_pipeline(KEY) is None
    proc = registry.get_procedure(KEY)
    assert proc["label"] == "Cấp thẻ căn cước cho người từ đủ 14 tuổi trở lên"
    assert proc["hasAttachmentStep"] is False
    assert proc["detect"]["urlIncludes"] == ["dvc-CCCD-tren-14-tuoi.html"]
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["label"] == proc["label"] and link["code"] == "2.000200"
    assert link["url"].endswith("dvc-CCCD-tren-14-tuoi.html") and link["needsAgencySelect"] is False


# ── Trợ lý người dân (handfree) ──
from app.channels.handfree.chat import flow  # noqa: E402
from app.channels.handfree.chat.intents import Intent  # noqa: E402

CAPS = {"supportsBcaCanCuoc": True}


def test_tro_ly_entry_cung_key_url_detect_va_hien_moi_tinh():
    from app.channels.handfree import procedure_registry as hf

    proc = hf.get_procedure(KEY)
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert proc["keKhaiUrl"] == link["url"] and proc["detect"] == registry.get_procedure(KEY)["detect"]
    assert proc["bcaPortal"] is True and proc["bcaAgencyFromDocs"] is True and proc["hasAttachmentStep"] is False
    assert proc["requiresCapability"] == "supportsBcaCanCuoc" and "provinceOnly" not in proc
    assert hf.get_pipeline(KEY) is registry.get_pipeline(KEY)
    for slug in ("khanhhoa", "laichau", "bacninh", ""):
        assert KEY in {p["key"] for p in hf.public_list_for(slug)}, slug


def test_tro_ly_thay_trang_ke_khai_sang_thang_giay_to():
    conv = {"state": "greet", "procedure_key": None, "location": {}}
    r = flow._to_confirm_procedure(conv, KEY)
    assert "chưa hỗ trợ" in r.display_md and not r.actions
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": dict(CAPS),
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Xã Mẫu Sơn"}}
    r = flow._to_confirm_procedure(conv, KEY)
    assert conv["state"] == "guide_login" and r.actions[0]["type"] == "navigate"
    r = flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True}))
    assert conv["state"] in ("ask_doc_method", "consent") and conv["agency_done"] is True
    assert "nơi cư trú" not in (r.display_md or "")


def test_tro_ly_dien_xong_nhac_kiem_tra_csdl_cam_doan_roi_luu_tiep_tuc():
    import asyncio
    from unittest import mock

    from app.channels.handfree.chat import pipeline_runner, tracing

    assert pipeline_runner.with_cap_the_can_cuoc_tu_du_14_tuoi_account_process_options(
        {}, {"tinh": "Lai Châu", "xa": "Xã Mẫu Sơn"}, KEY)["_accountAgency"]["xa"] == "Xã Mẫu Sơn"
    conv = {"_id": "c1", "state": "filling", "procedure_key": KEY, "docs_target": "declaration",
            "auto_attach_after_fill": True, "upload_session_id": "s1", "location": {},
            "client_capabilities": dict(CAPS)}
    with mock.patch.object(tracing, "set_report", mock.AsyncMock()):
        r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {"filled": 9})))
    assert "Lưu và Tiếp tục" in r.display_md and "Đính kèm" not in r.display_md


def test_tro_ly_ten_mong_va_cau_chon_thu_tuc():
    from app.channels.handfree.chat import script_mong
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS

    assert script_mong.PROCEDURE_HMONG[KEY]
    assert "làm căn cước lần đầu" in PROCEDURE_HINTS[KEY]


def test_tro_ly_trang_ke_khai_khong_nhan_ra_form_van_la_buoc_ke_khai():
    """18/11/2026: bấm "Đã đưa đủ giấy tờ" mà extension báo formKind rỗng → trợ lý nói "chưa biết trang đang ở bước
    nào". Khối cơ quan (bcaAgencyBlock) chỉ có trên trang kê khai của cổng Bộ Công an → coi là bước kê khai."""
    from app.channels.handfree import procedure_registry as hf

    proc = hf.get_procedure(KEY)
    assert flow._resolve_docs_target(proc, {"formKind": "", "bcaAgencyBlock": True}) == "declaration"
    # Sidebar cũ không gửi bcaAgencyBlock: đã qua khối cơ quan (agency_done) thì vẫn là kê khai.
    assert flow._resolve_docs_target(proc, {"formKind": ""}, {"agency_done": True}) == "declaration"
    assert flow._resolve_docs_target(proc, {"formKind": ""}, {"agency_done": False}) == ""
    # Thủ tục cổng khác không bị ảnh hưởng.
    other = hf.get_procedure("dang-ky-xe-lan-dau-san-xuat-lap-rap-trong-nuoc")
    assert flow._resolve_docs_target(other, {"formKind": "", "bcaAgencyBlock": True}, {"agency_done": True}) == ""
    conv = {"procedure_key": KEY, "state": "collecting_docs", "agency_done": True, "docs_target": ""}
    assert flow._remember_docs_target(conv, proc, {"formKind": "", "bcaAgencyBlock": True})[0] == "declaration"
    assert conv["docs_target"] == "declaration"
