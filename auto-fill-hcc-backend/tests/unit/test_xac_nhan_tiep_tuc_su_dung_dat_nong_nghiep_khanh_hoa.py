import asyncio
import re
from types import SimpleNamespace

from app.pipelines._shared import fold
from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_khanh_hoa.attach import planner
from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_khanh_hoa.attach.prompt import SYSTEM_PROMPT
from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_khanh_hoa.process import mapper
from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_khanh_hoa.process.prompt import EXTRA_RULES
from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_khanh_hoa.process.schema import ALLOWED
from app.procedures.ke_khai_links import KE_KHAI_LINKS, procedure_province_slugs
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

_KEY = "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep-khanh-hoa"

# Cột "Tên giấy tờ" của 2 dòng thành phần hồ sơ trên cổng Khánh Hòa, đúng thứ tự DOM (ảnh ánh xạ, quy trình 1.013947-1.1).
_ROWS = [
    "Văn bản đề nghị xác nhận lại thời hạn sử dụng đất theo Mẫu số 09",
    "(2) Giấy chứng nhận đã cấp.,",
]
_PAGE_TITLE = "Xác nhận tiếp tục sử dụng đất nông nghiệp"


def _fe_fold(value: str) -> str:
    """Như foldChoiceText của FE: bỏ dấu, gộp mọi dấu gạch cùng khoảng trắng quanh nó thành một khoảng trắng."""
    return re.sub(r"\s+", " ", re.sub(r"\s*[-–—]+\s*", " ", fold(value))).strip()


def _fe_matches(row_text: str, name: str) -> bool:
    row, want = _fe_fold(row_text), _fe_fold(name)
    return row == want or want in row or row in want


def _fe_find_row(name: str, index: int) -> int | None:
    """Như findAttachmentRowByComponent của FE: dòng theo STT trước, không khớp tên mới dò dòng khớp đầu tiên."""
    if 1 <= index <= len(_ROWS) and _fe_matches(_ROWS[index - 1], name):
        return index
    return next((stt for stt, row in enumerate(_ROWS, start=1) if _fe_matches(row, name)), None)


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _facts(**values) -> list[dict]:
    return [{"name": name, "value": value} for name, value in values.items()]


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM (attp-row 2 dòng + nút Thêm giấy tờ)
# --------------------------------------------------------------------------------------
def test_sample_bundle_routes_like_attachment_mapping():
    """Ánh xạ hồ sơ: Đơn -> dòng 1; Giấy chứng nhận và Phiếu đo đạc -> CÙNG dòng 2 (cùng componentName để FE chọn cả hai
    file trong một lần "Chọn tệp tin"), mỗi file nguyên khối."""
    attachments, warnings, classified = planner.build_plan_items(
        _files(["d.pdf", "g.pdf", "td.pdf"]), None, {0: ["don_de_nghi"], 1: ["gcn"], 2: ["manh_trich_do"]},
    )
    assert [(item["componentIndex"], item["fileName"]) for item in attachments] == [
        (1, "d.pdf"), (2, "g.pdf"), (2, "td.pdf")]
    assert all(item["target"] == "attp-row" and "loaiBan" not in item for item in attachments)
    assert attachments[1]["componentName"] == attachments[2]["componentName"]
    assert attachments[1]["documentName"] != attachments[2]["documentName"]
    assert [_fe_find_row(item["componentName"], item["componentIndex"]) for item in attachments] == [1, 2, 2]
    assert [item["componentIndex"] for item in classified] == [1, 2, 2]
    assert warnings == []


def test_component_name_resolves_to_its_own_row_on_fe():
    for doc_type, route in planner._ROUTES.items():
        assert _fe_find_row(route["name"], route["row"]) == route["row"], doc_type
        assert _fe_find_row(route["name"], 99) == route["row"], doc_type
    for group in planner._ADD_DOCUMENTS.values():
        assert _fe_find_row(group["componentName"], 99) is None


def test_extra_documents_go_through_add_document_dialog():
    attachments, warnings, classified = planner.build_plan_items(
        _files(["d.pdf", "g.pdf", "uq.pdf", "cccd.pdf", "bd.pdf", "la.pdf"]), None,
        {0: ["don_de_nghi"], 1: ["gcn"], 2: ["authorization", "identity"], 3: ["identity"], 4: ["don_bien_dong"],
         5: "abc"},
    )
    added = attachments[2:]
    assert [item["target"] for item in added] == ["add-document-dialog"] * 4
    assert [item["componentName"] for item in added] == [
        "Văn bản ủy quyền", "Căn cước công dân", "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất", "la.pdf"]
    assert [item["loaiBan"] for item in added] == ["Bản chính", "Bản sao", "Bản chính", "Bản sao"]
    assert all(_fe_find_row(item["fallbackComponentName"], 1) == 1 for item in added)
    assert [item.get("addDocument") for item in classified[2:]] == [True] * 4
    assert warnings == ["Chưa nhận diện chắc loại giấy tờ cho 'la.pdf' — tạm thêm qua nút 'Thêm giấy tờ'; cán bộ kiểm "
                        "tra lại."]


def test_bundle_and_missing_core_documents():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["tat-ca.pdf"]), None, {0: ["don_de_nghi", "gcn", "manh_trich_do", "identity"]})
    assert [item["componentIndex"] for item in attachments] == [1]
    bundled = [warning for warning in warnings if "gộp nhiều giấy tờ" in warning]
    assert len(bundled) == 1 and "(dòng 2)" in bundled[0] and "Căn cước" not in bundled[0]
    assert not [warning for warning in warnings if "chưa có" in warning]

    _attachments, warnings, _classified = planner.build_plan_items(_files(["td.pdf"]), None, {0: ["manh_trich_do"]})
    assert warnings == [message for _doc_type, message in planner._REQUIRED_DOCS]
    assert planner.build_plan_items([], None, {}) == ([], [], [])


def test_attach_prompt_lists_every_type():
    for doc_type in list(planner._ROUTES) + list(planner._ADD_DOCUMENTS) + ["other"]:
        assert doc_type in SYSTEM_PROMPT
    assert '"docTypes"' in SYSTEM_PROMPT and "PHIẾU ĐO ĐẠC CHỈNH LÝ" in SYSTEM_PROMPT and "KT. CHỦ TỊCH" in SYSTEM_PROMPT


def test_plan_parses_llm_doc_type_lists(monkeypatch):
    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["gcn"]},{"index":1,"docType":"manh_trich_do"}]}'

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name=name, type="application/pdf", dataUrl="x") for name in ("g.pdf", "td.pdf")]

    result = asyncio.run(planner.plan(files))

    assert [item["componentIndex"] for item in result["attachments"]] == [2, 2]
    assert any("Đơn xin xác nhận lại" in error for error in result["errors"])


# --------------------------------------------------------------------------------------
# ĐIỀN (Form.io ba khối; người nộp = người thứ nhất, chủ hồ sơ = người thứ hai)
# --------------------------------------------------------------------------------------
_TWO_PEOPLE = dict(
    NSD1_HoTen="Trần Văn Bình",
    NSD1_NgaySinh="5/3/1965",
    NSD1_SoDinhDanh="056 065 012 345",
    # GCN mẫu cũ: ngày cấp + nơi cấp của CMND 9 số, LLM ghép nhầm vào số CCCD mới của Đơn.
    NSD1_NgayCap="12/4/1983",
    NSD1_NoiCap="Công an tỉnh Phú Khánh",
    NSD1_DiaChi={"tinh": "Khánh Hòa", "xa": "phường Phước Long", "chiTietDuoiXa": "12 Đường Số 5"},
    NSD2_HoTen="Lê Thị Hoa",
    NSD2_NgaySinh="20/10/1966",
    NSD2_SoDinhDanh="056166012345",
    Don_DiaChiLienHe={"xa": "phường Nam Nha Trang", "chiTietDuoiXa": "12 Đường Số 5"},
    Don_DienThoai="0905.123.456",
    Don_NoiDungDeNghi="đến ngày 15 tháng 10 năm 2063. Cấp đổi sổ",
)
_PARCEL = dict(
    ThuaDat_SoThua="132",
    ThuaDat_SoTo="17",
    ThuaDat_SoThuaMoi="585",
    ThuaDat_SoToMoi="136",
    ThuaDat_DiaChi={"tinh": "Khánh Hòa", "xa": "phường Nam Nha Trang", "chiTietDuoiXa": "12 Đường Số 5"},
    ThuaDat_DiaChiDayDu="12 Đường Số 5, phường Nam Nha Trang (P. Phước Long cũ), tỉnh Khánh Hòa",
)


def test_two_land_users_split_into_applicant_and_owner():
    fields, warnings = mapper.enrich(_facts(**_TWO_PEOPLE, **_PARCEL))
    values = _values(fields)

    assert values["data[fullname]"] == "Trần Văn Bình" and values["data[ownerFullname]"] == "Lê Thị Hoa"
    assert values["data[birthday]"] == "05/03/1965" and values["data[ownerBirthday]"] == "20/10/1966"
    assert values["data[identityNumber]"] == "056065012345" and values["data[ownerIdentityNumber]"] == "056166012345"
    # Điện thoại + địa chỉ liên hệ Đơn mục 2 (địa danh mới) dùng chung, đứng trước địa chỉ cũ in trên GCN.
    assert values["data[phoneNumber]"] == values["data[ownerPhoneNumber]"] == "0905123456"
    for prefix, suffix in (("", ""), ("1", "")):
        assert values[f"data[province{prefix}]"] == "Tỉnh Khánh Hòa"
        assert values[f"data[village{prefix}]"] == "Phường Nam Nha Trang"
    assert values["data[address]"] == values["data[ownerAddress]"] == "12 Đường Số 5"
    assert values["data[noidungyeucaugiaiquyet]"] == (
        "Xác nhận lại thời hạn sử dụng đất đến ngày 15 tháng 10 năm 2063. Cấp đổi sổ")
    assert (values["data[SoThuaDat]"], values["data[SoToBanDo]"]) == ("132", "17")
    assert values["data[diaChiThuaDat]"] == _PARCEL["ThuaDat_DiaChiDayDu"]
    assert (values["data[province2]"], values["data[village2]"]) == ("Tỉnh Khánh Hòa", "Phường Nam Nha Trang")
    # Ngày cấp CMND cũ không ghép vào số CCCD -> trả về trống; email không có -> trống.
    cleared = {item["name"] for item in fields if item.get("clear")}
    assert cleared == {"data[identityDate]", "data[identityAgency_text]", "data[ownerIdentityDate]",
                       "data[ownerIdentityAgency]", "data[email]", "data[ownerEmail]"}
    assert [warning for warning in warnings if "CMND cũ" in warning] == [
        "Ngày cấp 12/04/1983 (Trần Văn Bình) là của CMND cũ, không khớp số CCCD 056065012345 — đã để trống ngày cấp, "
        "nơi cấp; cán bộ nhập theo thẻ CCCD."]
    assert any("thửa 585, tờ 136" in warning and "thửa 132" in warning for warning in warnings)
    assert len(warnings) == 2


def test_single_land_user_fills_both_blocks_and_keeps_matching_card_date():
    facts = {key: value for key, value in _TWO_PEOPLE.items() if not key.startswith("NSD2_")}
    facts.update(NSD1_SoDinhDanh="220042954", Don_NoiDungDeNghi="")
    values = _values(mapper.enrich(_facts(**facts, ThuaDat_SoThua="132", ThuaDat_SoTo="17"))[0])
    assert values["data[fullname]"] == values["data[ownerFullname]"] == "Trần Văn Bình"
    # Số CMND 9 số in cùng dòng GCN với ngày cấp/nơi cấp -> giữ.
    assert values["data[identityNumber]"] == values["data[ownerIdentityNumber]"] == "220042954"
    assert values["data[identityDate]"] == "12/04/1983"
    assert values["data[noidungyeucaugiaiquyet]"] == mapper.DEFAULT_REQUEST


def test_authorized_submitter_takes_part_one_owner_stays_second_land_user():
    fields, warnings = mapper.enrich(_facts(
        **_TWO_PEOPLE, **_PARCEL,
        UyQuyen_HoTen="Nguyễn Văn Nam",
        UyQuyen_SoDinhDanh="056090012345",
        UyQuyen_DiaChi={"tinh": "Khánh Hòa", "xa": "xã Diên Khánh", "chiTietDuoiXa": "Thôn A"},
    ))
    values = _values(fields)
    assert values["data[fullname]"] == "Nguyễn Văn Nam" and values["data[identityNumber]"] == "056090012345"
    assert values["data[village]"] == "Xã Diên Khánh"
    # Số ở Đơn mục 2 là của người sử dụng đất: không gán cho bên được ủy quyền.
    assert values["data[phoneNumber]"] == ""
    assert values["data[ownerFullname]"] == "Lê Thị Hoa" and values["data[ownerPhoneNumber]"] == "0905123456"
    assert any("bên được ủy quyền Nguyễn Văn Nam" in warning and "Trần Văn Bình" in warning for warning in warnings)


def test_handwritten_contact_matching_parcel_takes_printed_address():
    """Đơn viết tay: "12 Đường Số 5 - phường Nam Nha Trang" OCR thành "125 Đường Sổ 6 - phường Nha Trang"; cùng số nhà và
    tên đường gần giống địa chỉ thửa đất IN trên Phiếu đo đạc → lấy bản in (số nhà, đường, phường) + cảnh báo."""
    facts = dict(_TWO_PEOPLE, Don_DiaChiLienHe={"tinh": "Khánh Hòa", "xa": "Phường Nha Trang",
                                                "chiTietDuoiXa": "125 Đường Sổ 6"})
    fields, warnings = mapper.enrich(_facts(**facts, **_PARCEL))
    values = _values(fields)
    assert values["data[address]"] == values["data[ownerAddress]"] == "12 Đường Số 5"
    assert values["data[village]"] == values["data[village1]"] == "Phường Nam Nha Trang"
    assert any("viết tay" in warning and "125 Đường Sổ 6" in warning for warning in warnings)
    # Địa chỉ liên hệ khác hẳn thửa đất (số nhà khác) → giữ nguyên Đơn.
    facts = dict(_TWO_PEOPLE, Don_DiaChiLienHe={"tinh": "Khánh Hòa", "xa": "Phường Nha Trang",
                                                "chiTietDuoiXa": "40 Trần Phú"})
    values = _values(mapper.enrich(_facts(**facts, **_PARCEL))[0])
    assert (values["data[address]"], values["data[village]"]) == ("40 Trần Phú", "Phường Nha Trang")


def test_request_drops_form_ellipsis_before_prefix():
    for raw in ("...đến ngày 15 tháng 10 năm 2063", "…Đến ngày 15 tháng 10 năm 2063"):
        values = _values(mapper.enrich(_facts(**dict(_TWO_PEOPLE, Don_NoiDungDeNghi=raw)))[0])
        assert values["data[noidungyeucaugiaiquyet]"] == "Xác nhận lại thời hạn sử dụng đất đến ngày 15 tháng 10 năm 2063"


def test_printed_name_fixes_handwritten_diacritics_only():
    from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_khanh_hoa.process.runner import apply_printed_names

    documents = [
        {"text": "ĐƠN XIN XÁC NHẬN LẠI\n1. Người sử dụng đất: Trần Văn Bính, sinh ngày 5/3/1965"},
        {"text": "PHIẾU ĐO ĐẠC CHỈNH LÝ THỬA ĐẤT\n3. Tên người sử dụng đất, người quản lý đất: Trần Văn Bình - Lê Thị "
                 "Hoa\n4. Địa chỉ người sử dụng đất:"},
    ]
    fields = apply_printed_names({"NSD1_HoTen": "Trần Văn Bính", "NSD2_HoTen": "Lê Thị Hòa"}, documents)
    assert fields == {"NSD1_HoTen": "Trần Văn Bình", "NSD2_HoTen": "Lê Thị Hoa"}
    # Tên khác chữ (không chỉ khác dấu) là người khác → giữ nguyên.
    assert apply_printed_names({"NSD1_HoTen": "Trần Văn Bảo"}, documents) == {"NSD1_HoTen": "Trần Văn Bảo"}
    gcn = [{"text": "I- Tên người sử dụng đất\nÔng: Trần Văn Bình\nSinh năm 1965\nBà: Lê Thị Hoa\n"}]
    assert apply_printed_names({"NSD1_HoTen": "Tran Van Binh"}, gcn) == {"NSD1_HoTen": "Trần Văn Bình"}


def test_schema_and_prompt_cover_traps():
    assert {"NSD1_HoTen", "NSD2_HoTen", "UyQuyen_HoTen", "Don_DiaChiLienHe", "ThuaDat_SoThuaMoi"} <= ALLOWED
    for phrase in ("CMND X", "NSD1_*", "PHƯỜNG MỚI", "ThuaDat_SoThuaMoi", "xoay", "chữ \"cũ\""):
        assert phrase in EXTRA_RULES, phrase


# --------------------------------------------------------------------------------------
# REGISTRY + LINK KÊ KHAI + TRỢ LÝ
# --------------------------------------------------------------------------------------
def test_registry_wires_both_pipelines_and_locks_khanh_hoa():
    procedure = get_procedure(_KEY)
    assert procedure["label"] == "Khánh Hòa - Xác nhận tiếp tục sử dụng đất nông nghiệp"
    assert procedure["detect"]["urlScope"] == ["khanhhoa.gov.vn"]
    assert procedure_province_slugs(procedure) == ["khanhhoa"]
    assert get_pipeline(_KEY).__module__.startswith("app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_khanh_hoa.")
    assert get_attach_pipeline(_KEY).__module__.startswith(
        "app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_khanh_hoa.")


def test_khanh_hoa_pages_do_not_cross_detect():
    page = fold(_PAGE_TITLE + " " + " ".join(_ROWS))
    khanh_hoa = [p for p in PROCEDURES if "khanhhoa.gov.vn" in (p.get("detect") or {}).get("urlScope", [])]
    assert _KEY in {p["key"] for p in khanh_hoa}
    for procedure in khanh_hoa:
        hits = all(fold(text) in page for text in procedure["detect"]["textIncludes"])
        assert hits == (procedure["key"] == _KEY), procedure["key"]
    # Bản Lào Cai cùng tên vẫn khóa cổng Lào Cai.
    for key in ("xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep", "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep-lao-cai"):
        assert get_procedure(key)["detect"]["urlScope"] == ["laocai.gov.vn"], key


def test_ke_khai_link_shares_registry_key_and_ward_cards():
    links = [link for link in KE_KHAI_LINKS if link["key"] == _KEY]
    assert len(links) == 1
    assert links[0]["code"] == "1.013947"
    assert links[0]["label"] == get_procedure(_KEY)["label"]
    assert links[0]["provinceOnlyAgency"] is True and not links[0].get("selectSo")
    cap_doi = next(link for link in KE_KHAI_LINKS if link["key"] == "cap-doi-gcn-khanh-hoa")
    assert links[0]["submitCardIncludesByWard"] == cap_doi["submitCardIncludesByWard"]


def test_tro_ly_chi_tai_khoan_khanh_hoa_hoi_truong_hop_giai_quyet():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review_registry
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(_KEY)
    core = get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert "Khánh Hòa - " + procedure["label"] == core["label"]
    assert procedure["detect"] == core["detect"]
    assert procedure["keKhaiUrl"] == link["url"]
    assert handfree.procedure_code(procedure) == "1.013947"
    assert procedure["flowProfile"] == "xay-dung" and procedure["maeDialogChoice"] == {"enabled": True}
    assert procedure["bxdFlow"]["capability"] == "supportsBxdFlowKhanhHoa"
    assert procedure["agencyProvince"] == "Khánh Hòa" and procedure["agencyProvinceOnly"] is True
    assert procedure["agencyCardIncludesByWard"] == link["submitCardIncludesByWard"]
    assert handfree.is_allowed_in_province(procedure, "khanhhoa")
    assert not handfree.is_allowed_in_province(procedure, "laocai")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert {doc["key"] for doc in procedure["requiredDocs"] if not doc.get("optional")} == {"don", "gcn"}
    assert PROCEDURE_HMONG[_KEY] and PROCEDURE_HINTS[_KEY]
    assert field_review_registry.get(_KEY)["required"] == ()
