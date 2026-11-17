import verify

OUT = """....F
=========================== short test summary info ===========================
FAILED tests/unit/test_a.py::test_x - AssertionError: sai
FAILED tests/unit/test_a.py::test_y
ERROR tests/unit/test_b.py
13 failed, 4097 passed, 40 skipped, 6 errors in 65.18s (0:01:05)
"""


def test_parse_pytest():
    parsed = verify.parse_pytest(OUT)
    assert (parsed["failed"], parsed["passed"], parsed["skipped"], parsed["errors"]) == (13, 4097, 40, 6)
    assert parsed["bad"] == ["ERROR tests/unit/test_b.py", "FAILED tests/unit/test_a.py::test_x", "FAILED tests/unit/test_a.py::test_y"]


def test_parse_pytest_toan_xanh():
    parsed = verify.parse_pytest("...\n3 passed in 0.10s\n")
    assert parsed["passed"] == 3 and parsed["failed"] == 0 and parsed["bad"] == []


def test_compare_chi_bat_test_moi_do():
    before = {"bad": ["FAILED a", "ERROR b"], "failed": 1, "passed": 10, "skipped": 0, "errors": 1}
    assert verify.compare(before, {"bad": ["FAILED a", "ERROR b"], "failed": 1, "passed": 11, "skipped": 0, "errors": 1})["ok"]
    result = verify.compare(before, {"bad": ["FAILED a", "FAILED c"], "failed": 2, "passed": 10, "skipped": 0, "errors": 0})
    assert not result["ok"] and result["new"] == ["FAILED c"] and result["fixed"] == ["ERROR b"]


def test_so_test_extension_chi_bat_file_moi_do():
    before = {"total": 5, "failed": ["a.test.js"]}
    same = verify.compare_extension(before, {"total": 5, "failed": ["a.test.js"]})
    assert same["ok"] and same["failedBefore"] == 1
    worse = verify.compare_extension(before, {"total": 5, "failed": ["b.test.js"]})
    assert not worse["ok"] and worse["new"] == ["b.test.js"] and worse["fixed"] == ["a.test.js"]


def test_bo_test_sap_khong_duoc_coi_la_dat():
    before = {"bad": [], "failed": 0, "passed": 10, "skipped": 0, "errors": 0}
    assert not verify.compare(before, {"bad": [], "failed": 0, "passed": 0, "skipped": 0, "errors": 0, "broken": True, "tail": "x"})["ok"]


def _server(monkeypatch, tmp_path, **overrides):
    import config

    values = {
        "SERVER_MODE": True, "SOURCE_MONGO_URI": "mongodb://ro@127.0.0.1:12004/", "SOURCE_UPLOADS": str(tmp_path),
        "TEST_MONGO_URI": "mongodb://127.0.0.1:12014/", "COMPOSE_FILE": str(tmp_path / "compose.server.yml"),
        "BACKEND_URL": "http://127.0.0.1:12015", "AUTH_BACKEND_URL": "http://127.0.0.1:12005",
    }
    for key, value in {**values, **overrides}.items():
        monkeypatch.setattr(config, key, value)
    return config


def test_server_du_cau_hinh_thi_khong_loi(monkeypatch, tmp_path):
    assert _server(monkeypatch, tmp_path).server_problems() == []


def test_server_khong_duoc_build_bang_compose_prod(monkeypatch, tmp_path):
    """Trên server trolyhoso compose.prod.yml là stack production: thiếu compose.server.yml thì dịch vụ không chạy."""
    config = _server(monkeypatch, tmp_path, COMPOSE_FILE="")
    assert any("AUTOTEST_COMPOSE_FILE" in p for p in config.server_problems())
    config = _server(monkeypatch, tmp_path, COMPOSE_FILE="/opt/autofill-hcc/compose.prod.yml")
    assert any("AUTOTEST_COMPOSE_FILE" in p for p in config.server_problems())
    monkeypatch.setattr(verify, "COMPOSE_FILE", "")
    monkeypatch.setattr(verify, "server_problems", config.server_problems)
    try:
        verify._compose()
    except RuntimeError as reason:
        assert "production" in str(reason)
    else:
        raise AssertionError("phải từ chối build")


def test_server_khong_dung_chung_mongo_va_backend_production(monkeypatch, tmp_path):
    config = _server(monkeypatch, tmp_path, TEST_MONGO_URI="mongodb://ro@127.0.0.1:12004/")
    assert any("AUTOTEST_TEST_MONGO_URI" in p for p in config.server_problems())
    config = _server(monkeypatch, tmp_path, BACKEND_URL="http://127.0.0.1:12005")
    assert any("AUTOTEST_BACKEND" in p for p in config.server_problems())


def test_compose_server_build_dung_file_va_service(monkeypatch, tmp_path):
    monkeypatch.setattr(verify, "COMPOSE_FILE", str(tmp_path / "compose.server.yml"))
    cmd, cwd, service = verify._compose()
    assert cmd[-1].endswith("compose.server.yml") and cwd == tmp_path.resolve() and service == "app"
