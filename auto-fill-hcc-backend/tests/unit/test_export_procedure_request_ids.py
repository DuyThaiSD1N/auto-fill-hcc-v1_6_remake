import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from scripts.export_procedure_request_ids import (
    _parse_args,
    request_ids_from_result,
    select_balanced_dossiers,
    write_request_ids,
)


def test_xuat_dung_mot_request_id_cho_moi_ho_so(tmp_path):
    result = SimpleNamespace(
        dossiers=[
            SimpleNamespace(request_id="req_new_1", related_request_ids=["req_new_1", "req_old_1"]),
            SimpleNamespace(request_id="req_2", related_request_ids=["req_2"]),
        ]
    )

    request_ids = request_ids_from_result(result)
    output = tmp_path / "request_ids.json"
    write_request_ids(output, request_ids)

    assert request_ids == ["req_new_1", "req_2"]
    assert json.loads(output.read_text(encoding="utf-8")) == ["req_new_1", "req_2"]


def test_cli_giu_bo_loc_giong_script_xuat_ho_so():
    args = _parse_args([
        "--procedure", "p1,p2",
        "--procedure", "p2",
        "--from", "25/08/2026",
        "--to", "26/08/2026",
        "--include-test-accounts",
    ])

    assert args.procedures == ["p1", "p2"]
    assert args.date_from == "25/08/2026"
    assert args.date_to == "26/08/2026"
    assert args.include_test_accounts is True


def _dossier(account: str, ordinal: int):
    return SimpleNamespace(
        request_id=f"req_{account}_{ordinal}",
        user_id=account,
        username=account,
        unit_name=account,
        created_at=datetime(2026, 8, 26, tzinfo=timezone.utc) + timedelta(minutes=ordinal),
    )


def test_limit_chia_deu_va_tu_phan_bo_lai_quota_thieu():
    dossiers = [
        *[_dossier("hcc_a", index) for index in range(10)],
        *[_dossier("hcc_b", index) for index in range(10)],
        _dossier("hcc_c", 1),
    ]

    selected = select_balanced_dossiers(dossiers, 8)
    counts = {}
    for dossier in selected:
        counts[dossier.user_id] = counts.get(dossier.user_id, 0) + 1

    assert len(selected) == 8
    assert counts == {"hcc_a": 4, "hcc_b": 3, "hcc_c": 1}
    # Trong mỗi tài khoản phải lấy request mới nhất trước.
    assert [item.request_id for item in selected if item.user_id == "hcc_a"] == [
        "req_hcc_a_9", "req_hcc_a_8", "req_hcc_a_7", "req_hcc_a_6",
    ]


def test_limit_la_option_thay_cho_khoang_ngay():
    args = _parse_args(["--procedure", "p1", "--limit", "200"])
    assert args.limit == 200

    with pytest.raises(SystemExit):
        _parse_args([
            "--procedure", "p1", "--limit", "200", "--from", "25/08/2026",
        ])
