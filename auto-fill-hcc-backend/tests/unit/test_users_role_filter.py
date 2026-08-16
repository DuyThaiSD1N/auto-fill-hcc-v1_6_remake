from app.users.service import _role_query


def test_user_role_filter_includes_legacy_accounts_without_role():
    assert _role_query("user") == {
        "$or": [
            {"role": "user"},
            {"role": {"$exists": False}},
            {"role": None},
        ]
    }


def test_specific_hcc_role_filter_is_exact():
    assert _role_query("commune") == {"role": "commune"}
    assert _role_query("province") == {"role": "province"}


def test_all_roles_has_no_mongo_filter():
    assert _role_query(None) == {}
