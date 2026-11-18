"""Điền đợt 2 của thủ tục cấp bản sao trích lục: lượt điền đầu giữ nguyên, lượt soát chỉ ghi các ô thanh tra sửa."""
from app.pipelines._shared.thanh_tra.ho_so import Result
from app.pipelines.trich_luc_dvc_moi import thanh_tra
from app.pipelines.trich_luc_dvc_moi.process import mapper
from app.pipelines.trich_luc_dvc_moi.process import runner as trich_luc_runner
from app.pipelines.trich_luc_dvc_moi.thanh_tra import dot_hai
from app.services import ocr
from app.services.llm import client
from app.config import settings
import pytest

_OTHER = {"formContext": {"applicantFullname": "Lê Thị Nộp Hộ", "applicantIdentityNumber": "001190000002"}}
_RAW = {
    "NguoiDuocCap_HoTen": "Trần Văn Mẫu", "NguoiDuocCap_SoDinhDanh": "001080000001",
    "NguoiDuocCap_NgaySinh": "02/03/1980", "GiayTo_LoaiSuKien": "birth", "GiayTo_TenGiayTo": "Giấy khai sinh",
    "GiayTo_So": "64/TLKS-BS", "GiayTo_CoQuanDangKy": "UBND xã Mẫu",
}


def _fields(values: dict) -> list[dict]:
    return [{"name": name, "comp": "x-input", "value": value} for name, value in values.items()]


def _first_fill(values: dict, options: dict) -> list[dict]:
    return mapper.enrich(_fields(values), options)[0]


def _fake_review(monkeypatch, changes: dict):
    async def review(documents, context, values, options=None):
        return Result({**values, **changes}, [{"outcome": "sua"}], {"inspect_ms": 1})
    monkeypatch.setattr(dot_hai, "review", review)


async def test_o_lop_soat_sua_ra_ban_va_kem_gia_tri_luot_dau(monkeypatch):
    _fake_review(monkeypatch, {"GiayTo_So": "140", "NguoiDuocCap_HoTen": "Trần Văn Mầu",
                               "GiayTo_CoQuanDangKy": "UBND xã Mẫu, huyện Y, tỉnh Z"})
    base = _first_fill(_RAW, _OTHER)
    out = await dot_hai.patch([{"name": "a", "text": "x"}], "", _fields(_RAW), base, _OTHER)
    got = {f["name"]: (f["value"], f["from"], f["by"]) for f in out["fields"]}
    assert got == {
        "citizenNDK_HoVaTen": ("TRẦN VĂN MẦU", "TRẦN VĂN MẪU", "nhan_than"),
        "citizenHoSo_CoQuanDangKy": ("UBND xã Mẫu, huyện Y, tỉnh Z", "UBND xã Mẫu", "ho_tich"),
        "citizencauhoi3": ("140", "64/TLKS-BS", "ho_tich"),
    }


async def test_lop_soat_khong_doi_gi_thi_ban_va_rong(monkeypatch):
    _fake_review(monkeypatch, {})
    out = await dot_hai.patch([], "", _fields(_RAW), _first_fill(_RAW, _OTHER), _OTHER)
    assert out["fields"] == []


async def test_quan_he_doi_thi_khong_va_gi(monkeypatch):
    # Tên + số định danh sau soát trùng chủ tài khoản → mapper chuyển sang "Bản thân", form đổi bố cục.
    _fake_review(monkeypatch, {"NguoiDuocCap_HoTen": "Lê Thị Nộp Hộ", "NguoiDuocCap_SoDinhDanh": "001190000002",
                               "GiayTo_So": "140"})
    out = await dot_hai.patch([], "", _fields(_RAW), _first_fill(_RAW, _OTHER), _OTHER)
    assert out["fields"] == []


async def test_ban_than_chi_soat_giay_ho_tich(monkeypatch):
    seen = []

    async def run(case, inspectors, *, title):
        seen.append([i.key for i in inspectors])
        return Result(dict(case.values), [], {})
    monkeypatch.setattr(thanh_tra.engine, "run", run)
    own = {"formContext": {"applicantFullname": "Trần Văn Mẫu", "applicantIdentityNumber": "001080000001"}}
    await thanh_tra.review([], "", dict(_RAW), own)
    await thanh_tra.review([], "", dict(_RAW), _OTHER)
    assert seen == [["ho_tich"], ["ho_tich", "nhan_than", "dia_chi"]]


async def test_runner_chi_tra_ham_dot_hai_khi_duoc_bat(monkeypatch):
    async def fake_uncached(files):
        return [{"name": f.get("name"), "text": "TỜ KHAI\nHọ, chữ đệm, tên: TRẦN VĂN MẪU", "provider": "tiengnoi"}
                for f in files]

    async def fake_primary(messages, temperature, max_tokens, enable_thinking=False):
        return '{"fields": {"NguoiDuocCap_HoTen": "Trần Văn Mẫu"}}'

    monkeypatch.setattr(settings, "ocr_cache_enabled", False)
    monkeypatch.setattr(ocr, "_ocr_per_file_uncached", fake_uncached)
    monkeypatch.setattr(client, "_chat_primary", fake_primary)
    files = {"": [{"name": "to-khai.png", "type": "image/png", "dataUrl": "data:image/png;base64,QUJD"}]}
    plain = await trich_luc_runner.run(files, {})
    wanted = await trich_luc_runner.run(files, {"_secondPass": True})
    assert "_second_pass" not in plain
    assert callable(wanted.pop("_second_pass"))
    assert plain["fields"] == wanted["fields"]


# ───────── Thanh tra địa chỉ ghép theo cấp (chép từ thủ tục hôn nhân) ─────────
import asyncio  # noqa: E402
import json  # noqa: E402

from app.pipelines._shared.thanh_tra.ho_so import Case  # noqa: E402
from app.pipelines.trich_luc_dvc_moi.thanh_tra import dia_chi_ghep  # noqa: E402

_CONTEXT = "<phan_vai_da_xac_dinh>\n<nguoi_duoc_cap>\nHọ tên: Lê Thị Hanh\n</nguoi_duoc_cap>\n</phan_vai_da_xac_dinh>"
_CURRENT_WARDS = {"dong mai": "Xã Đông Mai"}
_OLD_WARDS = {"dong tho": "Xã Đông Mai"}
_KHAI = ("TỜ KHAI CẤP BẢN SAO TRÍCH LỤC HỘ TỊCH\nĐề nghị cấp bản sao cho người có tên dưới đây:\n"
         "Họ, chữ đệm, tên: Lê Thị Hanh\nNơi cư trú: 5T Cao Thắng, xã Đông Mai, tỉnh Bắc Ninh\n"
         "Giấy tờ tùy thân: CCCD số 001185000007\nNgười yêu cầu\n(Ký, ghi rõ họ, chữ đệm, tên)\nHanh")
_THE = ("\n───── Trang 2/2 ─────\nCĂN CƯỚC CÔNG DÂN\nHọ và tên / Full name: LÊ THỊ HANH\n"
        "Nơi thường trú / Place of residence: 57 Cao Thắng\nĐông Thọ, Yên Phong, Bắc Ninh")


def _fake_area(value, ocr_text=""):
    key = dia_chi_ghep.base._bare(value.get("xa"))
    ward = _CURRENT_WARDS.get(key) or _OLD_WARDS.get(key)
    return {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": ward or str(value.get("xa") or ""),
            "diaChi": str(value.get("diaChi") or ""), **({} if ward else {"_xaChuaChon": True})}


def _address(monkeypatch, current):
    reply = {"dong": [{"so": n, "thuoc_ve": "người được cấp", "loai": "nơi cư trú / thường trú"} for n in (1, 2)],
             "chon": None}

    async def fake_chat(messages, **kwargs):
        return json.dumps(reply)

    monkeypatch.setattr(client, "chat", fake_chat)
    monkeypatch.setattr(dia_chi_ghep.mapper, "_area", _fake_area)
    monkeypatch.setattr(dia_chi_ghep, "_in_catalog", lambda split: None if _fake_area(split).get("_xaChuaChon")
                        else _fake_area(split))
    case = Case([{"name": "hs.pdf", "text": _KHAI + _THE}], _CONTEXT, {dia_chi_ghep.FIELD: current}, {})
    return asyncio.run(dia_chi_ghep.find(dia_chi_ghep.INSPECTOR, case, "thử"))


def test_dia_chi_xa_theo_dong_ba_cap_chi_tiet_theo_dong_in(monkeypatch):
    # Tờ khai (viết tay, ba cấp mới) đọc lệch số nhà; thẻ (in, địa chỉ cũ cùng xã mới) ghi rõ.
    [finding] = _address(monkeypatch, {"tinh": "Bắc Ninh", "xa": "Đông Thọ", "diaChi": "5T Cao Thắng"})
    assert finding.values[dia_chi_ghep.FIELD] == {"tinh": "tỉnh Bắc Ninh", "xa": "xã Đông Mai", "diaChi": "57 Cao Thắng"}
    assert finding.backed and "dòng in [2]" in " ".join(finding.evidence)


def test_dia_chi_luot_trich_da_dung_thi_khong_de_xuat(monkeypatch):
    assert _address(monkeypatch, {"tinh": "Bắc Ninh", "xa": "Đông Mai", "diaChi": "Số nhà 57, đường Cao Thắng"}) == []


def test_dong_noi_sau_dia_chi_cu_la_nguon_rieng_ba_cap():
    item = {"line": "Nơi cư trú: (2) Khu phố A phường 1 TP B - tỉnh C",
            "text": "Nơi cư trú: (2) Khu phố A phường 1 TP B - tỉnh C tại tổ dân phố D phường E, tỉnh C"}
    follow = dia_chi_ghep._continuation(item)
    assert follow["line"] == "tại tổ dân phố D phường E, tỉnh C"
    assert follow["_split"] == {"tinh": "tỉnh C", "xa": "phường E", "diaChi": "tổ dân phố D"}
    assert dia_chi_ghep._continuation({"line": "Nơi cư trú: Thôn A, xã B", "text": "Nơi cư trú: Thôn A, xã B tỉnh C"}) is None


def test_chi_tiet_de_xuat_con_chu_chi_cap_thi_bo_o_chi_tiet(monkeypatch):
    monkeypatch.setattr(dia_chi_ghep.mapper, "_area", lambda value, ocr_text="": {**value, "quocGia": "Việt Nam"})
    case = Case([], _CONTEXT, {dia_chi_ghep.FIELD: {"tinh": "C", "xa": "Phường E", "diaChi": "Khu phố 3"}}, {})

    def screened(detail):
        finding = thanh_tra.engine.Finding(dia_chi_ghep.INSPECTOR, dia_chi_ghep.base.UNITS[0],
                                           {dia_chi_ghep.FIELD: {"tinh": "C", "xa": "Phường E", "diaChi": detail}},
                                           "dòng", 1)
        return dia_chi_ghep.screen(finding, case)
    # Cùng xã, chi tiết đề xuất bẩn → bỏ chi tiết; còn lại không khác lượt trích nên không đề xuất gì.
    assert screened("Khu phố 3, phường 1 TP B, tỉnh C") is None
    assert screened("xóm Tĩnh Hòa") is not None


def test_chi_tiet_bo_nhan_mau_in_lien():
    assert dia_chi_ghep._clean_detail("TDP(thôn Đông Lương...") == "TDP Đông Lương"
    assert dia_chi_ghep._clean_detail("TDP(thôn) Đông Lương") == "TDP Đông Lương"


# ───────── Nhân thân: MRZ lệch một chữ, cụm thẻ vô lý, dân tộc ─────────
from app.pipelines.trich_luc_dvc_moi.thanh_tra import nhan_than  # noqa: E402

_CARD = ("CĂN CƯỚC\nHọ, chữ đệm và tên khai sinh / Full name:\nTRẦN THỊ HƯƠNG\n"
         "IDVNM0011650052878001165005287<<6\n6512255F3512255VNM<<<<<<<<<<<8\nTRAN<<THI<HUONG<<<<<<<<<<<<<<<<")
_NHAN_THAN_CTX = "<nguoi_duoc_cap>\nHọ tên: Trần Thị Hưng\nGiới tính: Nữ\n</nguoi_duoc_cap>"


def test_mrz_lech_mot_chu_van_nhan_va_lam_can_cu_ho_ten():
    case = Case([{"name": "the.pdf", "text": _CARD}], _NHAN_THAN_CTX, {"NguoiDuocCap_HoTen": "Trần Thị Hưng"}, {})
    assert [card["name"] for card in nhan_than._subject_cards(case)] == ["tran thi huong"]
    unit = next(u for u in nhan_than.UNITS if u.key == "ho_ten")
    assert [ok for ok, _ in nhan_than.signals(unit, {"NguoiDuocCap_HoTen": "TRẦN THỊ HƯƠNG"}, case)] == [True]
    assert [ok for ok, _ in nhan_than.signals(unit, {"NguoiDuocCap_HoTen": "Trần Thị Hưng"}, case)] == [False]


def test_cum_the_bo_ngay_cap_trung_ngay_sinh_va_noi_cap_khong_xac_dinh():
    unit = next(u for u in nhan_than.UNITS if u.key == "giay_to_tuy_than")
    case = Case([], "", {"NguoiDuocCap_NgaySinh": "25/12/1965"}, {})
    finding = thanh_tra.engine.Finding(nhan_than.INSPECTOR, unit, {
        "NguoiDuocCap_LoaiGiayTo": "Căn cước", "NguoiDuocCap_SoGiayTo": "001165005287",
        "NguoiDuocCap_NgayCap": "25/12/1965", "NguoiDuocCap_NoiCap": "Không xác định"}, "dòng", 1)
    assert nhan_than._tidy_card(finding, case) == {"NguoiDuocCap_LoaiGiayTo": "Căn cước",
                                                   "NguoiDuocCap_SoGiayTo": "001165005287"}


@pytest.mark.parametrize("owner,line_no,expected", [
    ("người được cấp", 1, {"NguoiDuocCap_DanToc": "Kinh"}),
    ("cha / mẹ của người được cấp", 2, {"NguoiDuocCap_DanToc": "Tày"}),  # engine bác theo thuoc_ve
])
async def test_dan_toc_cau_hoi_dong_tren_dong_co_chu_dan_toc(monkeypatch, owner, line_no, expected):
    text = ("Họ, chữ đệm, tên: TRẦN THỊ HƯNG\nGiới tính: Nữ Dân tộc: (2) Kinh\n"
            "Họ, chữ đệm, tên người mẹ: LÊ THỊ A\nNăm sinh: 1990 Dân tộc: Tày")
    seen = []

    async def fake_chat(messages, **kwargs):
        seen.append(messages[1]["content"])
        return json.dumps({"dong": line_no, "value": expected["NguoiDuocCap_DanToc"], "thuoc_ve": owner})
    monkeypatch.setattr(client, "chat", fake_chat)
    finding = await nhan_than._ethnic_finding(Case([{"name": "ks.pdf", "text": text}], _NHAN_THAN_CTX, {}, {}), "thử")
    assert "[1] Giới tính: Nữ Dân tộc: (2) Kinh" in seen[0] and "Họ, chữ đệm, tên: TRẦN THỊ HƯNG" in seen[0]
    assert finding.values == expected and finding.owner == owner
    assert bool(thanh_tra.engine.reject_reason(finding, Case([{"name": "ks.pdf", "text": text}], "", {}, {}))) is (
        owner != "người được cấp")


async def test_da_co_dan_toc_thi_khong_hoi(monkeypatch):
    async def fake_chat(messages, **kwargs):
        raise AssertionError("không được gọi")
    monkeypatch.setattr(client, "chat", fake_chat)
    assert await nhan_than._ethnic_finding(Case([{"name": "a", "text": "Dân tộc: Kinh"}], "", {"NguoiDuocCap_DanToc": "Kinh"}, {}), "t") is None


def test_cum_the_bo_ngay_cap_trung_ngay_sinh_trong_mrz():
    unit = next(u for u in nhan_than.UNITS if u.key == "giay_to_tuy_than")
    case = Case([{"name": "the.pdf", "text": _CARD}], _NHAN_THAN_CTX, {"NguoiDuocCap_NgaySinh": "1965"}, {})
    finding = thanh_tra.engine.Finding(nhan_than.INSPECTOR, unit, {
        "NguoiDuocCap_SoGiayTo": "001165005287", "NguoiDuocCap_NgayCap": "25/12/1965"}, "dòng", 1)
    assert nhan_than._tidy_card(finding, case) == {"NguoiDuocCap_SoGiayTo": "001165005287"}


def test_chi_tiet_nhet_ten_xa_huyen_bi_bo_ca_khi_luot_trich_trong_giu_xa():
    case = Case([], _CONTEXT, {}, {})
    finding = thanh_tra.engine.Finding(dia_chi_ghep.INSPECTOR, dia_chi_ghep.base.UNITS[0], {dia_chi_ghep.FIELD: {
        "tinh": "tỉnh C", "xa": "Phường E", "diaChi": "thôn A ngoài xã B huyện D"}}, "dòng", 1)
    assert dia_chi_ghep.screen(finding, case).values[dia_chi_ghep.FIELD] == {"tinh": "tỉnh C", "xa": "Phường E"}


@pytest.mark.parametrize("extra,kept", [
    ({"NguoiDuocCap_NgayCap": "18/12/2042"}, {}),                                       # ngày hết hạn của thẻ
    ({"NguoiDuocCap_NoiCap": "Nghĩa Kỳ, Tỉnh Quảng Ngãi"}, {}),                         # nơi cấp giấy kết hôn
    ({"NguoiDuocCap_NoiCap": "CA Quảng Ngãi"}, {"NguoiDuocCap_NoiCap": "CA Quảng Ngãi"}),
    ({"NguoiDuocCap_NoiCap": "Cục Cảnh sát QLHC về TTXH", "NguoiDuocCap_NgayCap": "10/05/2021"},
     {"NguoiDuocCap_NoiCap": "Cục Cảnh sát QLHC về TTXH", "NguoiDuocCap_NgayCap": "10/05/2021"}),
])
def test_cum_the_bo_ngay_het_han_va_noi_cap_khong_phai_co_quan(extra, kept):
    unit = next(u for u in nhan_than.UNITS if u.key == "giay_to_tuy_than")
    finding = thanh_tra.engine.Finding(nhan_than.INSPECTOR, unit, {"NguoiDuocCap_SoGiayTo": "250199202", **extra},
                                       "dòng", 1)
    assert nhan_than._tidy_card(finding, Case([], "", {}, {})) == {"NguoiDuocCap_SoGiayTo": "250199202", **kept}


_TRICH_LUC_KHAI_TU_TAI_NHA = """TRÍCH LỤC KHAI TỬ
(BẢN SAO)
Họ, chữ đệm, tên: NGUYỄN VĂN A
Nơi chết: Tại nhà ở thôn Một, xã Vĩnh Ngọc, thành phố Nha Trang, tỉnh Khánh Hòa
Đã được đăng ký khai tử tại: UBND xã Vĩnh Ngọc"""


def test_thanh_tra_dia_chi_chet_tai_nha_bo_sung_noi_cu_tru():
    from app.pipelines._shared.thanh_tra.ho_so import Case
    from app.pipelines.trich_luc_dvc_moi.thanh_tra import dia_chi_ghep

    values = {"GiayTo_LoaiSuKien": "death", "NguoiDuocCap_HoTen": "NGUYỄN VĂN A"}
    case = Case([{"name": "tl.pdf", "text": _TRICH_LUC_KHAI_TU_TAI_NHA}], "", values)
    finding = dia_chi_ghep.home_finding(case, None)
    area = finding.values["NguoiDuocCap_NoiCuTru"]
    assert area["tinh"] == "Khánh Hòa" and area["diaChi"] == "thôn Một" and finding.backed
    # Lượt trích đã điền đúng nhà đó → không có gì để xử.
    assert dia_chi_ghep.home_finding(Case(case.documents, "", {**values, "NguoiDuocCap_NoiCuTru": area}), None) is None
    family = _TRICH_LUC_KHAI_TU_TAI_NHA.replace("Tại nhà ở thôn Một,", "Tại gia đình, thôn Một,")
    assert dia_chi_ghep.home_finding(Case([{"text": family}], "", values), None).values["NguoiDuocCap_NoiCuTru"][
        "diaChi"] == "thôn Một"
    # Chết ở bệnh viện → không phải nơi cư trú.
    hospital = _TRICH_LUC_KHAI_TU_TAI_NHA.replace("Tại nhà ở thôn Một,", "Bệnh viện tỉnh,")
    assert dia_chi_ghep.home_finding(Case([{"text": hospital}], "", values), None) is None
