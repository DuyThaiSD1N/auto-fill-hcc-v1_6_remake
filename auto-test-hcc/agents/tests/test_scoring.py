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


# ---- Đính kèm: kế hoạch quy thành ô ảo ---------------------------------------------------------------------------

from scoring import attach_fields  # noqa: E402

PLAN = [
    {"fileIndex": 0, "sourceSegments": [{"fileIndex": 0, "pageIndexes": [0, 1]}], "documentName": "Tờ khai",
     "componentName": "Tờ khai đăng ký", "target": "existing", "detectedType": "to_khai"},
    {"fileIndex": 0, "sourceSegments": [{"fileIndex": 0, "pageIndexes": [3]}, {"fileIndex": 1, "pageIndexes": None}],
     "documentName": "Căn cước", "componentName": "Giấy tờ tùy thân", "target": "existing"},
    {"fileIndex": 2, "documentName": "Giấy khác", "componentName": "Giấy tờ khác", "target": "new", "needsAddComponent": True},
]


def values(fields):
    return {f["name"]: f["value"] for f in fields}


def test_ke_hoach_dinh_kem_thanh_o_ao():
    got = values(attach_fields(PLAN, [4, 1, None], ["Thiếu giấy X"]))
    assert got["dòng: Tờ khai đăng ký"] == "Tờ khai [#1:1-2]"
    assert got["dòng: Giấy tờ tùy thân"] == "Căn cước [#1:4 + #2]"
    assert got["dòng: Thêm mới: Giấy tờ khác"] == "Giấy khác [#3]"
    assert got["loại: to_khai"] == "Tờ khai đăng ký"
    assert got["tệp #1"] == "1→Tờ khai đăng ký; 2→Tờ khai đăng ký; 3→(không đính); 4→Giấy tờ tùy thân"
    assert got["tệp #3"] == "cả tệp→Thêm mới: Giấy tờ khác"
    assert got["tổng: số mục"] == "3"
    assert got["tổng: trang thiếu"] == "#1:3"
    assert got["tổng: trang trùng"] == ""
    assert got["tổng: lỗi"] == "Thiếu giấy X"


def test_dong_them_moi_mang_ten_giay_gom_chung_mot_khoa():
    plan = [
        {"fileIndex": 0, "documentName": "Bằng tốt nghiệp", "componentName": "Bằng tốt nghiệp", "target": "new", "needsAddComponent": True},
        {"fileIndex": 1, "documentName": "Chứng chỉ tin học", "target": "new", "needsAddComponent": True},
    ]
    got = values(attach_fields(plan, [1, 1]))
    # Tên giấy LLM đặt đổi giữa các lần chạy: khoá dòng và ô tệp #n không được đổi theo.
    assert got["dòng: Thêm mới"] == "Bằng tốt nghiệp [#1] | Chứng chỉ tin học [#2]"
    assert got["tệp #1"] == "1→Thêm mới" and got["tệp #2"] == "1→Thêm mới"


def test_trang_trung_va_tep_khong_dinh():
    plan = [
        {"fileIndex": 0, "documentName": "A", "componentName": "Dòng 1", "target": "existing"},
        {"fileIndex": 0, "sourceSegments": [{"fileIndex": 0, "pageIndexes": [1]}], "documentName": "B", "componentName": "Dòng 2",
         "target": "existing"},
    ]
    got = values(attach_fields(plan, [2, 1]))
    assert got["tổng: trang trùng"] == "#1:2"  # cả tệp 1 vào dòng 1, trang 2 lại vào dòng 2
    assert got["tệp #2"] == "1→(không đính)"
    assert got["tổng: trang thiếu"] == "#2:1"


def test_khong_biet_so_trang_thi_danh_dau_chua_ro():
    plan = [{"fileIndex": 0, "sourceSegments": [{"fileIndex": 0, "pageIndexes": [0]}], "documentName": "A", "componentName": "D",
             "target": "existing"}]
    got = values(attach_fields(plan, [None]))
    assert got["tệp #1"] == "1→D"
    assert got["tổng: trang thiếu"] == "#1:?"  # có thể đủ, có thể sót: tiêu chí "trang thiếu rỗng" không tự đạt


def test_tieu_chi_dinh_kem_cham_nhu_field():
    good = {"status": "ok", "response": {"fields": attach_fields(PLAN, [3, 1, None])}}
    wrong = [dict(PLAN[0]), dict(PLAN[1], componentName="Giấy tờ khác"), PLAN[2]]
    bad = {"status": "ok", "response": {"fields": attach_fields(wrong, [3, 1, None])}}
    checks = [
        {"field": "dòng: Giấy tờ tùy thân", "op": "contains", "expected": "Căn cước"},
        {"field": "tổng: số mục", "op": "equals", "expected": "3"},
    ]
    result = evaluate(checks, [good, bad])
    assert [cell["ok"] for cell in result["rows"][0]["cells"]] == [True, False]
    assert result["passed"] == 1


# ---- thủ tục có thanh tra (điền đợt 2) --------------------------------------------------------------------------------

def test_ghep_ban_va_thanh_tra_ghi_de_dung_o_va_them_o_moi():
    from scoring import merge_patch

    first = [f("hoTen", "Nguyen Van B"), f("ngay", "01/02/2000", occurrence=2), f("xa", "Xã Mẫu")]
    patch = [{"name": "hoTen", "value": "Nguyễn Văn B", "from": "Nguyen Van B", "by": "dinh_danh"},
             {"name": "soGiay", "value": "001", "from": None, "by": "dinh_danh"}]
    merged = merge_patch(first, patch)
    assert run_values(merged) == {"hoTen": "Nguyễn Văn B", "ngay#2": "01/02/2000", "xa": "Xã Mẫu", "soGiay": "001"}
    assert all("from" not in m and "by" not in m for m in merged)
    assert first[0]["value"] == "Nguyen Van B"  # không sửa list lượt đầu tại chỗ


def test_bang_field_co_cot_dot1_khi_thanh_tra_doi_o():
    patched = {"status": "ok", "response": {"fields": [f("hoTen", "Nguyễn Văn B"), f("xa", "Xã Mẫu")],
                                            "firstPassFields": [f("hoTen", "Nguyen Van B"), f("xa", "Xã Mẫu")]}}
    plain = run([f("hoTen", "Nguyễn Văn B"), f("xa", "Xã Mẫu")])
    table = {row["field"]: row for row in field_table([f("hoTen", "Nguyễn Văn B"), f("xa", "Xã Mẫu")], [patched, plain],
                                                       [f("hoTen", "Nguyen Van B"), f("xa", "Xã Mẫu")])}
    assert table["hoTen"]["dot1"] == ["Nguyen Van B", None]
    assert table["hoTen"]["originalDot1"] == "Nguyen Van B"
    assert "dot1" not in table["xa"]  # ô thanh tra không đổi thì bảng giữ như cũ
