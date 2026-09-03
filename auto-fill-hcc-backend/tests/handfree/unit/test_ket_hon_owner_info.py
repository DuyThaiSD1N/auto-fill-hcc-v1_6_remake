import pytest

from app.channels.handfree.owner_info import run as shared_owner_run
from app.channels.handfree.owner_info import runner as owner_runner
from app.channels.handfree.owner_info.schema import ISSUE_PLACE_OPTIONS
from app.channels.handfree.owner_info.prompt import build_rules
from app.channels.handfree.owner_info.schema import fields_for
from app.pipelines.ket_hon.handfree.owner_info import run as legacy_ket_hon_owner_run


def test_legacy_ket_hon_import_points_to_shared_owner_pipeline():
    assert legacy_ket_hon_owner_run is shared_owner_run


@pytest.mark.parametrize(("raw", "expected"), [
    ("CỤC CẢNH SÁT ĐKQL CƯ TRÚ VÀ DLQG VỀ DÂN CƯ", ISSUE_PLACE_OPTIONS[0]),
    ("Cục Cảnh sát QLHC về TTXH", ISSUE_PLACE_OPTIONS[1]),
    ("BỘ CÔNG AN / MINISTRY OF PUBLIC SECURITY", ISSUE_PLACE_OPTIONS[2]),
    ("CỤC QUẢN LÝ XUẤT NHẬP CẢNH", ISSUE_PLACE_OPTIONS[3]),
    ("Công an tỉnh Lai Châu", ""),
])
def test_owner_issue_place_is_exact_portal_option(raw, expected):
    assert owner_runner._owner_issue_place(raw) == expected


def test_owner_matches_name_or_identity_number():
    context = {"fullName": "VŨ ĐÌNH THIẾT", "identityNumber": "040203015844"}
    assert owner_runner.owner_matches(context, {
        "Owner_FullName": "Vũ Đình Thiết", "Owner_IdentityNumber": "999999999999",
    })
    assert owner_runner.owner_matches(context, {
        "Owner_FullName": "NGƯỜI KHÁC", "Owner_IdentityNumber": "0402 0301 5844",
    })
    assert not owner_runner.owner_matches(context, {
        "Owner_FullName": "NGƯỜI KHÁC", "Owner_IdentityNumber": "999999999999",
    })


def test_self_branch_has_no_authorization_schema_or_prompt():
    field_names = {field["name"] for field in fields_for(False)}
    rules = build_rules({"fullName": "VŨ ĐÌNH THIẾT"}, False)

    assert not any(name.startswith("Authorization_") for name in field_names)
    assert "ủy quyền" not in rules.casefold()
    assert "authorization" not in rules.casefold()


def test_authorized_branch_adds_authorization_schema_and_prompt():
    field_names = {field["name"] for field in fields_for(True)}
    rules = build_rules({"fullName": "VŨ ĐÌNH THIẾT"}, True)

    assert "Authorization_GrantorFullName" in field_names
    assert "Authorization_RecipientIdentityNumber" in field_names
    assert "<personal_authorization_task>" in rules


def test_authorization_recipient_requires_name_and_id_when_both_are_available():
    context = {"fullName": "VŨ ĐÌNH THIẾT", "identityNumber": "040203015844"}

    matched, by_name, by_id = owner_runner._person_matches(
        context, "NGƯỜI KHÁC", "040203015844"
    )

    assert by_id is True and by_name is False
    assert matched is False


@pytest.mark.asyncio
async def test_owner_pipeline_blocks_wrong_person(monkeypatch):
    async def fake_run(*_args, **_kwargs):
        return {"fields": [
            {"name": "Owner_FullName", "value": "NGƯỜI KHÁC"},
            {"name": "Owner_IdentityNumber", "value": "999999999999"},
            {"name": "Owner_IssueDate", "value": "02/07/2021"},
        ], "errors": []}

    monkeypatch.setattr(owner_runner.runner, "run", fake_run)
    result = await owner_runner.run({"": [{}]}, {
        "ownerContext": {"fullName": "VŨ ĐÌNH THIẾT", "identityNumber": "040203015844"},
    })
    assert result["fields"] == []
    assert result["owner_match"]["matched"] is False


@pytest.mark.asyncio
async def test_owner_pipeline_returns_only_portal_fields(monkeypatch):
    async def fake_run(*_args, **_kwargs):
        return {"fields": [
            {"name": "Owner_FullName", "value": "Vũ Đình Thiết"},
            {"name": "Owner_IdentityNumber", "value": "000000000000"},
            {"name": "Owner_IssueDate", "value": "02/07/2021"},
            {"name": "Owner_IssuePlace", "value": "Cục Cảnh sát QLHC về TTXH"},
            {"name": "Owner_PhoneNumber", "value": "không rõ"},
            {"name": "Owner_DetailedAddress", "value": {
                "quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Tân Phong",
                "diaChi": "Xóm Long Thành",
            }},
        ], "errors": []}

    monkeypatch.setattr(owner_runner.runner, "run", fake_run)
    result = await owner_runner.run({"": [{}]}, {
        "ownerContext": {"fullName": "VŨ ĐÌNH THIẾT", "identityNumber": "040203015844"},
    })
    values = {field["name"]: field["value"] for field in result["fields"]}
    assert "Owner_FullName" not in values and "Owner_IdentityNumber" not in values
    assert "Owner_PhoneNumber" not in values
    assert values["Owner_IssueDate"] == "02/07/2021"
    assert values["Owner_IssuePlace"] == ISSUE_PLACE_OPTIONS[1]
    assert values["Owner_DetailedAddress"] == "Xóm Long Thành"


@pytest.mark.asyncio
async def test_authorized_pipeline_returns_grantor_only_after_document_and_recipient_match(monkeypatch):
    async def fake_run(*_args, **kwargs):
        assert any(
            field["name"] == "Authorization_GrantorFullName"
            for field in kwargs["fields"]
        )
        return {
            "ocr_text": "GIẤY ỦY QUYỀN\nBên ủy quyền: NGUYỄN VĂN A\n"
                        "Bên được ủy quyền: VŨ ĐÌNH THIẾT, CCCD 040203015844",
            "fields": [
                {"name": "Owner_FullName", "value": "VŨ ĐÌNH THIẾT"},
                {"name": "Owner_IdentityNumber", "value": "040203015844"},
                {"name": "Owner_IssueDate", "value": "02/07/2021"},
                {"name": "Authorization_DocumentTitle", "value": "GIẤY ỦY QUYỀN"},
                {"name": "Authorization_RecipientFullName", "value": "VŨ ĐÌNH THIẾT"},
                {"name": "Authorization_RecipientIdentityNumber", "value": "040203015844"},
                {"name": "Authorization_GrantorFullName", "value": "NGUYỄN VĂN A"},
                {"name": "Authorization_GrantorDateOfBirth", "value": "01/01/1980"},
                {"name": "Authorization_Relationship", "value": "Cha"},
                {"name": "Authorization_GrantorIdentityNumber", "value": "A 123 4567"},
            ],
            "errors": [],
        }

    monkeypatch.setattr(owner_runner.runner, "run", fake_run)
    result = await owner_runner.run({"": [{}]}, {
        "ownerContext": {"fullName": "VŨ ĐÌNH THIẾT", "identityNumber": "040203015844"},
        "executionSubject": "authorized_person",
    })
    values = {field["name"]: field["value"] for field in result["fields"]}

    assert result["authorization_match"]["matched"] is True
    assert values["Authorization_GrantorFullName"] == "NGUYỄN VĂN A"
    assert values["Authorization_GrantorDateOfBirth"] == "01/01/1980"
    assert values["Authorization_Relationship"] == "Cha"
    assert values["Authorization_GrantorIdentityNumber"] == "A1234567"


@pytest.mark.asyncio
async def test_authorized_pipeline_blocks_grantor_when_authorization_recipient_mismatches(monkeypatch):
    async def fake_run(*_args, **_kwargs):
        return {
            "ocr_text": "GIẤY ỦY QUYỀN\nBên ủy quyền: NGUYỄN VĂN A\n"
                        "Bên được ủy quyền: NGƯỜI KHÁC, CCCD 999999999999",
            "fields": [
                {"name": "Owner_FullName", "value": "VŨ ĐÌNH THIẾT"},
                {"name": "Owner_IdentityNumber", "value": "040203015844"},
                {"name": "Authorization_RecipientFullName", "value": "NGƯỜI KHÁC"},
                {"name": "Authorization_RecipientIdentityNumber", "value": "999999999999"},
                {"name": "Authorization_GrantorFullName", "value": "NGUYỄN VĂN A"},
            ],
            "errors": [],
        }

    monkeypatch.setattr(owner_runner.runner, "run", fake_run)
    result = await owner_runner.run({"": [{}]}, {
        "ownerContext": {"fullName": "VŨ ĐÌNH THIẾT", "identityNumber": "040203015844"},
        "executionSubject": "authorized_person",
    })

    assert result["authorization_match"]["matched"] is False
    assert not any(field["name"].startswith("Authorization_") for field in result["fields"])
    assert "không khớp chủ hồ sơ" in result["errors"][-1]
