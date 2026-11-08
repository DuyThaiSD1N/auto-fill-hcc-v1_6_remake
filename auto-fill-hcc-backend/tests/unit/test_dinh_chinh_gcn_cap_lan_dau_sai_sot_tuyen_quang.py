import asyncio
import base64
import re
from types import SimpleNamespace

import fitz

from app.pipelines._shared import fold
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang import attach
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.attach import planner as dispatcher
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.attach.dinh_kem_khong_tach import planner
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.attach.dinh_kem_khong_tach.prompt import (
    SYSTEM_PROMPT,
)
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.attach.dinh_kem_tach import planner as tach
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.attach.dinh_kem_tach.prompt import (
    SYSTEM_PROMPT as TACH_PROMPT,
)
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.process import mapper
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.process.prompt import EXTRA_RULES
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.process_ilis import mapper as ilis_mapper
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.process_ilis.prompt import (
    EXTRA_RULES as ILIS_RULES,
)
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.process_ilis.schema import (
    ALLOWED as ILIS_ALLOWED,
    FIELDS as ILIS_FIELDS,
    UI_COMP_BY_NAME as ILIS_UI,
)
from app.procedures.ke_khai_links import KE_KHAI_LINKS, procedure_province_slugs
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

_KEY = "dinh-chinh-gcn-cap-lan-dau-sai-sot-tuyen-quang"
_ILIS_KEY = "dinh-chinh-gcn-cap-lan-dau-sai-sot-tuyen-quang-ilis"

_PROOF = (
    "Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận so với thông tin tại thời điểm đề nghị "
    "đính chính hoặc sai sót thông tin về thửa đất, tài sản gắn liền với đất so với thông tin trên Giấy chứng nhận đã cấp"
)
# Cột "Tên giấy tờ" của 8 dòng thành phần hồ sơ trên cổng Tuyên Quang, đúng thứ tự DOM (file mapping, Phần III).
_ROWS = [
    "- Bản gốc Giấy chứng nhận đã cấp;",
    "- " + _PROOF,
    "- Trường hợp người sử dụng đất, chủ sở hữu tài sản gắn liền với đất thực hiện thủ tục thông qua người đại diện "
    "theo quy định của pháp luật về dân sự thì phải có văn bản về việc ủy quyền theo quy định của pháp luật về dân sự",
    "- Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 11/ĐK (bản chính) ban hành kèm theo Nghị "
    "định số 101/2024/NĐ-CP ngày 29 tháng 7 năm 2024 của Chính phủ quy định về điều tra cơ bản đất đai; đăng ký, cấp "
    "Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất và Hệ thống thông tin đất đai;",
    "- Bản gốc Giấy chứng nhận đã cấp.",
    _PROOF + ".",
    "Văn bản về việc ủy quyền theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục thông qua "
    "người đại diện.",
    "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
]


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
    return {item["name"]: item["value"] for item in fields if not item.get("clear")}


def _cleared(fields: list[dict]) -> set[str]:
    """Ô gửi cờ clear: extension xoá trắng giá trị cổng điền sẵn và tô đỏ cho cán bộ nhập tay."""
    cleared = {item["name"] for item in fields if item.get("clear")}
    assert all(item["value"] == "" and item.get("markEmpty") for item in fields if item.get("clear"))
    return cleared


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM (attp-row 8 dòng, danh mục lặp hai lần)
# --------------------------------------------------------------------------------------
def test_sample_bundle_goes_whole_once_to_don_row():
    """Không tách: file scan gộp có Đơn đính NGUYÊN FILE một lần vào dòng 8, không rải sang dòng 1, 2, 5, 6."""
    attachments, warnings, classified = planner.build_plan_items(
        _files(["ho-so.pdf"]), None,
        {0: ["giay_to_chung_minh_sai_sot", "land_certificate", "don_mau_18", "identity"]},
    )
    assert [(item["componentIndex"], item["loaiBan"], item["documentName"]) for item in attachments] == [
        (8, "Bản chính", "ho-so.pdf")]
    assert "sourceSegments" not in attachments[0] and attachments[0]["target"] == "attp-row"
    assert classified[0]["rows"] == [8]
    assert len(warnings) == 1 and "dòng 8" in warnings[0] and "dòng 1, 2" in warnings[0]


def test_untick_rows_without_files_like_bxd():
    """Cổng iGate Tuyên Quang tick sẵn mọi dòng → mọi mục kế hoạch (cả hai chế độ) mang untickUnplannedRows để FE bỏ
    tick hết rồi chỉ tick lại dòng có tệp."""
    attachments, _w, _c = planner.build_plan_items(
        _files(["don.pdf", "gcn.pdf"]), None, {0: ["don_mau_11"], 1: ["land_certificate"]})
    assert attachments and all(item["untickUnplannedRows"] is True for item in attachments)
    assert tach._item(0, "don.pdf", 4, "Đơn", "don_mau_11", None)["untickUnplannedRows"] is True


def test_component_name_resolves_to_its_own_row_on_fe():
    assert sorted(planner._ROWS) == [1, 2, 3, 4, 8]  # dòng 5/6/7 lặp dòng 1/2/3, không đính
    for row, route in planner._ROWS.items():
        assert _fe_find_row(route["name"], row) == row, row
    assert len({_fe_fold(route["name"]) for route in planner._ROWS.values()}) == len(planner._ROWS)
    # Tên dòng 2 cũng khớp chữ dòng 6 (dòng 6 chỉ thêm dấu chấm): chỉ STT giữ file ở dòng 2.
    assert _fe_matches(_ROWS[5], planner._ROWS[2]["name"])


def test_separate_files_go_to_their_own_row():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["don.pdf", "gcn.pdf", "uq.pdf", "cccd.jpg"]), None,
        {0: ["don_mau_11"], 1: ["land_certificate"], 2: ["authorization"], 3: ["identity"]},
    )
    assert [(item["fileIndex"], item["componentIndex"]) for item in attachments] == [(0, 4), (1, 1), (2, 3), (3, 2)]
    assert attachments[0]["documentName"] == "Đơn đăng ký biến động đất đai (Mẫu số 11/ĐK)"
    assert attachments[3]["loaiBan"] == "Bản sao"
    assert warnings == []


def test_proof_with_identity_is_not_a_bundle():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["chung-minh.pdf"]), None, {0: ["identity", "giay_to_chung_minh_sai_sot"]}
    )
    assert [item["componentIndex"] for item in attachments] == [2]
    assert attachments[0]["documentName"] == "Giấy tờ chứng minh sai sót"
    assert warnings == []


def test_bundle_without_don_uses_gcn_row():
    attachments, warnings, _classified = planner.build_plan_items(
        _files(["gcn-cccd.pdf"]), None, {0: ["identity", "land_certificate"]}
    )
    assert [item["componentIndex"] for item in attachments] == [1]
    assert len(warnings) == 1 and "dòng 2" in warnings[0]


def test_unknown_routed_to_don_row_with_original_name():
    attachments, warnings, classified = planner.build_plan_items(_files(["la.pdf", "trong.pdf"]), None, {0: "abc"})
    assert [item["componentIndex"] for item in attachments] == [8, 8]
    assert [item["documentName"] for item in attachments] == ["la.pdf", "trong.pdf"]
    assert len(warnings) == 2
    assert [item["source"] for item in classified] == ["llm", "unknown"]


def test_attach_prompt_lists_every_type():
    for doc_type in list(planner._TYPE_ROW) + ["other"]:
        assert doc_type in SYSTEM_PROMPT
    assert '"docTypes"' in SYSTEM_PROMPT


def test_plan_sends_every_page_of_bundle_to_llm(monkeypatch):
    """PDF gộp nhiều trang: LLM thấy đầu MỌI trang, kể cả Giấy chứng nhận và CCCD nằm cuối file."""
    pages = ["ĐƠN ĐĂNG KÝ BIẾN ĐỘNG " + "x " * 3000, "HỢP ĐỒNG " + "y " * 3000, "GIẤY CHỨNG NHẬN", "CĂN CƯỚC CÔNG DÂN"]
    text = pages[0] + "".join(f"\n───── Trang {n}/4 ─────\n{page}" for n, page in enumerate(pages[1:], start=2))
    sent: list[str] = []

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": text} for item in files]

    async def fake_chat(messages, **kwargs):
        sent.append(messages[1]["content"])
        return '{"documents":[{"index":0,"docTypes":["don_mau_18","land_certificate","identity"]}]}'

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl="x")]

    result = asyncio.run(planner.plan(files))

    assert "GIẤY CHỨNG NHẬN" in sent[0] and "CĂN CƯỚC CÔNG DÂN" in sent[0]
    assert [item["componentIndex"] for item in result["attachments"]] == [8]


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM — CHẾ ĐỘ TÁCH (cài đặt "Có tách hồ sơ khi đính kèm")
# --------------------------------------------------------------------------------------
_PAGE = "Nội dung trang đủ dài để không bị coi là trang trắng của bản scan hồ sơ đính chính. " * 2


def _pdf_data_url(pages: int) -> str:
    with fitz.open() as doc:
        for _ in range(pages):
            doc.new_page()
        return "data:application/pdf;base64," + base64.b64encode(doc.tobytes()).decode()


def test_dispatcher_picks_mode_from_split_setting(monkeypatch):
    calls = []

    async def fake_tach(files, options, session):
        calls.append("tach")
        return {}

    async def fake_khong_tach(files, options, session):
        calls.append("khong_tach")
        return {}

    monkeypatch.setattr(dispatcher, "plan_with_split", fake_tach)
    monkeypatch.setattr(dispatcher, "plan_without_split", fake_khong_tach)
    for options in ({"splitDocuments": True}, {"splitDocuments": "true"}, {}, None,
                    {"splitDocuments": True, "supportsSourceSegments": False}):
        asyncio.run(attach.plan([], options))
    assert calls == ["tach", "khong_tach", "khong_tach", "khong_tach", "khong_tach"]


def test_split_sample_bundle_one_row_per_document_skips_twin_rows():
    """Bộ mẫu 11 trang: mỗi giấy một tệp cắt trang, chỉ dòng 1/2/8 — không đính dòng trùng 5/6."""
    pages = [_PAGE] * 11
    documents = {0: [
        (0, "don_mau_18", "Đơn đăng ký biến động"),
        (1, "giay_to_chung_minh_sai_sot", "Hợp đồng chuyển dịch quyền sở hữu nhà"),
        (5, "land_certificate", "Giấy chứng nhận quyền sở hữu nhà ở"),
        (7, "giay_to_chung_minh_sai_sot", "Giấy khai sinh"),
        (9, "identity", "Căn cước công dân"),
        (10, "giay_to_chung_minh_sai_sot", "Trích lục kết hôn"),
    ]}
    attachments, warnings, segments = tach.build_plan_items(_files(["ho-so.pdf"]), {0: pages}, documents)

    assert [(item["componentIndex"], item["sourceSegments"][0]["pageIndexes"]) for item in attachments] == [
        (8, [0]), (2, [1, 2, 3, 4]), (1, [5, 6]), (2, [7, 8]), (2, [9]), (2, [10])]
    assert not {item["componentIndex"] for item in attachments} & {5, 6, 7}
    assert {item["componentIndex"]: item["loaiBan"] for item in attachments} == {
        8: "Bản chính", 2: "Bản sao", 1: "Bản chính"}
    assert attachments[1]["documentName"] == "Hợp đồng chuyển dịch quyền sở hữu nhà"
    assert warnings == []
    assert segments[2]["pages"] == [6, 7]


def test_split_drops_blank_pages_and_numbers_same_names():
    pages = [_PAGE, "Qwen", _PAGE, _PAGE]
    documents = {0: [(0, "identity", "Căn cước công dân"), (2, "identity", "Căn cước công dân"),
                     (3, "authorization", "")]}
    attachments, _warnings, _segments = tach.build_plan_items(_files(["cccd.pdf"]), {0: pages}, documents)

    assert [item["sourceSegments"][0]["pageIndexes"] for item in attachments] == [[0], [2], [3]]
    assert [item["documentName"] for item in attachments] == [
        "Căn cước công dân", "Căn cước công dân 2", "Văn bản ủy quyền"]
    assert attachments[2]["componentIndex"] == 3


def test_split_single_document_file_is_attached_whole():
    attachments, warnings, _segments = tach.build_plan_items(
        _files(["gcn.pdf", "cccd.jpg"]), {0: [_PAGE, _PAGE], 1: [_PAGE]},
        {0: [(0, "land_certificate", "")], 1: [(0, "identity", "Căn cước công dân")]},
    )
    assert [(item["componentIndex"], "sourceSegments" in item) for item in attachments] == [(1, False), (2, False)]
    assert attachments[0]["documentName"] == "Bản gốc Giấy chứng nhận đã cấp"
    assert warnings == []


def test_split_unsplittable_bundle_goes_whole_once_like_no_split():
    attachments, warnings, _segments = tach.build_plan_items(
        _files(["gop.pdf"]), {0: ["trích đoạn"]},
        {0: [(0, "land_certificate", "GCN"), (0, "don_mau_18", "Đơn"), (0, "identity", "CCCD")]},
    )
    assert [(item["componentIndex"], item["documentName"]) for item in attachments] == [(8, "gop.pdf")]
    assert "sourceSegments" not in attachments[0]
    assert len(warnings) == 1 and "dòng 8" in warnings[0] and "dòng 1, 2" in warnings[0]


def test_split_single_page_file_keeps_llm_name():
    attachments, _warnings, _segments = tach.build_plan_items(
        _files(["anh.jpg"]), {0: [_PAGE]}, {0: [(0, "identity", "Căn cước công dân")]},
    )
    assert [(item["componentIndex"], item["documentName"]) for item in attachments] == [(2, "Căn cước công dân")]


def test_split_unknown_and_missing_text_go_to_don_row_with_warning():
    attachments, warnings, _segments = tach.build_plan_items(
        _files(["a.pdf", "b.pdf"]), {0: [_PAGE, _PAGE]}, {0: [(0, "land_certificate", ""), (1, "other", "")]},
    )
    assert [(item["fileIndex"], item["componentIndex"]) for item in attachments] == [(0, 1), (0, 8), (1, 8)]
    assert [item["documentName"] for item in attachments[1:]] == ["a.pdf", "b.pdf"]
    assert len(warnings) == 2 and "a.pdf, trang 2" in warnings[0]


def test_split_parse_documents_keeps_pages_in_file():
    parsed = tach.parse_documents(
        {"tep": [{"fileIndex": 0, "giayTo": [{"trangDau": 3, "docType": "identity", "ten": "CCCD/thẻ"},
                                             {"trangDau": 1, "docType": "Don_Mau_18"},
                                             {"trangDau": 9, "docType": "identity"}]},
                 {"fileIndex": 5, "giayTo": [{"trangDau": 1, "docType": "identity"}]}]},
        {0: 4},
    )
    assert parsed == {0: [(0, "don_mau_18", ""), (2, "identity", "CCCD-thẻ")]}


def test_split_plan_cuts_real_pdf_pages(monkeypatch):
    from app.services import ocr

    text = "\n".join(f"───── Trang {n}/3 ─────\n{_PAGE}" for n in range(1, 4))

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": text} for item in files]

    async def fake_chat(messages, **kwargs):
        assert '"soTrang": 3' in messages[1]["content"]
        return ('{"tep":[{"fileIndex":0,"giayTo":[{"trangDau":1,"docType":"don_mau_18","ten":"Đơn"},'
                '{"trangDau":2,"docType":"land_certificate","ten":"Giấy chứng nhận"}]}]}')

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tach.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl=_pdf_data_url(3))]

    result = asyncio.run(attach.plan(files, {"splitDocuments": True}))

    assert [(item["componentIndex"], item["sourceSegments"]) for item in result["attachments"]] == [
        (8, [{"fileIndex": 0, "pageIndexes": [0]}]), (1, [{"fileIndex": 0, "pageIndexes": [1, 2]}])]


def test_split_falls_back_to_no_split_mode(monkeypatch):
    from app.services import ocr

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def broken_segment(units):
        raise ValueError("JSON hỏng")

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["don_mau_18","land_certificate","identity","authorization"]}]}'

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(tach, "_segment", broken_segment)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl="x")]

    result = asyncio.run(attach.plan(files, {"splitDocuments": True}))

    assert [item["componentIndex"] for item in result["attachments"]] == [8]
    assert result["errors"][0].startswith("Tách giấy tờ: JSON hỏng")
    assert "dòng 1, 2, 3" in result["errors"][-1]


def test_split_prompt_lists_every_type():
    for doc_type in list(planner._TYPE_ROW) + ["other"]:
        assert doc_type in TACH_PROMPT
    assert '"giayTo"' in TACH_PROMPT and '"trangDau"' in TACH_PROMPT


# --------------------------------------------------------------------------------------
# ĐIỀN (Form.io bước 1: Phần I người nộp/chủ hồ sơ, Phần II người ủy quyền)
# --------------------------------------------------------------------------------------
_OWNER = dict(
    ChuHoSo_HoTen="LÊ THỊ HOA",
    ChuHoSo_NgaySinh="5/3/1962",
    ChuHoSo_GioiTinh="Nữ",
    ChuHoSo_SoDinhDanh="048 162 012 345",
    ChuHoSo_NgayCap="15/03/2021",
    ChuHoSo_NoiCap="Cục trưởng Cục Cảnh sát quản lý hành chính về trật tự xã hội",
    ChuHoSo_NoiCuTru={"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Thạch Thang", "chiTietDuoiXa": "K15/2 Lê Lợi"},
    ChuHoSo_DienThoai="0905.123.456",
    Don_NoiDungBienDong="Đính chính tên bà Lê Thị Hòe thành bà Lê Thị Hoa",
)


def test_self_submit_fills_part_one_from_owner():
    fields, warnings = mapper.enrich(_facts(**_OWNER))
    values = _values(fields)

    assert values["data[fullname]"] == "LÊ THỊ HOA"
    assert values["data[identityNumber]"] == "048162012345"
    assert values["data[gender]"] == "Nữ"
    assert values["data[birthday]"] == "05/03/1962"
    assert values["data[identityDate]"] == "15/03/2021"
    assert values["data[identityAgency]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    # Phường cũ đổi sang đơn vị sau sắp xếp để khớp danh sách Phường/Xã của cổng.
    assert (values["data[province]"], values["data[district]"], values["data[address]"]) == (
        "Thành phố Đà Nẵng", "Phường Hải Châu", "K15/2 Lê Lợi")
    assert values["data[phoneNumber]"] == "0905123456"
    assert values["data[textField]"] == "Đính chính tên bà Lê Thị Hòe thành bà Lê Thị Hoa"
    assert values["data[tenHoSo]"] == "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót"
    assert values["data[hinhThucNop]"] == "Trực tuyến"
    defaults = {item["name"] for item in fields if item.get("default")}
    assert defaults == {"data[nation]", "data[hinhThucNop]", "data[tenHoSo]"}
    assert not {"data[Hovaten]", "data[Sogiaytotuythan]", "data[sodienthoai]", "data[diachi]"} & set(values)
    assert warnings == []


def test_authorized_submitter_fills_part_one_and_owner_goes_to_part_two():
    fields, _warnings = mapper.enrich(_facts(
        **_OWNER,
        NguoiNop_HoTen="Trần Văn Bình",
        NguoiNop_GioiTinh="Nam",
        NguoiNop_SoDinhDanh="008 090 012 345",
        NguoiNop_NoiCuTru={"tinh": "Tuyên Quang", "xa": "Phường Minh Xuân", "chiTietDuoiXa": "Tổ 5"},
    ))
    values = _values(fields)

    assert values["data[fullname]"] == "Trần Văn Bình"
    assert values["data[identityNumber]"] == "008090012345"
    assert values["data[gender]"] == "Nam"
    assert (values["data[province]"], values["data[district]"], values["data[address]"]) == (
        "Tỉnh Tuyên Quang", "Phường Minh Xuân", "Tổ 5")
    # Số điện thoại trên Đơn là của chủ hồ sơ: không gán cho người được ủy quyền → xoá trắng ô cổng điền sẵn.
    assert "data[phoneNumber]" not in values
    assert {"data[phoneNumber]", "data[birthday]", "data[identityDate]", "data[identityAgency]"} <= _cleared(fields)
    assert values["data[Hovaten]"] == "LÊ THỊ HOA"
    assert values["data[Sogiaytotuythan]"] == "048162012345"
    assert values["data[sodienthoai]"] == "0905123456"
    assert values["data[diachi]"] == "K15/2 Lê Lợi, Phường Hải Châu, Thành phố Đà Nẵng"


def test_same_person_as_submitter_is_not_authorization():
    fields, _warnings = mapper.enrich(_facts(**_OWNER, NguoiNop_HoTen="Lê Thị Hoa"))
    values = _values(fields)
    assert values["data[fullname]"] == "LÊ THỊ HOA"
    assert "data[Hovaten]" not in values


def test_missing_personal_fields_are_cleared_instead_of_keeping_account_values():
    """Không có ngày sinh (chỉ có năm), giới tính, địa chỉ… → xoá trắng ô cổng đổ sẵn theo tài khoản, tô đỏ."""
    fields, warnings = mapper.enrich(_facts(ChuHoSo_HoTen="LÊ THỊ HOA", ChuHoSo_NgaySinh="1962"))
    assert set(_values(fields)) == {"data[fullname]", "data[nation]", "data[hinhThucNop]", "data[tenHoSo]"}
    assert _cleared(fields) == {
        "data[identityNumber]", "data[gender]", "data[birthday]", "data[identityDate]", "data[identityAgency]",
        "data[province]", "data[district]", "data[address]", "data[phoneNumber]", "data[email]"}
    # Phần II (người ủy quyền) chỉ có khi nộp thay: không xoá, không tô đỏ.
    assert not {"data[Hovaten]", "data[Sogiaytotuythan]"} & _cleared(fields)
    assert len(warnings) == 1 and "đã xoá" in warnings[0]
    assert "Giới tính" in warnings[0] and "Ngày sinh" in warnings[0] and "Tỉnh/TP" in warnings[0]


def test_schema_skips_organisation_fields_and_prompt_covers_traps():
    assert "data[fullname1]" not in UI_COMP_BY_NAME and "data[agency1]" not in UI_COMP_BY_NAME
    assert {"ChuHoSo_HoTen", "NguoiNop_HoTen", "Don_NoiDungBienDong"} <= ALLOWED
    assert "Người viết đơn" in EXTRA_RULES and "BỊ SAI" in EXTRA_RULES and "CMND 9 chữ số" in EXTRA_RULES


# --------------------------------------------------------------------------------------
# ĐIỀN FORM 2 — quy trình "iLis cấp xã" (người nộp / thửa đất / chủ hồ sơ / thông tin chi tiết)
# --------------------------------------------------------------------------------------
_ILIS_OWNER = {key: value for key, value in _OWNER.items() if key != "ChuHoSo_DienThoai"}
_ILIS_APPLICANT = dict(
    NguoiNop_HoTen="TRẦN VĂN BÌNH",
    NguoiNop_NgaySinh="10/3/1960",
    NguoiNop_GioiTinh="Nam",
    NguoiNop_SoDinhDanh="048060012345",
    # Ngày/nơi cấp của CMND 9 số cũ trong hợp đồng, LLM ghép nhầm vào số 12 chữ số trên Đơn.
    NguoiNop_NgayCap="14/12/1993",
    NguoiNop_NoiCap="UBND Quận Hải Châu",
    NguoiNop_DienThoai="0905.111.222",
    NguoiNop_NoiCuTru={"tinh": "Đà Nẵng", "xa": "Thạch Thang", "chiTietDuoiXa": "K15/2 Lê Lợi"},
)
_ILIS_PARCEL = dict(
    ThuaDat_DiaChi={"tinh": "Đà Nẵng", "xa": "Thạch Thang", "chiTietDuoiXa": "K15/2 Lê Lợi"},
    GCN_So="3401012345",
    GCN_NgayCap="9/6/2011",
    GCN_DonViCap="Ủy ban nhân dân Thành phố Đà Nẵng",
    GCN_NoiCap="Đà Nẵng",
)


def test_ilis_two_people_fill_applicant_and_owner_blocks_separately():
    fields, warnings = ilis_mapper.enrich(_facts(**_ILIS_OWNER, **_ILIS_APPLICANT, **_ILIS_PARCEL))
    values = _values(fields)

    # Phần I — người nộp (người kê khai đầu tiên trên Đơn)
    assert values["data[fullname]"] == "TRẦN VĂN BÌNH"
    assert values["data[birthday]"] == "10/03/1960"
    assert values["data[gender]"] == "Nam"
    assert values["data[identityNumber]"] == "048060012345"
    assert values["data[phoneNumber]"] == "0905111222"
    assert (values["data[province]"], values["data[village]"], values["data[address]"]) == (
        "Thành phố Đà Nẵng", "Phường Hải Châu", "K15/2 Lê Lợi")
    assert values["data[ghiChu]"] == "Đính chính tên bà Lê Thị Hòe thành bà Lê Thị Hoa"
    # Số chỉ có trên Đơn: không ngày/nơi cấp, không mượn của chủ hồ sơ.
    assert "data[identityDate]" not in values and "data[identityAgency]" not in values
    assert {"data[identityDate]", "data[identityAgency]", "data[email]"} <= _cleared(fields)
    # Phần II — thửa đất
    assert (values["data[province2]"], values["data[village2]"]) == ("Thành phố Đà Nẵng", "Phường Hải Châu")
    # Phần III — chủ hồ sơ
    assert values["data[ownerFullname]"] == "LÊ THỊ HOA"
    assert values["data[gender1]"] == "Nữ"
    assert values["data[ownerBirthday]"] == "05/03/1962"
    assert values["data[ownerIdentityNumber]"] == "048162012345"
    assert values["data[ownerIdentityDate]"] == "15/03/2021"
    assert values["data[ownerIdentityAgency]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert (values["data[province1]"], values["data[village1]"], values["data[ownerAddress]"]) == (
        "Thành phố Đà Nẵng", "Phường Hải Châu", "K15/2 Lê Lợi")
    assert "data[ownerPhoneNumber]" not in values
    assert {"data[ownerPhoneNumber]", "data[ownerEmail]"} <= _cleared(fields)
    assert not {"data[licenseCode]", "data[nation1]"} & _cleared(fields)
    # Phần IV — Giấy chứng nhận đang đính chính
    assert (values["data[licenseCode]"], values["data[licenseDate]"]) == ("3401012345", "09/06/2011")
    assert values["data[licensingPlace]"] == "Ủy ban nhân dân Thành phố Đà Nẵng"
    assert values["data[licensingAgency]"] == "Thành phố Đà Nẵng"
    assert {item["name"] for item in fields if item.get("default")} == {"data[nation]", "data[nation1]"}
    assert len(warnings) == 1 and "Nơi cấp CMND/CCCD người nộp" in warnings[0]
    assert "Ngày sinh" not in warnings[0] and "thửa đất" not in warnings[0]


def test_ilis_single_person_fills_both_blocks_from_owner():
    fields, warnings = ilis_mapper.enrich(_facts(**_OWNER, **_ILIS_PARCEL))
    values = _values(fields)
    for applicant, owner in (("data[fullname]", "data[ownerFullname]"), ("data[birthday]", "data[ownerBirthday]"),
                             ("data[identityAgency]", "data[ownerIdentityAgency]"),
                             ("data[phoneNumber]", "data[ownerPhoneNumber]"), ("data[village]", "data[village1]")):
        assert values[applicant] == values[owner], applicant
    assert warnings == []


def test_ilis_different_people_never_borrow_attributes():
    applicant = {key: value for key, value in _ILIS_APPLICANT.items() if key != "NguoiNop_NgaySinh"}
    fields, warnings = ilis_mapper.enrich(_facts(**_ILIS_OWNER, **applicant))
    values = _values(fields)
    assert "data[birthday]" not in values and values["data[ownerBirthday]"] == "05/03/1962"
    assert "Ngày sinh người nộp" in warnings[0] and "thửa đất" in warnings[0]


def test_ilis_license_place_gets_full_province_label_only_for_province_names():
    assert ilis_mapper._place("Đà Nẵng") == ilis_mapper._place("TP. Đà Nẵng") == "Thành phố Đà Nẵng"
    assert ilis_mapper._place("Tuyên Quang") == "Tỉnh Tuyên Quang"
    assert ilis_mapper._place("Huyện Yên Sơn, Tuyên Quang") == "Huyện Yên Sơn, Tuyên Quang"


def test_issue_date_and_issuer_must_fit_the_identity_number():
    from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.process.mapper import _id_issued

    # Số 12 chữ số chỉ có từ 2012: ngày cấp 1993 là của CMND cũ → bỏ cả ngày lẫn nơi cấp.
    assert _id_issued("048060012345", "14/12/1993", "Công an tỉnh Quảng Nam") == (None, None)
    assert _id_issued("200080392", "14/12/1993", "CA tỉnh Quảng Nam")[0] == "14/12/1993"
    # Nơi cấp giấy tờ tùy thân phải là cơ quan công an.
    assert _id_issued("048162012345", "15/03/2021", "UBND Quận Hải Châu") == ("15/03/2021", None)
    assert _id_issued("048162012345", "15/03/2021", "Bộ Công an") == ("15/03/2021", "Bộ Công an")
    assert _id_issued("048162012345", "15/03/2021", "Cục trưởng Cục Cảnh sát quản lý hành chính về trật tự xã hội")[1] \
        == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


def test_ilis_schema_and_prompt():
    assert not {"data[organization]", "data[BUTTON3]", "data[effectiveDate]", "data[expirationDate]"} & set(ILIS_UI)
    assert {"ThuaDat_DiaChi", "GCN_So", "GCN_NgayCap", "NguoiNop_HoTen", "ChuHoSo_NoiCuTru"} <= ILIS_ALLOWED
    descs = {field["name"]: field["desc"] for field in ILIS_FIELDS}
    assert "KHÔNG lấy số ở dòng của người đồng sử dụng" in descs["ChuHoSo_DienThoai"]
    assert "ĐẦU TIÊN" in descs["NguoiNop_HoTen"]
    assert "Người viết đơn" in ILIS_RULES and "BỊ SAI" in ILIS_RULES


# --------------------------------------------------------------------------------------
# REGISTRY + LINK KÊ KHAI
# --------------------------------------------------------------------------------------
def test_registry_wires_both_pipelines_and_locks_tuyen_quang():
    procedure = get_procedure(_KEY)
    assert procedure["label"] == "Tuyên Quang - Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót"
    assert procedure["detect"]["urlScope"] == ["tuyenquang.gov.vn"]
    assert procedure["supportsSplitDocuments"] is True
    assert procedure_province_slugs(procedure) == ["tuyenquang"]
    module = "app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang."
    assert get_pipeline(_KEY).__module__.startswith(module)
    assert get_attach_pipeline(_KEY).__module__.startswith(module)


def _detect(url: str, body: str) -> str:
    """Như bước 0 của detectProcedureKeyFromSignals (popup.js): entry textPriority đúng cổng, đủ mọi cụm, tổng dài nhất."""
    text = fold(body)
    best, best_score = "", 0
    for procedure in PROCEDURES:
        detect = procedure.get("detect") or {}
        if not detect.get("textPriority") or detect.get("detectDisabled"):
            continue
        if detect.get("urlScope") and not any(scope.lower() in url for scope in detect["urlScope"]):
            continue
        phrases = [fold(phrase) for phrase in detect.get("textIncludes") or []]
        if phrases and all(phrase in text for phrase in phrases) and sum(map(len, phrases)) > best_score:
            best, best_score = procedure["key"], sum(map(len, phrases))
    return best


def test_ilis_page_detected_as_form_2_and_normal_page_as_form_1():
    url = "https://dichvucong.tuyenquang.gov.vn/vi/padsvc/apply-online/abc"
    title = "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót"
    assert _detect(url, f"{title} - iLis cấp xã - 8 ngày Họ tên Ngày sinh") == _ILIS_KEY
    assert _detect(url, f"{title} - Quy trình giải quyết TTHC 5 Bước Họ và tên:") == _KEY
    assert _detect("https://dichvucong.quangngai.gov.vn/x", f"{title} iLis") != _ILIS_KEY


def test_registry_wires_ilis_form_to_its_own_fill_and_shared_attach():
    procedure = get_procedure(_ILIS_KEY)
    assert procedure["label"].startswith("Tuyên Quang - Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót")
    assert procedure["detect"]["urlScope"] == ["tuyenquang.gov.vn"]
    assert procedure["supportsSplitDocuments"] is True
    assert procedure_province_slugs(procedure) == ["tuyenquang"]
    assert get_pipeline(_ILIS_KEY).__module__.startswith(
        "app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_tuyen_quang.process_ilis.")
    assert get_attach_pipeline(_ILIS_KEY) is get_attach_pipeline(_KEY)
    # Cùng thủ tục: popup đổi từ form gốc (link kê khai) sang form iLis mà không xoá giấy tờ.
    assert procedure["formVariantOf"] == _KEY and "formVariantOf" not in get_procedure(_KEY)


def test_ke_khai_link_shares_registry_key():
    links = [link for link in KE_KHAI_LINKS if link["key"] == _KEY]
    assert len(links) == 1
    assert links[0]["code"] == "1.012796"
    assert links[0]["label"] == get_procedure(_KEY)["label"]


def test_quy_trinh_ilis_option_runs_form_2(monkeypatch):
    """Trợ lý: công dân chọn quy trình iLis ở hộp thoại "Chọn trường hợp giải quyết" → options.quyTrinh → key gốc điền
    form 2; không có khóa này (Auto Fill) thì vẫn form 1."""
    from app.pipelines._shared.compact_agent import runner

    async def fake_run(files_by_role, **kwargs):
        return {"fields": _facts(ChuHoSo_HoTen="Trần Thị Bình", ThuaDat_DiaChi={"tinh": "Tuyên Quang",
                                                                              "xa": "Xã Thượng Lâm"}), "errors": []}

    monkeypatch.setattr(runner, "run", fake_run)
    form1 = asyncio.run(get_pipeline(_KEY)({"": []}, {}))
    form2 = asyncio.run(get_pipeline(_KEY)({"": []}, {"quyTrinh": "ilis"}))
    assert "data[fullname]" in _values(form1["fields"]) and "data[ownerFullname]" not in _values(form1["fields"])
    assert _values(form2["fields"])["data[ownerFullname]"] == "Trần Thị Bình"
    assert _values(form2["fields"]) == _values(asyncio.run(get_pipeline(_ILIS_KEY)({"": []}, {}))["fields"])
    # Quy trình form 1 không dùng khóa của thủ tục khác.
    assert _values(asyncio.run(get_pipeline(_KEY)({"": []}, {"quyTrinh": "vbdlis"}))["fields"]) == _values(form1["fields"])


def test_tro_ly_chi_tai_khoan_tuyen_quang_va_hop_thoai_chon_quy_trinh():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(_KEY)
    core = get_procedure(_KEY)
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert "Tuyên Quang - " + procedure["label"] == core["label"]
    assert procedure["detect"] == core["detect"] and procedure["keKhaiUrl"] == link["url"]
    assert handfree.procedure_code(procedure) == "1.012796"
    assert handfree.is_allowed_in_province(procedure, "tuyenquang")
    assert not handfree.is_allowed_in_province(procedure, "laichau")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert PROCEDURE_HMONG[_KEY]
    for label, options in (("Quy trình 5 bước", {}), ("iLis cấp xã", {"quyTrinh": "ilis"})):
        conv = {"mae_dialog_options": {"process": {"options": [label], "current": label}}}
        assert handfree.case_pipeline_options(procedure, conv) == options, label
