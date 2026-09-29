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


def test_relation_read_as_father_flips_to_self_when_requester_is_subject():
    # Dòng quan hệ viết tay "bản thân" bị OCR đọc thành "bố/thuỷ"; cha trên tờ khai là người khác.
    declaration = (
        "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH\n"
        "Họ, chữ đệm, tên người yêu cầu: TRẦN VĂN BÌNH\n"
        "Giấy tờ tùy thân: CCCD số 068090001111\n"
        "Quan hệ với người được khai sinh: bố/thuỷ\n"
        "Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây:\n"
        "Họ, chữ đệm, tên: TRẦN VĂN BÌNH\n"
        "Ngày, tháng, năm sinh: 10/05/1990\n"
        "Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam\n"
        "Họ, chữ đệm, tên người mẹ: LÊ THỊ HOA\n"
        "Năm sinh: 1965 Dân tộc: Kinh Quốc tịch: Việt Nam\n"
        "Họ, chữ đệm, tên người cha: TRẦN VĂN AN\n"
        "Năm sinh: 1962 Dân tộc: Kinh Quốc tịch: Việt Nam\n"
        "Tôi cam đoan những nội dung khai trên đây là đúng sự thật"
    )
    raw = "<quan_he_nguoi_yeu_cau>\nKết luận: cha\nCăn cứ: Tờ khai ghi bố.\n</quan_he_nguoi_yeu_cau>"
    context = reason._render_context(raw, {}, [{"name": "to-khai.pdf", "text": declaration}])

    assert reason._labeled_value(reason._section(context, "quan_he_nguoi_yeu_cau"), "Kết luận") == "bản thân"


_DECLARATION_WINS_TEXT = (
    "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH\n"
    "Họ, chữ đệm, tên người yêu cầu: TRẦN VĂN BÌNH\n"
    "Giấy tờ tùy thân: CCCD số 06809000111\n"
    "Quan hệ với người được khai sinh: Bản thân\n"
    "Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây:\n"
    "Họ, chữ đệm, tên: TRẦN VĂN BÌNH\n"
    "Ngày, tháng, năm sinh: 10-05-1990\n"
    "Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam\n"
    "Họ, chữ đệm, tên người mẹ: LÊ THỊ HOA\n"
    "Năm sinh: 1965 Dân tộc: Kinh Quốc tịch: Việt Nam\n"
    "Giấy tờ tùy thân: CCCD số 068165002222\n"
    "Họ, chữ đệm, tên người cha: TRẦN VĂN AN\n"
    "Năm sinh: 1962 Dân tộc: Kinh Quốc tịch: Việt Nam\n"
    "Giấy tờ tùy thân: CCCD số 068062003333, Cục CSQLHC về TTXH cấp ngày 11-08-2021\n"
    "Tôi cam đoan những nội dung khai trên đây là đúng sự thật"
)


def _card(identity: str, name: str, birth: str, sex: str) -> str:
    return (
        f"CĂN CƯỚC CÔNG DÂN\nSố / No.: {identity}\nHọ và tên / Full name: {name}\n"
        f"Ngày sinh / Date of birth: {birth}\nGiới tính / Sex: {sex} Quốc tịch / Nationality: Việt Nam"
    )


def test_declaration_wins_over_every_card_value():
    docs = [
        {"name": "to-khai.pdf", "text": _DECLARATION_WINS_TEXT},
        # Cùng người nhưng thẻ ghi khác tờ khai: con lệch tên + ngày sinh, cha lệch số + năm sinh.
        {"name": "cccd-con.pdf", "text": _card("068090001122", "TRẦN VĂN BINH", "11/05/1990", "Nam")},
        {"name": "cccd-cha.pdf", "text": _card("068063003344", "TRẦN VĂN AN", "01/01/1963", "Nam")},
    ]
    context = reason._render_context("", {}, docs)
    # Agent trích toàn bộ theo CCCD.
    fields = [
        {"name": "Requester_RelationToSubject", "value": "Bản thân"},
        {"name": "Requester_FullName", "value": "TRẦN VĂN BINH"},
        {"name": "Requester_IdNumber", "value": "068090001122"},
        {"name": "Subject_FullName", "value": "TRẦN VĂN BINH"},
        {"name": "Subject_BirthDate", "value": "11/05/1990"},
        {"name": "Subject_BirthDateFromId", "value": "11/05/1990"},
        {"name": "Father_FullName", "value": "TRẦN VĂN AN"},
        {"name": "Father_Gender", "value": "Nam"},
        {"name": "Father_IdNumber", "value": "068063003344"},
        {"name": "Father_IdIssueDate", "value": "10/08/2021"},
        {"name": "Father_BirthDateOrYear", "value": "01/01/1963"},
    ]

    values = {field["name"]: field["value"] for field in reason.sanitize_extracted_fields(fields, context)}

    assert values["Requester_FullName"] == "TRẦN VĂN BÌNH"
    assert values["Requester_IdNumber"] == "06809000111"  # sai độ dài vẫn theo tờ khai
    assert values["Subject_FullName"] == "TRẦN VĂN BÌNH"
    assert values["Subject_BirthDate"] == "10/05/1990"
    assert "Subject_BirthDateFromId" not in values
    assert values["Father_IdNumber"] == "068062003333"
    assert values["Father_IdIssueDate"] == "11/08/2021"
    assert values["Father_BirthDateOrYear"] == "1962"
    assert values["Mother_IdNumber"] == "068165002222"


def test_declaration_year_only_keeps_card_full_date_of_same_year():
    docs = [
        {"name": "to-khai.pdf", "text": _DECLARATION_WINS_TEXT},
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
