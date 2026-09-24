"""Phân vai con/cha/mẹ theo thế hệ khi hồ sơ đăng ký lại khai sinh chỉ có 3 CCCD hoặc 2 CCCD + khai tử.

Dữ liệu trong file này là dữ liệu bịa.
"""

from app.pipelines.khai_sinh_dang_ky_lai.process import reason


def _card(name, id_number, birth, gender="Nam"):
    gender_line = f"Giới tính / Sex: {gender} " if gender else ""
    return (
        "CĂN CƯỚC CÔNG DÂN\n"
        f"Số / No.: {id_number}\n"
        f"Họ và tên / Full name: {name}\n"
        f"Ngày sinh / Date of birth: {birth}\n"
        f"{gender_line}Quốc tịch / Nationality: Việt Nam"
    )


def _death(name, birth, gender="Nam"):
    return (
        "TRÍCH LỤC KHAI TỬ\n"
        "Phần ghi về người được khai tử:\n"
        f"Họ, chữ đệm, tên: {name}\n"
        f"Ngày, tháng, năm sinh: {birth}\n"
        f"Giới tính: {gender} Dân tộc: Kinh Quốc tịch: Việt Nam\n"
        "Giấy tờ tùy thân: Căn cước công dân số 001070000222\n"
        "Họ, chữ đệm, tên người đi khai tử: PHẠM VĂN DŨNG"
    )


_CHILD = _card("TRẦN VĂN BÌNH", "001098000111", "05/06/1998")
_FATHER = _card("TRẦN VĂN AN", "001070000222", "01/02/1970")
_MOTHER = _card("LÊ THỊ CÚC", "001172000333", "03/04/1972", gender="Nữ")


def _docs(*texts):
    return [{"name": f"file-{index}.pdf", "text": text} for index, text in enumerate(texts, 1)]


def _roles(context):
    return {tag: reason._role_name(reason._section(context, tag)) for tag in ("con", "cha", "me")}


# Agent tráo hết vai: mẹ vào <con>, con vào <cha>, cha vào <me>.
_RAW_SWAPPED = """<con>
Họ tên: LÊ THỊ CÚC
Số CCCD/CMND: 001172000333
Ngày sinh: 03/04/1972
Giới tính: Nữ
</con>
<cha>
Họ tên: TRẦN VĂN BÌNH
Số CCCD/CMND: 001098000111
Ngày sinh: 05/06/1998
Giới tính: Nam
</cha>
<me>
Họ tên: TRẦN VĂN AN
Số CCCD/CMND: 001070000222
Ngày sinh: 01/02/1970
Giới tính: Nam
</me>"""


def test_three_cards_override_swapped_agent_roles():
    context = reason._render_context(_RAW_SWAPPED, {}, _docs(_MOTHER, _CHILD, _FATHER))

    assert _roles(context) == {"con": "TRẦN VĂN BÌNH", "cha": "TRẦN VĂN AN", "me": "LÊ THỊ CÚC"}


def test_two_cards_and_death_certificate_dead_father_never_child():
    raw = """<con>
Họ tên: TRẦN VĂN AN
Ngày sinh: 01/02/1970
Giới tính: Nam
Trạng thái: đã chết
</con>"""
    documents = _docs(_CHILD, _MOTHER, _death("TRẦN VĂN AN", "01/02/1970"))

    context = reason._render_context(raw, {}, documents)

    assert _roles(context) == {"con": "TRẦN VĂN BÌNH", "cha": "TRẦN VĂN AN", "me": "LÊ THỊ CÚC"}
    assert "đã chết" in reason._section(context, "cha")


def test_death_certificate_mentioning_citizen_card_is_not_identity_card():
    person = reason._person_from_document({"name": "kt.pdf", "text": _death("TRẦN VĂN AN", "1970")})

    assert person["is_identity"] is False
    assert "đã chết" in person["section"]


def test_old_death_certificate_layout_is_read():
    text = (
        "GIẤY CHỨNG TỬ\n"
        "Họ và tên người chết: LÊ THỊ CÚC\n"
        "Ngày, tháng, năm sinh: 1972\n"
        "Giới tính: Nữ Dân tộc: Kinh"
    )
    person = reason._person_from_document({"name": "ct.pdf", "text": text})

    assert person["name"] == "LÊ THỊ CÚC"
    assert person["year"] == 1972
    assert person["is_identity"] is False


def test_card_without_gender_line_uses_identity_number():
    mother_no_gender = _card("LÊ THỊ CÚC", "001172000333", "03/04/1972", gender="")
    person = reason._person_from_document({"name": "cccd.pdf", "text": mother_no_gender})

    assert reason._fold(person["gender"]) == "nu"
    context = reason._render_context("", {}, _docs(_CHILD, _FATHER, mother_no_gender))
    assert _roles(context)["me"] == "LÊ THỊ CÚC"


def test_one_line_health_card_name_stops_at_next_label():
    # Thẻ BHYT in cả tấm trên một dòng, nằm chung trang với CCCD của cùng người.
    text = (
        "THẺ BẢO HIỂM Y TẾ\n"
        "Họ và tên: LÊ THỊ CÚC Giới tính: Nữ Ngày sinh: 03/04/1972 Địa chỉ: 12 Đường A, Phường B\n"
        + _card("LÊ THỊ CÚC", "001172000333", "03/04/1972", gender="Nữ")
    )
    person = reason._person_from_document({"name": "cccd.pdf", "text": text})

    assert person["name"] == "LÊ THỊ CÚC"
    assert person["id"] == "001172000333"


def test_card_name_cut_at_household_book_gender_label():
    text = _card("TRẦN VĂN BÌNH Nam/nữ: Nam", "001098000111", "05/06/1998")
    person = reason._person_from_document({"name": "cccd.pdf", "text": text})

    assert person["name"] == "TRẦN VĂN BÌNH"


def test_father_and_son_with_same_name_stay_two_people():
    son = _card("TRẦN VĂN AN", "001098000111", "05/06/1998")

    context = reason._render_context("", {}, _docs(son, _FATHER, _MOTHER))

    assert reason._role_year(reason._section(context, "con")) == 1998
    assert reason._role_year(reason._section(context, "cha")) == 1970


def test_dead_father_with_card_and_death_certificate_counts_once():
    documents = _docs(_CHILD, _MOTHER, _FATHER, _death("TRẦN VĂN AN", "01/02/1970"))

    context = reason._render_context("", {}, documents)

    assert _roles(context) == {"con": "TRẦN VĂN BÌNH", "cha": "TRẦN VĂN AN", "me": "LÊ THỊ CÚC"}
    father = reason._section(context, "cha")
    assert "đã chết" in father
    assert "001070000222" in father


def test_override_skips_when_woman_is_too_old_to_be_mother():
    grandmother = _card("LÊ THỊ CÚC", "001140000333", "03/04/1940", gender="Nữ")
    sections = {"con": "", "cha": "", "me": ""}

    assert reason._override_family_by_generation(sections, _docs(_CHILD, _FATHER, grandmother)) == sections


def test_override_skips_when_child_surname_differs_from_father():
    helper = _card("PHẠM VĂN DŨNG", "001070000222", "01/02/1970")
    sections = {"con": "", "cha": "", "me": ""}

    assert reason._override_family_by_generation(sections, _docs(_CHILD, helper, _MOTHER)) == sections


def test_override_skips_when_old_birth_certificate_has_labels():
    birth = "GIẤY KHAI SINH\nHọ và tên: TRẦN VĂN BÌNH\nHọ và tên cha: TRẦN VĂN AN"
    sections = {"con": "", "cha": "", "me": ""}

    assert reason._override_family_by_generation(sections, _docs(_CHILD, _FATHER, _MOTHER, birth)) == sections


def test_override_keeps_agent_extra_facts_for_same_person():
    raw = """<con>
Họ tên: TRẦN VĂN BÌNH
Số CCCD/CMND: 001098000111
Ngày sinh: 05/06/1998
Giới tính: Nam
Dân tộc: Tày
</con>"""

    context = reason._render_context(raw, {}, _docs(_CHILD, _FATHER, _MOTHER))

    assert reason._labeled_value(reason._section(context, "con"), "Dân tộc") == "Tày"
