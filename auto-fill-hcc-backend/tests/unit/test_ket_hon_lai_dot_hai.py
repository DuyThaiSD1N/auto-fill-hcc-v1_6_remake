"""Đăng ký lại kết hôn: lượt trích (nhóm field theo giấy, hậu kiểm tất định), mapper và lớp soát thứ hai."""
import re

import pytest

from app.pipelines._shared.thanh_tra.ho_so import Case, Result
from app.pipelines.ket_hon_lai import thanh_tra
from app.pipelines.ket_hon_lai.process import base_prompt, mapper
from app.pipelines.ket_hon_lai.process import runner as ket_hon_lai_runner
from app.pipelines.ket_hon_lai.process.prompt import EXTRA_RULES
from app.pipelines.ket_hon_lai.process.schema import ALLOWED, FIELDS
from app.pipelines.ket_hon_lai.thanh_tra import chu_the, dia_chi, dot_hai
from app.services.llm import client

NAM, NU = chu_the.SIDES
TO_KHAI = """TỜ KHAI ĐĂNG KÝ LẠI KẾT HÔN
Kính gửi: UBND phường Yên Trung
Họ, chữ đệm, tên người yêu cầu: Trần Văn Em
Nơi cư trú: Tổ 5, phường Yên Trung, tỉnh Bắc Ninh
Đề nghị cơ quan đăng ký lại kết hôn theo nội dung dưới đây:
Họ, chữ đệm, tên của vợ: Lê Thị Hanh
Ngày, tháng, năm sinh: 05/03/1985
Dân tộc: (2) Tày Quốc tịch: (2) Việt Nam
Nơi cư trú: TDP....Sơn...., phường Yên Trung,
tỉnh Bắc Ninh
Giấy tờ tùy thân: CCCD/CC số: 001185000007, Cục CSQLHC về TTXH/Bộ Công an cấp ngày: 10/05/2021
Họ, chữ đệm, tên của chồng: Trần Văn Em
Ngày, tháng, năm sinh: 02/04/1980
Dân tộc: (2) Kinh Quốc tịch: (2) Việt Nam
Nơi cư trú: Tổ 5, phường Yên Trung, tỉnh Bắc Ninh
Giấy tờ tùy thân: CCCD/CC số: 001080000009
Đã đăng ký kết hôn tại: UBND xã Đông Mai, huyện Yên Phong, tỉnh Bắc Ninh
Theo Giấy chứng nhận kết hôn số: (5), Quyển số: (5)
Đề nghị cấp bản sao(6): Có □, Không □
Số lượng:……bản
(5) Chỉ khai trong trường hợp biết rõ."""
THE_NU = """CĂN CƯỚC CÔNG DÂN
Số / No.: 001185000007
Họ và tên / Full name: LÊ THỊ HANH
Ngày sinh / Date of birth: 05/03/1985
Nơi thường trú / Place of residence: Thôn Sơn
Đông Mai, Yên Phong, Bắc Ninh"""
VALUES = {
    "BenNu_HoTen": "LÊ THỊ HANH", "BenNu_SoDinhDanh": "001185000007", "BenNu_NgaySinh": "05/03/1985",
    "BenNam_HoTen": "Trần Văn Em", "BenNam_SoDinhDanh": "001080000009", "BenNam_NgaySinh": "02/04/1980",
}
DOCS = [{"name": "tk.pdf", "text": TO_KHAI}, {"name": "nu.pdf", "text": THE_NU}]


def _case(values=None, docs=DOCS):
    return Case(docs, "", chu_the.effective({**VALUES, **(values or {})}), {})


def _fields(values: dict) -> list[dict]:
    return [{"name": name, "comp": "x-input", "value": value} for name, value in values.items()]


def _ui(values: dict, options=None) -> dict:
    return {f["name"]: f for f in mapper.enrich(_fields(values), options)}


# ───────── Lượt trích: prompt + hậu kiểm ─────────
def test_prompt_chi_dung_ten_field_co_trong_schema():
    prompt = base_prompt.build_system_prompt(FIELDS, EXTRA_RULES)
    names = set(re.findall(r"\b(?:BenNam|BenNu|ToKhaiNam|ToKhaiNu|ToKhai|CopyRequest|KetHonCu|CccdNam|CccdNu)_[A-Za-z]\w*",
                           prompt))
    assert not sorted(name for name in names if name not in ALLOWED and not name.endswith("_"))
    assert "ĐẾM TỪ CUỐI" not in prompt
    for block in ("<to_khai>", "<ket_hon_cu>", "<dan_toc>", "<the_can_cuoc>"):
        assert block in EXTRA_RULES


def _fallback(values: dict, docs=DOCS) -> dict:
    return ket_hon_lai_runner._compact_field_fallback(dict(values), docs)


def test_so_chu_thich_in_san_cua_mau_to_khai_khong_phai_so_dang_ky_cu():
    out = _fallback({"KetHonCu_So": "5", "KetHonCu_QuyenSo": "(5)", "KetHonCu_TinhDangKy": "Bắc Ninh"})
    assert out == {"KetHonCu_TinhDangKy": "Bắc Ninh"}
    # Người khai ghi thật số sau nhãn → giữ.
    text = TO_KHAI.replace("Theo Giấy chứng nhận kết hôn số: (5), Quyển số: (5)",
                           "Theo Giấy chứng nhận kết hôn số: 5, Quyển số: 01")
    assert _fallback({"KetHonCu_So": "5"}, [{"text": text}]) == {"KetHonCu_So": "5"}


def test_so_va_ngay_chi_co_tren_giay_khai_sinh_cua_con_thi_bo():
    birth = ("GIẤY KHAI SINH\nHọ, chữ đệm, tên: Trần Văn Út\nSố: 123/2010\nQuyển số: 02\n"
             "Ngày, tháng, năm đăng ký: 15/06/2010\nNơi đăng ký: UBND xã Đông Mai")
    docs = DOCS + [{"text": "───── Trang 3/3 ─────"}, {"text": birth}]
    out = _fallback({"KetHonCu_So": "123/2010", "KetHonCu_QuyenSo": "02", "KetHonCu_NgayDangKy": "15/06/2010"}, docs)
    assert out == {}
    # Cùng số có trên giấy chứng nhận kết hôn cũ → giữ.
    marriage = "GIẤY CHỨNG NHẬN KẾT HÔN\nSố: 123/2010\nNgày đăng ký: 15/06/2010"
    out = _fallback({"KetHonCu_So": "123/2010", "KetHonCu_NgayDangKy": "15/06/2010"}, docs + [{"text": marriage}])
    assert out == {"KetHonCu_So": "123/2010", "KetHonCu_NgayDangKy": "15/06/2010"}


# ───────── Mapper ─────────
def test_noi_cu_tru_theo_to_khai_truoc_the_va_khong_mac_dinh_so_lan():
    out = _ui({**VALUES, "BenNu_NoiCuTru_TrongNuoc": {"tinh": "Bắc Ninh", "xa": "Đông Mai", "diaChi": "Thôn Sơn"},
               "ToKhaiNu_NoiCuTru_TrongNuoc": {"tinh": "Bắc Ninh", "xa": "Phường Yên Trung", "diaChi": "TDP Sơn"}})
    assert out["NoiCuTru_BenNu_TrongNuoc"]["value"]["diaChi"] == "TDP Sơn"
    assert "SoLanKetHon_BenNu" not in out and "SoLanKetHon_BenNam" not in out
    assert out["LoaiTinhTrangHonNhan_BenNu"].get("default") is True


def test_ngay_dang_ky_cu_chi_co_nam_thi_de_trong():
    assert "ngayDangKyTruocDay" not in _ui({"KetHonCu_NgayDangKy": "1978"})
    assert _ui({"KetHonCu_NgayDangKy": "08/01/1982"})["ngayDangKyTruocDay"]["value"] == "08/01/1982"


def test_noi_dang_ky_cu_tinh_da_giai_the_va_co_quan_cap_huyen():
    # Tỉnh cũ đã giải thể: chỉ nhận đơn vị nằm trong tỉnh hiện hành chứa địa bàn tỉnh cũ; không tra ra thì chỉ điền tỉnh.
    out = _ui({"KetHonCu_TinhDangKy": "Hà Bắc", "KetHonCu_XaDangKy": "Xã Không Có Thật"})
    assert out["noiDangKyTruocDay_filter"]["value"] == "Bắc Ninh" and "noiDangKyTruocDay" not in out
    # Cơ quan cấp huyện không phải đơn vị cấp xã của dropdown.
    out = _ui({"KetHonCu_TinhDangKy": "Lào Cai", "KetHonCu_XaDangKy": "Thị xã Lào Cai"})
    assert out["noiDangKyTruocDay_filter"]["value"] == "Lào Cai" and "noiDangKyTruocDay" not in out


def test_dan_toc_ngoai_danh_muc_thi_xet_nguon_ke_tiep():
    out = _ui({**VALUES, "ToKhaiNu_DanToc": "Khinh", "BenNu_DanToc": "Kinh", "ToKhaiNam_DanToc": "Tây"})
    assert out["DanTocBenNu"]["value"] == "Kinh" and out["DanTocBenNam"]["value"] == "Tày"
    assert "DanTocBenNu" not in _ui({**VALUES, "ToKhaiNu_DanToc": "Khinh"})


def test_noi_cap_in_san_hai_co_quan_thi_theo_ngay_cap_khong_co_ngay_thi_de_trong():
    values = {"ToKhaiNu_HoTen": "Lê Thị Hanh", "ToKhaiNu_SoDinhDanh": "001185000007",
              "ToKhaiNu_NoiCap": "Cục CSQLHC về TTXH/Bộ Công an", "ToKhaiNu_NgayCap": "10/05/2021"}
    assert _ui(values)["NoiCapDD_BenNu"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    values.pop("ToKhaiNu_NgayCap")
    assert "NoiCapDD_BenNu" not in _ui(values)


def test_the_khong_bi_coi_la_nguoi_khac_khi_to_khai_doc_hong_hoac_chep_so_ben_kia():
    base = {**VALUES, "BenNu_NoiCap": "Bộ Công an", "BenNu_NgayCap": "09/09/2024"}
    garbled = _ui({**base, "ToKhaiNu_HoTen": "Lê Thị 842", "ToKhaiNu_SoDinhDanh": "001185999999"})
    assert garbled["HoTenBenNu"]["value"] == "LÊ THỊ HANH" and garbled["NoiCapDD_BenNu"]["value"] == "Bộ Công an"
    copied = _ui({**base, "ToKhaiNu_HoTen": "Phạm Thị Lan", "ToKhaiNu_SoDinhDanh": "001080000009"})
    assert copied["SoDinhDanh_BenNu"]["value"] == "001185000007"
    other = _ui({**base, "ToKhaiNu_HoTen": "Phạm Thị Lan", "ToKhaiNu_SoDinhDanh": "001185999999"})
    assert other["HoTenBenNu"]["value"] == "PHẠM THỊ LAN" and other["HoTenBenNu"].get("default") is True


# ───────── Khối vợ / chồng trên tờ khai ─────────
def test_khoi_vo_chong_cua_to_khai_doc_theo_dong_nhan():
    [table] = chu_the.declaration_tables(DOCS)
    assert chu_the.cell(table, "ho_ten", NU)[0] == "Lê Thị Hanh" and chu_the.cell(table, "ho_ten", NAM)[0] == "Trần Văn Em"
    assert chu_the.cell(table, "dan_toc", NU)[0] == "Tày" and chu_the.cell(table, "dan_toc", NAM)[0] == "Kinh"
    assert chu_the.cell(table, "cu_tru", NU) == ("TDP....Sơn...., phường Yên Trung, tỉnh Bắc Ninh",
                                                 "Nơi cư trú: TDP....Sơn...., phường Yên Trung,")
    # Khối người yêu cầu không phải khối của chồng.
    assert chu_the.cell(table, "cu_tru", NAM)[1] == "Nơi cư trú: Tổ 5, phường Yên Trung, tỉnh Bắc Ninh"
    assert chu_the.declaration_tables([{"text": THE_NU}]) == []


@pytest.fixture
def old_card_catalog(monkeypatch):
    """Danh mục giả: "Đông Mai" là xã cũ của huyện "Yên Phong", đã nhập vào phường Yên Trung."""
    wards = {"dong mai": "Phường Yên Trung", "yen trung": "Phường Yên Trung"}

    def area(value):
        return {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "diaChi": str(value.get("diaChi") or ""),
                "xa": wards.get(dia_chi.base._bare(value.get("xa")), str(value.get("xa") or ""))}

    monkeypatch.setattr(dia_chi.mapper, "_area", area)
    monkeypatch.setattr(dia_chi.area_remap, "is_current_area", lambda tinh, xa: xa in wards.values())
    monkeypatch.setattr(dia_chi, "_in_catalog", lambda split: {"xa": "Phường Yên Trung"} if (
        split.get("xa") == "Đông Mai" and split.get("huyen") == "Yên Phong") else None)


def test_dia_chi_lay_theo_the_cu_thi_de_xuat_theo_khoi_to_khai(old_card_catalog):
    from_card = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Đông Mai", "diaChi": "Thôn Sơn"}
    finding = dia_chi.side_finding(_case({"ToKhaiNu_NoiCuTru_TrongNuoc": from_card}), NU)
    assert finding.unit.key == "nu.noi_cu_tru" and finding.owner == "bên vợ"
    proposed = finding.values["ToKhaiNu_NoiCuTru_TrongNuoc"]
    assert proposed["diaChi"] == "TDP Sơn" and dia_chi.base._bare(proposed["xa"]) == "yen trung"
    assert finding.quote in TO_KHAI


def test_dia_chi_da_dung_theo_to_khai_thi_khong_de_xuat(old_card_catalog):
    right = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Yên Trung", "diaChi": "TDP Sơn"}
    assert dia_chi.side_finding(_case({"ToKhaiNu_NoiCuTru_TrongNuoc": right}), NU) is None


# ───────── Điền đợt 2 ─────────
def test_bo_thanh_tra_dinh_danh_va_dia_chi_cho_ca_hai_ben():
    assert [i.key for i in thanh_tra.INSPECTORS] == ["dinh_danh", "dia_chi"]
    for inspector in thanh_tra.INSPECTORS:
        assert {unit.key.split(".")[0] for unit in inspector.units} == {"nam", "nu"}


def test_form_cu_can_nang_luc_rieng_de_chay_dot_hai():
    from app.procedures.registry import get_procedure
    from app.second_pass import service

    assert service.capability(get_procedure("dang-ky-lai-ket-hon")) == "secondPassLegacy"


async def test_ban_va_chi_gom_o_lop_soat_doi_kem_gia_tri_luot_dau(monkeypatch):
    async def review(documents, values, options=None):
        return Result({**values, "BenNu_HoTen": "LÊ THỊ MANH"}, [{"outcome": "sua"}], {})

    monkeypatch.setattr(dot_hai, "review", review)
    base = mapper.enrich(_fields(VALUES), {})
    out = await dot_hai.patch(DOCS, _fields(VALUES), base, {})
    assert {f["name"]: (f["value"], f["from"], f["by"]) for f in out["fields"]} == {
        "HoTenBenNu": ("LÊ THỊ MANH", "LÊ THỊ HANH", "dinh_danh")}


async def test_runner_chi_tra_ham_dot_hai_khi_duoc_bat(monkeypatch):
    from app.config import settings
    from app.services import ocr

    async def fake_uncached(files):
        return [{"name": f.get("name"), "text": THE_NU, "provider": "tiengnoi"} for f in files]

    async def fake_primary(messages, temperature, max_tokens, enable_thinking=False):
        return '{"fields": {"BenNu_HoTen": "Lê Thị Hanh", "BenNu_SoDinhDanh": "001185000007"}}'

    monkeypatch.setattr(settings, "ocr_cache_enabled", False)
    monkeypatch.setattr(ocr, "_ocr_per_file_uncached", fake_uncached)
    monkeypatch.setattr(client, "_chat_primary", fake_primary)
    files = {"": [{"name": "the.png", "type": "image/png", "dataUrl": "data:image/png;base64,QUJD"}]}
    plain = await ket_hon_lai_runner.run(files, {})
    wanted = await ket_hon_lai_runner.run(files, {"_secondPass": True})
    assert "_second_pass" not in plain and callable(wanted.pop("_second_pass"))
    assert plain["fields"] == wanted["fields"]


def test_noi_cu_tru_to_khai_bo_cham_giu_cho_va_thieu_tinh_thi_bu_tinh_tu_the():
    out = _ui({**VALUES, "BenNu_NoiCuTru_TrongNuoc": {"tinh": "Bắc Ninh", "xa": "Đông Mai", "diaChi": "Thôn Sơn"},
               "ToKhaiNu_NoiCuTru_TrongNuoc": {"tinh": "", "xa": "Phường Yên Trung", "diaChi": "TDP....Sơn...."}})
    area = out["NoiCuTru_BenNu_TrongNuoc"]["value"]
    assert area["diaChi"] == "TDP Sơn" and "Bắc Ninh" in area["tinh"]


def test_so_dang_ky_cu_khong_dung_sau_nhan_so_thi_bo():
    docs = [{"text": "Trang số: 11\nĐã đăng ký kết hôn ngày 16/08/1976\nTheo Giấy chứng nhận kết hôn số: (5), Quyển số: (5) Năm 1978"}]
    assert _fallback({"KetHonCu_So": "11", "KetHonCu_QuyenSo": "08"}, docs) == {}
    assert _fallback({"KetHonCu_So": "1978"}, docs) == {}
    docs = [{"text": "GIẤY CHỨNG NHẬN KẾT HÔN\nSố: 40/1990\nQuyển số: 01"}]
    assert _fallback({"KetHonCu_So": "40/1990", "KetHonCu_QuyenSo": "1"}, docs) == {"KetHonCu_So": "40/1990", "KetHonCu_QuyenSo": "1"}


def test_dia_chi_chi_tiet_cua_a_co_tren_giay_khac_thi_khong_lui_ve_dong_the_cu(old_card_catalog):
    # Khối chồng chỉ ghi tên, chi tiết "TDP Sơn" của A có ở bản cam đoan; dòng thẻ in địa chỉ cũ với chi tiết khác.
    text = TO_KHAI.replace("Nơi cư trú: Tổ 5, phường Yên Trung, tỉnh Bắc Ninh\nGiấy tờ tùy thân: CCCD/CC số: 001080000009",
                           "Nơi cư trú: Yên Trung, Bắc Ninh\nGiấy tờ tùy thân: CCCD/CC số: 001080000009")
    the_nam = ("CĂN CƯỚC CÔNG DÂN\nSố / No.: 001080000009\nHọ và tên / Full name: TRẦN VĂN EM\n"
               "Nơi thường trú / Place of residence: Thôn Hạ\nĐông Mai, Yên Phong, Bắc Ninh")
    cam_doan = "BẢN CAM ĐOAN\nNơi cư trú: TDP Sơn, phường Yên Trung, tỉnh Bắc Ninh"
    current = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Yên Trung", "diaChi": "TDP Sơn"}
    case = _case({"ToKhaiNam_NoiCuTru_TrongNuoc": current},
                 [{"text": text}, {"text": the_nam}, {"text": cam_doan}])
    assert dia_chi.side_finding(case, NAM) is None


def test_mapper_dia_chi_dau_gach_chi_tiet_khong_xa_ten_mat_dau_va_tp():
    card = {"tinh": "Bắc Ninh", "xa": "Thị trấn Chờ", "diaChi": "Thôn Trung Ban",
            "_tach": "chi tiết: Thôn Trung Ban | xã: Thị trấn Chờ | huyện (bỏ): Yên Phong | tỉnh: Bắc Ninh"}
    dash = {"tinh": "—", "xa": "—", "diaChi": "—", "_tach": "chi tiết: — | xã: — | huyện (bỏ): — | tỉnh: —"}
    out = _ui({**VALUES, "BenNu_NoiCuTru_TrongNuoc": card, "ToKhaiNu_NoiCuTru_TrongNuoc": dash})
    assert out["NoiCuTru_BenNu_TrongNuoc"]["value"]["diaChi"] == "Thôn Trung Ban"
    assert out["NoiCuTru_BenNu_TrongNuoc"]["value"]["xa"]
    # Tờ khai chỉ ghi chi tiết, không xã → lấy trọn theo thẻ.
    out = _ui({**VALUES, "BenNu_NoiCuTru_TrongNuoc": card, "ToKhaiNu_NoiCuTru_TrongNuoc": {"diaChi": "Thôn Gia"}})
    assert out["NoiCuTru_BenNu_TrongNuoc"]["value"]["diaChi"] == "Thôn Trung Ban"
    # Tên phường mất dấu → tên duy nhất của tỉnh trùng khi bỏ dấu; "TP <tên>" dưới xã là "TDP".
    out = _ui({**VALUES, "ToKhaiNu_NoiCuTru_TrongNuoc": {"tinh": "Bắc Ninh", "xa": "phường Tien phong", "diaChi": "TP Đông"}})
    area = out["NoiCuTru_BenNu_TrongNuoc"]["value"]
    assert area["xa"] == "Phường Tiền Phong" and area["diaChi"] == "TDP Đông"


def test_noi_cap_bo_cong_an_cho_the_cap_truoc_7_2024_la_cuc_va_so_ban_sao_bi_bo():
    out = _ui({**VALUES, "BenNu_NoiCap": "Bộ Công an", "BenNu_NgayCap": "16/04/2021"})
    assert out["NoiCapDD_BenNu"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert out["LoaiGiayToDinhDanh_BenNu"]["value"] == "Căn cước công dân"
    out = _ui({**VALUES, "BenNu_NoiCap": "Bộ Công an", "BenNu_NgayCap": "16/09/2024"})
    assert out["NoiCapDD_BenNu"]["value"] == "Bộ Công an"
    assert "soDangKyTruocDay" not in _ui({"KetHonCu_So": "893/TL.KH-BS"})
    assert _ui({"KetHonCu_So": "40/1990"})["soDangKyTruocDay"]["value"] == "40/1990"


def _rec(name, number="", birth="", role="", handwritten=False, tier=3, doc=2):
    from app.pipelines.ket_hon_lai.thanh_tra import dinh_danh
    return {"name": name, "number": number, "birth": dinh_danh.base._birth_key(birth) if birth else "", "role": role,
            "handwritten": handwritten, "tier": tier, "doc": doc, "text": f"Họ, chữ đệm, tên: {name}"}


def test_ho_ten_lech_dau_tren_the_thi_theo_da_so_giay_khac_the():
    from app.pipelines.ket_hon_lai.thanh_tra import dinh_danh
    case = _case({"BenNu_HoTen": "LÊ THỊ HẢO"})
    records = [_rec("LÊ THỊ HẢO", "001185000007", "05/03/1985", "chủ thẻ", tier=2),
               _rec("Lê Thị Hào", "001185000007", "05/03/1985", "người cam đoan"),
               _rec("LÊ THỊ HÀO", role="mẹ", tier=4),
               _rec("Lê Thị Hào", "001185000007", role="vợ", handwritten=True, tier=1)]
    finding = dinh_danh._printed_spelling_finding(NU, case, records)
    assert finding.values == {"BenNu_HoTen": "Lê Thị Hào"} and finding.backed
    # Một giấy khác thẻ ngang một giấy khác ghi cách khác → không đủ căn cứ.
    tie = [records[0], _rec("Lê Thị Hào", role="mẹ", tier=4), _rec("Lê Thị Hảo", role="vợ", tier=4)]
    assert dinh_danh._printed_spelling_finding(NU, case, tie) is None
    # Người khác trùng tên bỏ dấu nhưng không trùng số / ngày sinh / vai → không tính.
    stranger = [records[0], _rec("Lê Thị Hào", role="con", tier=4), _rec("Lê Thị Hào", role="người làm chứng", tier=4)]
    assert dinh_danh._printed_spelling_finding(NU, case, stranger) is None
