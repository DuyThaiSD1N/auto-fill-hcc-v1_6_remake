"""Xác nhận thông tin về cư trú (1.010041, Cổng DVC Bộ Công an): mapper ô form, Trường hợp trên / khác địa bàn,
hình thức nhận kết quả, nhận diện trang dùng chung với đăng ký thường trú, luồng trợ lý, đính kèm (tách / không tách,
bảng phẳng một dòng Tờ khai + dòng "+" theo ảnh chạy thật 24/11/2026)."""
import asyncio
import json

from app.channels.handfree.chat import flow
from app.pipelines.xac_nhan_thong_tin_ve_cu_tru.attach import planner as attach
from app.pipelines.xac_nhan_thong_tin_ve_cu_tru.attach.dinh_kem_khong_tach import planner as khong_tach
from app.pipelines.xac_nhan_thong_tin_ve_cu_tru.attach.dinh_kem_khong_tach.planner import GROUP, ROWS
from app.pipelines.xac_nhan_thong_tin_ve_cu_tru.process import mapper
from app.pipelines.xac_nhan_thong_tin_ve_cu_tru.process import runner as process_runner
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls
from app.process.schemas import FileItem
from app.services import ocr
from app.services.llm import client as llm_client

KEY = "xac-nhan-thong-tin-ve-cu-tru"
# Khai hộ: người đề nghị là con, bố (chủ hộ) được ủy quyền nộp thay.
PERSON = {
    "CoQuan_Tinh": "Tỉnh Lai Châu", "CoQuan_Xa": "Phường Đoàn Kết",
    "NguoiDeNghi_HoTen": "Le Minh Khoa", "NguoiDeNghi_NgaySinh": "3/5/2005", "NguoiDeNghi_GioiTinh": "Nam",
    "NguoiDeNghi_SoDinhDanh": "0122 0500 0123", "NguoiDeNghi_SoDienThoai": "0987 000 222",
    "NguoiDeNghi_Email": "Khoa.Le@example.com",
    "NoiThuongTru_Tinh": "Tỉnh Lai Châu", "NoiThuongTru_Xa": "Phường Đoàn Kết",
    "ChuHo_HoTen": "Le Van Hai", "ChuHo_QuanHe": "Con", "ChuHo_SoDinhDanh": "012070000456",
    "NoiDungDeNghi": "Đề nghị xác nhận thông tin về cư trú: nơi thường trú hiện tại. Mục đích: bổ sung hồ sơ học bổng.",
    # LLM chép nhầm chủ hộ vào bảng cùng thay đổi → bỏ theo số định danh.
    "ThanhVien": [{"hoTen": "Le Van Hai", "soDinhDanh": "012070000456", "quanHeVoiChuHo": "Chủ hộ"}],
    "HinhThucNhanKetQua": "Bản giấy, nhận trực tiếp",
}


def _enrich(values: dict, options=None) -> list[dict]:
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def _by(values: dict, options=None) -> dict:
    return {f["name"]: f for f in _enrich(values, options)}


def test_thu_tu_va_gia_tri_o_form():
    out = _enrich(PERSON)
    by = {f["name"]: f for f in out}
    names = [f["name"] for f in out]
    assert names[:2] == ["cboORG", "cboBPROC_CASE_CODE"]
    assert names.index("cboFORMAT_DATE") < names.index("txtBIRTH_DATE") < names.index("txtFULLNAME")
    assert names[-2:] == ["cboTYPE_GET_RESULT", "txtNUMBER_OF_RESULT"]
    assert by["cboORG"]["value"] == {"province": "Tỉnh Lai Châu", "ward": "Phường Đoàn Kết",
                                     "cityId": "cboRECEIVE_ADDR_CITY_ID", "wardId": "cboRECEIVE_ADDR_VILLAGE_ID",
                                     "readySelect": "cboBPROC_CASE_CODE"}
    assert by["cboORG"]["onlyIfEmpty"] is True and "default" not in by["cboORG"]
    # Thường trú cùng phường với cơ quan tiếp nhận → trên địa bàn quản lý.
    assert by["cboBPROC_CASE_CODE"]["value"] == "Cấp cho NK thường trú trên địa bàn quản lý"
    assert "default" not in by["cboBPROC_CASE_CODE"]
    assert by["txtFULLNAME"]["value"] == "LE MINH KHOA" and by["txtID_CARD_NUMBER"]["value"] == "012205000123"
    assert by["txtBIRTH_DATE"]["value"] == "03/05/2005" and by["cboFORMAT_DATE"]["value"] == "Ngày tháng năm"
    assert by["cboGENDER_ID"]["value"] == "Nam"
    assert by["txtPHONE_NUMBER"]["value"] == "0987000222" and by["txtEMAIL"]["value"] == "khoa.le@example.com"
    assert by["txtHH_HEAD_FULLNAME"]["value"] == "LE VAN HAI"
    assert by["cboRELATIONSHIP_WITH_HHHEAD_ID"]["value"] == "Con"
    assert by["txtID_CARD_NUMBER_HHEAD"]["value"] == "012070000456"
    assert by["txtCHANGED_CONTENT_NOTE"]["value"].startswith("Đề nghị xác nhận thông tin về cư trú")
    # Bảng cùng thay đổi chỉ có chủ hộ chép nhầm → bỏ, không gửi bảng rỗng.
    assert "tblNguoi_CUNGTD" not in by
    # Ô của đăng ký thường trú mà thủ tục này ẩn / không điền.
    assert not {"radIsHouseHold", "txtSUGGEST_DETAIL_ADDR", "radIsChangePerson", "chkRULE"} & set(by)
    # Nhận bản giấy trực tiếp; giấy không ghi số lượng phiếu → 1, tô vàng.
    assert by["cboTYPE_GET_RESULT"]["value"] == "Nhận trực tiếp"
    assert by["txtNUMBER_OF_RESULT"]["value"] == "1" and by["txtNUMBER_OF_RESULT"]["default"] is True


def test_thuong_tru_khac_phuong_thi_khac_dia_ban():
    values = dict(PERSON, NoiThuongTru_Xa="Phường Tân Phong")
    assert _by(values)["cboBPROC_CASE_CODE"]["value"] == "Cấp cho NK thường trú khác địa bàn quản lý"
    values = dict(PERSON, NoiThuongTru_Tinh="Tỉnh Điện Biên", NoiThuongTru_Xa="Phường Mường Thanh")
    assert _by(values)["cboBPROC_CASE_CODE"]["value"] == "Cấp cho NK thường trú khác địa bàn quản lý"


def test_llm_bo_tien_to_xa_van_cung_dia_ban():
    values = dict(PERSON, NoiThuongTru_Tinh="", NoiThuongTru_Xa="Đoàn Kết")
    case = _by(values)["cboBPROC_CASE_CODE"]
    assert case["value"] == "Cấp cho NK thường trú trên địa bàn quản lý" and "default" not in case


def test_khong_biet_noi_thuong_tru_thi_tren_dia_ban_to_vang():
    values = {k: v for k, v in PERSON.items() if not k.startswith("NoiThuongTru_")}
    case = _by(values)["cboBPROC_CASE_CODE"]
    assert case["value"] == "Cấp cho NK thường trú trên địa bàn quản lý" and case["default"] is True


def test_giay_khong_ghi_co_quan_thi_lay_xa_tai_khoan_to_vang():
    values = {k: v for k, v in PERSON.items() if not k.startswith("CoQuan_")}
    options = mapper.with_account_process_options({}, {"tinh": "Tỉnh Mẫu", "xa": "Phường Mẫu"}, KEY)
    agency = _by(values, options)["cboORG"]
    assert agency["value"]["ward"] == "Phường Mẫu" and agency["default"] is True
    # Thủ tục khác không nhận cờ của thủ tục này.
    assert "_accountAgency" not in mapper.with_account_process_options({}, {"tinh": "T", "xa": "X"}, "khac")


def test_hinh_thuc_nhan_ket_qua():
    # Không giấy nào ghi → giữ mặc định của cổng, không gửi ô nào.
    by = _by({k: v for k, v in PERSON.items() if k != "HinhThucNhanKetQua"})
    assert not {"cboTYPE_GET_RESULT", "txtNUMBER_OF_RESULT"} & set(by)
    by = _by(dict(PERSON, HinhThucNhanKetQua="Nhận kết quả trên Cổng dịch vụ công"))
    assert by["cboTYPE_GET_RESULT"]["value"] == "Nhận qua cổng thông tin" and "txtNUMBER_OF_RESULT" not in by
    by = _by(dict(PERSON, HinhThucNhanKetQua="Gửi qua bưu chính", SoLuongPhieu="02 bản"))
    assert by["cboTYPE_GET_RESULT"]["value"] == "Qua đường bưu chính"
    assert by["txtNUMBER_OF_RESULT"]["value"] == "2" and "default" not in by["txtNUMBER_OF_RESULT"]


def test_runner_dung_mapper(monkeypatch):
    async def fake_run(files_by_role, **kwargs):
        assert kwargs["comp_by_name"]["ThanhVien"] == "x-array"
        assert "NoiThuongTru_Xa" in kwargs["allowed"]
        return {"fields": [{"name": k, "value": v} for k, v in PERSON.items()]}

    monkeypatch.setattr(process_runner.runner, "run", fake_run)
    res = asyncio.run(process_runner.run({}, {}))
    assert {f["name"] for f in res["fields"]} >= {"cboORG", "cboBPROC_CASE_CODE", "txtFULLNAME"}


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
    assert link["code"] == "1.010041" and "TT=THUONGTRU_09" in link["url"]
    proc = registry.get_procedure(KEY)
    assert registry.get_pipeline(KEY) is not None
    # Có đính kèm + tách giấy tờ (ảnh user 24/11/2026).
    assert proc["hasAttachmentStep"] is True and proc["supportsSplitDocuments"] is True
    assert registry.get_attach_pipeline(KEY) is attach.plan
    # Cùng trang dang-ky-thuong-tru.html: _09 → thủ tục này, _08 điều chỉnh, _01 vẫn là đăng ký thường trú.
    assert _detect(link["url"]) == KEY
    for other in ("dieu-chinh-thong-tin-ve-cu-tru", "dang-ky-thuong-tru"):
        assert _detect(next(item for item in KE_KHAI_LINKS if item["key"] == other)["url"]) == other


def test_entry_tro_ly_cung_key_toan_quoc():
    from app.channels.handfree import procedure_registry as handfree

    hf = handfree.get_procedure(KEY)
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert hf["keKhaiUrl"] == link["url"] and hf["detect"] == registry.get_procedure(KEY)["detect"]
    assert hf["requiresCapability"] == "supportsBcaThuongTru" and hf["submitCommitCheckbox"] == "chkRULE"
    # Đính kèm cùng trang, điền xong HỎI rồi mới đính như tách hộ.
    assert hf["hasAttachmentStep"] is True and hf["samePageAttach"] is True and hf["askBeforeAttach"] is True
    assert hf["supportsSplitDocuments"] is True and hf["docsAdjustRefill"] is True and "provinceOnly" not in hf
    assert handfree._HOAN_THIEN_THEO_TINH[KEY] == handfree._TAT_CA
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": {"supportsBcaThuongTru": True},
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "lai_chau", "ward": "Phường Đoàn Kết"}}
    flow._to_confirm_procedure(conv, KEY)
    from app.channels.handfree.chat.intents import Intent

    r = flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True}))
    assert "nơi thường trú" in r.display_md


def test_moi_thu_tuc_bo_cong_an_tren_trang_ke_khai_thi_dien_truoc_roi_moi_dinh():
    """Ảnh chạy thật 20/11/2026: trang kê khai Bộ Công an có sẵn bảng đính kèm (#tblGiayToDinhKem / Thành phần hồ sơ)
    nên extension báo attachmentTarget → trợ lý hiện "Đã đưa đủ giấy tờ, đính kèm đi" khi form còn trống. Mọi thủ tục
    Bộ Công an trên trợ lý: đứng ở trang kê khai thì nhận giấy để ĐIỀN tờ khai; đính kèm (nếu có) chạy sau khi điền."""
    from app.channels.handfree import procedure_registry as handfree

    bca = [p for p in handfree.PROCEDURES
           if p.get("bcaPortal") or flow._BCA_NTH_HOST in ((p.get("detect") or {}).get("urlScope") or [])]
    assert len(bca) >= 18
    # Trang thường trú / tạm trú / căn cước: form + khối cơ quan + bảng đính kèm cùng DOM.
    dan_cu = {"formKind": "standard", "attachmentTarget": True, "bcaAgencyBlock": True, "bcaKeKhaiForm": False}
    # eForm Nth bocongan: form CongDan_* đang hiện cùng bảng Thành phần hồ sơ (extension mới / cũ chưa báo cờ).
    nth_moi = {"formKind": "standard", "attachmentTarget": True, "bcaKeKhaiForm": True}
    nth_cu = {"formKind": "standard", "attachmentTarget": True}
    for p in bca:
        for ctx in (nth_moi, nth_cu) if flow._bca_nth(p) else (dan_cu,):
            assert flow._resolve_docs_target(p, ctx, {"agency_done": True}) == "declaration", (p["key"], ctx)
        if flow._bca_nth(p):
            # Sang trang Thành phần hồ sơ riêng (form ẩn) thì mới là bước đính kèm.
            ctx = {"formKind": "", "attachmentTarget": True, "bcaKeKhaiForm": False}
            assert flow._resolve_docs_target(p, ctx, {"agency_done": True}) == "attachment", p["key"]


# ── Đính kèm (Auto Fill) ──
# Bộ hồ sơ như ảnh user: tờ khai CT01 (con dâu nhập vào hộ mẹ chồng, ý kiến đồng ý ghi trên tờ khai), giấy kết hôn,
# một PDF 2 trang gồm thẻ căn cước của chủ hộ và người đăng ký.
_FILES = {
    "to_khai.pdf": ["TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ"],
    "ket_hon.pdf": ["GIẤY CHỨNG NHẬN KẾT HÔN"],
    "cccd.pdf": ["CĂN CƯỚC CÔNG DÂN", "CĂN CƯỚC"],
}
_DOCS = [
    {"fileIndex": 0, "pages": [1], "docType": "to_khai", "documentName": "Tờ khai thay đổi thông tin cư trú"},
    {"fileIndex": 1, "pages": [1], "docType": "nhan_than", "documentName": "Giấy chứng nhận kết hôn"},
    {"fileIndex": 2, "pages": [1], "docType": "cccd", "documentName": "Thẻ căn cước", "matThe": "ca_hai",
     "chuThe": "MAU THI A"},
    {"fileIndex": 2, "pages": [2], "docType": "cccd", "documentName": "Thẻ căn cước", "matThe": "ca_hai",
     "chuThe": "MAU THI B"},
]


def _ocr_text(pages):
    return "\n".join(f"───── Trang {i + 1}/{len(pages)} ─────\n{t}\nTrang {i + 1} / {len(pages)}"
                     for i, t in enumerate(pages))


def _files(names=tuple(_FILES)):
    return [FileItem(name=n, type="application/pdf", dataUrl="data:,", role="") for n in names]


def _patch(monkeypatch, documents, fail_split=False, texts=None):
    texts = texts or {n: _ocr_text(p) for n, p in _FILES.items()}

    async def fake_ocr(files):
        return [{"name": f["name"], "text": texts[f["name"]]} for f in files]

    async def fake_chat(messages, max_tokens=None, **_):
        if fail_split and "TỪNG TRANG" in messages[0]["content"]:
            raise RuntimeError("llm hỏng")
        return json.dumps({"documents": documents})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(llm_client, "chat", fake_chat)


_TK = ROWS["to_khai"]


def test_tat_tach_dinh_nguyen_tep_bang_phang_giay_khac_qua_dau_cong(monkeypatch):
    """Ảnh chạy thật 24/11/2026: trang THUONGTRU_09 KHÔNG có nhóm như thường trú — một bảng #tblGiayToDinhKem hiện sẵn
    chỉ có dòng Tờ khai + nút "+". Gửi số nhóm làm extension gọi load_table_tphs_new(3) → trang lỗi, không đính được."""
    _patch(monkeypatch, _DOCS)
    for options in ({}, {"splitDocuments": "true"}, None):
        res = asyncio.run(attach.plan(_files(), options))
        items = res["attachments"]
        assert all(i["target"] == "bca-row" and i["bcaPlainTable"] is True and i["groupIndex"] == 0 for i in items)
        assert all("sourceSegments" not in i for i in items)
        assert [(i["fileIndex"], i["rowKey"], i["newRow"], i["componentName"]) for i in items] == [
            (0, _TK["rowKey"], False, _TK["componentName"]),
            (1, "", True, "Giấy chứng nhận kết hôn"),
            # Hai thẻ một tệp → MỘT dòng "+" đính nguyên tệp, ghi chú gồm hai thẻ.
            (2, "", True, "Thẻ căn cước"),
        ]
        assert items[2]["rowFields"] == {
            "count": "01", "note": "Đính kèm chung tệp cccd.pdf (2 trang): Thẻ căn cước tại trang 1–2/2"}
        # Không còn cảnh báo nhóm / dòng của trang thường trú.
        assert not res["errors"]


def test_tach_file_dung_dong_va_khong_sot_trang(monkeypatch):
    docs = [
        {"fileIndex": 0, "pages": [1], "docType": "to_khai", "documentName": "Tờ khai thay đổi thông tin cư trú"},
        {"fileIndex": 0, "pages": [2], "docType": "hop_dong", "documentName": "Hợp đồng cho ở nhờ"},
        {"fileIndex": 0, "pages": [3], "docType": "dien_tich", "documentName": "Xác nhận diện tích nhà ở"},
        {"fileIndex": 0, "pages": [4], "docType": "nhan_than", "documentName": "Giấy chứng nhận kết hôn"},
        {"fileIndex": 0, "pages": [5], "docType": "cccd", "documentName": "Thẻ căn cước", "matThe": "ca_hai",
         "chuThe": "MAU THI A"},
        {"fileIndex": 0, "pages": [6], "docType": "cccd", "documentName": "Thẻ căn cước", "matThe": "ca_hai",
         "chuThe": "MAU THI B"},
    ]
    pages = ["TỜ KHAI", "HỢP ĐỒNG CHO Ở NHỜ", "XÁC NHẬN DIỆN TÍCH", "GIẤY CHỨNG NHẬN KẾT HÔN", "CĂN CƯỚC", "CĂN CƯỚC"]
    _patch(monkeypatch, docs, texts={"hoso.pdf": _ocr_text(pages)})
    res = asyncio.run(attach.plan(_files(["hoso.pdf"]), {"splitDocuments": True}))
    items = res["attachments"]
    got = [(i["rowKey"] or i["componentName"], i["newRow"], i["sourceSegments"][0]["pageIndexes"]) for i in items]
    assert got == [
        (_TK["rowKey"], False, [0]),
        ("Hợp đồng cho ở nhờ", True, [1]),
        ("Xác nhận diện tích nhà ở", True, [2]),
        ("Giấy chứng nhận kết hôn", True, [3]),
        (items[4]["componentName"], True, [4]),
        (items[5]["componentName"], True, [5]),
    ]
    # Thẻ của hai người là hai dòng riêng (tên khác nhau → extension không gom chung).
    assert items[4]["componentName"] != items[5]["componentName"]
    assert sorted(p for i in items for s in i["sourceSegments"] for p in s["pageIndexes"]) == list(range(6))
    assert all(i["bcaPlainTable"] is True for i in items)
    assert items[0]["rowFields"] == {"count": "01"}
    assert not res["errors"]


def test_giay_cho_o_qua_dong_cong_thieu_to_khai_canh_bao():
    docs = [
        {"fileIndex": 0, "pages": [1], "docType": "to_khai"},
        {"fileIndex": 0, "pages": [2, 3], "docType": "so_huu", "documentName": "Giấy chứng nhận quyền sử dụng đất"},
        {"fileIndex": 1, "pages": [1], "docType": "hop_dong", "documentName": "Hợp đồng cho thuê nhà"},
    ]
    items, warnings, _ = khong_tach.build_plan_items(["hoso.pdf", "hd.pdf"], {0: 3, 1: 1}, docs)
    assert [(i["rowKey"], i["newRow"], i["componentName"]) for i in items] == [
        (_TK["rowKey"], False, _TK["componentName"]),
        ("", True, "Giấy chứng nhận quyền sử dụng đất"),
        ("", True, "Hợp đồng cho thuê nhà"),
    ]
    assert items[1]["rowFields"]["note"] == (
        "Đính kèm chung tệp hoso.pdf (3 trang): Giấy chứng nhận quyền sử dụng đất tại trang 2–3/3")
    assert not warnings
    # Không có tờ khai → cảnh báo thiếu dòng Tờ khai.
    _, warnings, _ = khong_tach.build_plan_items(["hd.pdf"], {0: 1}, [dict(docs[2], fileIndex=0)])
    assert any(_TK["componentName"] in w for w in warnings)


def test_giay_chua_ro_loai_qua_dong_cong_canh_bao():
    items, warnings, _ = khong_tach.build_plan_items(["bia.pdf"], {0: 1}, [{"fileIndex": 0, "pages": [1],
                                                                            "docType": "other"}])
    assert items[0]["newRow"] is True and items[0]["componentName"] == "Giấy tờ khác"
    assert any("bia.pdf" in w for w in warnings)


def test_tach_loi_quay_ve_khong_tach(monkeypatch):
    _patch(monkeypatch, _DOCS, fail_split=True)
    res = asyncio.run(attach.plan(_files(), {"splitDocuments": True}))
    assert res["attachments"] and all("sourceSegments" not in i for i in res["attachments"])
    assert any("(tách)" in e for e in res["errors"])


def test_llm_loi_khong_tach_van_dinh_du_tep_vao_dong_to_khai(monkeypatch):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": _ocr_text(_FILES[f["name"]])} for f in files]

    async def broken(*_a, **_k):
        raise RuntimeError("llm hỏng")

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(llm_client, "chat", broken)
    res = asyncio.run(attach.plan(_files(), {}))
    assert [i["rowKey"] for i in res["attachments"]] == [_TK["rowKey"]] * 3
    assert res["attachments"][0]["rowFields"]["count"] == "03"
    assert any("Chưa phân loại được" in e for e in res["errors"])


def test_ke_hoach_qua_duoc_response_model(monkeypatch):
    from app.attachments.schemas import AttachmentPlanResp

    _patch(monkeypatch, _DOCS)
    res = asyncio.run(attach.plan(_files(), {}))
    out = AttachmentPlanResp.model_validate(res).model_dump(mode="json")["attachments"]
    assert out[0]["rowKey"] == _TK["rowKey"]
    assert out[0]["bcaPlainTable"] is True and out[0]["groupLabel"] == GROUP["groupLabel"]
    assert out[1]["newRow"] is True and out[1]["componentName"] == "Giấy chứng nhận kết hôn"
