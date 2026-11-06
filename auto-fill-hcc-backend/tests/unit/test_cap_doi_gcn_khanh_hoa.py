import asyncio
import re
from types import SimpleNamespace

from app.pipelines._shared import fold
from app.pipelines.cap_doi_gcn_khanh_hoa.attach import planner
from app.pipelines.cap_doi_gcn_khanh_hoa.attach.prompt import SYSTEM_PROMPT
from app.pipelines.cap_doi_gcn_khanh_hoa.process import mapper
from app.pipelines.cap_doi_gcn_khanh_hoa.process.prompt import EXTRA_RULES
from app.pipelines.cap_doi_gcn_khanh_hoa.process.runner import apply_printed_fallback
from app.pipelines.cap_doi_gcn_khanh_hoa.process.schema import ALLOWED
from app.procedures.ke_khai_links import KE_KHAI_LINKS, procedure_province_slugs
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

_KEY = "cap-doi-gcn-khanh-hoa"

# Cột "Tên giấy tờ" của 4 dòng thành phần hồ sơ trên cổng Khánh Hòa, đúng thứ tự DOM (file mapping, Phần IV).
_ROWS = [
    "(2) Bản gốc Giấy chứng nhận đã cấp.",
    "Giấy chứng nhận quyền sử dụng đất; Giấy chứng nhận quyền sở hữu nhà ở và quyền sử dụng đất ở; Giấy chứng nhận "
    "quyền sở hữu nhà ở; Giấy chứng nhận quyền sở hữu công trình xây dựng; Giấy chứng nhận quyền sử dụng đất, quyền sở "
    "hữu nhà ở và tài sản khác gắn liền với đất; Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với "
    "đất",
    "(3) Mảnh trích đo bản đồ địa chính thửa đất đối với trường hợp trích đo địa chính thửa đất mà ranh giới thửa đất "
    "không thay đổi hoặc trường hợp cấp đổi Giấy chứng nhận mà người sử dụng đất có nhu cầu đo đạc để xác định lại "
    "kích thước các cạnh, diện tích của thửa đất.",
    "(1) Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18 ban hành kèm theo Nghị định số "
    "151/2025/NĐ-CP. Trường hợp hộ gia đình có yêu cầu ghi đầy đủ tên thành viên có chung quyền sử dụng đất của hộ gia "
    "đình thì trong Đơn đăng ký biến động đất đai, tài sản gắn liền với đất phải thể hiện thông tin các thành viên có "
    "chung quyền sử dụng đất của hộ gia đình.",
]
_PAGE_TITLE = (
    "Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất. Quy trình: 1.012783-1.1 - Cấp "
    "đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất - Đối với trường hợp còn lại."
)


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
# ĐÍNH KÈM (attp-row 4 dòng + nút Thêm giấy tờ)
# --------------------------------------------------------------------------------------
def test_sample_bundle_routes_like_attachment_mapping():
    """Ánh xạ hồ sơ: file GCN (bìa + thửa + trang bổ sung) nguyên khối -> dòng 1, Đơn -> dòng 4, dòng 2 bỏ trống,
    dòng 3 tick sẵn mà hồ sơ không có trích đo -> nhắc cán bộ."""
    attachments, warnings, classified = planner.build_plan_items(
        _files(["gcn.pdf", "don.pdf"]), None, {0: ["gcn"], 1: ["don_bien_dong"]}
    )
    assert [(item["componentIndex"], item["fileName"]) for item in attachments] == [(1, "gcn.pdf"), (4, "don.pdf")]
    assert all(item["target"] == "attp-row" and "loaiBan" not in item for item in attachments)
    assert [_fe_find_row(item["componentName"], item["componentIndex"]) for item in attachments] == [1, 4]
    assert [item["componentIndex"] for item in classified] == [1, 4]
    assert len(warnings) == 1 and "Dòng 3" in warnings[0] and "bỏ tick" in warnings[0]


def test_component_name_resolves_to_its_own_row_on_fe():
    rows = {route["row"] for route in planner._ROUTES.values()}
    assert rows == {1, 3, 4}  # dòng 2 cùng loại GCN với dòng 1: không đính
    for doc_type, route in planner._ROUTES.items():
        assert _fe_find_row(route["name"], route["row"]) == route["row"], doc_type
        # Dò theo tên (khi FE lệch STT) cũng ra đúng dòng.
        assert _fe_find_row(route["name"], 99) == route["row"], doc_type
    assert _fe_find_row(planner._ADD_DOCUMENT["componentName"], 99) is None


def test_trich_do_file_goes_to_row_three_and_silences_reminder():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["gcn.pdf", "trich-do.pdf", "don.pdf"]), None,
        {0: ["gcn"], 1: ["manh_trich_do"], 2: ["don_bien_dong"]},
    )
    assert [item["componentIndex"] for item in attachments] == [1, 3, 4]
    assert warnings == []


def test_bundle_file_stays_whole_on_highest_priority_place():
    attachments, warnings, classified = planner.build_plan_items(
        _files(["tat-ca.pdf"]), None, {0: ["gcn", "don_bien_dong", "identity", "manh_trich_do"]}
    )
    assert [item["componentIndex"] for item in attachments] == [4]
    assert classified[0]["docTypes"] == ["gcn", "don_bien_dong", "identity", "manh_trich_do"]
    assert len(warnings) == 1
    assert "dòng 1" in warnings[0] and "dòng 3" in warnings[0] and "nhân thân" not in warnings[0]


def test_authorization_goes_to_add_dialog_with_don_row_fallback():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["gcn.pdf", "don.pdf", "uq.pdf"]), None,
        {0: ["gcn"], 1: ["don_bien_dong"], 2: ["authorization", "identity"]},
    )
    uq = attachments[2]
    assert uq["target"] == "add-document-dialog" and uq["needsAddComponent"] is True
    assert "componentIndex" not in uq
    assert _fe_find_row(uq["fallbackComponentName"], 4) == 4
    assert uq["formOptionHints"][0] == uq["componentName"] == "Giấy ủy quyền"
    assert not any("uq.pdf" in warning for warning in warnings)


def test_missing_gcn_and_don_are_reminded_but_empty_upload_is_silent():
    _attachments, warnings, _classified = planner.build_plan_items(_files(["cccd.pdf"]), None, {0: ["identity"]})
    assert len(warnings) == 3
    assert "Bản gốc Giấy chứng nhận" in warnings[0] and "Đơn đăng ký biến động" in warnings[2]
    assert planner.build_plan_items([], None, {}) == ([], [], [])


def test_unknown_routed_to_don_row_with_original_name():
    attachments, warnings, classified = planner.build_plan_items(
        _files(["gcn.pdf", "la.pdf", "trong.pdf"]), None, {0: ["gcn"], 1: "abc"}
    )
    assert [item["componentIndex"] for item in attachments] == [1, 4, 4]
    assert [item["documentName"] for item in attachments[1:]] == ["la.pdf", "trong.pdf"]
    assert sum("Chưa nhận diện chắc" in warning for warning in warnings) == 2
    assert [item["source"] for item in classified] == ["llm", "llm", "unknown"]


def test_attach_prompt_lists_every_type():
    for doc_type in list(planner._ROUTES) + ["authorization", "other"]:
        assert doc_type in SYSTEM_PROMPT
    assert '"docTypes"' in SYSTEM_PROMPT and "III. Sơ đồ thửa đất" in SYSTEM_PROMPT
    # Chữ ký thay của cơ quan trên GCN từng bị LLM gắn nhầm "authorization".
    assert "KT. CHỦ TỊCH" in SYSTEM_PROMPT and "TM. ỦY BAN" in SYSTEM_PROMPT


def test_plan_parses_llm_doc_type_lists(monkeypatch):
    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["gcn"]},{"index":1,"docType":"don_bien_dong"}]}'

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name=name, type="application/pdf", dataUrl="x") for name in ("gcn.pdf", "don.pdf")]

    result = asyncio.run(planner.plan(files))

    assert [item["componentIndex"] for item in result["attachments"]] == [1, 4]
    assert any("Dòng 3" in error for error in result["errors"])


# --------------------------------------------------------------------------------------
# ĐIỀN (Form.io ba khối, cùng template đăng ký đất đai lần đầu Khánh Hòa)
# --------------------------------------------------------------------------------------
_OWNER = dict(
    ChuHoSo_HoTen="LÊ THỊ HOA",
    ChuHoSo_NgaySinh="5 - 3 - 1965",
    ChuHoSo_SoDinhDanh="056 165 012 345",
    ChuHoSo_DienThoai="0905.123.456",
    # Đơn viết tay chỉ ghi tổ dân phố + phường, không ghi tỉnh.
    ChuHoSo_DiaChi={"xa": "phường Nam Nha Trang", "chiTietDuoiXa": "Tổ dân phố 3"},
    Don_NoiDungBienDong="Cấp đổi sổ do bị rách",
)
_PARCEL = dict(
    ThuaDat_DiaChi={"tinh": "Khánh Hòa", "xa": "Xã Phước Đồng", "chiTietDuoiXa": "Thôn A"},
    ThuaDat_DiaChiDayDu="Thôn A - Xã Phước Đồng - Nha Trang - Khánh Hòa.",
    ThuaDat_SoThua="Thửa đất số: 12",
    ThuaDat_SoTo="3",
)


def test_self_submit_fills_all_three_blocks():
    fields, warnings = mapper.enrich(_facts(**_OWNER, NguoiNop_HoTen="Lê Thị Hoa", **_PARCEL))
    values = _values(fields)

    assert values["data[fullname]"] == values["data[ownerFullname]"] == "LÊ THỊ HOA"
    assert values["data[birthday]"] == values["data[ownerBirthday]"] == "05/03/1965"
    assert values["data[identityNumber]"] == values["data[ownerIdentityNumber]"] == "056165012345"
    assert values["data[phoneNumber]"] == values["data[ownerPhoneNumber]"] == "0905123456"
    # Tỉnh bù từ tỉnh thửa đất vì phường thuộc đúng tỉnh đó.
    assert (values["data[province]"], values["data[village]"], values["data[address]"]) == (
        "Tỉnh Khánh Hòa", "Phường Nam Nha Trang", "Tổ dân phố 3")
    assert (values["data[province1]"], values["data[village1]"], values["data[ownerAddress]"]) == (
        "Tỉnh Khánh Hòa", "Phường Nam Nha Trang", "Tổ dân phố 3")
    assert values["data[noidungyeucaugiaiquyet]"] == "Cấp đổi sổ do bị rách"
    assert values["data[chonDoiTuong]"] == "Cá nhân"
    # Thửa đất: chữ nguyên văn GCN, phường/xã cũ đổi sang đơn vị sau sắp xếp để khớp danh sách của cổng.
    assert values["data[diaChiThuaDat]"] == "Thôn A - Xã Phước Đồng - Nha Trang - Khánh Hòa."
    assert (values["data[SoThuaDat]"], values["data[SoToBanDo]"]) == ("12", "3")
    assert (values["data[province2]"], values["data[village2]"]) == ("Tỉnh Khánh Hòa", "Phường Nam Nha Trang")
    defaults = {item["name"] for item in fields if item.get("default")}
    assert defaults == {"data[chonDoiTuong]", "data[nation2]"}
    assert warnings == []


def test_authorized_submitter_keeps_roles_apart():
    fields, warnings = mapper.enrich(_facts(
        **_OWNER,
        NguoiNop_HoTen="Trần Văn Bình",
        NguoiNop_SoDinhDanh="056 090 012 345",
        NguoiNop_NgaySinh="20/10/1990",
        NguoiNop_DiaChi={"tinh": "Gia Lai", "xa": "xã Bình Hiệp", "chiTietDuoiXa": "Thôn B"},
        **_PARCEL,
    ))
    values = _values(fields)

    assert values["data[fullname]"] == "Trần Văn Bình"
    assert values["data[identityNumber]"] == "056090012345"
    assert (values["data[province]"], values["data[village]"]) == ("Tỉnh Gia Lai", "Xã Bình Hiệp")
    # Số ở Đơn mục 1d là của chủ hồ sơ: không gán cho người được ủy quyền — trả về trống, không để số tài khoản.
    assert values["data[phoneNumber]"] == ""
    assert values["data[ownerFullname]"] == "LÊ THỊ HOA"
    assert values["data[ownerPhoneNumber]"] == "0905123456"
    assert len(warnings) == 1 and "Số điện thoại người nộp" in warnings[0]


def test_ward_outside_portal_province_is_not_given_a_wrong_province():
    owner = dict(_OWNER, ChuHoSo_DiaChi={"xa": "Phường Hải Châu", "chiTietDuoiXa": "K15 Lê Lợi"})
    values = _values(mapper.enrich(_facts(**owner, **_PARCEL))[0])
    assert "data[province1]" not in values
    assert values["data[ownerAddress]"] == "K15 Lê Lợi"


def test_missing_required_fields_are_returned_blank_and_reminded():
    fields, warnings = mapper.enrich(_facts(ChuHoSo_HoTen="LÊ THỊ HOA", ChuHoSo_NgaySinh="1965"))
    values = _values(fields)
    # Không có ngày sinh đầy đủ: trả về TRỐNG (xoá ngày sinh cổng đổ theo tài khoản) + tô đỏ, không bỏ qua ô.
    cleared = {item["name"]: item for item in fields if item.get("clear")}
    assert values["data[birthday]"] == values["data[ownerBirthday]"] == ""
    assert cleared["data[birthday]"]["markEmpty"] is True and cleared["data[ownerBirthday]"]["markEmpty"] is True
    assert len(warnings) == 1
    for label in ("Số điện thoại người nộp", "Ngày sinh người nộp", "CMND/CCCD chủ hồ sơ", "Phường/xã của thửa đất"):
        assert label in warnings[0]
    assert "Họ tên" not in warnings[0] and "đã để trống" in warnings[0]


def test_request_falls_back_to_procedure_name_with_serial():
    owner = {key: value for key, value in _OWNER.items() if key != "Don_NoiDungBienDong"}
    fields, _warnings = mapper.enrich(_facts(**owner, GCN_SoPhatHanh="AB 123456", **_PARCEL))
    item = next(item for item in fields if item["name"] == "data[noidungyeucaugiaiquyet]")
    assert item["value"] == mapper.DEFAULT_REQUEST + " số phát hành AB 123456"
    assert item["default"] is True


def test_co_user_and_organisation_owner():
    fields, warnings = mapper.enrich(_facts(**_OWNER, ChuHoSo_NguoiCungSuDung="Nguyễn Văn Nam", **_PARCEL))
    assert len(warnings) == 1 and "Nguyễn Văn Nam" in warnings[0] and "LÊ THỊ HOA" in warnings[0]

    fields, _warnings = mapper.enrich(_facts(ChuHoSo_HoTen="Công ty TNHH Ví Dụ", **_PARCEL))
    assert _values(fields)["data[chonDoiTuong]"] == "Tổ chức"


def test_printed_fallback_fills_parcel_numbers_only_when_unambiguous():
    documents = [
        {"text": "II. Thửa đất\na) Thửa đất số:      12 , tờ bản đồ số:   3;\nPhần còn lại thửa 233"},
        {"text": "TRANG BỔ SUNG GIẤY CHỨNG NHẬN\nThửa đất số: 12      Tờ bản đồ số: 03"},
    ]
    assert apply_printed_fallback([], documents) == {"ThuaDat_SoThua": "12", "ThuaDat_SoTo": "3"}
    # LLM đã có số thì giữ.
    assert apply_printed_fallback({"ThuaDat_SoThua": "15"}, documents)["ThuaDat_SoThua"] == "15"
    # Hai số thửa khác nhau (vd tách thửa) -> không bù.
    documents.append({"text": "tách từ thửa đất số 9"})
    assert "ThuaDat_SoThua" not in apply_printed_fallback([], documents)


_DON_TEXT = (
    "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\n1. Người sử dụng đất…\na) Tên(2):\nLÊ THỊ HOA\n"
    "c) Địa chỉ(2):\nTổ dân phố Hòa Bình, Hòn Rớ 2 phường Nam nha trang\nd) Điện thoại liên hệ (nếu có): 0905123456"
)


def test_don_ward_replaces_hamlet_name_llm_took_as_ward():
    """LLM áp quy tắc CCCD (bỏ cụm sát trước tỉnh) cho dòng Đơn: lấy tên tổ dân phố làm phường. Phường đó không có
    trong danh mục tỉnh -> lấy phường ghi rõ sau chữ "phường" trên Đơn, cho cả hai khối khi tự nộp."""
    wrong = {"tinh": "Khánh Hòa", "xa": "Phường Hòa Bình", "chiTietDuoiXa": "Tổ dân phố Hòa Bình, Hòn Rớ 2"}
    raw = {"ChuHoSo_HoTen": "LÊ THỊ HOA", "ChuHoSo_DiaChi": dict(wrong),
           "NguoiNop_HoTen": "Lê Thị Hoa", "NguoiNop_DiaChi": dict(wrong)}
    fields = apply_printed_fallback(raw, [{"text": _DON_TEXT}])
    for name in ("ChuHoSo_DiaChi", "NguoiNop_DiaChi"):
        assert fields[name]["xa"] == "Phường Nam Nha Trang", name
        assert fields[name]["chiTietDuoiXa"] == "Tổ dân phố Hòa Bình, Hòn Rớ 2", name


def test_don_ward_keeps_valid_llm_ward_and_authorized_submitter():
    raw = {
        "ChuHoSo_HoTen": "LÊ THỊ HOA",
        # Phường hợp lệ (vd đọc từ CCCD, nguồn ưu tiên) -> giữ.
        "ChuHoSo_DiaChi": {"tinh": "Khánh Hòa", "xa": "Phường Bắc Nha Trang", "chiTietDuoiXa": "Tổ 1"},
        # Người được ủy quyền: địa chỉ ở Đơn không phải của họ -> không đụng.
        "NguoiNop_HoTen": "Trần Văn Bình",
        "NguoiNop_DiaChi": {"tinh": "Khánh Hòa", "xa": "Phường Hòa Bình", "chiTietDuoiXa": "Tổ 2"},
    }
    fields = apply_printed_fallback(raw, [{"text": _DON_TEXT}])
    assert fields["ChuHoSo_DiaChi"]["xa"] == "Phường Bắc Nha Trang"
    assert fields["NguoiNop_DiaChi"]["xa"] == "Phường Hòa Bình"
    # Không có dòng "c) Địa chỉ" -> không bù gì.
    assert apply_printed_fallback({"ChuHoSo_DiaChi": raw["NguoiNop_DiaChi"]}, [{"text": "Tổ 2 phường Nam Nha Trang"}])[
        "ChuHoSo_DiaChi"]["xa"] == "Phường Hòa Bình"


def test_don_ward_reads_new_form_18_layout_and_skips_signature_block():
    """Mẫu 18 mới ghi "- Địa chỉ(4): <chi tiết> - phường X - Tỉnh Y"; khối chữ ký số in "Địa chỉ: CƠ QUAN …" ngay dưới
    tiêu đề không được coi là địa chỉ người sử dụng đất."""
    text = (
        "Mẫu số 18. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất\nĐịa chỉ: CƠ QUAN VĂN PHÒNG ĐĂNG KÝ\n"
        "I. Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất:\n- Tên(2): LÊ THỊ HOA\n"
        "- Địa chỉ(4): Đường Số 5 - Tổ dân phố Hòa Bình -\n- phường Nam Nha Trang - Tỉnh Khánh Hòa.\n"
        "- Mã số thuế (nếu có):\nII. Nội dung biến động(5): nhận tặng cho\n"
        "Tờ khai\n[08] Địa chỉ: TDP Hòa Bình, phường Bắc Nha Trang"
    )
    raw = {"ChuHoSo_HoTen": "LÊ THỊ HOA",
           "ChuHoSo_DiaChi": {"tinh": "Khánh Hòa", "xa": "Phường Hòa Bình", "chiTietDuoiXa": "Đường Số 5"}}
    assert apply_printed_fallback(raw, [{"text": text}])["ChuHoSo_DiaChi"]["xa"] == "Phường Nam Nha Trang"


def test_ward_missing_from_catalog_is_warned():
    owner = dict(_OWNER, ChuHoSo_DiaChi={"tinh": "Khánh Hòa", "xa": "Phường Hòa Bình", "chiTietDuoiXa": "Tổ 2"})
    fields, warnings = mapper.enrich(_facts(**owner, **_PARCEL))
    assert _values(fields)["data[village1]"] == "Phường Hòa Bình"
    assert [warning for warning in warnings if "không có trong danh mục" in warning] == [
        "Phường/xã 'Phường Hòa Bình' (người nộp) không có trong danh mục Tỉnh Khánh Hòa — cán bộ chọn lại.",
        "Phường/xã 'Phường Hòa Bình' (chủ hồ sơ) không có trong danh mục Tỉnh Khánh Hòa — cán bộ chọn lại.",
    ]


def test_schema_and_prompt_cover_transfer_chain_traps():
    assert {"ChuHoSo_NguoiCungSuDung", "Don_NoiDungBienDong", "GCN_SoPhatHanh", "ThuaDat_DiaChiDayDu"} <= ALLOWED
    assert "MUỘN NHẤT" in EXTRA_RULES and "Thế chấp" in EXTRA_RULES and "Người ký" in EXTRA_RULES


# --------------------------------------------------------------------------------------
# REGISTRY + LINK KÊ KHAI + TRỢ LÝ
# --------------------------------------------------------------------------------------
def test_registry_wires_both_pipelines_and_locks_khanh_hoa():
    procedure = get_procedure(_KEY)
    assert procedure["label"] == (
        "Khánh Hòa - Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất")
    assert procedure["detect"]["urlScope"] == ["khanhhoa.gov.vn"]
    assert procedure_province_slugs(procedure) == ["khanhhoa"]
    assert get_pipeline(_KEY).__module__.startswith("app.pipelines.cap_doi_gcn_khanh_hoa.")
    assert get_attach_pipeline(_KEY).__module__.startswith("app.pipelines.cap_doi_gcn_khanh_hoa.")


def test_khanh_hoa_pages_do_not_cross_detect():
    """Trên cổng Khánh Hòa: trang cấp đổi chỉ khớp cụm của thủ tục này; dòng "cấp đổi sang Giấy chứng nhận" của thủ
    tục giao đất không khớp cụm cấp đổi."""
    page = fold(_PAGE_TITLE + " " + " ".join(_ROWS))
    khanh_hoa = [p for p in PROCEDURES if "khanhhoa.gov.vn" in (p.get("detect") or {}).get("urlScope", [])]
    assert _KEY in {p["key"] for p in khanh_hoa}
    for procedure in khanh_hoa:
        hits = all(fold(text) in page for text in procedure["detect"]["textIncludes"])
        assert hits == (procedure["key"] == _KEY), procedure["key"]
    giao_dat_row = ("không phải cấp đổi sang Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất")
    assert fold(get_procedure(_KEY)["detect"]["textIncludes"][0]) not in fold(giao_dat_row)


def test_ke_khai_link_shares_registry_key():
    links = [link for link in KE_KHAI_LINKS if link["key"] == _KEY]
    assert len(links) == 1
    assert links[0]["code"] == "1.012783"
    assert links[0]["label"] == get_procedure(_KEY)["label"]


def test_tro_ly_chi_tai_khoan_khanh_hoa_dung_pipeline_loi():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(_KEY)
    core = get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert "Khánh Hòa - " + procedure["label"] == core["label"]
    assert "Khánh Hòa" not in procedure["shortLabel"]
    assert procedure["detect"] == core["detect"]
    assert procedure["keKhaiUrl"] == link["url"]
    assert handfree.procedure_code(procedure) == "1.012783"
    assert procedure["agencyProvince"] == "Khánh Hòa"
    # DVCQG chỉ chọn Tỉnh Khánh Hòa, không chọn Phường/Xã, không gạt "Sở" — khớp cờ của link kê khai.
    assert link.get("provinceOnlyAgency") is True and not link.get("selectSo")
    assert procedure["agencyProvinceOnly"] is True and "agencySoFirst" not in procedure
    assert handfree.is_allowed_in_province(procedure, "khanhhoa")
    assert not handfree.is_allowed_in_province(procedure, "bacninh")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert {doc["key"] for doc in procedure["requiredDocs"] if not doc.get("optional")} == {"don", "gcn"}
    assert PROCEDURE_HMONG[_KEY] and PROCEDURE_HINTS[_KEY]
    assert procedure["agencyCardIncludesByWard"] == link["submitCardIncludesByWard"]


_KH_CARD_KEYS = ("cap-doi-gcn-khanh-hoa", "dang-ky-bien-dong-chuyen-nhuong-thua-ke-tang-cho-khanh-hoa")


def test_hai_link_khanh_hoa_chi_chon_tinh_roi_bam_chi_nhanh_vpdk_cua_xa():
    """1.012783 + 1.013831 Khánh Hòa: DVCQG chỉ chọn Tỉnh; trang kết quả ra thẻ VPĐK tỉnh (thẻ đầu) rồi từng Chi nhánh
    VPĐK đất đai theo huyện cũ → bấm chi nhánh của xã đang chọn, không bấm thẻ đầu."""
    from app.locations.catalog import WARDS_BY_SLUG

    links = {link["key"]: link for link in KE_KHAI_LINKS if link["key"] in _KH_CARD_KEYS}
    assert {link["code"] for link in links.values()} == {"1.012783", "1.013831"}
    communes = set(WARDS_BY_SLUG["khanhhoa"]["communes"])
    for key, link in links.items():
        assert link["provinceOnlyAgency"] is True and not link.get("selectSo"), key
        by_ward = link["submitCardIncludesByWard"]
        assert by_ward == links[_KH_CARD_KEYS[0]]["submitCardIncludesByWard"], key
        # Popup so tên xã tuyệt đối với danh mục (đã đổi "Hoà" → "Hòa") → khóa phải đúng chữ danh mục.
        assert set(by_ward) <= communes, set(by_ward) - communes
        assert all(card.startswith("Chi nhánh Văn phòng Đăng ký đất đai ") for card in by_ward.values()), key
    by_ward = links[_KH_CARD_KEYS[0]]["submitCardIncludesByWard"]
    assert by_ward["Phường Nam Nha Trang"] == "Chi nhánh Văn phòng Đăng ký đất đai Nha Trang"
    assert by_ward["Xã Nam Cam Ranh"] == "Chi nhánh Văn phòng Đăng ký đất đai Cam Ranh"
    assert by_ward["Xã Suối Dầu"] == "Chi nhánh Văn phòng Đăng ký đất đai Cam Lâm"
    assert by_ward["Xã Tân Định"] == "Chi nhánh Văn phòng Đăng ký đất đai Ninh Hòa"
    assert by_ward["Xã Suối Hiệp"] == "Chi nhánh Văn phòng Đăng ký đất đai Diên Khánh"
    # 7 chi nhánh vùng Ninh Thuận cũ (QĐ 296/QĐ-UBND 12/7/2025) — gán theo huyện cũ của các xã nhập vào.
    assert by_ward["Phường Đông Hải"] == "Chi nhánh Văn phòng Đăng ký đất đai Phan Rang"
    assert by_ward["Phường Ninh Chử"] == "Chi nhánh Văn phòng Đăng ký đất đai Ninh Hải"
    assert by_ward["Xã Công Hải"] == "Chi nhánh Văn phòng Đăng ký đất đai Thuận Bắc"
    assert by_ward["Xã Anh Dũng"] == "Chi nhánh Văn phòng Đăng ký đất đai Ninh Sơn"
    assert by_ward["Xã Cà Ná"] == "Chi nhánh Văn phòng Đăng ký đất đai Thuận Nam"
    assert len({card for card in by_ward.values()}) == 15
    # Chỉ Đặc khu Trường Sa không có chi nhánh → giữ quy ước thẻ đầu (VPĐK tỉnh).
    assert communes - set(by_ward) == {"Đặc khu Trường Sa"}


def test_tro_ly_khanh_hoa_chi_chon_tinh_va_bam_the_chi_nhanh_theo_xa():
    from app.channels.handfree.chat import flow
    from app.channels.handfree.chat.flow import Intent

    proc = flow.get_procedure(_KEY)
    loc = {"province": "Tỉnh Khánh Hòa", "province_slug": "khanhhoa", "ward": "Phường Nam Nha Trang"}
    conv = {"_id": "t-kh-card", "state": "guide_login", "history": [], "milestones": [], "procedure_key": _KEY,
            "client_capabilities": {"supportsAgencyCard": True}, "location": dict(loc)}
    r = flow._guide_login_on_page(conv, proc, dict(loc), {"agencyBlock": True})  # noqa: SLF001
    assert r.actions == [{"type": "select_agency", "province": r.actions[0]["province"], "ward": "",
                          "cardIncludes": "Chi nhánh Văn phòng Đăng ký đất đai Nha Trang"}]
    assert "Khánh Hòa" in r.actions[0]["province"]
    # Dấu cũ "Hoà" vẫn ra đúng chi nhánh; xã không có trong bảng (Trường Sa) thì về quy ước thẻ đầu như trước.
    assert flow._agency_card(proc, {"ward": "Xã Bắc Ninh Hoà"}) == "Chi nhánh Văn phòng Đăng ký đất đai Ninh Hòa"  # noqa: SLF001
    assert flow._agency_card(proc, {"ward": "Phường Phan Rang"}) == "Chi nhánh Văn phòng Đăng ký đất đai Phan Rang"  # noqa: SLF001
    assert flow._agency_card(proc, {"ward": "Đặc khu Trường Sa"}) == ""  # noqa: SLF001
    missing = flow._handle_guide_login(conv, Intent("event", "agency_card_missing", {"value": "x"}))  # noqa: SLF001
    assert "Chi nhánh Văn phòng Đăng ký đất đai Nha Trang" in missing.display_md
    # Trợ lý bản cũ (chưa biết chọn thẻ): dặn chọn tay, chỉ đọc tỉnh — không ra ", Tỉnh Khánh Hòa".
    old = {"_id": "t-kh-card-old", "state": "guide_login", "history": [], "milestones": [], "procedure_key": _KEY,
           "client_capabilities": {}, "location": dict(loc)}
    manual = flow._guide_login_on_page(old, proc, dict(loc), {"agencyBlock": True})  # noqa: SLF001
    assert manual.actions == [] and "Chi nhánh Văn phòng Đăng ký đất đai Nha Trang" in manual.display_md
    assert "**, " not in manual.display_md and "Khánh Hòa**" in manual.display_md
