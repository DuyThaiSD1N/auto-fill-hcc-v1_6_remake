"""Xóa đăng ký tạm trú (1.010028, Cổng DVC Bộ Công an): mapper ô form, Trường hợp theo lý do, cơ quan (chọn đè mặc
định Hà Nội của cổng, CT01 chỉ ghi xã thì tỉnh theo tài khoản), nhận diện trang dùng chung với đăng ký tạm trú, luồng
trợ lý, đính kèm (tách / không tách) vào bảng giấy tờ cùng trang."""
import asyncio
import json

from app.channels.handfree.chat import flow
from app.pipelines.xoa_dang_ky_tam_tru.attach import planner as attach
from app.pipelines.xoa_dang_ky_tam_tru.attach.dinh_kem_khong_tach import planner as khong_tach
from app.pipelines.xoa_dang_ky_tam_tru.attach.dinh_kem_khong_tach.planner import ROWS
from app.pipelines.xoa_dang_ky_tam_tru.process import mapper
from app.pipelines.xoa_dang_ky_tam_tru.process import runner as process_runner
from app.process.schemas import FileItem
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls
from app.services import ocr
from app.services.llm import client as llm_client

KEY = "xoa-dang-ky-tam-tru"
# Người đề nghị tự là chủ hộ tạm trú, đã đăng ký thường trú ngay tại nơi tạm trú.
PERSON = {
    "CoQuan_Tinh": "Tỉnh Lai Châu", "CoQuan_Xa": "Phường Đoàn Kết",
    "TruongHop": "Nhân khẩu do đã đăng ký thường trú tại chính nơi tạm trú",
    "NguoiDeNghi_HoTen": "Hoang Thi Mai", "NguoiDeNghi_NgaySinh": "7/9/1992", "NguoiDeNghi_GioiTinh": "Nữ",
    "NguoiDeNghi_SoDinhDanh": "0121 9200 0555", "NguoiDeNghi_SoDienThoai": "………", "NguoiDeNghi_Email": "",
    "ChuHo_HoTen": "Hoang Thi Mai", "ChuHo_QuanHe": "chủ hộ", "ChuHo_SoDinhDanh": "012192000555",
    "NoiDungDeNghi": "Đề nghị xóa đăng ký tạm trú do đã đăng ký thường trú tại nơi tạm trú",
    "ThanhVien": [],
}


def _enrich(values: dict, options=None) -> list[dict]:
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def _by(values: dict, options=None) -> dict:
    return {f["name"]: f for f in _enrich(values, options)}


def test_thu_tu_va_gia_tri_o_form():
    out = _enrich(PERSON)
    by = {f["name"]: f for f in out}
    names = [f["name"] for f in out]
    assert names[:2] == ["cboRECEIVE_ORG", "cboBPROC_CASE_CODE"]
    assert names.index("cboDATE_FORMAT") < names.index("txtDOB")
    # Cổng chọn sẵn Hà Nội / Ba Đình → chọn đè, KHÔNG onlyIfEmpty; cặp id của trang tạm trú.
    assert by["cboRECEIVE_ORG"]["value"] == {"province": "Tỉnh Lai Châu", "ward": "Phường Đoàn Kết",
                                             "cityId": "cboRECEIVE_ADDR_CITY_CODE",
                                             "wardId": "cboRECEIVE_ADDR_VILLAGE_CODE",
                                             "readySelect": "cboBPROC_CASE_CODE"}
    assert "onlyIfEmpty" not in by["cboRECEIVE_ORG"] and "default" not in by["cboRECEIVE_ORG"]
    assert by["cboBPROC_CASE_CODE"]["value"] == "Nhân khẩu do đã đăng ký thường trú tại chính nơi tạm trú"
    assert by["txtFULLNAME"]["value"] == "HOANG THI MAI" and by["txtIDENTIFIER_NUMBER"]["value"] == "012192000555"
    assert by["txtDOB"]["value"] == "07/09/1992" and by["cboDATE_FORMAT"]["value"] == "Ngày tháng năm"
    assert by["cboGENDER_CODE"]["value"] == "Nữ"
    assert by["txtHH_PERSON_FULLNAME"]["value"] == "HOANG THI MAI"
    assert by["cboHH_PERSON_RELATIONSHIP_CODE"]["value"] == "Chủ hộ"
    assert by["txtHH_PERSON_IDENTIFIER_NUMBER"]["value"] == "012192000555"
    # Ô trống / chấm chấm không điền; khối ẩn với TAMTRU_06 không điền.
    assert not {"txtPHONE_NUMBER", "txtEMAIL", "txtRECEIVER_EMAIL", "listNormal", "txtCHANGED_NOTE", "txtSUGGEST_ADDRESS",
                "txtTEMP_RESIDENT_TO", "txtFULLNAME0", "chkCHECK_LIABILITY"} & set(by)


def test_khoi_nhan_ket_qua_co_email_thi_qua_email_dien_email():
    out = _enrich({**PERSON, "NguoiDeNghi_Email": "mai,hoang@gmail,com"})
    names = [f["name"] for f in out]
    by = {f["name"]: f for f in out}
    # Khối "Thông tin nhận thông báo tình trạng hồ sơ, kết quả giải quyết hồ sơ": chọn hình thức TRƯỚC ô email.
    assert names[-2:] == ["cboRECEIVER_TYPE", "txtRECEIVER_EMAIL"]
    assert by["cboRECEIVER_TYPE"]["value"] == "Qua email" and by["cboRECEIVER_TYPE"]["comp"] == "dom-select"
    assert by["cboRECEIVER_TYPE"]["default"] is True  # giấy không ghi hình thức nhận → tô vàng cho công dân xem lại
    assert by["txtRECEIVER_EMAIL"]["value"] == "mai.hoang@gmail.com" == by["txtEMAIL"]["value"]
    assert by["txtRECEIVER_EMAIL"]["keepPortalValue"] is True and "default" not in by["txtRECEIVER_EMAIL"]
    # Hình thức nhận thông báo để mặc định của cổng (select2 nhiều lựa chọn).
    assert not {"cboNOTIFICATION_TYPE", "txtNOTIFICATION_EMAIL", "txtNOTIFICATION_PHONE"} & set(by)


def test_khoi_nhan_ket_qua_khong_co_email_thi_nhan_qua_cong_khong_bo_trong_o_bat_buoc():
    by = _by(PERSON)
    assert by["cboRECEIVER_TYPE"]["value"] == "Nhận qua cổng thông tin" and by["cboRECEIVER_TYPE"]["default"] is True
    assert "txtRECEIVER_EMAIL" not in by


def test_truong_hop_theo_ly_do_khi_llm_khong_chon():
    cases = {
        "Đề nghị xóa đăng ký tạm trú do đã đăng ký thường trú tại nơi tạm trú":
            "Nhân khẩu do đã đăng ký thường trú tại chính nơi tạm trú",
        "Xóa đăng ký tạm trú cho cả hộ do đã đăng ký thường trú tại đây":
            "Hộ do đã đăng ký thường trú tại chính nơi tạm trú",
        "Đã hết hạn hợp đồng thuê nhà, chuyển đi nơi khác": "Nhân khẩu do không còn chỗ ở hợp pháp",
        "Vắng mặt liên tục từ 6 tháng trở lên": "Nhân khẩu do vắng mặt từ 6 tháng trở lên",
    }
    for reason, want in cases.items():
        assert _by(dict(PERSON, TruongHop="", NoiDungDeNghi=reason))["cboBPROC_CASE_CODE"]["value"] == want, reason
    # LLM rút gọn nhãn hộ → vẫn ra đúng nhãn hộ.
    assert _by(dict(PERSON, TruongHop="Hộ do vắng mặt 6 tháng"))["cboBPROC_CASE_CODE"]["value"] == \
        "Hộ do vắng mặt từ 6 tháng trở lên"
    # Không có căn cứ → không gửi ô (giữ nguyên trên cổng).
    assert "cboBPROC_CASE_CODE" not in _by(dict(PERSON, TruongHop="", NoiDungDeNghi="Đề nghị xóa"))


def test_ct01_chi_ghi_xa_thi_tinh_theo_tai_khoan_to_vang():
    options = mapper.with_account_process_options({}, {"tinh": "Tỉnh Lai Châu", "xa": "Phường Tân Phong"}, KEY)
    agency = _by(dict(PERSON, CoQuan_Tinh=""), options)["cboRECEIVE_ORG"]
    assert agency["value"]["province"] == "Tỉnh Lai Châu" and agency["value"]["ward"] == "Phường Đoàn Kết"
    assert agency["default"] is True
    # Giấy không ghi cơ quan → xã/tỉnh tài khoản, tô vàng.
    agency = _by({k: v for k, v in PERSON.items() if not k.startswith("CoQuan_")}, options)["cboRECEIVE_ORG"]
    assert agency["value"]["ward"] == "Phường Tân Phong" and agency["default"] is True
    # Không giấy, không tài khoản → không gửi ô cơ quan.
    assert "cboRECEIVE_ORG" not in _by({k: v for k, v in PERSON.items() if not k.startswith("CoQuan_")})
    assert "_accountAgency" not in mapper.with_account_process_options({}, {"tinh": "T", "xa": "X"}, "khac")


def test_chu_ho_khac_va_bang_thanh_vien():
    values = dict(PERSON, ChuHo_HoTen="Lo Van Tien", ChuHo_QuanHe="vợ", ChuHo_SoDinhDanh="012088000777",
                  ThanhVien=[{"hoTen": "Lo Van Tien", "soDinhDanh": "012088000777", "quanHeVoiChuHo": "Chủ hộ"},
                             {"hoTen": "Lo Gia Huy", "ngaySinh": "2019", "gioiTinh": "", "soDinhDanh": "012219000888",
                              "quanHeVoiChuHo": "con"}])
    by = _by(values)
    assert by["txtHH_PERSON_FULLNAME"]["value"] == "LO VAN TIEN"
    assert by["cboHH_PERSON_RELATIONSHIP_CODE"]["value"] == "Vợ"
    table = by["listNormal"]["value"]
    assert table["addSelector"].startswith("#listNormal")
    # Chủ hộ chép nhầm vào bảng → bỏ; ngày sinh chỉ có năm → Định dạng "Năm" chọn trước ô ngày.
    assert table["rows"] == [[
        {"id": "txtFULLNAME_CUNGTD0", "comp": "dom-input", "value": "LO GIA HUY"},
        {"id": "cboDATE_FORMAT_CUNGTD0", "comp": "dom-select", "value": "Năm"},
        {"id": "txtDOB_CUNGTD0", "comp": "dom-input", "value": "2019"},
        {"id": "cboGENDER_CUNGTD0", "comp": "dom-select", "value": "Nam"},
        {"id": "txtIDENTIFIER_NOCARD_NUMBER_CUNGTD0", "comp": "dom-input", "value": "012219000888"},
        {"id": "cboRELATIONSHIP_CHUHO_CUNGTD0", "comp": "dom-select", "value": "Con"},
    ]]


def test_runner_dung_mapper(monkeypatch):
    async def fake_run(files_by_role, **kwargs):
        assert kwargs["comp_by_name"]["ThanhVien"] == "x-array" and "TruongHop" in kwargs["allowed"]
        return {"fields": [{"name": k, "value": v} for k, v in PERSON.items()]}

    monkeypatch.setattr(process_runner.runner, "run", fake_run)
    res = asyncio.run(process_runner.run({}, {}))
    assert {f["name"] for f in res["fields"]} >= {"cboRECEIVE_ORG", "cboBPROC_CASE_CODE", "txtFULLNAME"}


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


def test_link_registry_va_nhan_dien_trang_chung_voi_tam_tru():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.010028" and "TT=TAMTRU_06" in link["url"]
    proc = registry.get_procedure(KEY)
    assert registry.get_pipeline(KEY) is not None
    # Có đính kèm + tách giấy tờ (user 20/11/2026).
    assert proc["hasAttachmentStep"] is True and proc["supportsSplitDocuments"] is True
    assert registry.get_attach_pipeline(KEY) is attach.plan
    # Cùng trang dang-ky-tam-tru.html: _06 → thủ tục này, _01 vẫn là đăng ký tạm trú.
    assert _detect(link["url"]) == KEY
    assert _detect(next(item for item in KE_KHAI_LINKS if item["key"] == "dang-ky-tam-tru")["url"]) == \
        "dang-ky-tam-tru"


def test_entry_tro_ly_cung_key_toan_quoc_dinh_kem_cung_trang_hoi_truoc():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.intents import Intent

    hf = handfree.get_procedure(KEY)
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert hf["keKhaiUrl"] == link["url"] and hf["detect"] == registry.get_procedure(KEY)["detect"]
    assert hf["bcaPortal"] is True and hf["submitCommitCheckbox"] == "chkCHECK_LIABILITY"
    # Đính kèm cùng trang nhưng HỎI trước như tách hộ; điền lại ở bước cuối là điền tờ khai, không đính lại.
    assert hf["hasAttachmentStep"] is True and hf["samePageAttach"] is True and hf["askBeforeAttach"] is True
    assert hf["supportsSplitDocuments"] is True and hf["docsAdjustRefill"] is True and "provinceOnly" not in hf
    assert flow.refill_at_done(hf)
    assert handfree._HOAN_THIEN_THEO_TINH[KEY] == handfree._TAT_CA
    conv = {"state": "greet", "procedure_key": None,
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "lai_chau", "ward": "Phường Đoàn Kết"}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True}))
    assert "nơi đang đăng ký tạm trú" in r.display_md
    # Trang có sẵn bảng giấy tờ đính kèm → giấy tờ nhận ở bước này vẫn để điền tờ khai trước.
    page = {"attachmentTarget": True, "attachmentComponentCount": 2, "bcaAgencyBlock": True}
    conv = {"state": "collecting_docs", "procedure_key": KEY, "agency_done": True}
    assert flow._resolve_docs_target(hf, page, conv) == "declaration"


def test_tro_ly_dien_xong_dung_hoi_roi_moi_dinh_kem():
    from unittest import mock

    from app.channels.handfree.chat import pipeline_runner, tracing
    from app.channels.handfree.chat.intents import Intent

    conv = {"_id": "c1", "state": "filling", "procedure_key": KEY, "docs_target": "declaration",
            "auto_attach_after_fill": True, "upload_session_id": "s1", "location": {}, "client_capabilities": {}}
    with mock.patch.object(pipeline_runner, "spawn") as spawn, \
            mock.patch.object(tracing, "set_report", mock.AsyncMock()):
        r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {"filled": 9})))
    # Điền xong KHÔNG tự đính, dừng ở rà soát với nút đi tiếp.
    assert not spawn.called and conv["state"] == "reviewing"
    assert r.chips[0]["send"] == "__action:confirm_review"
    # Công dân bấm "Đính kèm giấy tờ" → chạy planner đính ngay trên trang.
    conv = {"_id": "c1", "state": "reviewing", "procedure_key": KEY, "docs_target": "declaration",
            "upload_session_id": "s1", "location": {}}
    with mock.patch.object(pipeline_runner, "spawn") as spawn, \
            mock.patch.object(pipeline_runner, "run_attach", mock.MagicMock(return_value=None)):
        asyncio.run(flow._handle_reviewing(conv, Intent("action", "confirm_review")))
    assert spawn.called and conv["state"] == "attaching" and conv["attachment_plan_started"]


# ── Trợ lý: chọn xong cơ quan → hỏi Trường hợp (cổng chưa hiện tờ khai) → chọn hộ → mới sang giấy tờ ──
def _conv_after_agency(caps=None):
    from app.channels.handfree.chat.intents import Intent

    conv = {"state": "greet", "procedure_key": None, "client_capabilities": dict(caps or {}),
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "lai_chau", "ward": "Phường Đoàn Kết"}}
    flow._to_confirm_procedure(conv, KEY)
    conv["state"] = "guide_login"
    flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True}))
    r = flow._handle_guide_login(conv, Intent("event", "bca_agency_result",
                                              {"ok": True, "ward": "Phường Đoàn Kết", "province": "Tỉnh Lai Châu"}))
    return conv, r


def test_tro_ly_chon_co_quan_xong_hoi_truong_hop_bang_nut():
    from app.channels.handfree.chat.intents import Intent
    from app.pipelines.xoa_dang_ky_tam_tru.process.schema import CASES

    conv, r = _conv_after_agency({"supportsBcaCase": True})
    # Chưa sang bước giấy tờ: hỏi Trường hợp, 6 nút đúng nhãn trên cổng (= nhãn mapper dùng).
    assert conv["state"] == "guide_login" and conv["bca_case_pending"] is True and conv["agency_done"] is True
    assert [c["label"] for c in r.chips] == list(CASES)
    assert r.chips[4]["send"] == "__action:bca_case:4"
    assert "Đã chọn Cơ quan thực hiện" in r.actions[0]["md"] and "Trường hợp" in r.display_md
    assert flow.build_progress(conv)["label"] == "Chọn trường hợp"
    # Trang đổi (cổng nạp lại ô) trong lúc hỏi → không hỏi lặp.
    again = flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True,
                                                                            "bcaAgencyDone": True}))
    assert not again.display_md and not again.chips
    # Bấm nút → extension chọn ô Trường hợp trên trang.
    r = flow._handle_guide_login(conv, Intent("action", "bca_case", {"value": 4}))
    assert r.actions == [{"type": "bca_select_case", "label": CASES[4], "id": "cboBPROC_CASE_CODE"}]
    assert conv["bca_case"] == CASES[4] and conv["state"] == "guide_login"
    # Chọn xong → sang bước giấy tờ, kèm câu đã chọn.
    r = flow._handle_guide_login(conv, Intent("event", "bca_case_result", {"ok": True}))
    assert conv["state"] == "consent" and "Đã chọn Trường hợp" in r.actions[0]["md"]


def test_tro_ly_ban_cu_khong_chon_ho_duoc_thi_dan_chon_tay_roi_sang_giay_to():
    from app.channels.handfree.chat.intents import Intent

    conv, _ = _conv_after_agency()
    r = flow._handle_guide_login(conv, Intent("action", "bca_case", {"value": 0}))
    assert conv["state"] == "consent" and "chọn giúp tôi ô **Trường hợp**" in r.actions[0]["md"]
    # Gõ linh tinh lúc đang hỏi → nhắc kèm lại các nút.
    conv, _ = _conv_after_agency()
    r = flow._handle_guide_login(conv, Intent("unknown", "", {"free_text": True}))
    assert len(r.chips) == 6 and conv["bca_case_pending"] is True


def test_truong_hop_cong_dan_chon_di_vao_pipeline_va_thang_nhan_llm():
    from app.channels.handfree.procedure_registry import case_pipeline_options, get_procedure

    chosen = "Hộ do vắng mặt từ 6 tháng trở lên"
    options = case_pipeline_options(get_procedure(KEY), {"bca_case": chosen})
    assert options == {"bcaCase": chosen}
    assert _by(PERSON, options)["cboBPROC_CASE_CODE"]["value"] == chosen
    # Nhãn lạ không lọt vào pipeline.
    assert case_pipeline_options(get_procedure(KEY), {"bca_case": "Khác"}) == {}


def test_thu_tuc_bo_cong_an_khac_chon_co_quan_xong_sang_thang_giay_to():
    from app.channels.handfree.chat.intents import Intent

    conv = {"state": "guide_login", "procedure_key": "dang-ky-tam-tru", "client_capabilities": {},
            "location": {"province": "Tỉnh Lai Châu", "ward": "Phường Đoàn Kết"}}
    flow._handle_guide_login(conv, Intent("event", "bca_agency_result",
                                          {"ok": True, "ward": "Phường Đoàn Kết", "province": "Tỉnh Lai Châu"}))
    assert conv["state"] == "consent" and not conv.get("bca_case_pending")


# ── Đính kèm (ảnh chạy thật 20/11/2026, trường hợp không còn chỗ ở hợp pháp: dòng Tờ khai + dòng chứng minh không còn
# chỗ ở hợp pháp, nút "+ Thêm mới" dưới bảng) ──
# Bộ hồ sơ gộp một PDF: tờ khai, biên bản thanh lý hợp đồng thuê 2 trang, thông báo kết quả đăng ký thường trú, CCCD.
_PAGES = ["TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ", "BIÊN BẢN THANH LÝ HỢP ĐỒNG THUÊ NHÀ", "Các bên ký tên",
          "THÔNG BÁO KẾT QUẢ GIẢI QUYẾT ĐĂNG KÝ THƯỜNG TRÚ", "CĂN CƯỚC CÔNG DÂN"]
_OCR = "\n".join(f"───── Trang {i + 1}/{len(_PAGES)} ─────\n{t}\nTrang {i + 1} / {len(_PAGES)}"
                 for i, t in enumerate(_PAGES))
_DOCS = [
    {"fileIndex": 0, "pages": [1], "docType": "to_khai", "documentName": "Tờ khai thay đổi thông tin cư trú"},
    {"fileIndex": 0, "pages": [2, 3], "docType": "cho_o", "documentName": "Biên bản thanh lý hợp đồng thuê nhà"},
    {"fileIndex": 0, "pages": [4], "docType": "thuong_tru", "documentName": "Thông báo kết quả đăng ký thường trú"},
    {"fileIndex": 0, "pages": [5], "docType": "cccd", "documentName": "Thẻ căn cước", "matThe": "ca_hai",
     "chuThe": "HOANG THI MAI"},
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
        (ROWS["cho_o"]["rowKey"], False, [1, 2]),
        # Giấy có loại rõ mà bảng không có dòng → dòng "+ Thêm mới" mang tên giấy.
        (items[2]["componentName"], True, [3]),
        (items[3]["componentName"], True, [4]),
    ]
    assert items[2]["componentName"] == items[2]["documentName"] and "thường trú" in items[2]["componentName"]
    assert sorted(p for i in items for s in i["sourceSegments"] for p in s["pageIndexes"]) == list(range(5))
    assert all(i["target"] == "bca-row" and i["bcaPlainTable"] is True for i in items)
    assert items[0]["rowFields"] == {"count": "01"} and not res["errors"]


def test_tat_tach_thi_dinh_nguyen_tep_vao_moi_dong_kem_ghi_chu(monkeypatch):
    _patch(monkeypatch, _DOCS)
    for options in ({}, {"splitDocuments": "true"}, None):
        res = asyncio.run(attach.plan(_files("hoso.pdf"), options))
        items = res["attachments"]
        assert all("sourceSegments" not in i and i["fileIndex"] == 0 for i in items)
        assert [(i["rowKey"], i["newRow"]) for i in items] == [
            (ROWS["to_khai"]["rowKey"], False), (ROWS["cho_o"]["rowKey"], False), ("", True)]
        assert items[1]["rowFields"]["note"] == (
            "Đính kèm chung tệp hoso.pdf (5 trang): Biên bản thanh lý hợp đồng thuê nhà tại trang 2–3/5")
        # Mọi giấy không có dòng của cùng tệp → MỘT dòng "+" liệt kê tên giấy.
        assert items[2]["componentName"] == "Thông báo kết quả đăng ký thường trú, Thẻ căn cước"
        assert items[2]["rowFields"]["note"].endswith("tại trang 4–5/5")


def test_dong_tren_cong_khop_ten_dong_trong_anh():
    # Chữ dòng trên cổng (ảnh 20/11/2026), so như extension: bỏ dấu, bỏ dấu câu, chứa rowKey.
    from app.pipelines._shared import fold

    for label, row in (("Tờ khai thay đổi thông tin cư trú", "to_khai"),
                       ("Giấy tờ chứng minh về việc không còn chỗ ở hợp pháp", "cho_o")):
        assert ROWS[row]["rowKey"] in fold(label), label


def test_ke_hoach_qua_duoc_response_model(monkeypatch):
    from app.attachments.schemas import AttachmentPlanResp

    _patch(monkeypatch, _DOCS)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {}))
    out = AttachmentPlanResp.model_validate(res).model_dump(mode="json")["attachments"]
    assert out[0]["rowKey"] == ROWS["to_khai"]["rowKey"] and out[0]["bcaPlainTable"] is True
    assert out[2]["newRow"] is True and out[2]["componentName"].startswith("Thông báo kết quả")


def test_giay_chua_ro_loai_vao_dong_to_khai_canh_bao():
    # Dòng chứng minh chỗ ở chỉ có ở trường hợp không còn chỗ ở hợp pháp → giấy chưa rõ loại vào dòng Tờ khai (luôn có).
    items, warnings, _ = khong_tach.build_plan_items(["bia.pdf"], {0: 1}, [{"fileIndex": 0, "pages": [1],
                                                                           "docType": "other"}])
    assert items[0]["rowKey"] == ROWS["to_khai"]["rowKey"] and "bia.pdf" in warnings[0]


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
    assert any("kiểm tra lại" in e for e in res["errors"])


# ── Bảng theo Trường hợp (ảnh user 24/11/2026): hai trường hợp không còn chỗ ở hợp pháp có dòng 2; vắng mặt / đã đăng ký
# thường trú tại chính nơi tạm trú CHỈ có dòng Tờ khai ──
def _ct01_ocr(reason: str, *more_pages: str) -> str:
    pages = [
        "TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ\n1. Họ, chữ đệm và tên: TRẦN THỊ BÌNH\n"
        f"10. Nội dung đề nghị(2): {reason}\n11. Những thành viên trong hộ gia đình cùng thay đổi:\n"
        "Ý KIẾN CỦA CHỦ HỘ  Ý KIẾN CỦA CHỦ SỞ HỮU CHỖ Ở HỢP PHÁP  Ý KIẾN CỦA CHA, MẸ HOẶC NGƯỜI GIÁM HỘ\n"
        "(2) Ghi rõ ràng, cụ thể nội dung đề nghị. Ví dụ: đăng ký thường trú; đăng ký tạm trú; xóa đăng ký thường trú",
        *more_pages,
    ]
    return "\n".join(f"───── Trang {i + 1}/{len(pages)} ─────\n{t}" for i, t in enumerate(pages))


_PERMANENT = "Đề nghị xóa đăng ký tạm trú do đã đăng ký thường trú tại nơi tạm trú"


def test_bang_theo_truong_hop_doc_ly_do_o_muc_10_to_khai():
    def has_row(reason, options=None):
        return khong_tach.table_has_no_home_row({0: khong_tach.ocr_pages(_ct01_ocr(reason))}, options)

    assert has_row("Xóa đăng ký tạm trú do hết hạn hợp đồng thuê nhà") is True
    assert has_row("Đề nghị xóa đăng ký tạm trú do không còn chỗ ở hợp pháp") is True
    # Khối "Ý kiến của chủ sở hữu chỗ ở hợp pháp" sau mục 11 và chú thích "(2)… đăng ký thường trú" không được tính.
    assert has_row(_PERMANENT) is False
    assert has_row("Xóa đăng ký tạm trú do vắng mặt liên tục từ 6 tháng trở lên") is False
    assert has_row("…………") is None
    assert khong_tach.table_has_no_home_row({0: ["CĂN CƯỚC CÔNG DÂN"]}) is None
    # Trợ lý: Trường hợp công dân chọn thắng lý do trên giấy.
    assert has_row(_PERMANENT, {"bcaCase": "Cả hộ do không còn chỗ ở hợp pháp"}) is True
    assert has_row("do hết hạn hợp đồng thuê", {"bcaCase": "Hộ do vắng mặt từ 6 tháng trở lên"}) is False


def _patch_ocr(monkeypatch, text, documents):
    async def fake_ocr(files):
        return [{"text": text} for _ in files]

    async def fake_chat(messages, max_tokens=None, **_):
        return json.dumps({"documents": documents})

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(llm_client, "chat", fake_chat)


_PERMANENT_DOCS = [
    {"fileIndex": 0, "pages": [1], "docType": "to_khai", "documentName": "Tờ khai thay đổi thông tin cư trú"},
    {"fileIndex": 0, "pages": [2], "docType": "cho_o", "documentName": "Biên bản thanh lý hợp đồng thuê nhà"},
]


def test_truong_hop_da_dang_ky_thuong_tru_giay_cho_o_vao_dong_them_moi(monkeypatch):
    # Bảng chỉ có dòng Tờ khai → giấy chứng minh chỗ ở không tìm dòng 2 (extension sẽ báo "Không thấy dòng").
    _patch_ocr(monkeypatch, _ct01_ocr(_PERMANENT, "BIÊN BẢN THANH LÝ HỢP ĐỒNG THUÊ NHÀ"), _PERMANENT_DOCS)
    for options in ({}, {"splitDocuments": True}):
        items = asyncio.run(attach.plan(_files("hoso.pdf"), options))["attachments"]
        assert [(i["rowKey"], i["newRow"]) for i in items] == [(ROWS["to_khai"]["rowKey"], False), ("", True)], options
        assert items[1]["componentName"] == "Biên bản thanh lý hợp đồng thuê nhà"
        assert all(i["rowKey"] != ROWS["cho_o"]["rowKey"] for i in items)


def test_truong_hop_khong_con_cho_o_van_vao_dong_2(monkeypatch):
    _patch_ocr(monkeypatch, _ct01_ocr("Xóa tạm trú do hết hạn hợp đồng thuê", "BIÊN BẢN THANH LÝ HỢP ĐỒNG THUÊ NHÀ"),
               _PERMANENT_DOCS)
    for options in ({}, {"splitDocuments": True}):
        items = asyncio.run(attach.plan(_files("hoso.pdf"), options))["attachments"]
        assert [(i["rowKey"], i["newRow"]) for i in items] == [
            (ROWS["to_khai"]["rowKey"], False), (ROWS["cho_o"]["rowKey"], False)], options


def test_ghi_chu_dong_to_khai_theo_anh_anh_xa(monkeypatch):
    # Ảnh ánh xạ 24/11: hồ sơ một tệp CT01 1 trang → dòng Tờ khai, Ghi chú nêu người đề nghị + các ý kiến; dòng 2 để trống.
    docs = [{"fileIndex": 0, "pages": [1], "docType": "to_khai", "documentName": "Tờ khai thay đổi thông tin cư trú",
             "nguoiDeNghi": "TRẦN THỊ BÌNH", "yKienChuHo": "Trần Thị Bình", "yKienChuSoHuu": "LÊ VĂN CƯỜNG",
             "yKienChaMe": "……………"}]
    _patch_ocr(monkeypatch, _ct01_ocr(_PERMANENT), docs)
    for options in ({}, {"splitDocuments": True}):
        items = asyncio.run(attach.plan(_files("CT01.pdf"), options))["attachments"]
        assert [i["rowKey"] for i in items] == [ROWS["to_khai"]["rowKey"]], options
        assert items[0]["rowFields"] == {
            "count": "01",
            "note": "Tờ khai CT01 bản gốc (1 trang) của Trần Thị Bình, kèm ý kiến chủ hộ Trần Thị Bình, chủ sở hữu "
                    "chỗ ở hợp pháp Lê Văn Cường",
        }, options
    # LLM không đọc được tên người đề nghị → không dựng câu.
    assert khong_tach.to_khai_note({"nguoiDeNghi": "…"}, 1) == ""


def test_tep_gop_ghi_chu_to_khai_kem_cau_dinh_kem_chung(monkeypatch):
    docs = [{**_PERMANENT_DOCS[0], "nguoiDeNghi": "Trần Thị Bình"}, _PERMANENT_DOCS[1]]
    _patch_ocr(monkeypatch, _ct01_ocr(_PERMANENT, "BIÊN BẢN THANH LÝ HỢP ĐỒNG THUÊ NHÀ"), docs)
    items = asyncio.run(attach.plan(_files("hoso.pdf"), {}))["attachments"]
    assert items[0]["rowFields"]["note"] == (
        "Tờ khai CT01 bản gốc (1 trang) của Trần Thị Bình; Đính kèm chung tệp hoso.pdf (2 trang): Tờ khai thay đổi "
        "thông tin cư trú tại trang 1/2")
