"""Dựng ca hồi quy: dữ liệu thật bị thay nhất quán giữa OCR / LLM / tiêu chí, còn sót thì không ghi ca."""
import json

import pytest

import regression_case
from regression_case import Anonymizer, Skip

NAME = "Trịnh Văn Thật"
CCCD = "001099012345"
ADDRESS = "Số 12 ngõ 5 phố Hàng Bông, Phường Hoàn Kiếm, Thành phố Hà Nội"
OCR = f"CĂN CƯỚC\nHọ và tên: {NAME.upper()}\nSố định danh: {CCCD}\nNơi thường trú: {ADDRESS}\nNgày sinh: 01/02/1990\n"
RAW = ('```json\n{"fields": {"HoTen": "' + NAME + '", "SoCCCD": "' + CCCD + '", "DiaChiThuongTru": "' + ADDRESS
       + '", "NgaySinh": "01/02/1990"}}\n```')
FIELDS = [{"name": "HoTen", "value": NAME.upper()}, {"name": "SoCCCD", "value": CCCD},
          {"name": "DiaChiThuongTru", "value": ADDRESS}, {"name": "NgaySinh", "value": "01/02/1990"}]


class Collection:
    def __init__(self, docs):
        self.docs = docs

    def find_one(self, query, projection=None):
        return next((d for d in self.docs if all(d.get(k) == v for k, v in query.items())), None)


class FakeDb:
    def __init__(self, raw=RAW, truncated=False):
        self.trace_steps = Collection([{"_id": "rq_run:autofill", "ocr": [{"name": "cccd.jpg", "sha256": "s1"}],
                                        "llm": [{"n": 1, "purpose": "extract", "raw": raw}]}])
        self.ocr_texts = Collection([{"_id": "s1", "text": OCR, "truncated": truncated}])
        self.process_requests = Collection([{"request_id": "rq_run", "fields": FIELDS}])


def build(db=None, checks=None):
    return regression_case.build(
        job={"id": "at_1", "requestId": "rq_goc"},
        case={"procedure": "thu-tuc", "label": "Thủ tục", "fields": FIELDS, "storedFiles": [{"name": "cccd.jpg", "role": "doc"}]},
        decision={"acceptance": checks or [{"field": "HoTen", "op": "equals", "expected": NAME.upper()},
                                           {"field": "NgaySinh", "op": "equals", "expected": "01/02/1990"}]},
        run_request_id="rq_run", db=db or FakeDb(), account={"username": "testxa", "xa": "Phường Hoàn Kiếm", "tinh": "Thành phố Hà Nội"},
        options={"formContext": {"applicantFullname": NAME, "applicantIdentityNumber": CCCD}},
    )


def test_thay_du_lieu_that_nhat_quan():
    case = build()
    dumped = json.dumps(case, ensure_ascii=False)
    for secret in (NAME, NAME.upper(), CCCD, "Hàng Bông", "rq_goc", "rq_run"):
        assert secret not in dumped
    fake = case["checks"][0]["expected"]
    assert fake.isupper() and fake != NAME.upper()
    assert fake in case["files"][0]["ocr"]  # OCR, LLM và tiêu chí cùng một tên giả
    assert fake.title() in case["llm"][0]["raw"] or fake in case["llm"][0]["raw"].upper()
    raw_digits = json.loads(case["llm"][0]["raw"].strip("`json\n"))["fields"]["SoCCCD"]
    assert raw_digits != CCCD and len(raw_digits) == 12 and raw_digits[:3] == CCCD[:3] and raw_digits in case["files"][0]["ocr"]
    # Giữ đơn vị hành chính và ngày tháng: mapper / remap cần.
    assert "Phường Hoàn Kiếm" in case["files"][0]["ocr"] and "01/02/1990" in case["files"][0]["ocr"]
    assert case["account"] == {"username": "testxa", "xa": "Phường Hoàn Kiếm", "tinh": "Thành phố Hà Nội"}
    assert NAME not in json.dumps(case["options"], ensure_ascii=False)


def test_ten_ma_hoa_unicode_trong_cau_tra_loi_llm_cung_bi_thay():
    escaped = json.dumps({"fields": {"HoTen": NAME}})  # ensure_ascii: "Trịnh Văn Thật"
    assert "\\u" in escaped
    case = build(db=FakeDb(raw=escaped))
    assert NAME not in case["llm"][0]["raw"] and "\\u1ecb" not in case["llm"][0]["raw"]


def test_bo_phan_suy_nghi_cua_model():
    case = build(db=FakeDb(raw="<think>người này tên " + NAME + "</think>" + RAW))
    assert "<think></think>" in case["llm"][0]["raw"] and NAME not in case["llm"][0]["raw"]


def test_ocr_bi_cat_khi_ghi_trace_thi_khong_dung_ca():
    with pytest.raises(Skip, match="bị cắt"):
        build(db=FakeDb(truncated=True))


def test_con_sot_du_lieu_that_thi_khong_ghi(monkeypatch):
    monkeypatch.setattr(Anonymizer, "text", lambda self, text: text)  # giả lập bước thay bỏ sót
    with pytest.raises(Skip, match="dữ liệu thật"):
        build()


def test_dia_chi_chi_thay_phan_so_nha_thon():
    anon = Anonymizer()
    anon.add_address("Thôn Đồng Xuân, Xã Song Liễu, Tỉnh Bắc Ninh")
    out = anon.text("Thôn Đồng Xuân, Xã Song Liễu, Tỉnh Bắc Ninh")
    assert "Đồng Xuân" not in out and out.endswith("Xã Song Liễu, Tỉnh Bắc Ninh") and out.startswith("Thôn Mẫu")


def test_ten_giay_to_khong_bi_coi_la_ten_nguoi():
    anon = Anonymizer()
    anon.collect({"documentName": "Giấy khai sinh", "fileName": "a b.pdf", "HoTenCha": "Lê Văn Bố"})
    assert "giấy khai sinh" not in anon.names and "lê văn bố" in anon.names


def _harness():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("harness", Path(__file__).resolve().parents[2] / "regression/harness.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tep_gia_la_png_hop_le_va_khac_nhau():
    import base64

    harness = _harness()
    first, second = harness.data_url(0), harness.data_url(1)
    assert first != second and first.startswith("data:image/png;base64,")
    assert base64.b64decode(first.split(",", 1)[1]).startswith(b"\x89PNG\r\n\x1a\n")


def test_llm_gia_tra_theo_purpose_roi_theo_thu_tu(monkeypatch):
    import asyncio
    import sys
    import types

    harness = _harness()
    current = {"purpose": None}
    client = types.SimpleNamespace(_call=types.SimpleNamespace(get=lambda: current))
    monkeypatch.setitem(sys.modules, "app", types.ModuleType("app"))
    monkeypatch.setitem(sys.modules, "app.services", types.ModuleType("app.services"))
    monkeypatch.setitem(sys.modules, "app.services.llm", types.SimpleNamespace(client=client))
    replayer = harness.Replayer({"files": [], "llm": [{"purpose": "extract", "raw": "A"}, {"purpose": "review", "raw": "B"},
                                                      {"purpose": "extract", "raw": "C"}]})
    current["purpose"] = "review"
    assert asyncio.run(replayer.llm([])) == "B"
    current["purpose"] = "extract"
    assert asyncio.run(replayer.llm([])) == "A" and asyncio.run(replayer.llm([])) == "C"
    with pytest.raises(RuntimeError, match="nhiều hơn lúc ghi"):
        asyncio.run(replayer.llm([]))
    assert replayer.extra == ["extract"]
