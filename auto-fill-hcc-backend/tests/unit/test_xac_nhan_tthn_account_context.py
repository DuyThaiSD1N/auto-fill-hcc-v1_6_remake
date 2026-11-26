"""TTHN: đối chiếu tài khoản đăng nhập cổng (formContext) sau khi mapper đã chọn mục I/II."""

from app.pipelines.xac_nhan_tthn.process.mapper import account_context, enrich

A_ID = "001190000001"
B_ID = "001185000002"
ACCOUNT = {
    "applicantFullname": "NGUYỄN THỊ AN", "applicantIdentityNumber": A_ID,
    "applicantBirthday": "5/3/1990", "applicantGender": "Nữ", "applicantEthnicity": "Kinh",
    "applicantIdDate": "10/04/2021", "applicantIdIssuer": "CỤC TRƯỞNG CỤC CẢNH SÁT QLHC VỀ TTXH",
    "applicantAddress": {"tinh": "Lạng Sơn", "xa": "Phường Đông Kinh", "diaChi": "Tổ 3"},
}


def _ui(values: dict, form_context: dict | None) -> dict:
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    options = {"formContext": form_context} if form_context is not None else {}
    return {f["name"]: f["value"] for f in enrich(fields, options)}


def _order(values: dict, form_context: dict) -> list[str]:
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    return [f["name"] for f in enrich(fields, {"formContext": form_context})]


def test_account_context_normalizes_optional_keys():
    ctx = account_context({"formContext": ACCOUNT})
    assert ctx["SoDinhDanh"] == A_ID and ctx["NgaySinh"] == "05/03/1990" and ctx["GioiTinh"] == "Nữ"
    assert ctx["NoiCap"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert ctx["NoiCuTru"]["tinh"] == "Lạng Sơn"
    assert account_context({}) == {}


def test_account_of_another_person_changes_nothing():
    card_b = {"NguoiDuocCap_HoTen": "TRẦN VĂN BÌNH", "NguoiDuocCap_SoDinhDanh": B_ID}
    assert _ui(card_b, ACCOUNT) == _ui(card_b, None)


def test_self_case_fills_both_sections_from_account():
    ui = _ui({
        "NguoiDuocCap_HoTen": "NGUYEN THI AN", "NguoiDuocCap_SoDinhDanh": A_ID,
        "NguoiDuocCap_NgaySinh": "15/03/1990", "NguoiDuocCap_NgayCap": "01/01/2020",
    }, ACCOUNT)
    for suffix in ("C", "C1"):
        assert ui[f"HoVaTen{suffix}"] == "NGUYỄN THỊ AN"
        assert ui[f"NgaySinh{suffix}"] == "05/03/1990"
        assert ui[f"NgayCapDD{suffix}"] == "10/04/2021"
    assert ui["DanTocC1"] == "Kinh" and ui["GioiTinhC1"] == "Nữ"
    assert ui["nxnNoiCuTru_TrongNuoc"]["tinh"] == "Lạng Sơn"
    assert ui["nycNoiCuTru_TrongNuoc"]["diaChi"] == "Tổ 3"


def test_both_blocks_match_account_despite_ocr_id_slip_become_self():
    ui = _ui({
        "ToKhaiYeuCau_HoTen": "Nguyễn Thị An", "ToKhaiYeuCau_SoDinhDanh": "001190000071",
        "ToKhaiYeuCau_QuanHe": "Bản thân",
        "ToKhai_HoTen": "Nguyễn Thị Ân", "ToKhai_SoDinhDanh": A_ID,
    }, ACCOUNT)
    assert ui["quanhevoinguoiduocxacminh"] == "1"
    assert "quanhekhac" not in ui
    assert ui["SoDinhDanhC"] == A_ID and ui["HoVaTenC1"] == "NGUYỄN THỊ AN"


def test_relative_declares_for_account_holder_only_section_two_changes():
    ui = _ui({
        "ToKhaiYeuCau_HoTen": "Trần Văn Bình", "ToKhaiYeuCau_SoDinhDanh": B_ID, "ToKhaiYeuCau_QuanHe": "là con",
        "ToKhai_HoTen": "Nguyen Thi An", "ToKhai_SoDinhDanh": A_ID,
    }, ACCOUNT)
    assert ui["HoVaTenC"] == "TRẦN VĂN BÌNH" and ui["SoDinhDanhC"] == B_ID
    assert ui["quanhevoinguoiduocxacminh"] == "2"
    assert ui["HoVaTenC1"] == "NGUYỄN THỊ AN" and ui["DanTocC1"] == "Kinh"


def test_block_without_id_needs_same_name_and_birthday():
    values = {"ToKhai_HoTen": "Nguyễn Thị An", "ToKhai_NgaySinh": "01/01/1991"}
    assert _ui(values, ACCOUNT)["NgaySinhC1"] == "01/01/1991"
    values["ToKhai_NgaySinh"] = "05/03/1990"
    assert _ui(values, ACCOUNT)["SoDinhDanhC1"] == A_ID


def test_old_extension_name_and_id_only_fixes_those_fields():
    old = {"applicantFullname": "NGUYỄN THỊ AN", "applicantIdentityNumber": A_ID}
    ui = _ui({"NguoiDuocCap_HoTen": "NGUYỄN THI AN", "NguoiDuocCap_SoDinhDanh": A_ID,
              "NguoiDuocCap_NgaySinh": "15/03/1990"}, old)
    assert ui["HoVaTenC1"] == "NGUYỄN THỊ AN"
    assert ui["NgaySinhC1"] == "15/03/1990"


def test_relation_radio_stays_before_section_one_identity():
    names = _order({
        "ToKhaiYeuCau_HoTen": "Nguyễn Thị An", "ToKhaiYeuCau_SoDinhDanh": "001190000071",
        "ToKhaiYeuCau_QuanHe": "Bản thân", "ToKhai_HoTen": "Nguyễn Thị An", "ToKhai_SoDinhDanh": A_ID,
    }, ACCOUNT)
    assert names.index("quanhevoinguoiduocxacminh") < names.index("HoVaTenC")


def test_handwritten_id_off_by_two_digits_matches_by_exact_name_and_birthday():
    ui = _ui({"ToKhai_HoTen": "Nguyễn Thị An", "ToKhai_SoDinhDanh": "001190000071",
              "ToKhai_NgaySinh": "05/03/1990"}, {**ACCOUNT, "applicantIdentityNumber": "001190000016"})
    assert ui["SoDinhDanhC1"] == "001190000016"
    ui = _ui({"ToKhai_HoTen": "Nguyễn Thị Ba", "ToKhai_SoDinhDanh": "001190000071",
              "ToKhai_NgaySinh": "05/03/1990"}, {**ACCOUNT, "applicantIdentityNumber": "001190000016"})
    assert ui["SoDinhDanhC1"] == "001190000071"


def test_account_ethnicity_and_gender_codes_are_decoded():
    ctx = account_context({"formContext": {"applicantFullname": "A", "applicantEthnicity": "1545",
                                           "applicantGender": "2"}})
    assert "DanToc" not in ctx and ctx["GioiTinh"] == "Nữ"
    ctx = account_context({"formContext": {"applicantEthnicity": "63001", "applicantGender": "1"}})
    assert ctx["DanToc"] == "Kinh" and ctx["GioiTinh"] == "Nam"
    assert account_context({"formContext": {"applicantEthnicity": "64505"}})["DanToc"] == "Kinh"
    for value in ("1514", "1541", "1516", "Thái"):
        assert "DanToc" not in account_context({"formContext": {"applicantEthnicity": value}})


def test_account_address_codes_from_portal_are_decoded():
    ctx = account_context({"formContext": {"applicantFullname": "A", "applicantAddress": {
        "tinh": "40", "xa": "17059", "diaChi": "Xóm Tam Long"}}})
    assert ctx["NoiCuTru"]["tinh"].endswith("Nghệ An")
    assert "Tam Hợp" in ctx["NoiCuTru"]["xa"] and ctx["NoiCuTru"]["diaChi"] == "Xóm Tam Long"


# --- Form cũ eForm Bộ Tư pháp (key xac-nhan-tinh-trang-hon-nhan-eform) ---------------------------------------------

_EFORM_KEY = "xac-nhan-tinh-trang-hon-nhan-eform"


def _popup_detect_key(url: str) -> str | None:
    """Mô phỏng bước khớp URL của popup: urlScope chặn host trước, rồi mới xét urlIncludes (đã lower-case)."""
    from app.procedures.ke_khai_links import with_ke_khai_detect_urls
    from app.procedures.registry import public_list

    url = url.lower()
    for proc in with_ke_khai_detect_urls(public_list()):
        detect = proc.get("detect") or {}
        scope = detect.get("urlScope") or []
        if scope and not any(s and str(s).lower() in url for s in scope):
            continue
        if any(u and str(u).lower() in url for u in detect.get("urlIncludes") or []):
            return proc["key"]
    return None


def test_eform_cu_noi_ve_pipeline_xac_nhan_tthn():
    from app.pipelines.xac_nhan_tthn.attach import plan as old_attach
    from app.pipelines.xac_nhan_tthn.process import run as old_run
    from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

    entry = get_procedure(_EFORM_KEY)
    assert entry["formVariantOf"] == "xac-nhan-tinh-trang-hon-nhan"
    assert entry["hasAttachmentStep"] is True and entry["supportsSplitDocuments"] is True
    assert entry["collectFormContext"] is True
    assert get_pipeline(_EFORM_KEY) is old_run
    assert get_attach_pipeline(_EFORM_KEY) is old_attach
    # Key gốc vẫn chạy Cổng DVC quốc gia mới.
    assert get_pipeline("xac-nhan-tinh-trang-hon-nhan") is not old_run


def test_eform_cu_nhan_dien_theo_url_moj_khong_tranh_voi_dvc_moi():
    moj = "https://dichvucongnganhtuphap.moj.gov.vn/nop-ho-so/100001?tinhThanhId=1&maThuTuc=1.004873&MaDVC=1.004873.01"
    assert _popup_detect_key(moj) == _EFORM_KEY
    dvc_moi = "https://dichvucong.gov.vn/nop-ho-so?formalityId=019d2bfd-6eb3-7019-bf3f-fc58c9ee44b9"
    assert _popup_detect_key(dvc_moi) == "xac-nhan-tinh-trang-hon-nhan"


def test_eform_cu_chi_cho_auto_fill_khong_len_tro_ly():
    from app.channels.handfree.procedure_registry import PROCEDURES as HANDFREE_PROCEDURES

    assert all(p.get("key") != _EFORM_KEY for p in HANDFREE_PROCEDURES)
