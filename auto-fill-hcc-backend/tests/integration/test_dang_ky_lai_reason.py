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


_MISREAD_CHILD_YEAR_DECLARATION = """TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH
Kính gửi: UBND phường Hòa An
Họ, chữ đệm, tên người yêu cầu: Trần Văn Bình
Ngày, tháng, năm sinh: 05/03/1968
Giấy tờ tùy thân: CCCD số 001068000123
Quan hệ với người được khai sinh: Tự khai
Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây:
Họ, chữ đệm, tên: Trần Văn Bình
Ngày, tháng, năm sinh: 05/03/1938
Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam
Nơi sinh: Hòa An
Họ, chữ đệm, tên người mẹ: Lê Thị Hoa
Ngày, tháng, năm sinh: 10/10/1942 Dân tộc: Kinh Quốc tịch: Việt Nam
Giấy tờ tùy thân: CCCD 001142000456
Họ, chữ đệm, tên người cha: Trần Văn An
Ngày, tháng, năm sinh: 02/02/1940 Dân tộc: Kinh Quốc tịch: Việt Nam
Giấy tờ tùy thân: CCCD 001040000789
Tôi cam đoan những nội dung khai trên đây là đúng sự thật."""

_BIRTH_CERTIFICATE_COPY = """GIẤY KHAI SINH
(BẢN SAO)
Họ, chữ đệm, tên: TRẦN VĂN BÌNH
Ngày, tháng, năm sinh: 05/03/1968
Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam
Họ, chữ đệm, tên người mẹ: LÊ THỊ HOA
Năm sinh: 1942
Họ, chữ đệm, tên người cha: TRẦN VĂN AN
Năm sinh: 1940"""


def test_misread_child_birth_year_is_fixed_instead_of_dropping_parents():
    # Tờ khai viết tay đọc năm sinh con 1968 thành 1938 → con "già" hơn cha/mẹ. Bản sao giấy khai
    # sinh và mục người yêu cầu cùng ghi 1968 → sửa năm con, giữ nguyên cả khối cha lẫn mẹ.
    documents = [
        {"name": "ban-sao-gks.pdf", "text": _BIRTH_CERTIFICATE_COPY},
        {"name": "to-khai.pdf", "text": _MISREAD_CHILD_YEAR_DECLARATION},
    ]
    context = reason._render_context("", {}, documents)

    assert reason._labeled_value(reason._section(context, "con"), "Ngày sinh") == "05/03/1968"
    assert reason._role_name(reason._section(context, "me")) == "Lê Thị Hoa"
    assert reason._role_name(reason._section(context, "cha")) == "Trần Văn An"


def test_misread_child_birth_year_without_other_source_still_drops_parents():
    documents = [{"name": "to-khai.pdf", "text": _MISREAD_CHILD_YEAR_DECLARATION.replace(
        "Họ, chữ đệm, tên người yêu cầu: Trần Văn Bình\nNgày, tháng, năm sinh: 05/03/1968",
        "Họ, chữ đệm, tên người yêu cầu: Trần Văn Bình\nNgày, tháng, năm sinh: 05/03/1938",
    )}]
    context = reason._render_context("", {}, documents)

    assert reason._is_unknown(reason._section(context, "me"))
    assert reason._is_unknown(reason._section(context, "cha"))
