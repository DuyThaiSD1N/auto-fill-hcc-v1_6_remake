"""Extract and deterministically validate Justice owner-page values."""

import re
import unicodedata

from app.pipelines._shared.compact_agent import runner

from .prompt import build_rules
from .schema import ISSUE_PLACE_OPTIONS, allowed_for, comp_by_name_for, fields_for


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _field_map(fields: list[dict]) -> dict[str, object]:
    return {str(field.get("name")): field.get("value") for field in fields if field.get("name")}


def _detailed_address(value) -> str:
    """Owner page accepts a scalar detail, not the compact agent's address object."""
    if isinstance(value, dict):
        return str(value.get("diaChi") or value.get("dia_chi") or value.get("diachi") or "").strip()
    return str(value or "").strip()


def _owner_issue_place(value) -> str:
    """Map OCR/LLM variants to the four exact React Select labels; unknown stays empty."""
    folded = _fold(value)
    if not folded:
        return ""
    by_fold = {_fold(option): option for option in ISSUE_PLACE_OPTIONS}
    if folded in by_fold:
        return by_fold[folded]

    compact = re.sub(r"[^a-z0-9]+", "", folded)
    if (
        "du lieu quoc gia ve dan cu" in folded
        or "dang ky quan ly cu tru" in folded
        or "dlqgvedancu" in compact
        or "dkqlcutru" in compact
    ):
        return ISSUE_PLACE_OPTIONS[0]
    if (
        "quan ly hanh chinh ve trat tu xa hoi" in folded
        or ("qlhc" in compact and "ttxh" in compact)
        or "cucsqlhc" in compact
        or "ccsqlhc" in compact
    ):
        return ISSUE_PLACE_OPTIONS[1]
    if "quan ly xuat nhap canh" in folded or "immigration department" in folded:
        return ISSUE_PLACE_OPTIONS[3]
    if "bo cong an" in folded or "ministry of public security" in folded:
        return ISSUE_PLACE_OPTIONS[2]
    return ""


def owner_matches(owner_context: dict, extracted: dict) -> bool:
    """A matching full name or identity number is sufficient for the approved owner gate."""
    expected_name = _fold(owner_context.get("fullName"))
    actual_name = _fold(extracted.get("Owner_FullName"))
    expected_id = _digits(owner_context.get("identityNumber"))
    actual_id = _digits(extracted.get("Owner_IdentityNumber"))
    name_match = bool(expected_name and actual_name and expected_name == actual_name)
    id_match = bool(expected_id and actual_id and expected_id == actual_id)
    return name_match or id_match


def _person_matches(owner_context: dict, full_name, identity_number) -> tuple[bool, bool, bool]:
    expected_name = _fold(owner_context.get("fullName"))
    expected_id = _digits(owner_context.get("identityNumber"))
    actual_name = _fold(full_name)
    actual_id = _digits(identity_number)
    by_name = bool(expected_name and actual_name and expected_name == actual_name)
    by_id = bool(expected_id and actual_id and expected_id == actual_id)
    # Giấy ủy quyền có đủ cả tên và số giấy tờ thì phải khớp cả hai; không để một
    # CCCD đúng nhưng vai trò/tên sai (hoặc ngược lại) vượt qua cổng đối chiếu.
    if expected_name and actual_name and expected_id and actual_id:
        matched = by_name and by_id
    elif expected_id and actual_id:
        matched = by_id
    else:
        matched = by_name
    return matched, by_name, by_id


def _has_authorization_document(ocr_text) -> bool:
    folded = _fold(ocr_text)
    title_markers = (
        "giay uy quyen", "van ban uy quyen", "hop dong uy quyen",
    )
    role_pair = (
        ("ben uy quyen" in folded or "nguoi uy quyen" in folded)
        and ("ben duoc uy quyen" in folded or "nguoi duoc uy quyen" in folded)
    )
    return any(marker in folded for marker in title_markers) or role_pair


def _document_number(value) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip().upper()


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    owner_context = dict((options or {}).get("ownerContext") or {})
    include_authorization = (options or {}).get("executionSubject") == "authorized_person"
    fields = fields_for(include_authorization)
    allowed = allowed_for(include_authorization)
    comp_by_name = comp_by_name_for(include_authorization)
    res = await runner.run(
        files_by_role,
        fields=fields,
        allowed=allowed,
        comp_by_name=comp_by_name,
        extra_rules=build_rules(owner_context, include_authorization),
        options=options,
        max_tokens=1900 if include_authorization else 1400,
    )
    values = _field_map(res.get("fields") or [])
    matched = owner_matches(owner_context, values)
    res["owner_match"] = {
        "matched": matched,
        "byName": bool(
            _fold(owner_context.get("fullName"))
            and _fold(owner_context.get("fullName")) == _fold(values.get("Owner_FullName"))
        ),
        "byIdentityNumber": bool(
            _digits(owner_context.get("identityNumber"))
            and _digits(owner_context.get("identityNumber"))
            == _digits(values.get("Owner_IdentityNumber"))
        ),
    }
    if not matched:
        res["fields"] = []
        res.setdefault("errors", []).append("Không xác định được tài liệu của đúng chủ hồ sơ.")
        return res

    allowed_output = {
        "Owner_IssueDate", "Owner_IssuePlace", "Owner_PhoneNumber", "Owner_DetailedAddress"
    }
    if include_authorization:
        document_detected = _has_authorization_document(res.get("ocr_text"))
        recipient_matched, by_name, by_id = _person_matches(
            owner_context,
            values.get("Authorization_RecipientFullName"),
            values.get("Authorization_RecipientIdentityNumber"),
        )
        authorization_matched = document_detected and recipient_matched
        res["authorization_match"] = {
            "required": True,
            "documentDetected": document_detected,
            "matched": authorization_matched,
            "byName": by_name,
            "byIdentityNumber": by_id,
        }
        if authorization_matched:
            allowed_output.update({
                "Authorization_GrantorFullName",
                "Authorization_GrantorDateOfBirth",
                "Authorization_Relationship",
                "Authorization_GrantorIdentityNumber",
            })
        elif not document_detected:
            res.setdefault("errors", []).append(
                "Chưa nhận diện được giấy tờ ủy quyền trong hồ sơ."
            )
        else:
            res.setdefault("errors", []).append(
                "Người được ủy quyền trên giấy tờ không khớp chủ hồ sơ."
            )
    output = [field for field in (res.get("fields") or []) if field.get("name") in allowed_output]
    for field in output:
        if field.get("name") == "Owner_PhoneNumber":
            phone = _digits(field.get("value"))
            if not re.fullmatch(r"(?:0\d{9}|84\d{9})", phone):
                field["value"] = ""
            else:
                field["value"] = "0" + phone[2:] if phone.startswith("84") else phone
        elif field.get("name") == "Owner_IssuePlace":
            field["value"] = _owner_issue_place(field.get("value"))
        elif field.get("name") == "Owner_DetailedAddress":
            field["value"] = _detailed_address(field.get("value"))
        elif field.get("name") == "Authorization_GrantorIdentityNumber":
            field["value"] = _document_number(field.get("value"))
    res["fields"] = [field for field in output if field.get("value") not in (None, "", [], {})]
    return res
