"""Kiểm thử tầng phân vai raw-text của đăng ký lại khai sinh."""

from app.pipelines.khai_sinh_dang_ky_lai.process import reason
from app.pipelines.khai_sinh_dang_ky_lai.process import runner as process_runner


def _raw_roles(
    *,
    requester="NGUYỄN THỊ HOÀ",
    requester_id="027176001591",
    child="MAN THỊ HUẾ",
    child_id="027195012144",
    mother="NGUYỄN THỊ HOÀ",
    mother_id="027176001591",
    father="MAN VĂN QUỲNH",
) -> str:
    return f"""
<nguoi_yeu_cau>
Họ tên: {requester}
Số CCCD/CMND: {requester_id}
Ngày sinh: 31/10/1976
Giới tính: Nữ
Nguồn: cccd-hoa.pdf
Căn cứ phân vai: Trùng số định danh requester_context.
Vai trò đồng thời: mẹ
</nguoi_yeu_cau>
<con>
Họ tên: {child}
Số CCCD/CMND: {child_id}
Ngày sinh: 18/11/1995
Giới tính: Nữ
Trạng thái: còn sống
Nguồn: cccd-hue.pdf
Căn cứ phân vai: Người trẻ nhất trong bộ ba có khoảng cách thế hệ hợp lý.
</con>
<me>
Họ tên: {mother}
Số CCCD/CMND: {mother_id}
Ngày sinh: 31/10/1976
Giới tính: Nữ
Trạng thái: còn sống
Nguồn: cccd-hoa.pdf
Căn cứ phân vai: Người nữ thuộc thế hệ trước con.
</me>
<cha>
Họ tên: {father}
Số CCCD/CMND: Không xác định
Ngày sinh: 01/11/1972
Giới tính: Nam
Trạng thái: đã chết
Nguồn: trich-luc-khai-tu.pdf
Căn cứ phân vai: Người nam thuộc thế hệ trước con; giấy khai tử chỉ xác nhận danh tính và trạng thái.
</cha>
<dang_ky_khai_sinh_truoc_day>
Có tài liệu khai sinh hợp lệ: Không
Nguồn: Không có
Căn cứ: Hồ sơ chỉ có CCCD và giấy khai tử.
</dang_ky_khai_sinh_truoc_day>
""".strip()


def _documents_without_birth_record() -> list[dict]:
    return [
        {
            "name": "cccd-hoa.pdf",
            "text": (
                "CĂN CƯỚC CÔNG DÂN\nSố / No.: 027176001591\n"
                "Họ và tên / Full name: NGUYỄN THỊ HOÀ\n"
                "Ngày sinh / Date of birth: 31/10/1976\n"
                "Giới tính / Sex: Nữ Quốc tịch / Nationality: Việt Nam"
            ),
        },
        {
            "name": "cccd-hue.pdf",
            "text": (
                "CĂN CƯỚC CÔNG DÂN\nSố / No.: 027195012144\n"
                "Họ và tên / Full name: MAN THỊ HUẾ\n"
                "Ngày sinh / Date of birth: 18/11/1995\n"
                "Giới tính / Sex: Nữ Quốc tịch / Nationality: Việt Nam"
            ),
        },
        {
            "name": "trich-luc-khai-tu.pdf",
            "text": (
                "Phần ghi về người được khai tử:\n"
                "Họ, chữ đệm, tên: MAN VĂN QUỲNH\n"
                "Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam\n"
                "Ngày, tháng, năm sinh: 01/11/1972"
            ),
        },
    ]


def test_render_context_keeps_three_people_in_correct_roles():
    context = reason._render_context(
        _raw_roles(),
        {
            "formContext": {
                "applicantFullname": "NGUYỄN THỊ HOÀ",
                "applicantIdentityNumber": "027176001591",
            }
        },
        _documents_without_birth_record(),
    )

    assert "<con>" in context and "MAN THỊ HUẾ" in reason._section(context, "con")
    assert "<me>" in context and "NGUYỄN THỊ HOÀ" in reason._section(context, "me")
    assert "<cha>" in context and "MAN VĂN QUỲNH" in reason._section(context, "cha")
    assert "Trạng thái: đã chết" in reason._section(context, "cha")
    assert (
        reason._labeled_value(
            reason._section(context, "dang_ky_khai_sinh_truoc_day"),
            "Có tài liệu khai sinh hợp lệ",
        )
        == "Không"
    )


def test_generation_gate_repairs_old_death_equals_parent_mistake():
    raw = """
<nguoi_yeu_cau>
Họ tên: NGUYỄN THỊ HOÀ
Số CCCD/CMND: 027176001591
Ngày sinh: 31/10/1976
Giới tính: Nữ
Nguồn: cccd-hoa.pdf
Căn cứ phân vai: Trùng requester_context
Vai trò đồng thời: không xác định
</nguoi_yeu_cau>
<con>
Họ tên: MAN VĂN QUỲNH
Số CCCD/CMND: Không xác định
Ngày sinh: 01/11/1972
Giới tính: Nam
Trạng thái: đã chết
Nguồn: trich-luc-khai-tu.pdf
Căn cứ phân vai: Bị gán nhầm từ giấy khai tử
</con>
<me>
Họ tên: MAN THỊ HUẾ
Số CCCD/CMND: 027195012144
Ngày sinh: 18/11/1995
Giới tính: Nữ
Trạng thái: còn sống
Nguồn: cccd-hue.pdf
Căn cứ phân vai: Bị gán nhầm theo giới tính
</me>
<cha>
Họ tên: MAN VĂN QUỲNH
Số CCCD/CMND: Không xác định
Ngày sinh: 01/11/1972
Giới tính: Nam
Trạng thái: đã chết
Nguồn: trich-luc-khai-tu.pdf
Căn cứ phân vai: Giấy khai tử
</cha>
<dang_ky_khai_sinh_truoc_day>
Có tài liệu khai sinh hợp lệ: Không
Nguồn: Không có
Căn cứ: Không có
</dang_ky_khai_sinh_truoc_day>
""".strip()

    context = reason._render_context(raw, {}, _documents_without_birth_record())

    assert "MAN THỊ HUẾ" in reason._section(context, "con")
    assert "NGUYỄN THỊ HOÀ" in reason._section(context, "me")
    assert "MAN VĂN QUỲNH" in reason._section(context, "cha")


def test_sanitizer_does_not_borrow_ethnicity_between_people():
    context = reason._render_context(
        _raw_roles(),
        {},
        _documents_without_birth_record(),
    )
    fields = [
        {"name": "Subject_FullName", "value": "MAN THỊ HUẾ"},
        {"name": "Subject_Ethnicity", "value": "Kinh"},
        {"name": "Subject_Nationality", "value": "Việt Nam"},
        {"name": "Mother_FullName", "value": "NGUYỄN THỊ HOÀ"},
        {"name": "Mother_Ethnicity", "value": "Kinh"},
        {"name": "Mother_Nationality", "value": "Việt Nam"},
        {"name": "Father_FullName", "value": "MAN VĂN QUỲNH"},
        {"name": "Father_Ethnicity", "value": "Kinh"},
        {"name": "Father_Nationality", "value": "Việt Nam"},
    ]

    result = reason.sanitize_extracted_fields(fields, context)
    names = {field["name"] for field in result}

    assert "Subject_Ethnicity" not in names
    assert "Mother_Ethnicity" not in names
    assert "Father_Ethnicity" in names
    assert "Subject_Nationality" in names
    assert "Mother_Nationality" in names
    assert "Father_Nationality" in names


def test_sanitizer_drops_wrong_people_and_death_registration_metadata():
    context = reason._render_context(
        _raw_roles(),
        {},
        _documents_without_birth_record(),
    )
    fields = [
        {"name": "Subject_FullName", "value": "MAN VĂN QUỲNH"},
        {"name": "Subject_BirthDate", "value": "01/11/1972"},
        {"name": "Father_FullName", "value": "MAN VĂN QUỲNH"},
        {"name": "Father_BirthDateOrYear", "value": "1972"},
        {"name": "Mother_FullName", "value": "MAN THỊ HUẾ"},
        {"name": "Mother_BirthDateOrYear", "value": "18/11/1995"},
        {"name": "PreviousRegistration_Number", "value": "07"},
        {"name": "PreviousRegistration_Date", "value": "24/02/2017"},
    ]

    result = reason.sanitize_extracted_fields(fields, context)
    values = {field["name"]: field["value"] for field in result}

    assert values == {
        "Father_FullName": "MAN VĂN QUỲNH",
        "Father_BirthDateOrYear": "1972",
    }


def test_valid_birth_document_allows_previous_registration_fields():
    documents = _documents_without_birth_record() + [
        {
            "name": "ban-sao-khai-sinh.pdf",
            "text": "GIẤY KHAI SINH\nHọ, chữ đệm, tên: MAN THỊ HUẾ\nSố: 15",
        }
    ]
    context = reason._render_context(_raw_roles(), {}, documents)
    fields = [
        {"name": "Subject_FullName", "value": "MAN THỊ HUẾ"},
        {"name": "PreviousRegistration_Number", "value": "15"},
        {"name": "PreviousRegistration_Date", "value": "20/11/1995"},
    ]

    result = reason.sanitize_extracted_fields(fields, context)
    assert {field["name"] for field in result} == {
        "Subject_FullName",
        "PreviousRegistration_Number",
        "PreviousRegistration_Date",
    }


def test_same_person_cannot_be_both_child_and_father():
    raw = _raw_roles(father="MAN THỊ HUẾ")
    context = reason._render_context(raw, {}, _documents_without_birth_record())

    assert "Không xác định" in reason._section(context, "cha")
    result = reason.sanitize_extracted_fields(
        [
            {"name": "Subject_FullName", "value": "MAN THỊ HUẾ"},
            {"name": "Father_FullName", "value": "MAN THỊ HUẾ"},
        ],
        context,
    )
    assert [field["name"] for field in result] == ["Subject_FullName"]


def test_requester_mismatch_does_not_destroy_family_roles():
    context = reason._render_context(
        _raw_roles(requester="NGƯỜI KHÁC", requester_id="012345678901"),
        {
            "formContext": {
                "applicantFullname": "NGUYỄN THỊ HOÀ",
                "applicantIdentityNumber": "027176001591",
            }
        },
        _documents_without_birth_record(),
    )

    assert "Không xác định" in reason._section(context, "nguoi_yeu_cau")
    assert "MAN THỊ HUẾ" in reason._section(context, "con")
    assert "MAN VĂN QUỲNH" in reason._section(context, "cha")


async def test_build_context_uses_raw_text_agent(monkeypatch):
    captured = {}

    async def _chat_text(messages, **kwargs):
        captured["messages"] = messages
        captured["kwargs"] = kwargs
        return _raw_roles()

    monkeypatch.setattr(reason.client, "chat_text", _chat_text)
    context = await reason.build_context(
        _documents_without_birth_record(),
        {
            "formContext": {
                "applicantFullname": "NGUYỄN THỊ HOÀ",
                "applicantIdentityNumber": "027176001591",
            }
        },
    )

    assert captured["kwargs"]["temperature"] == 0
    assert "không trả JSON" in captured["messages"][0]["content"]
    assert "<phan_vai_da_xac_dinh>" in context
    assert "MAN THỊ HUẾ" in reason._section(context, "con")


async def test_process_runner_sanitizes_before_mapper(monkeypatch):
    context = reason._render_context(
        _raw_roles(),
        {},
        _documents_without_birth_record(),
    )
    extracted = [
        {"name": "Subject_FullName", "value": "MAN VĂN QUỲNH"},
        {"name": "Father_FullName", "value": "MAN VĂN QUỲNH"},
        {"name": "PreviousRegistration_Number", "value": "07"},
    ]
    seen = {}

    async def _compact_run(*_args, **_kwargs):
        return {
            "fields": extracted,
            "reasoning_context": context,
            "errors": [],
        }

    def _mapper_enrich(fields, _options):
        seen["fields"] = fields
        return fields

    monkeypatch.setattr(process_runner.runner, "run", _compact_run)
    monkeypatch.setattr(process_runner.mapper, "enrich", _mapper_enrich)

    result = await process_runner.run({}, {})

    assert seen["fields"] == [{"name": "Father_FullName", "value": "MAN VĂN QUỲNH"}]
    assert result["fields"] == seen["fields"]


def _context_with_shared_parent_id(mother_id: str = "024075019811") -> str:
    """Tờ khai ghi mục "Giấy tờ tùy thân" của MẸ bằng đúng số CCCD của CHA.

    Agent phân vai chép y nguyên nên <me> và <cha> mang cùng một số định danh.
    """
    return (
        "<phan_vai_da_xac_dinh>\n"
        "<nguoi_yeu_cau>\n"
        "Họ tên: Dương Văn Lĩnh\nSố CCCD/CMND: 024075019811\nNgày sinh: 20/8/1975\n"
        "Giới tính: Nam\nVai trò đồng thời: cha\n"
        "</nguoi_yeu_cau>\n"
        "<con>\n"
        "Họ tên: Dương Văn Ánh\nSố CCCD/CMND: 024200006467\nNgày sinh: 23/4/2000\n"
        "Giới tính: Nam\nTrạng thái: còn sống\nDân tộc: Kinh\nQuốc tịch: Việt Nam\n"
        "</con>\n"
        "<me>\n"
        f"Họ tên: Hà Thị Thu\nSố CCCD/CMND: {mother_id}\nNgày sinh: 20/8/1975\n"
        "Giới tính: Nữ\nTrạng thái: còn sống\nDân tộc: Kinh\nQuốc tịch: Việt Nam\n"
        "</me>\n"
        "<cha>\n"
        "Họ tên: Dương Văn Lĩnh\nSố CCCD/CMND: 024075019811\nNgày sinh: 20/8/1975\n"
        "Giới tính: Nam\nTrạng thái: còn sống\nDân tộc: Kinh\nQuốc tịch: Việt Nam\n"
        "</cha>\n"
        "</phan_vai_da_xac_dinh>"
    )


def _mother_fields(full_name: str = "Hà Thị Thư") -> list[dict]:
    return [
        {"name": "Subject_FullName", "value": "Dương Văn Ánh"},
        {"name": "Subject_IdNumber", "value": "024200006467"},
        {"name": "Father_FullName", "value": "Dương Văn Lĩnh"},
        {"name": "Father_IdNumber", "value": "024075019811"},
        {"name": "Mother_FullName", "value": full_name},
        {"name": "Mother_IdNumber", "value": "024177008469"},
        {"name": "Mother_BirthDateOrYear", "value": "20/08/1977"},
    ]


def test_sanitizer_keeps_mother_when_role_block_copied_father_id():
    # Số định danh trong <me> là của CHA nên không dùng làm mỏ neo được; họ tên (bỏ dấu:
    # "ha thi thu") vẫn khớp nên khối mẹ PHẢI được giữ với số CCCD thật của mẹ.
    result = reason.sanitize_extracted_fields(
        _mother_fields(), _context_with_shared_parent_id()
    )
    values = {field["name"]: field["value"] for field in result}

    assert values["Mother_FullName"] == "Hà Thị Thư"
    assert values["Mother_IdNumber"] == "024177008469"
    assert values["Father_IdNumber"] == "024075019811"
    assert values["Subject_FullName"] == "Dương Văn Ánh"


def test_sanitizer_still_drops_other_person_when_role_id_is_shared():
    # Số bị dùng chung thì quay về so họ tên — người khác tên vẫn phải bị loại.
    result = reason.sanitize_extracted_fields(
        _mother_fields(full_name="Nguyễn Thị Khác"), _context_with_shared_parent_id()
    )

    assert not any(field["name"].startswith("Mother_") for field in result)


def test_sanitizer_keeps_strict_id_check_when_role_id_is_unique():
    # Số định danh của <me> là riêng của mẹ → vẫn so CHẶT theo số, lệch là loại.
    result = reason.sanitize_extracted_fields(
        _mother_fields(), _context_with_shared_parent_id(mother_id="024199999999")
    )

    assert not any(field["name"].startswith("Mother_") for field in result)


# ---------------------------------------------------------------------------
# Tờ khai viết tay ghi tên cha lệch MỘT tiếng so với CCCD ("Vũ Huy Hoàn" → "Vũ Huy Hoà"),
# lệch xong lại trùng đúng tên con. Trước đây khối <cha> bị coi là "trùng chính người đã
# được phân vai là con" rồi xoá trắng, kéo theo toàn bộ Father_* bị sanitize loại bỏ →
# biểu mẫu bỏ trống mục IV (họ tên cha, số định danh, nơi cư trú "Đã chết").
# ---------------------------------------------------------------------------

_TO_KHAI_CHA_LECH_TEN = """TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH
Họ, chữ đệm, tên người yêu cầu: VŨ HUY HÒA
Quan hệ với người được khai sinh: Bản thân
Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây:
Họ, chữ đệm, tên: VŨ HUY HÒA
Ngày, tháng, năm sinh: 28/02/1991
Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam
Họ, chữ đệm, tên người mẹ: Ngô Thị Hồng Thiệu
Năm sinh: (5) 1962 Dân tộc: Kinh Quốc tịch: Việt Nam
Nơi cư trú: (2) TDP Xuân Vũ
Họ, chữ đệm, tên người cha: Vũ Huy Hoà
Năm sinh: (5) 1958 Dân tộc: Kinh Quốc tịch: Việt Nam
Nơi cư trú: (2) Đã chết
Đã đăng ký khai sinh tại: (6) UBND xã Ninh Vân
"""

_CCCD_CHA_HOAN = """CĂN CƯỚC CÔNG DÂN
Citizen Identity Card
Số / No.: 037058009458
Họ và tên / Full name: VŨ HUY HOÀN
Ngày sinh / Date of birth: 01/01/1958
Giới tính / Sex: Nam Quốc tịch / Nationality: Việt Nam
"""

_CCCD_CON_HOA = """CĂN CƯỚC CÔNG DÂN
Citizen Identity Card
Số / No.: 037091015133
Họ và tên / Full name: VŨ HUY HÒA
Ngày sinh / Date of birth: 28/02/1991
Giới tính / Sex: Nam Quốc tịch / Nationality: Việt Nam
"""

_RAW_CHA_LECH_TEN = """
<nguoi_yeu_cau>
Họ tên: VŨ HUY HÒA
Số CCCD/CMND: 037091015133
Ngày sinh: 28/02/1991
Giới tính: Nam
Nguồn: to-khai.pdf
Căn cứ phân vai: Tờ khai ghi quan hệ Bản thân.
Vai trò đồng thời: con
</nguoi_yeu_cau>
<con>
Họ tên: VŨ HUY HÒA
Số CCCD/CMND: 037091015133
Ngày sinh: 28/02/1991
Giới tính: Nam
Trạng thái: còn sống
Nguồn: cccd-con.pdf
Căn cứ phân vai: Tờ khai chỉ đích danh người được đăng ký lại.
</con>
<me>
Họ tên: NGÔ THỊ HỒNG THÊU
Số CCCD/CMND: 037162011511
Ngày sinh: 01/01/1962
Giới tính: Nữ
Trạng thái: còn sống
Nguồn: cccd-me.pdf
Căn cứ phân vai: Tờ khai ghi tên người mẹ.
</me>
<cha>
Họ tên: VŨ HUY HOÀN
Số CCCD/CMND: 037058009458
Ngày sinh: 01/01/1958
Giới tính: Nam
Trạng thái: đã chết
Nguồn: cccd-cha.pdf
Căn cứ phân vai: Tờ khai ghi tên người cha; trích lục khai tử xác nhận đã chết.
</cha>
""".strip()


def _documents_cha_lech_ten() -> list[dict]:
    return [
        {"name": "to-khai.pdf", "text": _TO_KHAI_CHA_LECH_TEN},
        {"name": "cccd-cha.pdf", "text": _CCCD_CHA_HOAN},
        {"name": "cccd-con.pdf", "text": _CCCD_CON_HOA},
    ]


def _context_cha_lech_ten() -> str:
    return reason._render_context(
        _RAW_CHA_LECH_TEN, {}, _documents_cha_lech_ten()
    )


def test_names_align_tolerates_one_syllable_ocr_drift():
    assert reason._names_align("Vũ Huy Hoà", "VŨ HUY HOÀN")
    assert reason._names_align("Ngô Thị Hồng Thiệu", "NGÔ THỊ HỒNG THÊU")
    # Lệch quá một tiếng, lệch quá một ký tự, hoặc khác số tiếng thì vẫn là hai người.
    assert not reason._names_align("Vũ Huy Hoà", "Vũ Văn Hoàn")
    assert not reason._names_align("Vũ Huy Hoà", "Vũ Huy Hoàng")
    assert not reason._names_align("Vũ Huy Hoà", "Vũ Huy")


def test_cha_survives_when_declaration_name_drifts_into_child_name():
    section = reason._section(_context_cha_lech_ten(), "cha")

    # Tên tờ khai trùng tên con nhưng năm sinh 1958 ≠ 1991 → KHÔNG được xoá khối cha.
    assert "Không xác định" not in reason._role_name(section)
    # CCCD của đúng người cha phải được bù vào, không phải CCCD của con.
    assert reason._role_id(section) == "037058009458"
    assert "đã chết" in section


def test_sanitizer_keeps_father_when_declaration_name_drifts():
    fields = [
        {"name": "Subject_FullName", "value": "VŨ HUY HÒA"},
        {"name": "Subject_BirthDate", "value": "28/02/1991"},
        {"name": "Mother_FullName", "value": "NGÔ THỊ HỒNG THÊU"},
        {"name": "Mother_IdNumber", "value": "037162011511"},
        {"name": "Father_FullName", "value": "VŨ HUY HOÀN"},
        {"name": "Father_IdNumber", "value": "037058009458"},
        {"name": "Father_BirthDateOrYear", "value": "01/01/1958"},
    ]

    values = {
        field["name"]: field["value"]
        for field in reason.sanitize_extracted_fields(fields, _context_cha_lech_ten())
    }

    assert values["Father_FullName"] == "VŨ HUY HOÀN"
    assert values["Father_IdNumber"] == "037058009458"
    assert values["Mother_FullName"] == "NGÔ THỊ HỒNG THÊU"
    assert values["Subject_FullName"] == "VŨ HUY HÒA"
