import asyncio
from types import SimpleNamespace

from app.pipelines._shared import fold
from app.pipelines._shared.compact_agent.issuer import ISSUER_BO_CONG_AN, ISSUER_CUC
from app.pipelines.hoa_giai_tranh_chap_dat_dai.attach import planner
from app.pipelines.hoa_giai_tranh_chap_dat_dai.attach.prompt import SYSTEM_PROMPT
from app.pipelines.hoa_giai_tranh_chap_dat_dai.process import mapper
from app.pipelines.hoa_giai_tranh_chap_dat_dai.process.prompt import EXTRA_RULES
from app.pipelines.hoa_giai_tranh_chap_dat_dai.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.procedures.ke_khai_links import KE_KHAI_LINKS, procedure_province_slugs
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_KEY = "hoa-giai-tranh-chap-dat-dai"
# Cột "Tên giấy tờ" của 2 dòng thành phần hồ sơ (ảnh ánh xạ đính kèm), đúng thứ tự DOM — cổng lặp chữ "yêu cầu".
_ROWS = [
    "- Các giấy tờ có liên quan đến việc sử dụng đất (bản phô tô hoặc có công chức hoặc có chứng thực).",
    "- Đơn yêu cầu yêu cầu hòa giải tranh chấp đất đai (bản chính).",
]


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _facts(**values) -> list[dict]:
    return [{"name": name, "value": value} for name, value in values.items()]


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _fe_row(component_name: str, component_index: int | None) -> int | None:
    """Mô phỏng findAttachmentRowByComponent của extension: thử rows[componentIndex - 1] rồi dò tên."""
    rows = [fold(row) for row in _ROWS]
    want = fold(component_name)

    def matches(row: str) -> bool:
        return want in row or row in want

    if component_index and 0 < component_index <= len(rows) and matches(rows[component_index - 1]):
        return component_index - 1
    return next((index for index, row in enumerate(rows) if matches(row)), None)


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM (attp-row 2 dòng, mỗi file nguyên khối)
# --------------------------------------------------------------------------------------
def test_sample_routes_like_attachment_mapping():
    """Ánh xạ: PDF gộp giấy tờ → nguyên dòng 1 (1 Bản sao), Đơn → dòng 2 (1 Bản chính), không tách file."""
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["GIAY_TO.pdf", "DON.pdf"]), {0: ["giay_to_su_dung_dat"], 1: ["don_yeu_cau_hoa_giai"]}
    )
    assert warnings == []
    assert [(item["fileIndex"], item["componentIndex"], item["loaiBan"]) for item in attachments] == [
        (0, 1, "Bản sao"), (1, 2, "Bản chính")]
    assert all(item["target"] == "attp-row" and "sourceSegments" not in item for item in attachments)
    assert [_fe_row(item["componentName"], item["componentIndex"]) for item in attachments] == [0, 1]


def test_component_name_matches_only_its_own_row_even_without_index():
    for spec in planner._ROWS.values():
        hits = [index for index, row in enumerate(_ROWS) if fold(spec["componentName"]) in fold(row)]
        assert hits == [spec["componentIndex"] - 1]
        assert _fe_row(spec["componentName"], None) == spec["componentIndex"] - 1
    # Cổng sửa lỗi lặp chữ "yêu cầu yêu cầu" thì dòng Đơn vẫn khớp.
    assert fold(planner._ROWS["don_yeu_cau_hoa_giai"]["componentName"]) in fold(
        "Đơn yêu cầu hòa giải tranh chấp đất đai (bản chính).")


def test_bundle_with_don_goes_whole_to_don_row_and_warns():
    attachments, warnings, classified = planner.build_plan_items(
        _files(["tat-ca.pdf"]), {0: ["giay_to_su_dung_dat", "don_yeu_cau_hoa_giai"]}
    )
    assert [item["componentIndex"] for item in attachments] == [2]
    assert classified[0]["docTypes"] == ["giay_to_su_dung_dat", "don_yeu_cau_hoa_giai"]
    assert len(warnings) == 1 and "dòng 1" in warnings[0]


def test_missing_don_warns_and_unknown_goes_to_row_one():
    attachments, warnings, classified = planner.build_plan_items(
        _files(["hop-dong.pdf", "trang.pdf"]), {0: ["other"]},
        {0: "HỢP ĐỒNG ỦY QUYỀN\nĐIỀU 5 PHƯƠNG THỨC GIẢI QUYẾT TRANH CHẤP HỢP ĐỒNG", 1: ""},
    )
    assert [item["componentIndex"] for item in attachments] == [1, 1]
    assert [item["source"] for item in classified] == ["rule", "unknown"]
    assert any("trang.pdf" in warning and "dòng 1" in warning for warning in warnings)
    assert any("Chưa có Đơn yêu cầu hòa giải" in warning for warning in warnings)


def test_rule_fallback_reads_don_title_when_llm_silent():
    text = ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nHÒA GIẢI\nĐƠN ĐỀ NGHỊ GIẢI QUYẾT TRANH CHẤP ĐẤT\n"
            "Kính gửi: UBND phường A, tỉnh B.\nTôi tên: Lê Văn An")
    attachments, warnings, classified = planner.build_plan_items(_files(["scan.pdf"]), {}, {0: text})
    assert attachments[0]["componentIndex"] == 2
    assert classified[0]["source"] == "rule"
    assert warnings == []


def test_many_files_on_row_one_get_distinct_names_for_fe_dedup():
    attachments, _warnings, _classified = planner.build_plan_items(
        _files(["Giay_chuyen_nhuong.pdf", "Ban_mo_ta_ranh_gioi.pdf", "Giay_chuyen_nhuong.jpg", "don.pdf"]),
        {0: ["giay_to_su_dung_dat"], 1: ["giay_to_su_dung_dat"], 2: ["giay_to_su_dung_dat"],
         3: ["don_yeu_cau_hoa_giai"]},
    )
    names = [item["documentName"] for item in attachments]
    assert names[:2] == ["Giay chuyen nhuong", "Ban mo ta ranh gioi"]
    assert names[3] == "Đơn yêu cầu hòa giải tranh chấp đất đai"
    fingerprints = [planner._fingerprint(name) for name in names]
    assert len(set(fingerprints)) == len(fingerprints)


def test_attach_prompt_lists_every_type():
    for doc_type in planner._ALLOWED:
        assert doc_type in SYSTEM_PROMPT
    assert '"docTypes"' in SYSTEM_PROMPT


def test_plan_uses_llm_types_then_rule_when_llm_fails(monkeypatch):
    async def fake_ocr(files):
        texts = {"giay.pdf": "HỢP ĐỒNG ỦY QUYỀN", "don.pdf": "ĐƠN YÊU CẦU HÒA GIẢI TRANH CHẤP ĐẤT ĐAI Kính gửi: UBND xã A"}
        return [{"name": item["name"], "type": item["type"], "text": texts[item["name"]]} for item in files]

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["giay_to_su_dung_dat"]},{"index":1,"docType":"don_yeu_cau_hoa_giai"}]}'

    async def broken_chat(messages, **kwargs):
        raise RuntimeError("llm down")

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    files = [SimpleNamespace(name=name, type="application/pdf", dataUrl="x") for name in ("giay.pdf", "don.pdf")]

    monkeypatch.setattr(planner.client, "chat", fake_chat)
    result = asyncio.run(planner.plan(files))
    assert [item["componentIndex"] for item in result["attachments"]] == [1, 2]
    assert result["errors"] == []

    monkeypatch.setattr(planner.client, "chat", broken_chat)
    result = asyncio.run(planner.plan(files))
    assert [item["componentIndex"] for item in result["attachments"]] == [1, 2]
    assert any("attachment_agent" in error for error in result["errors"])


# --------------------------------------------------------------------------------------
# ĐIỀN (Form.io: Phần I người nộp, Phần II chủ hồ sơ, Ghi chú)
# --------------------------------------------------------------------------------------
_REQUESTER = dict(
    NguoiYeuCau_LoaiChuThe="Cá nhân",
    NguoiYeuCau_HoTen="Lê Văn An",
    NguoiYeuCau_NgaySinh="5/6/1980",
    NguoiYeuCau_DanhXung="Ông",
    NguoiYeuCau_SoDinhDanh="056 080 012 345",
    NguoiYeuCau_NgayCap="02/12/2024",
    NguoiYeuCau_DiaChi={"quocGia": "Việt Nam", "tinh": "tỉnh Khánh Hòa", "xa": "phường Nha Trang",
                        "diaChi": "12 Đường A"},
    NguoiYeuCau_DienThoai="0912.345.678",
    Don_NoiDung="Năm 2010, tôi nhận chuyển nhượng một thửa đất tại tổ 1. Nay tôi viết đơn này đề nghị hòa giải.",
)
_SELF = {"formContext": {"applicantFullname": "LÊ VĂN AN", "applicantIdentityNumber": "056080012345"}}
_PROXY = {"formContext": {"applicantFullname": "Trần Thị Bình", "applicantIdentityNumber": "056185099999"}}


def test_self_submit_fills_part_one_and_ticks_owner_check():
    fields, warnings = mapper.enrich(_facts(**_REQUESTER), _SELF)
    values = _values(fields)
    assert fields[0]["name"] == "data[chonDoiTuong]" and values["data[chonDoiTuong]"] == "Cá nhân"
    assert values["data[fullname]"] == "LÊ VĂN AN"
    assert values["data[birthday]"] == "05/06/1980"
    assert values["data[gender]"] == "Nam"
    assert values["data[identityDate]"] == "02/12/2024"
    # Căn cước cấp từ 01/7/2024, Đơn không ghi nơi cấp → Bộ Công an.
    assert values["data[idIssuePlace]"] == ISSUER_BO_CONG_AN
    assert (values["data[province]"], values["data[district]"], values["data[address]"]) == (
        "Tỉnh Khánh Hòa", "Phường Nha Trang", "12 Đường A")
    assert values["data[phoneNumber]"] == "0912345678"
    assert values["data[isOwnerDossierCheck]"] is True
    assert values["data[ghiChu]"] == _REQUESTER["Don_NoiDung"]
    assert not any(name.startswith("data[owner") for name in values)
    assert "data[identityNumber]" not in values  # ô CCCD khoá theo tài khoản
    assert warnings == []


def test_proxy_submit_keeps_part_one_and_fills_owner_from_requester():
    applicant_card = dict(
        Cccd1_HoTen="TRẦN THỊ BÌNH", Cccd1_SoDinhDanh="056185099999", Cccd1_GioiTinh="Nữ",
        Cccd1_NgayCap="10/10/2022", Cccd1_NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội",
        Cccd1_ThuongTru={"tinh": "Khánh Hòa", "xa": "Phường Nam Nha Trang", "diaChi": "Tổ 2"},
    )
    fields, warnings = mapper.enrich(_facts(**_REQUESTER, **applicant_card), _PROXY)
    values = _values(fields)
    assert "data[fullname]" not in values and "data[birthday]" not in values
    assert values["data[gender]"] == "Nữ"
    assert values["data[identityDate]"] == "10/10/2022"
    assert values["data[idIssuePlace]"] == ISSUER_CUC
    assert (values["data[province]"], values["data[district]"], values["data[address]"]) == (
        "Tỉnh Khánh Hòa", "Phường Nam Nha Trang", "Tổ 2")
    assert values["data[isOwnerDossierCheck]"] is False
    assert values["data[ownerFullname]"] == "Lê Văn An"
    assert values["data[ownerBirthday]"] == "05/06/1980"
    assert values["data[ownerGender]"] == "Nam"
    assert values["data[ownerIdentityNumber]"] == "056080012345"
    assert values["data[ownerIdentityDate]"] == "02/12/2024"
    assert values["data[ownerIdIssuePlace]"] == ISSUER_BO_CONG_AN
    assert (values["data[ownerProvince]"], values["data[ownerDistrict]"], values["data[ownerAddress]"]) == (
        "Tỉnh Khánh Hòa", "Phường Nha Trang", "12 Đường A")
    assert values["data[ownerPhoneNumber]"] == "0912345678"
    assert values["data[ownerNation]"] == "Việt Nam"
    assert warnings == []


def test_proxy_without_applicant_card_warns_and_clears_missing_owner_cells():
    facts = {key: value for key, value in _REQUESTER.items() if key not in ("NguoiYeuCau_NgaySinh",)}
    fields, warnings = mapper.enrich(_facts(**facts, NguoiYeuCau_NgaySinh="Sinh năm 1980"), _PROXY)
    values = _values(fields)
    assert "data[gender]" not in values and "data[province]" not in values
    cleared = {item["name"] for item in fields if item.get("clear")}
    assert "data[ownerBirthday]" in cleared and "data[ownerEmail]" in cleared
    assert any("Phần I giữ theo tài khoản" in warning for warning in warnings)
    assert any("ngày sinh" in warning and "Phần II" in warning for warning in warnings)


def test_new_can_cuoc_card_wins_over_old_cmnd_in_old_papers():
    card = dict(Cccd1_HoTen="Lê Văn An", Cccd1_SoDinhDanh="056080012345", Cccd1_NgayCap="02/12/2024",
                Cccd1_NoiCap="BỘ CÔNG AN / MINISTRY OF PUBLIC SECURITY")
    facts = dict(_REQUESTER, NguoiYeuCau_SoDinhDanh="225 000 111", NguoiYeuCau_NgayCap=None)
    fields, _warnings = mapper.enrich(_facts(**{k: v for k, v in facts.items() if v}, **card), _PROXY)
    values = _values(fields)
    assert values["data[ownerIdentityNumber]"] == "056080012345"
    assert values["data[ownerIdentityDate]"] == "02/12/2024"
    assert values["data[ownerIdIssuePlace]"] == ISSUER_BO_CONG_AN


def test_self_submit_with_old_cmnd_does_not_put_its_issue_date_on_locked_number():
    facts = dict(_REQUESTER, NguoiYeuCau_SoDinhDanh="225000111", NguoiYeuCau_NgayCap="01/01/2005")
    fields, _warnings = mapper.enrich(_facts(**facts), _SELF)
    values = _values(fields)
    assert values["data[isOwnerDossierCheck]"] is True
    assert "data[identityDate]" not in values and "data[idIssuePlace]" not in values


def test_gender_falls_back_to_identity_number_digit():
    facts = {key: value for key, value in _REQUESTER.items() if key != "NguoiYeuCau_DanhXung"}
    fields, _warnings = mapper.enrich(_facts(**dict(facts, NguoiYeuCau_SoDinhDanh="056185012345")), _PROXY)
    assert _values(fields)["data[ownerGender]"] == "Nữ"


# Cài đặt "Lấy người nộp theo tờ khai" — Auto Fill (popup) và trợ lý (account_settings) cùng gửi khoá này.
_DECLARATION = {**_PROXY, "submitterMode": "owner_as_submitter"}


def test_declaration_mode_puts_requester_in_part_one_even_when_account_differs():
    fields, warnings = mapper.enrich(_facts(**_REQUESTER), _DECLARATION)
    by_name = {item["name"]: item for item in fields}
    values = _values(fields)
    for name, value in (("data[fullname]", "Lê Văn An"), ("data[birthday]", "05/06/1980"),
                        ("data[identityNumber]", "056080012345")):
        assert by_name[name]["value"] == value and by_name[name]["enableInput"] is True, name
        assert not by_name[name].get("clear")
    assert values["data[gender]"] == "Nam"
    assert values["data[identityDate]"] == "02/12/2024"
    assert values["data[idIssuePlace]"] == ISSUER_BO_CONG_AN
    assert (values["data[province]"], values["data[district]"], values["data[address]"]) == (
        "Tỉnh Khánh Hòa", "Phường Nha Trang", "12 Đường A")
    assert values["data[isOwnerDossierCheck]"] is True
    assert not any(name.startswith("data[owner") for name in values)
    assert warnings == []


def test_declaration_mode_clears_locked_cells_the_form_lacks():
    facts = {key: value for key, value in _REQUESTER.items()
             if key not in ("NguoiYeuCau_NgaySinh", "NguoiYeuCau_SoDinhDanh", "NguoiYeuCau_NgayCap")}
    fields, warnings = mapper.enrich(_facts(**facts), _DECLARATION)
    by_name = {item["name"]: item for item in fields}
    for name in ("data[birthday]", "data[identityNumber]"):
        assert by_name[name]["clear"] is True and by_name[name]["markEmpty"] is True
        assert by_name[name]["enableInput"] is True and by_name[name]["value"] == ""
    assert by_name["data[fullname]"]["value"] == "Lê Văn An"
    assert any("ngày sinh, số CC/CCCD" in warning for warning in warnings)


def test_declaration_mode_without_requester_falls_back_to_account():
    fields, warnings = mapper.enrich(_facts(Don_NoiDung="Nội dung đơn."), _DECLARATION)
    values = _values(fields)
    assert "data[fullname]" not in values and "data[identityNumber]" not in values
    assert values["data[isOwnerDossierCheck]"] is False
    assert any("chưa đọc được người viết đơn" in warning for warning in warnings)


def test_declaration_mode_state_agency_keeps_agency_as_owner():
    fields, _warnings = mapper.enrich(_facts(
        **dict(_REQUESTER, NguoiYeuCau_LoaiChuThe="Cơ quan nhà nước"),
        NguoiYeuCau_TenToChuc="Ủy ban nhân dân xã Ví Dụ", NguoiYeuCau_MaSoThue="0109876543",
    ), _DECLARATION)
    values = _values(fields)
    assert values["data[chonDoiTuong]"] == "Cơ quan nhà nước"
    assert values["data[fullname]"] == "Lê Văn An"
    assert values["data[isOwnerDossierCheck]"] is False
    assert values["data[ownerOrganizationFullname]"] == "Ủy ban nhân dân xã Ví Dụ"
    assert "data[ownerFullname]" not in values


def test_default_mode_still_never_touches_locked_identity_cell():
    for options in (_SELF, _PROXY):
        fields, _warnings = mapper.enrich(_facts(**_REQUESTER), options)
        assert "data[identityNumber]" not in _values(fields)
        assert not any(item.get("enableInput") for item in fields)


def test_organization_fills_both_parts_with_organization():
    fields, warnings = mapper.enrich(_facts(
        **dict(_REQUESTER, NguoiYeuCau_LoaiChuThe="Tổ chức"),
        NguoiYeuCau_TenToChuc="Công ty TNHH Ví Dụ", NguoiYeuCau_MaSoThue="0101-234-567",
    ), _PROXY)
    values = _values(fields)
    assert values["data[chonDoiTuong]"] == "Tổ chức/Doanh nghiệp"
    assert values["data[organization]"] == values["data[ownerOrganizationFullname]"] == "Công ty TNHH Ví Dụ"
    assert values["data[taxCode]"] == values["data[ownerTaxCode]"] == "0101234567"
    assert "data[fullname]" not in values and "data[ownerFullname]" not in values
    assert warnings == []


def test_missing_content_and_name_warn():
    fields, warnings = mapper.enrich(_facts(NguoiYeuCau_DienThoai="0912345678"), _PROXY)
    assert "data[ghiChu]" not in _values(fields)
    assert any("Ghi chú" in warning for warning in warnings)
    assert any("Thiếu họ tên người yêu cầu" in warning for warning in warnings)


def test_schema_prompt_and_ui_keys_follow_mapping():
    assert {"NguoiYeuCau_HoTen", "NguoiYeuCau_DiaChi", "Don_NoiDung", "Cccd1_HoTen", "Cccd2_ThuongTru"} <= ALLOWED
    assert {"data[ghiChu]", "data[district]", "data[ownerDistrict]", "data[isOwnerDossierCheck]",
            "data[identityNumber]"} <= set(UI_COMP_BY_NAME)
    assert "Người viết đơn" in EXTRA_RULES and "Cccd1_" in EXTRA_RULES


# --------------------------------------------------------------------------------------
# REGISTRY + LINK KÊ KHAI
# --------------------------------------------------------------------------------------
def test_registry_wires_pipelines_in_folder_named_after_key():
    procedure = get_procedure(_KEY)
    assert procedure["label"] == "Hòa giải tranh chấp đất đai"
    assert procedure["mode"] == "agent" and procedure["hasAttachmentStep"] is True
    assert "urlScope" not in procedure["detect"]
    assert procedure_province_slugs(procedure) == []
    package = "app.pipelines." + _KEY.replace("-", "_") + "."
    assert get_pipeline(_KEY).__module__.startswith(package)
    assert get_attach_pipeline(_KEY).__module__.startswith(package)


def test_tro_ly_dung_pipeline_loi_va_link_ke_khai():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert procedure["label"] == get_procedure(_KEY)["label"]
    assert procedure["keKhaiUrl"] == link["url"]
    assert handfree.procedure_code(procedure) == "1.012812"
    assert not procedure.get("provinceOnly")
    assert procedure["maePortal"] is True and procedure["maeAgencyLevel"] == "ward"
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert field_review.get(_KEY)["noAsk"] == ("ghiChu",)
    assert PROCEDURE_HINTS[_KEY] and PROCEDURE_HMONG[_KEY]


def test_ke_khai_link_shares_registry_key_and_picks_ward():
    links = [link for link in KE_KHAI_LINKS if link["key"] == _KEY]
    assert len(links) == 1
    link = links[0]
    assert link["code"] == "1.012812"
    assert link["needsAgencySelect"] is True
    assert not link.get("provinceOnlyAgency") and not link.get("selectSo")
