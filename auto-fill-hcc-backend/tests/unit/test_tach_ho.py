"""Tách hộ (1.010038, Cổng DVC Bộ Công an): mapper ô form, bảng thành viên tách theo, dự phòng nơi tách hộ / nội dung
đề nghị / cơ quan, nhận diện trang dùng chung với đăng ký thường trú, đính kèm Auto Fill (tách / không tách), luồng
trợ lý (không đính kèm)."""
import asyncio
import json

from app.channels.handfree.chat import flow
from app.pipelines.tach_ho.attach import planner as attach
from app.pipelines.tach_ho.attach.dinh_kem_khong_tach import planner as khong_tach
from app.pipelines.tach_ho.attach.dinh_kem_khong_tach.planner import ROWS
from app.pipelines.tach_ho.process import mapper
from app.pipelines.tach_ho.process import runner as process_runner
from app.process.schemas import FileItem
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls
from app.services import ocr
from app.services.llm import client as llm_client

KEY = "tach-ho"
# Người con tách khỏi hộ bố mẹ, lập hộ mới cùng vợ và con trên chỗ ở của bố mẹ.
PERSON = {
    "CoQuan_Tinh": "Tỉnh Lai Châu", "CoQuan_Xa": "Phường Đoàn Kết",
    "NguoiDeNghi_HoTen": "Tran Van Minh", "NguoiDeNghi_NgaySinh": "5/3/1998", "NguoiDeNghi_GioiTinh": "Nam",
    "NguoiDeNghi_SoDinhDanh": "0120 9800 0111", "NguoiDeNghi_SoDienThoai": "",
    "NguoiDeNghi_Email": "Minh.Tran@example.com",
    "NoiTachHo_DiaChiChiTiet": "Tổ dân phố 7, Phường Đoàn Kết, Tỉnh Lai Châu",
    "NoiDungDeNghi": "Đề nghị tách hộ tại Tổ dân phố 7, phường Đoàn Kết, tỉnh Lai Châu",
    # Bảng đơn xác nhận tách hộ có cả dòng người đề nghị ("Chủ hộ") → bỏ trước khi đánh chỉ số dòng.
    "ThanhVien": [
        {"hoTen": "Tran Van Minh", "ngaySinh": "1998", "gioiTinh": "Nam", "soDinhDanh": "012098000111",
         "quanHeVoiChuHo": "Chủ hộ"},
        {"hoTen": "Pham Thi Lan", "ngaySinh": "12/8/2000", "gioiTinh": "Nữ", "soDinhDanh": "012300000222",
         "quanHeVoiChuHo": "Vợ"},
        {"hoTen": "Tran Gia Bao", "ngaySinh": "02/01/2025", "gioiTinh": "", "soDinhDanh": "012225000333",
         "quanHeVoiChuHo": "Con"},
    ],
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
    # Gõ địa chỉ nơi đề nghị là cổng ghi đè nội dung → nội dung đứng sau địa chỉ.
    assert names.index("txtSUGGEST_DETAIL_ADDR") < names.index("txtCHANGED_CONTENT_NOTE")
    assert by["cboORG"]["value"] == {"province": "Tỉnh Lai Châu", "ward": "Phường Đoàn Kết",
                                     "cityId": "cboRECEIVE_ADDR_CITY_ID", "wardId": "cboRECEIVE_ADDR_VILLAGE_ID",
                                     "readySelect": "cboBPROC_CASE_CODE"}
    assert by["cboORG"]["onlyIfEmpty"] is True and "default" not in by["cboORG"]
    assert by["cboBPROC_CASE_CODE"]["value"] == "Tách hộ"
    assert by["txtFULLNAME"]["value"] == "TRAN VAN MINH" and by["txtID_CARD_NUMBER"]["value"] == "012098000111"
    assert by["txtBIRTH_DATE"]["value"] == "05/03/1998" and by["cboFORMAT_DATE"]["value"] == "Ngày tháng năm"
    assert by["cboGENDER_ID"]["value"] == "Nam" and by["txtEMAIL"]["value"] == "minh.tran@example.com"
    assert "txtPHONE_NUMBER" not in by
    # Ô địa chỉ nơi đề nghị chỉ nhận phần dưới cấp xã.
    assert by["txtSUGGEST_DETAIL_ADDR"]["value"] == "Tổ dân phố 7"
    assert by["txtCHANGED_CONTENT_NOTE"]["value"] == "Đề nghị tách hộ tại Tổ dân phố 7, phường Đoàn Kết, tỉnh Lai Châu"
    assert "default" not in by["txtCHANGED_CONTENT_NOTE"]
    # Ô của các thủ tục cùng trang mà tách hộ không có / không điền.
    assert not {"radIsHouseHold", "txtHH_HEAD_FULLNAME", "cboRELATIONSHIP_WITH_HHHEAD_ID", "txtID_CARD_NUMBER_HHEAD",
                "radIsChangePerson", "chkRULE", "cboTYPE_GET_RESULT", "cboSUGGEST_CITY_ADDR"} & set(by)


def test_bang_thanh_vien_bo_nguoi_de_nghi():
    table = _by(PERSON)["tblNguoi_CUNGTD"]["value"]
    assert table["addSelector"] == "#tblNguoi_CUNGTD a.add_CUNGTD"
    rows = [{cell["id"]: cell["value"] for cell in row} for row in table["rows"]]
    assert rows == [
        {"txtFULLNAME_CUNGTD0": "PHAM THI LAN", "txtDOB_CUNGTD0": "12/08/2000", "cboGENDER_CUNGTD0": "Nữ",
         "txtIDENTIFIER_NOCARD_NUMBER_CUNGTD0": "012300000222", "cboRELATIONSHIP_CHUHO_CUNGTD0": "Vợ"},
        # Giới tính trống → suy từ chữ số thứ 4 của số định danh (2 = nam sinh thế kỷ 21).
        {"txtFULLNAME_CUNGTD1": "TRAN GIA BAO", "txtDOB_CUNGTD1": "02/01/2025", "cboGENDER_CUNGTD1": "Nam",
         "txtIDENTIFIER_NOCARD_NUMBER_CUNGTD1": "012225000333", "cboRELATIONSHIP_CHUHO_CUNGTD1": "Con"},
    ]
    # Dòng người đề nghị không có số định danh vẫn bị bỏ theo họ tên.
    members = [dict(PERSON["ThanhVien"][0], soDinhDanh="", quanHeVoiChuHo="")] + PERSON["ThanhVien"][1:2]
    rows = _by(dict(PERSON, ThanhVien=members))["tblNguoi_CUNGTD"]["value"]["rows"]
    assert len(rows) == 1 and rows[0][0]["value"] == "PHAM THI LAN"
    # Không còn thành viên nào → không gửi bảng rỗng.
    assert "tblNguoi_CUNGTD" not in _by(dict(PERSON, ThanhVien=PERSON["ThanhVien"][:1]))


def test_thieu_dia_chi_thi_cat_tu_noi_dung_de_nghi():
    by = _by(dict(PERSON, NoiTachHo_DiaChiChiTiet=""))
    assert by["txtSUGGEST_DETAIL_ADDR"]["value"] == "Tổ dân phố 7"


def test_khong_co_ct01_thi_dung_noi_dung_de_nghi_to_vang():
    by = _by(dict(PERSON, NoiDungDeNghi=""))
    note = by["txtCHANGED_CONTENT_NOTE"]
    assert note["value"] == "Đề nghị tách hộ tại Tổ dân phố 7, Phường Đoàn Kết, Tỉnh Lai Châu"
    assert note["default"] is True


def test_giay_khong_ghi_co_quan_thi_lay_xa_tai_khoan_to_vang():
    values = {k: v for k, v in PERSON.items() if not k.startswith("CoQuan_")}
    options = mapper.with_account_process_options({}, {"tinh": "Tỉnh Mẫu", "xa": "Phường Mẫu"}, KEY)
    agency = _by(values, options)["cboORG"]
    assert agency["value"]["ward"] == "Phường Mẫu" and agency["default"] is True
    # Thủ tục khác không nhận cờ của thủ tục này.
    assert "_accountAgency" not in mapper.with_account_process_options({}, {"tinh": "T", "xa": "X"}, "khac")


def test_runner_dung_mapper(monkeypatch):
    async def fake_run(files_by_role, **kwargs):
        assert kwargs["comp_by_name"]["ThanhVien"] == "x-array"
        assert "NoiTachHo_DiaChiChiTiet" in kwargs["allowed"]
        assert "chủ hộ MỚI" in kwargs["extra_rules"]
        return {"fields": [{"name": k, "value": v} for k, v in PERSON.items()]}

    monkeypatch.setattr(process_runner.runner, "run", fake_run)
    res = asyncio.run(process_runner.run({}, {}))
    assert {f["name"] for f in res["fields"]} >= {"cboORG", "cboBPROC_CASE_CODE", "txtFULLNAME", "tblNguoi_CUNGTD"}


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
    assert link["code"] == "1.010038" and "TT=THUONGTRU_05" in link["url"]
    proc = registry.get_procedure(KEY)
    assert registry.get_pipeline(KEY) is not None
    # Auto Fill có đính kèm + tách giấy tờ (user 20/11/2026); trợ lý không đính kèm (test entry trợ lý bên dưới).
    assert proc["hasAttachmentStep"] is True and proc["supportsSplitDocuments"] is True
    assert registry.get_attach_pipeline(KEY) is not None
    # Cùng trang dang-ky-thuong-tru.html: _05 → tách hộ, các thủ tục cùng trang vẫn nhận đúng.
    assert _detect(link["url"]) == KEY
    for other in ("dieu-chinh-thong-tin-ve-cu-tru", "xac-nhan-thong-tin-ve-cu-tru", "dang-ky-thuong-tru"):
        assert _detect(next(item for item in KE_KHAI_LINKS if item["key"] == other)["url"]) == other


def test_entry_tro_ly_cung_key_toan_quoc():
    from app.channels.handfree import procedure_registry as handfree

    hf = handfree.get_procedure(KEY)
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert hf["keKhaiUrl"] == link["url"] and hf["detect"] == registry.get_procedure(KEY)["detect"]
    assert hf["requiresCapability"] == "supportsBcaThuongTru" and hf["submitCommitCheckbox"] == "chkRULE"
    # Đính kèm cùng trang nhưng HỎI trước (user 20/11/2026: tách 2 luồng điền / đính như tư pháp).
    assert hf["hasAttachmentStep"] is True and hf["samePageAttach"] is True and hf["askBeforeAttach"] is True
    assert hf["supportsSplitDocuments"] is True and "provinceOnly" not in hf
    assert handfree._HOAN_THIEN_THEO_TINH[KEY] == handfree._TAT_CA
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": {"supportsBcaThuongTru": True},
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "lai_chau", "ward": "Phường Đoàn Kết"}}
    flow._to_confirm_procedure(conv, KEY)
    from app.channels.handfree.chat.intents import Intent

    r = flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True}))
    assert "nơi thường trú" in r.display_md


def test_tro_ly_bang_dinh_kem_an_tren_trang_khong_thanh_buoc_dinh_kem():
    # Ảnh chạy thật 20/11/2026: trang thường trú luôn có bảng #tblGiayToDinhKem → extension báo attachmentTarget, trợ lý
    # nhận giấy rồi "đính kèm đi" thay vì điền tờ khai. Giấy tờ nhận ở bước này LUÔN để điền tờ khai trước.
    from app.channels.handfree import procedure_registry as handfree

    page = {"attachmentTarget": True, "attachmentComponentCount": 3, "bcaAgencyBlock": True}
    for key in (KEY, "xac-nhan-thong-tin-ve-cu-tru"):
        proc = handfree.get_procedure(key)
        conv = {"state": "collecting_docs", "procedure_key": key, "agency_done": True}
        assert flow._resolve_docs_target(proc, page, conv) == "declaration", key
        assert flow._remember_docs_target(conv, proc, page)[0] == "declaration"
        assert flow._docs_done_label_for_conv(conv) == "✅ Đã đưa đủ giấy tờ, điền tờ khai đi"
    # Thủ tục không đính kèm: trang có bảng ẩn cũng không tính là đã tới trang đính kèm.
    xac_nhan = handfree.get_procedure("xac-nhan-thong-tin-ve-cu-tru")
    assert flow._attachment_page_reached({}, xac_nhan, page) is False
    # Thủ tục CÓ đính kèm (trang đính kèm riêng) vẫn nhận trang đính kèm như cũ; chưa khai cờ cũng vậy.
    for proc in ({"key": "x", "mode": "agent", "hasAttachmentStep": True}, {"key": "x", "mode": "agent"},
                 {"key": "x", "mode": "attach", "hasAttachmentStep": False}):
        assert flow._resolve_docs_target(proc, {"attachmentTarget": True}, {}) == "attachment", proc


def _fill_report(caps=None, review=None):
    from unittest import mock

    from app.channels.handfree.chat import pipeline_runner, tracing
    from app.channels.handfree.chat.intents import Intent

    conv = {"_id": "c1", "state": "filling", "procedure_key": KEY, "docs_target": "declaration",
            "auto_attach_after_fill": True, "upload_session_id": "s1", "location": {},
            "client_capabilities": dict(caps or {})}
    payload = {"filled": 9, **({"review": review} if review else {})}
    with mock.patch.object(pipeline_runner, "spawn") as spawn, \
            mock.patch.object(tracing, "set_report", mock.AsyncMock()):
        r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", payload)))
    return conv, r, spawn


def test_tro_ly_dien_xong_dung_hoi_roi_moi_dinh_kem():
    # Tách 2 luồng như tư pháp: điền xong KHÔNG tự đính, dừng ở rà soát với nút "Đính kèm giấy tờ".
    from unittest import mock

    from app.channels.handfree.chat import pipeline_runner
    from app.channels.handfree.chat.intents import Intent

    conv, r, spawn = _fill_report()
    assert not spawn.called and conv["state"] == "reviewing"
    assert r.chips[0]["send"] == "__action:confirm_review"
    # Luồng có vòng bổ sung ô (extension mới): đủ ô bắt buộc → nút đi tiếp là "Đính kèm giấy tờ".
    caps = {"supportsFieldReview": True, "supportsBcaFlow": True, "supportsTickCommit": True}
    conv, r, spawn = _fill_report(caps, {"filled": 9, "optional": 0, "required": 0})
    assert not spawn.called and r.chips[0]["send"] == "__action:confirm_review"
    trail = " ".join(a.get("md", "") for a in r.actions if a.get("type") == "trail_message")
    assert "Đính kèm giấy tờ" in trail
    # Công dân bấm "Đính kèm giấy tờ" → chạy planner đính ngay trên trang (bảng cùng trang).
    conv = {"_id": "c1", "state": "reviewing", "procedure_key": KEY, "docs_target": "declaration",
            "upload_session_id": "s1", "location": {}}
    with mock.patch.object(pipeline_runner, "spawn") as spawn, \
            mock.patch.object(pipeline_runner, "run_attach", mock.MagicMock(return_value=None)):
        asyncio.run(flow._handle_reviewing(conv, Intent("action", "confirm_review")))
    assert spawn.called and conv["state"] == "attaching" and conv["attachment_plan_started"]


# ── Đính kèm (Auto Fill) ──
# Bộ hồ sơ gộp một PDF: tờ khai, đơn xác nhận, GCN 2 trang, giấy kết hôn, giấy khai sinh, CCCD hai người.
_PAGES = ["TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ", "ĐƠN XÁC NHẬN TÁCH HỘ TRÊN CÙNG MỘT CHỖ Ở HỢP PHÁP",
          "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT", "SƠ ĐỒ THỬA ĐẤT", "GIẤY CHỨNG NHẬN KẾT HÔN", "GIẤY KHAI SINH",
          "CĂN CƯỚC CÔNG DÂN", "CĂN CƯỚC"]
_OCR = "\n".join(f"───── Trang {i + 1}/{len(_PAGES)} ─────\n{t}\nTrang {i + 1} / {len(_PAGES)}"
                 for i, t in enumerate(_PAGES))
_DOCS = [
    {"fileIndex": 0, "pages": [1], "docType": "to_khai", "documentName": "Tờ khai thay đổi thông tin cư trú"},
    {"fileIndex": 0, "pages": [2], "docType": "cho_o", "documentName": "Đơn xác nhận tách hộ"},
    {"fileIndex": 0, "pages": [3, 4], "docType": "cho_o", "documentName": "Giấy chứng nhận quyền sử dụng đất"},
    {"fileIndex": 0, "pages": [5], "docType": "nhan_than", "documentName": "Giấy chứng nhận kết hôn"},
    {"fileIndex": 0, "pages": [6], "docType": "nhan_than", "documentName": "Giấy khai sinh"},
    {"fileIndex": 0, "pages": [7], "docType": "cccd", "documentName": "Thẻ căn cước", "matThe": "ca_hai",
     "chuThe": "TRAN VAN MINH"},
    {"fileIndex": 0, "pages": [8], "docType": "cccd", "documentName": "Thẻ căn cước", "matThe": "ca_hai",
     "chuThe": "PHAM THI LAN"},
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
    monkeypatch.setattr(llm_client, "chat", fake_chat)


def test_tach_file_dung_dong_va_khong_sot_trang(monkeypatch):
    _patch(monkeypatch, _DOCS)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    items = res["attachments"]
    got = [(i["rowKey"] or i["componentName"], i["newRow"], i["sourceSegments"][0]["pageIndexes"]) for i in items]
    assert got == [
        (ROWS["to_khai"]["rowKey"], False, [0]),
        (ROWS["cho_o"]["rowKey"], False, [1]),
        (ROWS["cho_o"]["rowKey"], False, [2, 3]),
        # Giấy có loại rõ mà bảng không có dòng → dòng "+" mang tên giấy, KHÔNG dồn vào dòng ly hôn.
        ("Giấy chứng nhận kết hôn", True, [4]),
        ("Giấy khai sinh", True, [5]),
        (items[5]["componentName"], True, [6]),
        (items[6]["componentName"], True, [7]),
    ]
    # Thẻ của hai người là hai dòng riêng (tên khác nhau → extension không gom chung).
    assert items[5]["componentName"] != items[6]["componentName"]
    assert sorted(p for i in items for s in i["sourceSegments"] for p in s["pageIndexes"]) == list(range(8))
    assert not any(i["rowKey"] == ROWS["ly_hon"]["rowKey"] for i in items)
    assert all(i["target"] == "bca-row" and i["bcaPlainTable"] is True for i in items)
    # Loại giấy tờ để mặc định cổng; Số lượng = số mục của dòng.
    assert items[0]["rowFields"] == {"count": "01"} and items[1]["rowFields"] == {"count": "02"}
    assert not res["errors"]


def test_tat_tach_thi_dinh_nguyen_tep_vao_moi_dong_kem_ghi_chu(monkeypatch):
    _patch(monkeypatch, _DOCS)
    for options in ({}, {"splitDocuments": "true"}, None):
        res = asyncio.run(attach.plan(_files("hoso.pdf"), options))
        items = res["attachments"]
        assert all("sourceSegments" not in i and i["fileIndex"] == 0 for i in items)
        assert [(i["rowKey"], i["newRow"]) for i in items] == [
            (ROWS["to_khai"]["rowKey"], False), (ROWS["cho_o"]["rowKey"], False), ("", True)]
        assert items[1]["rowFields"]["note"] == (
            "Đính kèm chung tệp hoso.pdf (8 trang): Đơn xác nhận tách hộ, Giấy chứng nhận quyền sử dụng đất tại "
            "trang 2–4/8")
        # Mọi giấy không có dòng của cùng tệp → MỘT dòng "+" liệt kê tên giấy.
        assert items[2]["componentName"] == "Giấy chứng nhận kết hôn, Giấy khai sinh, Thẻ căn cước"
        assert items[2]["rowFields"]["note"].endswith("tại trang 5–8/8")


def test_ke_hoach_qua_duoc_response_model(monkeypatch):
    from app.attachments.schemas import AttachmentPlanResp

    _patch(monkeypatch, _DOCS)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {}))
    out = AttachmentPlanResp.model_validate(res).model_dump(mode="json")["attachments"]
    assert out[0]["rowKey"] == ROWS["to_khai"]["rowKey"] and out[0]["bcaPlainTable"] is True
    assert out[2]["newRow"] is True and out[2]["componentName"].startswith("Giấy chứng nhận kết hôn")


def test_giay_chua_ro_loai_vao_dong_cho_o_canh_bao():
    items, warnings, _ = khong_tach.build_plan_items(["bia.pdf"], {0: 1}, [{"fileIndex": 0, "pages": [1],
                                                                           "docType": "other"}])
    assert items[0]["rowKey"] == ROWS["cho_o"]["rowKey"] and "bia.pdf" in warnings[0]


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
    monkeypatch.setattr(llm_client, "chat", broken)
    res = asyncio.run(attach.plan(_files("a.pdf", "b.pdf"), {}))
    assert [i["rowKey"] for i in res["attachments"]] == [ROWS["to_khai"]["rowKey"]] * 2
    assert res["attachments"][0]["rowFields"]["count"] == "02"
