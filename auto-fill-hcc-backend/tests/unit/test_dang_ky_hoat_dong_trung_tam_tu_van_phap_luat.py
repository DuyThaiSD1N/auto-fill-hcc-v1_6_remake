"""Pipeline "Đăng ký hoạt động của Trung tâm tư vấn pháp luật" (1.000627): mapper eForm Mẫu TP-TVPL-01-sđ + đính kèm
3 dòng (chế độ tách / không tách).

Dữ liệu trong test là ví dụ bịa (tên, số giấy tờ, cơ quan) — không lấy từ hồ sơ thật.
"""

import asyncio
import json

from app.pipelines.dang_ky_hoat_dong_trung_tam_tu_van_phap_luat.attach import planner as attach
from app.pipelines.dang_ky_hoat_dong_trung_tam_tu_van_phap_luat.attach.dinh_kem_khong_tach import planner as khong_tach
from app.pipelines.dang_ky_hoat_dong_trung_tam_tu_van_phap_luat.attach.dinh_kem_khong_tach.planner import (
    build_plan_items,
    rule_types,
    validated_classifications,
)
from app.pipelines.dang_ky_hoat_dong_trung_tam_tu_van_phap_luat.attach.dinh_kem_tach import planner as tach
from app.pipelines.dang_ky_hoat_dong_trung_tam_tu_van_phap_luat.process import runner as process_runner
from app.pipelines.dang_ky_hoat_dong_trung_tam_tu_van_phap_luat.process.mapper import enrich
from app.pipelines.dang_ky_hoat_dong_trung_tam_tu_van_phap_luat.process.schema import UI_COMP_BY_NAME
from app.process.schemas import FileItem
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.services import ocr

_KEY = "dang-ky-hoat-dong-trung-tam-tu-van-phap-luat"

APPLICATION_TEXT = (
    "Mẫu TP-TVPL-01-sđ CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM ĐƠN ĐĂNG KÝ HOẠT ĐỘNG CỦA TRUNG TÂM TƯ VẤN PHÁP LUẬT "
    "Kính gửi: Sở Tư pháp tỉnh Ninh Bình được thành lập theo Quyết định số: 07/QĐ-HLG ngày 02/10/2026 "
    "5. Danh sách tư vấn viên pháp luật, luật sư và nhân viên khác: Lê Văn Bình Giám đốc"
)
CHARTER_TEXT = (
    "DỰ THẢO QUY CHẾ Tổ chức và hoạt động của Trung tâm Tư vấn pháp luật Hội Luật gia tỉnh Ninh Bình "
    "Chương I NHỮNG QUY ĐỊNH CHUNG Điều 1. Tên gọi, địa chỉ trụ sở"
)
DECISION_TEXT = (
    "HỘI LUẬT GIA TỈNH NINH BÌNH Số: 07/QĐ-HLG QUYẾT ĐỊNH Về việc thành lập Trung tâm Tư vấn pháp luật Hội Luật gia "
    "tỉnh Ninh Bình ... QUYẾT ĐỊNH Về việc cử Giám đốc Trung tâm Tư vấn pháp luật Hội Luật gia tỉnh Ninh Bình "
    "Điều 2. ... theo Quy chế tổ chức, hoạt động của Trung tâm"
)
STAFF_TEXT = "DANH SÁCH KÈM THEO HỒ SƠ của người được đề nghị cấp Thẻ tư vấn viên pháp luật"
INDEX_TEXT = (
    "DANH MỤC HỒ SƠ đăng ký hoạt động 1. Đơn đăng ký hoạt động 2. Dự thảo Quy chế tổ chức, hoạt động "
    "3. Quyết định số 07/QĐ-HLG về việc thành lập Trung tâm Tư vấn pháp luật"
)
CCCD_TEXT = "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số định danh cá nhân 037080001234 Họ, chữ đệm và tên LÊ VĂN BÌNH"


def _raw(*names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _files(*names):
    return [FileItem(name=n, type="application/pdf", dataUrl="data:,", role="") for n in names]


def _rows(items):
    return {item["componentIndex"]: item for item in items if item["target"] == "existing"}


# ---------------------------------------------------------------- Registry / ke_khai_links

def test_registry_wires_key_from_ke_khai_links():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.000627"
    assert link["needsAgencySelect"] is True and link["selectSo"] is True
    procedure = registry.get_procedure(_KEY)
    assert procedure["label"] == link["label"]
    assert procedure["mode"] == "agent" and procedure["hasAttachmentStep"] is True
    assert procedure["supportsSplitDocuments"] is True
    assert "maThuTuc=1.000627" in procedure["detect"]["urlIncludes"]
    assert registry.get_attach_pipeline(_KEY) is attach.plan
    assert registry.get_pipeline(_KEY) is process_runner.run


def test_ba_link_tu_phap_duoc_them_cung_dot_chon_so():
    by_code = {item.get("code"): item for item in KE_KHAI_LINKS}
    for code, key in (("1.000627", _KEY), ("1.002153", "dang-ky-hanh-nghe-luat-su-voi-tu-cach-ca-nhan"),
                      ("1.014076", "cap-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te")):
        link = next(item for item in KE_KHAI_LINKS if item["key"] == key)
        assert link["code"] == code and link["selectSo"] is True and link["needsAgencySelect"] is True
        assert "provinceOnly" not in link
    assert by_code["1.000627"]["url"].endswith("019d2bfd-3fa9-7372-90fd-8901c2e22177")


# ---------------------------------------------------------------- Tờ khai eForm Mẫu TP-TVPL-01-sđ (process/mapper.py)

# Tên ô của eForm thật (bảng mapping 18/11/2026), đúng loại control.
EFORM_COMPS = {
    "KinhGui": "x-input", "TTTVPL": "x-input", "Quyetdinhso": "x-input", "Ngay2": "x-date", "TTTVPL2": "x-input",
    "Tendaydu": "x-input", "Tenviettat": "x-input", "DCTS_Tinh": "x-select", "DCTS_Xa": "x-select",
    "Diachitruso": "x-input", "DienthoaiC": "x-input", "FaxC": "x-input", "EmailC": "x-input", "Hovaten": "x-input",
    "Gioitinh": "x-select", "Ngaythangnam": "x-date", "Quoctich": "x-select", "LoaiGiayToDinhDanhC": "x-select",
    "Sothe": "x-input", "Ngaythangnam1": "x-date", "Noicap": "x-input", "Thetuvanvien": "x-input",
    "Capngay": "x-date", "Chungchi": "x-input", "Capngay1": "x-date", "Theluatsu": "x-input", "Capngay2": "x-date",
    "Phamvihoatdong": "x-input", "Hovaten1": "x-input", "Chucdanh": "x-input", "Hovaten2": "x-input",
    "Chucdanh1": "x-input", "Hovaten3": "x-input", "Chucdanh2": "x-input", "TinhThanhPho": "x-select",
    "Ngay1": "x-input", "Thang": "x-input", "Nam": "x-input", "Chuky": "x-input",
}


def _compact(**values) -> list[dict]:
    return [{"name": name, "comp": "x-input", "value": value} for name, value in values.items()]


def _ui(fields: list[dict]) -> dict:
    return {f["name"]: f for f in fields}


def _facts(**extra) -> list[dict]:
    base = dict(
        KinhGui="Sở Tư pháp tỉnh Ninh Bình",
        TT_TenDayDu="Trung tâm Tư vấn pháp luật Hội Luật gia tỉnh Ninh Bình",
        TT_TenVietTat="TTTVPL HLG NB",
        QD_ThanhLap={"so": "Số: 07 / QĐ-HLG", "ngay": "2/10/2026", "coQuan": "Ban Thường vụ Hội Luật gia tỉnh Ninh Bình"},
        DK_QuyetDinh={"so": "07/QĐ-HLG", "ngay": "02/10/2026", "coQuan": "Ban Thường vụ Hội Luật gia tỉnh Ninh Bình"},
        TT_TruSo={"quocGia": "Việt Nam", "tinh": "tỉnh Ninh Bình", "xa": "phường Hoa Lư",
                  "chiTietDuoiXa": "Số 3, đường Trần Hưng Đạo"},
        TT_DienThoai="0229 3123 456",
        TT_Fax="0229 3123 457",
        TT_Email="tvpl.nb@example.com",
        GD_HoTen="Lê Văn Bình",
        GD_GioiTinh="Nam",
        GD_NgaySinh="5/6/1980",
        GD_QuocTich="Việt Nam",
        GD_SoDinhDanh="037 080 001 234",
        GD_NgayCap="20/8/2021",
        GD_NoiCap="Cục Cảnh sát quản lý hành chính về trật tự xã hội (đối với Số thẻ căn cước công dân)",
        GD_TheTuVanVien={"so": "01/TVV", "ngay": "1/2/2015"},
        GD_ChungChiLuatSu={"so": "9876/TP/LS-CCHN", "ngay": "10/06/2012"},
        GD_TheLuatSu={"so": "5432/LS", "ngay": "05/09/2012"},
        PhamViHoatDong="- Hướng dẫn, giải đáp pháp luật;\n- Lĩnh vực: dân sự, đất đai.",
        NhanSu=[{"hoTen": "Lê Văn Bình", "chucDanh": "Giám đốc, luật sư"},
                {"hoTen": "Phạm Thị Cúc", "chucDanh": "Phó Giám đốc, tư vấn viên PL"},
                {"hoTen": "Đỗ Minh Đức", "chucDanh": "Luật sư (hợp đồng lao động)"}],
        LamDon_NoiNgay={"diaDanh": "Ninh Bình", "ngay": "9/11/2026"},
        NguoiKy="Lê Văn Bình",
    )
    base.update(extra)
    return _compact(**base)


def test_o_ui_dung_ten_va_loai_control_eform_that():
    assert UI_COMP_BY_NAME == EFORM_COMPS
    fields, warnings = enrich(_facts(), {})
    assert {f["name"] for f in fields} == set(EFORM_COMPS), "hồ sơ đủ giấy thì điền đủ 39 ô của eForm"
    for field in fields:
        assert field["comp"] == EFORM_COMPS[field["name"]]
        assert field["value"] not in ("", None)
    assert warnings == []


def test_dau_don_va_muc_1_2_trung_tam():
    ui = _ui(enrich(_facts(), {})[0])
    assert ui["KinhGui"]["value"] == "Sở Tư pháp tỉnh Ninh Bình" and "default" not in ui["KinhGui"]
    assert ui["TTTVPL"]["value"] == "Trung tâm Tư vấn pháp luật Hội Luật gia tỉnh Ninh Bình"
    assert ui["Quyetdinhso"]["value"] == "07/QĐ-HLG"
    assert ui["Ngay2"]["value"] == "02/10/2026"
    # TTTVPL2 là tổ chức chủ quản ban hành quyết định, không phải tên Trung tâm.
    assert ui["TTTVPL2"]["value"] == "Ban Thường vụ Hội Luật gia tỉnh Ninh Bình"
    assert ui["Tendaydu"]["value"] == "TRUNG TÂM TƯ VẤN PHÁP LUẬT HỘI LUẬT GIA TỈNH NINH BÌNH"
    assert ui["DCTS_Tinh"]["value"] == "Tỉnh Ninh Bình"
    assert ui["DCTS_Xa"]["value"] == "Phường Hoa Lư"
    assert ui["Diachitruso"]["value"] == "Số 3, đường Trần Hưng Đạo"
    assert ui["DienthoaiC"]["value"] == "02293123456"
    assert ui["EmailC"]["value"] == "tvpl.nb@example.com"


def test_muc_3_giam_doc():
    ui = _ui(enrich(_facts(), {})[0])
    assert ui["Hovaten"]["value"] == "LÊ VĂN BÌNH"
    assert ui["Gioitinh"]["value"] == "Nam"
    assert ui["Ngaythangnam"]["value"] == "05/06/1980"
    assert ui["Quoctich"]["value"] == "Việt Nam"
    assert ui["LoaiGiayToDinhDanhC"]["value"] == "Căn cước công dân"
    assert ui["Sothe"]["value"] == "037080001234"
    assert ui["Ngaythangnam1"]["value"] == "20/08/2021"
    assert ui["Noicap"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert (ui["Thetuvanvien"]["value"], ui["Capngay"]["value"]) == ("01/TVV", "01/02/2015")
    assert (ui["Chungchi"]["value"], ui["Capngay1"]["value"]) == ("9876/TP/LS-CCHN", "10/06/2012")
    assert (ui["Theluatsu"]["value"], ui["Capngay2"]["value"]) == ("5432/LS", "05/09/2012")


def test_muc_4_5_va_noi_ngay_ky():
    ui = _ui(enrich(_facts(), {})[0])
    assert ui["Phamvihoatdong"]["value"] == "- Hướng dẫn, giải đáp pháp luật; - Lĩnh vực: dân sự, đất đai."
    assert [(ui[n]["value"], ui[t]["value"]) for n, t in (("Hovaten1", "Chucdanh"), ("Hovaten2", "Chucdanh1"),
                                                           ("Hovaten3", "Chucdanh2"))] == [
        ("Lê Văn Bình", "Giám đốc, luật sư"), ("Phạm Thị Cúc", "Phó Giám đốc, tư vấn viên PL"),
        ("Đỗ Minh Đức", "Luật sư (hợp đồng lao động)")]
    assert ui["TinhThanhPho"]["value"] == "Tỉnh Ninh Bình" and "default" not in ui["TinhThanhPho"]
    assert (ui["Ngay1"]["value"], ui["Thang"]["value"], ui["Nam"]["value"]) == ("09", "11", "2026")
    assert ui["Chuky"]["value"] == "Lê Văn Bình"


def test_o_don_ghi_khong_thi_de_trong():
    fields, warnings = enrich(_facts(TT_TenVietTat="Không", TT_Fax="không", GD_TheTuVanVien={"so": "Không có"}), {})
    names = {f["name"] for f in fields}
    assert not names & {"Tenviettat", "FaxC", "Thetuvanvien", "Capngay"}
    assert warnings == []  # Giám đốc là luật sư → không cần thẻ tư vấn viên


def test_giam_doc_khong_co_the_tvv_lan_chung_chi_thi_canh_bao():
    _, warnings = enrich(_facts(GD_TheTuVanVien=None, GD_ChungChiLuatSu=None), {})
    assert any("Thẻ tư vấn viên pháp luật hoặc Chứng chỉ hành nghề luật sư" in w for w in warnings)


def test_don_nhieu_hon_3_nguoi_dien_3_dong_va_canh_bao_nguoi_con_lai():
    staff = [{"hoTen": f"Người {i}", "chucDanh": f"Chức {i}"} for i in range(1, 6)]
    fields, warnings = enrich(_facts(NhanSu=staff), {})
    ui = _ui(fields)
    assert ui["Hovaten3"]["value"] == "Người 3" and "Hovaten4" not in ui
    assert any("chỉ có 3 dòng" in w and "Người 4 – Chức 4; Người 5 – Chức 5" in w for w in warnings)


def test_hai_nguon_quyet_dinh_lech_thi_canh_bao_va_theo_quyet_dinh():
    fields, warnings = enrich(_facts(DK_QuyetDinh={"so": "70/QĐ-HLG", "ngay": "03/10/2026"}), {})
    ui = _ui(fields)
    assert (ui["Quyetdinhso"]["value"], ui["Ngay2"]["value"]) == ("07/QĐ-HLG", "02/10/2026")
    assert sum("lệch giữa Quyết định" in w for w in warnings) == 2


def test_khong_co_quyet_dinh_lay_theo_don():
    ui = _ui(enrich(_facts(QD_ThanhLap=None), {})[0])
    assert (ui["Quyetdinhso"]["value"], ui["Ngay2"]["value"]) == ("07/QĐ-HLG", "02/10/2026")
    assert ui["TTTVPL2"]["value"] == "Ban Thường vụ Hội Luật gia tỉnh Ninh Bình"


def test_khong_co_don_dung_mac_dinh_vien_vang():
    fields, warnings = enrich(_facts(KinhGui=None, NhanSu=None, LamDon_NoiNgay=None, NguoiKy=None, DK_QuyetDinh=None), {})
    ui = _ui(fields)
    assert ui["KinhGui"]["value"] == "Sở Tư pháp tỉnh Ninh Bình" and ui["KinhGui"]["default"] is True
    assert (ui["Hovaten1"]["value"], ui["Chucdanh"]["value"]) == ("Lê Văn Bình", "Giám đốc")
    assert ui["Hovaten1"]["default"] is True and "Hovaten2" not in ui
    assert ui["TinhThanhPho"]["value"] == "Tỉnh Ninh Bình" and ui["TinhThanhPho"]["default"] is True
    assert ui["Chuky"]["value"] == "Lê Văn Bình" and ui["Chuky"]["default"] is True
    assert "Ngay1" not in ui
    assert warnings == []


def test_the_can_cuoc_cap_sau_01_7_2024_do_bo_cong_an_cap():
    ui = _ui(enrich(_facts(GD_NgayCap="15/08/2024", GD_NoiCap="Cục Cảnh sát QLHC về TTXH"), {})[0])
    assert ui["Noicap"]["value"] == "Bộ Công an"
    assert ui["LoaiGiayToDinhDanhC"]["value"] == "Thẻ căn cước"


def test_tai_khoan_khong_phai_giam_doc_thi_canh_bao():
    _, warnings = enrich(_facts(), {"formContext": {"applicantFullname": "Trần Văn Khác"}})
    assert any("không phải Giám đốc Trung tâm" in w for w in warnings)
    _, warnings = enrich(_facts(), {"formContext": {"applicantFullname": "LÊ VĂN BÌNH",
                                                    "applicantIdentityNumber": "037080001234"}})
    assert warnings == []


def test_ho_so_rong_khong_bia_o_nao():
    fields, warnings = enrich([], {})
    assert fields == []
    assert any("số quyết định thành lập" in w for w in warnings)
    assert any("họ tên Giám đốc" in w for w in warnings)


async def test_run_noi_mapper_va_gop_canh_bao(monkeypatch):
    captured = {}

    async def fake_run(files_by_role, **kwargs):
        captured.update(kwargs)
        return {"fields": _facts(DK_QuyetDinh={"so": "99/QĐ-HLG", "ngay": "02/10/2026"}), "errors": ["ocr: chậm"]}

    monkeypatch.setattr(process_runner.runner, "run", fake_run)
    res = await process_runner.run({"": []}, {})
    assert {f["name"] for f in res["fields"]} == set(EFORM_COMPS)
    assert res["errors"][0] == "ocr: chậm" and any("99/QĐ-HLG" in e for e in res["errors"][1:])
    assert "QD_ThanhLap" in captured["allowed"] and captured["comp_by_name"]["TT_TruSo"] == "x-select-area"
    assert "TP-TVPL-01-sđ" in captured["extra_rules"]


# ---------------------------------------------------------------- Đính kèm — chế độ không tách

def test_rule_types_nhan_tieu_de_khong_nham_cau_nhac_lai():
    assert rule_types(APPLICATION_TEXT) == ["application"]
    assert rule_types(CHARTER_TEXT) == ["charter"]
    # Quyết định cử Giám đốc nhắc "Quy chế tổ chức, hoạt động của Trung tâm" → không nhận nhầm thành Quy chế.
    assert rule_types(DECISION_TEXT) == ["decision"]
    assert rule_types(STAFF_TEXT) == ["staff_list"]
    assert rule_types(INDEX_TEXT)[0] == "dossier_index"
    assert rule_types(CCCD_TEXT) == []


def test_du_giay_vao_dung_3_dong_don_danh_muc_cccd_khong_dinh():
    items, classified, warnings = build_plan_items(
        _raw("ds.pdf", "qc.pdf", "qd.pdf", "don.pdf", "dm.pdf", "cccd.jpg"),
        {0: STAFF_TEXT, 1: CHARTER_TEXT, 2: DECISION_TEXT, 3: APPLICATION_TEXT, 4: INDEX_TEXT, 5: CCCD_TEXT})
    rows = _rows(items)
    assert {k: v["fileIndex"] for k, v in rows.items()} == {1: 0, 2: 1, 3: 2}
    assert all(not item["needsAddComponent"] for item in items) and len(items) == 3
    assert rows[3]["componentName"].startswith("Quyết định của tổ chức chủ quản")
    assert [c["target"] for c in classified] == ["existing"] * 3 + ["skip"] * 3
    assert len(warnings) == 3
    assert "dòng 4" in warnings[0] and "don.pdf" in warnings[0]
    assert "Danh mục hồ sơ" in warnings[1] and "dm.pdf" in warnings[1]
    assert "cccd.jpg" in warnings[2]


def test_nhieu_tep_cung_dong_gop_mot_pdf_va_thieu_dong_thi_canh_bao():
    items, _, warnings = build_plan_items(
        _raw("qd_thanh_lap.pdf", "qd_cu_gd.pdf", "don.pdf"), {0: DECISION_TEXT, 1: DECISION_TEXT, 2: APPLICATION_TEXT})
    rows = _rows(items)
    assert rows[3]["sourceFileIndexes"] == [0, 1]
    assert sum("Cần bổ sung" in w for w in warnings) == 2  # thiếu danh sách (dòng 1) + Quy chế (dòng 2)


def test_tep_gop_ca_bo_dinh_nguyen_tep_vao_dong_thieu_danh_muc_khong_tinh():
    whole = APPLICATION_TEXT + " " + CHARTER_TEXT + " " + DECISION_TEXT
    items, classified, warnings = build_plan_items(_raw("hoso.pdf", "dm.pdf"), {0: whole, 1: INDEX_TEXT})
    rows = _rows(items)
    assert {k: v["fileIndex"] for k, v in rows.items()} == {2: 0, 3: 0}
    assert classified[0]["componentIndexes"] == [2, 3]
    # Tệp gộp đã đính vào dòng → không báo "không đính" cho Đơn; Danh mục (nhắc tên mọi giấy) không bị kéo vào dòng.
    assert not any("dòng 4" in w for w in warnings)
    assert any("Danh mục hồ sơ" in w for w in warnings)


def test_giay_la_them_thanh_phan_moi_theo_ten_llm():
    items, _, warnings = build_plan_items(
        _raw("qd.pdf", "x.pdf"), {0: DECISION_TEXT, 1: "Biên bản họp"},
        {1: {"type": "other", "documentName": "Biên bản họp Ban Thường vụ"}})
    extra = [i for i in items if i["target"] == "new"]
    assert [(i["fileIndex"], i["componentName"]) for i in extra] == [(1, "Biên bản họp Ban Thường vụ")]
    assert any("thêm thành phần hồ sơ mới: x.pdf" in w for w in warnings)


def test_validated_classifications_bo_index_sai_va_chuan_hoa_type():
    out = validated_classifications(
        [{"fileIndex": 0, "type": "quy_che"}, {"fileIndex": 5, "type": "decision"}, {"index": 1, "type": "lạ"},
         {"fileIndex": 0, "type": "decision"}], 2)
    assert out == {0: {"type": "charter", "documentName": ""}, 1: {"type": "other", "documentName": ""}}


def test_khong_tach_chi_hoi_llm_tep_tieu_de_khong_nhan_ra(monkeypatch):
    texts = {"qd.pdf": DECISION_TEXT, "the_ls.pdf": "THẺ LUẬT SƯ Số 5432/LS"}
    asked = []

    async def fake_ocr(files, **_):
        return [{"text": texts[f["name"]]} for f in files]

    async def fake_classify(documents):
        asked.append([d["fileIndex"] for d in documents])
        return [{"fileIndex": 1, "type": "staff_list"}, {"fileIndex": 0, "type": "other"}]

    monkeypatch.setattr(khong_tach.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(khong_tach, "_classify_with_llm", fake_classify)
    out = asyncio.run(attach.plan(_files("qd.pdf", "the_ls.pdf"), {}))
    assert asked == [[1]]
    assert {k: v["fileIndex"] for k, v in _rows(out["attachments"]).items()} == {1: 1, 3: 0}
    assert out["extracted"]["attachmentMode"] == "preserve_files"


# ---------------------------------------------------------------- Đính kèm — chế độ tách

_PAGES = [
    "ĐƠN ĐĂNG KÝ HOẠT ĐỘNG CỦA TRUNG TÂM TƯ VẤN PHÁP LUẬT", "5. Danh sách ... Ghi chú",
    "QUY CHẾ Tổ chức và hoạt động của Trung tâm Tư vấn pháp luật", "Chương II", "Chương IV", "Chương VI",
    "QUYẾT ĐỊNH Về việc thành lập Trung tâm Tư vấn pháp luật", "Điều 2. Nơi nhận",
    "QUYẾT ĐỊNH Về việc cử Giám đốc Trung tâm Tư vấn pháp luật", "Điều 3. Nơi nhận",
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
        {"fileIndex": 0, "pages": [1, 2], "docType": "application", "documentName": "Đơn đăng ký hoạt động"},
        {"fileIndex": 0, "pages": [3, 4, 5, 6], "docType": "charter", "documentName": "Dự thảo Quy chế"},
        {"fileIndex": 0, "pages": [7, 8], "docType": "decision", "documentName": "Quyết định thành lập"},
        # trang 10 (Nơi nhận) LLM bỏ sót → gộp vào giấy liền trước, không mất trang.
        {"fileIndex": 0, "pages": [9], "docType": "decision", "documentName": "Quyết định cử Giám đốc"},
    ])
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    rows = _rows(res["attachments"])
    assert set(rows) == {2, 3} and len(res["attachments"]) == 2
    assert rows[2]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [2, 3, 4, 5]}]
    # Hai quyết định chung MỘT thành phần (dòng 3): extension ghép hai đoạn thành một PDF.
    assert rows[3]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [6, 7]},
                                         {"fileIndex": 0, "pageIndexes": [8, 9]}]
    assert res["extracted"]["skipped"] == [{"fileIndex": 0, "pages": [0, 1], "docType": "application"}]
    attached = {p for item in res["attachments"] for s in item["sourceSegments"] for p in s["pageIndexes"]}
    skipped = {p for s in res["extracted"]["skipped"] for p in s["pages"]}
    assert attached | skipped == set(range(len(_PAGES))) and not attached & skipped
    assert any("dòng 4" in e and "hoso.pdf (trang 1, 2)" in e for e in res["errors"])
    assert any("(dòng 1). Cần bổ sung" in e for e in res["errors"])


def test_tach_tep_gon_mot_giay_thi_dinh_nguyen_tep():
    segments = [{"fileIndex": 0, "pages": [0, 1], "doc": {"docType": "decision"}},
                {"fileIndex": 1, "pages": [0], "doc": {"docType": "decision"}},
                {"fileIndex": 2, "pages": None, "doc": {}}]
    items, warnings, skipped = tach.build_split_items(["qd1.pdf", "qd2.pdf", "anh.heic"], segments)
    rows = _rows(items)
    assert "sourceSegments" not in rows[3] and rows[3]["sourceFileIndexes"] == [0, 1]
    assert [(i["fileIndex"], i["target"]) for i in items if i["target"] == "new"] == [(2, "new")]
    assert skipped == []


def test_tat_tach_thi_dinh_nguyen_tep(monkeypatch):
    _patch_split(monkeypatch, [])

    async def fake_classify(_documents):
        return [{"fileIndex": 0, "type": "decision"}]

    monkeypatch.setattr(khong_tach, "_classify_with_llm", fake_classify)
    for options in ({}, {"splitDocuments": "true"}, None):
        res = asyncio.run(attach.plan(_files("hoso.pdf"), options))
        # Tệp gộp: tiêu đề đầu là Đơn, chứa Quy chế + quyết định → đính nguyên tệp vào dòng 2 và 3.
        rows = _rows(res["attachments"])
        assert set(rows) == {2, 3}
        assert all("sourceSegments" not in item for item in res["attachments"])


def test_tach_loi_quay_ve_khong_tach(monkeypatch):
    _patch_split(monkeypatch, [])

    async def boom(*_a, **_k):
        raise RuntimeError("llm hỏng")

    monkeypatch.setattr(tach.client, "chat", boom)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    assert set(_rows(res["attachments"])) == {2, 3}
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
    lawyer = handfree.get_procedure("dang-ky-tham-du-kiem-tra-ket-qua-tap-su-hanh-nghe-cong-chung")
    assert proc["mode"] == "agent" and proc["flowProfile"] == "tu-phap"
    assert proc["supportsSplitDocuments"] is True
    assert proc["keKhaiUrl"] == link["url"]
    assert proc["agencyProvinceOnly"] is True and proc["agencySoFirst"] is True
    assert proc["agencyDeptLabel"] == "Sở Tư pháp"
    assert proc["ownerInfo"]["enabled"] is True and proc["ownerInfo"] == lawyer["ownerInfo"]
    assert "maThuTuc=1.000627" in proc["detect"]["urlIncludes"]
    assert handfree.get_attach_pipeline(_KEY) is registry.get_attach_pipeline(_KEY)
    assert handfree.get_pipeline(_KEY) is registry.get_pipeline(_KEY)
    assert handfree._HOAN_THIEN_THEO_TINH[_KEY] == handfree._TAT_CA
    assert "provinceOnly" not in proc
    assert _KEY in PROCEDURE_HINTS and _KEY in PROCEDURE_HMONG
    required = field_review_registry.get(_KEY)["required"]
    assert set(required) <= set(UI_COMP_BY_NAME)
    assert {"Hovaten", "Quyetdinhso", "TTTVPL2", "DCTS_Tinh", "Phamvihoatdong", "Chuky"} <= set(required)
    assert not {"Tenviettat", "FaxC", "EmailC", "Thetuvanvien", "Chungchi", "Theluatsu"} & set(required)
