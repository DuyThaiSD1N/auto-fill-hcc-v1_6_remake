import pytest

from app.channels.handfree.flow_profiles import resolve_flow_profile
from app.channels.handfree.procedure_registry import (
    get_attach_pipeline,
    get_owner_info_pipeline,
    get_pipeline,
    public_list,
)
from app.procedures import registry as core_registry


def test_tu_phap_profile_materializes_owner_wizard_without_mutating_raw_entry():
    raw = {"key": "thu-tuc-moi", "flowProfile": "tu-phap", "mode": "agent"}

    resolved = resolve_flow_profile(raw)

    assert "ownerInfo" not in raw and "wizard" not in raw
    assert resolved["needsAgencySelect"] is True
    assert resolved["hasAttachmentStep"] is True
    assert resolved["wizard"] == {
        "ownerStep": 1,
        "declarationStep": 2,
        "attachmentStep": 3,
        "resultStep": 4,
    }
    fields = resolved["ownerInfo"]["fields"]
    assert fields["Owner_PhoneNumber"]["name"] == "soDienThoai"
    assert fields["Owner_DetailedAddress"]["name"] == "diaChiThuongTru"
    assert resolved["executionSubject"] == {
        "enabled": True,
        "default": "self",
        "options": [
            {
                "key": "self",
                "label": "Làm thủ tục cho bản thân",
                "portalValue": "null",
            },
            {
                "key": "authorized_person",
                "label": "Người khác ủy quyền",
                "portalValue": "canhan",
            },
            {
                "key": "enterprise_authorized",
                "label": "Doanh nghiệp ủy quyền",
                "portalValue": "",
            },
            {
                "key": "other_person",
                "label": "Làm thủ tục cho người khác",
                "portalValue": "",
            },
            {
                "key": "organization_representative",
                "label": "Đại diện cơ quan, tổ chức",
                "portalValue": "",
            },
        ],
    }
    authorization = resolved["authorizationInfo"]
    assert authorization["activeWhen"] == {"executionSubject": "authorized_person"}
    assert authorization["sectionLabel"] == "Thông tin ủy quyền cá nhân"
    assert authorization["fields"]["Authorization_GrantorFullName"]["name"] == "hoTen"
    assert authorization["fields"]["Authorization_GrantorDateOfBirth"]["comp"] == "owner-date"


def test_tu_phap_profile_allows_narrow_procedure_override():
    resolved = resolve_flow_profile({
        "key": "thu-tuc-khac-control",
        "flowProfile": "tu-phap",
        "ownerInfo": {
            "fields": {
                "Owner_PhoneNumber": {"name": "phoneNumber"},
            },
        },
    })

    phone = resolved["ownerInfo"]["fields"]["Owner_PhoneNumber"]
    assert phone["name"] == "phoneNumber"
    assert phone["key"] == "phoneNumber" and phone["comp"] == "owner-input"
    assert resolved["ownerInfo"]["fields"]["Owner_IssueDate"]["comp"] == "owner-date"


def test_unknown_flow_profile_fails_fast():
    with pytest.raises(ValueError, match="flowProfile không tồn tại"):
        resolve_flow_profile({"key": "sai-profile", "flowProfile": "khong-co"})


def test_tu_phap_profile_rejects_invalid_execution_subject_default():
    with pytest.raises(ValueError, match="executionSubject không hợp lệ"):
        resolve_flow_profile({
            "key": "sai-doi-tuong",
            "flowProfile": "tu-phap",
            "executionSubject": {"default": "khong-ton-tai"},
        })


def test_tu_phap_profile_rejects_authorization_subject_outside_declared_options():
    with pytest.raises(ValueError, match="authorizationInfo không hợp lệ"):
        resolve_flow_profile({
            "key": "sai-nhanh-uy-quyen",
            "flowProfile": "tu-phap",
            "authorizationInfo": {
                "activeWhen": {"executionSubject": "doanhnghiep"},
            },
        })


def test_registered_procedures_use_their_declared_flow_family():
    procedures = {procedure["key"]: procedure for procedure in public_list()}

    linked_birth = procedures.pop("khai-sinh-dang-ky")
    assert linked_birth.get("flowProfile") is None
    business = procedures.pop("dang-ky-kinh-doanh")
    assert business.get("flowProfile") is None
    assert business["businessWorkflow"] == "create"
    assert len(business["pages"]) == 8

    assert procedures
    assert {
        key for key, procedure in procedures.items()
        if procedure.get("flowProfile") != "tu-phap"
    } == set()

    attach_only = {"chung-thuc-ban-sao", "chung-thuc-chu-ky"}
    for key, procedure in procedures.items():
        owner_enabled = procedure["ownerInfo"]["enabled"]
        assert owner_enabled is (key not in attach_only)
        assert procedure["needsAgencySelect"] is True
        assert procedure["hasAttachmentStep"] is True
        assert procedure["executionSubject"]["default"] == "self"
        assert [
            option["portalValue"] for option in procedure["executionSubject"]["options"]
        ] == ["null", "canhan", "", "", ""]
        assert get_owner_info_pipeline(key) is not None


def test_all_handfree_procedures_delegate_business_core_to_autofill_registry():
    procedures = public_list()
    assert len(procedures) == 16

    for procedure in procedures:
        key = procedure["key"]
        assert get_pipeline(key) is core_registry.get_pipeline(key)
        assert get_attach_pipeline(key) is core_registry.get_attach_pipeline(key)
        if procedure.get("mode") != "attach":
            assert get_pipeline(key) is not None, key
        if procedure.get("hasAttachmentStep"):
            assert get_attach_pipeline(key) is not None, key
