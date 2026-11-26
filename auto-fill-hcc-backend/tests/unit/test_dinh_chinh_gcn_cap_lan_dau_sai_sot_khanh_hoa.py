import asyncio
import base64
import re
from types import SimpleNamespace

import fitz

from app.pipelines._shared import fold
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_khanh_hoa import attach
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_khanh_hoa.attach import planner as dispatcher
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_khanh_hoa.attach.dinh_kem_khong_tach import planner
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_khanh_hoa.attach.dinh_kem_khong_tach.prompt import (
    SYSTEM_PROMPT,
)
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_khanh_hoa.attach.dinh_kem_tach import planner as tach
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_khanh_hoa.attach.dinh_kem_tach.prompt import (
    SYSTEM_PROMPT as SPLIT_PROMPT,
)
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_khanh_hoa.process import mapper, runner
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_khanh_hoa.process.prompt import EXTRA_RULES
from app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_khanh_hoa.process.schema import ALLOWED, FIELDS
from app.procedures.ke_khai_links import KE_KHAI_LINKS, procedure_province_slugs
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline, get_procedure

_KEY = "dinh-chinh-gcn-cap-lan-dau-sai-sot-khanh-hoa"

# Cột "Tên giấy tờ" của 4 dòng thành phần hồ sơ trên cổng Khánh Hòa (quy trình 1.012796-01), đúng thứ tự DOM.
_ROWS = [
    "Bản gốc Giấy chứng nhận đã cấp.",
    "Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận so với thông tin tại thời điểm đề nghị "
    "đính chính hoặc sai sót thông tin về thửa đất, tài sản gắn liền với đất so với thông tin trên Giấy chứng nhận đã "
    "cấp.",
    "Văn bản về việc ủy quyền theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục thông qua "
    "người đại diện.",
    "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18",
]
_PAGE_TITLE = (
    "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót. UBND phường Bắc Cam Ranh. DVCTT Một phần. Quy trình: "
    "1.012796-01 - (Cấp Xã) Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót - Đối với trường hợp còn lại."
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


def _rows(attachments: list[dict]) -> list[tuple[int, int]]:
    return [(item["fileIndex"], item["componentIndex"]) for item in attachments]


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM KHÔNG TÁCH (attp-row 4 dòng)
# --------------------------------------------------------------------------------------
_SAMPLE_FILES = ["giay-chung-nhan.pdf", "khai-sinh.pdf", "khai-sinh-ban-sao.pdf", "don.pdf", "cccd.pdf",
                 "cccd-ban-sao.pdf"]
_SAMPLE_TYPES = {0: ["gcn"], 1: ["bang_chung"], 2: ["bang_chung"], 3: ["don_bien_dong"], 4: ["identity"],
                 5: ["identity"]}


def test_sample_bundle_routes_like_attachment_mapping():
    """Ảnh ánh xạ: GCN + giấy khai sinh (2 bản) -> dòng 2; Đơn + CCCD (2 bản) -> dòng 4; dòng 1 và 3 không đính."""
    attachments, warnings, classified = planner.build_plan_items(_files(_SAMPLE_FILES), llm_types=_SAMPLE_TYPES)

    assert _rows(attachments) == [(0, 2), (1, 2), (2, 2), (3, 4), (4, 4), (5, 4)]
    assert {item["componentIndex"] for item in attachments}.isdisjoint({1, 3})
    assert all(item["loaiBan"] == "Bản chính" and item["target"] == "attp-row" for item in attachments)
    # Cổng tick sẵn 4 dòng → FE bỏ tích hết, tích lại dòng có tệp (dòng 1 bản gốc + dòng 3 ủy quyền còn trống).
    assert all(item["untickUnplannedRows"] is True for item in attachments)
    assert [item["documentName"] for item in attachments] == [
        "Giấy chứng nhận đã cấp", "Giấy tờ chứng minh sai sót thông tin", "Giấy tờ chứng minh sai sót thông tin",
        "Đơn đăng ký biến động đất đai (Mẫu số 18)", "Căn cước công dân", "Căn cước công dân"]
    assert warnings == []
    assert classified[3]["rows"] == [4]


def test_component_names_resolve_to_their_own_rows_on_fe():
    attachments, _, _ = planner.build_plan_items(
        _files(["gcn.pdf", "uq.pdf", "don.pdf"]), llm_types={0: ["gcn"], 1: ["authorization"], 2: ["don_bien_dong"]})
    for item in attachments:
        assert _fe_find_row(item["componentName"], item["componentIndex"]) == item["componentIndex"], item
        assert _fe_find_row(item["componentName"]) == item["componentIndex"], item
    # Cổng có thể in STT "(n) " trước tên: vẫn khớp chuỗi con.
    assert _fe_matches("(4) " + _ROWS[3], attachments[2]["componentName"])


def test_authorization_goes_to_row_three():
    attachments, warnings, _ = planner.build_plan_items(
        _files(["gcn.pdf", "uq.pdf", "don.pdf"]), llm_types={0: ["gcn"], 1: ["authorization"], 2: ["don_bien_dong"]})
    assert _rows(attachments) == [(0, 2), (1, 3), (2, 4)]
    assert warnings == []


def test_bundle_file_goes_whole_once_to_don_row_and_warns():
    attachments, warnings, _ = planner.build_plan_items(
        _files(["ho-so.pdf"]), llm_types={0: ["gcn", "don_bien_dong", "identity", "bang_chung"]})
    assert _rows(attachments) == [(0, 4)]
    assert attachments[0]["documentName"] == "ho-so.pdf"
    assert len(warnings) == 1 and "dòng 4" in warnings[0] and "dòng 2" in warnings[0]


def test_proof_and_residence_share_row_two_without_bundle_warning():
    attachments, warnings, _ = planner.build_plan_items(
        _files(["gcn.pdf", "chung-minh.pdf", "don.pdf"]),
        llm_types={0: ["gcn", "bang_chung"], 1: ["cu_tru", "bang_chung"], 2: ["don_bien_dong"]})
    assert _rows(attachments) == [(0, 2), (1, 2), (2, 4)]
    assert warnings == []


def test_unknown_routed_to_row_two_with_original_name_and_missing_are_reminded():
    attachments, warnings, classified = planner.build_plan_items(_files(["la.pdf"]), llm_types={0: ["other"]})
    assert _rows(attachments) == [(0, 2)] and attachments[0]["documentName"] == "la.pdf"
    assert any("la.pdf" in w and "dòng 2" in w for w in warnings)
    assert any("Giấy chứng nhận đã cấp" in w for w in warnings)
    assert any("Mẫu số 18" in w for w in warnings)
    assert classified[0]["source"] == "llm"
    assert planner.build_plan_items([], llm_types={}) == ([], [], [])


def test_attach_prompt_lists_every_type():
    for doc_type in ("don_bien_dong", "gcn", "bang_chung", "cu_tru", "identity", "authorization", "other"):
        assert f"- {doc_type}:" in SYSTEM_PROMPT
    assert "Mẫu số 18" in SYSTEM_PROMPT and "GIẤY KHAI SINH" in SYSTEM_PROMPT


def test_plan_parses_llm_doc_type_lists(monkeypatch):
    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["gcn"]},{"index":1,"docType":"don_bien_dong"}]}'

    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name=name, type="application/pdf", dataUrl="x") for name in ("gcn.pdf", "don.pdf")]

    result = asyncio.run(attach.plan(files, {"splitDocuments": False}))

    assert [item["componentIndex"] for item in result["attachments"]] == [2, 4]
    assert result["errors"] == []


# --------------------------------------------------------------------------------------
# ĐÍNH KÈM TÁCH (cài đặt "Có tách hồ sơ khi đính kèm")
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


def test_split_sample_bundle_one_document_per_row_without_losing_pages():
    """Bộ mẫu gộp 13 trang: GCN 4 trang, giấy khai sinh 2 + bản sao 2, Đơn 1, CCCD 2 mặt + bản sao 2 mặt."""
    pages = [_PAGE] * 13
    documents = {0: [
        (0, "gcn", "Giấy chứng nhận quyền sử dụng đất"),
        (4, "bang_chung", "Giấy khai sinh"),
        (6, "bang_chung", "Giấy khai sinh (bản sao)"),
        (8, "don_bien_dong", "Đơn đăng ký biến động"),
        (9, "identity", "Căn cước công dân"),
        (11, "identity", "Căn cước công dân (bản sao)"),
    ]}
    attachments, warnings, segments = tach.build_plan_items(_files(["ho-so.pdf"]), {0: pages}, documents)

    assert [(item["componentIndex"], item["sourceSegments"][0]["pageIndexes"]) for item in attachments] == [
        (2, [0, 1, 2, 3]), (2, [4, 5]), (2, [6, 7]), (4, [8]), (4, [9, 10]), (4, [11, 12])]
    # Không sót trang nào, không trang nào đính hai lần.
    cut = [page for item in attachments for page in item["sourceSegments"][0]["pageIndexes"]]
    assert sorted(cut) == list(range(13))
    assert all(item["untickUnplannedRows"] is True and item["loaiBan"] == "Bản chính" for item in attachments)
    assert warnings == []
    assert segments[0]["pages"] == [1, 2, 3, 4]


def test_split_drops_blank_pages_and_numbers_same_names():
    pages = [_PAGE, "Qwen", _PAGE, _PAGE]
    documents = {0: [(0, "identity", "Căn cước công dân"), (2, "identity", "Căn cước công dân"),
                     (3, "authorization", "")]}
    attachments, _warnings, _segments = tach.build_plan_items(_files(["cccd.pdf"]), {0: pages}, documents)

    assert [item["sourceSegments"][0]["pageIndexes"] for item in attachments] == [[0], [2], [3]]
    assert [item["documentName"] for item in attachments] == [
        "Căn cước công dân", "Căn cước công dân 2", "Văn bản ủy quyền"]
    assert [item["componentIndex"] for item in attachments] == [4, 4, 3]


def test_split_single_document_file_is_attached_whole():
    attachments, _warnings, _segments = tach.build_plan_items(
        _files(["gcn.pdf", "don.jpg"]), {0: [_PAGE, _PAGE], 1: [_PAGE]},
        {0: [(0, "gcn", "")], 1: [(0, "don_bien_dong", "Đơn đăng ký biến động")]},
    )
    assert [(item["componentIndex"], "sourceSegments" in item) for item in attachments] == [(2, False), (4, False)]
    assert attachments[0]["documentName"] == "Giấy chứng nhận đã cấp"


def test_split_unsplittable_bundle_goes_whole_once_like_no_split():
    attachments, warnings, _segments = tach.build_plan_items(
        _files(["gop.pdf"]), {0: ["trích đoạn"]},
        {0: [(0, "gcn", "GCN"), (0, "don_bien_dong", "Đơn"), (0, "identity", "CCCD")]},
    )
    assert [(item["componentIndex"], item["documentName"]) for item in attachments] == [(4, "gop.pdf")]
    assert "sourceSegments" not in attachments[0]
    assert any("dòng 4" in w and "dòng 2" in w for w in warnings)


def test_split_unknown_pages_go_to_row_two_with_warning():
    attachments, warnings, _segments = tach.build_plan_items(
        _files(["a.pdf", "b.pdf"]), {0: [_PAGE, _PAGE]}, {0: [(0, "don_bien_dong", ""), (1, "other", "")]},
    )
    assert [(item["fileIndex"], item["componentIndex"]) for item in attachments] == [(0, 4), (0, 2), (1, 2)]
    assert [item["documentName"] for item in attachments[1:]] == ["a.pdf", "b.pdf"]
    assert any("a.pdf, trang 2" in w for w in warnings)
    assert any("Giấy chứng nhận đã cấp" in w for w in warnings)  # thiếu GCN vẫn nhắc


def test_split_parse_documents_keeps_pages_in_file():
    parsed = tach.parse_documents(
        {"tep": [{"fileIndex": 0, "giayTo": [{"trangDau": 3, "docType": "identity", "ten": "CCCD/thẻ"},
                                             {"trangDau": 1, "docType": "Don_Bien_Dong"},
                                             {"trangDau": 9, "docType": "identity"}]},
                 {"fileIndex": 5, "giayTo": [{"trangDau": 1, "docType": "identity"}]}]},
        {0: 4},
    )
    assert parsed == {0: [(0, "don_bien_dong", ""), (2, "identity", "CCCD-thẻ")]}


def test_split_plan_cuts_real_pdf_pages(monkeypatch):
    from app.services import ocr

    text = "\n".join(f"───── Trang {n}/3 ─────\n{_PAGE}" for n in range(1, 4))

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": text} for item in files]

    async def fake_chat(messages, **kwargs):
        assert '"soTrang": 3' in messages[1]["content"]
        return ('{"tep":[{"fileIndex":0,"giayTo":[{"trangDau":1,"docType":"don_bien_dong","ten":"Đơn"},'
                '{"trangDau":2,"docType":"identity","ten":"Căn cước công dân"}]}]}')

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tach.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl=_pdf_data_url(3))]

    result = asyncio.run(attach.plan(files, {"splitDocuments": True}))

    assert [(item["componentIndex"], item["sourceSegments"]) for item in result["attachments"]] == [
        (4, [{"fileIndex": 0, "pageIndexes": [0]}]), (4, [{"fileIndex": 0, "pageIndexes": [1, 2]}])]


def test_split_falls_back_to_no_split_mode(monkeypatch):
    from app.services import ocr

    async def fake_ocr(files):
        return [{"name": item["name"], "type": item["type"], "text": "ocr"} for item in files]

    async def broken_segment(units):
        raise ValueError("JSON hỏng")

    async def fake_chat(messages, **kwargs):
        return '{"documents":[{"index":0,"docTypes":["don_bien_dong","gcn","identity"]}]}'

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner, "_ocr_for_classify", fake_ocr)
    monkeypatch.setattr(tach, "_segment", broken_segment)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [SimpleNamespace(name="ho-so.pdf", type="application/pdf", dataUrl="x")]

    result = asyncio.run(attach.plan(files, {"splitDocuments": True}))

    assert [item["componentIndex"] for item in result["attachments"]] == [4]
    assert "sourceSegments" not in result["attachments"][0]
    assert result["errors"][0].startswith("Tách giấy tờ: JSON hỏng")


def test_split_prompt_lists_every_type():
    for doc_type in ("don_bien_dong", "gcn", "bang_chung", "cu_tru", "identity", "authorization", "other"):
        assert f"- {doc_type}:" in SPLIT_PROMPT
    assert "Mặt trước + mặt sau CCCD" in SPLIT_PROMPT


# --------------------------------------------------------------------------------------
# ĐIỀN (Form.io ba khối, cùng template đính chính 1.012790 Khánh Hòa)
# --------------------------------------------------------------------------------------
_REQUEST = ("Xin điều chỉnh năm sinh trên giấy chứng nhận quyền sử dụng đất từ 1970 sang 1971 để phù hợp với giấy khai "
            "sinh và định danh điện tử.")
_OWNER = dict(
    ChuHoSo_HoTen="Trần Văn Bình",
    ChuHoSo_NgaySinh="05/3/1971",
    ChuHoSo_SoDinhDanh="056 071 001 234",
    ChuHoSo_NgayCap="20/6/2023",
    ChuHoSo_NoiCap="CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    ChuHoSo_DienThoai="0905.222.333",
    ChuHoSo_DiaChi={"tinh": "Khánh Hòa", "xa": "Phường Bắc Cam Ranh", "chiTietDuoiXa": "Số 12 đường A"},
    Don_NoiDungBienDong=_REQUEST,
    GCN_NguoiSuDung="Ông Trần Văn Bình",
)
_PARCEL = dict(
    ThuaDat_DiaChi={"tinh": "Khánh Hòa", "xa": "Phường Bắc Cam Ranh", "chiTietDuoiXa": "Số 12 đường A"},
    ThuaDat_DiaChiDayDu="Số 12 đường A, Phường 3, thị xã Cam Ranh",
    ThuaDat_SoThua="17",
    ThuaDat_SoTo="09",
)


def test_self_submit_fills_all_three_blocks():
    fields, warnings = mapper.enrich(_facts(**_OWNER, NguoiNop_HoTen="TRẦN VĂN BÌNH", **_PARCEL))
    values = _values(fields)

    assert values["data[fullname]"] == values["data[ownerFullname]"] == "Trần Văn Bình"
    assert values["data[birthday]"] == values["data[ownerBirthday]"] == "05/03/1971"
    assert values["data[identityNumber]"] == values["data[ownerIdentityNumber]"] == "056071001234"
    assert values["data[identityDate]"] == values["data[ownerIdentityDate]"] == "20/06/2023"
    assert values["data[identityAgency_text]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[phoneNumber]"] == values["data[ownerPhoneNumber]"] == "0905222333"
    assert (values["data[province1]"], values["data[village1]"], values["data[ownerAddress]"]) == (
        "Tỉnh Khánh Hòa", "Phường Bắc Cam Ranh", "Số 12 đường A")
    assert values["data[noidungyeucaugiaiquyet]"] == _REQUEST
    assert values["data[diaChiThuaDat]"] == "Số 12 đường A, Phường 3, thị xã Cam Ranh"
    assert (values["data[SoThuaDat]"], values["data[SoToBanDo]"]) == ("17", "09")
    assert (values["data[province2]"], values["data[village2]"]) == ("Tỉnh Khánh Hòa", "Phường Bắc Cam Ranh")
    assert values["data[chonDoiTuong]"] == "Cá nhân"
    assert not any("cùng một hồ sơ" in w or "cùng ký" in w for w in warnings)


def test_gcn_with_spouse_but_don_lists_one_person_is_reminded():
    """GCN đứng tên hai vợ chồng, Đơn chỉ kê khai người có năm sinh sai → nhắc cán bộ, không coi là lệch hồ sơ."""
    both = dict(_OWNER, GCN_NguoiSuDung="Bà Lê Thị Hoa và Ông Trần Văn Bình")
    _, warnings = mapper.enrich(_facts(**both, **_PARCEL))
    assert not any("cùng một hồ sơ" in w for w in warnings)
    (reminder,) = [w for w in warnings if "cùng ký" in w]
    assert "Lê Thị Hoa" in reminder and "Trần Văn Bình" in reminder

    # Đơn kê khai cả người kia (người cùng sử dụng) → không nhắc.
    listed = dict(both, ChuHoSo_NguoiCungSuDung="Lê Thị Hoa")
    _, warnings = mapper.enrich(_facts(**listed, **_PARCEL))
    assert not any("cùng ký" in w for w in warnings)
    # GCN của người khác hẳn → cảnh báo lệch hồ sơ của mapper gốc, không thêm nhắc cùng ký.
    other = dict(_OWNER, GCN_NguoiSuDung="Bà Hồ Thị Mai và Ông Phạm Văn Tâm")
    _, warnings = mapper.enrich(_facts(**other, **_PARCEL))
    assert any("cùng một hồ sơ" in w for w in warnings) and not any("cùng ký" in w for w in warnings)


def test_authorized_submitter_keeps_roles_apart():
    fields, _ = mapper.enrich(_facts(
        **_OWNER,
        NguoiNop_HoTen="Đỗ Minh Quân",
        NguoiNop_SoDinhDanh="056 095 000 456",
        NguoiNop_DiaChi={"tinh": "Khánh Hòa", "xa": "Phường Nam Nha Trang", "chiTietDuoiXa": "Tổ dân phố 1"},
        **_PARCEL,
    ))
    values = _values(fields)
    assert values["data[fullname]"] == "Đỗ Minh Quân" and values["data[identityNumber]"] == "056095000456"
    assert values["data[ownerFullname]"] == "Trần Văn Bình" and values["data[ownerPhoneNumber]"] == "0905222333"
    assert values["data[phoneNumber]"] == ""  # số ở Đơn mục 1d là của chủ hồ sơ

    # Bật "Lấy người nộp theo tờ khai": Phần I = chủ hồ sơ.
    fields, _ = mapper.enrich(_facts(**_OWNER, NguoiNop_HoTen="Đỗ Minh Quân", **_PARCEL),
                              {"submitterMode": "owner_as_submitter"})
    assert _values(fields)["data[fullname]"] == "Trần Văn Bình"


def test_request_falls_back_to_this_procedure_name():
    owner = {key: value for key, value in _OWNER.items() if key != "Don_NoiDungBienDong"}
    fields, _ = mapper.enrich(_facts(**owner, GCN_SoPhatHanh="AB 123456", **_PARCEL))
    item = next(item for item in fields if item["name"] == "data[noidungyeucaugiaiquyet]")
    assert item["value"] == ("Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót số phát hành AB 123456")
    assert item["default"] is True


def test_missing_birthday_is_cleared_not_taken_from_gcn_year():
    fields, _ = mapper.enrich(_facts(ChuHoSo_HoTen="Trần Văn Bình", ChuHoSo_NgaySinh="1970"))
    values = _values(fields)
    assert values["data[birthday]"] == values["data[ownerBirthday]"] == ""


def test_old_gcn_layout_is_left_to_llm():
    """GCN mẫu cũ "I- Tên người sử dụng đất" không khớp mục I mẫu mới → bù tất định không ghi đè tên LLM đọc."""
    gcn = ("GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\nI- Tên người sử dụng đất\nBà LÊ THỊ HOA ; sinh năm 1975\nVà Ông TRẦN VĂN "
           "BÌNH ; sinh năm 1970\nII- Thửa đất được quyền sử dụng\n1. Thửa đất số : 17 2. Tờ bản đồ số: 09")
    fields = runner.apply_fallback({"GCN_NguoiSuDung": "Bà Lê Thị Hoa và Ông Trần Văn Bình"}, [{"text": gcn}])
    assert fields["GCN_NguoiSuDung"] == "Bà Lê Thị Hoa và Ông Trần Văn Bình"


def test_schema_and_prompt_cover_correction_traps():
    assert {"Don_NoiDungBienDong", "GCN_NguoiSuDung", "GCN_SoPhatHanh", "ThuaDat_DiaChiDayDu"} <= ALLOWED
    desc = {field["name"]: field["desc"] for field in FIELDS}
    assert "Giấy khai sinh" in desc["ChuHoSo_NgaySinh"] and "TUYỆT ĐỐI không lấy năm sinh" in desc["ChuHoSo_NgaySinh"]
    assert "Mẫu số 18" in desc["ChuHoSo_HoTen"]
    assert "Phường (xã):" in desc["ThuaDat_DiaChi"]
    assert "KHÔNG BAO GIỜ lấy từ GCN" in EXTRA_RULES and "xa lấy theo ĐƠN" in EXTRA_RULES
    assert '"Số chứng thực"' in EXTRA_RULES and "CÔNG CHỨNG VIÊN" in EXTRA_RULES


# --------------------------------------------------------------------------------------
# REGISTRY + LINK KÊ KHAI + TRỢ LÝ
# --------------------------------------------------------------------------------------
def test_registry_wires_both_pipelines_supports_split_and_locks_khanh_hoa():
    procedure = get_procedure(_KEY)
    assert procedure["label"] == "Khánh Hòa - Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót"
    assert procedure["supportsSplitDocuments"] is True
    assert procedure["detect"]["urlScope"] == ["khanhhoa.gov.vn"]
    assert procedure_province_slugs(procedure) == ["khanhhoa"]
    assert get_pipeline(_KEY).__module__.startswith("app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_khanh_hoa.")
    assert get_attach_pipeline(_KEY).__module__.startswith("app.pipelines.dinh_chinh_gcn_cap_lan_dau_sai_sot_khanh_hoa.")


def test_khanh_hoa_page_detects_only_this_procedure():
    """Trang 1.012796 trên cổng Khánh Hòa chỉ khớp thủ tục này (không khớp đính chính 1.012790 dù tên là chuỗi con);
    trang 1.012790 không khớp thủ tục này."""
    page = fold(_PAGE_TITLE + " " + " ".join(_ROWS))
    khanh_hoa = [p for p in PROCEDURES if "khanhhoa.gov.vn" in (p.get("detect") or {}).get("urlScope", [])]
    for procedure in khanh_hoa:
        hits = all(fold(text) in page for text in procedure["detect"]["textIncludes"])
        assert hits == (procedure["key"] == _KEY), procedure["key"]
    page_1012790 = fold("Đính chính Giấy chứng nhận đã cấp. Quy trình: 1.012790-1.1 - Thủ tục Đính chính Giấy chứng "
                        "nhận đã cấp - Đối với trường hợp còn lại.")
    assert not all(fold(text) in page_1012790 for text in get_procedure(_KEY)["detect"]["textIncludes"])
    # Cùng mã ở cổng Tuyên Quang: bản đó khóa tuyenquang.gov.vn.
    assert get_procedure("dinh-chinh-gcn-cap-lan-dau-sai-sot-tuyen-quang")["detect"]["urlScope"] == ["tuyenquang.gov.vn"]


def test_ke_khai_link_shares_registry_key_and_picks_ward_agency():
    (link,) = [link for link in KE_KHAI_LINKS if link["key"] == _KEY]
    assert link["code"] == "1.012796"
    assert link["label"] == get_procedure(_KEY)["label"]
    assert link["url"].endswith("019d2bfa-76cb-741b-996e-33d1ef50be50")
    # Quy trình "(Cấp Xã)": DVCQG chọn Tỉnh + Phường/Xã (UBND phường/xã), không thẻ Chi nhánh VPĐK.
    assert link["needsAgencySelect"] is True
    assert not link.get("provinceOnlyAgency") and not link.get("submitCardIncludesByWard") and not link.get("selectSo")


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
    assert handfree.procedure_code(procedure) == "1.012796"
    assert procedure["supportsSplitDocuments"] is True
    assert procedure["flowProfile"] == "xay-dung" and procedure["maePortal"] is True
    assert procedure["bxdFlow"]["capability"] == "supportsBxdFlowKhanhHoa"
    assert procedure["agencyProvince"] == "Khánh Hòa"
    assert "agencyProvinceOnly" not in procedure and "agencyCardIncludesByWard" not in procedure
    assert field_review_registry.get(_KEY)["required"] == ()
    assert handfree.is_allowed_in_province(procedure, "khanhhoa")
    assert not handfree.is_allowed_in_province(procedure, "tuyenquang")
    assert handfree.get_pipeline(_KEY) is get_pipeline(_KEY)
    assert handfree.get_attach_pipeline(_KEY) is get_attach_pipeline(_KEY)
    assert {doc["key"] for doc in procedure["requiredDocs"] if not doc.get("optional")} == {"don", "gcn"}
    assert PROCEDURE_HMONG[_KEY] and PROCEDURE_HINTS[_KEY]
