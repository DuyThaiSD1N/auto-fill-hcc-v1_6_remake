"""Đăng ký thường trú (Cổng DVC Bộ Công an): mapper ô form + nối registry + luồng trợ lý."""
from app.channels.handfree.chat import flow
from app.channels.handfree.chat.intents import Intent
from app.pipelines.dang_ky_thuong_tru.process import mapper
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "dang-ky-thuong-tru"
PERSON = {
    "CoQuan_Tinh": "Hà Nội", "CoQuan_Xa": "Phường Ba Đình",
    "TruongHop": "nhân khẩu", "HinhThuc": "vào hộ đã có",
    "NguoiDangKy_HoTen": "Tran Thi B", "NguoiDangKy_NgaySinh": "5/3/1998", "NguoiDangKy_GioiTinh": "Nữ",
    "NguoiDangKy_SoDinhDanh": "0011 9800 0002", "NguoiDangKy_SoDienThoai": "0912 345 678",
    "ChuHo_HoTen": "Nguyen Van A", "ChuHo_QuanHe": "Vợ", "ChuHo_SoDinhDanh": "001090000001",
    "NoiDangKy_DiaChiChiTiet": "Số 1 ngõ 2, phường Ba Đình, thành phố Hà Nội",
    "NoiDungDeNghi": "Đăng ký thường trú vào hộ chồng",
    "ThanhVien": [{"hoTen": "Nguyen Van C", "ngaySinh": "1/2/2023", "gioiTinh": "Nam", "soDinhDanh": "001223000003",
                   "quanHeVoiChuHo": "Con"}],
}


def _enrich(values: dict, options=None) -> list[dict]:
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def test_thu_tu_va_gia_tri_o_form():
    out = _enrich(PERSON)
    by = {f["name"]: f for f in out}
    names = [f["name"] for f in out]
    # Cơ quan → Trường hợp → Hình thức trước khối người đề nghị; định dạng trước ngày sinh; nội dung sau địa chỉ.
    assert names[:3] == ["cboORG", "cboBPROC_CASE_CODE", "radIsHouseHold"]
    assert names.index("cboFORMAT_DATE") < names.index("txtBIRTH_DATE") < names.index("txtFULLNAME")
    assert names.index("txtSUGGEST_DETAIL_ADDR") < names.index("txtCHANGED_CONTENT_NOTE")
    agency = by["cboORG"]
    assert agency["comp"] == "bca-agency" and agency["onlyIfEmpty"] is True
    assert agency["value"] == {"province": "Thành phố Hà Nội", "ward": "Phường Ba Đình",
                               "cityId": "cboRECEIVE_ADDR_CITY_ID", "wardId": "cboRECEIVE_ADDR_VILLAGE_ID",
                               "readySelect": "cboBPROC_CASE_CODE"}
    assert by["cboBPROC_CASE_CODE"]["value"] == "Đăng ký thường trú nhân khẩu"
    assert by["radIsHouseHold"]["value"] == "Đăng ký thường trú vào hộ đã có"
    assert by["txtBIRTH_DATE"]["value"] == "05/03/1998" and by["cboFORMAT_DATE"]["value"] == "Ngày tháng năm"
    assert by["txtID_CARD_NUMBER"]["value"] == "001198000002"
    assert by["txtSUGGEST_DETAIL_ADDR"]["value"] == "Số 1 ngõ 2"
    assert by["cboRELATIONSHIP_WITH_HHHEAD_ID"]["value"] == "Vợ"
    rows = by["tblNguoi_CUNGTD"]["value"]["rows"]
    assert {c["id"]: c["value"] for c in rows[0]} == {
        "txtFULLNAME_CUNGTD0": "NGUYEN VAN C", "txtDOB_CUNGTD0": "01/02/2023", "cboGENDER_CUNGTD0": "Nam",
        "txtIDENTIFIER_NOCARD_NUMBER_CUNGTD0": "001223000003", "cboRELATIONSHIP_CHUHO_CUNGTD0": "Con"}


def test_lap_ho_moi_khong_dien_khoi_chu_ho():
    out = {f["name"]: f["value"] for f in _enrich({**PERSON, "HinhThuc": "lập hộ mới", "ChuHo_QuanHe": "Chủ hộ"})}
    assert out["radIsHouseHold"] == "Đăng ký thường trú lập hộ mới"
    assert not {"txtHH_HEAD_FULLNAME", "cboRELATIONSHIP_WITH_HHHEAD_ID", "txtID_CARD_NUMBER_HHEAD"} & set(out)


def test_lan_dau_thi_cong_ep_vao_ho_da_co():
    out = {f["name"]: f["value"] for f in _enrich({**PERSON, "TruongHop": "lần đầu", "HinhThuc": "lập hộ mới"})}
    assert out["radIsHouseHold"] == "Đăng ký thường trú vào hộ đã có"


def test_giay_khong_ghi_co_quan_thi_lay_xa_tai_khoan_to_vang():
    values = {k: v for k, v in PERSON.items() if not k.startswith("CoQuan_")}
    options = mapper.with_account_process_options({}, {"tinh": "Tỉnh Mẫu", "xa": "Phường Mẫu"}, KEY)
    agency = next(f for f in _enrich(values, options) if f["name"] == "cboORG")
    assert agency["value"]["ward"] == "Phường Mẫu" and agency["default"] is True


def test_registry_link_va_entry_handfree():
    from app.channels.handfree.procedure_registry import get_procedure

    assert registry.get_pipeline(KEY) is not None
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.004222" and get_procedure(KEY)["keKhaiUrl"] == link["url"]
    hf = get_procedure(KEY)
    assert hf["submitCommitCheckbox"] == "chkRULE" and hf["requiresCapability"] == "supportsBcaThuongTru"


def test_tro_ly_ban_cu_thi_bao_cap_nhat_ban_moi_hoi_noi_dang_ky_thuong_tru():
    conv = {"state": "greet", "procedure_key": None, "location": {}}
    r = flow._to_confirm_procedure(conv, KEY)
    assert "chưa hỗ trợ" in r.display_md
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": {"supportsBcaThuongTru": True},
            "location": {"province": "Thành phố Hà Nội", "province_slug": "ha_noi", "ward": "Phường Ba Đình"}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True}))
    assert "nơi đăng ký thường trú" in r.display_md and "tạm trú" not in r.display_md


def test_luat_bat_nut_nop_trang_thuong_tru():
    import re

    from app.procedures.portal_submit import portal_submit_rules

    rule = portal_submit_rules()["dichvucong.dancuquocgia.gov.vn"]
    assert re.match(rule["urlPattern"], "/portal/p/home/dang-ky-thuong-tru.html")
    assert "btn_Save_Send" in rule["buttonIds"]



# ── Đính kèm ──
from app.pipelines.dang_ky_thuong_tru.attach import planner  # noqa: E402

FILES = [{"name": n} for n in ("to-khai.pdf", "ket-hon.pdf", "khai-sinh.pdf", "cccd.jpg")]


def test_planner_nhom_chu_ho_dong_y_giay_quan_he_vao_dong_them_moi():
    llm = {"case": "consented", "documents": [
        {"index": 0, "docType": "to_khai"}, {"index": 1, "docType": "quan_he", "documentName": "Giấy chứng nhận kết hôn"},
        {"index": 2, "docType": "quan_he", "documentName": "Giấy khai sinh"}, {"index": 3, "docType": "cccd"}]}
    kinds, names, case, source = planner.resolve(len(FILES), llm)
    items, warnings, _ = planner.build_plan_items(FILES, kinds, names, case)
    assert source == "llm" and {i["groupIndex"] for i in items} == {2}
    assert [i["rowKey"] for i in items] == ["to khai thay doi thong tin cu tru", "", "", "to khai thay doi thong tin cu tru"]
    assert items[1]["newRow"] and items[1]["componentName"] == items[2]["componentName"] == "Giấy tờ chứng minh quan hệ nhân thân"
    assert items[1]["documentName"] == "Giấy chứng nhận kết hôn"
    assert len(items) == len(FILES) and "cccd.jpg" in warnings[0], "không bỏ sót tệp nào"


def test_planner_thue_muon_co_dong_hop_dong_va_dien_tich():
    llm = {"case": "rented", "documents": [{"index": 0, "docType": "hop_dong"}, {"index": 1, "docType": "dien_tich"}]}
    kinds, names, case, _ = planner.resolve(2, llm)
    items, _, _ = planner.build_plan_items(FILES[:2], kinds, names, case)
    assert [i["rowKey"] for i in items] == ["hop dong cho thue", "du dien tich nha o"] and items[0]["groupIndex"] == 3


def test_planner_llm_loi_van_dinh_du_tep_va_bao_can_bo():
    kinds, names, case, source = planner.resolve(len(FILES), {})
    items, warnings, _ = planner.build_plan_items(FILES, kinds, names, case)
    assert source == "default" and len(items) == len(FILES)
    assert all(i["rowKey"] == "to khai thay doi thong tin cu tru" for i in items)
    assert registry.get_attach_pipeline(KEY) is not None


# ── Trợ lý: "Điều chỉnh giấy tờ" sau khi đã đính = điền lại tờ khai, đính lại là lệnh riêng (user 20/11/2026) ──
def _adjust_mocks(monkeypatch, calls):
    from app.channels.handfree.chat import pipeline_runner, tracing

    async def noop(*_a, **_k):
        return None

    async def reopen(sid):
        return {"_id": sid, "files": [{"name": "to-khai.pdf"}]}

    async def progress(_sid):
        return {"received": 3, "total": 3, "files_count": 3}

    monkeypatch.setattr(pipeline_runner, "run_process", lambda *a: calls.append("process"))
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a: calls.append("attach"))
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)
    monkeypatch.setattr(tracing, "set_report", noop)
    monkeypatch.setattr(flow.conv_store, "save", noop)
    monkeypatch.setattr(flow.up_store, "reopen_for_supplement", reopen)
    monkeypatch.setattr(flow.upload_service, "sync_for_conversation", noop)
    monkeypatch.setattr(flow.upload_service, "complete_session", noop)
    monkeypatch.setattr(flow.upload_service, "progress_of", progress)


def test_tro_ly_dieu_chinh_giay_to_sau_dinh_kem_la_dien_lai_khong_dinh_lai(monkeypatch):
    import asyncio

    from app.channels.handfree.procedure_registry import get_procedure

    # Mọi thủ tục Bộ Công an có đính kèm khai cờ (tách hộ thêm 20/11/2026 khi trợ lý đã đính kèm).
    for key in ("dang-ky-tam-tru", KEY, "dieu-chinh-thong-tin-ve-cu-tru", "dang-ky-mau-con-dau",
                "cap-ho-chieu-pho-thong-o-trong-nuoc", "cap-thi-thuc-cho-nguoi-nuoc-ngoai-tai-viet-nam",
                "cap-the-tam-tru-cho-nguoi-nuoc-ngoai-tai-viet-nam", "trinh-bao-mat-ho-chieu-pho-thong-cap-xa",
                "trinh-bao-mat-ho-chieu-pho-thong-cap-tinh", "tach-ho"):
        assert get_procedure(key).get("docsAdjustRefill") is True, key

    calls = []
    _adjust_mocks(monkeypatch, calls)
    caps = {"supportsFieldReview": True, "supportsBcaFlow": True, "supportsTickCommit": True,
            "supportsPageBoundDocsComplete": True}
    conv = {"_id": "c-adj", "state": "done", "history": [], "procedure_key": KEY, "upload_session_id": "s1",
            "docs_target": "attachment", "attach_done": True, "fields": [{"name": "x"}], "location": {},
            "client_capabilities": caps}
    r = asyncio.run(flow._handle_turn_inner(conv, Intent("action", "add_documents", {})))
    assert conv["documents_adjustment_target"] == "declaration"
    assert [c["label"] for c in r.chips] == ["✅ Hoàn tất điều chỉnh, điền lại tờ khai"]
    assert "Đính kèm lại" in r.display_md and conv["attach_done"] is True

    # Chốt giấy tờ (trang báo form + bảng cùng trang) → chỉ điền lại, không đính.
    page = {"pageContextCaptured": True, "formKind": "standard", "attachmentTarget": True, "bcaAgencyBlock": True}
    asyncio.run(flow._docs_complete(conv, page))
    assert calls == ["process"] and conv["auto_attach_after_fill"] is False

    # Điền xong: về bước cuối, nút tích cam kết + Đính kèm lại; không có "Đính kèm giấy tờ ▶".
    r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {
        "filled": 9, "review": {"filled": 9, "optional": 0, "required": 0}})))
    sends = [c["send"] for c in r.chips]
    assert calls == ["process"] and conv["state"] == "done"
    assert "__action:reattach" in sends and "__action:confirm_review" not in sends
    assert [c["send"] for c in r.chips if c.get("cta")] == ["__action:tick_commit"]
    assert not conv.get("supplementing_documents")

    # "Đính kèm lại" là lệnh riêng: chỉ đính, không điền lại.
    asyncio.run(flow._handle_turn_inner(conv, Intent("action", "reattach", {})))
    assert calls == ["process", "attach"]


def test_tro_ly_mo_dieu_chinh_giay_to_trang_bao_bang_dinh_kem_khong_tu_chot(monkeypatch):
    """Ảnh chạy thật 20/11 (1.010039): vừa mở "Điều chỉnh giấy tờ", watcher gửi page_status của trang (form + bảng
    #tblGiayToDinhKem cùng trang) → trước đây coi là công dân tự sang bước đính kèm, tự chốt phiên và đính lại khi công
    dân chưa kịp thêm / xoá tệp. Phải đứng chờ tới khi bấm "Hoàn tất điều chỉnh, điền lại tờ khai"."""
    import asyncio

    for key in ("dieu-chinh-thong-tin-ve-cu-tru", KEY, "dang-ky-tam-tru"):
        calls = []
        _adjust_mocks(monkeypatch, calls)
        caps = {"supportsFieldReview": True, "supportsBcaFlow": True, "supportsTickCommit": True,
                "supportsPageBoundDocsComplete": True}
        page = {"pageContextCaptured": True, "formKind": "standard", "attachmentTarget": True,
                "attachmentComponentCount": 3, "bcaAgencyBlock": True, "loggedIn": True}
        conv = {"_id": "c-adj4", "state": "done", "history": [], "procedure_key": key, "upload_session_id": "s1",
                "docs_target": "attachment", "attach_done": True, "fields": [{"name": "x"}], "location": {},
                "client_capabilities": caps, "docs_page_context": flow._docs_page_context(page)}
        asyncio.run(flow._handle_turn_inner(conv, Intent("action", "add_documents", {})))
        assert conv["documents_adjustment_target"] == "declaration", key

        asyncio.run(flow._handle_turn_inner(conv, Intent("event", "page_status", dict(page))))
        assert calls == [], key
        assert conv["state"] == "ask_doc_method" and conv["supplementing_documents"] is True, key
        assert conv["documents_adjustment_target"] == "declaration" and conv["docs_target"] == "declaration", key

        # Bấm nút hoàn tất mới chạy: điền lại tờ khai, không đính lại.
        asyncio.run(flow._handle_turn_inner(conv, Intent("action", "docs_done", dict(page))))
        assert calls == ["process"] and conv["auto_attach_after_fill"] is False, key


def test_tro_ly_dieu_chinh_giay_to_truoc_dinh_kem_van_hoi_dinh_kem(monkeypatch):
    """Chưa đính lần nào (đang rà soát sau điền): điều chỉnh xong điền lại rồi hỏi đính kèm như lượt đầu."""
    import asyncio

    calls = []
    _adjust_mocks(monkeypatch, calls)
    caps = {"supportsFieldReview": True, "supportsBcaFlow": True, "supportsTickCommit": True}
    conv = {"_id": "c-adj2", "state": "reviewing", "history": [], "procedure_key": KEY, "upload_session_id": "s1",
            "docs_target": "attachment", "location": {}, "client_capabilities": caps}
    asyncio.run(flow._handle_turn_inner(conv, Intent("action", "add_documents", {})))
    assert conv["documents_adjustment_target"] == "declaration" and not conv.get("refill_keeps_attach")
    asyncio.run(flow._docs_complete(conv))
    r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {
        "filled": 9, "review": {"filled": 9, "optional": 0, "required": 0}})))
    assert conv["state"] == "reviewing" and r.chips[0]["send"] == "__action:confirm_review"
    assert calls == ["process"]


def test_tro_ly_dien_lai_to_khai_o_buoc_cuoi_khong_dinh_lai(monkeypatch):
    """Ảnh chạy thật 20/11: nói "Điền lại tờ khai" sau khi đã đính trên trang thường trú thì trước đây bị nuốt."""
    import asyncio

    calls = []
    _adjust_mocks(monkeypatch, calls)
    conv = {"_id": "c-adj3", "state": "done", "history": [], "procedure_key": KEY, "upload_session_id": "s1",
            "docs_target": "attachment", "attach_done": True, "auto_attach_after_fill": True, "location": {},
            "client_capabilities": {"supportsFieldReview": True, "supportsBcaFlow": True}}
    asyncio.run(flow._handle_turn_inner(conv, Intent("action", "refill", {})))
    assert calls == ["process"] and conv["docs_target"] == "declaration"
    assert conv["auto_attach_after_fill"] is False and conv["refill_keeps_attach"] is True
