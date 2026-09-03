from scripts.list_report_accounts import format_accounts


def test_formats_only_report_account_columns_and_sorts_by_username():
    output = format_accounts([
        {
            "username": "z-user",
            "name": "HCC Xã Z",
            "xa": "Xã Z",
            "tinh": "Tỉnh Bắc Ninh",
            "role": "commune",
            "password_hash": "secret",
        },
        {
            "username": "a-user",
            "name": "HCC Phường A\n",
            "xa": "Phường A",
            "tinh": "Đà Nẵng",
        },
    ])

    assert [value.strip() for value in output.splitlines()[0].split(" | ")] == [
        "username",
        "name",
        "xã",
        "tỉnh",
    ]
    assert output.index("a-user") < output.index("z-user")
    assert "HCC Phường A" in output
    assert "password" not in output and "secret" not in output and "role" not in output
