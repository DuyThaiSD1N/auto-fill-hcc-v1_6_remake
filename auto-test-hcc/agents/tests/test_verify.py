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
