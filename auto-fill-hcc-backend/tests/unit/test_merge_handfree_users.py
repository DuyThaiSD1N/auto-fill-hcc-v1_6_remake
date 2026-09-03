from datetime import datetime, timezone

from bson import ObjectId

from scripts.merge_handfree_users import build_merge_plan, canonical_username


NOW = datetime(2026, 8, 31, tzinfo=timezone.utc)


def _user(username: str, **overrides):
    data = {
        "_id": ObjectId(),
        "username": username,
        "password_hash": "$2b$12$handfree-password-hash",
        "name": username,
        "tinh": "Tỉnh Bắc Ninh",
        "xa": "Phường Song Liễu",
        "role": "user",
        "access_disabled": False,
        "created_at": NOW,
    }
    data.update(overrides)
    return data


def test_hai_chau_old_username_maps_to_existing_auto_fill_user():
    source = _user("hcchaichau", tinh="Thành phố Đà Nẵng", xa="Phường Hải Châu")
    target = _user("hccphuonghaichau", tinh="Thành phố Đà Nẵng", xa="Phường Hải Châu")

    plan = build_merge_plan([source], [target], now=NOW)

    assert canonical_username(" HCCHaiChau ") == "hccphuonghaichau"
    assert plan.report["insertCount"] == 0
    assert plan.report["userIdMap"][str(source["_id"])] == str(target["_id"])


def test_confirmed_conflicts_keep_auto_fill_role_status_and_location():
    source_users = [
        _user("hcctester", tinh="Tỉnh Bắc Ninh", xa="Phường Song Liễu"),
        _user("skquangngai", role="province", tinh="Tỉnh Quảng Ngãi", xa="Phường Nghĩa Lộ"),
        _user("hccnghiahung", access_disabled=True, tinh="Tỉnh Ninh Bình", xa="Xã Nghĩa Hưng"),
    ]
    target_users = [
        _user("hcctester", tinh="Thành phố Đà Nẵng", xa="Phường Hải Châu"),
        _user("skquangngai", role="user", tinh="Tỉnh Quảng Ngãi", xa=None),
        _user("hccnghiahung", access_disabled=False, tinh="Tỉnh Ninh Bình", xa="Xã Nghĩa Hưng"),
    ]

    plan = build_merge_plan(source_users, target_users, now=NOW)

    assert plan.report["insertCount"] == 0
    assert plan.report["matchedCount"] == 3
    by_username = {item["username"]: item for item in plan.report["matched"]}
    assert by_username["hcctester"]["policy"] == "auto_fill_kept"
    assert by_username["skquangngai"]["differences"]["role"]["autoFillKept"] == "user"
    assert by_username["hccnghiahung"]["differences"]["access_disabled"]["autoFillKept"] is False


def test_handfree_only_user_is_planned_with_existing_password_hash():
    source = _user(
        "dattest",
        tinh="Thành phố Hà Nội",
        xa="Phường Thanh Xuân",
        role="user",
    )

    plan = build_merge_plan([source], [], now=NOW)

    assert plan.report["errorCount"] == 0
    assert plan.report["insertCount"] == 1
    inserted = plan.inserts[0].document
    assert inserted["_id"] == source["_id"]
    assert inserted["password_hash"] == source["password_hash"]
    assert inserted["tinh"] == "Thành phố Hà Nội"
    assert inserted["xa"] == "Phường Thanh Xuân"


def test_public_users_api_export_is_rejected_before_apply():
    source = _user("dattest")
    source.pop("password_hash")

    plan = build_merge_plan([source], [], now=NOW)

    assert plan.report["insertCount"] == 0
    assert plan.report["errorCount"] == 1
    assert "password_hash" in plan.report["errors"][0]["error"]


def test_confirmed_auto_fill_user_must_exist_and_nghiahung_must_be_active():
    missing_target = build_merge_plan([_user("hcctester")], [], now=NOW)
    disabled_target = build_merge_plan(
        [_user("hccnghiahung", access_disabled=True)],
        [_user("hccnghiahung", access_disabled=True)],
        now=NOW,
    )

    assert missing_target.report["insertCount"] == 0
    assert missing_target.report["errorCount"] == 1
    assert disabled_target.report["insertCount"] == 0
    assert disabled_target.report["errorCount"] == 1
    assert "trạng thái hoạt động" in disabled_target.report["errors"][0]["error"]
