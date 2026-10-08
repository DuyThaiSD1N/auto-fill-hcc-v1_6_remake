"""Đổi, cấp lại Giấy xác nhận khuyết tật (1.001653): mapper, prompt, đính kèm, registry."""

import json

from app.pipelines.doi_cap_lai_giay_xac_nhan_khuyet_tat import process as agent
from app.pipelines.doi_cap_lai_giay_xac_nhan_khuyet_tat.attach import planner
from app.pipelines.doi_cap_lai_giay_xac_nhan_khuyet_tat.process import mapper
from app.pipelines.doi_cap_lai_giay_xac_nhan_khuyet_tat.process.prompt import EXTRA_RULES
from app.pipelines.doi_cap_lai_giay_xac_nhan_khuyet_tat.process.schema import ALLOWED, LY_DO_LABELS
from app.pipelines.khuyet_tat.process import runner as runner_base
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure
from app.services import ocr

_REPRESENTED = [
    {"name": "ChuHoSo_HoTen", "value": "LÊ VĂN AN"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "001210012345"},
    {"name": "Nkt_HoTen", "value": "LÊ VĂN AN"},
    {"name": "Nkt_SoDinhDanh", "value": "001210012345"},
    {"name": "Nkt_NgaySinh", "value": "02/03/2012"},
    {"name": "Ndd_HoTen", "value": "LÊ VĂN BÌNH"},
    {"name": "Ndd_SoDinhDanh", "value": "001085067890"},
    {"name": "Ndd_QuanHe", "value": "bố đẻ"},
]


def _values(fields, options=None):
    return {f["name"]: f for f in mapper.enrich(fields, options or {})}


def test_cap_lai_ticks_option_3_and_defaults_reason_to_lost():
    out = mapper.enrich(_REPRESENTED + [{"name": "DeNghi_NoiDung", "value": "cap_lai"}], {})
    names = [f["name"] for f in out]
    by_name = {f["name"]: f for f in out}

    assert by_name["data[chonNoiDungDeNghi][]"]["optionValue"] == "3"
    assert by_name["data[chonNoiDungDeNghi][]"]["value"] is True
    assert by_name["data[LydoCapdoiCaplaiMa]"]["value"] == LY_DO_LABELS["mat_hu_hong"]
    assert by_name["data[LydoCapdoiCaplaiMa]"]["comp"] == "dom-select"
    # Nội dung đề nghị đứng trước khối người khuyết tật, như thứ tự trên form.
    assert names.index("data[chonNoiDungDeNghi][]") < names.index("data[NktHoTen]")
    assert names.index("data[ownerFullname]") < names.index("data[chonNoiDungDeNghi][]")
    assert by_name["data[NddQuanheNkt]"]["value"] == "Cha"


def test_cap_doi_ticks_option_4_and_leaves_reason_unless_stated():
    values = _values(_REPRESENTED + [{"name": "DeNghi_NoiDung", "value": "cap_doi"}])
    assert values["data[chonNoiDungDeNghi][]"]["optionValue"] == "4"
    assert "data[LydoCapdoiCaplaiMa]" not in values

    stated = _values(_REPRESENTED + [
        {"name": "DeNghi_NoiDung", "value": "cap_doi"},
        {"name": "DeNghi_LyDo", "value": "sai_thong_tin"},
    ])
    assert stated["data[LydoCapdoiCaplaiMa]"]["value"] == LY_DO_LABELS["sai_thong_tin"]


def test_xac_dinh_options_of_base_form_are_never_emitted():
    values = _values(_REPRESENTED + [{"name": "DeNghi_NoiDung", "value": "xac_dinh"}])
    assert "data[chonNoiDungDeNghi][]" not in values
    assert "data[LydoCapdoiCaplaiMa]" not in values


def test_section_iii_is_still_mapped_from_shared_form():
    values = _values(_REPRESENTED + [
        {"name": "DeNghi_NoiDung", "value": "cap_lai"},
        {"name": "KhuyetTat_ChiTiet", "value": ["kt5_1"]},
        {"name": "MucDo_HoatDong", "value": {"1": "CTG"}},
    ])
    assert values["data[khuyetTat5Obj][khuyetTatRadio]"]["value"] == "co"
    assert values["data[khuyetTat5Obj][khuyetTatRadio1]"]["value"] == "co"
    assert values["data[mucDoKhuyetTatObj][mucDoRadio1]"]["value"] == "CTG"


_OCR_DON = """ĐƠN ĐỀ NGHỊ XÁC ĐỊNH, XÁC ĐỊNH LẠI MỨC ĐỘ KHUYẾT TẬT
I. Thông tin người được xác định mức độ khuyết tật
- Họ và tên: Lê Văn An
- Sinh ngày 02 tháng 3 năm 2012 Giới tính: nam
- Số CMND hoặc căn cước công dân: 001212 012345
- Nơi ở hiện nay: Xóm 3, xã Nghi Hoa, tỉnh Nghệ An.
II. Thông tin người đại diện hợp pháp (nếu có)
- Họ và tên: Lê Văn Bình
- Số CMND hoặc căn cước công dân: 001085067890
"""


def test_section_i_identity_reads_only_person_in_section_i():
    assert runner_base.section_i_identity(_OCR_DON) == "001212012345"
    # Mục I bỏ trống số → không được lấy số của người đại diện ở mục II.
    blank = _OCR_DON.replace("001212 012345", "")
    assert runner_base.section_i_identity(blank) == ""


def test_missing_section_i_identity_is_filled_for_disabled_person_and_owner():
    """LLM chỉ trả họ tên chủ hồ sơ, bỏ sót số căn cước mục I dù OCR đọc rõ."""
    res = {
        "ocr_text": _OCR_DON,
        "fields": [
            {"name": "ChuHoSo_HoTen", "value": "Lê Văn An"},
            {"name": "Nkt_HoTen", "value": "Lê Văn An"},
            {"name": "Nkt_NgaySinh", "value": "02/03/2012"},
            {"name": "Nkt_GioiTinh", "value": "Nam"},
            {"name": "Ndd_HoTen", "value": "Lê Văn Bình"},
            {"name": "Ndd_SoDinhDanh", "value": "001085067890"},
            {"name": "DeNghi_NoiDung", "value": "cap_lai"},
        ],
    }
    runner_base.fill_section_i_identity(res)
    values = _values(res["fields"])

    assert values["data[NktSoDinhdanh]"]["value"] == "001212012345"
    assert values["data[ownerIdentityNumber]"]["value"] == "001212012345"
    assert values["data[ownerBirthday]"]["value"] == "02/03/2012"
    assert values["data[ownerGender]"]["value"] == "Nam"
    assert values["data[NddSoDinhdanh]"]["value"] == "001085067890"


def test_owner_is_not_merged_with_section_i_when_names_conflict():
    values = _values([
        {"name": "ChuHoSo_HoTen", "value": "Trần Thị Cúc"},
        {"name": "Nkt_HoTen", "value": "Lê Văn An"},
        {"name": "Nkt_SoDinhDanh", "value": "001212012345"},
        {"name": "Nkt_NgaySinh", "value": "02/03/2012"},
    ])
    assert values["data[ownerFullname]"]["value"] == "Trần Thị Cúc"
    assert "data[ownerIdentityNumber]" not in values
    assert "data[ownerBirthday]" not in values


def test_prompt_replaces_proposal_rules_of_base_procedure():
    assert "Đổi, cấp lại Giấy xác nhận khuyết tật" in EXTRA_RULES
    assert '"cap_lai"' in EXTRA_RULES and '"cap_doi"' in EXTRA_RULES
    assert '"xac_dinh_lai"' not in EXTRA_RULES
    assert "<cccd_rules>" in EXTRA_RULES
    assert {"DeNghi_NoiDung", "DeNghi_LyDo", "ChuHoSo_HoTen", "MucDo_HoatDong"} <= ALLOWED


def _file(name: str) -> FileItem:
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


async def test_attach_puts_every_file_into_single_row(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "don.pdf", "text": "ĐƠN ĐỀ NGHỊ ... CẤP, CẤP ĐỔI, CẤP LẠI GIẤY XÁC NHẬN KHUYẾT TẬT"},
            {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN Số: 001085067890"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "type": "don_de_nghi", "title": "Đơn đề nghị"},
            {"index": 1, "type": "cccd", "title": "Căn cước công dân"},
        ]}, ensure_ascii=False)

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)

    res = await planner.plan([_file("don.pdf"), _file("cccd.pdf")], {}, {})

    items = res["attachments"]
    assert [i["fileName"] for i in items] == ["don.pdf", "cccd.pdf"]
    assert all(i["target"] == "fixed-slot" and i["slotIndex"] == 0 for i in items)
    assert items[0]["documentName"] == "Đơn đề nghị cấp đổi, cấp lại Giấy xác nhận khuyết tật"
    assert len(res["errors"]) == 1 and "cccd.pdf" in res["errors"][0]


async def test_attach_keeps_files_when_llm_fails(monkeypatch):
    async def fake_ocr_per_file(files):
        return [{"name": "don.pdf", "text": "ĐƠN ĐỀ NGHỊ"}]

    async def broken_chat(messages, max_tokens, enable_thinking):
        raise RuntimeError("llm down")

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", broken_chat)

    res = await planner.plan([_file("don.pdf")], {}, {})

    assert len(res["attachments"]) == 1
    assert res["attachments"][0]["slotIndex"] == 0
    assert any("attachment_agent" in err for err in res["errors"])


def test_registry_wires_process_and_attach_pipelines():
    key = "doi-cap-lai-giay-xac-nhan-khuyet-tat"
    proc = get_procedure(key)

    assert get_pipeline(key) is agent.run
    assert get_attach_pipeline(key) is planner.plan
    assert proc["label"] == "Đổi, cấp lại Giấy xác nhận khuyết tật"
    assert "maThuTuc=1.001653" in proc["detect"]["urlIncludes"]
    assert proc["hasAttachmentStep"] is True
    # Không tranh URL với thủ tục xác định mức độ khuyết tật cùng cổng.
    assert "maThuTuc=1.001653" not in get_procedure("xac-dinh-muc-do-khuyet-tat")["detect"]["urlIncludes"]
