from scoring import check_passes, evaluate, field_key, field_table, find_regressions, known_fields, replay_coverage, run_values, unknown_fields, value_text


def run(fields, status="ok"):
    return {"status": status, "response": {"fields": fields}}


def f(name, value, **extra):
    return {"name": name, "value": value, **extra}


def test_value_text_giong_web():
    assert value_text("  Nguyễn   Văn  A ") == "Nguyễn Văn A"
    assert value_text(None) == ""
    assert value_text({"a": None, "b": ""}) == ""
    assert value_text(True) == "true"
    assert value_text({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    assert value_text(12) == "12"


def test_value_text_chuan_hoa_unicode():
    assert value_text("Hoà") == value_text("Hoà")


def test_field_key_co_occurrence():
    assert field_key(f("x", 1)) == "x"
    assert field_key(f("x", 1, occurrence=2)) == "x#2"


def test_check_passes_tung_phep():
    assert check_passes({"op": "equals", "expected": "A"}, "A")
    assert not check_passes({"op": "equals", "expected": "A"}, "a")
    assert check_passes({"op": "contains", "expected": "Nội"}, "Hà Nội")
    assert check_passes({"op": "not_contains", "expected": "x"}, "abc")
    assert check_passes({"op": "empty", "expected": ""}, "")
    assert check_passes({"op": "not_empty", "expected": ""}, "a")
    assert check_passes({"op": "regex", "expected": r"^\d{2}/\d{2}/\d{4}$"}, "01/02/2003")


def test_check_rong_khong_duoc_tu_dong_dat():
    # expected rỗng ở contains/not_contains là tiêu chí hỏng: "" nằm trong mọi chuỗi nên sẽ luôn đạt.
    assert not check_passes({"op": "contains", "expected": ""}, "abc")
    assert not check_passes({"op": "not_contains", "expected": ""}, "abc")


def test_regex_hong_khong_lam_sap():
    assert not check_passes({"op": "regex", "expected": "("}, "abc")


def test_evaluate_can_dat_het_moi_lan():
    checks = [{"field": "a", "op": "equals", "expected": "1"}, {"field": "b", "op": "not_empty", "expected": ""}]
    runs = [run([f("a", "1"), f("b", "x")]), run([f("a", "1"), f("b", "")]), run([f("a", "2"), f("b", "x")])]
    result = evaluate(checks, runs)
    assert result["passed"] == 1 and result["total"] == 3 and not result["allPass"]


def test_luot_loi_tinh_la_truot():
    checks = [{"field": "a", "op": "empty", "expected": ""}]
    result = evaluate(checks, [run([f("a", "")]), {"status": "error", "error": "x"}])
    assert result["passed"] == 1 and not result["allPass"]


def test_khong_co_tieu_chi_thi_khong_dat():
    assert not evaluate([], [run([])])["allPass"]


def test_field_vang_mat_tinh_la_rong():
    assert evaluate([{"field": "a", "op": "empty", "expected": ""}], [run([f("b", "x")])])["allPass"]


def test_unknown_fields_bo_qua_phep_kiem_rong():
    known = known_fields([f("a", "1")], [run([f("b", "2")])])
    assert known == {"a", "b"}
    checks = [{"field": "c", "op": "equals"}, {"field": "d", "op": "empty"}, {"field": "a", "op": "equals"}]
    assert unknown_fields(checks, known) == ["c"]


def test_field_table():
    table = field_table([f("a", "0")], [run([f("a", "1")]), run([f("a", "2"), f("b", "x")]), {"status": "error"}])
    assert table[0] == {"field": "a", "original": "0", "runs": ["1", "2", None], "stable": False}
    assert table[1] == {"field": "b", "original": "", "runs": ["", "x", None], "stable": False}


def test_hoi_quy_chi_tinh_gia_tri_chua_tung_thay():
    baseline = [run_values([f("a", "1"), f("b", "x")]), run_values([f("a", "2"), f("b", "x")])]
    # a dao động sẵn giữa 1 và 2 nên về 2 không phải hồi quy; b đổi hẳn sang y thì là hồi quy.
    assert [r["field"] for r in find_regressions(baseline, [run([f("a", "2"), f("b", "y")])], set())] == ["b"]


def test_hoi_quy_bo_qua_field_trong_pham_vi_sua():
    baseline = [run_values([f("a", "sai")])]
    assert find_regressions(baseline, [run([f("a", "dung")])], {"a"}) == []


def test_do_giong_luot_goc():
    original = [f("a", "1"), f("b", "2"), f("c", ""), f("d", "4")]
    # c trống ở lượt gốc nên không tính; lấy lần tốt nhất.
    result = replay_coverage(original, [run([f("a", "x")]), run([f("a", "x"), f("b", "y")]), {"status": "error"}])
    assert result == {"original": 3, "matched": 2, "ratio": 0.667}


def test_luot_goc_rong_thi_khong_canh_bao():
    assert replay_coverage([f("a", "")], [run([])])["ratio"] == 1.0


def test_mat_field_la_hoi_quy():
    baseline = [run_values([f("a", "1"), f("b", "x")])]
    assert [r["field"] for r in find_regressions(baseline, [run([f("a", "1")])], set())] == ["b"]
