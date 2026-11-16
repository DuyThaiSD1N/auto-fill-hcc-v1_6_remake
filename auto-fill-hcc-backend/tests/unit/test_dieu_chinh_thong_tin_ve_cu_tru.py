"""Điều chỉnh thông tin về cư trú (1.010039, Cổng DVC Bộ Công an): mapper ô form, nhận diện trang dùng chung với
đăng ký thường trú, đính kèm tách / không tách, luồng trợ lý."""
import asyncio
import json

from app.channels.handfree.chat import flow
from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.attach import planner as attach
from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.attach.dinh_kem_khong_tach import planner as khong_tach
from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.attach.dinh_kem_khong_tach.planner import ROWS
from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.attach.dinh_kem_tach import planner as tach
from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.process import mapper
from app.process.schemas import FileItem
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls
from app.services import ocr

KEY = "dieu-chinh-thong-tin-ve-cu-tru"
PERSON = {
    "CoQuan_Tinh": "Tỉnh Lai Châu", "CoQuan_Xa": "Phường Đoàn Kết",
    "NguoiDeNghi_HoTen": "Nguyen Van B", "NguoiDeNghi_NgaySinh": "4/9/1990", "NguoiDeNghi_GioiTinh": "Nam",
    "NguoiDeNghi_SoDinhDanh": "0120 9000 0002", "NguoiDeNghi_SoDienThoai": "0912 000 111",
    "ChuHo_HoTen": "Nguyen Van A", "ChuHo_QuanHe": "Con", "ChuHo_SoDinhDanh": "012060000001",
    "NoiDungDeNghi": "Đề nghị điều chỉnh chủ hộ do chủ hộ đã chết",
    "ThanhVien": [
        {"hoTen": "Tran Thi C", "ngaySinh": "1/2/1962", "gioiTinh": "Nữ", "soDinhDanh": "012162000003",
         "quanHeVoiChuHo": "Mẹ"},
        # LLM chép nhầm người đề nghị vào bảng → bỏ theo số định danh.
        {"hoTen": "Nguyen Van B", "ngaySinh": "4/9/1990", "soDinhDanh": "012090000002", "quanHeVoiChuHo": "Chủ hộ"},
        {"hoTen": "Nguyen Gia D", "ngaySinh": "5/5/2016", "soDinhDanh": "012216000004", "quanHeVoiChuHo": "Con"},
    ],
}


def _enrich(values: dict, options=None) -> list[dict]:
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def test_thu_tu_va_gia_tri_o_form():
    out = _enrich(PERSON)
    by = {f["name"]: f for f in out}
    names = [f["name"] for f in out]
    assert names[:2] == ["cboORG", "cboBPROC_CASE_CODE"]
    assert names.index("cboFORMAT_DATE") < names.index("txtBIRTH_DATE") < names.index("txtFULLNAME")
    assert by["cboORG"]["value"] == {"province": "Tỉnh Lai Châu", "ward": "Phường Đoàn Kết",
                                     "cityId": "cboRECEIVE_ADDR_CITY_ID", "wardId": "cboRECEIVE_ADDR_VILLAGE_ID",
                                     "readySelect": "cboBPROC_CASE_CODE"}
    assert by["cboORG"]["onlyIfEmpty"] is True
    assert by["cboBPROC_CASE_CODE"]["value"] == "Thay đổi chủ hộ"
    assert by["txtFULLNAME"]["value"] == "NGUYEN VAN B" and by["txtID_CARD_NUMBER"]["value"] == "012090000002"
    assert by["txtBIRTH_DATE"]["value"] == "04/09/1990" and by["cboFORMAT_DATE"]["value"] == "Ngày tháng năm"
    assert by["txtPHONE_NUMBER"]["value"] == "0912000111"
    # Khối chủ hộ = chủ hộ hiện tại (chủ hộ cũ), luôn điền.
    assert by["txtHH_HEAD_FULLNAME"]["value"] == "NGUYEN VAN A"
    assert by["cboRELATIONSHIP_WITH_HHHEAD_ID"]["value"] == "Con"
    assert by["txtID_CARD_NUMBER_HHEAD"]["value"] == "012060000001"
    assert by["txtCHANGED_CONTENT_NOTE"]["value"] == "Đề nghị điều chỉnh chủ hộ do chủ hộ đã chết"
    # Không có ô của đăng ký thường trú mà thủ tục này ẩn.
    assert not {"radIsHouseHold", "txtSUGGEST_DETAIL_ADDR"} & set(by)
    rows = by["tblNguoi_CUNGTD"]["value"]["rows"]
    assert [{c["id"]: c["value"] for c in row} for row in rows] == [
        {"txtFULLNAME_CUNGTD0": "TRAN THI C", "txtDOB_CUNGTD0": "01/02/1962", "cboGENDER_CUNGTD0": "Nữ",
         "txtIDENTIFIER_NOCARD_NUMBER_CUNGTD0": "012162000003", "cboRELATIONSHIP_CHUHO_CUNGTD0": "Mẹ"},
        {"txtFULLNAME_CUNGTD1": "NGUYEN GIA D", "txtDOB_CUNGTD1": "05/05/2016", "cboGENDER_CUNGTD1": "Nam",
         "txtIDENTIFIER_NOCARD_NUMBER_CUNGTD1": "012216000004", "cboRELATIONSHIP_CHUHO_CUNGTD1": "Con"},
    ]


def test_giay_khong_ghi_co_quan_thi_lay_xa_tai_khoan_to_vang():
    values = {k: v for k, v in PERSON.items() if not k.startswith("CoQuan_")}
    options = mapper.with_account_process_options({}, {"tinh": "Tỉnh Mẫu", "xa": "Phường Mẫu"}, KEY)
    agency = next(f for f in _enrich(values, options) if f["name"] == "cboORG")
    assert agency["value"]["ward"] == "Phường Mẫu" and agency["default"] is True
    # Thủ tục khác không nhận cờ của thủ tục này.
    assert "_accountAgency" not in mapper.with_account_process_options({}, {"tinh": "T", "xa": "X"}, "khac")


def _detect(url: str) -> str:
    """Bước khớp URL của popup.js: rule urlIncludes đầu tiên (đúng urlScope) thắng, so trên URL đã lower-case."""
    url = url.lower()
    for proc in with_ke_khai_detect_urls(registry.PROCEDURES):
        detect = proc.get("detect") or {}
        scope = detect.get("urlScope") or []
        if scope and not any(s and s.lower() in url for s in scope):
            continue
        if any(u and u.lower() in url for u in detect.get("urlIncludes") or []):
            return proc["key"]
    return ""


def test_link_registry_va_nhan_dien_trang_chung_voi_thuong_tru():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.010039"
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    assert registry.get_procedure(KEY)["supportsSplitDocuments"] is True
    # Cùng trang dang-ky-thuong-tru.html: TT=THUONGTRU_08 → thủ tục này, TT=THUONGTRU_01 vẫn là đăng ký thường trú.
    assert _detect(link["url"]) == KEY
    thuong_tru = next(item for item in KE_KHAI_LINKS if item["key"] == "dang-ky-thuong-tru")
    assert _detect(thuong_tru["url"]) == "dang-ky-thuong-tru"


def test_entry_tro_ly_cung_key_toan_quoc():
    from app.channels.handfree import procedure_registry as handfree

    hf = handfree.get_procedure(KEY)
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert hf["keKhaiUrl"] == link["url"] and hf["detect"] == registry.get_procedure(KEY)["detect"]
    assert hf["requiresCapability"] == "supportsBcaThuongTru" and hf["submitCommitCheckbox"] == "chkRULE"
    assert hf["supportsSplitDocuments"] is True and "provinceOnly" not in hf
    assert handfree._HOAN_THIEN_THEO_TINH[KEY] == handfree._TAT_CA
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": {"supportsBcaThuongTru": True},
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "lai_chau", "ward": "Phường Đoàn Kết"}}
    flow._to_confirm_procedure(conv, KEY)
    from app.channels.handfree.chat.intents import Intent

    r = flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True}))
    assert "nơi thường trú của hộ" in r.display_md


# ── Đính kèm ──
_PAGES = ["DANH MỤC THÀNH PHẦN HỒ SƠ", "TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ",
          "VĂN BẢN THỐNG NHẤT CỦA CÁC THÀNH VIÊN HỘ GIA ĐÌNH", "TRÍCH LỤC KHAI TỬ (BẢN SAO)", "CĂN CƯỚC"]
# Hồ sơ in sẵn chân trang "Trang i / N" ngay dưới mốc trang của OCR — không được đếm thành trang riêng.
_OCR = "\n".join(f"───── Trang {i + 1}/{len(_PAGES)} ─────\n{t}\nTrang {i + 1} / {len(_PAGES)}"
                 for i, t in enumerate(_PAGES))
_DOCS = [
    {"fileIndex": 0, "pages": [1], "docType": "other", "documentName": "Danh mục thành phần hồ sơ"},
    {"fileIndex": 0, "pages": [2], "docType": "to_khai", "documentName": "Tờ khai thay đổi thông tin cư trú"},
    {"fileIndex": 0, "pages": [3], "docType": "y_kien", "documentName": "Văn bản thống nhất"},
    {"fileIndex": 0, "pages": [4], "docType": "chung_minh", "documentName": "Trích lục khai tử"},
]


def _files(*names):
    return [FileItem(name=n, type="application/pdf", dataUrl="data:,", role="") for n in names]


def _patch(monkeypatch, documents, fail_split=False):
    async def fake_ocr(files):
        return [{"text": _OCR} for _ in files]

    async def fake_chat(messages, max_tokens=None, **_):
        if fail_split and "TỪNG TRANG" in messages[0]["content"]:
            raise RuntimeError("llm hỏng")
        return json.dumps({"documents": documents})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(tach.client, "chat", fake_chat)


def test_tach_file_dung_dong_va_khong_sot_trang(monkeypatch):
    # Trang 5 (CCCD) LLM bỏ sót → gộp vào giấy liền trước, không mất trang.
    _patch(monkeypatch, _DOCS)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    got = [(i["rowKey"], i["sourceSegments"][0]["pageIndexes"]) for i in res["attachments"]]
    assert got == [
        (ROWS["chung_minh"]["rowKey"], [0]),  # bìa / danh mục: không có dòng riêng → dòng 3 + cảnh báo
        (ROWS["to_khai"]["rowKey"], [1]),
        (ROWS["y_kien"]["rowKey"], [2]),
        (ROWS["chung_minh"]["rowKey"], [3, 4]),
    ]
    assert sorted(p for i in res["attachments"] for s in i["sourceSegments"] for p in s["pageIndexes"]) == [0, 1, 2, 3, 4]
    assert all(i["target"] == "bca-row" and i["bcaPlainTable"] is True for i in res["attachments"])
    to_khai = res["attachments"][1]["rowFields"]
    assert to_khai == {"kind": "Giấy tờ điện tử", "count": "01"}
    assert res["attachments"][3]["rowFields"] == {"kind": "Bản sao", "count": "02"}
    assert any("Danh mục thành phần hồ sơ" in e for e in res["errors"])


def test_tach_va_json_thieu_ngoac_va_tieu_de_trang_rong(monkeypatch):
    # Đúng kiểu trả lời chạy thật: quên "}" đóng mục "tep" + tiêu đề trang văn bản thống nhất để rỗng.
    raw = ('{"tep":[{"fileIndex":0,"tieuDeTrang":["","Tờ khai","","Trích lục khai tử","Căn cước"]],"documents":'
           + json.dumps([*_DOCS, {"fileIndex": 0, "pages": [5], "docType": "cccd", "documentName": "Căn cước",
                                  "matThe": "ca_hai", "chuThe": ""}], ensure_ascii=False) + "}")
    _patch(monkeypatch, [])

    async def fake_chat(*_a, **_k):
        return raw

    monkeypatch.setattr(tach.client, "chat", fake_chat)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    assert not any("(tách)" in e for e in res["errors"])
    got = [(i["rowKey"], i["sourceSegments"][0]["pageIndexes"]) for i in res["attachments"]]
    assert got == [
        (ROWS["chung_minh"]["rowKey"], [0]),
        (ROWS["to_khai"]["rowKey"], [1]),
        (ROWS["y_kien"]["rowKey"], [2]),  # không bị dồn vào tờ khai dù tiêu đề trang rỗng
        (ROWS["chung_minh"]["rowKey"], [3]),
        (ROWS["chung_minh"]["rowKey"], [4]),
    ]


def test_tat_tach_thi_dinh_nguyen_tep_vao_moi_dong_kem_ghi_chu(monkeypatch):
    _patch(monkeypatch, [*_DOCS, {"fileIndex": 0, "pages": [5], "docType": "cccd", "documentName": "Căn cước"}])
    for options in ({}, {"splitDocuments": "true"}, None):
        res = asyncio.run(attach.plan(_files("hoso.pdf"), options))
        items = res["attachments"]
        assert all("sourceSegments" not in i and i["fileIndex"] == 0 for i in items)
        assert [i["rowKey"] for i in items] == [ROWS[k]["rowKey"] for k in ("to_khai", "y_kien", "chung_minh")]
        assert items[0]["rowFields"]["note"] == (
            "Đính kèm chung tệp hoso.pdf (5 trang): Tờ khai thay đổi thông tin cư trú tại trang 2/5")
        assert items[2]["rowFields"] == {"kind": "Bản sao", "count": "01",
                                         "note": "Đính kèm chung tệp hoso.pdf (5 trang): Trích lục khai tử tại "
                                                 "trang 4/5"}


def test_ke_hoach_bca_row_qua_duoc_response_model_va_giu_du_truong(monkeypatch):
    # Chạy thật 16/11/2026: AttachmentPlanResp chưa nhận target "bca-row" → /process 500; thiếu khai trường thì
    # response_model lược mất rowKey / groupIndex… → extension không tìm được dòng.
    from app.attachments.schemas import AttachmentPlanResp
    from app.pipelines.dang_ky_thuong_tru.attach import planner as thuong_tru

    _patch(monkeypatch, _DOCS)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {}))
    out = AttachmentPlanResp.model_validate(res).model_dump(mode="json")
    item = out["attachments"][0]
    assert item["target"] == "bca-row" and item["rowKey"] == ROWS["to_khai"]["rowKey"]
    assert item["bcaPlainTable"] is True and item["groupIndex"] == 0
    assert item["rowFields"]["kind"] == "Giấy tờ điện tử" and item["rowFields"]["note"].startswith("Đính kèm chung")
    # Đăng ký thường trú dùng chung target: nhóm + dòng thêm mới cũng phải giữ nguyên.
    kinds, names, case, _ = thuong_tru.resolve(1, {"case": "consented", "documents": [{"index": 0, "docType": "quan_he"}]})
    items, _, _ = thuong_tru.build_plan_items([{"name": "a.pdf"}], kinds, names, case)
    kept = AttachmentPlanResp.model_validate({"attachments": items}).model_dump(mode="json")["attachments"][0]
    assert (kept["groupIndex"], kept["newRow"], kept["groupLabel"]) == (2, True, items[0]["groupLabel"])


def test_tep_rieng_le_khong_ghi_chu_cccd_vao_dong_chung_minh():
    names = ["to-khai.pdf", "cccd.jpg"]
    docs = [{"fileIndex": 0, "pages": [1, 2], "docType": "to_khai"},
            {"fileIndex": 1, "pages": [1], "docType": "cccd", "documentName": "Căn cước"}]
    items, warnings, _ = khong_tach.build_plan_items(names, {0: 2, 1: 1}, docs)
    assert [(i["fileIndex"], i["rowKey"]) for i in items] == [
        (0, ROWS["to_khai"]["rowKey"]), (1, ROWS["chung_minh"]["rowKey"])]
    assert "note" not in items[0]["rowFields"] and "cccd.jpg" in warnings[0]


def test_tach_loi_quay_ve_khong_tach(monkeypatch):
    _patch(monkeypatch, _DOCS, fail_split=True)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    assert res["attachments"] and all("sourceSegments" not in i for i in res["attachments"])
    assert any("(tách)" in e for e in res["errors"])


def test_llm_loi_khong_tach_van_dinh_du_tep_vao_dong_to_khai(monkeypatch):
    async def fake_ocr(files):
        return [{"text": _OCR} for _ in files]

    async def broken(*_a, **_k):
        raise RuntimeError("llm hỏng")

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(khong_tach.client, "chat", broken)
    res = asyncio.run(attach.plan(_files("a.pdf", "b.pdf"), {}))
    assert [i["rowKey"] for i in res["attachments"]] == [ROWS["to_khai"]["rowKey"]] * 2
    assert res["attachments"][0]["rowFields"]["count"] == "02"
