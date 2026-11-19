"""Cấp lại thẻ căn cước 2.001194 (Cổng DVC Bộ Công an, cùng trang với cấp đổi ?TT=CAP_LAI): mapper + registry + trợ lý."""
from app.pipelines.cap_lai_the_can_cuoc.process import mapper
from app.pipelines.cap_lai_the_can_cuoc.process.prompt import EXTRA_RULES
from app.pipelines.cap_lai_the_can_cuoc.process.schema import FIELDS
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "cap-lai-the-can-cuoc"
SELF = {
    "CoQuan_Tinh": "tỉnh Lai Châu", "CoQuan_Xa": "phường Đoàn Kết",
    "LyDoCap": "Cấp lại thẻ căn cước do mất thẻ căn cước",
    "NoiDungDeNghi": "Cấp lại thẻ căn cước do bị mất.",
    "NguoiCanCap_HoTen": "Tran Thi Mau", "NguoiCanCap_NgaySinh": "3/4/1990", "NguoiCanCap_GioiTinh": "Nữ",
    "NguoiCanCap_SoDinhDanh": "0121 9000 0003", "NguoiCanCap_SoDienThoai": "0912 000 333",
    "NguoiCanCap_Email": "Mau.Tran@Example.com",
    "NguoiDaiDien_HoTen": "……", "NguoiDaiDien_SoDienThoai": "………",
    "NhanKetQua_HinhThuc": "Qua dịch vụ bưu chính",
    "NhanKetQua_Tinh": "Lai Châu", "NhanKetQua_Xa": "Phường Đoàn Kết",
    "NhanKetQua_DiaChiChiTiet": "Số 7, tổ dân phố số 2, phường Đoàn Kết, tỉnh Lai Châu",
    "NhanKetQua_SoDienThoai": "0912000333",
}


def _enrich(values: dict, options=None) -> list[dict]:
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def _by(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_tu_ke_khai_nhan_radio_cap_lai_va_ly_do_mat_the():
    out = _enrich(SELF)
    names = [f["name"] for f in out]
    by = _by(out)
    assert "txtFULLNAME_NDN" not in by
    # Radio chọn theo tài khoản đăng nhập (extension), nhãn của trang cấp lại.
    assert by["radIsNCC"]["selfLabel"] == "Người kê khai là người cần cấp lại căn cước"
    assert by["radIsNCC"]["otherLabel"] == ("Người kê khai là cha/mẹ/người đại diện hợp pháp của người cần cấp lại "
                                            "căn cước")
    assert by["radIsNCC"]["subject"] == {"name": "TRAN THI MAU", "id": "012190000003"}
    assert all(f.get("bcaOtherOnly") for f in out if f["name"].endswith("_NCC"))
    assert by["txtPHONE_NUMBER_NDN"] == "0912000333" and by["txtEMAIL_ADDRESS_NDN"] == "mau.tran@example.com"
    assert by["cboLyDoCap"] == "Cấp lại thẻ căn cước do mất thẻ căn cước"
    assert names.index("cboLyDoCap") < names.index("radCapThucHien") < names.index("cboORG") < names.index("radNhanKetQua")
    assert by["radCapThucHien"] == "Cấp Xã"
    assert by["cboORG"]["province"] == "Tỉnh Lai Châu" and by["cboORG"]["ward"] == "Phường Đoàn Kết"
    assert by["cboGET_RESULT_CITY_ADDR"] == "Tỉnh Lai Châu" and by["txtGET_RESULT_DETAIL_ADDR"] == "Số 7, tổ dân phố số 2"
    assert by["txtFULLNAME_NN"] == "TRAN THI MAU" and by["txtPHONE_NUMBER_NN"] == "0912000333"


def test_cha_me_ke_khai_thay_nhan_radio_cap_lai():
    values = {**SELF, "NguoiDaiDien_HoTen": "Tran Van Cha", "NguoiDaiDien_SoDinhDanh": "012065000004",
              "NguoiDaiDien_SoDienThoai": "0987 000 444", "NguoiDaiDien_QuanHe": "Cha"}
    by = _by(_enrich(values))
    assert by["txtFULLNAME_NCC"] == "TRAN THI MAU" and by["txtIDENTIFY_NUMBER_NCC"] == "012190000003"
    assert by["cboRELATIONSHIP_WITH_NDN"]["people"] == [{"relation": "Cha", "name": "TRAN VAN CHA",
                                                         "id": "012065000004"}]
    assert by["txtPHONE_NUMBER_NDN"] == "0987000444"


def test_ly_do_chi_trong_3_option_cap_lai():
    def reason(said, content=""):
        return _by(_enrich({**SELF, "LyDoCap": said, "NoiDungDeNghi": content})).get("cboLyDoCap")

    assert reason("thẻ bị đánh rơi") == "Cấp lại thẻ căn cước do mất thẻ căn cước"
    assert reason("", "Thẻ căn cước cấp năm 2024 bị mất ngày 01/11") == "Cấp lại thẻ căn cước do mất thẻ căn cước"
    assert reason("Thẻ bị hư hỏng, gãy chíp") == "Cấp lại thẻ căn cước do thẻ căn cước bị hư hỏng không sử dụng được"
    assert reason("được trở lại quốc tịch Việt Nam") == "Cấp lại thẻ căn cước cho công dân trở lại quốc tịch Việt Nam"
    # Lý do của cấp đổi không có option trên trang cấp lại → để trống, không chọn bừa.
    assert reason("Đổi thẻ căn cước khi công dân đủ 25 tuổi") is None
    assert reason("", "") is None


def test_cap_doi_van_giu_nhan_cu():
    from app.pipelines.cap_doi_the_can_cuoc.process import mapper as cap_doi

    by = _by(cap_doi.enrich([{"name": k, "value": v} for k, v in
                             {**SELF, "LyDoCap": "Đổi thẻ căn cước khi công dân đủ 25 tuổi"}.items()]))
    assert by["radIsNCC"]["selfLabel"] == "Người kê khai là người cần cấp đổi căn cước"
    assert by["cboLyDoCap"] == "Đổi thẻ căn cước khi công dân đủ 25 tuổi"


def test_giay_khong_ghi_co_quan_thi_lay_xa_tai_khoan_to_vang():
    values = {k: v for k, v in SELF.items() if not k.startswith("CoQuan_")}
    options = mapper.with_account_process_options({}, {"tinh": "Lai Châu", "xa": "Phường Mẫu"}, KEY)
    out = _enrich(values, options)
    agency = next(f for f in out if f["name"] == "cboORG")
    assert agency["value"]["ward"] == "Phường Mẫu" and agency["default"] is True
    assert "_accountAgency" not in mapper.with_account_process_options({}, {"tinh": "A", "xa": "B"}, "khac")


def test_prompt_va_schema_noi_cap_lai():
    assert "Cấp lại thẻ căn cước do mất thẻ căn cước" in EXTRA_RULES
    assert "Đổi thẻ căn cước" not in EXTRA_RULES and "KHÔNG lấy cha, mẹ ở" in EXTRA_RULES
    assert not any("cấp đổi" in f["desc"] for f in FIELDS)


def test_registry_va_link_ke_khai_khong_dinh_kem():
    assert registry.get_pipeline(KEY) is not None
    assert registry.get_attach_pipeline(KEY) is None
    proc = registry.get_procedure(KEY)
    assert proc["hasAttachmentStep"] is False
    assert proc["detect"]["urlScope"] == ["dvc-CCCD-cap-doi-hoac-cap-lai.html"]
    assert proc["detect"]["urlIncludes"] == ["TT=CAP_LAI"]
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "2.001194" and link["url"].endswith("dvc-CCCD-cap-doi-hoac-cap-lai.html?TT=CAP_LAI")
    # Trang chung với cấp đổi: hai thủ tục chốt query khác nhau, không đè nhau.
    assert registry.get_procedure("cap-doi-the-can-cuoc")["detect"]["urlIncludes"] == ["TT=CAP_DOI"]


# ── Trợ lý người dân (handfree) ──
def test_tro_ly_entry_cung_key_url_detect_toan_quoc():
    from app.channels.handfree import procedure_registry as hf
    from app.channels.handfree.chat import pipeline_runner, script_mong
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS

    proc = hf.get_procedure(KEY)
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert proc["keKhaiUrl"] == link["url"] and proc["detect"] == registry.get_procedure(KEY)["detect"]
    assert proc["bcaPortal"] is True and proc["bcaAgencyFromDocs"] is True and proc["hasAttachmentStep"] is False
    assert proc["requiresCapability"] == "supportsBcaCanCuoc" and "provinceOnly" not in proc
    assert hf.get_pipeline(KEY) is registry.get_pipeline(KEY)
    for slug in ("khanhhoa", "laichau", "bacninh", ""):
        assert KEY in {p["key"] for p in hf.public_list_for(slug)}, slug
    assert pipeline_runner.with_cap_lai_the_can_cuoc_account_process_options(
        {}, {"tinh": "Khánh Hòa", "xa": "Phường Nam Nha Trang"}, KEY)["_accountAgency"]["xa"] == "Phường Nam Nha Trang"
    assert script_mong.PROCEDURE_HMONG[KEY] and "mất thẻ căn cước" in PROCEDURE_HINTS[KEY]
