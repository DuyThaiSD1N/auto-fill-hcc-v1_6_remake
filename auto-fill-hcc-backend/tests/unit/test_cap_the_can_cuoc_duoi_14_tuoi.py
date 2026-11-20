"""Cấp thẻ căn cước cho người dưới 14 tuổi 1.012549 / 1.014062 (Cổng DVC Bộ Công an): mapper ô form + nối registry /
link kê khai / trợ lý."""
from app.pipelines.cap_the_can_cuoc_duoi_14_tuoi.process import mapper
from app.pipelines.cap_the_can_cuoc_duoi_14_tuoi.process.prompt import EXTRA_RULES
from app.pipelines.cap_the_can_cuoc_duoi_14_tuoi.process.schema import ALLOWED
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "cap-the-can-cuoc-duoi-14-tuoi"
# Hồ sơ mẫu bịa: mẹ kê khai thay con gái 8 tuổi, nộp Công an phường, nhận trực tiếp.
HO_SO = {
    "CoQuan_Tinh": "tỉnh Lai Châu", "CoQuan_Xa": "Công an phường Đoàn Kết",
    "NguoiCanCap_HoTen": "Le Thi Mai", "NguoiCanCap_NgaySinh": "5/3/2018", "NguoiCanCap_GioiTinh": "Nữ",
    "NguoiCanCap_SoDinhDanh": "0123 1800 0001",
    "NguoiDaiDien_HoTen": "Trần Thị Hoa", "NguoiDaiDien_SoDinhDanh": "012190000002",
    "NguoiDaiDien_QuanHe": "Mẹ – người đại diện hợp pháp",
    "NguoiDaiDien_SoDienThoai": "………", "NguoiDaiDien_Email": "",
    "Cha_HoTen": "LÊ VĂN NAM", "Cha_SoDinhDanh": "012088000003", "Me_HoTen": "TRẦN THỊ HOA", "Me_SoDinhDanh": "",
    "NhanKetQua_HinhThuc": "Trực tiếp tại Công an phường Đoàn Kết",
    "NhanKetQua_Tinh": "Lai Châu", "NhanKetQua_Xa": "Phường Đoàn Kết",
    "NhanKetQua_DiaChiChiTiet": "Số 3, tổ dân phố số 5, phường Đoàn Kết, tỉnh Lai Châu",
}


def _enrich(values: dict, options=None) -> list[dict]:
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def _by(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_me_ke_khai_thay_dien_phan_ii_co_quan_va_nhan_truc_tiep():
    out = _enrich(HO_SO)
    names = [f["name"] for f in out]
    by = _by(out)
    # Phần I khoá theo tài khoản cha/mẹ; Lý do cấp / Loại hồ sơ cổng tự khoá; không có radio người kê khai.
    assert not {"txtFULLNAME_NDN", "txtIDENTIFY_NUMBER_NDN", "cboLyDoCap", "cboLoaiHoSo", "radIsNCC"} & set(by)
    assert by["txtFULLNAME_NCC"] == "LE THI MAI" and by["txtBIRTHDATE_NCC"] == "05/03/2018"
    assert by["cboGENDER_ID_NCC"] == "Nữ" and by["txtIDENTIFY_NUMBER_NCC"] == "012318000001"
    # Quan hệ KHÔNG chốt theo giấy: extension so tài khoản VNeID ở Phần I với cha/mẹ trên giấy lúc điền.
    relation = next(f for f in out if f["name"] == "cboRELATIONSHIP_WITH_NDN")
    assert relation["comp"] == "bca-relation"
    assert relation["value"]["fallback"] == "Người đại diện hợp pháp"
    assert relation["value"]["accountNameId"] == "txtFULLNAME_NDN"
    assert relation["value"]["accountIdId"] == "txtIDENTIFY_NUMBER_NDN"
    # Mẹ: số định danh bù từ người kê khai trên giấy (thẻ căn cước nộp kèm) vì bảng người thân bỏ trống.
    assert relation["value"]["people"] == [
        {"relation": "Mẹ", "name": "TRẦN THỊ HOA", "id": "012190000002"},
        {"relation": "Cha", "name": "LÊ VĂN NAM", "id": "012088000003"},
    ]
    # SĐT / email người kê khai: giấy chấm chấm / trống → không điền.
    assert "txtPHONE_NUMBER_NDN" not in by and "txtEMAIL_ADDRESS_NDN" not in by
    assert names.index("txtIDENTIFY_NUMBER_NCC") < names.index("radCapThucHien") < names.index("cboORG")
    agency = next(f for f in out if f["name"] == "cboORG")
    assert agency["comp"] == "bca-agency" and agency["onlyIfEmpty"] is True and "default" not in agency
    assert agency["value"] == {"province": "Tỉnh Lai Châu", "ward": "Phường Đoàn Kết", "cityId": "cboORGTinh",
                               "wardId": "cboORGXa", "readySelect": "cboDiaChiTram", "readyPick": True}
    assert by["radCapThucHien"] == "Cấp Xã"
    # Nhận tại cơ quan: chỉ chọn radio, không điền nhóm địa chỉ bưu chính.
    assert by["radNhanKetQua"] == "Nhận kết quả tại cơ quan công an nơi tiếp nhận hồ sơ"
    assert not {"cboGET_RESULT_CITY_ADDR", "txtGET_RESULT_DETAIL_ADDR", "txtFULLNAME_NN"} & set(by)


def test_sdt_email_phan_i_chi_ghi_khi_tai_khoan_la_nguoi_ky_muc_ii():
    # 20/11/2026 (1.012549 / 1.014062): Phần I là tài khoản đăng nhập — SĐT / email mục II DC02 chỉ ghi khi tài khoản đúng
    # là người ký mục II (extension so Phần I với bcaAccountIs), không thì để ô cho chủ tài khoản.
    out = _enrich({**HO_SO, "NguoiDaiDien_SoDienThoai": "0987 000 222", "NguoiDaiDien_Email": "Hoa.Mau@Example.com"})
    for name in ("txtPHONE_NUMBER_NDN", "txtEMAIL_ADDRESS_NDN"):
        field = next(f for f in out if f["name"] == name)
        assert field["bcaAccountIs"] == {"name": "TRẦN THỊ HOA", "id": "012190000002"}, name
        assert field["keepPortalValue"] is True, name
    assert not any("bcaAccountIs" in f for f in out if f["name"] not in ("txtPHONE_NUMBER_NDN", "txtEMAIL_ADDRESS_NDN"))
    # Mục II không ghi người ký → không biết SĐT là của ai → không ghi vào Phần I.
    by = _by(_enrich({**HO_SO, "NguoiDaiDien_HoTen": "", "NguoiDaiDien_SoDinhDanh": "",
                      "NguoiDaiDien_SoDienThoai": "0987 000 222"}))
    assert "txtPHONE_NUMBER_NDN" not in by


def test_danh_sach_cha_me_cho_extension_so_tai_khoan():
    people = lambda **kw: _by(_enrich({**HO_SO, **kw})).get("cboRELATIONSHIP_WITH_NDN", {}).get("people")  # noqa: E731
    # Người giám hộ ghi trên giấy (không phải cha mẹ) → thêm một dòng "Người đại diện hợp pháp".
    got = people(NguoiDaiDien_HoTen="Phạm Văn Bình", NguoiDaiDien_SoDinhDanh="012080000009",
                 NguoiDaiDien_QuanHe="Người giám hộ")
    assert {"relation": "Người đại diện hợp pháp", "name": "PHẠM VĂN BÌNH", "id": "012080000009"} in got
    # Giấy ghi "Bà nội" (không phải cha mẹ, không phải đại diện) → chỉ cha mẹ, không gán số của bà cho ai.
    got = people(NguoiDaiDien_HoTen="Phạm Thị Bình", NguoiDaiDien_SoDinhDanh="012060000008",
                 NguoiDaiDien_QuanHe="Bà nội")
    assert [p["relation"] for p in got] == ["Mẹ", "Cha"] and "012060000008" not in {p.get("id") for p in got}
    # Giấy không cho biết cha mẹ là ai → không phát ô (không chọn "Người đại diện" cho mọi tài khoản).
    assert people(NguoiDaiDien_HoTen="", NguoiDaiDien_SoDinhDanh="", Cha_HoTen="", Cha_SoDinhDanh="",
                  Me_HoTen="") is None


def test_so_dinh_danh_tre_trung_cha_me_thi_bo_va_gioi_tinh_theo_so():
    for adult in ("012190000002", "012088000003"):
        by = _by(_enrich({**HO_SO, "NguoiCanCap_SoDinhDanh": adult}))
        assert "txtIDENTIFY_NUMBER_NCC" not in by
    # Không đọc được giới tính: chữ số thứ 4 của số định danh (3 = lẻ = nữ).
    by = _by(_enrich({**HO_SO, "NguoiCanCap_GioiTinh": ""}))
    assert by["cboGENDER_ID_NCC"] == "Nữ"


def test_nop_cong_an_tinh_chon_cap_tinh():
    by = _by(_enrich({**HO_SO, "CoQuan_Tinh": "Đồng Nai", "CoQuan_Xa": ""}))
    assert by["radCapThucHien"] == "Cấp Tỉnh"
    assert by["cboORG"]["province"] == "Thành phố Đồng Nai" and by["cboORG"]["ward"] == ""


def test_nhan_qua_buu_chinh_nguoi_nhan_mac_dinh_la_nguoi_ke_khai():
    by = _by(_enrich({**HO_SO, "NhanKetQua_HinhThuc": "Qua dịch vụ bưu chính",
                      "NguoiDaiDien_SoDienThoai": "0912 000 333", "NguoiDaiDien_Email": "Hoa.Mau@Example.com"}))
    assert by["radNhanKetQua"] == "Nhận kết quả qua dịch vụ bưu chính"
    assert by["cboGET_RESULT_CITY_ADDR"] == "Tỉnh Lai Châu" and by["cboGET_RESULT_VILLAGE_ADDR"] == "Phường Đoàn Kết"
    assert by["txtGET_RESULT_DETAIL_ADDR"] == "Số 3, tổ dân phố số 5"
    assert by["txtFULLNAME_NN"] == "TRẦN THỊ HOA" and by["txtPHONE_NUMBER_NN"] == "0912000333"
    assert by["txtPHONE_NUMBER_NDN"] == "0912000333" and by["txtEMAIL_ADDRESS_NDN"] == "hoa.mau@example.com"


def test_giay_khong_ghi_co_quan_thi_lay_xa_tai_khoan_to_vang():
    values = {k: v for k, v in HO_SO.items() if not k.startswith("CoQuan_")}
    options = mapper.with_account_process_options({}, {"tinh": "Lai Châu", "xa": "Phường Mẫu"}, KEY)
    out = _enrich(values, options)
    agency = next(f for f in out if f["name"] == "cboORG")
    level = next(f for f in out if f["name"] == "radCapThucHien")
    assert agency["value"]["ward"] == "Phường Mẫu" and agency["default"] is True and level["default"] is True
    # Thủ tục khác không mang xã tài khoản sang, cũng không xoá xã do thủ tục cấp đổi gắn.
    assert "_accountAgency" not in mapper.with_account_process_options({}, {"tinh": "A", "xa": "B"}, "khac")
    kept = {"_accountAgency": {"tinh": "A", "xa": "B"}}
    assert mapper.with_account_process_options(kept, None, "cap-doi-the-can-cuoc") == kept


def test_prompt_va_schema():
    assert "KHÔNG lấy họ tên, ngày sinh, số" in EXTRA_RULES and "Mối quan hệ với chủ hộ" not in EXTRA_RULES
    assert "Số CMND 9 số" in EXTRA_RULES
    # Email người kê khai dùng chung bộ sửa email theo OCR của cấp đổi (khớp theo tên ô NguoiDaiDien_Email).
    assert {"NguoiDaiDien_Email", "Cha_HoTen", "Cha_SoDinhDanh", "Me_HoTen", "Me_SoDinhDanh"} <= ALLOWED
    assert "LyDoCap" not in ALLOWED


def test_registry_va_link_ke_khai():
    assert registry.get_pipeline(KEY) is not None
    assert registry.get_attach_pipeline(KEY) is None
    proc = registry.get_procedure(KEY)
    assert proc["label"] == "Cấp thẻ căn cước cho người dưới 14 tuổi"
    assert proc["hasAttachmentStep"] is False
    assert proc["detect"]["urlIncludes"] == ["dvc-CCCD-duoi-14-tuoi.html"]
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["label"] == proc["label"]
    assert "1.012549" in link["code"] and "1.014062" in link["code"]
    assert link["url"].endswith("dvc-CCCD-duoi-14-tuoi.html") and link["needsAgencySelect"] is False


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
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Phường Đoàn Kết"}}
    r = flow._to_confirm_procedure(conv, KEY)
    assert conv["state"] == "guide_login" and r.actions[0]["type"] == "navigate"
    r = flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True}))
    assert conv["state"] in ("ask_doc_method", "consent") and conv["agency_done"] is True
    assert "nơi cư trú" not in (r.display_md or "")


def test_tro_ly_dien_xong_nhac_kiem_tra_csdl_cam_doan_roi_luu_tiep_tuc():
    import asyncio
    from unittest import mock

    from app.channels.handfree.chat import pipeline_runner, tracing

    assert pipeline_runner.with_cap_the_can_cuoc_duoi_14_tuoi_account_process_options(
        {}, {"tinh": "Lai Châu", "xa": "Phường Đoàn Kết"}, KEY)["_accountAgency"]["xa"] == "Phường Đoàn Kết"
    conv = {"_id": "c1", "state": "filling", "procedure_key": KEY, "docs_target": "declaration",
            "auto_attach_after_fill": True, "upload_session_id": "s1", "location": {},
            "client_capabilities": dict(CAPS)}
    with mock.patch.object(tracing, "set_report", mock.AsyncMock()):
        r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {"filled": 9})))
    assert "Kiểm tra thông tin trong CSDL" in r.display_md and "Lưu và Tiếp tục" in r.display_md
    assert "Đính kèm" not in r.display_md


def test_tro_ly_ten_mong_va_cau_chon_thu_tuc():
    from app.channels.handfree.chat import script_mong
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS

    assert script_mong.PROCEDURE_HMONG[KEY]
    assert "làm căn cước cho con" in PROCEDURE_HINTS[KEY]
