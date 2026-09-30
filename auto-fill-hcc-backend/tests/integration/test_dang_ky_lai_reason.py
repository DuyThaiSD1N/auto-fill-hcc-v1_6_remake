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


# req_e30f70b0d62b: trang 2 dồn ba MẶT TRƯỚC (con, mẹ, cha), trang 3 dồn ba MẶT SAU. Mặt sau không
# in họ tên — chỉ dải MRZ mới cho biết đó là thẻ của ai.
_STACKED_CARDS_OCR = """
───── Trang 1/2 ─────
CĂN CƯỚC CÔNG DÂN
Citizen Identity Card
Số / No.: 027192010120
Họ và tên / Full name:
NGUYỄN THỊ TRANG
Ngày sinh / Date of birth: 14/07/1992
Giới tính / Sex: Nữ Quốc tịch / Nationality: Việt Nam
Có giá trị đến: 14/07/2032

CĂN CƯỚC
IDENTITY CARD
Số định danh cá nhân / Personal identification number:
027165009519
Họ, chữ đệm và tên khai sinh / Full name:
NGUYỄN THỊ AN
Ngày, tháng, năm sinh / Date of birth: 05/06/1965
Giới tính / Sex: Nữ

CĂN CƯỚC CÔNG DÂN
Citizen Identity Card
Số / No.: 027062009749
Họ và tên / Full name:
NGUYỄN VĂN DẦN
Ngày sinh / Date of birth: 01/01/1962
Giới tính / Sex: Nam Quốc tịch / Nationality: Việt Nam

───── Trang 2/2 ─────
Đặc điểm nhận dạng / Personal identification:
Ngày, tháng, năm / Date, month, year: 09/05/2021
CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI
IDVNM1920101202027192010120<<5
9207145F3207143VNM<<<<<<<<<<<<<<4
NGUYEN<<THI<TRANG<<<<<<<<<<<<<<<
Nơi cư trú / Place of residence Khu Sơn Trung
Ngày, tháng, năm cấp / Date of issue:
06/06/2025
Ngày, tháng, năm hết hạn / Date of expiry:
Không thời hạn
BỘ CÔNG AN/MINISTRY OF PUBLIC SECURITY
IDVNM1650095196027165009519<<9
6506054F9912315VNM<<<<<<<<<<<<<<2
NGUYEN<<THI<AN<<<<<<<<<<<<<<<<
Đặc điểm nhận dạng / Personal identification:
Ngày, tháng, năm / Date, month, year: 09/05/2021
CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI
IDVNMO620097499027062009749<<2
6201016M9912315VNM<<<<<<<<<<<<<<2
NGUYEN<<VAN<DAN<<<<<<<<<<<<<<<<
""".strip()


def test_card_backs_pair_by_mrz_not_page_order():
    backs = reason._mrz_card_backs([{"name": "ho-so.pdf", "text": _STACKED_CARDS_OCR}])

    cuc = "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert backs == {
        "027192010120": {"issue_date": "09/05/2021", "issue_place": cuc},
        "027165009519": {"issue_date": "06/06/2025", "issue_place": "Bộ Công an"},
        "027062009749": {"issue_date": "09/05/2021", "issue_place": cuc},
    }


def test_sanitizer_fixes_issue_date_swapped_between_child_and_mother():
    raw = _raw_roles(
        requester="NGUYỄN THỊ TRANG",
        requester_id="027192010120",
        child="NGUYỄN THỊ TRANG",
        child_id="027192010120",
        mother="NGUYỄN THỊ AN",
        mother_id="027165009519",
        father="NGUYỄN VĂN DẦN",
    )
    context = reason._render_context(raw, {}, [{"name": "ho-so.pdf", "text": _STACKED_CARDS_OCR}])
    # Đúng output agent của req_e30f70b0d62b: ngày cấp/nơi cấp con và mẹ bị tráo.
    fields = [
        {"name": "Subject_FullName", "value": "NGUYỄN THỊ TRANG"},
        {"name": "Subject_IdNumber", "value": "027192010120"},
        {"name": "Subject_IdIssueDate", "value": "06/06/2025"},
        {"name": "Subject_IdIssuePlace", "value": "Bộ Công an"},
        {"name": "Mother_FullName", "value": "NGUYỄN THỊ AN"},
        {"name": "Mother_Gender", "value": "Nữ"},
        {"name": "Mother_IdNumber", "value": "027165009519"},
        {"name": "Mother_IdIssueDate", "value": "09/05/2021"},
        {"name": "Mother_IdIssuePlace", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    ]

    values = {field["name"]: field["value"] for field in reason.sanitize_extracted_fields(fields, context)}

    assert values["Subject_IdIssueDate"] == "09/05/2021"
    assert values["Subject_IdIssuePlace"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["Mother_IdIssueDate"] == "06/06/2025"
    assert values["Mother_IdIssuePlace"] == "Bộ Công an"


# Tờ khai ghi cha/mẹ một đằng, hai tấm CCCD nộp kèm lại là của hai người khác hẳn (lệch cả tên lẫn số).
_MISMATCHED_PARENT_CARDS_DOCS = [
    {
        "name": "to-khai.pdf",
        "text": (
            "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH\n"
            "Họ, chữ đệm, tên người yêu cầu: TRẦN VĂN BÌNH\n"
            "Quan hệ với người được khai sinh: Bản thân\n"
            "Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây:\n"
            "Họ, chữ đệm, tên: TRẦN VĂN BÌNH\n"
            "Ngày, tháng, năm sinh: 10/05/1990\n"
            "Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam\n"
            "Họ, chữ đệm, tên người mẹ: LÊ THỊ HOA\n"
            "Năm sinh: 1965 Dân tộc: Kinh Quốc tịch: Việt Nam\n"
            "Giấy tờ tùy thân: CCCD số 068165002222\n"
            "Họ, chữ đệm, tên người cha: TRẦN VĂN AN\n"
            "Năm sinh: 1962 Dân tộc: Kinh Quốc tịch: Việt Nam\n"
            "Giấy tờ tùy thân: CCCD số 068062003333\n"
            "Tôi cam đoan những nội dung khai trên đây là đúng sự thật"
        ),
    },
    {
        "name": "cccd-1.pdf",
        "text": (
            "CĂN CƯỚC CÔNG DÂN\nSố / No.: 068062009999\nHọ và tên / Full name: PHẠM VĂN KHÁNH\n"
            "Ngày sinh / Date of birth: 01/01/1962\nGiới tính / Sex: Nam Quốc tịch / Nationality: Việt Nam"
        ),
    },
    {
        "name": "cccd-2.pdf",
        "text": (
            "CĂN CƯỚC CÔNG DÂN\nSố / No.: 068165008888\nHọ và tên / Full name: ĐỖ THỊ MAI\n"
            "Ngày sinh / Date of birth: 02/02/1965\nGiới tính / Sex: Nữ Quốc tịch / Nationality: Việt Nam"
        ),
    },
]


def _mismatched_parent_cards_context() -> str:
    raw = _raw_roles(
        requester="TRẦN VĂN BÌNH",
        requester_id="068090001111",
        child="TRẦN VĂN BÌNH",
        child_id="068090001111",
        mother="ĐỖ THỊ MAI",
        mother_id="068165008888",
        father="PHẠM VĂN KHÁNH",
    )
    return reason._render_context(raw, {}, _MISMATCHED_PARENT_CARDS_DOCS)


def test_parents_take_cards_by_generation_when_declaration_mismatches_all_cards():
    context = _mismatched_parent_cards_context()
    # Tờ khai lệch cả tên lẫn số với mọi CCCD, nhưng thẻ nam 1962 / nữ 1965 hợp tuổi với con 1990
    # → chốt thẻ theo thế hệ: nhân thân theo thẻ, tô vàng.
    assert reason._labeled_value(reason._section(context, "cha"), reason._GENERATION_CARD_LABEL)
    assert reason._labeled_value(reason._section(context, "me"), reason._GENERATION_CARD_LABEL)
    fields = [
        {"name": "Subject_FullName", "value": "TRẦN VĂN BÌNH"},
        {"name": "Father_FullName", "value": "PHẠM VĂN KHÁNH"},
        {"name": "Father_IdNumber", "value": "068062009999"},
        {"name": "Mother_FullName", "value": "ĐỖ THỊ MAI"},
        {"name": "Mother_IdNumber", "value": "068165008888"},
    ]

    result = reason.sanitize_extracted_fields(fields, context)
    values = {field["name"]: field["value"] for field in result}
    defaults = {field["name"] for field in result if field.get("default")}

    assert values["Father_FullName"] == "PHẠM VĂN KHÁNH"
    assert values["Father_IdNumber"] == "068062009999"
    assert values["Mother_FullName"] == "ĐỖ THỊ MAI"
    assert values["Mother_IdNumber"] == "068165008888"
    assert {"Father_FullName", "Father_IdNumber", "Mother_FullName", "Mother_IdNumber"} <= defaults


def test_generation_card_overrides_declared_identity_extracted_by_agent():
    context = _mismatched_parent_cards_context()
    # Agent trích tên theo tờ khai → nhân thân vẫn đặt lại theo thẻ đã chốt theo thế hệ.
    fields = [
        {"name": "Subject_FullName", "value": "TRẦN VĂN BÌNH"},
        {"name": "Father_FullName", "value": "TRẦN VĂN AN"},
        {"name": "Father_IdNumber", "value": "068062003333"},
        {"name": "Mother_FullName", "value": "LÊ THỊ HOA"},
    ]

    values = {field["name"]: field["value"] for field in reason.sanitize_extracted_fields(fields, context)}

    assert values["Father_FullName"] == "PHẠM VĂN KHÁNH"
    assert values["Father_IdNumber"] == "068062009999"
    assert values["Mother_FullName"] == "ĐỖ THỊ MAI"
    assert values["Mother_IdNumber"] == "068165008888"


def _cards_out_of_generation_context() -> str:
    # Thẻ lạ lệch cả tên lẫn số VÀ không hợp tuổi với con (sinh sau con) → không chốt được, theo tờ khai.
    docs = [
        _MISMATCHED_PARENT_CARDS_DOCS[0],
        {"name": "cccd-1.pdf", "text": _card("068095009999", "PHẠM VĂN KHÁNH", "01/01/1995", "Nam")},
        {"name": "cccd-2.pdf", "text": _card("068196008888", "ĐỖ THỊ MAI", "02/02/1996", "Nữ")},
    ]
    return reason._render_context(_raw_roles(child="TRẦN VĂN BÌNH", child_id="068090001111"), {}, docs)


def test_parents_fall_back_to_declaration_when_cards_do_not_fit_generation():
    context = _cards_out_of_generation_context()
    fields = [
        {"name": "Subject_FullName", "value": "TRẦN VĂN BÌNH"},
        {"name": "Father_FullName", "value": "PHẠM VĂN KHÁNH"},
        {"name": "Father_IdNumber", "value": "068062009999"},
        {"name": "Mother_FullName", "value": "ĐỖ THỊ MAI"},
        {"name": "Mother_IdNumber", "value": "068165008888"},
    ]

    result = reason.sanitize_extracted_fields(fields, context)
    values = {field["name"]: field["value"] for field in result}
    defaults = {field["name"] for field in result if field.get("default")}

    assert values["Father_FullName"] == "TRẦN VĂN AN"
    assert values["Father_IdNumber"] == "068062003333"
    assert values["Mother_FullName"] == "LÊ THỊ HOA"
    assert values["Mother_IdNumber"] == "068165002222"
    assert {"Father_FullName", "Father_IdNumber", "Mother_FullName", "Mother_IdNumber"} <= defaults


def test_parent_id_from_foreign_card_falls_back_to_declaration():
    context = _cards_out_of_generation_context()
    # Tên theo tờ khai nhưng số + ngày cấp chép từ thẻ của người khác (mã năm sinh 1995 ≠ cha 1962);
    # mẹ bị bỏ trống số.
    fields = [
        {"name": "Subject_FullName", "value": "TRẦN VĂN BÌNH"},
        {"name": "Father_FullName", "value": "TRẦN VĂN AN"},
        {"name": "Father_IdNumber", "value": "068095009999"},
        {"name": "Father_IdIssueDate", "value": "01/01/2021"},
        {"name": "Mother_FullName", "value": "LÊ THỊ HOA"},
    ]

    result = reason.sanitize_extracted_fields(fields, context)
    values = {field["name"]: field["value"] for field in result}

    assert values["Father_IdNumber"] == "068062003333"
    assert "Father_IdIssueDate" not in values
    assert values["Mother_FullName"] == "LÊ THỊ HOA"
    assert values["Mother_IdNumber"] == "068165002222"


def test_parent_card_matching_name_is_not_flagged_as_foreign():
    # Thẻ của cha đúng tên tờ khai (số lệch do OCR tờ khai) → vẫn là thẻ của cha, không fallback.
    docs = [
        _MISMATCHED_PARENT_CARDS_DOCS[0],
        {
            "name": "cccd-1.pdf",
            "text": _MISMATCHED_PARENT_CARDS_DOCS[1]["text"].replace("PHẠM VĂN KHÁNH", "TRẦN VĂN AN"),
        },
        _MISMATCHED_PARENT_CARDS_DOCS[2],
    ]
    context = reason._render_context(_raw_roles(child="TRẦN VĂN BÌNH", child_id="068090001111"), {}, docs)

    assert not reason._labeled_value(reason._section(context, "cha"), reason._NO_CARD_MATCH_LABEL)
    assert not reason._labeled_value(reason._section(context, "cha"), reason._GENERATION_CARD_LABEL)
    # Thẻ nữ còn thừa hợp tuổi → mẹ chốt theo thế hệ thay cho TH1.
    assert reason._labeled_value(reason._section(context, "me"), reason._GENERATION_CARD_LABEL)


def test_child_takes_card_by_generation_when_declaration_name_and_id_are_garbled():
    docs = [
        _MISMATCHED_PARENT_CARDS_DOCS[0],
        {"name": "cccd-con.pdf", "text": _card("068090007777", "TRẦN VĂN BẢO", "10/05/1990", "Nam")},
        {"name": "cccd-cha.pdf", "text": _card("068062003333", "TRẦN VĂN AN", "01/01/1962", "Nam")},
        {"name": "cccd-me.pdf", "text": _card("068165002222", "LÊ THỊ HOA", "02/02/1965", "Nữ")},
    ]
    context = reason._render_context("", {}, docs)

    assert reason._labeled_value(reason._section(context, "con"), reason._GENERATION_CARD_LABEL)
    result = reason.sanitize_extracted_fields(
        [
            {"name": "Subject_FullName", "value": "TRẦN VĂN BÌNH"},
            {"name": "Subject_BirthPlaceDomestic", "value": {"tinh": "Tỉnh Nam Định"}},
            {"name": "Father_FullName", "value": "TRẦN VĂN AN"},
            {"name": "Mother_FullName", "value": "LÊ THỊ HOA"},
        ],
        context,
    )
    values = {field["name"]: field["value"] for field in result}
    defaults = {field["name"] for field in result if field.get("default")}

    assert values["Subject_FullName"] == "TRẦN VĂN BẢO"
    assert values["Subject_IdNumber"] == "068090007777"
    assert values["Subject_BirthPlaceDomestic"] == {"tinh": "Tỉnh Nam Định"}
    assert "Subject_FullName" in defaults


def test_relation_read_as_father_flips_to_self_when_requester_is_subject():
    declaration = _MISMATCHED_PARENT_CARDS_DOCS[0]["text"].replace(
        "Quan hệ với người được khai sinh: Bản thân", "Quan hệ với người được khai sinh: bố/thuỷ"
    )
    raw = (
        "<quan_he_nguoi_yeu_cau>\nKết luận: cha\nCăn cứ: Tờ khai ghi bố.\n</quan_he_nguoi_yeu_cau>"
    )
    context = reason._render_context(raw, {}, [{"name": "to-khai.pdf", "text": declaration}])

    assert reason._labeled_value(reason._section(context, "quan_he_nguoi_yeu_cau"), "Kết luận") == "bản thân"


def _card(identity: str, name: str, birth: str, sex: str) -> str:
    return (
        f"CĂN CƯỚC CÔNG DÂN\nSố / No.: {identity}\nHọ và tên / Full name: {name}\n"
        f"Ngày sinh / Date of birth: {birth}\nGiới tính / Sex: {sex} Quốc tịch / Nationality: Việt Nam"
    )



def test_declaration_year_only_keeps_card_full_date_of_same_year():
    # TH2: thẻ trùng số tờ khai; tờ khai chỉ ghi năm sinh → giữ ngày sinh đầy đủ của thẻ cùng năm.
    docs = [
        _MISMATCHED_PARENT_CARDS_DOCS[0],
        {"name": "cccd-me.pdf", "text": _card("068165002222", "LÊ THỊ HOA", "02/02/1965", "Nữ")},
    ]
    context = reason._render_context("", {}, docs)
    fields = [
        {"name": "Mother_FullName", "value": "LÊ THỊ HOA"},
        {"name": "Mother_Gender", "value": "Nữ"},
        {"name": "Mother_IdNumber", "value": "068165002222"},
        {"name": "Mother_BirthDateOrYear", "value": "02/02/1965"},
    ]

    values = {field["name"]: field["value"] for field in reason.sanitize_extracted_fields(fields, context)}

    assert values["Mother_BirthDateOrYear"] == "02/02/1965"

# Thẻ căn cước mẫu 2024: ngày sinh in ở DÒNG DƯỚI dòng nhãn "Date of birth:  Giới tính / Sex:".
_NEW_CARD_MOTHER = (
    "CĂN CƯỚC\nIDENTITY CARD\n"
    "Số định danh cá nhân / Personal identification number:\n048130001234\n"
    "Họ, chữ đệm và tên khai sinh / Full name:\nPHẠM THỊ LAN\n"
    "Ngày, tháng, năm sinh / Date of birth:  Giới tính / Sex:\n03/03/1930 Nữ\n"
    "Quốc tịch / Nationality:\nViệt Nam"
)


def test_new_card_reads_birth_date_on_line_below_label():
    person = reason._person_from_document({"name": "can-cuoc.pdf", "text": _NEW_CARD_MOTHER})

    assert person["name"] == "PHẠM THỊ LAN"
    assert person["year"] == 1930


def test_generation_rule_runs_despite_birth_certificate_of_subjects_child():
    docs = [
        {"name": "cccd-con.pdf", "text": _card("048162005678", "LÊ THỊ THU", "12/12/1962", "Nữ")},
        {"name": "can-cuoc-me.pdf", "text": _NEW_CARD_MOTHER},
        {
            "name": "khai-tu-cha.pdf",
            "text": (
                "TRÍCH LỤC KHAI TỬ\nHọ, chữ đệm, tên: LÊ VĂN HẢI\nNgày, tháng, năm sinh: 04/04/1929\n"
                "Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam"
            ),
        },
        # Giấy khai sinh của CON bà Thu (bà Thu đứng tên MẸ) — không được chặn luật thế hệ.
        {
            "name": "khai-sinh-con.pdf",
            "text": "BẢN SAO GIẤY KHAI SINH Số: 55\nKhai về Cha, Mẹ CHA MẸ\nHọ, tên Đỗ Văn Nam Lê thị Thu",
        },
    ]
    # Agent lấy chồng bà Thu (ghi trên giấy khai sinh của con) làm "cha", bỏ trống mẹ.
    raw = (
        "<con>\nHọ tên: LÊ THỊ THU\nSố CCCD/CMND: 048162005678\nNgày sinh: 12/12/1962\nGiới tính: Nữ\n"
        "Nguồn: cccd-con.pdf\nCăn cứ phân vai: CCCD\n</con>\n"
        "<cha>\nHọ tên: ĐỖ VĂN NAM\nSố CCCD/CMND: Không xác định\nNgày sinh: Không xác định\n"
        "Giới tính: Nam\nNguồn: khai-sinh-con.pdf\nCăn cứ phân vai: Giấy khai sinh.\n</cha>\n"
        "<me>\nHọ tên: Không xác định\n</me>"
    )

    context = reason._render_context(raw, {}, docs)

    assert reason._role_name(reason._section(context, "me")) == "PHẠM THỊ LAN"
    assert reason._role_name(reason._section(context, "cha")) == "LÊ VĂN HẢI"


def test_same_id_card_wins_name_birth_gender_over_declaration():
    # TH2: CCCD cha mang ĐÚNG số tờ khai ghi nhưng tên viết tay trên tờ khai bị OCR đọc lệch hẳn.
    docs = [
        _MISMATCHED_PARENT_CARDS_DOCS[0],
        {
            "name": "cccd-cha.pdf",
            "text": _card("068062003333", "PHẠM VĂN KHÁNH", "01/01/1962", "Nam")
            + "\nNgày, tháng, năm / Date, month, year: 10/08/2021\n"
            "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
        },
    ]
    context = reason._render_context(_raw_roles(child="TRẦN VĂN BÌNH", child_id="068090001111"), {}, docs)
    # Agent trích tên/năm sinh cha theo tờ khai.
    fields = [
        {"name": "Subject_FullName", "value": "TRẦN VĂN BÌNH"},
        {"name": "Father_FullName", "value": "TRẦN VĂN AN"},
        {"name": "Father_IdNumber", "value": "068062003333"},
        {"name": "Father_BirthDateOrYear", "value": "1962"},
    ]

    values = {field["name"]: field["value"] for field in reason.sanitize_extracted_fields(fields, context)}

    assert values["Father_FullName"] == "PHẠM VĂN KHÁNH"
    assert values["Father_BirthDateOrYear"] == "01/01/1962"
    assert values["Father_Gender"] == "Nam"
    assert values["Father_IdNumber"] == "068062003333"
    assert values["Father_IdIssueDate"] == "10/08/2021"


def test_card_matching_name_with_garbled_declared_id_wins_identity():
    # Tờ khai viết tay: tên mất dấu, số CCCD rụng chữ số (không hợp lệ) → thẻ khớp tên vẫn là của mẹ,
    # họ tên/ngày sinh theo thẻ in.
    declaration = _MISMATCHED_PARENT_CARDS_DOCS[0]["text"].replace(
        "Họ, chữ đệm, tên người mẹ: LÊ THỊ HOA", "Họ, chữ đệm, tên người mẹ: LE THI HOA"
    ).replace("CCCD số 068165002222", "CCCD số 0681650022")
    docs = [
        {"name": "to-khai.pdf", "text": declaration},
        {"name": "cccd-me.pdf", "text": _card("068165002222", "LÊ THỊ HOA", "02/02/1965", "Nữ")},
    ]
    context = reason._render_context("", {}, docs)

    assert reason._labeled_value(reason._section(context, "me"), reason._OWN_CARD_LABEL)
    values = {
        field["name"]: field["value"]
        for field in reason.sanitize_extracted_fields(
            [
                {"name": "Subject_FullName", "value": "TRẦN VĂN BÌNH"},
                {"name": "Mother_FullName", "value": "LE THI HOA"},
                {"name": "Mother_IdNumber", "value": "068165002222"},
                {"name": "Mother_BirthDateOrYear", "value": "1965"},
            ],
            context,
        )
    }

    assert values["Mother_FullName"] == "LÊ THỊ HOA"
    assert values["Mother_BirthDateOrYear"] == "02/02/1965"
    assert values["Mother_IdNumber"] == "068165002222"



# ---- Tờ khai lấp chỗ trống (replay hồ sơ thật: agent bỏ sót vai / người yêu cầu) ----
_DECLARATION_WITH_REQUESTER_ID = _MISMATCHED_PARENT_CARDS_DOCS[0]["text"].replace(
    "Họ, chữ đệm, tên người yêu cầu: TRẦN VĂN BÌNH\n",
    "Họ, chữ đệm, tên người yêu cầu: TRẦN VĂN BÌNH\nGiấy tờ tùy thân: CCCD số 068090001111 cấp ngày 10-08-2021\n",
)


def test_declaration_fills_role_agent_dropped_when_no_card():
    # Không có thẻ nào, agent bỏ sót cả khối mẹ → mẹ vẫn điền theo tờ khai.
    context = reason._render_context("", {}, [{"name": "to-khai.pdf", "text": _DECLARATION_WITH_REQUESTER_ID}])
    values = {
        field["name"]: field["value"]
        for field in reason.sanitize_extracted_fields(
            [
                {"name": "Subject_FullName", "value": "TRẦN VĂN BÌNH"},
                {"name": "Father_FullName", "value": "TRẦN VĂN AN"},
            ],
            context,
        )
    }

    assert values["Mother_FullName"] == "LÊ THỊ HOA"
    assert values["Mother_BirthDateOrYear"] == "1965"
    assert values["Mother_IdNumber"] == "068165002222"
    assert values["Mother_Ethnicity"] == "Kinh"


def test_declaration_fills_requester_id_and_issue_date_agent_dropped():
    context = reason._render_context("", {}, [{"name": "to-khai.pdf", "text": _DECLARATION_WITH_REQUESTER_ID}])
    values = {
        field["name"]: field["value"]
        for field in reason.sanitize_extracted_fields([{"name": "Subject_FullName", "value": "TRẦN VĂN BÌNH"}], context)
    }

    assert values["Requester_IdNumber"] == "068090001111"
    assert values["Requester_IdIssueDate"] == "10/08/2021"


def test_declaration_fill_never_overwrites_card_identity():
    docs = [
        {"name": "to-khai.pdf", "text": _DECLARATION_WITH_REQUESTER_ID.replace("LÊ THỊ HOA", "LE THI HOA")},
        {"name": "cccd-me.pdf", "text": _card("068165002222", "LÊ THỊ HOA", "02/02/1965", "Nữ")},
    ]
    context = reason._render_context("", {}, docs)
    values = {
        field["name"]: field["value"]
        for field in reason.sanitize_extracted_fields(
            [{"name": "Subject_FullName", "value": "TRẦN VĂN BÌNH"}, {"name": "Mother_FullName", "value": "LE THI HOA"}],
            context,
        )
    }

    assert values["Mother_FullName"] == "LÊ THỊ HOA"
    assert values["Mother_BirthDateOrYear"] == "02/02/1965"


def test_subject_id_of_other_family_member_is_dropped_not_used_to_rewrite_birth():
    # Agent gán số CCCD của MẸ (mã năm sinh 1965, nữ) cho con sinh 1990 → bỏ số, giữ ngày sinh con.
    context = reason._render_context("", {}, [{"name": "to-khai.pdf", "text": _DECLARATION_WITH_REQUESTER_ID}])
    values = {
        field["name"]: field["value"]
        for field in reason.sanitize_extracted_fields(
            [
                {"name": "Subject_FullName", "value": "TRẦN VĂN BÌNH"},
                {"name": "Subject_Gender", "value": "Nam"},
                {"name": "Subject_BirthDate", "value": "10/05/1990"},
                {"name": "Subject_IdNumber", "value": "068165002222"},
            ],
            context,
        )
    }

    assert values["Subject_BirthDate"] == "10/05/1990"
    assert values.get("Subject_IdNumber") != "068165002222"


def test_card_number_with_dropped_digit_does_not_replace_valid_declared_number():
    # OCR đọc rụng một chữ số NGAY TRÊN THẺ (11 số) → giữ số 12 chữ số tờ khai ghi.
    docs = [
        _MISMATCHED_PARENT_CARDS_DOCS[0],
        {"name": "cccd-me.pdf", "text": _card("06816500222", "LÊ THỊ HOA", "02/02/1965", "Nữ")},
    ]
    context = reason._render_context("", {}, docs)
    values = {
        field["name"]: field["value"]
        for field in reason.sanitize_extracted_fields(
            [
                {"name": "Subject_FullName", "value": "TRẦN VĂN BÌNH"},
                {"name": "Mother_FullName", "value": "LÊ THỊ HOA"},
                {"name": "Mother_IdNumber", "value": "06816500222"},
            ],
            context,
        )
    }

    assert values["Mother_IdNumber"] == "068165002222"



def test_generation_does_not_take_card_whose_year_contradicts_declaration():
    # Tờ khai: con sinh 1990, không CCCD. Thẻ nữ sinh 2010 (con/cháu của người được đăng ký nộp
    # kèm) — năm sinh lệch hẳn tờ khai → không phải người được đăng ký lại, giữ tờ khai.
    docs = [
        _MISMATCHED_PARENT_CARDS_DOCS[0],
        {"name": "cccd-chau.pdf", "text": _card("068310005555", "TRẦN THỊ NGỌC", "05/02/2010", "Nữ")},
    ]
    context = reason._render_context("", {}, docs)

    assert not reason._labeled_value(reason._section(context, "con"), reason._GENERATION_CARD_LABEL)
    assert reason._role_name(reason._section(context, "con")) == "TRẦN VĂN BÌNH"


def test_old_card_birth_and_gender_on_one_line_reads_clean_date():
    person = reason._person_from_document({
        "name": "cmnd.pdf",
        "text": (
            "CĂN CƯỚC CÔNG DÂN\nSố / No.: 068155001234\nHọ và tên / Full name: LÊ THỊ HOA\n"
            "Ngày sinh / Date of birth: 28/05/1955 Giới tính / Sex: Nữ\nQuốc tịch / Nationality: Việt Nam"
        ),
    })

    assert reason._labeled_value(person["section"], "Ngày sinh") == "28/05/1955"


# Hồ sơ 4 CCCD không tờ khai: cán bộ đăng nhập cổng scan kèm thẻ của chính mình + con + mẹ + cha.
_OFFICER_FRONT = (
    "CĂN CƯỚC CÔNG DÂN\nSố / No: 001201012345\nHọ và tên / Full name:\nTRẦN MINH KHOA\n"
    "Ngày sinh / Date of birth: 02/03/2001\nGiới tính / Sex: Nam Quốc tịch / Nationality: Việt Nam\n"
    "Nơi thường trú / Place of residence: Thôn Đông\nSong Liễu, Thuận Thành, Bắc Ninh\n"
    "Có giá trị đến: 02/03/2026"
)
_OFFICER_BACK = (
    "Ngày, tháng, năm / Date, month, year: 10/04/2021\n"
    "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI\n"
    "IDVNM2010123452001201012345<<9"
)
_FOUR_CARD_DOCS = [
    {"name": "cccd-can-bo.jpg", "text": _OFFICER_FRONT},
    {"name": "cccd-can-bo-sau.jpg", "text": _OFFICER_BACK},
    {"name": "cccd-con.jpg", "text": _card("027078001111", "LÊ VĂN HÙNG", "05/06/1978", "Nam")},
    {"name": "cccd-me.jpg", "text": _card("027150002222", "PHẠM THỊ MAI", "07/08/1950", "Nữ")},
    {"name": "cccd-cha.jpg", "text": _card("027048003333", "LÊ VĂN SƠN", "09/10/1948", "Nam")},
]
# Agent chọn người trẻ nhất (cán bộ) làm con — đúng lỗi của hồ sơ thật.
_FOUR_CARD_RAW = (
    "<con>\nHọ tên: TRẦN MINH KHOA\nSố CCCD/CMND: 001201012345\nNgày sinh: 02/03/2001\nGiới tính: Nam\n"
    "Nguồn: cccd-can-bo.jpg\nCăn cứ phân vai: Người trẻ nhất.\n</con>\n"
    "<me>\nHọ tên: PHẠM THỊ MAI\nSố CCCD/CMND: 027150002222\nNgày sinh: 07/08/1950\nGiới tính: Nữ\n"
    "Nguồn: cccd-me.jpg\nCăn cứ phân vai: Thế hệ.\n</me>\n"
    "<cha>\nHọ tên: LÊ VĂN SƠN\nSố CCCD/CMND: 027048003333\nNgày sinh: 09/10/1948\nGiới tính: Nam\n"
    "Nguồn: cccd-cha.jpg\nCăn cứ phân vai: Thế hệ.\n</cha>"
)
_OFFICER_LOGIN = {"formContext": {"applicantFullname": "TRẦN MINH KHOA", "applicantIdentityNumber": "001201012345"}}


def test_officer_card_of_logged_in_account_is_excluded_from_family_roles():
    context = reason._render_context(_FOUR_CARD_RAW, _OFFICER_LOGIN, _FOUR_CARD_DOCS)

    assert reason._role_name(reason._section(context, "con")) == "LÊ VĂN HÙNG"
    assert reason._role_name(reason._section(context, "me")) == "PHẠM THỊ MAI"
    assert reason._role_name(reason._section(context, "cha")) == "LÊ VĂN SƠN"
    requester = reason._section(context, "nguoi_yeu_cau")
    assert reason._labeled_value(requester, "Căn cứ phân vai") == reason.APPLICANT_CARD_BASIS
    assert reason._labeled_value(requester, "Số CCCD/CMND") == "001201012345"
    assert reason._labeled_value(requester, "Ngày cấp") == "10/04/2021"
    assert reason._labeled_value(reason._section(context, "quan_he_nguoi_yeu_cau"), "Kết luận") == "khác"


def test_officer_card_matched_by_name_when_portal_sends_no_id():
    options = {"formContext": {"applicantFullname": "Trần Minh Khoa"}}
    context = reason._render_context(_FOUR_CARD_RAW, options, _FOUR_CARD_DOCS)

    assert reason._role_name(reason._section(context, "me")) == "PHẠM THỊ MAI"
    assert reason._labeled_value(reason._section(context, "nguoi_yeu_cau"), "Họ tên") == "TRẦN MINH KHOA"


def test_lineage_repair_keeps_mother_card_without_portal_anchor():
    # Không có mỏ neo cổng: ghép con/cha theo dòng họ vẫn phải ghép lại mẹ, không bỏ trống.
    context = reason._render_context(_FOUR_CARD_RAW, {}, _FOUR_CARD_DOCS)

    assert reason._role_name(reason._section(context, "con")) == "LÊ VĂN HÙNG"
    assert reason._role_name(reason._section(context, "me")) == "PHẠM THỊ MAI"
    assert reason._labeled_value(reason._section(context, "nguoi_yeu_cau"), "Căn cứ phân vai") != (
        reason.APPLICANT_CARD_BASIS
    )


def test_logged_in_subject_card_is_not_treated_as_officer():
    # Người đăng nhập chính là con (3 thẻ con/mẹ/cha) → vẫn "bản thân", không dựng khối cán bộ.
    docs = _FOUR_CARD_DOCS[2:]
    options = {"formContext": {"applicantFullname": "LÊ VĂN HÙNG", "applicantIdentityNumber": "027078001111"}}
    context = reason._render_context("", options, docs)

    assert reason._role_name(reason._section(context, "con")) == "LÊ VĂN HÙNG"
    assert reason._labeled_value(reason._section(context, "quan_he_nguoi_yeu_cau"), "Kết luận") == "bản thân"
    assert reason._labeled_value(reason._section(context, "nguoi_yeu_cau"), "Căn cứ phân vai") != (
        reason.APPLICANT_CARD_BASIS
    )


def test_mapper_fills_requester_from_officer_card_and_mother_from_her_card():
    context = reason._render_context(_FOUR_CARD_RAW, _OFFICER_LOGIN, _FOUR_CARD_DOCS)
    fields = [
        {"name": "Subject_FullName", "value": "LÊ VĂN HÙNG"},
        {"name": "Subject_IdNumber", "value": "027078001111"},
        {"name": "Mother_FullName", "value": "PHẠM THỊ MAI"},
        {"name": "Mother_Gender", "value": "Nữ"},
        {"name": "Mother_IdNumber", "value": "027150002222"},
        {"name": "Father_FullName", "value": "LÊ VĂN SƠN"},
        {"name": "Father_Gender", "value": "Nam"},
        {"name": "Father_IdNumber", "value": "027048003333"},
    ]
    fields = reason.sanitize_extracted_fields(fields, context)

    out = {f["name"]: f for f in mapper.enrich(fields, {**_OFFICER_LOGIN, "_reasoning_context": context})}

    assert out["QuanHe"]["value"] == "Khac" and not out["QuanHe"].get("default")
    assert out["HoVaTenC"]["value"] == "TRẦN MINH KHOA"
    assert out["SoDinhDanhC"]["value"] == "001201012345"
    assert out["NgayCapDDC"]["value"] == "10/04/2021"
    assert out["nycNoiCuTru_TrongNuoc"]["value"]["tinh"] == "Bắc Ninh"
    assert out["HoTenMeKS"]["value"] == "PHẠM THỊ MAI"
    assert out["SoDinhDanhMe"]["value"] == "027150002222"
    assert not any(f.get("clear") for f in out.values() if f["name"].endswith("C"))
