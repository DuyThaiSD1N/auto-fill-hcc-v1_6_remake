"""Liên vận Việt - Lào: Qwen đọc ảnh song song (bảng Giấy đề nghị, phường/xã, điện thoại, số khung/số máy IN trên
giấy xe) ghép với kết quả OCR + LLM. Dữ liệu giả."""

import asyncio
import json

from app.pipelines.cap_giay_phep_lien_van_viet_lao.process import mapper, runner, vision

_LLM_CAR = {"bienSo": "43A-000.01", "soKhung": "KHUNGOCR", "soMay": "MAYOCR", "mauSon": "B1",
            "hinhThucHoatDong": "Vận chuyển hành khách"}


def _parsed(**kw):
    base = {"rows": [], "certs": [], "area": {}, "phone": ""}
    base.update(kw)
    return base


def test_parse_bo_hang_rong_va_sai_khung():
    parsed = vision.parse({
        "dia_chi": {"tinh": "Quảng Trị", "xa": "Phường A"}, "dien_thoai": "0900 000 001",
        "phuong_tien": [{"bienSo": "", "mauSon": ""}, {"mauSon": "Trắng", "soKhung": "AB 12 34"}],
        "giay_xe": [{"soKhung": "AB1234"}],
    })
    assert parsed["rows"] == [{"mauSon": "Trắng", "soKhung": "AB1234"}]
    assert parsed["certs"] == [{"soKhung": "AB1234"}]
    assert parsed["phone"] == "0900000001"
    assert vision.parse({"x": []}) is None


def test_merge_mau_son_so_khung_bang_anh_thang_hinh_thuc_giu_llm():
    rows = [{"bienSo": "43A 00001", "soKhung": "KHUNGANH", "mauSon": "Bạc", "hinhThucHoatDong": "Hành Khách",
             "cuaKhau": "Tất cả"}]
    cars, _ = vision.merge_vehicles([dict(_LLM_CAR)], _parsed(rows=rows))
    assert cars[0]["mauSon"] == "Bạc"
    assert cars[0]["soKhung"] == "KHUNGANH"
    assert cars[0]["soMay"] == "MAYOCR"
    assert cars[0]["hinhThucHoatDong"] == "Vận chuyển hành khách"
    assert cars[0]["cuaKhau"] == "Tất cả"


def test_merge_so_in_tren_giay_xe_vao_khoa_dang_ky():
    certs = [{"bienSo": "43A-000.01", "soKhung": "KHUNGIN", "soMay": "MAYIN"}]
    cars, _ = vision.merge_vehicles(json.dumps([_LLM_CAR]), _parsed(certs=certs))
    assert cars[0]["soKhungDangKy"] == "KHUNGIN" and cars[0]["soMayDangKy"] == "MAYIN"


def test_merge_ngay_chi_giu_khi_hai_luot_doc_khop():
    car = dict(_LLM_CAR, tuNgay="08/10/2026", denNgay="21/10/2026")
    rows = [{"bienSo": "43A00001", "tuNgay": "8/10/2026", "denNgay": "31/12/2026"}]
    cars, warnings = vision.merge_vehicles([car], _parsed(rows=rows))
    assert cars[0]["tuNgay"] == "08/10/2026"
    assert "denNgay" not in cars[0]
    assert len(warnings) == 1 and "đến ngày" in warnings[0]


def test_merge_khong_co_ket_qua_anh_thi_giu_nguyen():
    assert vision.merge_vehicles([dict(_LLM_CAR)], None) == ([_LLM_CAR], [])


def test_mapper_uu_tien_so_in_tren_giay_xe_va_bo_mau_son_lan_so():
    car = mapper._vehicles([{"bienSo": "43A00001", "soKhung": "VIETTAY", "soKhungDangKy": "IN TREN GIAY",
                             "soMay": "MAY1", "mauSon": "B1", "tuNgay": "08/10/2026", "denNgay": "08/10/2026"}])[0]
    assert car["soKhung"] == "INTRENGIAY"
    assert car["soMay"] == "MAY1"
    assert "soKhungDangKy" not in car and "mauSon" not in car
    assert car["tuNgay"] == "08/10/2026" and "denNgay" not in car


def _run(monkeypatch, llm_fields, parsed):
    async def fake_compact(_files_by_role, **_kwargs):
        return {"fields": llm_fields, "errors": []}

    async def fake_vision(_files):
        return parsed

    monkeypatch.setattr(runner.runner, "run", fake_compact)
    monkeypatch.setattr(vision, "read_application", fake_vision)
    res = asyncio.run(runner.run({"doc": []}, {}))
    return {f["name"]: f["value"] for f in res["fields"]}, res.get("errors", [])


def test_runner_ghep_phuong_xa_dien_thoai_va_canh_bao(monkeypatch):
    fields = [
        {"name": "NguoiNop_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "NguoiNop_ThuongTru", "value": {"tinh": "Quảng Trị", "xa": "Phường Không Có", "diaChi": "Số 1"}},
        {"name": "NguoiNop_DienThoai", "value": "0900000001"},
        {"name": "DeNghi_PhuongTien", "value": [dict(_LLM_CAR)]},
    ]
    parsed = _parsed(area={"tinh": "Quảng Trị", "xa": "P. Đúng"}, phone="0900000002",
                     rows=[{"bienSo": "43A00001", "mauSon": "Bạc"}],
                     certs=[{"bienSo": "43A00001", "soKhung": "KHUNGIN"}])
    d, errors = _run(monkeypatch, fields, parsed)
    assert d["data[district]"] == "Phường Đúng"
    assert d["data[address]"] == "Số 1"
    assert d["data[phoneNumber]"] == "0900000002"
    assert any("điện thoại" in e for e in errors)
    car = json.loads(d["data[panel_caNhanToChuc][BienSoXeData]"])[0]
    assert car["mauSon"] == "Bạc" and car["soKhung"] == "KHUNGIN"


def test_vision_loi_thi_runner_giu_ket_qua_llm(monkeypatch):
    fields = [{"name": "DeNghi_PhuongTien", "value": [{"bienSo": "43A00001", "mauSon": "Xanh"}]}]
    d, _ = _run(monkeypatch, fields, None)
    assert json.loads(d["data[panel_caNhanToChuc][BienSoXeData]"])[0]["mauSon"] == "Xanh"


def test_mapper_nguoi_nop_to_chuc_chon_doi_tuong_to_chuc():
    out, warnings = mapper.enrich([
        {"name": "NguoiNop_LoaiDoiTuong", "value": "Tổ chức"},
        {"name": "NguoiNop_HoTen", "value": "CÔNG TY TNHH GIẢ"},
    ])
    d = {f["name"]: f["value"] for f in out}
    assert d["data[chonDoiTuong]"] == "Tổ chức" and d["data[fullname]"] == "CÔNG TY TNHH GIẢ"
    assert any("mã số thuế" in w for w in warnings)
    out, _ = mapper.enrich([{"name": "NguoiNop_HoTen", "value": "NGUYỄN VĂN A"}])
    assert {f["name"]: f["value"] for f in out}["data[chonDoiTuong]"] == "Cá nhân"
