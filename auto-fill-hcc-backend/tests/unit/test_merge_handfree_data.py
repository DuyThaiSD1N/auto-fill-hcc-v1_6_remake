from bson import ObjectId

from scripts.merge_handfree_data import (
    duplicate_query,
    prepare_documents,
)


def test_trace_is_labeled_remapped_and_exact_source_id_is_idempotent():
    source_user = str(ObjectId())
    target_user = str(ObjectId())
    source = {
        "_id": ObjectId(),
        "request_id": "req-handfree-1",
        "kind": "process",
        "user_id": source_user,
        "experience": "wrong-old-value",
    }

    prepared, summary, errors = prepare_documents(
        "traces",
        [source, dict(source)],
        {source_user: target_user},
    )

    assert errors == []
    assert summary == {
        "sourceCount": 2,
        "preparedCount": 1,
        "sourceDuplicateCount": 1,
        "remappedUserCount": 1,
    }
    assert prepared[0]["experience"] == "handfree"
    assert prepared[0]["user_id"] == target_user
    assert prepared[0]["migration_source_id"] == str(source["_id"])
    assert duplicate_query("traces", prepared[0]) == {
        "experience": "handfree",
        "migration_source": "tro_ly_nguoi_dan_legacy",
        "migration_source_id": str(source["_id"]),
    }


def test_missing_user_mapping_blocks_preflight_without_pii():
    prepared, summary, errors = prepare_documents(
        "process_requests",
        [{
            "_id": ObjectId(),
            "request_id": "req-handfree-2",
            "user_id": str(ObjectId()),
        }],
        {},
    )

    assert prepared == []
    assert summary["preparedCount"] == 0
    assert len(errors) == 1
    assert "user_id chưa được ánh xạ" in errors[0]["error"]


def test_two_source_traces_with_same_request_and_kind_are_both_preserved():
    source_user = str(ObjectId())
    documents = [
        {
            "_id": ObjectId(),
            "request_id": "req-retry",
            "kind": "process",
            "user_id": source_user,
        },
        {
            "_id": ObjectId(),
            "request_id": "req-retry",
            "kind": "process",
            "user_id": source_user,
        },
    ]

    prepared, summary, errors = prepare_documents(
        "traces",
        documents,
        {source_user: str(ObjectId())},
    )

    assert errors == []
    assert summary["preparedCount"] == 2
    assert summary["sourceDuplicateCount"] == 0
    assert prepared[0]["migration_source_id"] != prepared[1]["migration_source_id"]


def test_handfree_consent_without_user_id_keeps_legacy_shape():
    prepared, summary, errors = prepare_documents(
        "consent_logs",
        [{"_id": "TLND-ABC123", "auth_username": "hccsonglieu"}],
        {},
    )

    assert errors == []
    assert summary["preparedCount"] == 1
    assert prepared[0]["_id"] == "TLND-ABC123"
    assert prepared[0]["experience"] == "handfree"
    assert duplicate_query("consent_logs", prepared[0]) == {
        "experience": "handfree",
        "migration_source": "tro_ly_nguoi_dan_legacy",
        "migration_source_id": "TLND-ABC123",
    }
