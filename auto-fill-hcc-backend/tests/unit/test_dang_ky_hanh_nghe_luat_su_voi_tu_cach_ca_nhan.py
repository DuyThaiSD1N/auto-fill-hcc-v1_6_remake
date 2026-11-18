"""Pipeline "Đăng ký hành nghề luật sư với tư cách cá nhân" (1.002153): mapper eForm Mẫu TP-LS-05-sđ + đính kèm 4
dòng (Thẻ luật sư chung dòng 2 + 4; chế độ tách / không tách).

Dữ liệu trong test là ví dụ bịa (tên, số giấy tờ, công ty) — không lấy từ hồ sơ thật hay bộ hồ sơ mẫu.
"""

import asyncio
import json

from app.pipelines.dang_ky_hanh_nghe_luat_su_voi_tu_cach_ca_nhan.attach import planner as attach
from app.pipelines.dang_ky_hanh_nghe_luat_su_voi_tu_cach_ca_nhan.attach.dinh_kem_khong_tach import planner as khong_tach
from app.pipelines.dang_ky_hanh_nghe_luat_su_voi_tu_cach_ca_nhan.attach.dinh_kem_khong_tach.planner import (
    build_plan_items,
    rule_types,
    validated_classifications,
)
from app.pipelines.dang_ky_hanh_nghe_luat_su_voi_tu_cach_ca_nhan.attach.dinh_kem_tach import planner as tach
from app.pipelines.dang_ky_hanh_nghe_luat_su_voi_tu_cach_ca_nhan.process import runner as process_runner
from app.pipelines.dang_ky_hanh_nghe_luat_su_voi_tu_cach_ca_nhan.process.mapper import enrich
from app.pipelines.dang_ky_hanh_nghe_luat_su_voi_tu_cach_ca_nhan.process.schema import UI_COMP_BY_NAME
from app.process.schemas import FileItem
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.services import ocr

_KEY = "dang-ky-hanh-nghe-luat-su-voi-tu-cach-ca-nhan"

APPLICATION_TEXT = (
    "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM ĐƠN ĐỀ NGHỊ ĐĂNG KÝ HÀNH NGHỀ LUẬT SƯ VỚI TƯ CÁCH CÁ NHÂN Kính gửi: Sở Tư "
    "pháp thành phố Đà Nẵng ... Thẻ luật sư số 20481/LS do Liên đoàn Luật sư Việt Nam cấp ngày 03/03/2019 "
    "2. Tên, địa chỉ của cơ quan, tổ chức ký hợp đồng lao động: Công ty TNHH Ví Dụ"
)
CONTRACT_TEXT = (
    "CÔNG TY TNHH VÍ DỤ Số: 08/2026/HĐLĐ HỢP ĐỒNG LAO ĐỘNG (Không xác định thời hạn) BÊN A – NGƯỜI SỬ DỤNG LAO ĐỘNG "
    "BÊN B – NGƯỜI LAO ĐỘNG Thẻ luật sư số: 20481/LS"
)
CARD_TEXT = "LIÊN ĐOÀN LUẬT SƯ VIỆT NAM VIET NAM BAR FEDERATION THẺ LUẬT SƯ LAWYER CARD Số thẻ / No.: 20481/LS"
CERT_TEXT = "BỘ TƯ PHÁP CHỨNG CHỈ HÀNH NGHỀ LUẬT SƯ Số: 11223/TP/LS-CCHN"
INDEX_TEXT = "DANH MỤC HỒ SƠ 1. Đơn đề nghị 2. Bản sao Hợp đồng lao động 3. Thẻ luật sư"
CCCD_TEXT = "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số định danh cá nhân 048190005678 Họ và tên NGUYỄN THỊ LAN"

# Tên ô của eForm thật (bảng mapping 18/11/2026, field-key không bị Google Dịch), đúng loại control.
EFORM_COMPS = {
    "KinhGuiC": "x-select", "HoVaTenC": "x-input", "GioiTinhC": "x-select", "NgaySinhC": "x-date",
    "SoDienThoai": "x-input", "FaxC": "x-input", "EmailC": "x-input", "LoaiGiayToDinhDanhC": "x-select",
    "SoDinhDanhC": "x-input", "NgayCapDDC": "x-date", "NoiCapDDC": "x-input",
    "TT_SoNhaToDanPhoC": "x-input", "TT_TinhThanhC": "x-select", "TT_PhuongXaC": "x-select",
    "NO_SoNhaToDanPhoC": "x-input", "NO_TinhThanhC": "x-select", "NO_PhuongXaC": "x-select",
    "TheLuatSuSoC": "x-input", "NgayCapTheC": "x-input", "ThanhVienDoanC": "x-select",
    "CoQuan_HopDongC": "x-input", "CoQuan_DienThoaiC": "x-input", "CoQuan_FaxC": "x-input",
    "CoQuan_EmailC": "x-input", "CoQuan_WebsiteC": "x-input",
    "NoiLapC": "x-select", "Ngay": "x-input", "Thang": "x-input", "Nam": "x-input", "ChuKyNguoiDeNghiC": "x-input",
}

_HOME = {"quocGia": "Việt Nam", "tinh": "thành phố Đà Nẵng", "xa": "phường Hải Châu",
         "chiTietDuoiXa": "Số 7, kiệt 15 đường Lê Lợi"}


def _raw(*names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _files(*names):
    return [FileItem(name=n, type="application/pdf", dataUrl="data:,", role="") for n in names]


def _rows(items):
    return {item["componentIndex"]: item for item in items if item["target"] == "existing"}


def _compact(**values) -> list[dict]:
    return [{"name": name, "comp": "x-input", "value": value} for name, value in values.items()]


def _ui(fields: list[dict]) -> dict:
    return {f["name"]: f for f in fields}


def _facts(**extra) -> list[dict]:
    base = dict(
        KinhGui="Sở Tư pháp thành phố Đà Nẵng",
        Ls_HoTen="Nguyễn Thị Lan",
        Ls_GioiTinh="Nữ",
        Ls_NgaySinh="9/1/1990",
        Ls_SoDinhDanh="048 190 005 678",
        Ls_NgayCap="12/5/2021",
        Ls_NoiCap="CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
        Ls_DienThoai="0905 111 222",
        Ls_Fax="Không có",
        Ls_Email="lan.luatsu@example.com",
        Ls_ThuongTru=_HOME,
        CCCD_ThuongTru=_HOME,
        Ls_NoiOHienTai={"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Phường Hải Châu",
                        "chiTietDuoiXa": "Tầng 3, số 20 đường Bạch Đằng"},
        TheLuatSu={"so": "20481 / LS", "ngay": "3/3/2019"},
        TheLuatSu_Don={"so": "20481/LS", "ngay": "03/03/2019"},
        DoanLuatSu="Thành phố Đà Nẵng",
        ToChuc_HDLD={"ten": "CÔNG TY TNHH VÍ DỤ", "truSo": "Số 1 đường Trần Phú, phường Hải Châu, thành phố Đà Nẵng",
                     "dienThoai": "0236 3800 100", "fax": "0236 3800 101", "email": "phapche@vidu.example",
                     "website": "www.vidu.example"},
        ToChuc_Don={"ten": "Công ty TNHH Ví Dụ", "truSo": "Số 1 đường Trần Phú, phường Hải Châu, thành phố Đà Nẵng"},
        LamDon_NoiNgay={"diaDanh": "Đà Nẵng", "ngay": "5/11/2026"},
        NguoiKy="Nguyễn Thị Lan",
    )
    base.update(extra)
    return _compact(**base)


# ---------------------------------------------------------------- Registry / ke_khai_links

def test_registry_wires_key_from_ke_khai_links():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.002153"
    assert link["needsAgencySelect"] is True and link["selectSo"] is True
    procedure = registry.get_procedure(_KEY)
    assert procedure["label"] == link["label"]
    assert procedure["mode"] == "agent" and procedure["hasAttachmentStep"] is True
    assert procedure["supportsSplitDocuments"] is True
    assert "maThuTuc=1.002153" in procedure["detect"]["urlIncludes"]
    assert registry.get_attach_pipeline(_KEY) is attach.plan
    assert registry.get_pipeline(_KEY) is process_runner.run


# ---------------------------------------------------------------- Tờ khai eForm Mẫu TP-LS-05-sđ (process/mapper.py)

def test_o_ui_dung_ten_va_loai_control_eform_that():
    assert UI_COMP_BY_NAME == EFORM_COMPS
    fields, warnings = enrich(_facts(), {})
    # Fax luật sư ghi "Không có" → để trống; còn lại hồ sơ đủ giấy thì điền đủ ô.
    assert {f["name"] for f in fields} == set(EFORM_COMPS) - {"FaxC"}
    for field in fields:
        assert field["comp"] == EFORM_COMPS[field["name"]]
        assert field["value"] not in ("", None)
        assert "default" not in field, field["name"]
    assert warnings == []


def test_nhan_than_luat_su_va_giay_to_tuy_than():
    ui = _ui(enrich(_facts(), {})[0])
    assert ui["KinhGuiC"]["value"] == "Thành phố Đà Nẵng"
    assert ui["HoVaTenC"]["value"] == "NGUYỄN THỊ LAN"
    assert ui["GioiTinhC"]["value"] == "Nữ"
    assert ui["NgaySinhC"]["value"] == "09/01/1990"
    assert ui["SoDienThoai"]["value"] == "0905111222"
    assert ui["EmailC"]["value"] == "lan.luatsu@example.com"
    assert ui["LoaiGiayToDinhDanhC"]["value"] == "Căn cước công dân"
    assert ui["SoDinhDanhC"]["value"] == "048190005678"
    assert ui["NgayCapDDC"]["value"] == "12/05/2021"
    assert ui["NoiCapDDC"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"


def test_dia_chi_thuong_tru_va_noi_o_hien_tai_moi_dia_chi_ba_o():
    ui = _ui(enrich(_facts(), {})[0])
    assert (ui["TT_TinhThanhC"]["value"], ui["TT_PhuongXaC"]["value"], ui["TT_SoNhaToDanPhoC"]["value"]) == (
        "Thành phố Đà Nẵng", "Phường Hải Châu", "Số 7, kiệt 15 đường Lê Lợi")
    assert (ui["NO_TinhThanhC"]["value"], ui["NO_PhuongXaC"]["value"], ui["NO_SoNhaToDanPhoC"]["value"]) == (
        "Thành phố Đà Nẵng", "Phường Hải Châu", "Tầng 3, số 20 đường Bạch Đằng")


def test_don_khong_ghi_noi_o_hien_tai_thi_chep_thuong_tru_vien_vang():
    ui = _ui(enrich(_facts(Ls_NoiOHienTai=None), {})[0])
    assert ui["NO_SoNhaToDanPhoC"]["value"] == "Số 7, kiệt 15 đường Lê Lợi"
    assert all(ui[n]["default"] is True for n in ("NO_TinhThanhC", "NO_PhuongXaC", "NO_SoNhaToDanPhoC"))
    assert "default" not in ui["TT_PhuongXaC"]


def test_cccd_ghi_phuong_khac_thi_dien_theo_don_va_canh_bao():
    old = {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Phường Thanh Khê", "chiTietDuoiXa": "Số 7"}
    fields, warnings = enrich(_facts(CCCD_ThuongTru=old), {})
    assert _ui(fields)["TT_PhuongXaC"]["value"] == "Phường Hải Châu"
    assert any("Nơi thường trú lệch giữa Đơn" in w and "Thanh Khê" in w for w in warnings)


def test_khong_co_don_lay_noi_thuong_tru_tren_cccd():
    ui = _ui(enrich(_facts(Ls_ThuongTru=None), {})[0])
    assert ui["TT_PhuongXaC"]["value"] == "Phường Hải Châu"


def test_the_luat_su_doan_luat_su_va_ngay_cap_la_o_chu():
    ui = _ui(enrich(_facts(), {})[0])
    assert ui["TheLuatSuSoC"]["value"] == "20481/LS"
    assert ui["NgayCapTheC"] == {"name": "NgayCapTheC", "comp": "x-input", "value": "03/03/2019"}
    assert ui["ThanhVienDoanC"]["value"] == "Thành phố Đà Nẵng"


def test_the_luat_su_lech_voi_don_thi_theo_the_va_canh_bao():
    fields, warnings = enrich(_facts(TheLuatSu_Don={"so": "20418/LS", "ngay": "03/04/2019"}), {})
    assert _ui(fields)["TheLuatSuSoC"]["value"] == "20481/LS"
    assert sum("lệch giữa Thẻ" in w for w in warnings) == 2


def test_thieu_kinh_gui_lay_tinh_doan_luat_su_vien_vang():
    ui = _ui(enrich(_facts(KinhGui=None, LamDon_NoiNgay=None, NguoiKy=None), {})[0])
    assert ui["KinhGuiC"]["value"] == "Thành phố Đà Nẵng" and ui["KinhGuiC"]["default"] is True
    assert ui["NoiLapC"]["value"] == "Thành phố Đà Nẵng" and ui["NoiLapC"]["default"] is True
    assert ui["ChuKyNguoiDeNghiC"]["value"] == "Nguyễn Thị Lan" and ui["ChuKyNguoiDeNghiC"]["default"] is True
    assert "Ngay" not in ui


def test_doan_luat_su_ghi_kem_chu_doan():
    ui = _ui(enrich(_facts(DoanLuatSu="Đoàn Luật sư tỉnh Khánh Hòa"), {})[0])
    assert ui["ThanhVienDoanC"]["value"] == "Tỉnh Khánh Hòa"


def test_muc_2_to_chuc_gop_ten_dia_chi_theo_hdld_cach_viet_cua_don():
    ui = _ui(enrich(_facts(), {})[0])
    assert ui["CoQuan_HopDongC"]["value"] == (
        "Công ty TNHH Ví Dụ; địa chỉ: Số 1 đường Trần Phú, phường Hải Châu, thành phố Đà Nẵng")
    assert ui["CoQuan_DienThoaiC"]["value"] == "02363800100"
    assert ui["CoQuan_FaxC"]["value"] == "02363800101"
    assert ui["CoQuan_EmailC"]["value"] == "phapche@vidu.example"
    assert ui["CoQuan_WebsiteC"]["value"] == "www.vidu.example"


def test_khong_co_hdld_lay_muc_2_cua_don_va_ten_lech_thi_canh_bao():
    ui = _ui(enrich(_facts(ToChuc_HDLD=None), {})[0])
    assert ui["CoQuan_HopDongC"]["value"].startswith("Công ty TNHH Ví Dụ; địa chỉ:")
    assert "CoQuan_DienThoaiC" not in ui
    _, warnings = enrich(_facts(ToChuc_Don={"ten": "Công ty Cổ phần Khác"}), {})
    assert any("Tên tổ chức ký hợp đồng lao động lệch" in w for w in warnings)


def test_noi_lap_va_ngay_lap_don():
    ui = _ui(enrich(_facts(), {})[0])
    assert ui["NoiLapC"]["value"] == "Thành phố Đà Nẵng" and "default" not in ui["NoiLapC"]
    assert (ui["Ngay"]["value"], ui["Thang"]["value"], ui["Nam"]["value"]) == ("05", "11", "2026")
    assert ui["ChuKyNguoiDeNghiC"]["value"] == "Nguyễn Thị Lan"


def test_the_can_cuoc_cap_sau_01_7_2024_do_bo_cong_an_cap():
    ui = _ui(enrich(_facts(Ls_NgayCap="15/08/2024", Ls_NoiCap="Cục Cảnh sát QLHC về TTXH"), {})[0])
    assert ui["NoiCapDDC"]["value"] == "Bộ Công an"
    assert ui["LoaiGiayToDinhDanhC"]["value"] == "Thẻ căn cước"


def test_tai_khoan_khong_phai_luat_su_thi_canh_bao():
    _, warnings = enrich(_facts(), {"formContext": {"applicantFullname": "Trần Văn Khác"}})
    assert any("không phải luật sư đề nghị" in w for w in warnings)
    _, warnings = enrich(_facts(), {"formContext": {"applicantFullname": "NGUYỄN THỊ LAN",
                                                    "applicantIdentityNumber": "048190005678"}})
    assert warnings == []


def test_ho_so_rong_khong_bia_o_nao():
    fields, warnings = enrich([], {})
    assert fields == []
    assert any("họ tên luật sư" in w for w in warnings)
    assert any("số Thẻ luật sư" in w for w in warnings)
    assert any("cơ quan, tổ chức ký hợp đồng lao động" in w for w in warnings)


async def test_run_noi_mapper_va_gop_canh_bao(monkeypatch):
    captured = {}

    async def fake_run(files_by_role, **kwargs):
        captured.update(kwargs)
        return {"fields": _facts(TheLuatSu_Don={"so": "99999/LS"}), "errors": ["ocr: chậm"]}

    monkeypatch.setattr(process_runner.runner, "run", fake_run)
    res = await process_runner.run({"": []}, {})
    assert {f["name"] for f in res["fields"]} == set(EFORM_COMPS) - {"FaxC"}
    assert res["errors"][0] == "ocr: chậm" and any("99999/LS" in e for e in res["errors"][1:])
    assert "TheLuatSu" in captured["allowed"] and captured["comp_by_name"]["Ls_ThuongTru"] == "x-select-area"
    assert "TP-LS-05-sđ" in captured["extra_rules"]


# ---------------------------------------------------------------- Đính kèm — chế độ không tách

def test_rule_types_nhan_tieu_de_khong_nham_cau_nhac_lai():
    # Đơn nhắc "Thẻ luật sư số … do Liên đoàn Luật sư Việt Nam" và "ký hợp đồng lao động" → vẫn chỉ là Đơn.
    assert rule_types(APPLICATION_TEXT) == ["application"]
    assert rule_types(CONTRACT_TEXT) == ["labor_contract"]
    assert rule_types(CARD_TEXT) == ["lawyer_card"]
    assert rule_types(CERT_TEXT) == ["certificate"]
    assert rule_types(INDEX_TEXT) == ["dossier_index"]
    assert rule_types(CCCD_TEXT) == []


def test_the_luat_su_dinh_chung_dong_2_va_4_thieu_chung_chi_thi_canh_bao():
    items, classified, warnings = build_plan_items(
        _raw("don.pdf", "hdld.pdf", "the.png", "cccd.jpg"), {0: APPLICATION_TEXT, 1: CONTRACT_TEXT, 2: CARD_TEXT,
                                                             3: CCCD_TEXT})
    rows = _rows(items)
    assert {k: v["fileIndex"] for k, v in rows.items()} == {2: 2, 3: 1, 4: 2}
    assert all("sourceFileIndexes" not in item for item in items) and len(items) == 3
    assert rows[2]["componentName"] == "Bản sao Chứng chỉ hành nghề luật sư, bản sao Thẻ luật sư"
    assert rows[4]["componentName"] == "Bản sao Thẻ luật sư"
    assert len({item["documentName"] for item in items}) == 3
    assert classified[2]["componentIndexes"] == [2, 4]
    assert [c["target"] for c in classified] == ["skip", "existing", "existing", "skip"]
    assert warnings[0] == "Hồ sơ đã gửi không có Bản sao Chứng chỉ hành nghề luật sư (dòng 1, 2). Cần bổ sung."
    assert any("dòng 5" in w and "don.pdf" in w for w in warnings)
    assert any("cccd.jpg" in w for w in warnings)
    assert not any("Thẻ luật sư (dòng" in w or "Hợp đồng lao động ký kết" in w for w in warnings)


def test_co_chung_chi_thi_dong_1_va_dong_2_ghep_chung_chi_truoc_the():
    items, _, warnings = build_plan_items(
        _raw("the.png", "chung_chi.pdf", "hdld.pdf"), {0: CARD_TEXT, 1: CERT_TEXT, 2: CONTRACT_TEXT})
    rows = _rows(items)
    assert rows[1]["fileIndex"] == 1 and "sourceFileIndexes" not in rows[1]
    assert rows[2]["fileIndex"] == 1 and rows[2]["sourceFileIndexes"] == [1, 0]
    assert rows[4]["fileIndex"] == 0
    assert not any("Cần bổ sung" in w for w in warnings)


def test_tep_gop_ca_bo_dinh_nguyen_tep_vao_cac_dong():
    whole = APPLICATION_TEXT + " " + CONTRACT_TEXT + " " + CARD_TEXT
    items, classified, warnings = build_plan_items(_raw("hoso.pdf"), {0: whole})
    assert {k: v["fileIndex"] for k, v in _rows(items).items()} == {2: 0, 3: 0, 4: 0}
    assert classified[0]["componentIndexes"] == [2, 3, 4]
    assert not any("dòng 5" in w for w in warnings)
    assert any("đính nguyên tệp" in w for w in warnings)


def test_giay_la_them_thanh_phan_moi_theo_ten_llm():
    items, _, warnings = build_plan_items(
        _raw("hdld.pdf", "x.pdf"), {0: CONTRACT_TEXT, 1: "Giấy xác nhận"},
        {1: {"type": "other", "documentName": "Giấy xác nhận công tác"}})
    extra = [i for i in items if i["target"] == "new"]
    assert [(i["fileIndex"], i["componentName"]) for i in extra] == [(1, "Giấy xác nhận công tác")]
    assert any("thêm thành phần hồ sơ mới: x.pdf" in w for w in warnings)


def test_validated_classifications_bo_index_sai_va_chuan_hoa_type():
    out = validated_classifications(
        [{"fileIndex": 0, "type": "the_luat_su"}, {"fileIndex": 5, "type": "certificate"}, {"index": 1, "type": "lạ"},
         {"fileIndex": 0, "type": "certificate"}], 2)
    assert out == {0: {"type": "lawyer_card", "documentName": ""}, 1: {"type": "other", "documentName": ""}}


def test_khong_tach_chi_hoi_llm_tep_tieu_de_khong_nhan_ra(monkeypatch):
    texts = {"hdld.pdf": CONTRACT_TEXT, "the.jpg": "THẺ LUẬT SƯ Số 20481/LS Đoàn Luật sư thành phố Đà Nẵng"}
    asked = []

    async def fake_ocr(files, **_):
        return [{"text": texts[f["name"]]} for f in files]

    async def fake_classify(documents):
        asked.append([d["fileIndex"] for d in documents])
        return [{"fileIndex": 1, "type": "lawyer_card"}, {"fileIndex": 0, "type": "other"}]

    monkeypatch.setattr(khong_tach.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(khong_tach, "_classify_with_llm", fake_classify)
    out = asyncio.run(attach.plan(_files("hdld.pdf", "the.jpg"), {}))
    assert asked == [[1]]
    assert {k: v["fileIndex"] for k, v in _rows(out["attachments"]).items()} == {2: 1, 3: 0, 4: 1}
    assert out["extracted"]["attachmentMode"] == "preserve_files"


# ---------------------------------------------------------------- Đính kèm — chế độ tách

# Bộ hồ sơ dồn một PDF: danh mục (1–2), Đơn (3–4), HĐLĐ 3 trang + lời chứng (5–8), CCCD (9), Thẻ luật sư (10).
_PAGES = [
    "DANH MỤC GIẤY TỜ", "Bảng đối chiếu dữ liệu",
    "ĐƠN ĐỀ NGHỊ ĐĂNG KÝ HÀNH NGHỀ LUẬT SƯ VỚI TƯ CÁCH CÁ NHÂN", "Luật sư đề nghị (đã ký)",
    "HỢP ĐỒNG LAO ĐỘNG (Không xác định thời hạn) BÊN A – NGƯỜI SỬ DỤNG LAO ĐỘNG", "Điều 2", "Điều 6 chữ ký", "LỜI CHỨNG CHỨNG THỰC BẢN SAO ĐÚNG VỚI BẢN CHÍNH",
    "CĂN CƯỚC CÔNG DÂN mặt trước mặt sau", "THẺ LUẬT SƯ LAWYER CARD",
]
_OCR = "\n".join(f"───── Trang {i + 1}/{len(_PAGES)} ─────\n{t}" for i, t in enumerate(_PAGES))


def _patch_split(monkeypatch, documents):
    async def fake_ocr(files):
        return [{"text": _OCR} for _ in files]

    async def fake_chat(messages, max_tokens=None, **_):
        return json.dumps({"documents": documents})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tach.client, "chat", fake_chat)


def test_tach_file_dung_dong_va_khong_sot_trang(monkeypatch):
    _patch_split(monkeypatch, [
        {"fileIndex": 0, "pages": [1, 2], "docType": "dossier_index", "documentName": "Danh mục giấy tờ"},
        {"fileIndex": 0, "pages": [3, 4], "docType": "application", "documentName": "Đơn đề nghị"},
        # trang 8 (lời chứng) thuộc bản sao HĐLĐ liền trước.
        {"fileIndex": 0, "pages": [5, 6, 7, 8], "docType": "labor_contract", "documentName": "Hợp đồng lao động"},
        {"fileIndex": 0, "pages": [9], "docType": "identity", "documentName": "Căn cước công dân"},
        {"fileIndex": 0, "pages": [10], "docType": "lawyer_card", "documentName": "Thẻ luật sư"},
    ])
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    rows = _rows(res["attachments"])
    assert set(rows) == {2, 3, 4} and len(res["attachments"]) == 3
    assert rows[3]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [4, 5, 6, 7]}]
    # Thẻ luật sư: CÙNG đoạn trang đính vào dòng 2 và dòng 4.
    assert rows[2]["sourceSegments"] == rows[4]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [9]}]
    assert [s["docType"] for s in res["extracted"]["skipped"]] == ["dossier_index", "application", "identity"]
    attached = {p for item in res["attachments"] for s in item["sourceSegments"] for p in s["pageIndexes"]}
    skipped = {p for s in res["extracted"]["skipped"] for p in s["pages"]}
    assert attached | skipped == set(range(len(_PAGES))) and not attached & skipped
    assert any("dòng 5" in e and "hoso.pdf (trang 3, 4)" in e for e in res["errors"])
    assert any("Chứng chỉ hành nghề luật sư (dòng 1, 2). Cần bổ sung" in e for e in res["errors"])


def test_tach_tep_gon_mot_giay_thi_dinh_nguyen_tep():
    segments = [{"fileIndex": 0, "pages": [0], "doc": {"docType": "certificate"}},
                {"fileIndex": 1, "pages": [0], "doc": {"docType": "lawyer_card"}},
                {"fileIndex": 2, "pages": None, "doc": {}}]
    items, warnings, skipped = tach.build_split_items(["cc.pdf", "the.pdf", "anh.heic"], segments)
    rows = _rows(items)
    assert "sourceSegments" not in rows[2] and rows[2]["sourceFileIndexes"] == [0, 1]
    assert rows[1]["fileIndex"] == 0 and rows[4]["fileIndex"] == 1
    assert [(i["fileIndex"], i["target"]) for i in items if i["target"] == "new"] == [(2, "new")]
    assert skipped == []
    assert any("Hợp đồng lao động ký kết với cơ quan, tổ chức (dòng 3)" in w for w in warnings)


def test_tat_tach_thi_dinh_nguyen_tep(monkeypatch):
    _patch_split(monkeypatch, [])

    async def fake_classify(_documents):
        return [{"fileIndex": 0, "type": "other"}]

    monkeypatch.setattr(khong_tach, "_classify_with_llm", fake_classify)
    for options in ({}, {"splitDocuments": "true"}, None):
        res = asyncio.run(attach.plan(_files("hoso.pdf"), options))
        # Tệp gộp: tiêu đề đầu là Đơn, chứa HĐLĐ + Thẻ → đính nguyên tệp vào dòng 2, 3, 4.
        rows = _rows(res["attachments"])
        assert set(rows) == {2, 3, 4}
        assert all("sourceSegments" not in item for item in res["attachments"])


def test_tach_loi_quay_ve_khong_tach(monkeypatch):
    _patch_split(monkeypatch, [])

    async def boom(*_a, **_k):
        raise RuntimeError("llm hỏng")

    monkeypatch.setattr(tach.client, "chat", boom)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    assert set(_rows(res["attachments"])) == {2, 3, 4}
    assert all("sourceSegments" not in item for item in res["attachments"])
    assert res["errors"][0].startswith("attachment_agent (tách): llm hỏng")


# ---------------------------------------------------------------- Trợ lý người dân

def test_tro_ly_cung_key_chon_so_tach_giay_va_dien_to_khai():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review_registry
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    proc = handfree.get_procedure(_KEY)
    center = handfree.get_procedure("dang-ky-hoat-dong-trung-tam-tu-van-phap-luat")
    assert proc["mode"] == "agent" and proc["flowProfile"] == "tu-phap"
    assert proc["supportsSplitDocuments"] is True
    assert proc["keKhaiUrl"] == link["url"]
    assert proc["agencyProvinceOnly"] is True and proc["agencySoFirst"] is True
    assert proc["agencyDeptLabel"] == "Sở Tư pháp"
    assert proc["ownerInfo"]["enabled"] is True and proc["ownerInfo"] == center["ownerInfo"]
    assert "maThuTuc=1.002153" in proc["detect"]["urlIncludes"]
    assert handfree.get_attach_pipeline(_KEY) is registry.get_attach_pipeline(_KEY)
    assert handfree.get_pipeline(_KEY) is registry.get_pipeline(_KEY)
    assert handfree._HOAN_THIEN_THEO_TINH[_KEY] == handfree._TAT_CA
    assert "provinceOnly" not in proc
    assert _KEY in PROCEDURE_HINTS and _KEY in PROCEDURE_HMONG
    required = field_review_registry.get(_KEY)["required"]
    assert set(required) <= set(UI_COMP_BY_NAME)
    assert {"KinhGuiC", "HoVaTenC", "TT_PhuongXaC", "TheLuatSuSoC", "ThanhVienDoanC", "CoQuan_HopDongC",
            "ChuKyNguoiDeNghiC"} <= set(required)
    assert not {"SoDienThoai", "FaxC", "EmailC", "CoQuan_FaxC", "CoQuan_WebsiteC"} & set(required)
