"""Đăng ký lại khai sinh — số định danh/ngày cấp/nơi cấp của cha, mẹ đọc từ CHÍNH tấm CCCD.

Tờ khai viết tay chỉ chốt AI là cha/mẹ; ba ô giấy tờ tùy thân là thuộc tính của tấm thẻ nên
khi họ tên trên tờ khai khớp họ tên in trên CCCD thì thẻ là nguồn đúng theo định nghĩa.
"""

from app.pipelines.khai_sinh_dang_ky_lai.process import reason


def _declaration() -> dict:
    return {
        "name": "to-khai.pdf",
        "text": (
            "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH\n"
            "Họ, chữ đệm, tên người yêu cầu: MAN THỊ HUẾ\n"
            "Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây:\n"
            "Họ, chữ đệm, tên: MAN THỊ HUẾ\n"
            "Ngày, tháng, năm sinh: 18/11/1995 Giới tính: Nữ Dân tộc: Kinh Quốc tịch: Việt Nam\n"
            "Họ, chữ đệm, tên người mẹ: NGUYỄN THỊ HOÀ\n"
            "Năm sinh: 31/10/1976 Dân tộc: Kinh Quốc tịch: Việt Nam\n"
            "Số định danh cá nhân: 027176001999\n"
            "Họ, chữ đệm, tên người cha: MAN VĂN QUỲNH\n"
            "Năm sinh: 01/11/1972 Dân tộc: Kinh Quốc tịch: Việt Nam\n"
        ),
    }


def _mother_card() -> dict:
    return {
        "name": "cccd-me.pdf",
        "text": (
            "CĂN CƯỚC CÔNG DÂN\nSố / No.: 027176001591\n"
            "Họ và tên / Full name: NGUYỄN THỊ HOÀ\n"
            "Ngày sinh / Date of birth: 31/10/1976\n"
            "Giới tính / Sex: Nữ Quốc tịch / Nationality: Việt Nam\n"
            "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI\n"
            "Ngày, tháng, năm / Date, month, year: 06/02/2021\n"
        ),
    }


def _father_card() -> dict:
    return {
        "name": "cmnd-cha.pdf",
        "text": (
            "CHỨNG MINH NHÂN DÂN\nSố / No.: 125478963\n"
            "Họ và tên / Full name: MAN VĂN QUỲNH\n"
            "Ngày sinh / Date of birth: 01/11/1972\n"
            "Giới tính / Sex: Nam Quốc tịch / Nationality: Việt Nam\n"
            "Nơi cấp: Công an tỉnh Bắc Ninh\n"
            "Ngày cấp: 12/03/2010\n"
        ),
    }


def _context(documents: list[dict]) -> str:
    return reason._render_context("", None, documents)


def test_context_takes_parent_id_fields_from_matching_cards():
    context = _context([_declaration(), _mother_card(), _father_card()])

    mother = reason._section(context, "me")
    # Tờ khai chép nhầm số 027176001999; thẻ mới là nguồn đúng.
    assert reason._labeled_value(mother, "Số CCCD/CMND") == "027176001591"
    assert reason._labeled_value(mother, "Ngày cấp") == "06/02/2021"
    assert reason._labeled_value(mother, "Nơi cấp") == (
        "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    )
    assert reason._labeled_value(mother, "Nguồn giấy tờ tùy thân") == "cccd-me.pdf"

    father = reason._section(context, "cha")
    assert reason._labeled_value(father, "Số CCCD/CMND") == "125478963"
    assert reason._labeled_value(father, "Ngày cấp") == "12/03/2010"
    assert reason._labeled_value(father, "Nơi cấp") == "Công an tỉnh Bắc Ninh"


def test_no_matching_card_leaves_declaration_values_alone():
    context = _context([_declaration(), _mother_card()])

    father = reason._section(context, "cha")
    assert not reason._labeled_value(father, "Nguồn giấy tờ tùy thân")
    assert reason._labeled_value(father, "Ngày cấp") == ""


def test_sanitize_overwrites_agent_values_with_card_values():
    context = _context([_declaration(), _mother_card(), _father_card()])
    fields = [
        {"name": "Subject_FullName", "comp": "x-input", "value": "MAN THỊ HUẾ"},
        {"name": "Mother_FullName", "comp": "x-input", "value": "NGUYỄN THỊ HOÀ"},
        {"name": "Mother_Gender", "comp": "x-input", "value": "Nữ"},
        # Agent chép số theo tờ khai và bỏ trống ngày/nơi cấp.
        {"name": "Mother_IdNumber", "comp": "x-input", "value": "027176001999"},
        {"name": "Father_FullName", "comp": "x-input", "value": "MAN VĂN QUỲNH"},
        {"name": "Father_Gender", "comp": "x-input", "value": "Nam"},
    ]

    values = {
        field["name"]: field["value"]
        for field in reason.sanitize_extracted_fields(fields, context)
    }

    assert values["Mother_IdNumber"] == "027176001591"
    assert values["Mother_IdIssueDate"] == "06/02/2021"
    assert values["Mother_IdIssuePlace"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["Father_IdNumber"] == "125478963"
    assert values["Father_IdIssueDate"] == "12/03/2010"
    assert values["Father_IdIssuePlace"] == "Công an tỉnh Bắc Ninh"


def test_dropped_role_is_not_resurrected_by_card_override():
    context = _context([_declaration(), _mother_card(), _father_card()])
    # Thẻ ghi "Nữ" mà agent điền vào vai cha → cả vai cha bị xoá, không được mọc lại từ CCCD.
    fields = [
        {"name": "Mother_FullName", "comp": "x-input", "value": "NGUYỄN THỊ HOÀ"},
        {"name": "Mother_Gender", "comp": "x-input", "value": "Nữ"},
        {"name": "Father_FullName", "comp": "x-input", "value": "MAN VĂN QUỲNH"},
        {"name": "Father_Gender", "comp": "x-input", "value": "Nữ"},
    ]

    names = {field["name"] for field in reason.sanitize_extracted_fields(fields, context)}

    assert not any(name.startswith("Father_") for name in names)


def test_birth_date_line_is_not_mistaken_for_issue_date():
    assert reason._card_issue_date("Ngày, tháng, năm sinh: 01/11/1972") == ""
    assert reason._card_issue_date("Ngày, tháng, năm hết hạn: 01/11/2032") == ""
    assert reason._card_issue_date("Ngày, tháng, năm: 06/02/2021") == "06/02/2021"
