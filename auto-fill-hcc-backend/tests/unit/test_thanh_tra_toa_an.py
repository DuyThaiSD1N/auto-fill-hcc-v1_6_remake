import asyncio
import json

import pytest

from app.pipelines._shared.cccd import mrz_records
from app.pipelines._shared.thanh_tra import engine
from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Inspector, Unit, compare_key
from app.pipelines.trich_luc_dvc_moi import thanh_tra
from app.pipelines.trich_luc_dvc_moi.thanh_tra import dia_chi, ho_tich, nhan_than
from app.services.llm import client

OCR = ("GIẤY KHAI SINH\nSố: 12/1990\nHọ, chữ đệm, tên: TRẦN THỊ BÌNH\nNgày, tháng, năm sinh: 01/02/1990\n"
       "Họ, chữ đệm, tên người mẹ: LÊ THỊ CÚC\nNơi cư trú: Thôn 1, xã An Phú, tỉnh Lâm Đồng\n"
       "Giấy tờ tùy thân: CMND số 250111222 cấp ngày 03/04/2005, CA Lâm Đồng")
DOCS = [{"name": "ks.pdf", "text": OCR}]
OWNERS = ("người được cấp", "cha / mẹ của người được cấp")
NAME = Unit("ho_ten", "Họ tên", (Field("HoTen", "họ tên"),))
BIRTH = Unit("ngay_sinh", "Ngày sinh", (Field("NgaySinh", "ngày sinh", "date"),))
CARD = Unit("giay_to", "Cụm giấy tờ", (Field("SoGiayTo", "số", "code"), Field("NgayCap", "ngày cấp", "date"),
                                       Field("NoiCap", "nơi cấp", "free")))
AREA = Unit("noi_cu_tru", "Nơi cư trú", (Field("NoiCuTru", "object địa chỉ", "area"),))


def _inspector(*units, check=None):
    return Inspector("nhom", "NHÓM THỬ", units, "luật thử", check, owners=OWNERS, accepted=OWNERS[:1])


def _answer(unit_key, values, quote, owner=OWNERS[0]):
    return {unit_key: {"values": values, "quote": quote, "doc": 1, "thuoc_ve": owner, "note": "x"}}


def _run(monkeypatch, values, inspector_reply, court_reply=None, inspectors=None):
    calls = []

    async def fake_chat(messages, **kwargs):
        purpose = kwargs.get("purpose")
        calls.append(purpose)
        if purpose == "thanh_tra.toa_an":
            return json.dumps(court_reply or {"phan_quyet": []})
        if isinstance(inspector_reply, Exception):
            raise inspector_reply
        return inspector_reply if isinstance(inspector_reply, str) else json.dumps(inspector_reply)

    monkeypatch.setattr(client, "chat", fake_chat)
    inspectors = inspectors or (_inspector(NAME, BIRTH, CARD, AREA),)
    result = asyncio.run(engine.run(Case(DOCS, "", values, {}), inspectors, title="thử"))
    return result, calls


def _verdict(choice, number=1):
    return {"phan_quyet": [{"id": number, "ly_do": "x", "chon": choice}]}


def test_trung_voi_luot_trich_thi_khong_co_vu_an_va_khong_goi_toa(monkeypatch):
    reply = _answer("ho_ten", {"HoTen": "Trần Thị Bình"}, "Họ, chữ đệm, tên: TRẦN THỊ BÌNH")
    result, calls = _run(monkeypatch, {"HoTen": "TRẦN THỊ BÌNH"}, reply)
    assert result.values == {"HoTen": "TRẦN THỊ BÌNH"} and not result.rulings
    assert "thanh_tra.toa_an" not in calls


@pytest.mark.parametrize("choice,expected,outcome", [
    ("B", "TRẦN THỊ BÌNH", "sua"), ("A", "TRẦN THỊ BINH", "giu"), ("KHONG_DU_CAN_CU", "TRẦN THỊ BINH", "giu"),
])
def test_toa_chon_ben_nao_thi_theo_ben_do(monkeypatch, choice, expected, outcome):
    reply = _answer("ho_ten", {"HoTen": "TRẦN THỊ BÌNH"}, "Họ, chữ đệm, tên: TRẦN THỊ BÌNH")
    result, _ = _run(monkeypatch, {"HoTen": "TRẦN THỊ BINH"}, reply, _verdict(choice))
    assert result.values["HoTen"] == expected
    assert [r["outcome"] for r in result.rulings] == [outcome]


def test_o_trong_duoc_bo_sung_khi_toa_chon_b(monkeypatch):
    reply = _answer("ngay_sinh", {"NgaySinh": "01/02/1990"}, "Ngày, tháng, năm sinh: 01/02/1990")
    result, _ = _run(monkeypatch, {}, reply, _verdict("B"))
    assert result.values == {"NgaySinh": "01/02/1990"} and result.rulings[0]["outcome"] == "bo_sung"


@pytest.mark.parametrize("court_reply", [
    {"phan_quyet": [{"id": 9, "ly_do": "x", "chon": "B"}]},  # sai id
    {"phan_quyet": [{"id": 1, "ly_do": "x", "chon": "C"}]},  # lựa chọn không hợp lệ
    {"phan_quyet": "B"},
])
def test_phan_quyet_khong_hop_le_thi_giu_luot_trich(monkeypatch, court_reply):
    reply = _answer("ho_ten", {"HoTen": "TRẦN THỊ BÌNH"}, "Họ, chữ đệm, tên: TRẦN THỊ BÌNH")
    result, _ = _run(monkeypatch, {"HoTen": "TRẦN THỊ BINH"}, reply, court_reply)
    assert result.values["HoTen"] == "TRẦN THỊ BINH" and result.rulings[0]["outcome"] == "giu"


@pytest.mark.parametrize("values,quote,owner,reason", [
    # Dòng chứng cứ không có trong OCR.
    ({"HoTen": "TRẦN THỊ BÌNH"}, "Họ tên người được khai sinh là Trần Thị Bình", OWNERS[0], "không có trong OCR"),
    # Giá trị bị đổi dấu so với giấy: không còn nguyên văn.
    ({"HoTen": "TRẦN THỊ BÍNH"}, "Họ, chữ đệm, tên: TRẦN THỊ BÌNH", OWNERS[0], "nguyên văn"),
    # Thanh tra tự khai dòng thuộc người khác.
    ({"HoTen": "LÊ THỊ CÚC"}, "Họ, chữ đệm, tên người mẹ: LÊ THỊ CÚC", OWNERS[1], "thuộc về"),
])
def test_ung_vien_khong_qua_cong_chan_thi_khong_ra_toa(monkeypatch, values, quote, owner, reason):
    result, calls = _run(monkeypatch, {"HoTen": "TRẦN THỊ BINH"}, _answer("ho_ten", values, quote, owner),
                         _verdict("B"))
    assert result.values["HoTen"] == "TRẦN THỊ BINH"
    assert result.rulings[0]["outcome"] == "bac_truoc_toa" and reason in result.rulings[0]["reason"]
    assert "thanh_tra.toa_an" not in calls


def test_check_cua_thu_tuc_bac_ung_vien(monkeypatch):
    inspector = _inspector(NAME, check=lambda unit, values, case: "lý do nghiệp vụ")
    reply = _answer("ho_ten", {"HoTen": "TRẦN THỊ BÌNH"}, "Họ, chữ đệm, tên: TRẦN THỊ BÌNH")
    result, calls = _run(monkeypatch, {"HoTen": "TRẦN THỊ BINH"}, reply, _verdict("B"), (inspector,))
    assert result.rulings[0]["reason"] == "lý do nghiệp vụ" and "thanh_tra.toa_an" not in calls


def test_cum_lech_thi_lay_nguyen_cum_cua_thanh_tra(monkeypatch):
    values = {"SoGiayTo": "001090000001", "NgayCap": "28/06/2021", "NoiCap": "Cục Cảnh sát"}
    reply = _answer("giay_to", {"SoGiayTo": "250111222", "NgayCap": "03/04/2005"},
                    "Giấy tờ tùy thân: CMND số 250111222 cấp ngày 03/04/2005, CA Lâm Đồng")
    result, _ = _run(monkeypatch, values, reply, _verdict("B"))
    # Nơi cấp của thẻ cũ không được trộn với số / ngày cấp của giấy khác.
    assert result.values == {"SoGiayTo": "250111222", "NgayCap": "03/04/2005"}


def test_cum_chi_thieu_field_thi_bo_sung_va_giu_phan_da_co(monkeypatch):
    values = {"SoGiayTo": "250111222", "NoiCap": "CA Lâm Đồng"}
    reply = _answer("giay_to", {"SoGiayTo": "250111222", "NgayCap": "03/04/2005"},
                    "Giấy tờ tùy thân: CMND số 250111222 cấp ngày 03/04/2005, CA Lâm Đồng")
    result, _ = _run(monkeypatch, values, reply, _verdict("B"))
    assert result.values == {"SoGiayTo": "250111222", "NgayCap": "03/04/2005", "NoiCap": "CA Lâm Đồng"}


def test_thanh_tra_khong_thay_field_thi_khong_tranh_chap(monkeypatch):
    reply = _answer("giay_to", {"SoGiayTo": "250111222"},
                    "Giấy tờ tùy thân: CMND số 250111222 cấp ngày 03/04/2005, CA Lâm Đồng")
    result, calls = _run(monkeypatch, {"SoGiayTo": "250111222", "NgayCap": "03/04/2005"}, reply)
    assert not result.rulings and "thanh_tra.toa_an" not in calls


@pytest.mark.parametrize("reply", [
    {"NoiCuTru": {"values": {"tinh": "Lâm Đồng", "xa": "An Phú", "diaChi": "Thôn 1"},
                  "quote": "Nơi cư trú: Thôn 1, xã An Phú, tỉnh Lâm Đồng", "doc": 1, "thuoc_ve": OWNERS[0]}},
    {"units": {"noi_cu_tru": {"values": {"NoiCuTru": {"tinh": "Lâm Đồng", "xa": "An Phú", "diaChi": "Thôn 1"}},
                              "quote": "Nơi cư trú: Thôn 1, xã An Phú, tỉnh Lâm Đồng", "doc": 1,
                              "thuoc_ve": OWNERS[0]}}},
])
def test_doc_duoc_cac_dang_model_tra_cho_dia_chi(monkeypatch, reply):
    result, _ = _run(monkeypatch, {}, reply, _verdict("B"))
    assert result.values["NoiCuTru"] == {"tinh": "Lâm Đồng", "xa": "An Phú", "diaChi": "Thôn 1"}


def test_model_bo_tien_to_ten_field_va_thua_ngoac_van_doc_duoc(monkeypatch):
    unit = Unit("ho_ten", "Họ tên", (Field("NguoiDuocCap_HoTen", "họ tên"),))
    raw = json.dumps(_answer("ho_ten", {"HoTen": "TRẦN THỊ BÌNH"}, "Họ, chữ đệm, tên: TRẦN THỊ BÌNH")) + "}"
    result, _ = _run(monkeypatch, {}, raw, _verdict("B"), (_inspector(unit),))
    assert result.values == {"NguoiDuocCap_HoTen": "TRẦN THỊ BÌNH"}


def test_thanh_tra_loi_hoac_toa_loi_khong_lam_hong_luot_trich(monkeypatch):
    result, _ = _run(monkeypatch, {"HoTen": "X"}, RuntimeError("LLM chết"))
    assert result.values == {"HoTen": "X"} and result.rulings[0]["outcome"] == "thanh_tra_loi"

    async def court_down(messages, **kwargs):
        if kwargs.get("purpose") == "thanh_tra.toa_an":
            raise RuntimeError("toà chết")
        return json.dumps(_answer("ho_ten", {"HoTen": "TRẦN THỊ BÌNH"}, "Họ, chữ đệm, tên: TRẦN THỊ BÌNH"))

    monkeypatch.setattr(client, "chat", court_down)
    result = asyncio.run(engine.run(Case(DOCS, "", {"HoTen": "TRẦN THỊ BINH"}, {}), (_inspector(NAME),), title="thử"))
    assert result.values == {"HoTen": "TRẦN THỊ BINH"} and result.rulings[0]["outcome"] == "giu"


def test_nhiem_vu_rieng_dung_sau_ocr_de_dung_lai_tien_to(monkeypatch):
    seen = []

    async def fake_chat(messages, **kwargs):
        seen.append(messages)
        return "{}"

    monkeypatch.setattr(client, "chat", fake_chat)
    asyncio.run(engine.llm_findings(_inspector(NAME), Case(DOCS, "", {}, {}), "thử"))
    user = seen[0][1]["content"]
    assert user.index(OCR) < user.index("<nhiem_vu")


@pytest.mark.parametrize("field,a,b,same", [
    (ho_tich.UNITS[1].fields[0], "34/2013", "34", True),       # số kèm / không kèm năm
    (ho_tich.UNITS[1].fields[0], "34/2013", "43/2013", False),
    (ho_tich.UNITS[1].fields[0], "08/2006", "88/TLKT-BS", True),  # số bản trích lục: mapper lo
    (ho_tich.UNITS[0].fields[0], "UBND xã An Phú", "Ủy ban nhân dân xã An Phú, huyện X, tỉnh Y", True),
    (ho_tich.UNITS[0].fields[0], "UBND xã An Phú", "UBND xã Bình Phú", False),
])
def test_quy_uoc_ho_tich_khong_tinh_la_lech(field, a, b, same):
    ka, kb = compare_key(field, a), compare_key(field, b)
    assert (ka == kb or bool(field.same and field.same(ka, kb))) is same


def _case(values=None, name="TRAN THI B", gender="Nữ", birth="01/02/1990", account=None):
    context = (f"<nguoi_duoc_cap>\nHọ tên: {name}\nNgày sinh: {birth}\nGiới tính: {gender}\n</nguoi_duoc_cap>")
    return Case(DOCS, context, values or {}, {"formContext": account or {
        "applicantFullname": "NGUYEN VAN A", "applicantIdentityNumber": "001090000001"}})


@pytest.mark.parametrize("unit_key,values,rejected", [
    ("so_dinh_danh", {"NguoiDuocCap_SoDinhDanh": "001190000002"}, False),
    ("so_dinh_danh", {"NguoiDuocCap_SoDinhDanh": "001090000001"}, True),   # số của người nộp
    ("so_dinh_danh", {"NguoiDuocCap_SoDinhDanh": "001090000002"}, True),   # số mã hoá Nam, người được cấp Nữ
    ("so_dinh_danh", {"NguoiDuocCap_SoDinhDanh": "001185000002"}, True),   # số mã hoá sinh 1985
    ("so_dinh_danh", {"NguoiDuocCap_SoDinhDanh": "250111222"}, True),      # CMND 9 số
    ("ho_ten", {"NguoiDuocCap_HoTen": "Trần Thị B"}, False),
    ("ho_ten", {"NguoiDuocCap_HoTen": "Lê Thị Cúc"}, True),                # người khác người đã phân vai
])
def test_nhan_than_check(unit_key, values, rejected):
    unit = next(u for u in nhan_than.UNITS if u.key == unit_key)
    assert bool(nhan_than.check(unit, values, _case())) is rejected


def test_mrz_va_tin_hieu_ngay_sinh():
    text = "IDVNM1900000029001190000002<<5\n9002015F3002013VNM<<<<<<<<<<<4\nTRAN<<THI<B<<<<<<<<<<<<<<<<<<<"
    assert mrz_records(text) == [{"id": "001190000002", "birth": (90, 2, 1), "gender": "Nữ", "name": "tran thi b"}]
    case = Case([{"name": "the.jpg", "text": text}], _case().context, {}, {})
    unit = next(u for u in nhan_than.UNITS if u.key == "ngay_sinh")
    assert nhan_than.signals(unit, {"NguoiDuocCap_NgaySinh": "01/02/1990"}, case)[0][0] is True
    assert nhan_than.signals(unit, {"NguoiDuocCap_NgaySinh": "07/02/1990"}, case)[0][0] is False


def test_hai_ben_deu_co_nguyen_van_thi_khong_khoi_to(monkeypatch):
    # Cùng một mô hình đọc ra hai giá trị đều có trên giấy: không có căn cứ bằng mã để thay lượt trích.
    reply = _answer("ho_ten", {"HoTen": "TRẦN THỊ BÌNH"}, "Họ, chữ đệm, tên: TRẦN THỊ BÌNH")
    result, calls = _run(monkeypatch, {"HoTen": "LÊ THỊ CÚC"}, reply, _verdict("B"))
    assert result.values == {"HoTen": "LÊ THỊ CÚC"}
    assert result.rulings[0]["outcome"] == "khong_khoi_to" and "thanh_tra.toa_an" not in calls


@pytest.mark.parametrize("current_ok,expected", [(False, "TRẦN THỊ BÌNH"), (True, "LÊ THỊ CÚC")])
def test_tin_hieu_ma_cua_thu_tuc_quyet_dinh_co_khoi_to(monkeypatch, current_ok, expected):
    def signals(unit, values, case):
        return [(current_ok or values["HoTen"] != "LÊ THỊ CÚC", "tín hiệu thử")]

    inspector = Inspector("nhom", "NHÓM THỬ", (NAME,), "luật", signals=signals, owners=OWNERS, accepted=OWNERS[:1])
    reply = _answer("ho_ten", {"HoTen": "TRẦN THỊ BÌNH"}, "Họ, chữ đệm, tên: TRẦN THỊ BÌNH")
    result, _ = _run(monkeypatch, {"HoTen": "LÊ THỊ CÚC"}, reply, _verdict("B"), (inspector,))
    assert result.values["HoTen"] == expected


# ---- Mỗi thanh tra của trích lục có cách tìm ứng viên riêng ----

_SUBJECT = "<nguoi_duoc_cap>\nHọ tên: TRẦN THỊ BÌNH\nGiới tính: Nữ\n</nguoi_duoc_cap>"


def _page_reply(name):
    return json.dumps(_answer("ho_ten", {"NguoiDuocCap_HoTen": name}, f"Họ, chữ đệm, tên: {name}",
                              "người được cấp"))


@pytest.mark.parametrize("pages,backed", [
    (["TRẦN THỊ BINH", "TRẦN THỊ BÌNH", "TRẦN THỊ BÌNH"], True),   # hai trang in cùng ghi, một trang lệch
    (["TRẦN THỊ BINH", "TRẦN THỊ BÌNH"], False),                    # mỗi bên một nguồn: không đủ căn cứ
])
def test_nhan_than_doc_tung_trang_va_dem_nguon(monkeypatch, pages, backed):
    text = "\n───── Trang 2/3 ─────\n".join(f"Họ, chữ đệm, tên: {name}" for name in pages)
    seen = []

    async def fake_chat(messages, **kwargs):
        user = messages[1]["content"]
        seen.append(user)
        return _page_reply(next(name for name in pages if f"đệm, tên: {name}\n" in user + "\n"))

    monkeypatch.setattr(client, "chat", fake_chat)
    case = Case([{"name": "hs.pdf", "text": text}], _SUBJECT, {"NguoiDuocCap_HoTen": "TRẦN THỊ BINH"}, {})
    findings = asyncio.run(nhan_than.find(nhan_than.INSPECTOR, case, "thử"))
    # Mỗi lượt đọc chỉ thấy đúng một trang.
    assert len(seen) == len(pages) and all(sum(f"đệm, tên: {n}\n" in u + "\n" for n in set(pages)) == 1 for u in seen)
    assert len(findings) == 1 and findings[0].backed is backed
    assert findings[0].values == {"NguoiDuocCap_HoTen": "TRẦN THỊ BÌNH"} if backed else True


def test_nhan_than_bo_trang_khong_nhac_ten_nguoi_duoc_cap(monkeypatch):
    text = "Họ, chữ đệm, tên: TRẦN THỊ BÌNH\n───── Trang 2/2 ─────\nHọ và tên: LÊ THỊ CÚC\nNgày sinh: 05/06/1970"
    calls = []

    async def fake_chat(messages, **kwargs):
        calls.append(messages)
        return "{}"

    monkeypatch.setattr(client, "chat", fake_chat)
    asyncio.run(nhan_than.find(nhan_than.INSPECTOR, Case([{"name": "a", "text": text}], _SUBJECT, {}, {}), "thử"))
    assert len(calls) == 1 and "LÊ THỊ CÚC" in calls[0][1]["content"]  # còn một nguồn → đọc cả hồ sơ như mặc định


def test_ho_tich_cau_hoi_dong_tren_dong_da_chat_loc(monkeypatch):
    seen = []

    async def fake_chat(messages, **kwargs):
        seen.append(messages[1]["content"])
        return json.dumps({"so": {"dong": 2, "value": "12/1990", "thuoc_ve": "giấy hộ tịch cần cấp của người được cấp"},
                           "quyen_so": {"dong": 99, "value": "01"}, "co_quan": None, "ngay_dang_ky": None})

    monkeypatch.setattr(client, "chat", fake_chat)
    findings = asyncio.run(ho_tich.find(ho_tich.INSPECTOR, Case(DOCS, "", {}, {}), "thử"))
    assert "[2] Số: 12/1990" in seen[0] and "LÊ THỊ CÚC" not in seen[0]  # chỉ dòng chắt lọc được gửi đi
    assert [(f.unit.key, f.values, f.quote) for f in findings] == [("so", {"GiayTo_So": "12/1990"}, "Số: 12/1990")]


_ADDRESS_OCR = ("Họ, chữ đệm, tên người mẹ: LÊ THỊ CÚC\nNơi cư trú: Thôn 2, xã Bình Phú, huyện Tân Lập, tỉnh Lâm Đồng\n"
                "CĂN CƯỚC CÔNG DÂN\nHọ và tên: TRẦN THỊ BÌNH\n"
                "Nơi thường trú: Tổ 5, Phường An Phú, Thành phố Tân Lập, Lâm Đồng")
_SPLIT = {"tinh": "Lâm Đồng", "huyen": "Thành phố Tân Lập", "xa": "Phường An Phú", "diaChi": "Tổ 5"}


def _dia_chi_find(monkeypatch, current, reply):
    seen = []

    async def fake_chat(messages, **kwargs):
        seen.append(messages[1]["content"])
        return json.dumps(reply)

    monkeypatch.setattr(client, "chat", fake_chat)
    case = Case([{"name": "hs.pdf", "text": _ADDRESS_OCR}], "", {dia_chi.FIELD: current} if current else {}, {})
    return asyncio.run(dia_chi.find(dia_chi.INSPECTOR, case, "thử")), seen


def _dia_chi_reply(chosen=2, split=_SPLIT, owner2="người được cấp"):
    rows = [{"so": 1, "thuoc_ve": "cha / mẹ của người được cấp", "loai": "nơi cư trú / thường trú"},
            {"so": 2, "thuoc_ve": owner2, "loai": "nơi cư trú / thường trú"}]
    rows[chosen - 1]["tach"] = split
    return {"dong": rows, "chon": chosen}


def test_dia_chi_chi_gui_dong_dia_chi_kem_dong_phia_tren(monkeypatch):
    _, seen = _dia_chi_find(monkeypatch, None, _dia_chi_reply())
    assert "[1] Nơi cư trú: Thôn 2" in seen[0] and "[2] Nơi thường trú: Tổ 5" in seen[0]
    assert "phía trên: Họ, chữ đệm, tên người mẹ: LÊ THỊ CÚC" in seen[0]


@pytest.mark.parametrize("current,faults", [
    # Huyện vào ô xã, xã vào chi tiết.
    ({"tinh": "Lâm Đồng", "xa": "Thành phố Tân Lập", "diaChi": "Tổ 5, An Phú"},
     ["đưa tên cấp huyện vào ô xã", "nhét tên cấp xã vào địa chỉ chi tiết"]),
    # Xã và huyện nằm cả trong chi tiết, ô xã trống.
    ({"tinh": "Lâm Đồng", "xa": "", "diaChi": "Tổ 5, Phường An Phú, TP Tân Lập"},
     ["nhét tên cấp xã vào địa chỉ chi tiết", "nhét tên cấp huyện vào địa chỉ chi tiết", "bỏ trống cấp xã có trên giấy"]),
    # Lấy dòng nơi cư trú của người mẹ.
    ({"tinh": "Lâm Đồng", "xa": "Bình Phú", "diaChi": "Thôn 2"}, ["lấy từ dòng [1] thuộc về cha / mẹ của người được cấp"]),
])
def test_dia_chi_soi_cau_truc_dia_chi_luot_trich(monkeypatch, current, faults):
    findings, _ = _dia_chi_find(monkeypatch, current, _dia_chi_reply())
    assert len(findings) == 1 and findings[0].backed
    assert [e.replace("địa chỉ của A ", "") for e in findings[0].evidence[:-1]] == faults
    assert findings[0].values == {dia_chi.FIELD: _SPLIT}


@pytest.mark.parametrize("current", [
    {"tinh": "Lâm Đồng", "huyen": "Tân Lập", "xa": "An Phú", "diaChi": "Tổ 5"},
    {"tinh": "Lâm Đồng", "xa": "An Phú", "diaChi": "Tổ 5"},   # không giữ cấp huyện: form không có ô huyện, không soát
])
def test_dia_chi_luot_trich_tach_dung_thi_khong_co_can_cu(monkeypatch, current):
    findings, _ = _dia_chi_find(monkeypatch, current, _dia_chi_reply())
    assert findings[0].backed is False
    field = dia_chi.UNITS[0].fields[0]
    assert compare_key(field, current) == compare_key(field, findings[0].values[dia_chi.FIELD])


@pytest.mark.parametrize("split,fault", [
    ({"tinh": "Lâm Đồng", "xa": "An Phú", "diaChi": "Tổ 5, An Phú"}, "chi tiết chứa lại"),
    ({"tinh": "Lâm Đồng", "xa": "Bình An", "diaChi": "Tổ 5"}, "không nằm trên dòng"),
    ({"tinh": "Tổ 5", "xa": "Lâm Đồng"}, "thứ tự"),
    ({"tinh": "Lâm Đồng", "huyen": "Tân Lập", "xa": "Tân Lập", "diaChi": "Tổ 5, An Phú"}, "cả cấp"),
    ({"tinh": "Lâm Đồng", "xa": "Thành phố Tân Lập", "diaChi": "Tổ 5, An Phú"}, "tiền tố cấp huyện"),
])
def test_dia_chi_cach_tach_sai_cau_truc(split, fault):
    # Dòng không ghi tiền tố cấp xã: mã không tự tách được, cách tách của model phải qua kiểm cấu trúc.
    assert fault in dia_chi.split_fault(split, "Nơi thường trú: Tổ 5, An Phú, Thành phố Tân Lập, Lâm Đồng")


def test_dia_chi_dong_co_tien_to_cap_xa_thi_ma_tach_thay_model(monkeypatch):
    wrong = {"tinh": "Lâm Đồng", "huyen": "Phường An Phú", "xa": "Tổ 5"}   # model đẩy lệch cấp
    findings, _ = _dia_chi_find(monkeypatch, None, _dia_chi_reply(split=wrong))
    assert findings[0].values == {dia_chi.FIELD: {"tinh": "Lâm Đồng", "huyen": "Thành phố Tân Lập",
                                                  "xa": "Phường An Phú", "diaChi": "Tổ 5"}}


def test_dia_chi_dong_duoc_chon_thuoc_nguoi_khac_thi_bi_bac_truoc_toa(monkeypatch):
    async def fake_chat(messages, **kwargs):
        if kwargs.get("purpose") == "thanh_tra.dia_chi":
            return json.dumps(_dia_chi_reply(chosen=1, owner2="người yêu cầu / người nộp",
                                             split={"tinh": "Lâm Đồng", "huyen": "Tân Lập", "xa": "Bình Phú",
                                                    "diaChi": "Thôn 2"}))
        return "{}"

    monkeypatch.setattr(client, "chat", fake_chat)
    result = asyncio.run(engine.run(Case([{"name": "hs.pdf", "text": _ADDRESS_OCR}], "", {}, {}),
                                    (dia_chi.INSPECTOR,), title="thử"))
    assert result.values == {} and result.rulings[0]["outcome"] == "bac_truoc_toa"


@pytest.mark.parametrize("raw_values,expected", [
    ({"ho_ten": "TRẦN THỊ BÌNH"}, {"NguoiDuocCap_HoTen": "TRẦN THỊ BÌNH"}),          # lấy khóa mục làm khóa field
    ({"HoTen": "TRẦN THỊ BÌNH"}, {"NguoiDuocCap_HoTen": "TRẦN THỊ BÌNH"}),
    ({"gia_tri": "TRẦN THỊ BÌNH"}, {"NguoiDuocCap_HoTen": "TRẦN THỊ BÌNH"}),
])
def test_khoa_field_model_dat_kieu_nao_cung_doc_duoc(raw_values, expected):
    unit = Unit("ho_ten", "Họ tên", (Field("NguoiDuocCap_HoTen", "họ tên"),))
    assert engine._unit_values(unit, raw_values) == expected


def test_khoa_field_trong_cum_khop_theo_duoi_ten():
    unit = next(u for u in nhan_than.UNITS if u.key == "giay_to_tuy_than")
    raw = {"so_giay_to": "250111222", "NgayCap": "03/04/2005", "noi_cap": "CA Lâm Đồng", "khac": "x"}
    assert engine._unit_values(unit, raw) == {"NguoiDuocCap_SoGiayTo": "250111222",
                                              "NguoiDuocCap_NgayCap": "03/04/2005",
                                              "NguoiDuocCap_NoiCap": "CA Lâm Đồng"}


def test_dia_chi_dong_nam_trong_khoi_nguoi_khac_ten_thi_bac_du_model_khai_la_cua_nguoi_duoc_cap(monkeypatch):
    # Model khai dòng [1] (dưới dòng họ tên người mẹ) là của người được cấp → mã vẫn bác theo tên của khối.
    reply = {"dong": [{"so": 1, "thuoc_ve": "người được cấp", "loai": "nơi cư trú / thường trú",
                       "tach": {"tinh": "tỉnh Lâm Đồng", "huyen": "huyện Tân Lập", "xa": "xã Bình Phú",
                                "diaChi": "Thôn 2"}}], "chon": 1}

    async def fake_chat(messages, **kwargs):
        return json.dumps(reply) if kwargs.get("purpose") == "thanh_tra.dia_chi" else "{}"

    monkeypatch.setattr(client, "chat", fake_chat)
    case = Case([{"name": "hs.pdf", "text": _ADDRESS_OCR}], _SUBJECT, {}, {})
    result = asyncio.run(engine.run(case, (dia_chi.INSPECTOR,), title="thử"))
    assert result.values == {} and result.rulings[0]["outcome"] == "bac_truoc_toa"
    assert "khối của người khác tên" in result.rulings[0]["reason"]


def test_dia_chi_khoi_cua_chinh_nguoi_duoc_cap_thi_qua(monkeypatch):
    findings, _ = _dia_chi_find(monkeypatch, None, _dia_chi_reply())
    case = Case([{"name": "hs.pdf", "text": _ADDRESS_OCR}], _SUBJECT, {}, {})
    assert [line["person"] for line in dia_chi.address_lines(case)] == [
        "Họ, chữ đệm, tên người mẹ: LÊ THỊ CÚC", "Họ và tên: TRẦN THỊ BÌNH"]
    assert findings[0].owner == "người được cấp"


_TWO_SOURCES = ("CĂN CƯỚC CÔNG DÂN\nHọ và tên: TRẦN THỊ BÌNH\n"
                "Nơi thường trú: Tổ 5, An Phú, Tân Lập, Lâm Đồng\n"
                "TỜ KHAI\nHọ, chữ đệm, tên: TRẦN THỊ BÌNH\n"
                "Nơi cư trú: Tổ 5, phường An Phú Mới, tỉnh Lâm Đồng")
_OLD = {"tinh": "Lâm Đồng", "huyen": "Tân Lập", "xa": "An Phú", "diaChi": "Tổ 5"}
_NEW = {"tinh": "tỉnh Lâm Đồng", "xa": "phường An Phú Mới", "diaChi": "Tổ 5"}


@pytest.mark.parametrize("llm_choice", [1, 2])
def test_dia_chi_uu_tien_dong_ba_cap_sau_sap_nhap_hon_dong_con_huyen(monkeypatch, llm_choice):
    reply = {"dong": [{"so": 1, "thuoc_ve": "người được cấp", "loai": "nơi cư trú / thường trú", "tach": _OLD},
                      {"so": 2, "thuoc_ve": "người được cấp", "loai": "nơi cư trú / thường trú", "tach": _NEW}],
             "chon": llm_choice}

    async def fake_chat(messages, **kwargs):
        return json.dumps(reply)

    monkeypatch.setattr(client, "chat", fake_chat)
    # Lượt trích lấy dòng cũ (đủ cả huyện, tách đúng) — vẫn bị đem ra xử vì có dòng ba cấp của chính chủ thể.
    case = Case([{"name": "hs.pdf", "text": _TWO_SOURCES}], _SUBJECT, {dia_chi.FIELD: dict(_OLD)}, {})
    findings = asyncio.run(dia_chi.find(dia_chi.INSPECTOR, case, "thử"))
    assert findings[0].values == {dia_chi.FIELD: _NEW} and findings[0].backed
    assert "ba cấp sau sáp nhập" in findings[0].evidence[0]


def test_dia_chi_luot_trich_da_lay_dong_ba_cap_thi_khong_doi(monkeypatch):
    reply = {"dong": [{"so": 1, "thuoc_ve": "người được cấp", "loai": "nơi cư trú / thường trú", "tach": _OLD},
                      {"so": 2, "thuoc_ve": "người được cấp", "loai": "nơi cư trú / thường trú", "tach": _NEW}],
             "chon": 1}

    async def fake_chat(messages, **kwargs):
        return json.dumps(reply)

    monkeypatch.setattr(client, "chat", fake_chat)
    case = Case([{"name": "hs.pdf", "text": _TWO_SOURCES}], _SUBJECT,
                {dia_chi.FIELD: {"tinh": "Lâm Đồng", "xa": "An Phú Mới", "diaChi": "Tổ 5"}}, {})
    findings = asyncio.run(dia_chi.find(dia_chi.INSPECTOR, case, "thử"))
    assert findings[0].values == {dia_chi.FIELD: _NEW} and findings[0].backed is False


@pytest.mark.parametrize("line,expected", [
    ("Nơi cư trú: Thôn 2, xã Bình Phú, huyện Tân Lập, tỉnh Lâm Đồng",
     {"tinh": "tỉnh Lâm Đồng", "huyen": "huyện Tân Lập", "xa": "xã Bình Phú", "diaChi": "Thôn 2"}),
    ("Thường trú: Số 5 Lê Lợi, Tổ 4, Phường An Phú, Thành phố Lâm Viên",
     {"tinh": "Thành phố Lâm Viên", "xa": "Phường An Phú", "diaChi": "Số 5 Lê Lợi, Tổ 4"}),
    ("Nơi cư trú: (2) Số 5 Lê Lợi, phường An Phú, tỉnh Lâm Đồng. Được cải chính chữ đệm",
     {"tinh": "tỉnh Lâm Đồng", "xa": "phường An Phú", "diaChi": "Số 5 Lê Lợi"}),
    ("Nơi cư trú: xã Bình Phú, huyện Tân Lập", {"huyen": "huyện Tân Lập", "xa": "xã Bình Phú"}),
    ("Nơi thường trú: Tổ 5, An Phú, Tân Lập, Lâm Đồng", None),            # không tiền tố cấp xã → để model tách
    ("Nơi cư trú: xã Bình Phú, Tân Lập, Tây Sơn, Lâm Đồng", None),        # thừa cụm chen giữa → không chắc
    # Dòng dính chữ khác sau tên tỉnh, hoặc hai cột dính một dòng → không chắc.
    ("Nơi cư trú: thôn 2, xã Bình Phú, huyện Tân Lập, tỉnh Lâm Đồng Ghi vào sổ hộ tịch việc khai tử Giấy tờ", None),
    ("Nơi thường trú (2): Khối 5, P. An Phú, Thị xã Tân Lập    Nơi thường trú (2): Bình Phú, Tỉnh Lâm Đồng", None),
])
def test_dia_chi_ma_tach_cap_theo_tien_to_tren_giay(line, expected):
    assert dia_chi.code_split(line) == expected


def test_dia_chi_mot_cum_khong_duoc_dung_cho_hai_cap():
    line = "Thường trú: Số 5 Lê Lợi, Phường An Phú, Thành phố Lâm Viên"
    assert "cả cấp" in dia_chi.split_fault({"tinh": "Lâm Viên", "huyen": "An Phú", "xa": "An Phú"}, line)
    assert "cả cấp" in dia_chi.split_fault({"tinh": "Lâm Viên", "huyen": "Lâm Viên", "xa": "An Phú"}, line)


@pytest.mark.parametrize("line,expected", [
    # Dòng viết liền không dấu phẩy: ngắt trước từng tiền tố cấp, phần trước tiền tố cấp xã giữ nguyên là chi tiết.
    ("Nơi cư trú: (2) Tổ 5 phường An Phú Tỉnh Lâm Đồng",
     {"tinh": "Tỉnh Lâm Đồng", "xa": "phường An Phú", "diaChi": "Tổ 5"}),
    ("Nơi cư trú cuối cùng: Tổ 5 P.An Phú T.Lâm Đồng", {"tinh": "T.Lâm Đồng", "xa": "P.An Phú", "diaChi": "Tổ 5"}),
    ("Nơi cư trú: Thôn 2 xã Bình Phú thị xã Tân Lập tỉnh Lâm Đồng",
     {"tinh": "tỉnh Lâm Đồng", "huyen": "thị xã Tân Lập", "xa": "xã Bình Phú", "diaChi": "Thôn 2"}),
    ("Nơi cư trú: Tổ 5 An Phú Tân Lập Lâm Đồng", None),                    # không tiền tố nào → để model tách
    # Dấu chấm sau chữ viết tắt không phải hết câu.
    ("Nơi cư trú: Tổ 5, P. An Phú, T. Lâm Đồng", {"tinh": "T. Lâm Đồng", "xa": "P. An Phú", "diaChi": "Tổ 5"}),
])
def test_dia_chi_ma_tach_dong_viet_lien_va_chu_viet_tat(line, expected):
    assert dia_chi.code_split(line) == expected


@pytest.mark.parametrize("split,fault", [
    # Hai cụm dùng chung một chữ trên dòng ("Tổ An" + "An Phú") → cắt lệch ranh giới tên.
    ({"tinh": "Lâm Đồng", "huyen": "Tân Lập", "xa": "An Phú", "diaChi": "Tổ An"}, "dùng chung chữ"),
    # Bỏ sót một chữ giữa xã và huyện trên dòng viết liền.
    ({"tinh": "Lâm Đồng", "huyen": "Tân Lập", "xa": "An", "diaChi": "Tổ"}, "chữ giữa các cấp"),
    ({"tinh": "Lâm Đồng", "huyen": "Tân Lập", "xa": "An Phú", "diaChi": "Tổ"}, ""),
])
def test_dia_chi_dong_viet_lien_cac_cum_phai_noi_tiep_khong_chong_chu(split, fault):
    result = dia_chi.split_fault(split, "Nơi cư trú: Tổ An Phú Tân Lập Lâm Đồng")
    assert fault in result if fault else result == ""


def test_dia_chi_o_huyen_mang_tien_to_viet_tat_cap_xa_thi_sai_cau_truc():
    split = {"tinh": "T.Lâm Đồng", "huyen": "P.An Phú", "xa": "Tổ 5"}
    assert "tiền tố cấp xã" in dia_chi.split_fault(split, "Nơi cư trú cuối cùng: Tổ 5 P.An Phú T.Lâm Đồng")


def test_dia_chi_khoi_cha_me_tren_giay_cua_chinh_nguoi_duoc_cap_thi_bac_du_ocr_doc_trung_ten(monkeypatch):
    # OCR đọc tên người mẹ trùng tên người con: cổng theo tên khối không chặn được, cổng theo vai khối phải chặn.
    ocr = ("GIẤY KHAI SINH\nHọ, chữ đệm, tên: TRẦN THỊ BÌNH\nHọ, chữ đệm, tên mẹ: TRẦN THỊ BÌNH\n"
           "Nơi cư trú: Thôn 2, xã Bình Phú, huyện Tân Lập, tỉnh Lâm Đồng")
    reply = {"dong": [{"so": 1, "thuoc_ve": "người được cấp", "loai": "nơi cư trú / thường trú"}], "chon": 1}

    async def fake_chat(messages, **kwargs):
        return json.dumps(reply) if kwargs.get("purpose") == "thanh_tra.dia_chi" else "{}"

    monkeypatch.setattr(client, "chat", fake_chat)
    case = Case([{"name": "ks.pdf", "text": ocr}], _SUBJECT, {}, {})
    result = asyncio.run(engine.run(case, (dia_chi.INSPECTOR,), title="thử"))
    assert result.values == {} and result.rulings[0]["outcome"] == "bac_truoc_toa"
    assert "khối cha / mẹ" in result.rulings[0]["reason"]


def test_dia_chi_dong_hai_cot_dinh_nhau_thi_khong_lam_nguon(monkeypatch):
    # Giấy in hai người cạnh nhau, OCR dồn hai cột vào một dòng: không biết nửa nào của ai → không đề xuất gì.
    ocr = ("Họ và tên chồng: LÊ VĂN DŨNG    Họ và tên vợ: TRẦN THỊ BÌNH\n"
           "Nơi thường trú: Tổ 5, P. An Phú, Thị xã Tân Lập    Nơi thường trú: Bình Phú, Tỉnh Lâm Đồng")
    reply = {"dong": [{"so": 1, "thuoc_ve": "người được cấp", "loai": "nơi cư trú / thường trú",
                       "tach": {"tinh": "Thị xã Tân Lập", "xa": "P. An Phú", "diaChi": "Tổ 5"}}], "chon": 1}

    async def fake_chat(messages, **kwargs):
        return json.dumps(reply)

    monkeypatch.setattr(client, "chat", fake_chat)
    case = Case([{"name": "kh.pdf", "text": ocr}], _SUBJECT, {dia_chi.FIELD: {"tinh": "Lâm Đồng", "diaChi": "Bình Phú"}}, {})
    assert asyncio.run(dia_chi.find(dia_chi.INSPECTOR, case, "thử")) == []


def test_dia_chi_o_tinh_mang_tien_to_cap_huyen_thi_sai_cau_truc():
    split = {"tinh": "Thị xã Tân Lập", "xa": "P. An Phú", "diaChi": "Tổ 5"}
    assert "ô tỉnh" in dia_chi.split_fault(split, "Nơi thường trú: Tổ 5, P. An Phú, Thị xã Tân Lập")


def test_dia_chi_dong_nguon_trong_khoi_dung_ten_thi_khong_coi_la_lay_cua_nguoi_khac():
    # Model khai dòng [1] là của người khác, nhưng dòng nằm ngay dưới dòng họ tên của chính người được cấp.
    lines = [{"text": "Nơi cư trú: Bình Phú An Phú, Lâm Đồng"}, {"text": "Địa chỉ: Tổ 5, P. An Phú, Lâm Đồng"}]
    labels = {1: ("người khác", "nơi cư trú / thường trú"), 2: ("người được cấp", "nơi cư trú / thường trú")}
    current = {"tinh": "Lâm Đồng", "xa": "An Phú", "diaChi": "Bình Phú"}
    best = {"tinh": "Lâm Đồng", "xa": "P. An Phú", "diaChi": "Tổ 5"}
    assert dia_chi.current_faults(current, best, lines, labels, 2, frozenset({1})) == []
    assert dia_chi.current_faults(current, best, lines, labels, 2) == ["lấy từ dòng [1] thuộc về người khác"]
