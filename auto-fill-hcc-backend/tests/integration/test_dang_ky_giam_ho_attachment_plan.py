import json

from app.pipelines.dang_ky_giam_ho.attach import planner
from app.pipelines.dang_ky_giam_ho.attach.dinh_kem_khong_tach import planner as preserve_planner
from app.pipelines.dang_ky_giam_ho.attach.dinh_kem_tach import planner as split_planner
from app.pipelines.dang_ky_giam_ho.attach.dinh_kem_tach.prompt import (
    SYSTEM_PROMPT as SPLIT_SYSTEM_PROMPT,
)
from app.pipelines.dang_ky_giam_ho.attach.prompt import SYSTEM_PROMPT, build_user_prompt
from app.process.schemas import FileItem
from app.procedures.registry import get_attach_pipeline, get_procedure


def _file(name):
    return FileItem(name=name, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")


def _session():
    return {
        "request_id": "req_dang_ky_giam_ho_attach",
        "procedure": "dang-ky-giam-ho",
        "fields": [
            {"name": "Requester_FullName", "value": "CHÈO TON SƠN"},
            {"name": "Guardian_FullName", "value": "HOÀNG A TOAN"},
            {"name": "Ward_FullName", "value": "CHẺO THÙY MY"},
        ],
    }


async def test_dang_ky_giam_ho_attachment_routes_rows_and_paper_declaration(monkeypatch):
    async def fake_ocr_per_file(files):
        texts = {
            "to-khai.pdf": "TỜ KHAI ĐĂNG KÝ GIÁM HỘ\nNgười giám hộ: HOÀNG A TOAN",
            "van-ban-cu.pdf": "VĂN BẢN THỎA THUẬN CỬ NGƯỜI GIÁM HỘ\nCử người có tên dưới đây làm người giám hộ",
            "ban-cam-doan.pdf": "BẢN CAM ĐOAN\nTôi có năng lực hành vi dân sự đầy đủ và có nhà riêng",
            "so-do.pdf": "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT\nThửa đất số 45",
            "cccd.pdf": "CĂN CƯỚC CÔNG DÂN\nSố / No.: 012081000601\nIDVNM081000601",
            "uy-quyen.pdf": "VĂN BẢN ỦY QUYỀN thực hiện việc đăng ký giám hộ",
            "hon-nhan.pdf": "GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN\nHọ tên: LÊ HUY CẬN",
        }
        return [{"name": f["name"], "text": texts[f["name"]], "provider": "tiengnoi"} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": []})

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    res = await planner.plan(
        [
            _file("to-khai.pdf"),
            _file("van-ban-cu.pdf"),
            _file("ban-cam-doan.pdf"),
            _file("so-do.pdf"),
            _file("cccd.pdf"),
            _file("uy-quyen.pdf"),
            _file("hon-nhan.pdf"),
        ],
        {},
        _session(),
    )
    items = res["attachments"]

    assert [item["fileName"] for item in items] == [
        "to-khai.pdf",
        "van-ban-cu.pdf",
        "ban-cam-doan.pdf",
        "so-do.pdf",
        "cccd.pdf",
        "uy-quyen.pdf",
        "hon-nhan.pdf",
    ]

    assert items[0]["target"] == "new"
    assert items[0]["componentName"] == "Tờ khai đăng ký giám hộ bản giấy"

    assert items[1]["target"] == "existing"
    assert items[1]["componentIndex"] == 2
    assert "Văn bản cử người giám hộ" in items[1]["componentName"]

    assert items[2]["target"] == "existing"
    assert items[2]["componentIndex"] == 3
    assert "Giấy tờ chứng minh điều kiện giám hộ" in items[2]["componentName"]

    assert items[3]["target"] == "new"
    assert items[4]["target"] == "new"
    assert items[5]["target"] == "existing"
    assert items[5]["componentIndex"] == 4
    assert "Văn bản ủy quyền" in items[5]["componentName"]
    assert items[6]["target"] == "new"
    assert items[6]["documentName"] == "Giấy xác nhận tình trạng hôn nhân"
    assert items[6]["componentName"] == "Giấy xác nhận tình trạng hôn nhân"
    assert any(
        entry["fileName"] == "hon-nhan.pdf"
        and entry["docType"] == "marital_status_certificate"
        for entry in res["extracted"]["classified"]
    )
    assert not res["errors"]


async def test_dang_ky_giam_ho_attachment_puts_all_identity_files_to_row_3(monkeypatch):
    async def fake_ocr_per_file(files):
        return [
            {"name": "cccd-nguoi-yeu-cau.pdf", "text": "CĂN CƯỚC CÔNG DÂN Số / No.: 012099002088"},
            {"name": "cccd-than-nhan.pdf", "text": "CĂN CƯỚC CÔNG DÂN Số / No.: 012177003172"},
        ]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"index": 0, "docType": "skip", "documentName": "Không liên quan"},
                {"index": 1, "docType": "other", "documentName": "Tài liệu khác"},
            ]
        })

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    res = await planner.plan([_file("cccd-nguoi-yeu-cau.pdf"), _file("cccd-than-nhan.pdf")], {}, _session())
    items = res["attachments"]

    assert len(items) == 2
    assert items[0]["componentIndex"] == 3
    assert items[0]["target"] == "existing"
    assert items[1]["componentIndex"] is None
    assert items[1]["target"] == "new"
    assert items[0]["documentName"] == "Căn cước công dân"


def test_dang_ky_giam_ho_attachment_registry():
    proc = get_procedure("dang-ky-giam-ho")

    assert proc["hasAttachmentStep"] is True
    assert get_attach_pipeline("dang-ky-giam-ho") is not None


def test_dang_ky_giam_ho_attachment_prompt_contract():
    assert "guardian_appointment" in SYSTEM_PROMPT
    assert "guardian_condition" in SYSTEM_PROMPT
    assert "Tờ khai đăng ký giám hộ bản giấy vẫn là paper_declaration" in SYSTEM_PROMPT
    assert "Mọi CCCD/CMND/căn cước/hộ chiếu" in SYSTEM_PROMPT
    assert "STT 1" in SYSTEM_PROMPT

    user_prompt = build_user_prompt([{"index": 0, "fileName": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN"}])
    assert "ocrText" in user_prompt
    assert "CĂN CƯỚC CÔNG DÂN" in user_prompt
    assert "fileName" not in user_prompt
    assert "cccd.pdf" not in user_prompt


async def test_preserve_mode_keeps_and_attaches_marital_status_whole_file(monkeypatch):
    ocr_text = """───── Trang 1/3 ─────
GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN
Họ, chữ đệm, tên: LÊ HUY CẬN
Giấy tờ tùy thân: Thẻ căn cước công dân số 038084030561
───── Trang 2/3 ─────
Thủ tục đăng ký giám hộ
Thông tin tra cứu cơ sở dữ liệu dân cư
CCCD / CMND: 012320003527
───── Trang 3/3 ─────
Thông tin gia đình
Số định danh: 012099002088
"""

    async def fake_ocr_per_file(files):
        return [{"name": files[0]["name"], "text": ocr_text, "provider": "tiengnoi"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        # Cố tình trả sai như trace thực tế; rule tiêu đề trang đầu phải thắng.
        return json.dumps({
            "documents": [{
                "index": 0,
                "docType": "guardian_condition",
                "documentName": "Căn cước công dân 2",
                "subjectName": "",
            }]
        })

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await planner.plan([_file("giấy xác nhận tình trạng hôn nhân.pdf")], {}, _session())

    assert result["attachments"] == [{
        "fileIndex": 0,
        "fileName": "giấy xác nhận tình trạng hôn nhân.pdf",
        "documentName": "Giấy xác nhận tình trạng hôn nhân",
        "componentName": "Giấy xác nhận tình trạng hôn nhân",
        "target": "new",
        "componentIndex": None,
        "needsAddComponent": True,
        "detectedType": "Giấy xác nhận tình trạng hôn nhân",
    }]
    assert result["extracted"]["attachmentMode"] == "preserve_files"
    assert result["extracted"]["classified"][0] == {
        "fileName": "giấy xác nhận tình trạng hôn nhân.pdf",
        "docType": "marital_status_certificate",
        "documentName": "Giấy xác nhận tình trạng hôn nhân",
        "target": "new",
        "componentIndex": None,
        "source": "rule",
    }


async def test_split_mode_splits_marital_status_from_population_database_pages(monkeypatch):
    ocr_text = """───── Trang 1/5 ─────
GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN
Họ, chữ đệm, tên: LÊ HUY CẬN
Giấy tờ tùy thân: Thẻ căn cước công dân số 038084030561
───── Trang 2/5 ─────
Thủ tục đăng ký giám hộ
Thông tin tra cứu cơ sở dữ liệu dân cư
Họ và tên: CHẺO YẾN NHI
CCCD / CMND: 012320003527
───── Trang 3/5 ─────
Thông tin gia đình
CHÈO TON SƠN Cha
───── Trang 4/5 ─────
Thông tin tra cứu cơ sở dữ liệu dân cư
Họ và tên: HOÀNG A TOAN
CCCD / CMND: 012081000601
───── Trang 5/5 ─────
Thông tin gia đình
TẨN SỦ MẨY Vợ
"""

    async def fake_ocr_per_file(files):
        return [{"name": files[0]["name"], "text": ocr_text, "provider": "tiengnoi"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "identity", "documentName": "Căn cước công dân"},
                {"fileIndex": 0, "pageFrom": 2, "pageTo": 3, "type": "guardian_condition", "documentName": "Trích xuất CSDL dân cư CHẺO YẾN NHI"},
                {"fileIndex": 0, "pageFrom": 4, "pageTo": 5, "type": "guardian_condition", "documentName": "Trích xuất CSDL dân cư HOÀNG A TOAN"},
            ]
        })

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await planner.plan(
        [_file("giấy xác nhận tình trạng hôn nhân.pdf")],
        {"splitDocuments": True},
        _session(),
    )

    assert result["extracted"]["attachmentMode"] == "split_documents"
    assert [item["documentName"] for item in result["attachments"]] == [
        "Giấy xác nhận tình trạng hôn nhân",
        "Trích xuất CSDL dân cư CHẺO YẾN NHI",
        "Trích xuất CSDL dân cư HOÀNG A TOAN",
    ]
    assert result["attachments"][0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0]}]
    assert result["attachments"][0]["target"] == "new"
    assert result["attachments"][0]["componentIndex"] is None
    assert result["attachments"][1]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1, 2]}]
    assert result["attachments"][1]["target"] == "existing"
    assert result["attachments"][1]["componentIndex"] == 3
    assert result["attachments"][2]["target"] == "new"
    assert result["attachments"][2]["componentIndex"] is None
    marital = result["extracted"]["classified"][0]
    assert marital["type"] == "marital_status_certificate"
    assert marital["documentName"] == "Giấy xác nhận tình trạng hôn nhân"
    assert marital["target"] == "new"
    assert (marital["pageFrom"], marital["pageTo"]) == (1, 1)


async def test_preserve_mode_names_land_certificate_from_structural_markers(monkeypatch):
    ocr_text = """II. Thửa đất, nhà ở và tài sản khác gắn liền với đất
1. Thửa đất:
a) Thửa đất số: 45, tờ bản đồ số: 72
Số vào sổ cấp GCN: CH00563
"""

    async def fake_ocr_per_file(files):
        return [{"name": files[0]["name"], "text": ocr_text, "provider": "tiengnoi"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [{
            "index": 0,
            "docType": "guardian_condition",
            "documentName": "Giấy tờ chứng minh điều kiện giám hộ",
            "subjectName": "",
        }]})

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    result = await planner.plan([_file("sổ đỏ bị mất tiêu đề.pdf")], {}, _session())

    assert result["attachments"][0]["documentName"] == "Giấy chứng nhận quyền sử dụng đất"
    assert result["attachments"][0]["target"] == "existing"
    assert result["attachments"][0]["componentIndex"] == 3


async def test_split_mode_splits_multiple_identity_subjects_without_reusing_component(monkeypatch):
    ocr_text = """───── Trang 1/4 ─────
CĂN CƯỚC CÔNG DÂN
Họ và tên: TẨN SỦ MẨY
Số / No.: 012181000685
───── Trang 2/4 ─────
Đặc điểm nhận dạng
CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI
IDVNM1810006853012181000685
───── Trang 3/4 ─────
CĂN CƯỚC CÔNG DÂN
Họ và tên: HOÀNG MÍ PHÚ
Số / No.: 012300000558
───── Trang 4/4 ─────
Đặc điểm nhận dạng
CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI
IDVNM3000005589012300000558
"""

    async def fake_ocr_per_file(files):
        return [{"name": files[0]["name"], "text": ocr_text, "provider": "tiengnoi"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({
            "documents": [
                {"fileIndex": 0, "pageFrom": 1, "pageTo": 2, "type": "identity", "documentName": "CCCD TẨN SỦ MẨY", "subjectName": "TẨN SỦ MẨY"},
                {"fileIndex": 0, "pageFrom": 3, "pageTo": 4, "type": "identity", "documentName": "CCCD HOÀNG MÍ PHÚ", "subjectName": "HOÀNG MÍ PHÚ"},
            ]
        })

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    result = await planner.plan(
        [_file("căn cước công dân.pdf")],
        {"splitDocuments": True},
        _session(),
    )

    assert [item["documentName"] for item in result["attachments"]] == [
        "CCCD TẨN SỦ MẨY",
        "CCCD HOÀNG MÍ PHÚ",
    ]
    assert result["attachments"][0]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [0, 1]}]
    assert result["attachments"][1]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [2, 3]}]
    assert result["attachments"][0]["componentIndex"] == 3
    assert result["attachments"][1]["componentIndex"] is None
    existing_components = [
        item["componentIndex"] for item in result["attachments"] if item["target"] == "existing"
    ]
    assert len(existing_components) == len(set(existing_components))


def test_split_prompt_locks_boundaries_and_marital_status_rule():
    assert "Mỗi trang phải xuất hiện ĐÚNG MỘT LẦN" in SPLIT_SYSTEM_PROMPT
    assert "Giấy xác nhận tình trạng hôn nhân" in SPLIT_SYSTEM_PROMPT
    assert "không được đổi thành identity" in SPLIT_SYSTEM_PROMPT.lower()
    assert "marital_status_certificate" in SPLIT_SYSTEM_PROMPT
    assert "PDF 10 trang gồm 5 CCCD" in SPLIT_SYSTEM_PROMPT


async def test_dang_ky_cham_dut_giam_ho_routes_basis_and_authorization_rows(monkeypatch):
    texts = {
        "to-khai.pdf": "TỜ KHAI ĐĂNG KÝ CHẤM DỨT GIÁM HỘ Kính gửi UBND phường An Bình",
        "cccd.pdf": "CĂN CƯỚC CÔNG DÂN Số / No.: 001090000111",
        "giay-khai-sinh.pdf": "GIẤY KHAI SINH Họ, chữ đệm, tên: LÊ THỊ HOA",
        "quyet-dinh.pdf": "QUYẾT ĐỊNH của Tòa án nhân dân về việc chấm dứt giám hộ",
        "uy-quyen.pdf": "VĂN BẢN ỦY QUYỀN Bên ủy quyền: ... Bên được ủy quyền: ...",
    }

    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "text": texts[f["name"]]} for f in files]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps({"documents": [
            {"index": 3, "docType": "other", "documentName": "Quyết định chấm dứt giám hộ"},
        ]})

    monkeypatch.setattr(preserve_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(preserve_planner.client, "chat", fake_chat)

    plan_fn = get_attach_pipeline("dang-ky-cham-dut-giam-ho")
    res = await plan_fn([_file(name) for name in texts], {}, {"request_id": "req_cham_dut"})
    by_file = {}
    for item in res["attachments"]:
        for idx in item.get("sourceFileIndexes") or [item["fileIndex"]]:
            by_file[list(texts)[idx]] = item

    declaration = by_file["to-khai.pdf"]
    assert declaration["target"] == "new"
    assert declaration["documentName"] == "Tờ khai đăng ký chấm dứt giám hộ bản giấy"

    # Bảng thành phần chấm dứt không có STT 3/4 của đăng ký giám hộ.
    assert all(item["componentIndex"] in (None, 2, 3) for item in res["attachments"])
    basis = [item for item in res["attachments"] if item["componentIndex"] == 2]
    assert len(basis) == 1
    assert basis[0]["componentName"] == "- Giấy tờ làm căn cứ chấm dứt giám hộ theo quy định của Bộ luật Dân sự"
    assert by_file["cccd.pdf"] is basis[0]
    for name in ("giay-khai-sinh.pdf", "quyet-dinh.pdf"):
        assert by_file[name]["target"] == "new"
        assert by_file[name]["needsAddComponent"] is True

    auth = by_file["uy-quyen.pdf"]
    assert auth["target"] == "existing"
    assert auth["componentIndex"] == 3
    assert auth["componentName"].startswith("- Văn bản ủy quyền")


def test_dang_ky_cham_dut_giam_ho_split_routing_renames_group_labels():
    result = {"attachments": [
        {"fileIndex": 0, "documentName": "Giấy tờ chứng minh điều kiện giám hộ", "target": "existing",
         "componentIndex": 3, "componentName": "- Giấy tờ chứng minh điều kiện giám hộ đương nhiên",
         "needsAddComponent": False, "detectedType": "Giấy tờ chứng minh điều kiện giám hộ"},
        {"fileIndex": 1, "documentName": "Tài liệu đăng ký giám hộ 2", "target": "new",
         "componentIndex": None, "componentName": "Tài liệu đăng ký giám hộ 2",
         "needsAddComponent": True, "detectedType": "Tài liệu đăng ký giám hộ 2"},
        {"fileIndex": 2, "documentName": "Giấy xác nhận tình trạng hôn nhân", "target": "new",
         "componentIndex": None, "componentName": "Giấy xác nhận tình trạng hôn nhân",
         "needsAddComponent": True, "detectedType": "Giấy xác nhận tình trạng hôn nhân"},
    ]}
    items = planner.route_cham_dut_attachments(result)["attachments"]

    assert items[0]["documentName"] == "Giấy tờ làm căn cứ chấm dứt giám hộ"
    assert items[0]["componentIndex"] == 2
    assert items[1]["documentName"] == "Tài liệu chấm dứt giám hộ 2"
    assert items[1]["target"] == "new"
    assert items[1]["componentName"] == "Tài liệu chấm dứt giám hộ 2"
    assert items[2]["target"] == "new"


async def test_dang_ky_cham_dut_giam_ho_split_mode_tach_cam_doan_trich_luc_to_khai(monkeypatch):
    assert get_procedure("dang-ky-cham-dut-giam-ho")["supportsSplitDocuments"] is True
    ocr_text = """───── Trang 1/3 ─────
CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
BẢN CAM ĐOAN
Họ, chữ đệm, tên: LÊ VĂN BÌNH
Giấy tờ tùy thân: 001090000111 cấp ngày 01/02/2021
Vợ chồng tôi đã về sinh sống tại địa phương, đủ điều kiện chăm sóc con.
───── Trang 2/3 ─────
UBND PHƯỜNG AN BÌNH
Số: 12/2025/TLGH
CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
TRÍCH LỤC ĐĂNG KÝ GIÁM HỘ
(BẢN SAO)
Người giám hộ: TRẦN VĂN CƯỜNG
Giấy tờ tùy thân: Thẻ căn cước công dân số 001060000222, Cục CS QLHC về trật tự xã hội cấp
Người được giám hộ: LÊ THỊ HOA
───── Trang 3/3 ─────
CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
TỜ KHAI ĐĂNG KÝ CHẤM DỨT GIÁM HỘ
Họ, chữ đệm, tên người yêu cầu: LÊ VĂN BÌNH
Giấy tờ tùy thân: CCCD số: 001090000111
"""

    async def fake_ocr_per_file(files):
        return [{"name": files[0]["name"], "text": ocr_text, "provider": "tiengnoi"}]

    async def fake_chat(messages, max_tokens, enable_thinking):
        # LLM đoán sai trang 2 là CCCD — luật tiêu đề trích lục phải thắng.
        return json.dumps({"documents": [
            {"fileIndex": 0, "pageFrom": 1, "pageTo": 1, "type": "guardian_condition",
             "documentName": "Bản cam đoan đủ điều kiện giám hộ"},
            {"fileIndex": 0, "pageFrom": 2, "pageTo": 2, "type": "identity",
             "documentName": "CCCD TRẦN VĂN CƯỜNG", "subjectName": "TRẦN VĂN CƯỜNG"},
            {"fileIndex": 0, "pageFrom": 3, "pageTo": 3, "type": "paper_declaration",
             "documentName": "Tờ khai đăng ký giám hộ bản giấy"},
        ]})

    monkeypatch.setattr(split_planner.ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(split_planner.client, "chat", fake_chat)

    plan_fn = get_attach_pipeline("dang-ky-cham-dut-giam-ho")
    res = await plan_fn([_file("scan.pdf")], {"splitDocuments": True}, {"request_id": "req_cham_dut"})
    items = res["attachments"]

    assert res["extracted"]["attachmentMode"] == "split_documents"
    assert [item["documentName"] for item in items] == [
        "Bản cam đoan",
        "Trích lục đăng ký giám hộ",
        "Tờ khai đăng ký chấm dứt giám hộ bản giấy",
    ]
    assert [item["sourceSegments"] for item in items] == [
        [{"fileIndex": 0, "pageIndexes": [0]}],
        [{"fileIndex": 0, "pageIndexes": [1]}],
        [{"fileIndex": 0, "pageIndexes": [2]}],
    ]
    assert items[0]["target"] == "existing"
    assert items[0]["componentIndex"] == 2
    assert items[0]["componentName"].startswith("- Giấy tờ làm căn cứ chấm dứt giám hộ")
    assert items[1]["target"] == "new" and items[1]["needsAddComponent"] is True
    assert items[2]["target"] == "new" and items[2]["needsAddComponent"] is True
    assert res["extracted"]["classified"][1]["type"] == "other"
