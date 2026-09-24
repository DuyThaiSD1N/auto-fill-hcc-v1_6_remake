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


# req_f0fa659d2248: không tờ khai. Thẻ căn cước MẪU MỚI của người được đăng ký lại (Thúc), thẻ của mẹ
# (Vậy) bị OCR đọc năm sinh 1994 trong khi số CCCD 027 1 39 ... nói 1939, và trích lục khai tử của cha.
_NEW_CARD_THUC = """CĂN CƯỚC
IDENTITY CARD
Số định danh cá nhân / Personal identification number:
027065010250
Họ, chữ đệm và tên khai sinh / Full name:
NGUYỄN ĐĂNG THÚC
Ngày, tháng, năm sinh / Date of birth:
20/10/1965
Giới tính / Sex:
Nam
Quốc tịch / Nationality:
Việt Nam
Nơi đăng ký khai sinh / Place of birth:
Hà Mãn, Thuận Thành, Bắc Ninh
Ngày, tháng, năm cấp / Date of issue:
10/02/2025
BỘ CÔNG AN/MINISTRY OF PUBLIC SECURITY"""

_CARD_VAY = """CĂN CƯỚC CÔNG DÂN
Số / No.: 027139005852
Họ và tên / Full name: DƯƠNG THỊ VẬY
Ngày sinh / Date of birth: 01/01/1994
Giới tính / Sex: Nữ Quốc tịch / Nationality: Việt Nam"""

_DEATH_KY = """TRÍCH LỤC KHAI TỬ
Họ, chữ đệm, tên: NGUYỄN ĐĂNG KY
Ngày, tháng, năm sinh: 1933
Giới tính: Nam Dân tộc: Kinh Quốc tịch: Việt Nam
Họ, chữ đệm, tên người đi khai tử: Nguyễn Văn Kiến"""

_RAW_VAY_AS_CHILD = """<con>
Họ tên: DƯƠNG THỊ VẬY
Số CCCD/CMND: 027139005852
Ngày sinh: 01/01/1994
Giới tính: Nữ
</con>
<me>
Họ tên: Không xác định
</me>
"""
_RAW_UNKNOWN_FATHER = """<cha>
Họ tên: Không xác định
</cha>"""


def _lineage_documents():
    return [
        {"name": "PDF_023.pdf", "text": _NEW_CARD_THUC},
        {"name": "PDF_024.pdf", "text": _CARD_VAY},
        {"name": "PDF_025.pdf", "text": _DEATH_KY},
    ]


def _assert_thuc_ky_vay(context):
    assert reason._role_name(reason._section(context, "con")) == "NGUYỄN ĐĂNG THÚC"
    cha = reason._section(context, "cha")
    assert reason._role_name(cha) == "NGUYỄN ĐĂNG KY"
    assert "đã chết" in cha
    me = reason._section(context, "me")
    assert reason._role_name(me) == "DƯƠNG THỊ VẬY"
    assert "01/01/1939" in me


def test_person_parser_reads_new_identity_card_layout():
    person = reason._person_from_document({"name": "PDF_023.pdf", "text": _NEW_CARD_THUC})

    assert person["name"] == "NGUYỄN ĐĂNG THÚC"
    assert person["year"] == 1965
    assert person["id"] == "027065010250"
    assert person["issue_date"] == "10/02/2025"
    assert person["is_identity"] is True


def test_birth_year_follows_identity_number_when_ocr_misreads_card():
    person = reason._person_from_document({"name": "PDF_024.pdf", "text": _CARD_VAY})

    assert person["year"] == 1939
    assert reason.reconcile_birth_with_id("01/01/1994", "027139005852", "Nữ") == "01/01/1939"
    # Giới tính mã hoá trong số lệch giới tính in trên thẻ → chính con số bị đọc sai, không tin.
    assert reason.reconcile_birth_with_id("01/01/1994", "027139005852", "Nam") == "01/01/1994"
    # CMND 9 số không mã hoá năm sinh.
    assert reason.reconcile_birth_with_id("1994", "125452298", "Nữ") == "1994"


def test_no_declaration_youngest_by_ocr_is_actually_mother():
    raw = _RAW_VAY_AS_CHILD + _RAW_UNKNOWN_FATHER

    _assert_thuc_ky_vay(reason._render_context(raw, {}, _lineage_documents()))


def test_no_declaration_replaces_father_with_different_surname_by_lineage():
    raw = _RAW_VAY_AS_CHILD + """<cha>
Họ tên: NGUYỄN ĐĂNG THÚC
Số CCCD/CMND: 027065010250
Ngày sinh: 20/10/1965
Giới tính: Nam
</cha>"""

    _assert_thuc_ky_vay(reason._render_context(raw, {}, _lineage_documents()))


def test_no_declaration_fills_missing_mother_by_generation():
    raw = """<con>
Họ tên: NGUYỄN ĐĂNG THÚC
Số CCCD/CMND: 027065010250
Ngày sinh: 20/10/1965
Giới tính: Nam
</con>
<me>
Họ tên: Không xác định
</me>
<cha>
Họ tên: NGUYỄN ĐĂNG KY
Ngày sinh: 1933
Giới tính: Nam
Trạng thái: đã chết
</cha>"""

    _assert_thuc_ky_vay(reason._render_context(raw, {}, _lineage_documents()))


def test_lineage_repair_skips_when_several_same_surname_pairs():
    grandson = """CHỨNG MINH NHÂN DÂN
Số / No.: 125452298
Họ và tên / Full name: NGUYỄN ĐĂNG AN
Ngày sinh / Date of birth: 02/02/1990
Giới tính / Sex: Nam"""
    documents = _lineage_documents() + [{"name": "cmnd-an.pdf", "text": grandson}]
    sections = {"con": "", "cha": "", "me": ""}

    assert reason._repair_family_by_lineage(sections, documents) == sections


def test_sanitizer_drops_requester_fields_and_fixes_mother_birth_year():
    raw = _RAW_VAY_AS_CHILD + _RAW_UNKNOWN_FATHER
    context = reason._render_context(raw, {}, _lineage_documents())
    fields = [
        {"name": "Subject_FullName", "comp": "x-input", "value": "NGUYỄN ĐĂNG THÚC"},
        {"name": "Subject_IdNumber", "comp": "x-input", "value": "027065010250"},
        {"name": "Mother_FullName", "comp": "x-input", "value": "DƯƠNG THỊ VẬY"},
        {"name": "Mother_IdNumber", "comp": "x-input", "value": "027139005852"},
        {"name": "Mother_BirthDateOrYear", "comp": "x-input", "value": "01/01/1994"},
        {"name": "Requester_RelationToSubject", "comp": "x-input", "value": "Khác"},
    ]

    values = {f["name"]: f["value"] for f in reason.sanitize_extracted_fields(fields, context)}

    assert values["Subject_FullName"] == "NGUYỄN ĐĂNG THÚC"
    assert values["Mother_FullName"] == "DƯƠNG THỊ VẬY"
    assert values["Mother_BirthDateOrYear"] == "01/01/1939"
    assert "Requester_RelationToSubject" not in values


# ---------------------------------------------------------------------------
# Giấy ủy quyền: người yêu cầu là BÊN ĐƯỢC ỦY QUYỀN (dữ liệu bịa).
# ---------------------------------------------------------------------------

_AUTHORIZATION_LETTER = """───── Trang 1/2 ─────
CĂN CƯỚC CÔNG DÂN
Số / No.: 001190000111
Họ và tên / Full name: TRẦN THỊ MẪU
Ngày sinh / Date of birth: 02/03/1990
Giới tính / Sex: Nữ Quốc tịch / Nationality: Việt Nam
───── Trang 2/2 ─────
GIẤY ỦY QUYỀN
I. BÊN ỦY QUYỀN:
Ông/bà: Trần Thị Mẫu Sinh năm: 1990
Số CCCD: 001190000111
Nơi thường trú: Thôn Một - Tiên Du - Bắc Ninh
II. BÊN ĐƯỢC ỦY QUYỀN:
Ông/bà: Lê Văn Thử Sinh năm: 1985
Số CCCD: 001085000222
Nơi thường trú: Thôn Hai - Phương Liễu - TP Bắc Ninh
III. NỘI DUNG ỦY QUYỀN:
Nộp hồ sơ Đăng ký khai sinh lại
- Mọi tranh chấp phát sinh giữa bên ủy quyền và bên được ủy quyền sẽ do hai bên tự giải quyết.
BÊN UỶ QUYỀN BÊN ĐƯỢC ỦY QUYỀN
Trần Thị Mẫu Lê Văn Thử
"""


def _authorization_context(text=_AUTHORIZATION_LETTER) -> str:
    block = reason._render_authorized([{"name": "ho_so.pdf", "text": text}])
    return f"<phan_vai_da_xac_dinh>\n{block}</phan_vai_da_xac_dinh>"


def _authorization_ui(fields, context, applicant=("TRẦN THỊ MẪU", "001190000111")):
    from app.pipelines.khai_sinh_dang_ky_lai.process import mapper

    out = mapper.enrich(fields, {
        "_reasoning_context": context,
        "formContext": {"applicantFullname": applicant[0], "applicantIdentityNumber": applicant[1]},
    })
    return {field["name"]: field for field in out}


def test_authorization_letter_reads_authorized_party_not_authorizer():
    section = reason._section(_authorization_context(), "nguoi_duoc_uy_quyen")

    assert reason._labeled_value(section, "Họ tên") == "Lê Văn Thử"
    assert reason._labeled_value(section, "Số CCCD/CMND") == "001085000222"
    assert reason._labeled_value(section, "Năm sinh") == "1985"
    assert reason._labeled_value(section, "Nơi cư trú") == "Thôn Hai - Phương Liễu - TP Bắc Ninh"


def test_authorization_letter_inline_header_format():
    text = (
        "GIẤY ỦY QUYỀN\n"
        "Bên ủy quyền: Bà Trần Thị Mẫu, sinh năm 1990\n"
        "Bên được ủy quyền: Ông Lê Văn Thử, sinh năm 1985, CCCD số 001085000222 cấp ngày 05/06/2022\n"
        "Nội dung ủy quyền: nộp hồ sơ\n"
    )
    section = reason._section(_authorization_context(text), "nguoi_duoc_uy_quyen")

    assert reason._labeled_value(section, "Họ tên") == "Lê Văn Thử"
    assert reason._labeled_value(section, "Số CCCD/CMND") == "001085000222"
    assert reason._labeled_value(section, "Ngày cấp") == "05/06/2022"


def test_no_authorization_letter_renders_nothing():
    text = "CĂN CƯỚC CÔNG DÂN\nHọ và tên / Full name: TRẦN THỊ MẪU\n"
    assert reason._render_authorized([{"name": "cccd.jpg", "text": text}]) == ""


def test_authorized_party_becomes_requester_without_declaration():
    fields = [
        {"name": "Subject_FullName", "value": "TRẦN THỊ MẪU"},
        {"name": "Subject_IdNumber", "value": "001190000111"},
    ]
    ui = _authorization_ui(fields, _authorization_context())

    assert ui["QuanHe"]["value"] == "Khac"
    assert not ui["QuanHe"].get("default")
    assert ui["HoVaTenC"]["value"] == "LÊ VĂN THỬ"
    assert ui["SoDinhDanhC"]["value"] == "001085000222"
    assert ui["LoaiGiayToDinhDanhC"]["default"] is True
    # Nhân thân tài khoản đăng nhập (người khác) không được sót lại ở mục I.
    assert ui["NgayCapDDC"].get("clear") is True
    assert ui["nycNoiCuTru_TrongNuoc"]["value"]["tinh"] == "Bắc Ninh"
    assert ui["nycNoiCuTru_TrongNuoc"]["value"]["diaChi"] == "Thôn Hai"


def test_authorized_party_wins_over_declaration_requester():
    fields = [
        {"name": "Requester_SourceDocumentTitle", "value": "TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH"},
        {"name": "Requester_FullName", "value": "TRẦN THỊ MẪU"},
        {"name": "Requester_RelationToSubject", "value": "Bản thân"},
        {"name": "Subject_FullName", "value": "TRẦN THỊ MẪU"},
    ]
    ui = _authorization_ui(fields, _authorization_context())

    assert ui["QuanHe"]["value"] == "Khac"
    assert ui["HoVaTenC"]["value"] == "LÊ VĂN THỬ"


def test_agent_authorized_fields_for_authorizer_are_ignored():
    fields = [
        {"name": "Subject_FullName", "value": "TRẦN THỊ MẪU"},
        {"name": "Authorized_SourceDocumentTitle", "value": "GIẤY ỦY QUYỀN"},
        {"name": "Authorized_FullName", "value": "TRẦN THỊ MẪU"},
        {"name": "Authorized_IdNumber", "value": "001190000111"},
        {"name": "Authorized_IdIssueDate", "value": "01/01/2021"},
    ]
    ui = _authorization_ui(fields, _authorization_context())

    assert ui["HoVaTenC"]["value"] == "LÊ VĂN THỬ"
    assert ui["SoDinhDanhC"]["value"] == "001085000222"
    assert ui["NgayCapDDC"].get("clear") is True


def test_agent_authorized_fields_used_when_python_found_no_block():
    fields = [
        {"name": "Subject_FullName", "value": "TRẦN THỊ MẪU"},
        {"name": "Authorized_SourceDocumentTitle", "value": "GIẤY ỦY QUYỀN"},
        {"name": "Authorized_FullName", "value": "Lê Văn Thử"},
        {"name": "Authorized_IdNumber", "value": "001085000222"},
        {"name": "Authorized_IdIssueDate", "value": "05/06/2022"},
    ]
    ui = _authorization_ui(fields, "")

    assert ui["QuanHe"]["value"] == "Khac"
    assert ui["HoVaTenC"]["value"] == "LÊ VĂN THỬ"
    assert ui["NgayCapDDC"]["value"] == "05/06/2022"
    assert ui["NoiCapDDC"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert not ui["LoaiGiayToDinhDanhC"].get("default")
