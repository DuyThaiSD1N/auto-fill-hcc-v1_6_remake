"""Regression tests for the two-subject social-pension contract."""

import asyncio

from app.pipelines.dieu_chinh_huu_tri_xa_hoi.process import mapper, runner, schema


def _fields(values: dict) -> list[dict]:
    return [{"name": name, "value": value} for name, value in values.items()]


def _run(values: dict, options: dict | None = None):
    fields, warnings = mapper.enrich(_fields(values), options or {})
    return {field["name"]: field["value"] for field in fields}, warnings


def _context(name: str, identity: str) -> dict:
    return {
        "formContext": {
            "applicantFullname": name,
            "applicantIdentityNumber": identity,
        }
    }


def test_schema_has_exactly_two_subject_namespaces():
    assert schema.ALLOWED
    assert all(
        name.startswith(("ChuHoSo_", "NguoiNop_"))
        for name in schema.ALLOWED
    )
    assert not any(
        name.startswith(("Person", "VanBan_"))
        for name in schema.ALLOWED
    )


def test_owner_matching_ui_is_self_submission_without_duplicate_owner_block():
    data, warnings = _run(
        {
            "ChuHoSo_HoTen": "HOÀNG THỊ A",
            "ChuHoSo_SoDinhDanh": "031050000001",
            "ChuHoSo_NgaySinh": "20/10/1950",
            "ChuHoSo_GioiTinh": "Nữ",
            "ChuHoSo_NgayCap": "11/11/2021",
            "ChuHoSo_NoiCap": (
                "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
            ),
            "ChuHoSo_NoiCuTru": {
                "tinh": "Tỉnh Lai Châu",
                "xa": "Phường Đoàn Kết",
                "diaChi": "Tổ 2",
            },
            "ChuHoSo_DienThoai": "0367000001",
        },
        {
            **_context("Hoàng Thị A", "031050000001"),
            "_ocr_text": (
                "Họ tên: HOÀNG THỊ A; số: 031050000001; "
                "Ngày, tháng, năm: 11/11/2021; "
                "Số điện thoại: 0367000001"
            ),
        },
    )

    assert data["data[isOwnerDossierCheck]"] is True
    assert data["data[fullname]"] == "HOÀNG THỊ A"
    assert data["data[identityNumber]"] == "031050000001"
    assert data["data[identityDate]"] == "11/11/2021"
    assert data["data[phoneNumber]"] == "0367000001"
    assert data["data[province]"] == "Lai Châu"
    assert data["data[district]"] == "Đoàn Kết"
    assert "data[ownerFullname]" not in data
    assert not warnings


def test_different_requester_and_owner_fill_both_with_requester_phone():
    data, warnings = _run(
        {
            "ChuHoSo_HoTen": "PHÀN A TỎN",
            "ChuHoSo_SoDinhDanh": "012046001677",
            "ChuHoSo_NgaySinh": "01/01/1946",
            "ChuHoSo_GioiTinh": "Nam",
            "ChuHoSo_NgayCap": "24/06/2021",
            "ChuHoSo_NoiCap": (
                "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
            ),
            "ChuHoSo_NoiCuTru": {
                "tinh": "Lai Châu",
                "xa": "Tả Lèng",
                "diaChi": "Bản Sì Thàng",
            },
            "NguoiNop_HoTen": "Vũ Đình Thiết",
            "NguoiNop_SoDinhDanh": "040203015844",
            "NguoiNop_NgaySinh": "26/04/2003",
            "NguoiNop_NgayCap": "02/07/2021",
            "NguoiNop_NoiCuTru": {
                "tinh": "Nghệ An",
                "xa": "Tam Hợp",
                "diaChi": "xóm Long Thành",
            },
            "NguoiNop_DienThoai": "0976134251",
        },
        {
            **_context("Vũ Đình Thiết", "040203015844"),
            "_ocr_text": (
                "PHÀN A TỎN, 012046001677, Giới tính: Nam, "
                "cấp ngày 24/6/2021, Cục Cảnh sát quản lý hành chính "
                "về trật tự xã hội; "
                "Vũ Đình Thiết, 040203015844, cấp ngày 2/7/2021, "
                "số điện thoại 0976134251"
            ),
        },
    )

    assert data["data[isOwnerDossierCheck]"] is False
    assert data["data[fullname]"] == "Vũ Đình Thiết"
    assert data["data[identityNumber]"] == "040203015844"
    assert data["data[identityDate]"] == "02/07/2021"
    assert data["data[phoneNumber]"] == "0976134251"
    assert data["data[ownerFullname]"] == "PHÀN A TỎN"
    assert data["data[ownerGender]"] == "Nam"
    assert data["data[ownerIdentityDate]"] == "24/06/2021"
    # Mục II không có giới tính/nơi cấp: không được suy đoán.
    assert "data[gender]" not in data
    assert "data[idIssuePlace]" not in data
    assert not warnings


def test_unmatched_requester_is_ignored_but_owner_is_still_filled():
    data, warnings = _run(
        {
            "ChuHoSo_HoTen": "TÀN THỊ SAM",
            "ChuHoSo_NgaySinh": "25/03/1951",
            "ChuHoSo_GioiTinh": "Nữ",
            "ChuHoSo_SoDinhDanh": "012151002007",
            "ChuHoSo_NoiCuTru": {
                "tinh": "Lai Châu",
                "xa": "Tả Leng",
                "diaChi": "Bản Hồ Thầu",
            },
            "ChuHoSo_DienThoai": "0367251365",
            "NguoiNop_HoTen": "LÙ LÝ TÀI",
            "NguoiNop_SoDinhDanh": "012053002962",
            "NguoiNop_DienThoai": "0368251365",
        },
        _context("Vũ Đình Thiết", "040203015844"),
    )

    assert data["data[isOwnerDossierCheck]"] is False
    assert "data[fullname]" not in data
    assert "data[phoneNumber]" not in data
    assert data["data[ownerFullname]"] == "TÀN THỊ SAM"
    assert data["data[ownerGender]"] == "Nữ"
    assert data["data[ownerPhoneNumber]"] == "0367251365"
    assert warnings == [
        "Không xác định được người nộp khớp thông tin trên form "
        "(040203015844); không điền phần người nộp."
    ]


def test_both_ui_anchors_must_match_requester():
    data, warnings = _run(
        {
            "ChuHoSo_HoTen": "PHÀN A TỎN",
            "ChuHoSo_SoDinhDanh": "012046001677",
            "NguoiNop_HoTen": "Vũ Đình Thiết",
            "NguoiNop_SoDinhDanh": "999999999999",
        },
        _context("Vũ Đình Thiết", "040203015844"),
    )

    assert "data[fullname]" not in data
    assert data["data[ownerFullname]"] == "PHÀN A TỎN"
    assert warnings


def test_issue_date_requires_literal_ocr_evidence():
    values = {
        "ChuHoSo_HoTen": "TÀN THỊ SAM",
        "ChuHoSo_SoDinhDanh": "012151002007",
        "ChuHoSo_NgayCap": "31/03/2023",
    }
    options = {
        **_context("Vũ Đình Thiết", "040203015844"),
        "_ocr_text": (
            "Thẻ Căn cước hoặc số định danh cá nhân: "
            "012151002007, cấp ngày 07/31 2023"
        ),
    }

    data, _ = _run(values, options)
    assert "data[ownerIdentityDate]" not in data

    values["ChuHoSo_NgayCap"] = "07/03/2023"
    options["_ocr_text"] = "Thẻ Căn cước: 012151002007, cấp ngày 07/03/2023"
    data, _ = _run(values, options)
    assert data["data[ownerIdentityDate]"] == "07/03/2023"


def test_mapper_does_not_fabricate_issuer_from_issue_date():
    data, _ = _run(
        {
            "ChuHoSo_HoTen": "PHÀN A TỎN",
            "ChuHoSo_SoDinhDanh": "012046001677",
            "ChuHoSo_NgayCap": "24/06/2021",
        },
        {
            **_context("Người Nộp Khác", "040203015844"),
            "_ocr_text": "cấp ngày 24/06/2021",
        },
    )

    assert data["data[ownerIdentityDate]"] == "24/06/2021"
    assert "data[ownerIdIssuePlace]" not in data


def test_requester_context_includes_only_matched_ocr_scope():
    context = asyncio.run(
        runner._requester_context(
            [{
                "text": (
                    "Họ tên: Vũ Đình Thiết\n"
                    "Thẻ Căn cước: 040203015844"
                )
            }],
            _context("Vũ Đình Thiết", "0402 0301 5844"),
        )
    )

    assert 'result="document_match"' in context
    assert 'document="1"' in context
    assert 'section="document"' in context
    assert "Vũ Đình Thiết" in context
    assert "040203015844" in context


def test_requester_context_forbids_requester_when_ocr_has_no_anchor():
    context = asyncio.run(
        runner._requester_context(
            [{"text": "Họ tên: Người khác\nSố: 012345678901"}],
            _context("Vũ Đình Thiết", "040203015844"),
        )
    )

    assert 'result="no_document_match"' in context
    assert "bỏ trống toàn bộ NguoiNop_*" in context


def test_requester_context_focuses_section_two_and_owner_form_address():
    form_text = """Mẫu số 01
I. Thông tin người đề nghị trợ cấp hưu trí xã hội
1. Họ tên: PHÀN A TỎN
3. Số định danh: 012046001677
4. Nơi cư trú: Bản Sì Thàng, xã Tả Lèng, tỉnh Lai Châu
5. Địa chỉ liên lạc: Bản Sì Thàng, xã Tả Lèng, tỉnh Lai Châu
7. Chế độ đang hưởng: Không
II. Thông tin người giám hộ, người được ủy quyền
1. Họ tên: Vũ Đình Thiết
2. Ngày sinh: 26/04/2003
3. Số định danh: 040203015844, cấp ngày 2/7/2021
4. Địa chỉ liên hệ: xóm Long Thành, xã Tam Hợp, tỉnh Nghệ An
5. Số điện thoại: 0976134251
Tôi xin cam đoan nội dung đúng."""
    cccd_text = """CĂN CƯỚC CÔNG DÂN
Số: 012046001677
Họ tên: PHÀN A TỎN
Nơi thường trú: Bản Tả Chải, Hồ Thầu, Tam Đường, Lai Châu"""

    context = asyncio.run(
        runner._requester_context(
            [
                {"text": form_text},
                {"text": cccd_text},
            ],
            _context("Vũ Đình Thiết", "040203015844"),
        )
    )

    assert 'section="II"' in context
    assert "Vũ Đình Thiết" in context
    assert "0976134251" in context
    assert "<owner_primary_ocr>" in context
    assert "Bản Sì Thàng, xã Tả Lèng, tỉnh Lai Châu" in context
    assert "PHÀN A TỎN" not in context
    assert "012046001677" not in context
    assert "Bản Tả Chải" not in context


def test_mapper_rejects_requester_copied_only_from_ui_context():
    data, warnings = _run(
        {
            "ChuHoSo_HoTen": "TÀN THỊ SAM",
            "ChuHoSo_SoDinhDanh": "012151002007",
            "NguoiNop_HoTen": "Vũ Đình Thiết",
            "NguoiNop_SoDinhDanh": "040203015844",
        },
        {
            **_context("Vũ Đình Thiết", "040203015844"),
            "_ocr_text": (
                "Thông tin người đề nghị: TÀN THỊ SAM, "
                "số định danh 012151002007"
            ),
        },
    )

    assert "data[fullname]" not in data
    assert data["data[ownerFullname]"] == "TÀN THỊ SAM"
    assert warnings


def test_requester_optional_fields_must_exist_in_requester_evidence_block():
    data, warnings = _run(
        {
            "ChuHoSo_HoTen": "PHÀN A TỎN",
            "ChuHoSo_SoDinhDanh": "012046001677",
            "ChuHoSo_GioiTinh": "Nam",
            "ChuHoSo_NoiCap": (
                "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
            ),
            "NguoiNop_HoTen": "Vũ Đình Thiết",
            "NguoiNop_SoDinhDanh": "040203015844",
            "NguoiNop_NgaySinh": "26/04/2003",
            # Hai field này là hallucination lấy từ chủ hồ sơ.
            "NguoiNop_GioiTinh": "Nam",
            "NguoiNop_NoiCap": (
                "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
            ),
            "NguoiNop_DienThoai": "0976134251",
        },
        {
            **_context("Vũ Đình Thiết", "040203015844"),
            "_ocr_text": """CĂN CƯỚC CÔNG DÂN
Số: 012046001677
Họ tên: PHÀN A TỎN
Giới tính: Nam
CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI
---
Mẫu số 01
I. Thông tin người đề nghị trợ cấp hưu trí xã hội
Họ tên: PHÀN A TỎN
Số định danh: 012046001677
II. Thông tin người giám hộ, người được ủy quyền
Họ tên: Vũ Đình Thiết
Ngày sinh: 26/04/2003
Số định danh: 040203015844
Số điện thoại: 0976134251""",
        },
    )

    assert data["data[fullname]"] == "Vũ Đình Thiết"
    assert data["data[birthday]"] == "26/04/2003"
    assert data["data[phoneNumber]"] == "0976134251"
    assert "data[gender]" not in data
    assert "data[idIssuePlace]" not in data
    assert not warnings
