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
    # Cổng Bộ NN&MT: không dùng profile tư pháp — wizard riêng (kê khai 1, đính kèm 2)
    # + luồng chọn cơ quan 2 tầng (DVCQG chỉ tỉnh → trang MAE chọn Sở + trường hợp).
    mae_fishing = procedures.pop("cap-giay-phep-khai-thac-thuy-san")
    assert mae_fishing.get("flowProfile") is None
    assert mae_fishing["agencyProvinceOnly"] is True
    assert mae_fishing["maePortal"] is True
    assert mae_fishing["wizard"]["declarationStep"] == 1
    assert mae_fishing["wizard"]["attachmentStep"] == 2
    # Bộ GD&ĐT: cùng nền iGate (wizard 1/2) nhưng KHÔNG có trang chọn nơi/loại;
    # DVCQG chọn Tỉnh + toggle "Sở" rồi lấy Sở đầu tiên (agencySoFirst).
    moet_diploma = procedures.pop("cap-ban-sao-van-bang-so-goc")
    assert moet_diploma.get("flowProfile") is None
    assert moet_diploma["agencyProvinceOnly"] is True
    assert moet_diploma["agencySoFirst"] is True
    assert "maePortal" not in moet_diploma
    assert moet_diploma["wizard"]["declarationStep"] == 1
    assert moet_diploma["wizard"]["attachmentStep"] == 2
    # Bộ Xây dựng (NOXH): cùng khuôn agencySoFirst + wizard iGate như văn bằng.
    moc_housing = procedures.pop("cho-thue-thue-mua-nha-o-xa-hoi")
    assert moc_housing.get("flowProfile") is None
    assert moc_housing["agencyProvinceOnly"] is True
    assert moc_housing["agencySoFirst"] is True
    assert "maePortal" not in moc_housing
    assert moc_housing["wizard"]["declarationStep"] == 1
    assert moc_housing["wizard"]["attachmentStep"] == 2
    # HkdOnline nhánh THAY ĐỔI: cùng cổng với thành lập mới nhưng workflow "change"
    # (wizard 4 bước + pageOrder động), không dùng profile tư pháp.
    business_change = procedures.pop("dang-ky-thay-doi-noi-dung-ho-kinh-doanh")
    assert business_change.get("flowProfile") is None
    assert business_change["businessWorkflow"] == "change"
    assert len(business_change["pages"]) == 7
    # Cổng tỉnh Bắc Ninh (Liferay eForm 2 tab cùng trang): không profile tư pháp, không wizard;
    # tỉnh chọn cố định Bắc Ninh + toggle "Sở" (agencySoFirst), điền xong tự đính kèm ngay.
    for bn_key in ("dang-ky-bien-phap-bao-dam-bac-ninh", "xoa-dang-ky-bien-phap-bao-dam-bac-ninh"):
        bn_secured = procedures.pop(bn_key)
        assert bn_secured.get("flowProfile") is None
        assert bn_secured["samePageAttach"] is True
        assert bn_secured["agencyProvince"] == "Bắc Ninh"
        assert bn_secured["agencyProvinceOnly"] is True
        assert bn_secured["agencySoFirst"] is True
        assert "wizard" not in bn_secured and "maePortal" not in bn_secured

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
    assert len(procedures) == 21

    for procedure in procedures:
        key = procedure["key"]
        assert get_pipeline(key) is core_registry.get_pipeline(key)
        assert get_attach_pipeline(key) is core_registry.get_attach_pipeline(key)
        if procedure.get("mode") != "attach":
            assert get_pipeline(key) is not None, key
        if procedure.get("hasAttachmentStep"):
            assert get_attach_pipeline(key) is not None, key
