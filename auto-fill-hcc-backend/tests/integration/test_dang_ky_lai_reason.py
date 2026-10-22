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

    # Subject_*/Mother_* sai người và PreviousRegistration_* (không có giấy khai sinh) bị loại.
    # Father_* cũng bị loại: trùng tên + năm sinh với Subject_* agent trả về, không có số định
    # danh/giới tính nào phân biệt được hai người (_role_is_subject) — thà bỏ trống còn hơn sai.
    # Mẹ có CCCD nhưng vai Mother_* bị loại vì sai người nên không dựng lại từ thẻ.
    assert values == {}


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
        # Vai mẹ agent bỏ trống được dựng lại từ chính CCCD của mẹ trong khối phân vai.
        *_MOTHER_CARD_FIELDS,
    }


# Nhân thân khối <me> đọc từ cccd-hoa.pdf: vai mẹ agent trả rỗng được dựng lại theo đúng thẻ này.
_MOTHER_CARD_FIELDS = {
    "Mother_IdNumber": "027176001591",
    "Mother_FullName": "NGUYỄN THỊ HOÀ",
    "Mother_Gender": "Nữ",
    "Mother_BirthDateOrYear": "31/10/1976",
    "Mother_Nationality": "Việt Nam",
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
    values = {field["name"]: field["value"] for field in result}
    assert not any(name.startswith("Father_") for name in values)
    assert values == {"Subject_FullName": "MAN THỊ HUẾ", **_MOTHER_CARD_FIELDS}


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

    async def _chat(messages, **kwargs):
        captured["messages"] = messages
        captured["kwargs"] = kwargs
        return _raw_roles()

    monkeypatch.setattr(reason.client, "chat", _chat)
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

    # Subject_* sai người, PreviousRegistration_* không có giấy khai sinh; Father_* trùng hệt
    # Subject_* agent trả (không gì phân biệt hai người) nên cũng bị loại. Vai mẹ rỗng → dựng từ thẻ.
    assert {f["name"]: f["value"] for f in seen["fields"]} == _MOTHER_CARD_FIELDS
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


# Tờ khai viết tay: năm sinh mẹ bị OCR đọc lệch thành SAU năm sinh con, không có CCCD nào khác.
_DECLARATION_MOTHER_YEAR_BROKEN = """CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH
Kính gửi: (1) UBND Xã Yên Bình - Tỉnh Lào Cai
Họ, chữ đệm, tên người yêu cầu: TRẦN VĂN KHẢI
Ngày, tháng, năm sinh: 10/02/1985
Nơi cư trú: (2) Thôn 3 Xã Yên Bình . Tỉnh Lào Cai
Giấy tờ tùy thân: (3) 015085000111 , Cục Cảnh sát QLHC về TTXH , Cấp ngày 01/04/2021
Quan hệ với người được khai sinh: Bản Thân
Đề nghị cơ quan đăng ký lại khai sinh cho người có tên dưới đây:
Họ, chữ đệm, tên: TRẦN VĂN KHẢI
Ngày, tháng, năm sinh: 10/02/1985 ghi bằng chữ: (Mười tháng Hai năm một nghìn chín trăm tám mươi lăm)
Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam
Nơi sinh: (4) Xã Yên Bình , Tỉnh Lào Cai
Họ, chữ đệm, tên người mẹ: LÊ THỊ HẠNH
Năm sinh: (5) 06/05/1989 Dân tộc: (2) Kinh Quốc tịch: (2) Việt Nam
Nơi cư trú: (2) Thôn 3 Xã Yên Bình , Tỉnh Lào Cai
Giấy tờ tùy thân: (3) 015160001234
Họ, chữ đệm, tên người cha: TRẦN VĂN BÌNH
Năm sinh: (5) 15/08/1955 Dân tộc: (2) Kinh Quốc tịch: (2) Việt Nam
Nơi cư trú: (2) Đã chết
Giấy tờ tùy thân: (3)
Đã đăng ký khai sinh tại: (6) Ủy ban nhân dân Thị xã Yên Bái
Tôi cam đoan những nội dung khai trên đây là đúng sự thật.
"""


def _broken_year_context() -> str:
    return reason._render_context("", {}, [{"name": "to-khai.pdf", "text": _DECLARATION_MOTHER_YEAR_BROKEN}])


def test_declared_mother_with_broken_birth_year_is_kept_not_wiped():
    """Năm sinh mẹ lệch thế hệ mà vai chốt từ nhãn in sẵn tờ khai → giữ nguyên khối, gắn nhãn soát."""
    me = reason._section(_broken_year_context(), "me")

    assert reason._role_name(me) == "LÊ THỊ HẠNH"
    assert reason._role_id(me) == "015160001234"
    assert reason._labeled_value(me, "Ngày sinh") == "06/05/1989"
    assert reason._labeled_value(me, reason._GENERATION_MISMATCH_LABEL)


def test_inferred_mother_with_broken_birth_year_is_still_wiped():
    """Vai KHÔNG đến từ nhãn tờ khai mà sai thế hệ thì vẫn xoá như cũ."""
    sections = {
        "con": "Họ tên: TRẦN VĂN KHẢI\nNgày sinh: 10/02/1985\nGiới tính: Nam\nCăn cứ phân vai: CCCD",
        "me": "Họ tên: LÊ THỊ HẠNH\nNgày sinh: 06/05/1989\nGiới tính: Nữ\nCăn cứ phân vai: Người nữ duy nhất.",
    }

    me = reason._validate_family_sections(sections)["me"]

    assert reason._is_unknown(me)


def test_sanitizer_fills_full_mother_from_declaration_when_agent_drops_her():
    """Agent bỏ sót cả vai mẹ → tờ khai lấp đủ; năm sinh giữ đúng OCR tờ khai, tô vàng."""
    fields = [
        {"name": "Subject_FullName", "value": "TRẦN VĂN KHẢI"},
        {"name": "Subject_BirthDate", "value": "10/02/1985"},
        {"name": "Father_FullName", "value": "TRẦN VĂN BÌNH"},
        {"name": "Father_BirthDateOrYear", "value": "15/08/1955"},
    ]

    result = reason.sanitize_extracted_fields(fields, _broken_year_context())
    values = {field["name"]: field["value"] for field in result}
    flagged = {field["name"] for field in result if field.get("default")}

    assert values["Mother_FullName"] == "LÊ THỊ HẠNH"
    assert values["Mother_IdNumber"] == "015160001234"
    assert values["Mother_Ethnicity"] == "Kinh"
    assert values["Mother_Nationality"] == "Việt Nam"
    assert values["Mother_ResidenceDomestic"]["xa"] == "Xã Yên Bình"
    assert values["Mother_ResidenceDomestic"]["diaChi"] == "Thôn 3"
    assert values["Mother_BirthDateOrYear"] == "06/05/1989"
    assert "Mother_BirthDateOrYear" in flagged


def test_sanitizer_keeps_ocr_birth_year_when_agent_extracts_mother():
    """Agent trích mẹ kèm CCCD: năm sinh KHÔNG bị sửa theo mã năm trong số CCCD, giữ đúng OCR."""
    fields = [
        {"name": "Subject_FullName", "value": "TRẦN VĂN KHẢI"},
        {"name": "Subject_BirthDate", "value": "10/02/1985"},
        {"name": "Mother_FullName", "value": "LÊ THỊ HẠNH"},
        {"name": "Mother_BirthDateOrYear", "value": "06/05/1989"},
        {"name": "Mother_IdNumber", "value": "015160001234"},
    ]

    values = {f["name"]: f["value"] for f in reason.sanitize_extracted_fields(fields, _broken_year_context())}

    assert values["Mother_BirthDateOrYear"] == "06/05/1989"
    assert values["Mother_FullName"] == "LÊ THỊ HẠNH"


_CARD_RESIDENCE = {"quocGia": "Việt Nam", "tinh": "Thành phố Huế", "xa": "Phường Kim Trà", "diaChi": "An Thuận"}


def _residence_fields() -> list[dict]:
    return [
        {"name": "Subject_FullName", "value": "TRẦN VĂN KHẢI"},
        {"name": "Subject_BirthDate", "value": "10/02/1985"},
        {"name": "Mother_FullName", "value": "LÊ THỊ HẠNH"},
        {"name": "Mother_IdNumber", "value": "015160001234"},
        {"name": "Mother_ResidenceDomestic", "value": dict(_CARD_RESIDENCE)},
        {"name": "Requester_FullName", "value": "TRẦN VĂN KHẢI"},
        {"name": "Requester_ResidenceDomestic", "value": dict(_CARD_RESIDENCE)},
    ]


def test_residence_follows_declaration_not_cccd_for_parent_and_requester():
    """Hồ sơ có cả tờ khai lẫn CCCD: agent lấy nơi cư trú theo thẻ thì vẫn đặt lại theo tờ khai."""
    values = {f["name"]: f["value"] for f in reason.sanitize_extracted_fields(_residence_fields(), _broken_year_context())}

    for name in ("Mother_ResidenceDomestic", "Requester_ResidenceDomestic"):
        assert values[name]["tinh"] == "Lào Cai"
        assert values[name]["xa"] == "Xã Yên Bình"
        assert values[name]["diaChi"] == "Thôn 3"


def test_residence_follows_declaration_even_when_card_chosen_by_generation():
    context = _broken_year_context()
    me = reason._section(context, "me")
    stamped = f"{me}\n{reason._GENERATION_CARD_LABEL}: {reason._GENERATION_CARD_VALUE}"
    context = context.replace(me, stamped, 1)

    values = {f["name"]: f["value"] for f in reason.sanitize_extracted_fields(_residence_fields(), context)}

    assert values["Mother_ResidenceDomestic"]["xa"] == "Xã Yên Bình"


def test_residence_not_overridden_by_role_line_filled_from_card():
    """Tờ khai bỏ trống nơi cư trú: dòng bù từ thẻ trong khối vai không được coi là tờ khai."""
    context = _broken_year_context()
    blank = context.replace("Nơi cư trú: Thôn 3 Xã Yên Bình , Tỉnh Lào Cai", "Nơi cư trú: Không xác định")
    me = reason._section(blank, "me")
    blank = blank.replace(
        me, me.replace("Nơi cư trú: Không xác định", "Nơi cư trú: Thôn 3 Xã Yên Bình , Tỉnh Lào Cai"), 1
    )

    values = {f["name"]: f["value"] for f in reason.sanitize_extracted_fields(_residence_fields(), blank)}

    assert values["Mother_ResidenceDomestic"] == _CARD_RESIDENCE


def test_declaration_residence_splits_commune_written_without_comma():
    area = reason._residence_from_declaration_line("Thôn 3 Xã Yên Bình , Tỉnh Lào Cai")

    assert area["tinh"] == "Lào Cai"
    assert area["xa"] == "Xã Yên Bình"
    assert area["diaChi"] == "Thôn 3"


_CAM_DOAN_KHOM_NAY_LA = """BẢN CAM ĐOAN
Kính gửi (1): UBND phường Xuân Hương Đà Lạt
Họ, chữ đệm, tên: PHẠM VĂN LỘC
Tôi xin cam đoan nội dung sau đây: Tôi được đăng ký khai sinh tại Khóm Xuân An phường II Đà Lạt (Nay là phường Xuân Hương Đà Lạt tỉnh Lâm Đồng nhưng bản chính giấy khai sinh không còn lưu trữ.
"""


def _agency_fields(commune: str) -> list[dict]:
    return [
        {"name": "PreviousRegistration_AgencyProvince", "value": "Lâm Đồng"},
        {"name": "PreviousRegistration_AgencyCommune", "value": commune},
        {"name": "PreviousRegistration_Number", "value": "120"},
    ]


def test_birth_agency_takes_current_name_not_hamlet_from_commitment():
    """Agent lấy KHÓM làm phường ("Phường Xuân An" → remap ra phường Phan Thiết) → câu cam đoan thắng."""
    context = reason._render_birth_agency_phrases([{"name": "cam-doan.pdf", "text": _CAM_DOAN_KHOM_NAY_LA}])

    values = {
        field["name"]: field["value"]
        for field in reason._apply_birth_agency_override(_agency_fields("Phường Xuân An"), context)
    }

    assert values["PreviousRegistration_AgencyProvince"] == "Lâm Đồng"
    assert values["PreviousRegistration_AgencyCommune"] == "Phường Xuân Hương - Đà Lạt"
    assert values["PreviousRegistration_Number"] == "120"


def test_birth_agency_skips_hamlet_and_converts_roman_ward():
    area = reason._agency_area_from_phrase("Khóm Xuân An phường II Đà Lạt", "Lâm Đồng")

    assert area == {"tinh": "Lâm Đồng", "xa": "Phường Xuân Hương - Đà Lạt"}


def test_birth_agency_phrase_without_commune_keeps_agent_value():
    text = "Đã đăng ký khai sinh tại: (6) Ủy ban nhân dân Thị xã Yên Bái\n"
    context = reason._render_birth_agency_phrases([{"name": "to-khai.pdf", "text": text}])

    fields = _agency_fields("Phường Yên Bái")

    assert reason._apply_birth_agency_override(fields, context) == fields
