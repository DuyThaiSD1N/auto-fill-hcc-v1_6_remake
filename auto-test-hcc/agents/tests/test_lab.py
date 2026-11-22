"""Auto test trong Monitor: đáp án ca test, dòng thời gian, ẩn danh ca dựng từ lượt thật, chạy bộ ca."""
import json
from datetime import datetime, timezone

import pytest

import lab
import regression_case

NAME = "Trịnh Văn Thật"
CCCD = "001099012345"
OCR = f"CĂN CƯỚC\nHọ và tên: {NAME.upper()}\nSố định danh: {CCCD}\nNgày sinh: 01/02/1990\n"
RAW = '```json\n{"fields": {"HoTen": "' + NAME + '", "SoCCCD": "' + CCCD + '", "NgaySinh": "01/02/1990"}}\n```'
BE_FIELDS = [{"name": "HoTen", "value": NAME.upper()}, {"name": "SoCCCD", "value": CCCD},
             {"name": "NgaySinh", "value": "01/02/1989"}, {"name": "GioiTinh", "value": "Nam"}]
START = datetime(2026, 11, 20, 3, 0, 0, tzinfo=timezone.utc)
T0 = int(START.timestamp() * 1000)


def review():
    return {
        "trust": "step",
        "snapshots": [
            {"kind": "fill", "trigger": "", "at": T0 + 6000, "fields": 6, "empty": False, "extVersion": "1.28.29"},
            {"kind": "edit", "trigger": "", "at": T0 + 30000, "fields": 6, "empty": False},
            {"kind": "step", "trigger": "Lưu và nộp hồ sơ", "at": T0 + 60000, "fields": 6, "empty": False},
        ],
        "rows": [
            {"name": "HoTen", "label": "Họ và tên", "inBe": True, "be": NAME.upper(), "fill": NAME.upper(), "final": NAME.upper(),
             "verdict": "same", "files": []},
            {"name": "SoCCCD", "label": "Số định danh", "inBe": True, "be": CCCD, "fill": CCCD, "final": CCCD, "verdict": "same",
             "files": []},
            {"name": "NgaySinh", "label": "Ngày sinh", "inBe": True, "be": "01/02/1989", "fill": "01/02/1989",
             "final": "01/02/1990", "verdict": "ocr", "files": [0]},
            {"name": "GioiTinh", "label": "Giới tính", "inBe": True, "be": "Nam", "fill": "Nam", "final": "", "verdict": "cleared",
             "files": []},
            {"name": "SoDienThoai", "label": "Số điện thoại", "inBe": False, "be": None, "fill": None, "final": "0912345678",
             "verdict": "missing", "files": []},
            {"name": "NoiSinh", "label": "Nơi sinh", "inBe": False, "be": None, "fill": None, "final": "Hà Nội",
             "verdict": "missing", "files": [0]},
            {"name": "QuocTich", "label": "Quốc tịch", "inBe": True, "be": "Việt Nam", "fill": "", "final": "",
             "verdict": "nodata", "files": []},
        ],
    }


class Collection:
    def __init__(self, docs=()):
        self.docs = list(docs)

    def find_one(self, query, projection=None):
        return next((d for d in self.docs if all(d.get(k) == v for k, v in query.items())), None)


class FakeDb:
    def __init__(self):
        self.ocr_texts = Collection([{"_id": "s1", "text": OCR}])
        self.users = Collection([{"_id": "u1", "username": "testxa", "xa": "Phường Hoàn Kiếm", "tinh": "Thành phố Hà Nội"}])
        self.conversations = Collection()
        self.dossiers = Collection()


def data(with_review=True):
    return {
        "requestId": "rq_goc",
        "request": {"request_id": "rq_goc", "procedure": "trich-luc-ks", "experience": "autofill", "user_id": "u1",
                    "created_at": START, "finished_at": START.replace(second=4),
                    "files": [{"name": "cccd.jpg", "role": "doc", "sha256": "s1"}],
                    "fields": BE_FIELDS, "options": {"formContext": {"applicantFullname": NAME}, "dossierId": "ho_so_1"}},
        "trace": {"kind": "autofill", "procedure_label": "Trích lục khai sinh", "timing": {"wait": 4000}},
        "steps": {"kind": "autofill", "timing": {"wait": 4000},
                  "spans": [{"i": 1, "p": None, "n": "pre.request", "t0": 0, "ms": 4000, "st": "ok"},
                            {"i": 2, "p": 1, "n": "ocr.call", "t0": 100, "ms": 900, "st": "ok"},
                            {"i": 3, "p": 1, "n": "post.mapper", "t0": 3500, "ms": 200, "st": "ok"}],
                  "ocr": [{"idx": 0, "name": "cccd.jpg", "sha256": "s1", "pages": 1, "chars": len(OCR), "cache": "miss"}],
                  "llm": [{"n": 1, "purpose": "extract", "t0": 1100, "ms": 2300, "model": "m", "raw": RAW,
                           "parsed": json.loads(RAW.strip("`json\n"))}],
                  "outputs": {"response": {"fields": BE_FIELDS}}},
        "stored": None, "review": review() if with_review else None, "db": FakeDb(), "source": "mongo",
    }


def test_dap_an_theo_gia_tri_nguoi_dan_de_lai_khi_nop():
    checks = {c["field"]: c for c in lab.answer_checks(lab._rows(data()), BE_FIELDS)}
    assert checks["HoTen"]["expected"] == NAME.upper() and not checks["HoTen"].get("edited")
    assert checks["NgaySinh"] == {**checks["NgaySinh"], "op": "equals", "expected": "01/02/1990", "edited": True}
    assert checks["GioiTinh"]["op"] == "empty"
    assert checks["NoiSinh"]["expected"] == "Hà Nội" and checks["NoiSinh"]["missed"]
    # Ô người dân tự gõ mà giấy tờ không có, ô form không nhận giá trị backend: backend không chấm được.
    assert "SoDienThoai" not in checks and "QuocTich" not in checks


def test_o_surveyjs_co_hau_to_so_theo_ten_goc_cua_backend():
    sample = data()
    sample["review"]["rows"].append({"name": "HoTenMe__1761724625529", "label": "Họ, tên Mẹ", "inBe": False, "be": None,
                                     "fill": None, "final": "Nguyễn Thị Mẫu", "verdict": "missing", "files": [0]})
    sample["request"]["fields"] = [*BE_FIELDS, {"name": "HoTenMe", "value": "Nguyễn Thị Mẫu"}]
    rows = {r["key"]: r for r in lab._rows(sample)}
    assert rows["HoTenMe__1761724625529"]["be"] == "Nguyễn Thị Mẫu" and rows["HoTenMe__1761724625529"]["inBe"]
    checks = {c["field"]: c for c in lab.answer_checks(list(rows.values()), sample["request"]["fields"])}
    assert checks["HoTenMe"]["expected"] == "Nguyễn Thị Mẫu" and "HoTenMe__1761724625529" not in checks


def test_chua_co_anh_chup_form_thi_dap_an_la_ket_qua_luc_ghi():
    checks = lab.answer_checks(lab._rows(data(with_review=False)), BE_FIELDS)
    assert {c["field"]: c["expected"] for c in checks}["NgaySinh"] == "01/02/1989"
    assert {c["verdict"] for c in checks} == {"recorded"}


def test_dong_thoi_gian_va_buoc():
    events, snapshots, start = lab._events(data(), [], None)
    assert start == T0 and events[0]["type"] == "request" and events[0]["t"] == 0
    assert [s["id"] for s in snapshots] == ["S1", "S2", "S3"] and snapshots[0]["t"] == 6000
    by_type = {e["type"]: e for e in events}
    assert by_type["llm"]["t"] == 1100 and by_type["llm"]["step"] == 2
    assert by_type["snapshot.edit"]["step"] == 3 and by_type["snapshot.step"]["step"] == 4  # bấm nộp = bước 5
    assert [e["no"] for e in events] == list(range(1, len(events) + 1))
    assert [e["t"] for e in events] == sorted(e["t"] for e in events)


def test_gio_backend_ghi_muon_hon_anh_chup_thi_doi_ve_truoc_lan_dien():
    late = data()
    late["request"]["created_at"] = START.replace(minute=5)
    late["request"]["finished_at"] = START.replace(minute=5)
    origin, estimated = lab.backend_origin(late)
    assert estimated and origin == T0 + 6000 - 1000 - 4000
    origin, estimated = lab.backend_origin(data())
    assert not estimated and origin == T0


def test_nhan_dien_o_nguoi_dan_sua():
    summary = lab._summary(lab._rows(data()))
    assert summary["edited"] == 2 and summary["same"] == 2 and summary["missing"] == 2 and summary["missingOnDocs"] == 1
    assert summary["nodata"] == 1


def test_ca_test_an_danh_nhat_quan():
    case = lab.build_case(data(), "TLK-0001")
    dumped = json.dumps(case, ensure_ascii=False)
    for secret in (NAME, NAME.upper(), CCCD, "rq_goc", "ho_so_1"):
        assert secret not in dumped
    checks = {c["field"]: c for c in case["checks"]}
    fake = checks["HoTen"]["expected"]
    assert fake != NAME.upper() and fake in case["files"][0]["ocr"]
    assert checks["NgaySinh"]["expected"] == "01/02/1990" and checks["NgaySinh"]["edited"]
    assert case["answer"] == "form" and case["stats"]["edited"] == 3 and case["origin"] == "lab"
    assert case["account"] == {"username": "testxa", "xa": "Phường Hoàn Kiếm", "tinh": "Thành phố Hà Nội"}
    assert "dossierId" not in case["options"]


def test_luot_dinh_kem_khong_tao_ca():
    attach = data()
    attach["trace"]["kind"] = "attach"
    with pytest.raises(regression_case.Skip):
        lab.build_case(attach, "TLK-0002")


def test_tao_ca_ghi_vao_runs_lab_va_khong_tao_trung(tmp_path, monkeypatch):
    monkeypatch.setattr(lab, "LAB", tmp_path)
    monkeypatch.setattr(lab, "SUITES", tmp_path / "suites")
    monkeypatch.setattr(lab, "INDEX", tmp_path / "cases.json")
    monkeypatch.setattr(lab, "ACCESS", tmp_path / "access.jsonl")
    monkeypatch.setattr(lab, "load", lambda request_id: data())
    first = lab.create_case("rq_goc", {"username": "admin"})
    assert first == {"caseId": "TLK-0001", "existing": False, "stats": first["stats"]}
    assert (tmp_path / "suites" / "trich-luc-ks" / "TLK-0001.json").is_file()
    assert lab.create_case("rq_goc", {"username": "admin"}) == {"caseId": "TLK-0001", "existing": True}
    assert lab.recent_access()[0]["action"] == "tạo ca test"
    suites = lab.suites()["suites"]
    assert suites[0]["key"] == "lab:trich-luc-ks" and suites[0]["cases"][0]["requestId"] == "rq_goc"


def test_trang_thai_ca():
    assert lab._status({"status": 200, "ok": True, "rows": [{"ok": True}]}) == "pass"
    assert lab._status({"status": 200, "ok": True, "rows": [{"ok": True}], "extraFields": ["X"]}) == "review"
    assert lab._status({"status": 200, "ok": False, "rows": [{"ok": False}]}) == "fail"
    assert lab._status({"status": 500, "ok": False, "error": "HTTP 500"}) == "error"
    assert lab._status({"ok": False, "error": "KeyError: x"}) == "error"
