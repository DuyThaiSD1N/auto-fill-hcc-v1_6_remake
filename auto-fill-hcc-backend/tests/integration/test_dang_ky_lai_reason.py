"""Kiểm thử tầng phân vai raw-text của đăng ký lại khai sinh."""

from app.pipelines.khai_sinh_dang_ky_lai.process import mapper, reason
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


def _declaration_with_two_names_for_mother() -> list[dict]:
    """Hồ sơ thật req_4e634f6f475f: tờ khai ghi mẹ "Đỗ Thị Canh", bản cam đoan ghi "Đào Thị An"."""
    return [
        {
            "name": "ho-so-dang-ky-lai.pdf",
            "text": (
                "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH\n"
                "Kính gửi: UBND xã Hiệp Hòa, tỉnh Bắc Ninh\n"
                "Họ, chữ đệm, tên người yêu cầu: Nguyễn Văn Hoà\n"
                "Ngày, tháng, năm sinh: 21-5-1965\n"
                "Nơi cư trú: Thôn Đông Vân, xã Hiệp Hòa, tỉnh Bắc Ninh\n"
                "Giấy tờ tùy thân: CCCD/CC số: 024065014018, Bộ Công an cấp ngày: 22/4/2025\n"
                "Quan hệ với người được khai sinh: bản thân\n"
                "Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây:\n"
                "Họ, chữ đệm, tên: Nguyễn Văn Hoà\n"
                "Ngày, tháng, năm sinh: 21-5-1965\n"
                "Giới tính: nam Dân tộc: Kinh Quốc tịch: Việt Nam\n"
                "Nơi sinh: Thôn Đông Lỗ, xã Hiệp Hòa, tỉnh Bắc Ninh\n"
                "Quê quán: Thôn Đông Lỗ, xã Hiệp Hòa, tỉnh Bắc Ninh\n"
                "Họ, chữ đệm, tên người mẹ: Đỗ Thị Canh\n"
                "Năm sinh: 1944 Dân tộc: Kinh Quốc tịch: Việt Nam\n"
                "Nơi cư trú: Đã chết\n"
                "Giấy tờ tùy thân:\n"
                "Họ, chữ đệm, tên người cha: Nguyễn Văn Hạ\n"
                "Năm sinh: 1942 Dân tộc: Kinh Quốc tịch: Việt Nam\n"
                "Nơi cư trú: Đã chết\n"
                "Giấy tờ tùy thân:\n"
            ),
        },
        {
            "name": "ban-cam-doan.pdf",
            "text": (
                "BẢN CAM ĐOAN\n"
                "Họ, chữ đệm, tên mẹ: Đào Thị An Năm sinh 1944\n"
                "Họ, chữ đệm, tên cha: Nguyễn Văn Hòa Năm sinh 1942\n"
            ),
        },
    ]


def _fields_with_mother_read_from_affidavit() -> list[dict]:
    """Agent lấy tên cha theo tờ khai nhưng tên mẹ lại theo bản cam đoan."""
    return [
        {"name": "Subject_FullName", "comp": "raw", "value": "NGUYỄN VĂN HÒA"},
        {"name": "Subject_BirthDate", "comp": "raw", "value": "21/05/1965"},
        {"name": "Father_FullName", "comp": "raw", "value": "NGUYỄN VĂN HẠ"},
        {"name": "Father_BirthDateOrYear", "comp": "raw", "value": "1942"},
        {"name": "Mother_FullName", "comp": "raw", "value": "ĐÀO THỊ AN"},
        {"name": "Mother_BirthDateOrYear", "comp": "raw", "value": "1944"},
    ]


def test_parent_dropped_for_name_mismatch_is_rebuilt_from_declaration():
    context = reason._render_context("", None, _declaration_with_two_names_for_mother())

    result = reason.sanitize_extracted_fields(
        _fields_with_mother_read_from_affidavit(), context
    )
    by_name = {field["name"]: field for field in result}

    # Vai mẹ bị loại vì lệch tên, nhưng tờ khai chốt vai nên dựng lại theo tờ khai thay vì bỏ trống.
    assert by_name["Mother_FullName"]["value"] == "Đỗ Thị Canh"
    assert by_name["Mother_FullName"]["default"] is True
    assert by_name["Mother_BirthDateOrYear"]["value"] == "1944"
    # Cha khớp tờ khai thì giữ nguyên giá trị agent trích và KHÔNG bị đánh dấu mặc định.
    assert by_name["Father_FullName"]["value"] == "NGUYỄN VĂN HẠ"
    assert "default" not in by_name["Father_FullName"]


def test_rebuilt_parent_block_reaches_ui_fields_marked_default():
    context = reason._render_context("", None, _declaration_with_two_names_for_mother())

    fields = reason.sanitize_extracted_fields(
        _fields_with_mother_read_from_affidavit(), context
    )
    ui = {
        field["name"]: field
        for field in mapper.enrich(fields, {"_reasoning_context": context})
    }

    assert ui["HoTenMeKS"]["value"] == "ĐỖ THỊ CANH"
    assert ui["HoTenMeKS"]["default"] is True
    assert ui["NamSinhMeKS"]["value"] == "1944"
    # Tờ khai ghi "Nơi cư trú: Đã chết" nên khối mẹ phải tick "Khác" rồi ghi chữ vào ô tự do.
    assert ui["MeNoiCuTru"]["value"] == "Khác"
    assert ui["MeNoiCuTru_NuocNgoai"]["value"] == "Đã chết"
    assert ui["HoTenChaKS"]["value"] == "NGUYỄN VĂN HẠ"
    assert "default" not in ui["HoTenChaKS"]


def test_parent_from_non_declaration_source_is_not_rebuilt():
    """Khối vai suy từ giấy khai tử/thế hệ không đủ chắc để lật lại kết quả trích xuất."""
    context = reason._render_context(
        _raw_roles(), {}, _documents_without_birth_record()
    )

    result = reason.sanitize_extracted_fields(
        [{"name": "Father_FullName", "comp": "raw", "value": "TRẦN VĂN LẠ"}], context
    )

    assert not [field for field in result if field["name"].startswith("Father_")]
