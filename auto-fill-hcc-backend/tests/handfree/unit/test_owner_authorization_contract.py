from app.channels.handfree.chat.pipeline_runner import _owner_field_config, _owner_pipeline_options
from app.channels.handfree.procedure_registry import get_procedure


def test_self_owner_pipeline_does_not_receive_authorization_context_or_fields():
    proc = get_procedure("ket-hon")
    owner_context = {"fullName": "VŨ ĐÌNH THIẾT", "identityNumber": "040203015844"}

    options = _owner_pipeline_options({"execution_subject": "self"}, owner_context)
    fields = _owner_field_config(proc, "self")

    assert options == {"ownerContext": owner_context}
    assert "executionSubject" not in options
    assert not any(name.startswith("Authorization_") for name in fields)


def test_authorized_owner_pipeline_receives_authorization_context_and_fields():
    proc = get_procedure("ket-hon")
    owner_context = {"fullName": "VŨ ĐÌNH THIẾT", "identityNumber": "040203015844"}

    options = _owner_pipeline_options(
        {"execution_subject": "authorized_person"}, owner_context
    )
    fields = _owner_field_config(proc, "authorized_person")

    assert options["executionSubject"] == "authorized_person"
    assert {
        "Authorization_GrantorFullName",
        "Authorization_GrantorDateOfBirth",
        "Authorization_Relationship",
        "Authorization_GrantorIdentityNumber",
    }.issubset(fields)


def test_other_subjects_use_only_basic_owner_fields_for_now():
    proc = get_procedure("ket-hon")
    owner_context = {"fullName": "VŨ ĐÌNH THIẾT", "identityNumber": "040203015844"}

    for subject in (
        "enterprise_authorized",
        "other_person",
        "organization_representative",
    ):
        options = _owner_pipeline_options({"execution_subject": subject}, owner_context)
        fields = _owner_field_config(proc, subject)

        assert options == {"ownerContext": owner_context}
        assert not any(name.startswith("Authorization_") for name in fields)
