"""Kiểm thử contract thủ tục hỗ trợ chi phí hỏa táng Bắc Ninh."""

from app.pipelines.ho_tro_chi_phi_hoa_tang_bac_ninh.attach.planner import build_plan_items
from app.pipelines.ho_tro_chi_phi_hoa_tang_bac_ninh.process.mapper import enrich
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _mapped(values: dict, purpose: str = "registration_form"):
    fields = [{"name": name, "value": value} for name, value in values.items()]
    mapped, warnings = enrich(fields, {"purpose": purpose})
    return {field["name"]: field for field in mapped}, warnings


def test_registration_mapper_separates_deceased_and_arranger_duplicate_labels():
    fields, warnings = _mapped({
        "Don_KinhGui": "Ủy ban nhân dân phường Song Liễu",
        "NguoiChet_HoTen": "NGUYỄN VĂN BÍNH",
        "NguoiChet_NgaySinh": "06/10/1958",
        "NguoiChet_SoDinhDanh": "027058003127",
        "NguoiChet_DiaChiThuongTru": "Song Liễu, Bắc Ninh",
        "NguoiChet_NgayChet": "16/06/2026",
        "KhaiTu_So": "73/2026/TLKT",
        "HoaTang_ThoiGian": "18/06/2026",
        "HoaTang_DiaDiem": "An Lạc Viên Thái Nguyên",
        "NguoiDungRa_HoTen": "NGUYỄN QUÝ KHANH",
        "NguoiDungRa_NgaySinh": "15/11/1984",
        "NguoiDungRa_SoDinhDanh": "027084015679",
        "NguoiDungRa_DiaChiThuongTru": "Song Liễu, Bắc Ninh",
        "NguoiDungRa_SoDienThoai": "0974362688",
        "NguoiDungRa_QuanHeVoiNguoiChet": "Con",
    })

    assert fields["element_75752"]["value"] == "NGUYỄN VĂN BÍNH"
    assert fields["element_75753"]["value"] == "06/10/1958"
    assert fields["element_75756"]["value"] == "027058003127"
    assert fields["element_75767"]["value"] == "NGUYỄN QUÝ KHANH"
    assert fields["element_75768"]["value"] == "15/11/1984"
    assert fields["element_75769"]["value"] == "027084015679"
    assert fields["element_75773"]["value"] == "0974362688"
    assert all(field["comp"] == "bn-input" for field in fields.values())
    assert not warnings


def test_authorized_mapper_requires_real_authorization_document():
    fields, warnings = _mapped({
        "NguoiDuocUyQuyen_HoTen": "PHẠM THỊ HỒNG",
        "NguoiDuocUyQuyen_SoDinhDanh": "027194012345",
    }, "authorized_person")

    assert fields == {}
    assert "Không tìm thấy" in warnings[0]


def test_authorized_mapper_fills_only_authorized_person_block():
    fields, warnings = _mapped({
        "UyQuyen_CoBienBan": True,
        "NguoiDuocUyQuyen_HoTen": "PHẠM THỊ HỒNG",
        "NguoiDuocUyQuyen_NgaySinh": "02/03/1994",
        "NguoiDuocUyQuyen_GioiTinh": "Nữ",
        "NguoiDuocUyQuyen_SoDinhDanh": "027194012345",
        "NguoiDuocUyQuyen_ThuongTru": {
            "quocGia": "Việt Nam",
            "tinh": "Bắc Ninh",
            "xa": "Phường Song Liễu",
            "diaChi": "Khu Thanh Lâm",
        },
        "NguoiDungRa_HoTen": "NGƯỜI KHÁC",
    }, "authorized_person")

    assert fields["doiTuongKhachoTen"]["value"] == "PHẠM THỊ HỒNG"
    assert fields["doiTuongKhacsoDinhDanh"]["value"] == "027194012345"
    assert fields["doiTuongKhactinhThanhId"]["comp"] == "bn-select"
    assert fields["doiTuongKhacphuongXaId"]["value"] == "Phường Song Liễu"
    assert "element_75767" not in fields
    assert not warnings


def test_combined_pdf_routes_once_to_declaration_row():
    raw_files = [{"name": "ho-so-gop.pdf", "type": "application/pdf", "dataUrl": "data:"}]
    ocr_results = [{
        "name": "ho-so-gop.pdf",
        "text": (
            "ĐƠN ĐỀ NGHỊ HỖ TRỢ KINH PHÍ HỎA TÁNG Mẫu số 01\n"
            "HỢP ĐỒNG DỊCH VỤ HỎA TÁNG tại cơ sở hỏa táng\n"
            "TRÍCH LỤC KHAI TỬ"
        ),
    }]

    attachments, classified = build_plan_items(raw_files, ocr_results)

    assert [item["componentName"] for item in attachments] == ["KQ001004"]
    assert [item["fileIndex"] for item in attachments] == [0]
    assert all(item["target"] == "existing" for item in attachments)
    assert classified[0]["labels"] == ["to_khai", "hop_dong_hoa_tang", "trich_luc_khai_tu"]
    assert classified[0]["routeLabel"] == "to_khai"


def test_standalone_authorization_routes_to_declaration_row_with_concrete_name():
    raw_files = [{"name": "uy-quyen.pdf", "type": "application/pdf", "dataUrl": "data:"}]
    ocr_results = [{"name": "uy-quyen.pdf", "text": "BIÊN BẢN ỦY QUYỀN nhận hỗ trợ chi phí hỏa táng"}]

    attachments, _ = build_plan_items(raw_files, ocr_results)

    assert attachments[0]["target"] == "existing"
    assert attachments[0]["componentName"] == "KQ001004"
    assert attachments[0]["documentName"] == "Biên bản ủy quyền nhận hỗ trợ hỏa táng"
    assert attachments[0]["documentName"] != "Tài liệu bổ sung"


def test_standalone_contract_routes_to_contract_row():
    raw_files = [{"name": "hop-dong.pdf", "type": "application/pdf", "dataUrl": "data:"}]
    ocr_results = [{
        "name": "hop-dong.pdf",
        "text": "HỢP ĐỒNG DỊCH VỤ HỎA TÁNG ký với cơ sở hỏa táng",
    }]

    attachments, classified = build_plan_items(raw_files, ocr_results)

    assert len(attachments) == 1
    assert attachments[0]["componentName"] == "KQ001005"
    assert attachments[0]["detectedType"] == "hop_dong_hoa_tang"
    assert classified[0]["routeLabel"] == "hop_dong_hoa_tang"


def test_contract_mixed_with_identity_document_routes_to_declaration_row():
    raw_files = [{"name": "hop-dong-va-cccd.pdf", "type": "application/pdf", "dataUrl": "data:"}]
    ocr_results = [{
        "name": "hop-dong-va-cccd.pdf",
        "text": "HỢP ĐỒNG DỊCH VỤ HỎA TÁNG\nCĂN CƯỚC CÔNG DÂN Citizen Identity Card",
    }]

    attachments, classified = build_plan_items(raw_files, ocr_results)

    assert len(attachments) == 1
    assert attachments[0]["componentName"] == "KQ001004"
    assert classified[0]["labels"] == ["hop_dong_hoa_tang", "cccd"]
    assert classified[0]["routeLabel"] == "to_khai"


def test_loose_documents_all_route_to_declaration_except_standalone_contract():
    raw_files = [
        {"name": "to-khai.pdf", "type": "application/pdf", "dataUrl": "data:"},
        {"name": "cccd.pdf", "type": "application/pdf", "dataUrl": "data:"},
        {"name": "khai-tu.pdf", "type": "application/pdf", "dataUrl": "data:"},
        {"name": "hoa-don.pdf", "type": "application/pdf", "dataUrl": "data:"},
        {"name": "hop-dong.pdf", "type": "application/pdf", "dataUrl": "data:"},
        {"name": "khong-ro.pdf", "type": "application/pdf", "dataUrl": "data:"},
    ]
    ocr_results = [
        {"name": "to-khai.pdf", "text": "ĐƠN ĐỀ NGHỊ HỖ TRỢ KINH PHÍ HỎA TÁNG Mẫu số 01"},
        {"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card"},
        {"name": "khai-tu.pdf", "text": "TRÍCH LỤC KHAI TỬ"},
        {"name": "hoa-don.pdf", "text": "HÓA ĐƠN THANH TOÁN DỊCH VỤ HỎA TÁNG"},
        {"name": "hop-dong.pdf", "text": "HỢP ĐỒNG DỊCH VỤ HỎA TÁNG"},
        {"name": "khong-ro.pdf", "text": "Tài liệu kèm theo"},
    ]

    attachments, _ = build_plan_items(raw_files, ocr_results)

    assert len(attachments) == len(raw_files)
    assert [item["fileIndex"] for item in attachments] == list(range(len(raw_files)))
    assert [item["componentName"] for item in attachments] == [
        "KQ001004",
        "KQ001004",
        "KQ001004",
        "KQ001004",
        "KQ001005",
        "KQ001004",
    ]


def test_registry_exposes_complete_three_step_procedure_contract():
    key = "ho-tro-chi-phi-hoa-tang-bac-ninh"
    procedure = get_procedure(key)

    assert procedure is not None
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert "maThuTucHanhChinh=1.014582" in procedure["detect"]["urlIncludes"]
    assert get_pipeline(key) is not None
    assert get_attach_pipeline(key) is not None
