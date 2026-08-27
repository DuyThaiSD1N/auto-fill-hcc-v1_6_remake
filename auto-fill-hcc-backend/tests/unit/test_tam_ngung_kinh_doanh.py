import json

from app.pipelines.tam_ngung_kinh_doanh.attach import planner
from app.pipelines.tam_ngung_kinh_doanh.attach.planner import _detect_type
from app.pipelines.tam_ngung_kinh_doanh.process import mapper
from app.pipelines.tam_ngung_kinh_doanh.process.fallback import apply_ocr_fallback
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure
from app.services import ocr


def _field(name, value):
    return {"name": name, "value": value}


def test_builds_suspension_and_applicant_pages_from_notice_and_certificate():
    pages, flow = mapper.build([
        _field("HoKinhDoanh_MaSo", "0270 8900 0919"),
        _field("HienTai_Ten", "HỘ KINH DOANH HOÀNG MAXX"),
        _field("TamNgung_TuNgay", "1/7/2026"),
        _field("TamNgung_DenNgay", "30/12/2026"),
        _field("TamNgung_LyDo", "Kinh doanh không hiệu quả, tạm ngừng để tái cơ cấu."),
        _field("ChuHo", {
            "hoTen": "NGUYỄN ĐÌNH HOÀNG",
            "soDinhDanh": "027089000919",
            "diaChi": {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Phường Song Liễu", "diaChi": "Tổ dân phố Đa Tiện"},
        }),
        # Giấy đề nghị chỉ có tên người ký; mapper phải bổ sung địa chỉ từ chủ hộ cùng tên.
        _field("NguoiNop", {"hoTen": "NGUYỄN ĐÌNH HOÀNG"}),
    ])

    assert flow["workflow"] == "suspension"
    assert flow["wizardType"] == "change"
    assert flow["amendmentType"] == "SUSPEN"
    assert flow["search"]["method"] == "businessNumber"
    assert flow["search"]["value"] == "027089000919"
    assert flow["pageOrder"] == ["tam-ngung-hoat-dong", "nguoi-nop-ho-so"]

    suspension = {item["name"]: item for item in pages["tam-ngung-hoat-dong"]}
    assert suspension["ctl00$C$UC_DW_SUSPENSIONEdtCtl$SUSPENSION_START_DATEFld"]["value"] == "01/07/2026"
    assert suspension["ctl00$C$UC_DW_SUSPENSIONEdtCtl$SUSPENSION_START_DATEFld"]["comp"] == "dom-date"
    assert suspension["ctl00$C$UC_DW_SUSPENSIONEdtCtl$SUSPENSION_END_DATEFld"]["value"] == "30/12/2026"
    assert suspension["ctl00$C$UC_DW_SUSPENSIONEdtCtl$SUSPENSION_END_DATEFld"]["comp"] == "dom-date"
    assert suspension["ctl00$C$UC_DW_SUSPENSIONEdtCtl$SUSPENSION_REASONFld"]["value"].startswith("Kinh doanh")
    assert suspension["ctl00$C$UC_DW_SUSPENSIONEdtCtl$SUSPENSION_REASONFld"]["comp"] == "dom-input"

    applicant = {item["name"]: item for item in pages["nguoi-nop-ho-so"]}
    assert applicant["ctl00$C$PERS_SUBGroup"]["value"] == "Người có thẩm quyền ký Giấy đề nghị đăng ký Hộ kinh doanh"
    assert applicant["ctl00$C$PERSCtl$ADDRCCtl$CITY_IDFld"]["value"] == "Bắc Ninh"
    assert applicant["ctl00$C$PERSCtl$ADDRCCtl$WARD_IDFld"]["value"] == "Song Liễu"


def test_does_not_fabricate_suspension_dates_when_missing():
    pages, _ = mapper.build([
        _field("ChuHo", {"hoTen": "Nguyễn Văn A", "soDinhDanh": "012345678901"}),
    ])
    names = [item["name"] for item in pages["tam-ngung-hoat-dong"]]
    assert names == []


def test_falls_back_to_owner_identity_for_search():
    _, flow = mapper.build([
        _field("ChuHo", {"hoTen": "Nguyễn Văn A", "soDinhDanh": "012345678901"}),
    ])
    assert flow["search"]["method"] == "identityNumber"
    assert flow["search"]["value"] == "012345678901"


def test_ocr_fallback_keeps_physical_cccd_as_identity_candidate():
    raw = {
        "HienTai_Ten": "HỘ KINH DOANH NGUYỄN PHÚ LUÂN",
        "NguoiNop": {"hoTen": "NGUYỄN PHÚ LUÂN"},
    }
    documents = [{"name": "GiayDeNghi.pdf", "text": "Mã số hộ kinh doanh: 001090057964"}, {
        "name": "cccd_thiet.pdf",
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

    fields = apply_ocr_fallback(raw, documents)
    assert fields["HoKinhDoanh_MaSo"] == "001090057964"
    card = fields["Cccd_DanhSach"][0]
    assert card["hoTen"] == "VŨ ĐÌNH THIẾT"
    assert card["soDinhDanh"] == "040203015844"
    assert card["ngaySinh"] == "26/04/2003"
    assert card["gioiTinh"] == "Nam"
    assert card["ngayCap"] == "02/07/2021"
    assert card["diaChi"] == {
        "quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Tam Hợp", "diaChi": "Xóm Long Thành",
    }

    _, flow = mapper.build([_field(name, value) for name, value in fields.items()])
    assert flow["search"] == {
        "method": "businessNumber",
        "value": "001090057964",
        "expectedName": "HỘ KINH DOANH NGUYỄN PHÚ LUÂN",
        "expectedBusinessNumber": "001090057964",
    }
    assert flow["identityCandidates"][0]["soDinhDanh"] == "040203015844"


def test_attachment_markers_route_three_portal_categories():
    assert _detect_type("GIẤY ĐỀ NGHỊ ĐĂNG KÝ TẠM NGỪNG KINH DOANH") == "suspension_notice"
    assert _detect_type("GIẤY CHỨNG NHẬN ĐĂNG KÝ HỘ KINH DOANH") == "registration_certificate"
    assert _detect_type("CĂN CƯỚC CÔNG DÂN") is None


def test_registry_exposes_complete_suspension_procedure():
    key = "tam-ngung-kinh-doanh"
    procedure = get_procedure(key)
    assert procedure["businessWorkflow"] == "suspension"
    assert [page["key"] for page in procedure["pages"]] == ["tam-ngung-hoat-dong", "nguoi-nop-ho-so"]
    assert get_pipeline(key) is not None
    assert get_attach_pipeline(key) is not None


async def test_attachment_plan_uses_exact_three_portal_categories(monkeypatch):
    texts = {
        "notice.pdf": "GIẤY ĐỀ NGHỊ ĐĂNG KÝ TẠM NGỪNG KINH DOANH",
        "certificate.pdf": "GIẤY CHỨNG NHẬN ĐĂNG KÝ HỘ KINH DOANH",
        "cccd.pdf": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card",
    }

    async def fake_ocr_per_file(files):
        return [{"name": item["name"], "text": texts[item["name"]]} for item in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 0, "type": "suspension_notice", "documentName": "Giấy đề nghị tạm ngừng kinh doanh HKD"},
            {"index": 1, "type": "registration_certificate", "documentName": "Giấy chứng nhận đăng ký HKD"},
            {"index": 2, "type": "other", "documentName": "Căn cước công dân chủ hộ"},
        ]}, ensure_ascii=False)

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [FileItem(
        name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc",
    ) for name in texts]
    result = await planner.plan(files)
    assert [item["category"] for item in result["attachments"]] == [
        "SUSPENSION_NOTICE",
        "BUSINESS_REG_CERT_ORIGINAL",
        "OTHERS",
    ]
