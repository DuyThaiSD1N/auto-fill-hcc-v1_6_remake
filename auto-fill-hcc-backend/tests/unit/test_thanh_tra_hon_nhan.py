"""Lớp soát thứ hai của thủ tục cấp Giấy XNTTHN: thanh tra định danh nhận người bằng mã và ưu tiên giấy in."""
import asyncio
import json

import pytest

from app.pipelines._shared.thanh_tra.ho_so import Case
from app.pipelines.xac_nhan_tthn_dvc_moi import thanh_tra
from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import dinh_danh
from app.services.llm import client

SUBJECT = {"name": "Lê Thị Hanh", "number": "001185000007", "birth": (5, 3, 1985)}
TO_KHAI = ("TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN\nHọ, chữ đệm, tên người yêu cầu: Trần Văn Em\n"
           "Đề nghị cấp Giấy xác nhận tình trạng hôn nhân cho người có tên dưới đây:\nHọ, chữ đệm, tên: Lê Thị Hanh\n"
           "Ngày, tháng, năm sinh: 05/03/1985\nGiấy tờ tùy thân: 001185000007\nNgười yêu cầu\n(Ký, ghi rõ họ, chữ đệm, tên)\nEm")
THE = ("CĂN CƯỚC CÔNG DÂN\nSố / No.: 001185000007\nHọ và tên / Full name: LÊ THỊ MANH\n"
       "Ngày sinh / Date of birth: 05/03/1985")
KET_HON = ("GIẤY CHỨNG NHẬN KẾT HÔN\nHọ, chữ đệm, tên vợ: LÊ THỊ MANH\nNgày, tháng, năm sinh: 05/03/1985\n"
           "Họ, chữ đệm, tên chồng: PHẠM VĂN GIANG")
VALUES = {"NguoiDuocCap_HoTen": "Lê Thị Hanh", "NguoiDuocCap_SoDinhDanh": "001185000007",
          "NguoiDuocCap_NgaySinh": "05/03/1985", "NguoiDuocCap_SoGiayTo": "001185000007"}
OTHER_ACCOUNT = {"formContext": {"applicantFullname": "Trần Văn Em", "applicantIdentityNumber": "001080000009"}}


def _record(name, number="", birth=None, handwritten=False, text="trang"):
    return {"name": name, "number": number, "birth": birth, "handwritten": handwritten, "text": text, "doc": 1,
            "role": ""}


@pytest.mark.parametrize("record,linked", [
    (_record("LÊ THỊ MANH", "001185000007", (5, 3, 1985)), True),    # trùng số + ngày sinh, tên lệch một chữ
    (_record("LÊ THỊ MANH", "001185000007"), True),                  # trùng đủ số định danh, tên lệch một chữ
    (_record("LÊ THỊ MANH", "", (5, 3, 1985)), True),                # giấy không ghi số: trùng ngày sinh + tên gần
    (_record("LÊ THỊ HANH", "001185000097", (5, 3, 1985)), True),    # số lệch một chữ số, còn lại trùng
    (_record("LÊ THỊ MANH", "", None), False),                       # chỉ có tên gần giống
    (_record("LÊ THỊ MANH", "001190000123", (5, 3, 1985)), False),   # số định danh khác hẳn → người khác
    (_record("PHẠM VĂN GIANG", "001185000007", (5, 3, 1985)), False),
])
def test_nhan_nguoi_bang_hai_trong_ba_thong_tin(record, linked):
    assert bool(dinh_danh._is_subject(record, SUBJECT)) is linked


def test_trang_chup_chung_to_khai_va_the_thi_phan_the_la_chu_in():
    page = TO_KHAI + "\n" + THE
    assert dinh_danh._handwritten("Họ, chữ đệm, tên: Lê Thị Hanh", page) is True
    assert dinh_danh._handwritten("Họ và tên / Full name: LÊ THỊ MANH", page) is False
    assert dinh_danh._handwritten("Họ và tên / Full name: LÊ THỊ MANH", THE) is False


def test_trong_so_nguon_giay_in_hon_to_khai_va_ten_chi_khac_dau_can_hai_nguon():
    hand = _record("Lê Thị Hanh", "001185000007", (5, 3, 1985), handwritten=True, text="tk")
    card = _record("LÊ THỊ MANH", "001185000007", (5, 3, 1985), text="the")
    weights = dinh_danh.weigh([hand, card], SUBJECT, [])
    key = dinh_danh._name_key
    assert weights[dinh_danh.NAME][key("lê thị manh")]["weight"] == 1 and weights[dinh_danh.NAME][key("lê thị hanh")]["weight"] == 0.5
    # Bản án không ghi số / ngày sinh nhưng cùng tên không dấu → vẫn là một nguồn cho cách viết có dấu.
    marked = [_record("LÊ THỊ HẠNH", text="ban an"), _record("Lê Thị Hạnh", text="uy quyen")]
    weights = dinh_danh.weigh([hand, *marked], SUBJECT, [])
    assert weights[dinh_danh.NAME][key("lê thị hạnh")]["weight"] == 2


def test_vi_tri_dat_dau_thanh_khac_nhau_van_la_mot_ten():
    assert dinh_danh._name_key("NGUYỄN THỊ THỦY") == dinh_danh._name_key("Nguyễn Thị Thuỷ")
    assert dinh_danh._name_key("Lê Thị Nga") != dinh_danh._name_key("Lê Thị Ngà")


def _fake_pages(monkeypatch, replies: dict):
    async def fake_chat(messages, **kwargs):
        if kwargs.get("purpose") == "thanh_tra.dinh_danh":
            page = messages[1]["content"]
            return json.dumps({"nguoi": next(people for marker, people in replies.items() if marker in page)})
        return json.dumps({"phan_quyet": []})

    monkeypatch.setattr(client, "chat", fake_chat)


_PEOPLE = {
    "TỜ KHAI": [{"ho_ten": "Lê Thị Hanh", "so_dinh_danh": "001185000007", "ngay_sinh": "05/03/1985",
                 "dong": "Họ, chữ đệm, tên: Lê Thị Hanh"}],
    "CĂN CƯỚC": [{"ho_ten": "LÊ THỊ MANH", "so_dinh_danh": "001185000007", "ngay_sinh": "05/03/1985",
                  "dong": "Họ và tên / Full name: LÊ THỊ MANH"}],
    "KẾT HÔN": [{"ho_ten": "LÊ THỊ MANH", "so_dinh_danh": None, "ngay_sinh": "05/03/1985",
                 "dong": "Họ, chữ đệm, tên vợ: LÊ THỊ MANH"},
                {"ho_ten": "PHẠM VĂN GIANG", "so_dinh_danh": None, "ngay_sinh": None,
                 "dong": "Họ, chữ đệm, tên chồng: PHẠM VĂN GIANG"}],
}


def test_ten_tren_to_khai_lech_giay_in_thi_de_xuat_theo_giay_in(monkeypatch):
    _fake_pages(monkeypatch, _PEOPLE)
    docs = [{"name": "tk.pdf", "text": TO_KHAI}, {"name": "the.pdf", "text": THE}, {"name": "kh.pdf", "text": KET_HON}]
    findings = asyncio.run(dinh_danh.find(dinh_danh.INSPECTOR, Case(docs, "", dict(VALUES), {}), "thử"))
    assert [(f.unit.key, f.values, f.backed) for f in findings] == [
        ("ho_ten", {"NguoiDuocCap_HoTen": "LÊ THỊ MANH"}, True)]
    assert findings[0].quote == "Họ và tên / Full name: LÊ THỊ MANH" and "2 điểm nguồn" in findings[0].evidence[0]


@pytest.mark.parametrize("current,proposed", [
    ("LÊ THỊ HANH", "LÊ THỊ HẠNH"),  # lượt trích theo thẻ, trích lục ghi khác dấu → theo trích lục
    ("LÊ THỊ HẠNH", None),           # lượt trích đã theo trích lục → thẻ không đủ để đổi
])
def test_ngang_diem_thi_giay_co_quan_cap_dung_tren_the_can_cuoc(monkeypatch, current, proposed):
    card = "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001185000007\nHọ và tên / Full name: LÊ THỊ HANH\nNgày sinh: 05/03/1985"
    extract = "TRÍCH LỤC KẾT HÔN\nHọ, chữ đệm, tên vợ: LÊ THỊ HẠNH\nNgày, tháng, năm sinh: 05/03/1985"
    _fake_pages(monkeypatch, {
        "CĂN CƯỚC": [{"ho_ten": "LÊ THỊ HANH", "so_dinh_danh": "001185000007", "ngay_sinh": "05/03/1985",
                      "loai_giay": "can_cuoc", "dong": "Họ và tên / Full name: LÊ THỊ HANH"}],
        "TRÍCH LỤC": [{"ho_ten": "LÊ THỊ HẠNH", "so_dinh_danh": None, "ngay_sinh": "05/03/1985",
                       "loai_giay": "co_quan_cap", "dong": "Họ, chữ đệm, tên vợ: LÊ THỊ HẠNH"}],
    })
    docs = [{"name": "the.pdf", "text": card}, {"name": "tl.pdf", "text": extract}]
    findings = asyncio.run(dinh_danh.find(dinh_danh.INSPECTOR, Case(docs, "", {**VALUES, "NguoiDuocCap_HoTen": current}, {}), "thử"))
    assert [f.values["NguoiDuocCap_HoTen"] for f in findings if f.backed] == ([proposed] if proposed else [])


def test_ngang_diem_ma_de_xuat_chi_la_ban_roi_dau_thi_khong_doi(monkeypatch):
    card = "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001185000007\nHọ và tên / Full name: LÊ THỊ HẠNH\nNgày sinh: 05/03/1985"
    ruling = "QUYẾT ĐỊNH CÔNG NHẬN THUẬN TÌNH LY HÔN\nBà Le Thị Hanh, sinh ngày 05/03/1985"
    _fake_pages(monkeypatch, {
        "CĂN CƯỚC": [{"ho_ten": "LÊ THỊ HẠNH", "so_dinh_danh": "001185000007", "ngay_sinh": "05/03/1985",
                      "loai_giay": "can_cuoc", "dong": "Họ và tên / Full name: LÊ THỊ HẠNH"}],
        "QUYẾT ĐỊNH": [{"ho_ten": "Le Thị Hanh", "so_dinh_danh": None, "ngay_sinh": "05/03/1985",
                        "loai_giay": "co_quan_cap", "dong": "Bà Le Thị Hanh, sinh ngày 05/03/1985"}],
    })
    docs = [{"name": "the.pdf", "text": card}, {"name": "qd.pdf", "text": ruling}]
    case = Case(docs, "", {**VALUES, "NguoiDuocCap_HoTen": "LÊ THỊ HẠNH"}, {})
    findings = asyncio.run(dinh_danh.find(dinh_danh.INSPECTOR, case, "thử"))
    assert [f.backed for f in findings] == [False] and "rơi dấu" in findings[0].evidence[0]


@pytest.mark.parametrize("declared,card_name,backed", [
    ("Lê Thị Hân", "LÊ THỊ HẪN", True),    # thẻ giữ đủ dấu của tờ khai và thêm dấu → một thẻ là đủ
    ("Lê Thị Hẫn", "LÊ THỊ HÂN", False),   # thẻ ít dấu hơn: có thể chính thẻ rơi dấu
    ("Lê Thị Hần", "LÊ THỊ HẪN", False),   # hai bên cùng còn dấu mà khác dấu: một thẻ chưa đủ
])
def test_ten_chi_khac_dau_mot_the_chi_du_khi_the_du_dau_hon_to_khai(monkeypatch, declared, card_name, backed):
    form = TO_KHAI.replace("Lê Thị Hanh", declared)
    card = THE.replace("LÊ THỊ MANH", card_name)
    _fake_pages(monkeypatch, {
        "TỜ KHAI": [{"ho_ten": declared, "so_dinh_danh": "001185000007", "ngay_sinh": "05/03/1985",
                     "loai_giay": "to_khai", "dong": f"Họ, chữ đệm, tên: {declared}"}],
        "CĂN CƯỚC": [{"ho_ten": card_name, "so_dinh_danh": "001185000007", "ngay_sinh": "05/03/1985",
                      "loai_giay": "can_cuoc", "dong": f"Họ và tên / Full name: {card_name}"}],
    })
    docs = [{"name": "tk.pdf", "text": form}, {"name": "the.pdf", "text": card}]
    case = Case(docs, "", {**VALUES, "NguoiDuocCap_HoTen": declared}, {})
    findings = [f for f in asyncio.run(dinh_danh.find(dinh_danh.INSPECTOR, case, "thử")) if f.unit.key == "ho_ten"]
    assert [(f.values["NguoiDuocCap_HoTen"], f.backed) for f in findings] == [(card_name, backed)]
    assert ("B ĐỦ DẤU HƠN A" in findings[0].evidence[0]) is backed


def test_giay_in_du_dau_hon_la_giu_moi_dau_va_them_dau():
    key = dinh_danh._name_key
    assert dinh_danh._adds_marks(key("Trần Văn Cáp"), key("TRẦN VĂN CẤP"))
    assert dinh_danh._adds_marks(key("Dinh Thị Thuy"), key("ĐINH THỊ THUỶ"))
    assert not dinh_danh._adds_marks(key("Lê Thị Hần"), key("Lê Thị Hẫn"))
    assert not dinh_danh._adds_marks(key("Lê Thị Hẫn"), key("Lê Thị Hân"))
    assert not dinh_danh._adds_marks(key("Lê Thị Hân"), key("LÊ THỊ HÂN"))


def test_roi_dau_chi_tinh_khi_chu_tro_han_khong_dau():
    assert dinh_danh._lost_marks("Dinh Thị Lan", "ĐINH THỊ LAN")
    assert not dinh_danh._lost_marks("Lê Thị Hanh", "LÊ THỊ HANH")
    assert not dinh_danh._lost_marks("Trần Văn Cáp", "Trần Văn Cấp")  # cùng còn dấu, khác dấu


def test_chu_d_gach_bi_doc_thanh_d_thi_khong_doi_du_nhieu_diem_hon():
    key = dinh_danh._name_key
    assert dinh_danh._lost_stroke(key("Dinh Thị Lan"), key("ĐINH THỊ LAN"))
    assert not dinh_danh._lost_stroke(key("ĐINH THỊ LAN"), key("Dinh Thị Lan"))
    assert not dinh_danh._lost_stroke(key("Đinh Thị Lân"), key("ĐINH THỊ LAN"))


def test_cach_viet_khong_dau_khong_gop_phieu_cho_chu_tro_dau():
    subject = {**SUBJECT, "name": "ĐỖ THỊ HANH"}
    records = [_record("ĐỖ THỊ HANH", "001185000007", (5, 3, 1985), text="the"),
               _record("Dỗ Thị Hanh", "", (5, 3, 1985), text="qd"),
               _record("DO THI HANH", "001185000007", (5, 3, 1985), text="mat sau")]
    weights = dinh_danh.weigh(records, subject, [])[dinh_danh.NAME]
    key = dinh_danh._name_key
    assert weights[key("Dỗ Thị Hanh")]["weight"] == weights[key("ĐỖ THỊ HANH")]["weight"] == 1


def test_ba_cach_viet_khac_dau_thi_bau_theo_tung_chu():
    # Thẻ sai dấu ở tên, tờ khai sai dấu ở họ, giấy tự lập đúng cả hai → cách viết đúng cả hai chữ nhiều điểm nhất.
    records = [_record("LÊ THỊ HANH", "001185000007", (5, 3, 1985), text="the"),
               _record("LỀ THỊ HẠNH", "001185000007", (5, 3, 1985), handwritten=True, text="tk"),
               _record("Lê Thị Hạnh", "001185000007", (5, 3, 1985), text="uq")]
    weights = dinh_danh.weigh(records, SUBJECT, [])[dinh_danh.NAME]
    key = dinh_danh._name_key
    assert weights[key("Lê Thị Hạnh")]["weight"] == 1.5 and weights[key("LÊ THỊ HANH")]["weight"] == 1
    assert weights[key("LỀ THỊ HẠNH")]["weight"] == 0.5


@pytest.mark.parametrize("number,birth,fits", [
    ("001185000007", (5, 3, 1985), True), ("001115000007", (5, 3, 1985), False),
    ("001205000007", (5, 3, 2005), True), ("001185000007", (5, 3, 2085), False), ("0011850007", (5, 3, 1985), None),
])
def test_ma_nam_sinh_trong_so_dinh_danh(number, birth, fits):
    assert dinh_danh._year_code_fits(number, birth) is fits


def test_so_tren_giay_in_lech_ma_nam_sinh_thi_khong_doi(monkeypatch):
    proxy = "GIẤY ỦY QUYỀN\nÔng (Bà): Lê Thị Hanh, Ngày, tháng, năm sinh: 05/03/1985\nCCCD số 001115000007"
    _fake_pages(monkeypatch, {
        "TỜ KHAI": _PEOPLE["TỜ KHAI"],
        "ỦY QUYỀN": [{"ho_ten": "Lê Thị Hanh", "so_dinh_danh": "001115000007", "ngay_sinh": "05/03/1985",
                      "loai_giay": "tu_lap", "dong": "Ông (Bà): Lê Thị Hanh, Ngày, tháng, năm sinh: 05/03/1985"}],
    })
    docs = [{"name": "tk.pdf", "text": TO_KHAI}, {"name": "uq.pdf", "text": proxy}]
    findings = asyncio.run(dinh_danh.find(dinh_danh.INSPECTOR, Case(docs, "", dict(VALUES), {}), "thử"))
    assert [(f.unit.key, f.backed) for f in findings] == [("so_dinh_danh", False)]
    assert "mã năm sinh" in findings[0].evidence[0]


def test_chi_co_to_khai_thi_khong_de_xuat_gi(monkeypatch):
    _fake_pages(monkeypatch, _PEOPLE)
    case = Case([{"name": "tk.pdf", "text": TO_KHAI}], "", dict(VALUES), {})
    assert asyncio.run(dinh_danh.find(dinh_danh.INSPECTOR, case, "thử")) == []


def test_ban_than_thi_khong_chay_thanh_tra_dinh_danh(monkeypatch):
    calls = []

    async def fake_chat(messages, **kwargs):
        calls.append(kwargs.get("purpose"))
        return "{}"

    monkeypatch.setattr(client, "chat", fake_chat)
    own = {"formContext": {"applicantFullname": "Lê Thị Hanh", "applicantIdentityNumber": "001185000007"}}
    docs = [{"name": "tk.pdf", "text": TO_KHAI}, {"name": "the.pdf", "text": THE}]
    result = asyncio.run(thanh_tra.review(docs, "", dict(VALUES), own))
    assert "thanh_tra.dinh_danh" not in calls and result.values["NguoiDuocCap_HoTen"] == "Lê Thị Hanh"


# ───────── Thanh tra giấy hộ tịch: giấy khai tử, bản án ly hôn ─────────
from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import giay_ho_tich  # noqa: E402

TRICH_LUC_KT = ("UBND XÃ ĐÔNG MAI\nSố: 9/TLKT-BS\nĐông Mai, ngày 7 tháng 5 năm 2022\nTRÍCH LỤC KHAI TỬ\n"
                "Họ, chữ đệm, tên: TRẦN VĂN K\nGiới tính: Nam\n"
                "Đã được đăng ký khai tử tại: UBND xã Đông Mai, huyện Yên Phong, tỉnh Bắc Ninh\n"
                "Số: 12/2020 ngày 3 tháng 4 năm 2020")
# Trích lục không in dòng đăng ký gốc: chỉ có số / ngày / cơ quan ở đầu giấy.
TRICH_LUC_KT_DAU = TRICH_LUC_KT.split("\nĐã được đăng ký khai tử tại")[0]
TO_KHAI_GOA = ("TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN\nHọ, chữ đệm, tên: Lê Thị Hanh\n"
               "Tình trạng hôn nhân: chồng đã chết theo trích lục khai tử số 9/TLKT-BS ngày 07/05/2022")
_GOC = {"viec": "khai_tu", "nguon": "dang_ky_goc", "so": "12/2020", "ngay": "03/04/2020",
        "co_quan": "UBND xã Đông Mai, huyện Yên Phong, tỉnh Bắc Ninh", "nguoi": "TRẦN VĂN K", "gioi_tinh": "Nam",
        "dong": "Số: 12/2020 ngày 3 tháng 4 năm 2020"}
_DAU = {"viec": "khai_tu", "nguon": "dau_giay", "so": "9/TLKT-BS", "ngay": "07/05/2022", "co_quan": "UBND XÃ ĐÔNG MAI",
        "nguoi": "TRẦN VĂN K", "gioi_tinh": "Nam", "dong": "Số: 9/TLKT-BS"}
# Bản CHÍNH trích lục khai tử (số đầu trang không có hậu tố BS): cổng nhận số đăng ký gốc.
TRICH_LUC_KT_CHINH = TRICH_LUC_KT.replace("Số: 9/TLKT-BS", "Số: 9/TLKT")
_DAU_CHINH = {**_DAU, "so": "9/TLKT", "dong": "Số: 9/TLKT"}
_NHAC = {"viec": "khai_tu", "nguon": "nhac_lai", "so": "9/TLKT-BS", "ngay": "07/05/2022", "co_quan": None,
         "nguoi": None, "gioi_tinh": None,
         "dong": "Tình trạng hôn nhân: chồng đã chết theo trích lục khai tử số 9/TLKT-BS ngày 07/05/2022"}


def _fake_sets(monkeypatch, replies: dict):
    async def fake_chat(messages, **kwargs):
        if kwargs.get("purpose") == "thanh_tra.giay_ho_tich":
            page = messages[1]["content"]
            return json.dumps({"bo": next((sets for marker, sets in replies.items() if marker in page), [])})
        return json.dumps({"phan_quyet": []})

    monkeypatch.setattr(client, "chat", fake_chat)


def _papers(values: dict, *texts: str):
    docs = [{"name": f"{i}.pdf", "text": text} for i, text in enumerate(texts)]
    base = {"NguoiDuocCap_HoTen": "Lê Thị Hanh", "NguoiDuocCap_GioiTinh": "Nữ", **values}
    return asyncio.run(giay_ho_tich.find(giay_ho_tich.INSPECTOR, Case(docs, "", base, {}), "thử"))


def test_khai_tu_ban_chinh_luot_trich_lay_so_dau_giay_thi_de_xuat_bo_dang_ky_goc(monkeypatch):
    _fake_sets(monkeypatch, {"TRÍCH LỤC KHAI TỬ": [_GOC, _DAU_CHINH], "TỜ KHAI": [_NHAC]})
    current = {"DeathCert_Number": "9/TLKT", "DeathCert_Date": "07/05/2022", "DeathCert_Agency": "UBND xã Đông Mai"}
    [finding] = _papers(current, TO_KHAI_GOA, TRICH_LUC_KT_CHINH)
    assert finding.backed and finding.quote == "Số: 12/2020 ngày 3 tháng 4 năm 2020"
    assert finding.values == {"DeathCert_Number": "12/2020", "DeathCert_Date": "03/04/2020",
                              "DeathCert_Agency": "UBND xã Đông Mai, huyện Yên Phong, tỉnh Bắc Ninh"}
    assert "bậc thấp hơn" in finding.evidence[0]


def test_khai_tu_so_goc_ghep_ngay_dau_giay_la_so_nay_ngay_kia(monkeypatch):
    _fake_sets(monkeypatch, {"TRÍCH LỤC KHAI TỬ": [_GOC, _DAU_CHINH]})
    current = {"DeathCert_Number": "12/2020", "DeathCert_Date": "07/05/2022",
               "DeathCert_Agency": "UBND xã Đông Mai, huyện Yên Phong, tỉnh Bắc Ninh"}
    [finding] = _papers(current, TRICH_LUC_KT_CHINH)
    assert finding.backed and "số này ngày kia" in finding.evidence[0]
    assert finding.values["DeathCert_Date"] == "03/04/2020"


def test_khai_tu_dong_giay_bao_tu_benh_vien_khong_phai_dong_dang_ky_goc(monkeypatch):
    # Trích lục bản chính không có dòng đăng ký gốc, thân giấy có dòng giấy báo tử của bệnh viện (giấy căn cứ): model gắn
    # nhầm nhãn "dang_ky_goc" thì mã bỏ bộ đó, lượt trích theo đầu giấy được giữ.
    page = TRICH_LUC_KT_DAU + ("\nGiấy báo tử/Giấy tờ thay thế Giấy báo tử số Giấy báo tử số 67, quyển số 01 do Bệnh viện "
                               "Mẫu cấp ngày 20/06/2023")
    bao_tu = {"viec": "khai_tu", "nguon": "dang_ky_goc", "so": "67", "ngay": "20/06/2023", "co_quan": "Bệnh viện Mẫu",
              "nguoi": "TRẦN VĂN K", "gioi_tinh": "Nam", "dong": page.splitlines()[-1]}
    _fake_sets(monkeypatch, {"TRÍCH LỤC KHAI TỬ": [bao_tu, _DAU]})
    current = {"DeathCert_Number": "9/TLKT-BS", "DeathCert_Date": "07/05/2022", "DeathCert_Agency": "Ủy ban nhân dân xã Đông Mai"}
    assert not [f for f in _papers(current, page) if f.values.get("DeathCert_Number") == "67"]
    # Dòng đăng ký gốc thật (số xuống dòng dưới cụm "Đã được đăng ký khai tử tại") vẫn được nhận.
    assert not giay_ho_tich._mislabeled_registration(TRICH_LUC_KT, {"matter": "khai_tu", "source": "dang_ky_goc",
                                                                    "line": "Số: 12/2020 ngày 3 tháng 4 năm 2020"})


def test_khai_tu_khong_co_dong_goc_thi_lay_dau_giay_va_bo_sung_o_trong(monkeypatch):
    _fake_sets(monkeypatch, {"TRÍCH LỤC KHAI TỬ": [_DAU], "TỜ KHAI": [_NHAC]})
    [finding] = _papers({"DeathCert_Number": "9/TLKT-BS"}, TO_KHAI_GOA, TRICH_LUC_KT_DAU)
    assert finding.values == {"DeathCert_Number": "9/TLKT-BS", "DeathCert_Date": "07/05/2022",
                              "DeathCert_Agency": "Ủy ban nhân dân xã Đông Mai"}
    # Chỉ có tờ khai: bộ nhắc lại là nguồn duy nhất.
    _fake_sets(monkeypatch, {"TỜ KHAI": [_NHAC]})
    [finding] = _papers({}, TO_KHAI_GOA)
    assert finding.values == {"DeathCert_Number": "9/TLKT-BS", "DeathCert_Date": "07/05/2022"}


def test_giay_khai_tu_cua_nguoi_cung_gioi_hoac_cua_chinh_nguoi_duoc_cap_thi_bo(monkeypatch):
    _fake_sets(monkeypatch, {"TRÍCH LỤC KHAI TỬ": [{**_GOC, "gioi_tinh": "Nữ"}, {**_DAU, "nguoi": "LÊ THỊ HANH"}]})
    assert _papers({}, TRICH_LUC_KT) == []


def test_ly_hon_uu_tien_van_ban_toa_an_hon_to_khai(monkeypatch):
    ruling = ("TÒA ÁN NHÂN DÂN\nHUYỆN YÊN PHONG\nSố: 15/2019/QĐST-HNGĐ\nYên Phong, ngày 2 tháng 3 năm 2019\n"
              "QUYẾT ĐỊNH CÔNG NHẬN THUẬN TÌNH LY HÔN\nBà Lê Thị Hanh và ông Trần Văn K")
    form = ("TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN\n"
            "Tình trạng hôn nhân: đã ly hôn theo quyết định số 15/2018 ngày 02/03/2018 của TAND huyện Yên Phong")
    _fake_sets(monkeypatch, {
        "QUYẾT ĐỊNH CÔNG NHẬN": [{"viec": "ly_hon", "nguon": "dau_giay", "so": "15/2019/QĐST-HNGĐ", "ngay": "02/03/2019",
                                  "co_quan": "TÒA ÁN NHÂN DÂN HUYỆN YÊN PHONG", "nguoi": "Lê Thị Hanh; Trần Văn K",
                                  "dong": "Số: 15/2019/QĐST-HNGĐ"}],
        "TỜ KHAI": [{"viec": "ly_hon", "nguon": "nhac_lai", "so": "15/2018", "ngay": "02/03/2018",
                     "co_quan": "TAND huyện Yên Phong",
                     "dong": "Tình trạng hôn nhân: đã ly hôn theo quyết định số 15/2018 ngày 02/03/2018 của TAND huyện Yên Phong"}],
    })
    current = {"BanAn_Number": "15/2018", "BanAn_Date": "02/03/2018", "BanAn_Agency": "TAND huyện Yên Phong"}
    [finding] = _papers(current, form, ruling)
    assert finding.backed and finding.values["BanAn_Number"] == "15/2019/QĐST-HNGĐ"
    assert finding.values["BanAn_Date"] == "02/03/2019"


def test_trich_luc_quyet_dinh_thi_lay_van_ban_goc_trong_than(monkeypatch):
    """Trích lục quyết định ly hôn: số / ngày / Tòa án ở đầu là của bản trích lục; dòng thân nêu quyết định gốc."""
    extract = ("TÒA ÁN NHÂN DÂN KHU VỰC 1 – TỈNH MẪU\nSố: 16/TL-TA\nMẫu, ngày 03 tháng 11 năm 2026\nTRÍCH LỤC QUYẾT ĐỊNH\n"
               "Tại Quyết định công nhận thuận tình ly hôn số: 12/2018/QĐST-HNGĐ ngày 24/7/2018, Tòa án nhân dân thành "
               "phố Mẫu đã quyết định: công nhận sự thuận tình ly hôn giữa ông Trần Văn K và bà Lê Thị Hanh")
    _fake_sets(monkeypatch, {
        "TRÍCH LỤC QUYẾT ĐỊNH": [
            {"viec": "ly_hon", "nguon": "dau_giay", "so": "16/TL-TA", "ngay": "03/11/2026",
             "co_quan": "TÒA ÁN NHÂN DÂN KHU VỰC 1 – TỈNH MẪU", "nguoi": "Trần Văn K; Lê Thị Hanh", "dong": "Số: 16/TL-TA"},
            {"viec": "ly_hon", "nguon": "dang_ky_goc", "so": "12/2018/QĐST-HNGĐ", "ngay": "24/07/2018",
             "co_quan": "Tòa án nhân dân thành phố Mẫu", "nguoi": "Trần Văn K; Lê Thị Hanh",
             "dong": "Tại Quyết định công nhận thuận tình ly hôn số: 12/2018/QĐST-HNGĐ ngày 24/7/2018, Tòa án nhân dân thành "
                     "phố Mẫu đã quyết định: công nhận sự thuận tình ly hôn giữa ông Trần Văn K và bà Lê Thị Hanh"}],
    })
    current = {"BanAn_Number": "16/TL-TA", "BanAn_Date": "03/11/2026", "BanAn_Agency": "Tòa án nhân dân khu vực 1 – tỉnh Mẫu"}
    [finding] = _papers(current, extract)
    assert finding.backed
    assert (finding.values["BanAn_Number"], finding.values["BanAn_Date"], finding.values["BanAn_Agency"]) == (
        "12/2018/QĐST-HNGĐ", "24/07/2018", "Tòa án nhân dân thành phố Mẫu")


def test_review_soat_cum_ly_hon_tren_gia_tri_se_duoc_dien(monkeypatch):
    seen = {}

    async def fake_run(case, inspectors, *, title):
        seen["values"], seen["keys"] = dict(case.values), [i.key for i in inspectors]
        return thanh_tra.Result(dict(case.values), [], {})

    monkeypatch.setattr(thanh_tra.engine, "run", fake_run)
    values = {**VALUES, "DivorceDecision_Number": "15/2018", "BanAn_Date": "02/03/2019"}
    asyncio.run(thanh_tra.review([], "", values, OTHER_ACCOUNT))
    assert seen["values"]["BanAn_Number"] == "15/2018" and seen["values"]["BanAn_Date"] == "02/03/2019"
    assert seen["keys"] == ["giay_ho_tich", "sdt_nguoi_nop", "dinh_danh", "dia_chi"]


def test_co_quan_chi_doi_khi_chep_tu_dong_goc_hoac_ghi_du_cap_hon(monkeypatch):
    _fake_sets(monkeypatch, {"TRÍCH LỤC KHAI TỬ": [_DAU]})
    # Cùng số, cùng ngày; đầu giấy in hoa không ghi đủ cấp bằng lượt trích → giữ cơ quan lượt trích, không thành vụ.
    same = {"DeathCert_Number": "9/TLKT-BS", "DeathCert_Date": "07/05/2022",
            "DeathCert_Agency": "Ủy ban nhân dân xã Đông Mai, huyện Yên Phong"}
    [finding] = _papers(same, TRICH_LUC_KT_DAU)
    assert finding.values["DeathCert_Agency"] == same["DeathCert_Agency"] and not finding.backed
    # Lượt trích chép cụt cơ quan → lấy cơ quan ghi đủ hơn ở đầu giấy, viết lại chữ in hoa.
    cut = {**same, "DeathCert_Agency": "Ủy ban nhân dân"}
    [finding] = _papers(cut, TRICH_LUC_KT_DAU)
    assert finding.values["DeathCert_Agency"] == "Ủy ban nhân dân xã Đông Mai" and finding.backed


@pytest.mark.parametrize("raw,tidy", [
    ("UBND PHƯỜNG NAM SƠN", "Ủy ban nhân dân phường Nam Sơn"),
    ("TÒA ÁN NHÂN DÂN HUYỆN YÊN PHONG TỈNH BẮC NINH", "Tòa án nhân dân huyện Yên Phong tỉnh Bắc Ninh"),
    ("UBND xã Đông Mai, huyện Yên Phong", "UBND xã Đông Mai, huyện Yên Phong"),
])
def test_co_quan_in_hoa_o_dau_giay_duoc_viet_lai_chu_thuong(raw, tidy):
    assert giay_ho_tich._tidy_agency(raw) == tidy


def test_ngay_model_tra_khong_co_tren_trang_thi_bo_ngay_do(monkeypatch):
    _fake_sets(monkeypatch, {"TRÍCH LỤC KHAI TỬ": [{**_DAU, "ngay": "01/01/1900"}]})
    current = {"DeathCert_Number": "9/TLKT-BS", "DeathCert_Date": "07/05/2022", "DeathCert_Agency": "UBND xã Đông Mai"}
    [finding] = _papers(current, TRICH_LUC_KT_DAU)
    assert finding.values["DeathCert_Date"] == "07/05/2022" and not finding.backed


def test_ly_hon_luot_trich_lay_so_thu_ly_thi_co_can_cu_doi_theo_dau_van_ban(monkeypatch):
    ruling = ("TÒA ÁN NHÂN DÂN\nHUYỆN YÊN PHONG\nSố: 15/2019/QĐST-HNGĐ\nYên Phong, ngày 2 tháng 3 năm 2019\n"
              "QUYẾT ĐỊNH CÔNG NHẬN THUẬN TÌNH LY HÔN\nThụ lý số 298\nBà Lê Thị Hanh và ông Trần Văn K")
    _fake_sets(monkeypatch, {"QUYẾT ĐỊNH CÔNG NHẬN": [
        {"viec": "ly_hon", "nguon": "dau_giay", "so": "15/2019/QĐST-HNGĐ", "ngay": "02/03/2019",
         "co_quan": "TÒA ÁN NHÂN DÂN HUYỆN YÊN PHONG", "nguoi": "Lê Thị Hanh; Trần Văn K", "dong": "Số: 15/2019/QĐST-HNGĐ"}]})
    [finding] = _papers({"BanAn_Number": "298", "BanAn_Date": "02/03/2019"}, ruling)
    assert finding.backed and "thụ lý" in finding.evidence[0] and finding.values["BanAn_Number"] == "15/2019/QĐST-HNGĐ"


def test_model_doc_sot_dong_dang_ky_goc_thi_ma_bo_sung_bo_do(monkeypatch):
    _fake_sets(monkeypatch, {"TRÍCH LỤC KHAI TỬ": [_DAU_CHINH]})
    current = {"DeathCert_Number": "9/TLKT", "DeathCert_Date": "07/05/2022", "DeathCert_Agency": "UBND xã Đông Mai"}
    [finding] = _papers(current, TRICH_LUC_KT_CHINH)
    assert finding.backed and finding.values["DeathCert_Number"] == "12/2020"
    assert finding.values["DeathCert_Date"] == "03/04/2020" and finding.quote == "Số: 12/2020 ngày 3 tháng 4 năm 2020"



def test_khai_tu_ban_sao_trich_luc_lay_so_dau_ban_sao():
    # Người dân nộp BẢN SAO trích lục: cổng nhận số -BS, ngày cấp, cơ quan cấp ở đầu bản sao.
    assert giay_ho_tich._death_kind(TRICH_LUC_KT) == "ban_sao"
    assert giay_ho_tich._death_kind(TRICH_LUC_KT_CHINH) == "ban_chinh"
    assert giay_ho_tich._death_kind(TRICH_LUC_KT_CHINH.replace("TRÍCH LỤC KHAI TỬ", "TRÍCH LỤC KHAI TỬ\n(BẢN SAO)")) == "ban_sao"


def test_khai_tu_ban_sao_luot_trich_lay_so_goc_thi_de_xuat_so_ban_sao(monkeypatch):
    _fake_sets(monkeypatch, {"TRÍCH LỤC KHAI TỬ": [_GOC, _DAU]})
    current = {"DeathCert_Number": "12/2020", "DeathCert_Date": "03/04/2020", "DeathCert_Agency": "UBND xã Đông Mai"}
    [finding] = _papers(current, TRICH_LUC_KT)
    assert finding.backed and finding.quote == "Số: 9/TLKT-BS"
    assert finding.values["DeathCert_Number"] == "9/TLKT-BS" and finding.values["DeathCert_Date"] == "07/05/2022"
    # Lượt trích đã lấy đúng số bản sao → không đổi sang số gốc.
    same = {"DeathCert_Number": "9/TLKT-BS", "DeathCert_Date": "07/05/2022", "DeathCert_Agency": "UBND xã Đông Mai"}
    assert all(not f.backed for f in _papers(same, TRICH_LUC_KT))


def test_khai_tu_co_ca_ban_chinh_lan_ban_sao_thi_theo_ban_chinh(monkeypatch):
    _fake_sets(monkeypatch, {"TLKT-BS": [_DAU], "Số: 9/TLKT\n": [_GOC, _DAU_CHINH]})
    current = {"DeathCert_Number": "9/TLKT-BS", "DeathCert_Date": "07/05/2022", "DeathCert_Agency": "UBND xã Đông Mai"}
    [finding] = _papers(current, TRICH_LUC_KT, TRICH_LUC_KT_CHINH)
    assert finding.backed and finding.values["DeathCert_Number"] == "12/2020"


# ───────── Thanh tra địa chỉ ─────────
from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import dia_chi  # noqa: E402

_CONTEXT = "<phan_vai_da_xac_dinh>\n<nguoi_duoc_cap>\nHọ tên: Lê Thị Hanh\n</nguoi_duoc_cap>\n</phan_vai_da_xac_dinh>"
_RESIDENCE = "nơi cư trú / thường trú"
# Danh mục giả: xã "hiện hành" là Đông Mai, Yên Trung; xã cũ "Đông Thọ" (huyện Yên Phong) đã nhập vào Đông Mai.
_CURRENT_WARDS = {"dong mai": "Xã Đông Mai", "yen trung": "Xã Yên Trung"}
_OLD_WARDS = {"dong tho": "Xã Đông Mai"}


def _fake_area(value, ocr_text=""):
    key = dia_chi.base._bare(value.get("xa"))
    ward = _CURRENT_WARDS.get(key) or _OLD_WARDS.get(key)
    return {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": ward or str(value.get("xa") or ""),
            "diaChi": str(value.get("diaChi") or ""), **({} if ward else {"_xaChuaChon": True})}


def _fake_catalog(split):
    area = _fake_area(split)
    return None if area.get("_xaChuaChon") else area


def _address(monkeypatch, current, text, labels, options=None):
    """labels: {số dòng: (thuộc về, tách hoặc None)} — câu trả lời giả của model cho từng dòng địa chỉ."""
    reply = {"dong": [{"so": n, "thuoc_ve": owner, "loai": _RESIDENCE, **({"tach": split} if split else {})}
                      for n, (owner, split) in labels.items()], "chon": None}

    async def fake_chat(messages, **kwargs):
        return json.dumps(reply)

    monkeypatch.setattr(client, "chat", fake_chat)
    monkeypatch.setattr(dia_chi.mapper, "_area", _fake_area)
    monkeypatch.setattr(dia_chi, "_in_catalog", _fake_catalog)
    case = Case([{"name": "hs.pdf", "text": text}], _CONTEXT, {dia_chi.FIELD: current} if current else {}, options or {})
    return asyncio.run(dia_chi.find(dia_chi.INSPECTOR, case, "thử"))


_KHAI = ("TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN\n"
         "Đề nghị cấp Giấy xác nhận tình trạng hôn nhân cho người có tên dưới đây:\n"
         "Họ, chữ đệm, tên: Lê Thị Hanh\nNơi cư trú: {dia_chi}\nGiấy tờ tùy thân: CCCD số 001185000007\n"
         "Người yêu cầu\n(Ký, ghi rõ họ, chữ đệm, tên)\nHanh")
_THE = ("\n───── Trang 2/2 ─────\nCĂN CƯỚC CÔNG DÂN\nHọ và tên / Full name: LÊ THỊ HANH\n"
        "Nơi thường trú / Place of residence: {dong_tren}\n{dong_duoi}")
_OWN = "người được cấp"


def test_dia_chi_uu_tien_dong_ba_cap_nhung_chi_tiet_lay_cach_viet_cua_dong_in(monkeypatch):
    # Tờ khai (viết tay, ba cấp mới) đọc lệch số nhà; thẻ (in, địa chỉ cũ cùng xã mới) ghi rõ → xã theo tờ khai,
    # chi tiết theo thẻ.
    text = _KHAI.format(dia_chi="5T Cao Thắng, xã Đông Mai, tỉnh Bắc Ninh") + _THE.format(
        dong_tren="57 Cao Thắng", dong_duoi="Đông Thọ, Yên Phong, Bắc Ninh")
    current = {"tinh": "Bắc Ninh", "xa": "Đông Thọ", "diaChi": "5T Cao Thắng"}
    [finding] = _address(monkeypatch, current, text, {1: (_OWN, None), 2: (_OWN, None)})
    assert finding.values[dia_chi.FIELD] == {"tinh": "tỉnh Bắc Ninh", "xa": "xã Đông Mai", "diaChi": "57 Cao Thắng"}
    assert finding.backed and "dòng in [2]" in " ".join(finding.evidence)


def test_dia_chi_luot_trich_da_dung_thi_khong_de_xuat(monkeypatch):
    text = _KHAI.format(dia_chi="5T Cao Thắng, xã Đông Mai, tỉnh Bắc Ninh") + _THE.format(
        dong_tren="57 Cao Thắng", dong_duoi="Đông Thọ, Yên Phong, Bắc Ninh")
    current = {"tinh": "Bắc Ninh", "xa": "Đông Mai", "diaChi": "Số nhà 57, đường Cao Thắng"}
    assert _address(monkeypatch, current, text, {1: (_OWN, None), 2: (_OWN, None)}) == []


def test_dia_chi_chi_tiet_khac_han_thi_theo_dong_sau_sap_nhap_khi_co_tu_hai_dong(monkeypatch):
    khai = _KHAI.format(dia_chi="TDP Quyết Tiến, xã Đông Mai, tỉnh Bắc Ninh")
    # Người yêu cầu cũng là người được cấp: khối người yêu cầu ghi cùng địa chỉ → chi tiết mới có ở hai dòng.
    requester = ("Họ, chữ đệm, tên người yêu cầu: Lê Thị Hanh\nNơi cư trú: TDP Quyết Tiến, xã Đông Mai, tỉnh Bắc Ninh\n"
                 "Giấy tờ tùy thân: CCCD\n")
    text = requester + khai + _THE.format(
        dong_tren="Thôn Quyết Tiến", dong_duoi="Đông Thọ, Yên Phong, Bắc Ninh")
    current = {"tinh": "Bắc Ninh", "xa": "Đông Mai", "diaChi": "Thôn Quyết Tiến"}
    labels = {1: (_OWN, None), 2: (_OWN, None), 3: (_OWN, None)}
    [finding] = _address(monkeypatch, current, text, labels)
    assert finding.values[dia_chi.FIELD]["diaChi"] == "TDP Quyết Tiến" and finding.backed
    # Chỉ MỘT dòng viết tay ghi chi tiết mới, thẻ in cùng tên → giữ cách viết của thẻ (đang là giá trị lượt trích).
    single = khai + _THE.format(dong_tren="Thôn Quyết Tiến", dong_duoi="Đông Thọ, Yên Phong, Bắc Ninh")
    assert _address(monkeypatch, current, single, {1: (_OWN, None), 2: (_OWN, None)}) == []
    [finding] = _address(monkeypatch, {**current, "diaChi": "Thôn Quyết Tiên Đông Thọ"}, single, {1: (_OWN, None), 2: (_OWN, None)})
    assert finding.values[dia_chi.FIELD]["diaChi"] == "Thôn Quyết Tiến" and "dòng in [2]" in " ".join(finding.evidence)


def test_dia_chi_dong_the_khong_ghi_tien_to_thi_tach_bang_danh_muc(monkeypatch):
    monkeypatch.setattr(dia_chi.mapper, "_area", _fake_area)
    monkeypatch.setattr(dia_chi, "_in_catalog", _fake_catalog)
    # Xã cũ viết liền sau chi tiết, tên huyện cũ nay là tên xã mới: gỡ xã cũ ra khỏi chi tiết.
    glued = {"line": "Nơi thường trú / Place of residence: 50 Lý Tự Trọng", "doc": 1,
             "text": "Nơi thường trú / Place of residence: 50 Lý Tự Trọng Tổ 21 Đông Thọ, Đông Mai, Bắc Ninh"}
    assert dia_chi.catalog_split(glued, Case([], "", {}, {})) == {
        "tinh": "Bắc Ninh", "huyen": "Đông Mai", "xa": "Đông Thọ", "diaChi": "50 Lý Tự Trọng, Tổ 21"}
    item = {"line": "Nơi thường trú / Place of residence: Thôn Hạ", "doc": 1,
            "text": "Nơi thường trú / Place of residence: Thôn Hạ Đông Thọ, Yên Phong, Bắc Ninh"}
    assert dia_chi.catalog_split(item, Case([], "", {}, {})) == {"tinh": "Bắc Ninh", "huyen": "Yên Phong", "xa": "Đông Thọ", "diaChi": "Thôn Hạ"}
    # Lượt trích dính xã cũ vào chi tiết và đưa huyện vào ô xã → đề xuất theo cách tách của danh mục.
    text = _KHAI.format(dia_chi="").replace("Nơi cư trú: \n", "") + _THE.format(
        dong_tren="Thôn Hạ", dong_duoi="Đông Thọ, Yên Phong, Bắc Ninh")
    current = {"tinh": "Bắc Ninh", "xa": "Yên Phong", "diaChi": "Thôn Hạ Đông Thọ"}
    [finding] = _address(monkeypatch, current, text, {1: (_OWN, None)})
    assert finding.values[dia_chi.FIELD]["xa"] == "Đông Thọ" and finding.values[dia_chi.FIELD]["diaChi"] == "Thôn Hạ"


def test_dia_chi_ten_xa_doc_lech_gan_trung_xa_cua_quay_thi_sua_theo_quay(monkeypatch):
    monkeypatch.setattr(dia_chi.area_remap, "canonical_ward", lambda tinh, xa: "Xã Đông Mai" if "Đông Mai" in xa else None)
    text = _KHAI.format(dia_chi="Thôn Đông, xã Đông Mal, tỉnh Bắc Ninh")
    current = {"tinh": "Bắc Ninh", "xa": "Đông Mal", "diaChi": "Thôn Đông"}
    assert _address(monkeypatch, current, text, {1: (_OWN, None)}) == []           # không có gợi ý: xã không chọn được
    [finding] = _address(monkeypatch, current, text, {1: (_OWN, None)}, {"counterWard": "HCC Xã Đông Mai"})
    assert finding.values[dia_chi.FIELD]["xa"] == "Xã Đông Mai" and "xã của quầy" in " ".join(finding.evidence)


def test_dia_chi_dong_cua_nguoi_khac_va_dia_chi_nuoc_ngoai_thi_khong_dung(monkeypatch):
    # Khối người yêu cầu mang tên NGƯỜI KHÁC: địa chỉ ở đó không phải của người được cấp, dù model gắn nhãn gì.
    other = ("Họ, chữ đệm, tên người yêu cầu: Trần Văn Em\nNơi cư trú: Thôn Đông, xã Đông Mai, tỉnh Bắc Ninh\n"
             "Giấy tờ tùy thân: CCCD\n")
    current = {"tinh": "Bắc Ninh", "xa": "Yên Trung", "diaChi": "Thôn Hạ"}
    assert _address(monkeypatch, current, other, {1: (_OWN, None)}) == []
    text = _KHAI.format(dia_chi="Thôn Đông, xã Đông Mai, tỉnh Bắc Ninh")
    assert _address(monkeypatch, {"quocGia": "Hàn Quốc", "diaChi": "Seoul"}, text, {1: (_OWN, None)}) == []


def test_khoi_nguoi_yeu_cau_mang_dung_ten_nguoi_duoc_cap_cung_la_dong_cua_ho(monkeypatch):
    requester = ("Họ, chữ đệm, tên người yêu cầu: Lê Thị Hanh\nNơi cư trú: Thôn Đông, xã Đông Mai, tỉnh Bắc Ninh\n"
                 "Giấy tờ tùy thân: CCCD\n")
    current = {"tinh": "Bắc Ninh", "xa": "Yên Trung", "diaChi": "Thôn Hạ"}
    [finding] = _address(monkeypatch, current, requester, {1: ("người yêu cầu / người nộp", None)})
    assert finding.owner == "người được cấp" and finding.values[dia_chi.FIELD]["xa"] == "xã Đông Mai"


def _screened(current, proposed, evidence=("địa chỉ của A lấy dòng [1] ghi địa chỉ cũ, trong khi người được cấp có dòng [2] ghi ba cấp sau sáp nhập",)):
    case = Case([], _CONTEXT, {dia_chi.FIELD: current}, {})
    finding = thanh_tra.engine.Finding(dia_chi.INSPECTOR, dia_chi.base.UNITS[0], {dia_chi.FIELD: proposed}, "dòng", 1,
                                       backed=True, evidence=evidence)
    return dia_chi.screen(finding, case)


def test_de_xuat_dia_chi_lam_mat_o_xa_doi_tinh_hoac_bo_chi_tiet_that_thi_bo(monkeypatch):
    monkeypatch.setattr(dia_chi.mapper, "_area", lambda value, ocr_text="": {**value, "_xaChuaChon": value.get("xa") == "Không Có"})
    current = {"tinh": "Bắc Ninh", "xa": "Đông Mai", "diaChi": "Thôn Đông"}
    assert _screened(current, {"tinh": "Bắc Ninh", "xa": "Không Có", "diaChi": "Thôn Đông"}) is None
    assert _screened(current, {"tinh": "Hà Nội", "xa": "Yên Sở"}) is None
    assert _screened(current, {"tinh": "Bắc Ninh", "xa": "Đông Mai"}) is None                         # mất chi tiết thật
    assert _screened({**current, "diaChi": "Đông Mai"}, {"tinh": "Bắc Ninh", "xa": "Đông Mai"}) is not None  # chi tiết toàn tên xã
    kept = _screened(current, {"tinh": "Bắc Ninh", "xa": "Yên Trung", "diaChi": "Thôn Hạ"})
    assert kept is not None and kept.backed


def test_chi_tiet_chi_la_chu_chi_cap_thi_bo_va_so_co_so_khong_dung_dau_la_mot():
    assert dia_chi._clean_detail("Phường") == "" and dia_chi._clean_detail("Thôn") == ""
    assert dia_chi._clean_detail("TDP.....Hựu....") == "TDP Hựu"
    assert dia_chi._detail_key("Thôn 01") == dia_chi._detail_key("thôn 1")
    assert dia_chi._detail_key("Số nhà 57, đường Cao Thắng") == dia_chi._detail_key("57 Cao Thắng")


def test_dong_dia_chi_khong_nam_trong_khoi_cua_nguoi_duoc_cap_thi_khong_dung(monkeypatch):
    # Dòng "Địa chỉ" đứng đầu một tờ giấy, phía trên không có dòng họ tên của người được cấp.
    text = "ĐƠN ĐỀ NGHỊ\nĐịa chỉ: TDP Mới, xã Yên Trung, tỉnh Bắc Ninh\nKính gửi: UBND xã"
    current = {"tinh": "Bắc Ninh", "xa": "Đông Mai", "diaChi": "Thôn Đông"}
    assert _address(monkeypatch, current, text, {1: (_OWN, None)}) == []


def test_chi_tiet_bo_chu_chi_cap_sot_o_cuoi():
    assert dia_chi._clean_detail("Tổ 50 Chung cư 8 Phường") == "Tổ 50 Chung cư 8"
    assert dia_chi._clean_detail("Chương Xá, P") == "Chương Xá"


def test_dia_chi_dong_ba_cap_tren_to_khai_dung_truoc_giay_cu_cung_ba_cap(monkeypatch):
    # Tờ khai lần này khai một tổ dân phố, Giấy XNTTHN cũ (đánh máy) ghi tổ dân phố khác cùng xã → theo tờ khai.
    old_paper = ("\n───── Trang 2/2 ─────\nGIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN\nHọ, chữ đệm, tên: LÊ THỊ HANH\n"
                 "Nơi cư trú: TDP An Thịnh, xã Đông Mai, tỉnh Bắc Ninh\nGiấy tờ tùy thân: CCCD")
    requester = ("Họ, chữ đệm, tên người yêu cầu: Lê Thị Hanh\nNơi cư trú: TDP Bình An, xã Đông Mai, tỉnh Bắc Ninh\n"
                 "Giấy tờ tùy thân: CCCD\n")
    text = requester + _KHAI.format(dia_chi="TDP Bình An, xã Đông Mai, tỉnh Bắc Ninh") + old_paper
    current = {"tinh": "Bắc Ninh", "xa": "Đông Mai", "diaChi": "TDP Bình An"}
    assert _address(monkeypatch, current, text, {1: (_OWN, None), 2: (_OWN, None), 3: (_OWN, None)}) == []
    [finding] = _address(monkeypatch, {**current, "diaChi": "TDP An Thịnh"}, text, {1: (_OWN, None), 2: (_OWN, None), 3: (_OWN, None)})
    assert finding.values[dia_chi.FIELD]["diaChi"] == "TDP Bình An"


_TO_KHAI_DAN_TOC = TO_KHAI.replace("Ngày, tháng, năm sinh: 05/03/1985\n",
                                   "Ngày, tháng, năm sinh: 05/03/1985\nGiới tính: (2) Nữ Dân tộc: (2) Kinh\n"
                                   "Tình trạng hôn nhân: đã ly hôn với Phạm Văn Giang, Dân tộc: Tày\n")
_PEOPLE_DAN_TOC = {"TỜ KHAI": [
    {"ho_ten": "Lê Thị Hanh", "so_dinh_danh": "001185000007", "ngay_sinh": "05/03/1985", "dan_toc": "(2) Kinh",
     "dong": "Họ, chữ đệm, tên: Lê Thị Hanh"},
    {"ho_ten": "Phạm Văn Giang", "so_dinh_danh": None, "ngay_sinh": None, "dan_toc": "Tày",
     "dong": "Tình trạng hôn nhân: đã ly hôn với Phạm Văn Giang, Dân tộc: Tày"}]}


@pytest.mark.parametrize("values,expected", [
    (dict(VALUES), [{"NguoiDuocCap_DanToc": "Kinh"}]),                      # lượt trích bỏ trống → bổ sung từ tờ khai
    ({**VALUES, "NguoiDuocCap_DanToc": "Kinh"}, []),                      # đã có thì không soát lại
    ({**VALUES, "GiayToKhac_DanToc": "Kinh"}, []),
])
def test_thieu_dan_toc_thi_bo_sung_theo_dong_cua_chinh_nguoi_duoc_cap(monkeypatch, values, expected):
    _fake_pages(monkeypatch, _PEOPLE_DAN_TOC)
    docs = [{"name": "tk.pdf", "text": _TO_KHAI_DAN_TOC}]
    findings = [f for f in asyncio.run(dinh_danh.find(dinh_danh.INSPECTOR, Case(docs, "", values, {}), "thử"))
                if f.unit.key == "dan_toc"]
    assert [f.values for f in findings] == expected
    if findings:
        assert findings[0].quote == "Giới tính: (2) Nữ Dân tộc: (2) Kinh" and findings[0].backed


def test_dan_toc_chi_cua_nguoi_khac_thi_khong_bo_sung(monkeypatch):
    _fake_pages(monkeypatch, {"TỜ KHAI": [{**_PEOPLE_DAN_TOC["TỜ KHAI"][0], "dan_toc": None},
                                          _PEOPLE_DAN_TOC["TỜ KHAI"][1]]})
    docs = [{"name": "tk.pdf", "text": _TO_KHAI_DAN_TOC}]
    findings = asyncio.run(dinh_danh.find(dinh_danh.INSPECTOR, Case(docs, "", dict(VALUES), {}), "thử"))
    assert not [f for f in findings if f.unit.key == "dan_toc"]


def test_khai_tu_don_vi_cau_hinh_ban_sao_van_lay_so_goc(monkeypatch):
    from app.pipelines.xac_nhan_tthn_dvc_moi.process import mapper as tthn_mapper

    _fake_sets(monkeypatch, {"TRÍCH LỤC KHAI TỬ": [_GOC, _DAU]})
    current = {"DeathCert_Number": "9/TLKT-BS", "DeathCert_Date": "07/05/2022", "DeathCert_Agency": "UBND xã Đông Mai"}
    base = {"NguoiDuocCap_HoTen": "Lê Thị Hanh", "NguoiDuocCap_GioiTinh": "Nữ", **current}
    options = tthn_mapper.with_account_process_options({}, {"tinh": "Tỉnh Quảng Trị", "xa": "Phường Đồng Thuận"},
                                                       tthn_mapper.PROCEDURE_KEY)
    docs = [{"name": "0.pdf", "text": TRICH_LUC_KT}]
    [finding] = asyncio.run(giay_ho_tich.find(giay_ho_tich.INSPECTOR, Case(docs, "", base, options), "thử"))
    assert finding.backed and finding.values["DeathCert_Number"] == "12/2020"
    assert "cấu hình đơn vị" in finding.evidence[0]
    # Đơn vị khác (client tự gửi cờ) không được bật.
    assert tthn_mapper.with_account_process_options({"deathOriginalNumber": True}, {"tinh": "Tỉnh Lâm Đồng", "xa": "Xã A"},
                                                    tthn_mapper.PROCEDURE_KEY) == {}


def test_ho_ten_trang_tu_mau_thuan_khong_lam_nguon_cho_cach_viet_khac():
    from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import dinh_danh as tthn_dinh_danh

    # Giấy ủy quyền đánh máy một cách viết, nhưng dòng chữ ký trên CHÍNH trang đó ghi cách viết của lượt trích hai lần.
    uy_quyen = "GIẤY ỦY QUYỀN\nÔng/bà: Lê Thị Mẩy Sinh năm: 1951\nBÊN ỦY QUYỀN\nMậy lê thi Mậy"
    slot = {"texts": [(uy_quyen, 1.0)]}
    assert tthn_dinh_danh._self_contradicted(slot, "Lê Thị Mẩy", "LÊ THỊ MẬY") == 1.0
    # Trang chỉ ghi cách viết của B → vẫn là nguồn của B.
    assert tthn_dinh_danh._self_contradicted({"texts": [("Ông/bà: Lê Thị Mẩy", 1.0)]}, "Lê Thị Mẩy", "LÊ THỊ MẬY") == 0.0
