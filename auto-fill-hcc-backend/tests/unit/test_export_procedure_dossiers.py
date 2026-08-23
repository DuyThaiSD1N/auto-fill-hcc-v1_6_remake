from datetime import datetime, timezone
from pathlib import Path
import zipfile

from scripts.export_procedure_dossiers import (
    ExportFile,
    _bundle_fingerprint,
    _folder_for,
    _parse_args,
    _safe_segment,
    collect_export_records,
    write_zip,
)


def _write_file(root: Path, name: str, content: bytes) -> dict:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    import hashlib

    return {
        "name": Path(name).name,
        "type": "application/pdf",
        "role": "doc",
        "size": len(content),
        "path": name,
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _trace(request_id: str, *, user_id: str = "u1", procedure: str = "p1", minute: int = 0) -> dict:
    return {
        "request_id": request_id,
        "user_id": user_id,
        "procedure": procedure,
        "procedure_label": "Thủ tục 1",
        "status": "done",
        "created_at": datetime(2026, 8, 21, 1, minute, tzinfo=timezone.utc),
        "dossier_ids": [request_id],
    }


def _request(request_id: str, files: list[dict], *, user_id: str = "u1") -> dict:
    return {"request_id": request_id, "user_id": user_id, "files": files}


def _official_user() -> dict:
    return {
        "username": "hccdonduong",
        "name": "Phường Đơn Dương",
        "tinh": "Lâm Đồng",
        "xa": "Đơn Dương",
        "role": "commune",
    }


def test_fingerprint_khong_phu_thuoc_ten_va_thu_tu(tmp_path):
    path_a = tmp_path / "a.pdf"
    path_b = tmp_path / "b.pdf"
    path_a.write_bytes(b"a")
    path_b.write_bytes(b"b")
    first = [
        ExportFile("ten-a.pdf", "", "", 1, "a" * 64, path_a),
        ExportFile("ten-b.pdf", "", "", 1, "b" * 64, path_b),
    ]
    second = [
        ExportFile("doi-ten-b.pdf", "", "", 1, "b" * 64, path_b),
        ExportFile("doi-ten-a.pdf", "", "", 1, "a" * 64, path_a),
    ]

    assert _bundle_fingerprint(first) == _bundle_fingerprint(second)


def test_gop_ho_so_cung_noi_dung_va_giu_request_moi_nhat(tmp_path):
    meta_a = _write_file(tmp_path, "r1/a.pdf", b"same-a")
    meta_b = _write_file(tmp_path, "r1/b.pdf", b"same-b")
    # File đổi tên, đảo thứ tự nhưng nội dung giữ nguyên.
    meta_b2 = _write_file(tmp_path, "r2/renamed-b.pdf", b"same-b")
    meta_a2 = _write_file(tmp_path, "r2/renamed-a.pdf", b"same-a")
    traces = [_trace("req_old", minute=1), _trace("req_new", minute=2)]
    requests = {
        "req_old": _request("req_old", [meta_a, meta_b]),
        "req_new": _request("req_new", [meta_b2, meta_a2]),
    }

    result = collect_export_records(
        traces=traces,
        requests_by_id=requests,
        users_by_id={"u1": _official_user()},
        storage_root=tmp_path,
    )

    assert [item.request_id for item in result.dossiers] == ["req_new"]
    assert result.dossiers[0].related_request_ids == ["req_new", "req_old"]
    assert any(
        item.request_id == "req_old"
        and item.reason == "Trùng toàn bộ nội dung file"
        and item.canonical_request_id == "req_new"
        for item in result.excluded
    )


def test_cung_ten_nhung_noi_dung_khac_van_la_hai_ho_so(tmp_path):
    meta_a = _write_file(tmp_path, "r1/a.pdf", b"first")
    meta_b = _write_file(tmp_path, "r2/a.pdf", b"second")
    result = collect_export_records(
        traces=[_trace("req_1"), _trace("req_2", minute=1)],
        requests_by_id={
            "req_1": _request("req_1", [meta_a]),
            "req_2": _request("req_2", [meta_b]),
        },
        users_by_id={"u1": _official_user()},
        storage_root=tmp_path,
    )

    assert {item.request_id for item in result.dossiers} == {"req_1", "req_2"}


def test_loai_tai_khoan_test_va_ho_so_thieu_file(tmp_path):
    missing = {
        "name": "missing.pdf",
        "path": "missing.pdf",
        "size": 10,
        "sha256": "a" * 64,
    }
    result = collect_export_records(
        traces=[_trace("req_test", user_id="tester"), _trace("req_missing")],
        requests_by_id={
            "req_test": _request("req_test", [missing], user_id="tester"),
            "req_missing": _request("req_missing", [missing]),
        },
        users_by_id={
            "tester": {"username": "hcctester", "role": "user"},
            "u1": _official_user(),
        },
        storage_root=tmp_path,
    )

    reasons = {item.request_id: item.reason for item in result.excluded}
    assert reasons["req_test"] == "Không phải tài khoản HCC chính thức"
    assert reasons["req_missing"] == "Hồ sơ thiếu file hợp lệ"
    assert result.dossiers == []


def test_thu_muc_chi_co_ba_cap_sau_goc(tmp_path):
    meta = _write_file(tmp_path, "r1/a.pdf", b"a")
    result = collect_export_records(
        traces=[_trace("req_123")],
        requests_by_id={"req_123": _request("req_123", [meta])},
        users_by_id={"u1": _official_user()},
        storage_root=tmp_path,
    )

    folder = _folder_for(result.dossiers[0])
    assert folder == "ho_so/p1/Lâm Đồng__Đơn Dương__req_123"
    assert len(folder.split("/")) == 3

    output = tmp_path / "export.zip"
    write_zip(output, result, ["p1"])
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()

    assert "ho_so/p1/Lâm Đồng__Đơn Dương__req_123/01_a.pdf" in names
    assert not any("Đơn Dương/req_123/" in name for name in names)


def test_ten_duong_dan_duoc_lam_sach_va_cli_nhan_nhieu_thu_tuc():
    assert _safe_segment('a<b>:c?.pdf', fallback="file") == "a_b__c_.pdf"
    args = _parse_args(["--procedure", "p1,p2", "--procedure", "p2", "--size-only"])
    assert args.procedures == ["p1", "p2"]
    assert args.size_only is True
