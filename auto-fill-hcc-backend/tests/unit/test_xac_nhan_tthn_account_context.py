"""TTHN: đối chiếu tài khoản đăng nhập cổng (formContext) sau khi mapper đã chọn mục I/II."""

from app.pipelines.xac_nhan_tthn.process.mapper import account_context, enrich

A_ID = "001190000001"
B_ID = "001185000002"
ACCOUNT = {
    "applicantFullname": "NGUYỄN THỊ AN", "applicantIdentityNumber": A_ID,
    "applicantBirthday": "5/3/1990", "applicantGender": "Nữ", "applicantEthnicity": "Tày",
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
    assert ui["DanTocC1"] == "Tày" and ui["GioiTinhC1"] == "Nữ"
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
    assert ui["HoVaTenC1"] == "NGUYỄN THỊ AN" and ui["DanTocC1"] == "Tày"


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
    assert ctx["DanToc"] == "Tày" and ctx["GioiTinh"] == "Nữ"
    ctx = account_context({"formContext": {"applicantEthnicity": "63001", "applicantGender": "1"}})
    assert ctx["DanToc"] == "Kinh" and ctx["GioiTinh"] == "Nam"
    assert account_context({"formContext": {"applicantEthnicity": "Thái"}})["DanToc"] == "Thái"


def test_account_address_codes_from_portal_are_decoded():
    ctx = account_context({"formContext": {"applicantFullname": "A", "applicantAddress": {
        "tinh": "40", "xa": "17059", "diaChi": "Xóm Tam Long"}}})
    assert ctx["NoiCuTru"]["tinh"].endswith("Nghệ An")
    assert "Tam Hợp" in ctx["NoiCuTru"]["xa"] and ctx["NoiCuTru"]["diaChi"] == "Xóm Tam Long"
