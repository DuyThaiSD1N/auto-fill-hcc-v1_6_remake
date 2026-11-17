"""Thông báo lưu trú (Cổng DVC Bộ Công an): mapper ô trang chính + danh sách người lưu trú cho modal."""
from app.pipelines.thong_bao_luu_tru.process import mapper
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "thong-bao-luu-tru"

GUEST_1 = {
    "hoTen": "Nguyen Van A",
    "ngaySinh": "3/8/1990",
    "gioiTinh": "Nam",
    "soDinhDanh": "0010 9000 0001",
    "quocTich": "Việt Nam",
    "noiCuTru": {"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "Phường Ba Đình", "chiTietDuoiXa": "Số 1 ngõ 2"},
    "loaiCuTru": "thường trú",
    "lyDo": "Thăm thân",
    "tuNgay": "12/11/2026",
    "denNgay": "16/11/2026",
}


def _enrich(**values):
    out = mapper.enrich([{"name": k, "value": v} for k, v in values.items()])
    return {f["name"]: (f["comp"], f["value"]) for f in out}


def _guest_fields(guest: dict) -> dict:
    return {f["id"]: f["value"] for f in guest["fields"]}


def test_co_so_luu_tru_va_nguoi_luu_tru_ra_dung_o():
    v = _enrich(
        CoSo_LoaiHinh="Hộ gia đình",
        CoSo_DiaChi={"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "Phường Ba Đình", "chiTietDuoiXa": "Số 9 tổ 3"},
        NguoiLuuTru=[GUEST_1],
    )
    assert v["accomStay_cboACCOMMODATION_TYPE"] == ("dom-select", "Hộ gia đình")
    assert v["accomStay_txtADDRESS"] == ("dom-input", "Số 9 tổ 3")
    comp, guests = v["listTTNguoiLuuTru"]
    assert comp == "bca-guest-list" and len(guests) == 1
    g = _guest_fields(guests[0])
    assert guests[0]["hoTen"] == "NGUYEN VAN A" and guests[0]["soDinhDanh"] == "001090000001"
    assert g["guest_cboDOB_FMT"] == "dd/mm/yyyy" and g["guest_txtDOB"] == "03/08/1990"
    assert g["guest_cboGENDER_ID"] == "Nam"
    assert g["guest_txtIDCARD_NUMBER"] == "001090000001"
    assert g["guest_mulNATIONALITY"] == "Việt Nam"
    assert g["guest_radADDRESS_TYPE"] == "0"
    assert g["guest_cboRDPROVINCE_ID"] == "Thành phố Hà Nội"
    assert g["guest_cboRDADDRESS_ID"] == "Phường Ba Đình"
    assert g["guest_txtRDADDRESS"] == "Số 1 ngõ 2"
    assert g["guest_txtREASON"] == "Thăm thân"
    assert g["guest_txtSTART_DATE"] == "12/11/2026" and g["guest_txtEND_DATE"] == "16/11/2026"


def test_thu_tu_dien_trong_modal():
    _, guests = _enrich(NguoiLuuTru=[GUEST_1])["listTTNguoiLuuTru"]
    ids = [f["id"] for f in guests[0]["fields"]]
    # Định dạng trước ngày sinh; quốc tịch trước tỉnh/xã (chọn Việt Nam cổng mới mở khối địa chỉ trong nước).
    assert ids.index("guest_cboDOB_FMT") < ids.index("guest_txtDOB")
    assert ids.index("guest_mulNATIONALITY") < ids.index("guest_cboRDPROVINCE_ID") < ids.index("guest_cboRDADDRESS_ID")


def test_ngay_sinh_chi_co_nam_va_khong_bia_quoc_tich_khi_khong_co_so():
    _, guests = _enrich(NguoiLuuTru=[{"hoTen": "Tran Thi B", "ngaySinh": "2016", "lyDo": "Đi khám bệnh"}])[
        "listTTNguoiLuuTru"]
    g = _guest_fields(guests[0])
    assert g["guest_cboDOB_FMT"] == "yyyy" and g["guest_txtDOB"] == "2016"
    assert "guest_mulNATIONALITY" not in g and "guest_cboRDPROVINCE_ID" not in g


def test_so_dinh_danh_12_so_thi_quoc_tich_viet_nam_to_vang():
    guest = {**GUEST_1, "quocTich": ""}
    _, guests = _enrich(NguoiLuuTru=[guest])["listTTNguoiLuuTru"]
    nat = next(f for f in guests[0]["fields"] if f["id"] == "guest_mulNATIONALITY")
    assert nat["value"] == "Việt Nam" and nat["default"] is True


def test_ho_chieu_khong_vao_o_cccd():
    guest = {"hoTen": "John Doe", "soDinhDanh": "B1234567", "quocTich": "Hoa Kỳ", "lyDo": "Du lịch"}
    _, guests = _enrich(NguoiLuuTru=[guest])["listTTNguoiLuuTru"]
    g = _guest_fields(guests[0])
    assert g["guest_txtPASSPORT_NO"] == "B1234567" and "guest_txtIDCARD_NUMBER" not in g
    assert "guest_cboRDPROVINCE_ID" not in g, "người nước ngoài: không dựng khối địa chỉ trong nước"


def test_mot_nguoi_lap_lai_chi_them_mot_lan_va_bo_item_khong_ten():
    _, guests = _enrich(NguoiLuuTru=[GUEST_1, {**GUEST_1, "lyDo": "khác"}, {"soDinhDanh": "001090000002"}])[
        "listTTNguoiLuuTru"]
    assert len(guests) == 1


def test_loai_hinh_co_danh_sach_co_so_thi_khong_dien_ten():
    v = _enrich(CoSo_LoaiHinh="Cơ sở lưu trú du lịch", CoSo_Ten="Nhà nghỉ X")
    assert "accomStay_txtNAME_T" not in v
    v = _enrich(CoSo_LoaiHinh="Không rõ", CoSo_Ten="Nhà Y")
    assert "accomStay_cboACCOMMODATION_TYPE" not in v and v["accomStay_txtNAME_T"] == ("dom-input", "Nhà Y")


def test_registry_va_link_ke_khai():
    proc = registry.get_procedure(KEY)
    assert proc and proc["mode"] == "agent" and proc["hasAttachmentStep"] is False
    assert registry.get_pipeline(KEY) is not None
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "2.001159" and "thong-bao-luu-tru.html" in link["url"]


# ── Luồng trợ lý handfree ──
from app.channels.handfree.chat import flow  # noqa: E402
from app.channels.handfree.chat.intents import Intent  # noqa: E402

CAPS = {"supportsBcaGuestList": True, "supportsTickCommit": True}


def test_tro_ly_ban_cu_chua_biet_them_nguoi_luu_tru_thi_bao_cap_nhat():
    conv = {"state": "greet", "procedure_key": None, "location": {}}
    r = flow._to_confirm_procedure(conv, KEY)
    assert "chưa hỗ trợ" in r.display_md and not r.actions
    assert conv.get("state") != "guide_login"


def test_hoi_co_quan_theo_noi_luu_tru_khong_noi_tam_tru():
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": dict(CAPS),
            "location": {"province": "Thành phố Hà Nội", "province_slug": "ha_noi", "ward": "Phường Ba Đình"}}
    r = flow._to_confirm_procedure(conv, KEY)
    assert conv["state"] == "guide_login" and r.actions[0]["type"] == "navigate"
    r = flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True}))
    assert "nơi lưu trú" in r.display_md and "tạm trú" not in r.display_md
    assert [c["send"] for c in r.chips] == ["__action:bca_fill_agency"]


def test_dien_xong_khong_moi_dinh_kem_ma_nhac_cam_ket_roi_nop():
    import asyncio
    from unittest import mock

    from app.channels.handfree.chat import tracing

    conv = {"_id": "c1", "state": "filling", "procedure_key": KEY, "docs_target": "declaration",
            "auto_attach_after_fill": True, "upload_session_id": "s1", "location": {},
            "client_capabilities": dict(CAPS)}
    with mock.patch.object(tracing, "set_report", mock.AsyncMock()):
        r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {"filled": 3})))
    sends = [c["send"] for c in r.chips]
    assert conv["state"] == "reviewing" and "__action:confirm_review" not in sends
    assert sends[-1] == "__action:tick_commit"
    assert "người lưu trú" in r.display_md and "Tôi xin chịu trách nhiệm" in r.display_md
    assert "Đính kèm" not in r.display_md

    # Bấm nút cam ngay ở bước rà soát (không có bước đính kèm nên conv chưa sang done) → phát lệnh tích ô.
    r = asyncio.run(flow._handle_reviewing(conv, Intent("action", "tick_commit")))
    assert r.actions == [{"type": "tick_commit", "id": "chkCHECK_LIABILITY",
                          "label": "Tôi xin chịu trách nhiệm trước pháp luật về lời khai trên"}]
    assert not r.display_md
    r = asyncio.run(flow._handle_reviewing(conv, Intent("event", "commit_result", {"ok": True})))
    assert "Nộp hồ sơ" in r.display_md and r.actions == [{"type": "chip_used", "send": "__action:tick_commit"}]
    r = asyncio.run(flow._handle_reviewing(conv, Intent("event", "commit_result", {"ok": False})))
    assert "chưa tích được" in r.display_md and r.chips[0]["send"] == "__action:tick_commit"

    # "Đúng rồi" ở bước rà soát: không chuyển sang đính kèm, nhắc lại tích cam kết rồi nộp.
    r = asyncio.run(flow._handle_reviewing(conv, Intent("confirm")))
    sends = [c["send"] for c in r.chips]
    assert conv["state"] == "reviewing" and "__action:confirm_review" not in sends
    assert sends[-1] == "__action:tick_commit" and "Đính kèm" not in r.display_md


def test_luat_bat_nut_nop_nhan_trang_thong_bao_luu_tru():
    import re

    from app.procedures.portal_submit import portal_submit_rules

    rule = portal_submit_rules()["dichvucong.dancuquocgia.gov.vn"]
    assert re.match(rule["urlPattern"], "/portal/p/home/thong-bao-luu-tru.html")
    assert re.match(rule["urlPattern"], "/portal/p/home/dang-ky-tam-tru.html")
    assert not re.match(rule["urlPattern"], "/portal/p/home/xem-ho-so.html")
    assert "btnSaveSend" in rule["buttonIds"]


def test_url_ke_khai_handfree_trung_link_ke_khai():
    from app.channels.handfree.procedure_registry import get_procedure

    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert get_procedure(KEY)["keKhaiUrl"] == link["url"]



def test_co_quan_thuc_hien_theo_giay_dien_truoc_va_khong_de_noi_da_chon():
    out = mapper.enrich([{"name": "CoQuan_Tinh", "value": "Hà Nội"}, {"name": "CoQuan_Xa", "value": "Phường Ba Đình"},
                         {"name": "CoSo_LoaiHinh", "value": "Hộ gia đình"}])
    assert [f["name"] for f in out][:2] == ["cboRECEIVE_ORG", "accomStay_cboACCOMMODATION_TYPE"]
    agency = out[0]
    assert agency["comp"] == "bca-agency" and agency["onlyIfEmpty"] is True and "default" not in agency
    assert agency["value"] == {"province": "Thành phố Hà Nội", "ward": "Phường Ba Đình"}


def test_giay_khong_ghi_co_quan_thi_lay_xa_tai_khoan_to_vang():
    options = mapper.with_account_process_options({}, {"tinh": "Tỉnh Mẫu", "xa": "Phường Mẫu"}, KEY)
    by = {f["name"]: f for f in mapper.enrich([], options)}
    assert by["cboRECEIVE_ORG"]["value"]["ward"] == "Phường Mẫu" and by["cboRECEIVE_ORG"]["default"] is True
    # Thủ tục khác / client tự gửi khoá này → không gắn.
    assert mapper.ACCOUNT_AGENCY_OPTION not in mapper.with_account_process_options(
        {mapper.ACCOUNT_AGENCY_OPTION: {"tinh": "X", "xa": "Y"}}, {"tinh": "X", "xa": "Y"}, "khac")
