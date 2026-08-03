import json

from app.pipelines.cap_lai_cap_doi_gcn_ho_kinh_doanh.attach import planner
from app.pipelines.cap_lai_cap_doi_gcn_ho_kinh_doanh.attach.planner import _detect_type
from app.pipelines.cap_lai_cap_doi_gcn_ho_kinh_doanh.process import mapper
from app.pipelines.cap_lai_cap_doi_gcn_ho_kinh_doanh.process.fallback import apply_ocr_fallback
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure
from app.services import ocr


def _field(name, value):
    return {"name": name, "value": value}


def test_builds_reissue_flow_from_handwritten_sample_without_forcing_code_length():
    pages, flow = mapper.build([
        _field("HoKinhDoanh_MaSo", "888.9545300"),
        _field("HienTai_Ten", "NGUYỄN THỊ QUỲNH"),
        _field("DeNghi_Loai", "cap_lai"),
        _field("DeNghi_LyDo", "Bị mất"),
        _field("ChuHo", {"hoTen": "NGUYỄN THỊ QUỲNH", "soDinhDanh": "033197013790"}),
        _field("NguoiKy", {"hoTen": "NGUYỄN THỊ QUỲNH"}),
    ])

    assert flow["workflow"] == "reissue"
    assert flow["wizardType"] == "reissue"
    assert flow["registrationOption"] == "REI"
    assert flow["requestKind"] == "cap_lai"
    assert flow["search"] == {
        "method": "businessNumber",
        "value": "8889545300",
        "expectedName": "NGUYỄN THỊ QUỲNH",
        "expectedBusinessNumber": "8889545300",
    }
    assert flow["pageOrder"] == ["thong-tin-de-nghi-cap-lai", "nguoi-nop-ho-so"]
    request = pages["thong-tin-de-nghi-cap-lai"][0]
    assert request == {"name": "__reissueRequest", "comp": "raw", "value": {
        "kind": "cap_lai", "reason": "Bị mất",
    }}


def test_cap_doi_remains_cap_doi_and_never_falls_back_to_cap_lai():
    pages, flow = mapper.build([
        _field("HoKinhDoanh_MaSo", "001090057964"),
        _field("DeNghi_Loai", "cap_doi"),
        _field("DeNghi_LyDo", "Cấp đổi sang Giấy chứng nhận đăng ký hộ kinh doanh"),
    ])
    request = pages["thong-tin-de-nghi-cap-lai"][0]["value"]
    assert request["kind"] == "cap_doi"
    assert flow["requestKind"] == "cap_doi"


def test_search_falls_back_to_signer_identity_when_business_code_is_missing():
    _, flow = mapper.build([
        _field("NguoiKy", {"hoTen": "NGUYỄN THỊ QUỲNH", "soDinhDanh": "033197013790"}),
    ])
    assert flow["search"]["method"] == "identityNumber"
    assert flow["search"]["value"] == "033197013790"


def test_ocr_fallback_keeps_physical_cccd_as_unassigned_identity_candidate():
    documents = [{"name": "mau2.pdf", "text": "Mã số hộ kinh doanh: 888.9545300"}, {
        "name": "cccd.pdf",
        "text": """CĂN CƯỚC CÔNG DÂN
Citizen Identity Card
Số / No.: 040203015844
Họ và tên / Full name:
VŨ ĐÌNH THIẾT
Ngày sinh / Date of birth: 26/04/2003
Giới tính / Sex: Nam Quốc tịch / Nationality: Việt Nam
Nơi thường trú / Place of residence: Xóm Long Thành
Tam Hợp, Quý Hợp, Nghệ An
Có giá trị đến: 26/04/2028
Ngày, tháng, năm / Date, month, year: 02/07/2021
""",
    }]
    fields = apply_ocr_fallback({}, documents)
    assert fields["HoKinhDoanh_MaSo"] == "8889545300"
    assert "NguoiKy" not in fields
    assert fields["Cccd_DanhSach"][0]["diaChi"] == {
        "quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Tam Hợp", "diaChi": "Xóm Long Thành",
    }


def test_attachment_markers_and_registry_contract():
    assert _detect_type("Mẫu số 2 GIẤY ĐỀ NGHỊ Cấp lại Giấy chứng nhận đăng ký hộ kinh doanh") == "reissue_application"
    assert _detect_type("CĂN CƯỚC CÔNG DÂN") is None
    key = "cap-lai-cap-doi-gcn-ho-kinh-doanh"
    procedure = get_procedure(key)
    assert procedure["businessWorkflow"] == "reissue"
    assert [page["key"] for page in procedure["pages"]] == ["thong-tin-de-nghi-cap-lai", "nguoi-nop-ho-so"]
    assert get_pipeline(key) is not None
    assert get_attach_pipeline(key) is not None


async def test_attachment_plan_uses_exact_portal_categories(monkeypatch):
    texts = {
        "application.pdf": "Mẫu số 2 GIẤY ĐỀ NGHỊ Cấp lại Giấy chứng nhận đăng ký hộ kinh doanh",
        "cccd.pdf": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card",
    }

    async def fake_ocr_per_file(files):
        return [{"name": item["name"], "text": texts[item["name"]]} for item in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "type": "reissue_application", "documentName": "Giấy đề nghị cấp lại GCN hộ kinh doanh"},
            {"index": 1, "type": "other", "documentName": "Căn cước công dân Vũ Đình Thiết"},
        ]}, ensure_ascii=False)

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")
             for name in texts]
    result = await planner.plan(files)
    assert [item["category"] for item in result["attachments"]] == ["BUSREISSUEFRM", "OTHERS"]
    assert result["attachments"][0]["componentName"] == "Giấy đề nghị cấp lại Giấy chứng nhận đăng ký hộ kinh doanh"
    assert result["attachments"][1]["documentName"] == "Căn cước công dân Vũ Đình Thiết"
