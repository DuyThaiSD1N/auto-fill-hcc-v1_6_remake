"""Phân vai hồ sơ đăng ký lại khai sinh trước bước trích field.

Agent chỉ trả text phân vai. Python kiểm tra lại mỏ neo người, giới tính, thế hệ
và loại tài liệu trước khi cho kết quả này điều khiển agent trích xuất.
"""

import re
import unicodedata

from app.config import settings
from app.services.llm import client

_REASON_MAX_TOKENS = 1100
_FAMILY_TAGS = ("con", "me", "cha")
_ROLE_PREFIX = {
    "con": "Subject_",
    "me": "Mother_",
    "cha": "Father_",
}
_FULL_NAME_FIELD = {
    "con": "Subject_FullName",
    "me": "Mother_FullName",
    "cha": "Father_FullName",
}
_ID_FIELD = {
    "me": "Mother_IdNumber",
    "cha": "Father_IdNumber",
}
_CONTEXT_EVIDENCE_FIELDS = {
    "Subject_Ethnicity": ("con", "Dân tộc"),
    "Subject_Nationality": ("con", "Quốc tịch"),
    "Mother_Ethnicity": ("me", "Dân tộc"),
    "Mother_Nationality": ("me", "Quốc tịch"),
    "Father_Ethnicity": ("cha", "Dân tộc"),
    "Father_Nationality": ("cha", "Quốc tịch"),
}
_ROLE_TAGS = (
    "nguoi_yeu_cau",
    "con",
    "me",
    "cha",
    "dang_ky_khai_sinh_truoc_day",
)
_IDENTITY_MARKERS = (
    "can cuoc cong dan",
    "citizen identity card",
    "can cuoc",
    "identity card",
    "chung minh nhan dan",
)

_ROLE_PROMPT = """
Bạn là agent PHÂN VAI hồ sơ ĐĂNG KÝ LẠI KHAI SINH. Chỉ xác định:
- người yêu cầu;
- người được đăng ký lại khai sinh (CON);
- MẸ;
- CHA;
- hồ sơ có hay không có tài liệu ghi nhận ĐĂNG KÝ KHAI SINH trước đây.

Đọc toàn bộ OCR, không trích field biểu mẫu, không trả JSON.

THỨ TỰ PHÂN VAI:
1. Ưu tiên nhãn rõ trên tờ khai đăng ký lại khai sinh, giấy khai sinh cũ hoặc trích lục khai sinh:
   "người được khai sinh/con", "mẹ", "cha".
2. Giấy khai tử chỉ chứng minh danh tính, năm sinh, giới tính và trạng thái đã chết của người trên giấy.
   KHÔNG mặc định người trong giấy khai tử là cha/mẹ. Chỉ gán cha/mẹ khi có quan hệ rõ hoặc khi quy tắc
   thế hệ tại mục 3 xác định được duy nhất.
3. Khi không có nhãn quan hệ nhưng hồ sơ thể hiện đúng một gia đình hợp lý:
   - người có năm sinh lớn nhất/gần hiện tại nhất là con;
   - người nam lớn hơn con ít nhất khoảng 15 tuổi là cha;
   - người nữ lớn hơn con ít nhất khoảng 15 tuổi là mẹ.
   Chỉ áp dụng khi mỗi vai có đúng một ứng viên và con trùng họ với ít nhất một người thuộc thế hệ trước;
   mơ hồ thì ghi "Không xác định".
4. CCCD/CMND chỉ cho biết thông tin của chính người trên thẻ. Tên file và thứ tự tải lên chỉ là tín hiệu
   phụ, không đủ để tự gán vai.
5. Người yêu cầu lấy theo requester_context: khớp chính xác số định danh trước, thiếu số mới khớp họ tên.
   Người yêu cầu có thể đồng thời là con, cha hoặc mẹ.
6. Vợ/chồng, người ký, chủ hộ, người nhận công văn không tự động là cha/mẹ/con.
7. Một người không được đồng thời là con và cha/mẹ. Không ghép tên, số định danh, ngày sinh hoặc nguồn
   của hai người khác nhau.
8. "Số/ngày đăng ký trước đây" chỉ hợp lệ khi thuộc GIẤY KHAI SINH, TRÍCH LỤC KHAI SINH hoặc
   TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH. Số/ngày trên giấy khai tử, kết hôn, CCCD không hợp lệ.

Chỉ trả TEXT theo đúng năm khối sau, không markdown/code fence và không thêm JSON:
Mỗi nhãn đúng một dòng; "Căn cứ phân vai" tối đa 20 từ. Chỉ ghi KẾT LUẬN, không trình bày chuỗi suy luận.
<nguoi_yeu_cau>
Họ tên: ...
Số CCCD/CMND: ...
Ngày sinh: ...
Giới tính: ...
Dân tộc: ...
Quốc tịch: ...
Nguồn: ...
Căn cứ phân vai: ...
Vai trò đồng thời: con|mẹ|cha|không xác định
</nguoi_yeu_cau>
<con>
Họ tên: ...
Số CCCD/CMND: ...
Ngày sinh: ...
Giới tính: ...
Dân tộc: ...
Quốc tịch: ...
Trạng thái: còn sống|đã chết|không xác định
Nguồn: ...
Căn cứ phân vai: ...
</con>
<me>
Họ tên: ...
Số CCCD/CMND: ...
Ngày sinh: ...
Giới tính: ...
Dân tộc: ...
Quốc tịch: ...
Trạng thái: còn sống|đã chết|không xác định
Nguồn: ...
Căn cứ phân vai: ...
</me>
<cha>
Họ tên: ...
Số CCCD/CMND: ...
Ngày sinh: ...
Giới tính: ...
Dân tộc: ...
Quốc tịch: ...
Trạng thái: còn sống|đã chết|không xác định
Nguồn: ...
Căn cứ phân vai: ...
</cha>
<dang_ky_khai_sinh_truoc_day>
Có tài liệu khai sinh hợp lệ: Có|Không
Nguồn: ...
Căn cứ: ...
</dang_ky_khai_sinh_truoc_day>
""".strip()


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d").lower()
    return re.sub(r"\s+", " ", text).strip()


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _section(text: str, tag: str) -> str:
    raw = str(text or "")
    opening = re.search(rf"<{tag}>\s*", raw, flags=re.IGNORECASE)
    if not opening:
        return ""
    remainder = raw[opening.end():]
    closing = re.search(rf"\s*</{tag}>", remainder, flags=re.IGNORECASE)
    if closing:
        return remainder[:closing.start()].strip()

    # Model có thể hết max_tokens trước thẻ đóng. Vẫn lấy đến khối kế tiếp/EOF
    # để một khối cuối bị cụt không làm mất toàn bộ kết quả phân vai.
    other_tags = "|".join(re.escape(item) for item in _ROLE_TAGS if item != tag)
    next_opening = re.search(rf"\s*<(?:{other_tags})>", remainder, flags=re.IGNORECASE)
    return remainder[:next_opening.start()].strip() if next_opening else remainder.strip()


def _labeled_value(section: str, label: str) -> str:
    match = re.search(
        rf"(?im)^\s*{re.escape(label)}\s*:\s*(.*?)\s*$",
        section,
    )
    return match.group(1).strip() if match else ""


def _requester_context(options: dict | None) -> tuple[str, str]:
    ctx = (options or {}).get("formContext") or {}
    return (
        str(ctx.get("applicantFullname") or "").strip(),
        _digits(ctx.get("applicantIdentityNumber")),
    )


def _is_unknown(section: str) -> bool:
    if not section:
        return True
    name = _fold(_labeled_value(section, "Họ tên"))
    return not name or "khong xac dinh" in name


def _role_name(section: str) -> str:
    if _is_unknown(section):
        return ""
    return _labeled_value(section, "Họ tên")


def _role_id(section: str) -> str:
    value = _digits(_labeled_value(section, "Số CCCD/CMND"))
    return value if len(value) in {9, 12} else ""


def _role_year(section: str) -> int | None:
    value = _labeled_value(section, "Ngày sinh")
    years = re.findall(r"(?<!\d)(?:18|19|20)\d{2}(?!\d)", value)
    return int(years[-1]) if years else None


def _unknown_role_section(reason: str) -> str:
    return (
        "Họ tên: Không xác định\n"
        "Số CCCD/CMND: Không xác định\n"
        "Ngày sinh: Không xác định\n"
        "Giới tính: Không xác định\n"
        "Dân tộc: Không xác định\n"
        "Quốc tịch: Không xác định\n"
        "Trạng thái: Không xác định\n"
        "Nguồn: Không xác định\n"
        f"Căn cứ phân vai: {reason}"
    )


def _as_family_section(section: str, basis: str) -> str:
    if not _labeled_value(section, "Trạng thái"):
        section += "\nTrạng thái: Không xác định"
    return section + f"\nCăn cứ kiểm tra thế hệ: {basis}"


def _first_match(text: str, patterns: tuple[str, ...]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


def _person_from_document(document: dict) -> dict | None:
    """Đọc nhân thân chính của CCCD hoặc người được khai tử ngay từ OCR."""
    text = str(document.get("text") or "")
    folded = _fold(text)
    is_identity = any(marker in folded for marker in _IDENTITY_MARKERS)
    death_match = re.search(
        r"Phần\s+ghi\s+về\s+người\s+được\s+khai\s+tử\s*:",
        text,
        flags=re.IGNORECASE,
    )
    is_death = bool(
        death_match
        or "trich luc khai tu" in folded
        or "giay bao tu" in folded
    )
    if not is_identity and not is_death:
        return None

    # Với sổ/trích lục khai tử, chỉ đọc phần người được khai tử; không lấy người
    # đi khai tử, người ký hay cán bộ xuất hiện phía sau.
    block = text[death_match.end():] if death_match else text
    name = _first_match(block, (
        r"^\s*Họ\s+và\s+tên(?:\s*/\s*Full\s*name)?\s*:\s*([^\n\r]+)",
        r"^\s*Họ,\s*chữ\s*đệm(?:,\s*|\s+và\s+)tên\s*:\s*([^\n\r]+)",
        r"^\s*Họ,\s*chữ\s*đệm,\s*tên\s*:\s*([^\n\r]+)",
    ))
    birth = _first_match(block, (
        r"^\s*Ngày\s+sinh(?:\s*/\s*Date\s+of\s+birth)?\s*:\s*([^\n\r]+)",
        r"^\s*Ngày,\s*tháng,\s*năm\s+sinh\s*:\s*([^\n\r]+)",
    ))
    gender = _first_match(block, (
        r"Giới\s*tính(?:\s*/\s*Sex)?\s*:\s*(Nam|Nữ|Male|Female)",
    ))
    id_number = _first_match(block, (
        r"Số\s*/\s*No\.?\s*:\s*([0-9 ]{9,})",
        r"Số\s+định\s+danh\s+cá\s+nhân(?:\s*/[^:\n]+)?\s*:\s*([0-9 ]{9,})",
    ))
    ethnicity = _first_match(block, (
        r"Dân\s*tộc\s*:\s*([^\n\r]+?)(?=\s+Quốc\s*tịch|$)",
    ))
    nationality = _first_match(block, (
        r"Quốc\s*tịch(?:\s*/\s*Nationality)?\s*:?\s*([^\n\r]+)",
    ))
    if not name or not birth or not gender:
        return None

    status = "đã chết" if is_death else "không xác định"
    section = (
        f"Họ tên: {name}\n"
        f"Số CCCD/CMND: {_digits(id_number) or 'Không xác định'}\n"
        f"Ngày sinh: {birth}\n"
        f"Giới tính: {gender}\n"
        f"Dân tộc: {ethnicity or 'Không xác định'}\n"
        f"Quốc tịch: {nationality or 'Không xác định'}\n"
        f"Trạng thái: {status}\n"
        f"Nguồn: {document.get('name') or '(không tên)'}\n"
        "Căn cứ phân vai: Nhân thân chính đọc trực tiếp từ OCR của tài liệu."
    )
    return {
        "section": section,
        "name": name,
        "year": _role_year(section),
        "gender": _fold(gender),
        "score": 10,
    }


def _repair_family_by_generation(
    raw: str,
    sections: dict[str, str],
    documents: list[dict],
) -> dict[str, str]:
    """Chốt ca đúng ba người khi nhãn quan hệ thiếu nhưng thế hệ xác định duy nhất.

    Mỗi người có thể xuất hiện hai lần (người yêu cầu đồng thời là cha/mẹ/con),
    nên gom theo họ tên trước khi xét năm sinh.
    """
    # Ưu tiên nhân thân được Python đọc trực tiếp từ từng tài liệu. Nhờ vậy raw
    # reason dài/bị cụt vẫn không làm mất người trẻ nhất hoặc nhầm giấy khai tử.
    document_candidates = [
        person
        for document in documents
        if (person := _person_from_document(document))
    ]
    candidates = {
        _fold(person["name"]): person
        for person in document_candidates
        if person.get("year")
    }

    if len(candidates) != 3:
        candidates = {}
        for tag in ("nguoi_yeu_cau", *_FAMILY_TAGS):
            section = _section(raw, tag)
            name = _role_name(section)
            year = _role_year(section)
            gender = _fold(_labeled_value(section, "Giới tính"))
            if not name or not year or gender not in {"nam", "nu", "male", "female"}:
                continue
            key = _fold(name)
            current = candidates.get(key)
            score = sum(bool(_labeled_value(section, label)) for label in (
                "Số CCCD/CMND", "Ngày sinh", "Giới tính", "Trạng thái", "Nguồn",
            ))
            if not current or score > current["score"]:
                candidates[key] = {
                    "section": section,
                    "name": name,
                    "year": year,
                    "gender": gender,
                    "score": score,
                }

    if len(candidates) != 3:
        return sections

    ordered = sorted(candidates.values(), key=lambda item: item["year"])
    youngest = ordered[-1]
    older = ordered[:-1]
    if youngest["year"] - max(item["year"] for item in older) < 15:
        return sections
    child_surname = _fold(youngest["name"]).split(" ", 1)[0]
    older_surnames = {_fold(item["name"]).split(" ", 1)[0] for item in older}
    if not child_surname or child_surname not in older_surnames:
        return sections

    men = [item for item in older if item["gender"] in {"nam", "male"}]
    women = [item for item in older if item["gender"] in {"nu", "female"}]
    if len(men) != 1 or len(women) != 1:
        return sections

    basis = "Đúng ba người, người trẻ nhất là con; hai người lớn hơn thuộc hai giới và cách ít nhất 15 năm."
    return {
        "con": _as_family_section(youngest["section"], basis),
        "cha": _as_family_section(men[0]["section"], basis),
        "me": _as_family_section(women[0]["section"], basis),
    }


def _valid_birth_source_names(documents: list[dict]) -> list[str]:
    """Chỉ nhận tài liệu thực sự ghi nhận khai sinh, không nhận giấy khai tử/kết hôn."""
    names: list[str] = []
    for document in documents:
        folded = _fold(document.get("text"))
        is_birth_record = (
            "giay khai sinh" in folded
            or "giay khai sanh" in folded
            or "trich luc khai sinh" in folded
            or (
                "to khai" in folded
                and "dang ky lai" in folded
                and "khai sinh" in folded
            )
        )
        if is_birth_record:
            names.append(str(document.get("name") or "(không tên)"))
    return names


def _source_hints(documents: list[dict], options: dict | None) -> str:
    requester_name, requester_id = _requester_context(options)
    valid_sources = _valid_birth_source_names(documents)
    return (
        "<requester_context>\n"
        f'Họ tên trên cổng: "{requester_name or "không có"}"\n'
        f'Số định danh trên cổng: "{requester_id or "không có"}"\n'
        "</requester_context>\n"
        "<birth_registration_source_check>\n"
        "Tài liệu khai sinh hợp lệ được Python nhận diện: "
        + (", ".join(valid_sources) if valid_sources else "Không có")
        + "\n</birth_registration_source_check>"
    )


def _build_user_content(documents: list[dict], options: dict | None) -> str:
    body = "\n\n---\n\n".join(
        f"===== Tài liệu {index}: {document.get('name') or '(không tên)'} =====\n"
        f"{str(document.get('text') or '').strip()}"
        for index, document in enumerate(documents, start=1)
    )
    return f"{_source_hints(documents, options)}\n\nOCR hồ sơ:\n\n{body}"


def _validated_requester(section: str, options: dict | None) -> str:
    requester_name, requester_id = _requester_context(options)
    if not requester_name and not requester_id:
        return section or _unknown_role_section("Cổng không truyền mỏ neo người yêu cầu.")

    section_id = _role_id(section)
    section_name = _fold(_role_name(section))
    id_matches = bool(requester_id and section_id and requester_id == section_id)
    name_matches = bool(requester_name and section_name and _fold(requester_name) == section_name)
    if id_matches or (not requester_id and name_matches):
        return section

    return (
        "Họ tên: Không xác định\n"
        "Số CCCD/CMND: Không xác định\n"
        "Ngày sinh: Không xác định\n"
        "Giới tính: Không xác định\n"
        "Dân tộc: Không xác định\n"
        "Quốc tịch: Không xác định\n"
        "Nguồn: Không xác định\n"
        "Căn cứ phân vai: Kết quả agent không khớp mỏ neo người yêu cầu trên cổng.\n"
        "Vai trò đồng thời: không xác định"
    )


def _validate_family_sections(sections: dict[str, str]) -> dict[str, str]:
    """Loại kết luận tự mâu thuẫn trước khi ghim vào prompt trích xuất."""
    result = dict(sections)

    # Cha/mẹ phải phù hợp giới tính khi OCR đã xác định rõ.
    if _fold(_labeled_value(result.get("cha", ""), "Giới tính")) in {"nu", "female"}:
        result["cha"] = _unknown_role_section("Ứng viên cha có giới tính Nữ.")
    if _fold(_labeled_value(result.get("me", ""), "Giới tính")) in {"nam", "male"}:
        result["me"] = _unknown_role_section("Ứng viên mẹ có giới tính Nam.")
    if "da chet" in _fold(_labeled_value(result.get("con", ""), "Trạng thái")):
        result["con"] = _unknown_role_section("Người được đăng ký lại khai sinh không thể là người đã chết.")

    # Một người không thể vừa là con vừa là cha/mẹ.
    child_id = _role_id(result.get("con", ""))
    child_name = _fold(_role_name(result.get("con", "")))
    for tag in ("cha", "me"):
        parent_id = _role_id(result.get(tag, ""))
        parent_name = _fold(_role_name(result.get(tag, "")))
        same_id = bool(child_id and parent_id and child_id == parent_id)
        same_name = bool(child_name and parent_name and child_name == parent_name)
        if same_id or same_name:
            result[tag] = _unknown_role_section("Trùng chính người đã được phân vai là con.")

    # Nếu có đủ năm sinh, cha/mẹ phải thuộc thế hệ trước con ít nhất khoảng 15 năm.
    child_year = _role_year(result.get("con", ""))
    if child_year:
        for tag in ("cha", "me"):
            parent_year = _role_year(result.get(tag, ""))
            if parent_year and child_year - parent_year < 15:
                result[tag] = _unknown_role_section(
                    "Năm sinh không tạo được khoảng cách thế hệ cha/mẹ - con hợp lý."
                )
    return result


def _render_context(raw: str, options: dict | None, documents: list[dict]) -> str:
    """Kiểm tra tất định kết quả LLM rồi ghim vào prompt trích xuất."""
    sections = {tag: _section(raw, tag) for tag in _FAMILY_TAGS}

    # Nếu LLM trả không ra ai → thử suy từ thế hệ (3 người, nam/nữ, cách 15 năm).
    if not any(not _is_unknown(s) for s in sections.values()):
        sections = _repair_family_by_generation(raw, sections, documents)

    if not any(not _is_unknown(s) for s in sections.values()):
        return ""

    sections = _validate_family_sections(sections)

    # Người yêu cầu: kiểm tra khớp mỏ neo cổng.
    requester_raw = _section(raw, "nguoi_yeu_cau")
    requester = _validated_requester(requester_raw, options)

    # Đăng ký khai sinh trước đây: Python tự kiểm tra loại tài liệu (không tin LLM).
    valid_sources = _valid_birth_source_names(documents)
    registration_value = "Có" if valid_sources else "Không"
    source_value = ", ".join(valid_sources) if valid_sources else "Không có"

    return (
        "\n\n<phan_vai_da_xac_dinh>\n"
        "Dùng đúng các vai dưới đây; không tự đổi người giữa Subject/Father/Mother.\n"
        "<nguoi_yeu_cau>\n"
        f"{requester}\n"
        "</nguoi_yeu_cau>\n"
        "<con>\n"
        f"{sections.get('con') or _unknown_role_section('Agent không xác định được.')}\n"
        "</con>\n"
        "<me>\n"
        f"{sections.get('me') or _unknown_role_section('Agent không xác định được.')}\n"
        "</me>\n"
        "<cha>\n"
        f"{sections.get('cha') or _unknown_role_section('Agent không xác định được.')}\n"
        "</cha>\n"
        "<dang_ky_khai_sinh_truoc_day>\n"
        f"Có tài liệu khai sinh hợp lệ: {registration_value}\n"
        f"Nguồn: {source_value}\n"
        "Căn cứ: Kết quả kiểm tra trực tiếp loại tài liệu OCR bằng Python.\n"
        "</dang_ky_khai_sinh_truoc_day>\n"
        "Subject_* chỉ thuộc <con>; Mother_* chỉ thuộc <me>; Father_* chỉ thuộc <cha>. "
        "Nếu một khối ghi Không xác định thì bỏ toàn bộ field của vai đó. "
        "PreviousRegistration_* chỉ được trả khi khối đăng ký khai sinh trước đây ghi Có.\n"
        "</phan_vai_da_xac_dinh>"
    )


def _identity_matches(fields_by_name: dict, context: str, tag: str) -> bool:
    section = _section(context, tag)
    if _is_unknown(section):
        return False

    expected_name = _fold(_role_name(section))
    actual_name = _fold(fields_by_name.get(_FULL_NAME_FIELD[tag]))
    expected_id = _role_id(section)
    actual_id = _digits(fields_by_name.get(_ID_FIELD.get(tag, "")))

    if expected_id and actual_id:
        return expected_id == actual_id
    return bool(expected_name and actual_name and expected_name == actual_name)


def sanitize_extracted_fields(fields: list[dict], context: str) -> list[dict]:
    """Không cho field của một người chảy sang vai khác sau bước trích xuất."""
    if not context:
        return fields

    values = {
        field.get("name"): field.get("value")
        for field in fields
        if field.get("name")
    }
    invalid_prefixes = {
        _ROLE_PREFIX[tag]
        for tag in _FAMILY_TAGS
        if not _identity_matches(values, context, tag)
    }
    registration = _section(context, "dang_ky_khai_sinh_truoc_day")
    has_birth_source = _fold(
        _labeled_value(registration, "Có tài liệu khai sinh hợp lệ")
    ) == "co"

    result: list[dict] = []
    for field in fields:
        name = str(field.get("name") or "")
        if any(name.startswith(prefix) for prefix in invalid_prefixes):
            continue
        evidence = _CONTEXT_EVIDENCE_FIELDS.get(name)
        if evidence:
            tag, label = evidence
            value = _fold(_labeled_value(_section(context, tag), label))
            if not value or "khong xac dinh" in value or value == "khong co":
                continue
        if name.startswith("PreviousRegistration_") and not has_birth_source:
            continue
        result.append(field)
    return result


async def build_context(documents: list[dict], options: dict | None = None) -> str:
    """OCR docs -> text phân vai đã qua kiểm tra tất định."""
    if not documents:
        return ""
    messages = [
        {"role": "system", "content": _ROLE_PROMPT},
        {"role": "user", "content": _build_user_content(documents, options)},
    ]
    raw = await client.chat(
        messages,
        max_tokens=_REASON_MAX_TOKENS,
        temperature=0,
        enable_thinking=settings.agent_reasoning,
    )
    return _render_context(raw, options, documents)
