"""[BN] Đăng ký biện pháp bảo đảm QSDĐ (1.011441) — luồng handfree cổng Liferay Bắc Ninh.

Khác iGate: trang eForm có 2 tab CÙNG TRANG (Nhập đơn đăng ký / Tải thành phần hồ sơ,
không wizard) → samePageAttach: kê khai ưu tiên trước dù attachmentTarget luôn dương,
điền xong bot chạy planner đính kèm NGAY (watcher không bắn lại vì chữ ký trang không
đổi), attach xong chốt tóm tắt kết quả cả hai bước. Tỉnh chọn ở DVCQG CỐ ĐỊNH Bắc Ninh
(agencyProvince), không lấy tỉnh tài khoản."""
from app.channels.handfree.chat import flow, intents
from app.channels.handfree.chat.procedure_picker import prompt as picker_prompt
from app.channels.handfree.procedure_registry import (
    get_attach_pipeline,
    get_pipeline,
    get_procedure,
    public_list,
)

KEY = "dang-ky-bien-phap-bao-dam-bac-ninh"


def _conv(**kw):
    base = {
        "_id": "t-bpbd-bn", "state": "greet", "history": [],
        # Tài khoản tỉnh KHÁC để chứng minh agencyProvince thắng tỉnh tài khoản.
        "location": {"province": "Thành phố Hà Nội", "ward": "Phường Ba Đình"},
    }
    base.update(kw)
    return base


def test_registry_entry_same_page_va_pipeline_noi_core():
    proc = get_procedure(KEY)
    assert proc, "thiếu entry handfree"
    assert get_pipeline(KEY) and get_attach_pipeline(KEY), "key phải trùng core registry"
    assert proc["samePageAttach"] is True
    assert proc["agencyProvinceOnly"] and proc["agencySoFirst"]
    assert proc["agencyProvince"] == "Bắc Ninh"
    assert proc["agencyDeptLabel"] == "Văn phòng Đăng ký đất đai Bắc Ninh"
    assert "variants" not in proc and "maePortal" not in proc and "wizard" not in proc
    assert any(p["key"] == KEY for p in public_list())
    keys = [d["key"] for d in proc["requiredDocs"]]
    assert keys == ["don", "hop_dong", "gcn", "cccd", "khac"]
    assert KEY in picker_prompt.PROCEDURE_HINTS


async def test_confirm_navigate_va_thoai_doc_tinh_bac_ninh():
    conv = _conv()
    await flow.handle_turn(conv, intents.Intent("action", "pick_procedure", {"key": KEY}))
    r = await flow.handle_turn(conv, intents.Intent("confirm"))
    assert conv["state"] == "guide_login"
    assert r.actions and r.actions[0]["type"] == "navigate"
    # Câu hướng dẫn phải đọc tỉnh CỦA THỦ TỤC (Bắc Ninh), không phải tỉnh tài khoản (Hà Nội).
    assert "Bắc Ninh" in r.display_md and "Hà Nội" not in r.display_md
    assert "Văn phòng Đăng ký đất đai Bắc Ninh" in r.display_md


async def test_select_agency_tinh_co_dinh_bac_ninh_so_mode():
    conv = _conv(state="guide_login", procedure_key=KEY, milestones=[], agency_done=False)
    r = await flow.handle_turn(conv, intents.Intent("event", "page_status", {"agencyBlock": True}))
    action = r.actions[0]
    assert action["type"] == "select_agency"
    assert action["province"] == "Bắc Ninh", "agencyProvince phải thắng tỉnh tài khoản"
    assert action["ward"] == "" and action["soMode"] is True


def test_docs_target_uu_tien_ke_khai_du_attachment_target_duong():
    proc = get_procedure(KEY)
    # Trang BN: formKind bacninh + ô đính kèm CÙNG DOM → vẫn phải vào kê khai trước.
    ctx = {"formKind": "bacninh", "attachmentTarget": True}
    assert flow._resolve_docs_target(proc, ctx) == "declaration"
    # Trang luôn đủ điều kiện đính kèm (engine FE tự mở tab) — không phụ thuộc bảng/stepper.
    conv = {"procedure_key": KEY}
    assert flow._attachment_page_reached(conv, proc, ctx) is True
    assert flow._attachment_page_reached(conv, proc, {"formKind": "bacninh"}) is False


async def test_fill_report_chay_planner_dinh_kem_ngay_khong_cho_chuyen_buoc(monkeypatch):
    from app.channels.handfree.chat import pipeline_runner

    spawned = []

    def fake_spawn(coro):
        spawned.append(coro)
        coro.close()  # không chạy pipeline thật trong test

    monkeypatch.setattr(pipeline_runner, "spawn", fake_spawn)
    conv = _conv(
        state="filling", procedure_key=KEY, docs_target="declaration",
        upload_session_id="HS-BN", auto_attach_after_fill=True,
        pipeline_status="running",
    )
    r = await flow.handle_turn(
        conv, intents.Intent("action", "fill_report", {"filled": 12, "notFound": []}))
    assert conv["state"] == "attaching"
    # samePageAttach: KHÔNG waiting_attachment_page — planner phải được spawn ngay.
    assert conv["pipeline_status"] == "running"
    assert conv["attachment_plan_started"] is True
    assert len(spawned) == 1
    assert "Tải thành phần hồ sơ" in r.display_md
    assert "chuyển sang **Thành phần hồ sơ**" not in r.display_md


async def test_attach_report_tom_tat_ket_qua_hai_buoc():
    conv = _conv(
        state="attaching", procedure_key=KEY, docs_target="attachment",
        upload_session_id="HS-BN", attach_plan=[{"documentName": "Phiếu 01a"}],
        fill_report={"filled": 12, "notFound": [], "errors": []},
    )
    r = await flow.handle_turn(
        conv, intents.Intent("action", "attach_report", {"attached": 4, "errors": []}))
    assert conv["state"] == "done" and conv["attach_done"] is True
    assert "📋 **Đơn đăng ký**" in r.display_md
    # Lời đọc tạm bỏ con số (khối TTS-TẠM trong script_vi) — con số nằm ở phần hiển thị.
    assert "12 ô ✓" in r.display_md and "4 tệp" in r.display_md
    assert "điền đơn và đính kèm xong" in r.tts_text


_BN_AUTHORIZED_KEYS = (
    KEY, "xoa-dang-ky-bien-phap-bao-dam-bac-ninh", "dang-ky-bien-dong-dat-dai-bac-ninh",
    "dang-ky-bien-dong-thoa-thuan-bac-ninh", "ho-tro-chi-phi-hoa-tang-bac-ninh",
    "dang-ky-nha-o-xa-hoi-bac-ninh",
)


def test_khoi_uy_quyen_bac_ninh_chi_bat_khi_chon_doi_tuong_uy_quyen_va_client_moi():
    from app.channels.handfree.chat import pipeline_runner

    caps = {"supportsBacNinhAuthorizedPerson": True}
    for key in _BN_AUTHORIZED_KEYS:
        proc = get_procedure(key)
        for subject in ("authorized_person", "enterprise_authorized"):
            block = pipeline_runner._bac_ninh_authorized_block(
                proc, {"execution_subject": subject, "client_capabilities": caps})
            assert block and block["subjectOption"] == "Cá nhân khác là Công dân Việt Nam", key
        for subject in ("self", "other_person", "organization_representative", None):
            assert pipeline_runner._bac_ninh_authorized_block(
                proc, {"execution_subject": subject, "client_capabilities": caps}) is None, key
        # Extension cũ không biết mở khối → không chạy lượt người ủy quyền.
        assert pipeline_runner._bac_ninh_authorized_block(
            proc, {"execution_subject": "authorized_person", "client_capabilities": {}}) is None
    # Thủ tục Bắc Ninh không có logic điền khối ủy quyền thì không bật.
    assert pipeline_runner._bac_ninh_authorized_block(
        get_procedure("cap-doi-gcn-bac-ninh"),
        {"execution_subject": "authorized_person", "client_capabilities": caps}) is None


def test_capability_khoi_uy_quyen_bac_ninh_qua_whitelist():
    from app.channels.handfree.chat.router import _clean_client_capabilities

    assert _clean_client_capabilities(
        {"supportsBacNinhAuthorizedPerson": True})["supportsBacNinhAuthorizedPerson"] is True
    assert _clean_client_capabilities({})["supportsBacNinhAuthorizedPerson"] is False


async def test_luot_nguoi_uy_quyen_goi_purpose_authorized_person_va_gan_o_danh_dau():
    from app.channels.handfree.chat import pipeline_runner

    calls = []

    async def fake_pipeline(files_by_role, options):
        calls.append(options)
        return {"fields": [{"name": "doiTuongKhachoTen", "comp": "bn-input", "value": "Nguyễn Văn A"}],
                "errors": []}

    config = get_procedure(KEY)["bacNinhAuthorizedPerson"]
    out = await pipeline_runner._run_bac_ninh_authorized(
        fake_pipeline, {"": []}, {"formContext": {"x": 1}}, config)
    assert calls == [{"formContext": {"x": 1}, "purpose": "authorized_person"}]
    assert out["fields"][0] == {"name": "loaiDoiTuongKhac", "comp": "bn-doi-tuong-khac",
                                "value": "Cá nhân khác là Công dân Việt Nam"}
    assert [f["name"] for f in out["fields"]] == ["loaiDoiTuongKhac", "doiTuongKhachoTen"]

    # Không có văn bản ủy quyền → không ô nào, kể cả ô đánh dấu; lỗi giữ lại cho trace.
    async def empty_pipeline(files_by_role, options):
        return {"fields": [], "errors": ["Không tìm thấy Văn bản ủy quyền trong hồ sơ."]}

    out = await pipeline_runner._run_bac_ninh_authorized(empty_pipeline, {"": []}, {}, config)
    assert out == {"fields": [], "errors": ["Không tìm thấy Văn bản ủy quyền trong hồ sơ."]}

    # Lượt ủy quyền nổ không được làm hỏng lệnh điền đơn.
    async def broken_pipeline(files_by_role, options):
        raise RuntimeError("LLM timeout")

    out = await pipeline_runner._run_bac_ninh_authorized(broken_pipeline, {"": []}, {}, config)
    assert out["fields"] == [] and "LLM timeout" in out["errors"][0]


def test_upload_classifier_fallback_dung_o():
    from app.upload_session.classifier_registry import _CLASSIFIERS

    classifier = _CLASSIFIERS.get(KEY)
    assert classifier is not None and callable(classifier.fallback_to_slot)
    docs = get_procedure(KEY)["requiredDocs"]
    assert classifier.fallback_to_slot(
        "PHIẾU YÊU CẦU ĐĂNG KÝ BIỆN PHÁP BẢO ĐẢM (Mẫu số 01a)", docs, [], None)[0] == "don"
    assert classifier.fallback_to_slot(
        "HỢP ĐỒNG THẾ CHẤP quyền sử dụng đất số 15/2026/HĐTC", docs, [], None)[0] == "hop_dong"
    assert classifier.fallback_to_slot(
        "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT quyền sở hữu tài sản gắn liền với đất",
        docs, [], None)[0] == "gcn"
    assert classifier.fallback_to_slot(
        "GIẤY GIỚI THIỆU — Ngân hàng TMCP cử ông A đi nộp hồ sơ", docs, [], None)[0] == "khac"


# Nhà ở xã hội 1.014632 đi vòng qua 1.014589 (như popup-ke-khai-di-vong.js của Auto Fill).
_NOXH = "dang-ky-nha-o-xa-hoi-bac-ninh"
_EFORM = ("https://dichvucong.bacninh.gov.vn/web/guest/eform?p_p_id=org_bn_hoso_noptructuyen&p_p_state=normal"
          "&_org_bn_hoso_noptructuyen_maThuTucHanhChinh={ma}&_org_bn_hoso_noptructuyen_x=a%2Fb")


async def test_nha_o_xa_hoi_mo_trang_dvcqg_cua_thu_tuc_cau():
    conv = _conv(location={"province": "Tỉnh Bắc Ninh", "ward": "Phường Hiệp Hòa"})
    await flow.handle_turn(conv, intents.Intent("action", "pick_procedure", {"key": _NOXH}))
    r = await flow.handle_turn(conv, intents.Intent("confirm"))
    assert conv["state"] == "guide_login"
    assert r.actions[0] == {"type": "navigate", "url": get_procedure("ho-tro-nguoi-cao-tuoi-bac-ninh")["keKhaiUrl"]}


async def test_nha_o_xa_hoi_eform_ma_cau_thi_mo_lai_voi_ma_dich():
    conv = _conv(state="guide_login", procedure_key=_NOXH, milestones=[], agency_done=True)
    page = {"formKind": "bacninh", "attachmentTarget": True}
    r = await flow.handle_turn(conv, intents.Intent("event", "page_status", dict(page)),
                               client_url=_EFORM.format(ma="1.014589"))
    # Chỉ đổi đúng tham số mã, các tham số khác giữ nguyên từng ký tự (kể cả %2F).
    assert r.actions == [{"type": "navigate", "url": _EFORM.format(ma="1.014632")}]
    assert conv["state"] == "guide_login" and not r.display_md

    # Cổng cứ đá về mã cầu: đổi tối đa 2 lần rồi thôi, không tải lại vô hạn.
    await flow.handle_turn(conv, intents.Intent("event", "page_status", dict(page)),
                           client_url=_EFORM.format(ma="1.014589"))
    r = await flow.handle_turn(conv, intents.Intent("event", "page_status", dict(page)),
                               client_url=_EFORM.format(ma="1.014589"))
    assert not any(a.get("type") == "navigate" for a in r.actions)


async def test_doi_ma_chi_ap_cho_thu_tuc_di_vong():
    # Đã ở mã đích → luồng thường; thủ tục cầu làm thật (người cao tuổi) → không bao giờ bị đổi mã.
    flow_cfg = get_procedure(_NOXH)
    assert flow._doi_ma_thu_tuc_reply({}, flow_cfg, _EFORM.format(ma="1.014632")) is None
    assert flow._doi_ma_thu_tuc_reply({}, flow_cfg, "https://dichvucong.gov.vn/x?"
                                      "_org_bn_hoso_noptructuyen_maThuTucHanhChinh=1.014589") is None
    cau = get_procedure("ho-tro-nguoi-cao-tuoi-bac-ninh")
    assert flow._doi_ma_thu_tuc_reply({}, cau, _EFORM.format(ma="1.014589")) is None
