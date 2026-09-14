"""Kiểm thử contract thủ tục 1.012749 — hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng.

Dữ liệu lấy từ hồ sơ mẫu đã đối chiếu tay: ông Kiều Văn Hùng ủy quyền cho ông Kiều Văn Thành làm hồ
sơ và nhận tiền hỗ trợ cho bà Nguyễn Thị Thảo.
"""

from app.pipelines.ho_tro_chi_phi_hoa_tang.attach import catalog
from app.pipelines.ho_tro_chi_phi_hoa_tang.attach.planner import build_plan_items
from app.pipelines.ho_tro_chi_phi_hoa_tang.process.mapper import enrich
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

_HO_SO = {
    "NguoiNop_LoaiDoiTuong": "Cá nhân",
    "NguoiNop_HoTen": "KIỀU VĂN THÀNH",
    "NguoiNop_NgaySinh": "10/08/1975",
    "NguoiNop_GioiTinh": "Nam",
    "NguoiNop_SoDinhDanh": "001075029105",
    "NguoiNop_NgayCap": "19/04/2021",
    "NguoiNop_NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    "NguoiNop_NoiCuTru": {
        "quocGia": "Việt Nam",
        "tinh": "Quảng Ngãi",
        "xa": "Phường Đăk Bla",
        "diaChi": "Tổ dân phố Plerơhai 2",
    },
    "NguoiNop_DienThoai": "0345.449.253",
    "UyQuyen_CoGiayUyQuyen": True,
    "NguoiUyQuyen_HoTen": "KIỀU VĂN HÙNG",
    "NguoiUyQuyen_DienThoai": "0342 754 773",
    "UyQuyen_NoiDung": "Ông Kiều Văn Hùng ủy quyền cho ông Kiều Văn Thành làm hồ sơ và nhận tiền hỗ trợ",
    "UyQuyen_SoChungThuc": "1596 quyển số 1 - SCT/CK, ĐC",
    "UyQuyen_NgayChungThuc": "03/09/2026",
    "Don_CoQuanTiepNhan": "Ủy ban nhân dân phường Đăk Bla",
    "Don_NoiDungDeNghi": "Đề nghị UBND phường Đăk Bla hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng theo quy định",
    "NguoiChet_HoTen": "NGUYỄN THỊ THẢO",
    "NguoiChet_NgayChet": "18/07/2026",
    "KhaiTu_So": "50/2026/TLKT",
}


def _mapped(values: dict, options: dict | None = None):
    fields = [{"name": name, "value": value} for name, value in values.items()]
    mapped, warnings = enrich(fields, options)
    return {field["name"]: field for field in mapped}, warnings


def test_procedure_is_registered_with_both_pipelines_and_ke_khai_link():
    procedure = get_procedure("ho-tro-chi-phi-hoa-tang")
    assert procedure and procedure["hasAttachmentStep"] is True
    assert "maThuTuc=1.012749" in procedure["detect"]["urlIncludes"]
    assert get_pipeline("ho-tro-chi-phi-hoa-tang")
    assert get_attach_pipeline("ho-tro-chi-phi-hoa-tang")

    link = next(item for item in KE_KHAI_LINKS if item["key"] == "ho-tro-chi-phi-hoa-tang")
    assert link["code"] == "1.012749"
    assert link["needsAgencySelect"] is True
    assert link["submitCardIncludes"] == "Cơ quan thực hiện: UBND"


def test_same_person_fills_both_owner_and_submitter_blocks():
    fields, warnings = _mapped(_HO_SO)

    assert fields["data[ownerFullName]"]["value"] == "KIỀU VĂN THÀNH"
    assert fields["data[ownerFullName]"]["aliases"] == ["data[ownerFullname]"]
    assert fields["data[fullname]"]["value"] == "KIỀU VĂN THÀNH"
    assert fields["data[birthday]"]["value"] == "10/08/1975"
    assert fields["data[gender]"]["value"] == "Nam"
    assert fields["data[identityNumber]"]["value"] == "001075029105"
    assert fields["data[identityDate]"]["value"] == "19/04/2021"
    assert fields["data[chonDoiTuong]"]["value"] == "Cá nhân"
    assert warnings == []


def test_authorization_phone_goes_to_its_own_field_and_note_records_the_paper():
    fields, _ = _mapped(_HO_SO)

    # Hai số điện thoại của hai người khác nhau, không được đổi chỗ.
    assert fields["data[phoneNumber]"]["value"] == "0345449253"
    assert fields["data[phoneNumber1]"]["value"] == "0342754773"
    assert "KIỀU VĂN HÙNG" in fields["data[note]"]["value"]
    assert "1596 quyển số 1" in fields["data[note]"]["value"]
    assert "ủy quyền" in fields["data[noidungyeucaugiaiquyet]"]["value"]


def test_address_is_split_into_province_ward_and_detail():
    fields, _ = _mapped(_HO_SO)

    assert fields["data[province]"]["value"] == "Tỉnh Quảng Ngãi"
    assert fields["data[district]"]["value"] == "Phường Đăk Bla"
    assert fields["data[address]"]["value"] == "Tổ dân phố Plerơhai 2"
    assert fields["data[nation]"]["value"] == "Việt Nam"


def test_missing_authorization_phone_is_reported_because_field_is_required():
    values = dict(_HO_SO)
    values.pop("NguoiUyQuyen_DienThoai")
    fields, warnings = _mapped(values)

    assert "data[phoneNumber1]" not in fields
    assert any("bên ủy quyền" in warning for warning in warnings)


def test_account_holder_different_from_applicant_is_flagged_not_silently_kept():
    _, warnings = _mapped(
        _HO_SO,
        {"formContext": {"applicantFullname": "NHẬM ĐẮC ĐẠT", "applicantIdentityNumber": "001099029923"}},
    )

    assert any("khác người nộp trong hồ sơ" in warning for warning in warnings)


def test_self_submitted_dossier_leaves_authorization_fields_empty():
    values = {key: value for key, value in _HO_SO.items() if not key.startswith(("UyQuyen_", "NguoiUyQuyen_"))}
    fields, warnings = _mapped(values)

    assert "data[phoneNumber1]" not in fields
    assert "data[note]" not in fields
    assert fields["data[noidungyeucaugiaiquyet]"]["value"].endswith("theo quy định.")
    assert warnings == []


def _files(names: list[str]) -> list[dict]:
    return [{"name": name, "type": "application/pdf"} for name in names]


def test_contract_and_invoice_share_row_three_while_declaration_takes_row_one():
    files = _files(["TO_KHAI.pdf", "HOP_DONG.pdf", "HOA_DON.pdf"])
    ocr = [
        {"name": "TO_KHAI.pdf", "text": "Mẫu số 01 TỜ KHAI đề nghị hỗ trợ chi phí hỏa táng"},
        {"name": "HOP_DONG.pdf", "text": "HỢP ĐỒNG DỊCH VỤ HỎA TÁNG số 8680/2026 BÊN A BÊN B"},
        {"name": "HOA_DON.pdf", "text": "HÓA ĐƠN GIÁ TRỊ GIA TĂNG Ký hiệu 1C26TVH Mã CQT 00F57"},
    ]
    items, warnings, _ = build_plan_items(files, ocr)
    by_file = {item["fileName"]: item for item in items}

    assert by_file["TO_KHAI.pdf"]["componentIndex"] == 1
    # Dòng 3 nhận MỘT tệp đã gộp: hợp đồng trước, hóa đơn sau.
    merged = by_file["HOP_DONG.pdf"]
    assert "HOA_DON.pdf" not in by_file
    assert merged["componentIndex"] == 3
    assert merged["sourceFileIndexes"] == [1, 2]
    assert merged["documentName"] == "Hợp đồng và Hóa đơn dịch vụ hỏa táng"
    assert len(items) == 2
    assert all(item["target"] == "existing" for item in items)
    assert warnings == []


def test_death_certificate_becomes_a_new_component_and_identity_card_is_skipped():
    files = _files(["TRICH_LUC.pdf", "CCCD.pdf", "TO_KHAI.pdf"])
    ocr = [
        {"name": "TRICH_LUC.pdf", "text": "TRÍCH LỤC KHAI TỬ số 50/2026/TLKT"},
        {"name": "CCCD.pdf", "text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card 001075029105"},
        {"name": "TO_KHAI.pdf", "text": "Mẫu số 01 TỜ KHAI đề nghị hỗ trợ chi phí hỏa táng"},
    ]
    items, _, classified = build_plan_items(files, ocr)
    by_file = {item["fileName"]: item for item in items}

    assert by_file["TRICH_LUC.pdf"]["target"] == "new"
    assert by_file["TRICH_LUC.pdf"]["needsAddComponent"] is True
    # Dòng do trợ lý tự thêm: tên mang theo số trích lục để đối chiếu với mục (8) của Tờ khai.
    assert by_file["TRICH_LUC.pdf"]["componentName"] == "Trích lục khai tử số 50/2026/TLKT"
    assert "CCCD.pdf" not in by_file
    assert next(item for item in classified if item["fileName"] == "CCCD.pdf")["skipped"] is True


def test_organization_declaration_routes_to_row_two():
    files = _files(["TO_KHAI_TO_CHUC.pdf"])
    ocr = [{"name": "TO_KHAI_TO_CHUC.pdf", "text": "Mẫu số 02 TỜ KHAI đề nghị hỗ trợ chi phí hỏa táng dành cho cơ quan, tổ chức"}]
    items, _, _ = build_plan_items(files, ocr)

    assert items[0]["componentIndex"] == 2
    assert items[0]["detectedType"] == catalog.TO_KHAI_02


def test_missing_declaration_is_reported():
    files = _files(["HOP_DONG.pdf", "HOA_DON.pdf"])
    ocr = [
        {"name": "HOP_DONG.pdf", "text": "HỢP ĐỒNG DỊCH VỤ HỎA TÁNG BÊN A BÊN B"},
        {"name": "HOA_DON.pdf", "text": "HÓA ĐƠN GIÁ TRỊ GIA TĂNG Ký hiệu 1C26TVH"},
    ]
    _, warnings, _ = build_plan_items(files, ocr)

    assert any("Tờ khai" in warning for warning in warnings)
