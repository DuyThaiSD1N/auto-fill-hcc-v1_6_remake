import asyncio
import re
from types import SimpleNamespace

from app.pipelines._shared import fold
from app.pipelines.dinh_chinh_gcn_da_cap_khanh_hoa.attach import planner
from app.pipelines.dinh_chinh_gcn_da_cap_khanh_hoa.attach.prompt import SYSTEM_PROMPT
from app.pipelines.dinh_chinh_gcn_da_cap_khanh_hoa.process import mapper, runner
from app.pipelines.dinh_chinh_gcn_da_cap_khanh_hoa.process.prompt import EXTRA_RULES
from app.pipelines.dinh_chinh_gcn_da_cap_khanh_hoa.process.schema import ALLOWED
from app.procedures.ke_khai_links import KE_KHAI_LINKS, procedure_province_slugs
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

_KEY = "dinh-chinh-gcn-da-cap-khanh-hoa"

# Cột "Tên giấy tờ" của 3 dòng thành phần hồ sơ trên cổng Khánh Hòa (quy trình 1.012790-1.1), đúng thứ tự DOM.
_ROWS = [
    "+ Bản gốc Giấy chứng nhận đã cấp;",
    "+ Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận so với thông tin tại thời điểm đề nghị "
    "đính chính hoặc sai sót thông tin về thửa đất, tài sản gắn liền với đất so với thông tin trên Giấy chứng nhận đã "
    "cấp;",
    "- Văn bản về việc ủy quyền theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục thông qua "
    "người đại diện.",
]
_PAGE_TITLE = (
    "Đính chính Giấy chứng nhận đã cấp. Sở Nông Nghiệp và Môi Trường. Quy trình: 1.012790-1.1 - Thủ tục Đính chính Giấy "
    "chứng nhận đã cấp - Đối với trường hợp đính chính Giấy chứng nhận đã cấp lần đầu cho tổ chức - Đối với trường hợp "
    "còn lại."
)


def _fe_fold(value: str) -> str:
    """Như foldChoiceText của FE: bỏ dấu, gộp mọi dấu gạch cùng khoảng trắng quanh nó thành một khoảng trắng."""
    return re.sub(r"\s+", " ", re.sub(r"\s*[-–—]+\s*", " ", fold(value))).strip()


def _fe_matches(row_text: str, name: str) -> bool:
    row, want = _fe_fold(row_text), _fe_fold(name)
    return row == want or want in row or row in want


def _fe_find_row(name: str, index: int | None = None) -> int | None:
    """Như findAttachmentRowByComponent của FE: dòng theo STT trước, không khớp tên mới dò dòng khớp đầu tiên."""
    if index and 1 <= index <= len(_ROWS) and _fe_matches(_ROWS[index - 1], name):
        return index
    return next((stt for stt, row in enumerate(_ROWS, start=1) if _fe_matches(row, name)), None)


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def _facts(**values) -> list[dict]:
    return [{"name": name, "value": value} for name, value in values.items()]


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields}


def _rows(attachments: list[dict]) -> list[tuple]:
    return [(item["fileIndex"], item.get("componentIndex") or item["target"]) for item in attachments]


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM (attp-row 3 dòng + nút Thêm giấy tờ)
# --------------------------------------------------------------------------------------
def test_sample_bundle_routes_like_attachment_mapping():
    """Ảnh ánh xạ: GCN -> dòng 1 và CÙNG TỆP ở dòng 2; không có ủy quyền -> bỏ tick dòng 3; Đơn Mẫu 27 -> Thêm giấy tờ."""
    attachments, warnings, _ = planner.build_plan_items(
        _files(["gcn.pdf", "don-mau-27.pdf"]), llm_types={0: ["gcn"], 1: ["don_bien_dong"]})

    assert _rows(attachments) == [(0, 1), (0, 2), (1, "add-document-dialog")]
    assert attachments[0]["untickRows"] == ["Văn bản về việc ủy quyền"]
    don = attachments[2]
    assert don["needsAddComponent"] is True and don["fallbackComponentName"] == "Giấy tờ chứng minh sai sót thông tin"
    assert "Mẫu số 27" in don["documentName"]
    assert warnings == []


def test_component_names_resolve_to_their_own_rows_on_fe():
    attachments, _, _ = planner.build_plan_items(
        _files(["gcn.pdf", "cccd.pdf", "uq.pdf"]), llm_types={0: ["gcn"], 1: ["identity"], 2: ["authorization"]})
    for item in attachments:
        assert _fe_find_row(item["componentName"], item["componentIndex"]) == item["componentIndex"], item
        assert _fe_find_row(item["componentName"]) == item["componentIndex"], item
    # Tên dòng 3 FE dùng để bỏ tick chỉ khớp đúng dòng 3; dòng 1 không lẫn vào đuôi "…Giấy chứng nhận đã cấp;" dòng 2.
    assert _fe_find_row("Văn bản về việc ủy quyền") == 3
    assert _fe_find_row("Bản gốc Giấy chứng nhận đã cấp") == 1


def test_authorization_goes_to_row_three_and_keeps_tick():
    attachments, warnings, _ = planner.build_plan_items(
        _files(["gcn.pdf", "uq.pdf", "don.pdf"]), llm_types={0: ["gcn"], 1: ["authorization"], 2: ["don_bien_dong"]})
    assert _rows(attachments) == [(0, 1), (0, 2), (1, 3), (2, "add-document-dialog")]
    assert not any(item.get("untickRows") for item in attachments)
    assert warnings == []


def test_identity_and_residence_proof_share_row_two_with_gcn_copy():
    attachments, _, classified = planner.build_plan_items(
        _files(["gcn.pdf", "cccd.pdf", "ct07.pdf", "khai-sinh.pdf"]),
        llm_types={0: ["gcn"], 1: ["identity"], 2: ["cu_tru"], 3: ["bang_chung"]})
    assert _rows(attachments) == [(0, 1), (0, 2), (1, 2), (2, 2), (3, 2)]
    assert [item["documentName"] for item in attachments[2:]] == [
        "Căn cước công dân", "Giấy xác nhận thông tin về cư trú", "Giấy tờ chứng minh sai sót thông tin"]
    assert classified[2]["componentIndex"] == 2


def test_bundle_file_stays_whole_and_warns_about_other_places():
    attachments, warnings, _ = planner.build_plan_items(
        _files(["ho-so.pdf"]), llm_types={0: ["don_bien_dong", "gcn", "identity", "authorization"]})
    # GCN đứng đầu ưu tiên: nguyên file vào dòng 1 + dòng 2; CCCD vốn ở dòng 2 nên không nhắc.
    assert _rows(attachments) == [(0, 1), (0, 2)]
    assert len(warnings) == 1
    assert "nút Thêm giấy tờ" in warnings[0] and "dòng 3" in warnings[0] and "Căn cước" not in warnings[0]
    assert "untickRows" not in attachments[0]  # file có ủy quyền: không bỏ tick dòng 3


def test_missing_gcn_and_don_are_reminded_but_empty_upload_is_silent():
    _, warnings, _ = planner.build_plan_items(_files(["cccd.pdf"]), llm_types={0: ["identity"]})
    assert any("Bản gốc Giấy chứng nhận" in w for w in warnings)
    assert any("Mẫu số 27" in w for w in warnings)
    assert planner.build_plan_items([], llm_types={}) == ([], [], [])


def test_unknown_routed_to_row_two_with_original_name():
    attachments, warnings, classified = planner.build_plan_items(
        _files(["gcn.pdf", "la.pdf"]), llm_types={0: ["gcn"], 1: ["other"]})
    assert attachments[-1]["componentIndex"] == 2 and attachments[-1]["documentName"] == "la.pdf"
    assert any("la.pdf" in w for w in warnings)
    assert classified[-1]["routedTo"] == 2


def test_attach_prompt_lists_every_type():
    for doc_type in ("don_bien_dong", "gcn", "identity", "cu_tru", "bang_chung", "authorization", "other"):
        assert f"- {doc_type}:" in SYSTEM_PROMPT
    assert "Mẫu số 27" in SYSTEM_PROMPT


def test_plan_parses_llm_doc_type_lists(monkeypatch):
    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["gcn"]},{"index":1,"docType":"don_bien_dong"}]}'

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name=name, type="application/pdf", dataUrl="x") for name in ("gcn.pdf", "don.pdf")]

    result = asyncio.run(planner.plan(files))

    assert [item.get("componentIndex") for item in result["attachments"]] == [1, 2, None]
    assert result["attachments"][2]["target"] == "add-document-dialog"
    assert result["errors"] == []


# --------------------------------------------------------------------------------------
# ĐIỀN (Form.io ba khối, cùng template cấp đổi GCN Khánh Hòa)
# --------------------------------------------------------------------------------------
_REQUEST = (
    "Đăng ký thay đổi thông tin về người sử dụng đất đối với thửa đất số 45, tờ bản đồ số 7, địa chỉ thửa đất: Thôn "
    "Đông, xã Suối Dầu, tỉnh Khánh Hòa.\n"
    "- Thay đổi giấy tờ nhân thân: ông Phạm Văn Tâm từ CMND số 225000111 sang CCCD số 056080000123.\n"
    "- Thay đổi địa chỉ: từ \"thôn Đông, xã Suối Tân, huyện Cam Lâm\" thành \"thôn Đông, xã Suối Dầu\"."
)
_OWNER = dict(
    ChuHoSo_HoTen="Phạm Văn Tâm",
    ChuHoSo_NguoiCungSuDung="Ông Phạm Văn Tâm; Bà Võ Thị Lan",
    ChuHoSo_NgaySinh="02/09/1980",
    ChuHoSo_SoDinhDanh="056 080 000 123",
    ChuHoSo_NgayCap="15/8/2021",
    ChuHoSo_NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    ChuHoSo_DienThoai="0905 111 222",
    ChuHoSo_Email="tam@example.com",
    ChuHoSo_DiaChi={"tinh": "Khánh Hòa", "xa": "xã Suối Dầu", "chiTietDuoiXa": "Thôn Đông"},
    Don_NoiDungBienDong=_REQUEST,
    GCN_NguoiSuDung="Ông Phạm Văn Tâm",
)
_PARCEL = dict(
    ThuaDat_DiaChi={"tinh": "Khánh Hòa", "xa": "Xã Suối Dầu", "chiTietDuoiXa": "Thôn Đông"},
    ThuaDat_DiaChiDayDu="Thôn Đông, xã Suối Dầu, tỉnh Khánh Hòa",
    ThuaDat_SoThua="45",
    ThuaDat_SoTo="tờ bản đồ số 7",
)


def test_self_submit_fills_all_three_blocks_and_keeps_request_lines():
    fields, warnings = mapper.enrich(_facts(**_OWNER, NguoiNop_HoTen="PHẠM VĂN TÂM", **_PARCEL))
    values = _values(fields)

    assert values["data[fullname]"] == values["data[ownerFullname]"] == "Phạm Văn Tâm"
    assert values["data[birthday]"] == values["data[ownerBirthday]"] == "02/09/1980"
    assert values["data[identityNumber]"] == values["data[ownerIdentityNumber]"] == "056080000123"
    assert values["data[identityDate]"] == values["data[ownerIdentityDate]"] == "15/08/2021"
    assert values["data[phoneNumber]"] == values["data[ownerPhoneNumber]"] == "0905111222"
    assert values["data[email]"] == values["data[ownerEmail]"] == "tam@example.com"
    assert (values["data[province1]"], values["data[village1]"], values["data[ownerAddress]"]) == (
        "Tỉnh Khánh Hòa", "Xã Suối Dầu", "Thôn Đông")
    # Nội dung yêu cầu: nguyên văn Đơn mục 2, giữ các dòng "- Thay đổi …".
    assert values["data[noidungyeucaugiaiquyet]"] == _REQUEST
    assert values["data[diaChiThuaDat]"] == "Thôn Đông, xã Suối Dầu, tỉnh Khánh Hòa"
    assert (values["data[SoThuaDat]"], values["data[SoToBanDo]"]) == ("45", "7")
    assert (values["data[province2]"], values["data[village2]"]) == ("Tỉnh Khánh Hòa", "Xã Suối Dầu")
    assert values["data[chonDoiTuong]"] == "Cá nhân"
    # Chỉ một cảnh báo: người cùng sử dụng (form có một chủ hồ sơ). GCN cùng tên chủ hồ sơ -> không nhắc lệch hồ sơ.
    assert len(warnings) == 1 and "Võ Thị Lan" in warnings[0]


def test_authorized_submitter_keeps_roles_apart():
    fields, warnings = mapper.enrich(_facts(
        **_OWNER,
        NguoiNop_HoTen="Đỗ Minh Quân",
        NguoiNop_SoDinhDanh="056 095 000 456",
        NguoiNop_NgaySinh="03/04/1995",
        NguoiNop_DiaChi={"tinh": "Khánh Hòa", "xa": "Phường Nam Nha Trang", "chiTietDuoiXa": "Tổ dân phố 1"},
        **_PARCEL,
    ))
    values = _values(fields)
    assert values["data[fullname]"] == "Đỗ Minh Quân" and values["data[identityNumber]"] == "056095000456"
    assert values["data[village]"] == "Phường Nam Nha Trang"
    assert values["data[phoneNumber]"] == ""  # số ở Đơn mục 1d là của chủ hồ sơ
    assert values["data[ownerFullname]"] == "Phạm Văn Tâm" and values["data[ownerPhoneNumber]"] == "0905111222"
    assert any("Số điện thoại người nộp" in w for w in warnings)


def test_gcn_of_another_person_is_warned_but_name_correction_is_not():
    other = dict(_OWNER, GCN_NguoiSuDung="Bà Hồ Thị Mai")
    _, warnings = mapper.enrich(_facts(**other, **_PARCEL))
    assert any("Hồ Thị Mai" in w and "cùng một hồ sơ" in w for w in warnings)

    # Đính chính chính cái tên: Đơn mục 2 nhắc tên in sai trên GCN -> không phải lệch hồ sơ.
    fixed = dict(_OWNER, GCN_NguoiSuDung="Phạm Văn Tầm",
                 Don_NoiDungBienDong="Đính chính họ tên người sử dụng đất từ Phạm Văn Tầm thành Phạm Văn Tâm.")
    _, warnings = mapper.enrich(_facts(**fixed, **_PARCEL))
    assert not any("cùng một hồ sơ" in w for w in warnings)


def test_gcn_holder_is_read_from_section_one_not_from_don():
    """LLM từng chép tên ở Đơn ("Ông A và vợ là bà B") vào GCN_NguoiSuDung: bù tất định tên in ở mục I của GCN."""
    don = ("ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\n1. Người sử dụng đất, chủ sở hữu tài sản gắn liền "
           "với đất, người quản lý đất:\na) Tên: Ông Phạm Văn Tâm, sinh năm 1980 và vợ là bà Võ Thị Lan\n")
    gcn = ("GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\nI- Người sử dụng đất, chủ sở hữu nhà ở và tài sản khác gắn liền với đất "
           "Hộ bà: Hồ Thị Mai Năm sinh: 1950 Số CMND: 225000999\nII- Thửa đất, nhà ở và tài sản khác gắn liền với đất\n"
           "IV. Những thay đổi sau khi cấp Giấy chứng nhận\nNguồn gốc sử dụng đất có sai sót, được đính chính lại.")
    documents = [{"text": don}, {"text": gcn}]
    assert runner.gcn_holder(don + gcn) == "Hộ bà: Hồ Thị Mai"
    fields = runner.apply_fallback({"GCN_NguoiSuDung": "Ông Phạm Văn Tâm và vợ là bà Võ Thị Lan"}, documents)
    assert fields["GCN_NguoiSuDung"] == "Hộ bà: Hồ Thị Mai"
    _, warnings = mapper.enrich(_facts(**dict(_OWNER, GCN_NguoiSuDung=fields["GCN_NguoiSuDung"]), **_PARCEL))
    assert any("Hồ Thị Mai" in w and "cùng một hồ sơ" in w for w in warnings)

    # Mục IV có chuyển nhượng: người hiện tại là người nhận -> không ghi đè, để LLM đọc.
    transferred = gcn.replace("Nguồn gốc sử dụng đất có sai sót, được đính chính lại.", "Chuyển nhượng cho ông X.")
    assert runner.gcn_holder(transferred) is None
    # Không có trang GCN (chỉ Đơn): không bịa.
    assert runner.gcn_holder(don) is None


def test_gcn_listing_both_spouses_matches_owner():
    both = dict(_OWNER, GCN_NguoiSuDung="Ông Phạm Văn Tâm và vợ là bà Võ Thị Lan")
    _, warnings = mapper.enrich(_facts(**both, **_PARCEL))
    assert not any("cùng một hồ sơ" in w for w in warnings)


def test_missing_required_fields_are_returned_blank_and_reminded():
    fields, warnings = mapper.enrich(_facts(ChuHoSo_HoTen="Phạm Văn Tâm", ChuHoSo_NgaySinh="1980"))
    values = _values(fields)
    cleared = {item["name"]: item for item in fields if item.get("clear")}
    assert values["data[birthday]"] == values["data[ownerBirthday]"] == ""
    assert cleared["data[ownerBirthday]"]["markEmpty"] is True
    assert any("Phường/xã của thửa đất" in w and "đã để trống" in w for w in warnings)


def test_request_falls_back_to_procedure_name_with_serial():
    owner = {key: value for key, value in _OWNER.items() if key != "Don_NoiDungBienDong"}
    fields, _ = mapper.enrich(_facts(**owner, GCN_SoPhatHanh="AB 123456", **_PARCEL))
    item = next(item for item in fields if item["name"] == "data[noidungyeucaugiaiquyet]")
    assert item["value"] == "Đính chính Giấy chứng nhận đã cấp số phát hành AB 123456" and item["default"] is True


def test_schema_and_prompt_cover_correction_traps():
    assert {"Don_NoiDungBienDong", "GCN_NguoiSuDung", "GCN_SoPhatHanh", "ThuaDat_DiaChiDayDu"} <= ALLOWED
    assert "từ X sang Y" in EXTRA_RULES and "KHÔNG chép giá trị sai" in EXTRA_RULES
    assert "Nam Nha Trang" in EXTRA_RULES


# --------------------------------------------------------------------------------------
# REGISTRY + LINK KÊ KHAI + TRỢ LÝ
# --------------------------------------------------------------------------------------
def test_registry_wires_both_pipelines_and_locks_khanh_hoa():
    procedure = get_procedure(_KEY)
    assert procedure["label"] == "Khánh Hòa - Đính chính Giấy chứng nhận đã cấp"
    assert procedure["detect"]["urlScope"] == ["khanhhoa.gov.vn"]
    assert procedure_province_slugs(procedure) == ["khanhhoa"]
    assert get_pipeline(_KEY).__module__.startswith("app.pipelines.dinh_chinh_gcn_da_cap_khanh_hoa.")
    assert get_attach_pipeline(_KEY).__module__.startswith("app.pipelines.dinh_chinh_gcn_da_cap_khanh_hoa.")


def test_khanh_hoa_pages_do_not_cross_detect():
    """Trên cổng Khánh Hòa: trang đính chính chỉ khớp thủ tục này; trang cấp đổi không khớp đính chính."""
    page = fold(_PAGE_TITLE + " " + " ".join(_ROWS))
    khanh_hoa = [p for p in PROCEDURES if "khanhhoa.gov.vn" in (p.get("detect") or {}).get("urlScope", [])]
    for procedure in khanh_hoa:
        hits = all(fold(text) in page for text in procedure["detect"]["textIncludes"])
        assert hits == (procedure["key"] == _KEY), procedure["key"]
    cap_doi_page = fold("Cấp đổi Giấy chứng nhận quyền sử dụng đất. Quy trình: 1.012783-1.1 - Bản gốc Giấy chứng nhận "
                        "đã cấp.")
    assert not all(fold(text) in cap_doi_page for text in get_procedure(_KEY)["detect"]["textIncludes"])
    # Cùng mã ở cổng Lào Cai: bản Lào Cai khóa laocai.gov.vn, bản này khóa khanhhoa.gov.vn.
    assert get_procedure("dinh-chinh-gcn-da-cap-dvcqg-lao-cai")["detect"]["urlScope"] == ["laocai.gov.vn"]


def test_ke_khai_link_shares_registry_key_and_picks_branch_by_ward():
    (link,) = [link for link in KE_KHAI_LINKS if link["key"] == _KEY]
    assert link["code"] == "1.012790"
    assert link["label"] == get_procedure(_KEY)["label"]
    assert link["provinceOnlyAgency"] is True and not link.get("selectSo")
    cap_doi = next(item for item in KE_KHAI_LINKS if item["key"] == "cap-doi-gcn-khanh-hoa")
    assert link["submitCardIncludesByWard"] == cap_doi["submitCardIncludesByWard"]
    assert link["submitCardIncludesByWard"]["Xã Suối Dầu"] == "Chi nhánh Văn phòng Đăng ký đất đai Cam Lâm"


def test_tro_ly_chi_tai_khoan_khanh_hoa_dung_pipeline_loi():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review_registry
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(_KEY)
    core = get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert "Khánh Hòa - " + procedure["label"] == core["label"]
    assert "Khánh Hòa" not in procedure["shortLabel"]
    assert procedure["detect"] == core["detect"]
    assert procedure["keKhaiUrl"] == link["url"]
    assert handfree.procedure_code(procedure) == "1.012790"
    assert procedure["flowProfile"] == "xay-dung" and procedure["maePortal"] is True
    assert procedure["bxdFlow"]["capability"] == "supportsBxdFlowKhanhHoa"
    assert field_review_registry.get(_KEY)["required"] == ()
    assert procedure["agencyProvinceOnly"] is True and "agencySoFirst" not in procedure
    assert procedure["agencyCardIncludesByWard"] == link["submitCardIncludesByWard"]
    assert handfree.is_allowed_in_province(procedure, "khanhhoa")
    assert not handfree.is_allowed_in_province(procedure, "laocai")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert {doc["key"] for doc in procedure["requiredDocs"] if not doc.get("optional")} == {"don", "gcn"}
    assert PROCEDURE_HMONG[_KEY] and PROCEDURE_HINTS[_KEY]
