"""Quét giấy tờ NGAY ở bước Thông tin chủ hồ sơ (guidedSteps.ownerScan).

Một lần quét dùng cho cả hai việc: điền ngày cấp/nơi cấp (và khối ủy quyền) rồi đính kèm ở
bước Thành phần hồ sơ — công dân không phải ra máy quét hai lần.

Trợ lý chỉ xin giấy tờ ở bước này khi trang CÒN ô bắt buộc trống. Nhánh ủy quyền luôn còn bốn
ô của khối "Thông tin ủy quyền cá nhân" nên luôn phải quét; nhánh tự làm mà cổng đã điền sẵn
đủ thì bỏ qua, để giấy tờ nhận một thể ở bước sau.

HÀNG RÀO TƯƠNG THÍCH: cả tính năng này gác sau `supportsOwnerScan`. Bản extension trên chợ
không khai cờ → thứ tự bước giữ NGUYÊN như cũ. Đây là lý do `ownerInfo.enabled` của registry
vẫn để False: bật cờ đó là bật cho cả bản cũ, mà bản cũ nhận giấy ở bước 1 xong sẽ kẹt vì thủ
tục attach-only không có bước Kê khai để đi tiếp.
"""
import pytest

from app.channels.handfree.chat import flow
from app.channels.handfree.chat.flow import Intent

KEY = "chung-thuc-ban-sao"
SCAN_CLIENT = {"supportsGuidedSteps": True, "supportsOwnerScan": True}
GUIDED_ONLY = {"supportsGuidedSteps": True}
OLD_CLIENT = {"supportsRating": True}


def _conv(caps=SCAN_CLIENT, **kw):
    base = {
        "_id": "t-owner-scan", "state": "guide_login", "history": [], "milestones": [],
        "procedure_key": KEY, "upload_session_id": "sid", "consent": {"accepted": True},
        "location": {"province": "Thành phố Đà Nẵng", "ward": "Phường Hải Châu"},
        "client_capabilities": dict(caps),
    }
    base.update(kw)
    return base


async def _owner_page(conv, **ctx):
    payload = {"loggedIn": True, "wizardStep": 1}
    payload.update(ctx)
    return await flow.handle_turn(conv, Intent("event", "page_status", payload))


# ── Quyết định có quét ở bước chủ hồ sơ hay không ─────────────────────────────────────────

async def test_con_o_trong_thi_xin_giay_to_ngay_tai_buoc_chu_ho_so():
    conv = _conv()
    r = await _owner_page(conv, ownerForm={"required": 4, "missing": 2})
    assert conv["state"] == "ask_doc_method", "phải chuyển sang hỏi cách gửi giấy tờ"
    assert conv["owner_phase"] is True
    assert any(card.get("kind") == "doc_options" for card in r.cards)


async def test_trang_da_du_o_thi_khong_bat_quet_lai():
    conv = _conv()
    r = await _owner_page(conv, ownerForm={"required": 4, "missing": 0})
    assert conv["state"] == "guide_login", "không được kéo sang bước nhận giấy tờ"
    assert not r.cards
    assert r.chips[0]["send"] == "__action:guided_next"
    assert "Thành phần hồ sơ" in r.display_md


async def test_nhanh_uy_quyen_luon_phai_quet():
    """Bốn ô của khối ủy quyền luôn trống khi trang vừa mở → tự rơi vào vế còn thiếu."""
    conv = _conv()
    await _owner_page(conv, authorizationBlock=True, ownerForm={"required": 8, "missing": 4})
    assert conv["state"] == "ask_doc_method"


async def test_fe_khong_doc_duoc_o_nao_thi_van_quet():
    """Thà hỏi thừa còn hơn bỏ qua rồi để công dân ngồi gõ tay."""
    conv = _conv()
    await _owner_page(conv)  # không có ownerForm
    assert conv["state"] == "ask_doc_method"


async def test_khong_hoi_lai_khi_watcher_gui_page_status_lien_tuc():
    conv = _conv()
    await _owner_page(conv, ownerForm={"required": 4, "missing": 0})
    r = await _owner_page(conv, ownerForm={"required": 4, "missing": 0})
    assert not r.display_md and not r.chips


# ── Hàng rào tương thích ──────────────────────────────────────────────────────────────────

async def test_client_cu_giu_nguyen_thu_tu_buoc():
    conv = _conv(OLD_CLIENT)
    r = await _owner_page(conv, ownerForm={"required": 4, "missing": 2})
    assert conv["state"] == "guide_login", "bản trên chợ không được kéo sang bước nhận giấy tờ"
    assert not r.chips and not r.cards


async def test_client_co_guided_nhung_chua_co_owner_scan_thi_van_luong_cu():
    conv = _conv(GUIDED_ONLY)
    r = await _owner_page(conv, ownerForm={"required": 4, "missing": 2})
    assert conv["state"] == "guide_login"
    assert r.chips[0]["send"] == "__action:guided_next", "vẫn là nút chuyển bước, không quét"


async def test_registry_khong_bat_ownerInfo_cho_client_cu():
    from app.channels.handfree.procedure_registry import get_procedure
    proc = get_procedure(KEY)
    assert (proc.get("ownerInfo") or {}).get("enabled") is False, (
        "bật cờ này là bật cho CẢ bản cũ trên chợ; luồng quét sớm phải gác bằng ownerScan"
    )
    assert proc["guidedSteps"]["ownerScan"] is True


# ── Nhận giấy xong: chạy pipeline chủ hồ sơ dù registry tắt ownerInfo ─────────────────────

async def test_nhan_giay_xong_thi_chay_pipeline_chu_ho_so(monkeypatch):
    spawned = []
    monkeypatch.setattr(
        "app.channels.handfree.chat.pipeline_runner.spawn",
        lambda coro: (spawned.append(coro), coro.close()),
    )

    async def _progress(_sid):
        return {"received": 2, "total": 1, "files_count": 2}

    monkeypatch.setattr(flow.upload_service, "progress_of", _progress)
    conv = _conv(state="collecting_docs", owner_phase=True, docs_target="owner")
    await flow.handle_turn(conv, Intent("event", "docs_complete", {
        "pageContextCaptured": True, "wizardStep": 1,
    }))
    assert conv["state"] == "owner_filling", "phải chạy pipeline chủ hồ sơ, không báo lạc bước"
    assert spawned


# ── Từ chủ hồ sơ sang thẳng Thành phần hồ sơ, dùng lại đúng phiên giấy tờ ─────────────────

async def _progress_stub(monkeypatch, files_count=2):
    async def _progress(_sid):
        return {"received": files_count, "total": 1, "files_count": files_count}

    monkeypatch.setattr(flow.upload_service, "progress_of", _progress)


async def test_sang_buoc_dinh_kem_thi_dung_lai_phien_giay_to_cu(monkeypatch):
    spawned = []
    monkeypatch.setattr(
        "app.channels.handfree.chat.pipeline_runner.spawn",
        lambda coro: (spawned.append(coro), coro.close()),
    )
    await _progress_stub(monkeypatch)
    # Extension thật LUÔN gửi cách đính kèm đã chọn trong Cài đặt → áp luôn, không hỏi.
    conv = _conv(state="owner_waiting_next", owner_info_done=True,
                 attachment_preferences={"attachMode": "merge"})
    await flow.handle_turn(conv, Intent("event", "page_status", {
        "wizardStep": 3, "attachmentTarget": True, "attachmentComponentCount": 1,
    }))
    assert conv["state"] == "attaching", "attach-only không có bước Kê khai để chờ"
    assert conv["docs_target"] == "attachment"
    assert conv["upload_session_id"] == "sid", "KHÔNG được bắt công dân quét lại phiên mới"


async def test_client_cu_o_owner_waiting_next_khong_bi_keo_sang_dinh_kem():
    conv = _conv(OLD_CLIENT, state="owner_waiting_next", owner_info_done=True)
    r = await flow.handle_turn(conv, Intent("event", "page_status", {
        "wizardStep": 3, "attachmentTarget": True,
    }))
    assert conv["state"] == "owner_waiting_next"
    assert not r.display_md


# ── Hỏi riêng thẻ căn cước ────────────────────────────────────────────────────────────────

async def _fill_report(conv):
    return await flow.handle_turn(conv, Intent("action", "owner_fill_report", {
        "filled": 2, "kept": 0, "filledLabels": ["Ngày cấp", "Nơi cấp"],
    }))


def _after_fill(caps=SCAN_CLIENT, **kw):
    return _conv(caps, state="owner_filling", owner_phase=True,
                 owner_fields=[{"name": "Owner_IssueDate", "label": "Ngày cấp",
                                "reportLabel": "ngày cấp", "value": "30/07/2026"}], **kw)


async def test_doc_duoc_can_cuoc_thi_hoi_co_chung_thuc_khong():
    conv = _after_fill()
    r = await _fill_report(conv)
    assert "Căn cước công dân" in r.display_md
    assert [chip["send"] for chip in r.chips] == [
        "__action:certify_identity:yes", "__action:certify_identity:no",
    ]


async def test_tra_loi_khong_thi_ghi_nhan_va_ra_nut_chuyen_buoc():
    conv = _after_fill()
    await _fill_report(conv)
    conv["state"] = "owner_waiting_next"
    r = await flow.handle_turn(conv, Intent("action", "certify_identity", {"value": "no"}))
    assert conv["certify_identity"] is False
    assert "không" in r.display_md.lower()
    assert r.chips[0]["send"] == "__action:guided_next"


async def test_tra_loi_co_thi_chuyen_the_sang_o_giay_can_chung_thuc(monkeypatch):
    """Ô "căn cước của chủ hồ sơ" bị rút khỏi checklist ở bước sau. Chọn chứng thực mà để tệp
    nằm lại ô đó thì công dân không còn thấy nó để xem hay xoá."""
    moved = []

    async def _move(sid, source, target):
        moved.append((sid, source, target))

    monkeypatch.setattr(flow.up_store, "move_files_between_slots", _move)
    conv = _after_fill()
    await _fill_report(conv)
    conv["state"] = "owner_waiting_next"
    r = await flow.handle_turn(conv, Intent("action", "certify_identity", {"value": "yes"}))
    assert conv["certify_identity"] is True
    assert moved == [("sid", "cccd_chu_ho_so", "khac")]
    assert r.chips[0]["send"] == "__action:guided_next"


async def test_tra_loi_khong_thi_giu_nguyen_o_cu(monkeypatch):
    """Không chứng thực → thẻ vẫn là giấy chỉ để điền form, không được lẫn vào giấy chứng thực."""
    moved = []

    async def _move(sid, source, target):
        moved.append(sid)

    monkeypatch.setattr(flow.up_store, "move_files_between_slots", _move)
    conv = _after_fill()
    await _fill_report(conv)
    conv["state"] = "owner_waiting_next"
    await flow.handle_turn(conv, Intent("action", "certify_identity", {"value": "no"}))
    assert not moved


async def test_khong_doc_duoc_giay_tuy_than_thi_khong_hoi_vu_vo():
    conv = _conv(state="owner_filling", owner_phase=True, owner_fields=[])
    r = await _fill_report(conv)
    assert "Căn cước công dân" not in r.display_md
    assert r.chips[0]["send"] == "__action:guided_next"


async def test_chi_hoi_mot_lan():
    conv = _after_fill()
    await _fill_report(conv)
    conv["state"] = "owner_filling"
    r = await _fill_report(conv)
    assert all("certify_identity" not in chip["send"] for chip in r.chips)


async def test_client_cu_khong_nhan_cau_hoi_lan_nut_nao():
    conv = _after_fill(OLD_CLIENT)
    r = await _fill_report(conv)
    assert "Căn cước công dân" not in r.display_md
    assert not r.chips


# ── Checklist giấy tờ THEO BƯỚC ───────────────────────────────────────────────────────────

def _docs(target, caps=SCAN_CLIENT):
    from app.channels.handfree.documents import service

    return [d["key"] for d in service.docs_for_conversation(_conv(caps, docs_target=target))]


def test_buoc_chu_ho_so_co_them_o_can_cuoc():
    assert _docs("owner") == ["cccd_chu_ho_so", "khac"]


def test_qua_buoc_dinh_kem_thi_chi_con_giay_can_chung_thuc():
    """Đã đi qua chủ hồ sơ rồi mới mở chỗ tải giấy → không đòi lại căn cước đã đưa."""
    assert _docs("attachment") == ["khac"]


def test_client_cu_khong_bao_gio_thay_o_phu():
    assert _docs("owner", OLD_CLIENT) == ["khac"]
    assert _docs("attachment", OLD_CLIENT) == ["khac"]


async def test_doi_buoc_thi_rut_o_khoi_phien_dang_dung(monkeypatch):
    from app.channels.handfree.documents import service

    updated = []

    async def _set(sid, docs):
        updated.append((sid, [d["key"] for d in docs]))

    monkeypatch.setattr(service.store, "set_required_docs", _set)
    conv = _conv(docs_target="attachment")
    await service.sync_for_conversation(conv, {"_id": "sid", "required_docs": [
        {"key": "cccd_chu_ho_so"}, {"key": "khac"},
    ]})
    assert updated == [("sid", ["khac"])]


async def test_dung_buoc_thi_khong_ghi_lai_phien(monkeypatch):
    from app.channels.handfree.documents import service

    updated = []
    monkeypatch.setattr(service.store, "set_required_docs",
                        lambda sid, docs: updated.append(sid))
    conv = _conv(docs_target="owner")
    await service.sync_for_conversation(conv, {"_id": "sid", "required_docs": [
        {"key": "cccd_chu_ho_so"}, {"key": "khac"},
    ]})
    assert not updated


async def test_thu_tuc_khong_khai_o_theo_buoc_thi_khong_dong_phien(monkeypatch):
    """Không được đụng phiên của thủ tục khác — kể cả một lượt đọc."""
    from app.channels.handfree.documents import service

    touched = []
    monkeypatch.setattr(service.store, "set_required_docs", lambda *a: touched.append(a))
    conv = _conv(procedure_key="ket-hon", docs_target="attachment")
    await service.sync_for_conversation(conv)
    assert not touched


def test_loi_bot_doc_dung_danh_sach_cua_buoc_va_noi_ro_dung_lam_gi():
    from app.channels.handfree.documents import service

    proc_obj = flow.get_procedure(KEY)
    docs = service.docs_for_conversation(_conv(docs_target="owner"))
    md, tts = flow._doc_list(proc_obj, docs)
    assert "Căn cước công dân của chủ hồ sơ" in md
    assert "để em điền thông tin chủ hồ sơ" in md
    assert "để đính kèm vào Thành phần hồ sơ ở bước sau" in md
    assert "để em điền thông tin chủ hồ sơ" in tts, "lời đọc cũng phải nêu mục đích"


def test_thu_tuc_khac_khong_bi_them_chu_vao_danh_sach_giay_to():
    """`purpose` là khóa mới; thủ tục chưa khai thì câu chữ giữ nguyên từng ký tự."""
    proc_obj = flow.get_procedure("ket-hon")
    md, _ = flow._doc_list(proc_obj)
    assert " — *" not in md


def test_mot_loai_duy_nhat_thi_khong_doc_muc_dich():
    """Đang Ở bước đính kèm mà đọc "để đính kèm ở bước sau" là sai; một loại duy nhất thì
    cũng không có gì để phân biệt."""
    from app.channels.handfree.documents import service

    proc_obj = flow.get_procedure(KEY)
    docs = service.docs_for_conversation(_conv(docs_target="attachment"))
    md, tts = flow._doc_list(proc_obj, docs)
    assert "bước sau" not in md and "bước sau" not in tts


def test_cau_scan_o_buoc_chu_ho_so_khong_noi_la_khong_phan_loai():
    """Bước này CÓ phân loại (hai ô) — đọc câu "nhận thẳng tất cả" của bước đính kèm là sai."""
    proc_obj = flow.get_procedure(KEY)
    owner = flow._scan_pick_template(_conv(docs_target="owner"), proc_obj)
    assert "không phân loại" not in owner["md"]
    assert "tự xếp đúng loại" in owner["md"]
    attach = flow._scan_pick_template(_conv(docs_target="attachment"), proc_obj)
    assert attach is flow.vi.SCAN_PICK_ATTACH, "bước đính kèm giữ nguyên câu cũ"


def test_client_cu_giu_nguyen_cau_scan_cu():
    proc_obj = flow.get_procedure(KEY)
    conv = _conv(OLD_CLIENT, docs_target="owner")
    assert flow._scan_pick_template(conv, proc_obj) is flow.vi.SCAN_PICK_ATTACH


def test_thu_tuc_attach_only_nhieu_o_khac_khong_bi_doi_cau_scan():
    """Chứng thực chữ ký / giao dịch tài sản / phân chia di sản cũng là attach-only mà vốn NHIỀU ô.
    Suy câu scan theo "nhiều hơn một ô" là nói về căn cước chủ hồ sơ ở thủ tục không có thứ đó.
    Và KHÔNG được đọc câu "nhận thẳng là Giấy tờ cần chứng thực bản sao, không phân loại": nhiều
    ô thì có phân loại, và đó cũng không phải thủ tục bản sao.
    """
    for key in ("chung-thuc-chu-ky", "chung-thuc-giao-dich-tai-san", "chung-thuc-phan-chia-di-san"):
        proc_obj = flow.get_procedure(key)
        assert len(proc_obj["requiredDocs"]) > 1, f"{key} phải nhiều ô thì test này mới có nghĩa"
        for caps in (SCAN_CLIENT, OLD_CLIENT):
            conv = _conv(caps, procedure_key=key, docs_target="owner")
            template = flow._scan_pick_template(conv, proc_obj)
            assert template is flow.vi.SCAN_PICK, key
            md, _ = flow._fmt(template, doc_name=flow._scan_pick_doc_name(conv))
            assert "bản sao" not in md and "không phân loại" not in md, key


def test_thu_tuc_mot_o_doc_dung_ten_o_cua_chinh_no():
    """Câu "nhận thẳng, không phân loại" đúng với checklist một ô — nhưng phải nêu tên ô của
    CHÍNH thủ tục, không ghi cứng "chứng thực bản sao"."""
    expect = {
        "chung-thuc-ban-sao": "Giấy tờ cần chứng thực bản sao",
        "chung-thuc-chu-ky-nguoi-dich-ctv": "Bản dịch và giấy tờ, văn bản cần dịch",
    }
    for key, name in expect.items():
        proc_obj = flow.get_procedure(key)
        conv = _conv(OLD_CLIENT, procedure_key=key, docs_target="attachment")
        template = flow._scan_pick_template(conv, proc_obj)
        assert template is flow.vi.SCAN_PICK_ATTACH, key
        md, _ = flow._fmt(template, doc_name=flow._scan_pick_doc_name(conv))
        assert f"**{name}**" in md, key
    ctv_md, _ = flow._fmt(flow.vi.SCAN_PICK_ATTACH, doc_name="Bản dịch và giấy tờ, văn bản cần dịch")
    assert "bản sao" not in ctv_md


def test_thu_tuc_khong_khai_requiredDocs_van_doc_theo_uploadHint():
    """`dang-ky-giam-ho` không khai requiredDocs → `_doc_list` phải giữ đường fallback
    uploadHint của nó, không bị đẩy sang danh sách giấy tờ chung."""
    from app.channels.handfree.chat import guided_steps as guided

    proc_obj = flow.get_procedure("dang-ky-giam-ho")
    assert not proc_obj.get("requiredDocs"), "thủ tục này phải chưa khai thì test mới có nghĩa"
    conv = _conv(SCAN_CLIENT, procedure_key="dang-ky-giam-ho", docs_target="owner")
    by_step = guided.docs_for_target(conv, proc_obj, "owner")
    assert flow._doc_list(proc_obj, by_step) == flow._doc_list(proc_obj)


# ── Công dân tự điền rồi tự sang bước đính kèm giữa lúc trợ lý đang chờ giấy tờ ───────────

def _switch_env(monkeypatch, files):
    """Phiên đang mang checklist của bước chủ hồ sơ."""
    from app.channels.handfree.documents import service

    sess = {"_id": "sid", "files": list(files), "required_docs": [
        {"key": "cccd_chu_ho_so"}, {"key": "khac"},
    ]}
    moved, synced = [], []

    async def _get(_sid):
        return sess

    async def _move(sid, source, target):
        moved.append((sid, source, target))

    async def _sync(conv, sess=None):
        synced.append(conv.get("docs_target"))

    monkeypatch.setattr(flow.up_store, "get", _get)
    monkeypatch.setattr(flow.up_store, "move_files_between_slots", _move)
    monkeypatch.setattr(service, "sync_for_conversation", _sync)
    return moved, synced


def _collecting(caps=SCAN_CLIENT):
    return _conv(caps, state="collecting_docs", doc_method="scan",
                 docs_target="owner", owner_phase=True)


async def _jump_to_attach(conv):
    return await flow.handle_turn(conv, Intent("event", "page_status", {
        "wizardStep": 3, "attachmentTarget": True, "attachmentComponentCount": 1,
    }))


async def test_chua_chon_cach_gui_giay_da_tu_bam_sang_buoc_sau(monkeypatch):
    """Ca HAY GẶP NHẤT: bot vừa hỏi "cung cấp giấy tờ bằng cách nào", công dân chưa chọn gì mà
    đã tự điền form rồi bấm Bước tiếp theo → CHƯA CÓ PHIÊN nào. Trước đây nhánh chuyển bước
    thoát sớm vì không tìm thấy phiên, nên màn hình đứng im ở lời mời của bước chủ hồ sơ."""

    async def _no_session(_sid):
        return None

    monkeypatch.setattr(flow.up_store, "get", _no_session)
    conv = _conv(state="ask_doc_method", docs_target="owner", owner_phase=True)
    conv["upload_session_id"] = None
    r = await _jump_to_attach(conv)
    assert conv["state"] == "ask_doc_method"
    assert conv["owner_phase"] is False
    assert "Thành phần hồ sơ" in r.display_md
    assert "Căn cước công dân của chủ hồ sơ" not in r.display_md
    assert any(card.get("kind") == "doc_options" for card in r.cards)


async def test_mo_thang_vao_buoc_dinh_kem_thi_khong_thong_bao_thua(monkeypatch):
    """Chưa từng qua bước chủ hồ sơ → không có gì để "chuyển", đừng đẻ thêm bubble."""
    monkeypatch.setattr(flow.up_store, "get", lambda _sid: None)
    conv = _conv(state="ask_doc_method", docs_target="")
    assert await flow._guided_docs_target_switch(
        conv, flow.get_procedure(KEY), "",
    ) is None


async def test_chua_co_tep_nao_thi_hoi_lai_voi_checklist_cua_buoc_dinh_kem(monkeypatch):
    _switch_env(monkeypatch, [])
    conv = _collecting()
    r = await _jump_to_attach(conv)
    assert conv["state"] == "ask_doc_method"
    assert conv["owner_phase"] is False
    assert "Thành phần hồ sơ" in r.display_md
    assert "Căn cước công dân của chủ hồ sơ" not in r.display_md, "ô này hết nghĩa ở bước đây"


async def test_hoi_lai_thi_xoa_han_loi_hoi_cua_buoc_truoc(monkeypatch):
    """Hai thẻ QR/Scan giống hệt nhau chồng lên nhau, thẻ cũ vẫn bấm được mà checklist của nó
    còn ô căn cước — lời hỏi cũ phải biến mất khỏi CẢ lịch sử lẫn màn hình đang mở."""
    _switch_env(monkeypatch, [])
    conv = _collecting()
    conv["history"] = [
        {"role": "bot", "text": "Đã vào bước Thông tin chủ hồ sơ ✓ …", "state": "ask_doc_method"},
    ]
    r = await _jump_to_attach(conv)

    assert conv["history"] == []
    assert {"type": "drop_stale_ask", "tag": "doc_method"} in r.actions


async def test_khong_co_loi_hoi_cu_thi_khong_bao_fe_xoa_gi(monkeypatch):
    """Công dân đã trả lời rồi đi tiếp → câu bot cuối không phải lời hỏi, đừng xoá nhầm."""
    _switch_env(monkeypatch, [])
    conv = _collecting()
    conv["history"] = [
        {"role": "bot", "text": "Đã vào bước Thông tin chủ hồ sơ ✓ …", "state": "ask_doc_method"},
        {"role": "bot", "text": "Em đã nhận giấy tờ ạ.", "state": "collecting_docs"},
    ]
    r = await _jump_to_attach(conv)

    assert len(conv["history"]) == 2
    assert not any(a.get("type") == "drop_stale_ask" for a in r.actions)


async def test_da_co_tep_thi_khong_bat_chon_lai_cach_cung_cap(monkeypatch):
    _switch_env(monkeypatch, [{"doc_key": "khac", "name": "a.pdf"}])
    conv = _collecting()
    r = await _jump_to_attach(conv)
    assert conv["state"] == "collecting_docs", "hỏi lại là bắt làm lại việc vừa làm"
    assert not r.cards
    assert r.chips and r.chips[0]["send"] == "__action:docs_done"
    assert "Thành phần hồ sơ" in r.display_md


async def test_the_can_cuoc_da_quet_duoc_chuyen_sang_giay_can_chung_thuc(monkeypatch):
    moved, _ = _switch_env(monkeypatch, [{"doc_key": "cccd_chu_ho_so", "name": "cccd.pdf"}])
    conv = _collecting()
    r = await _jump_to_attach(conv)
    assert moved == [("sid", "cccd_chu_ho_so", "khac")]
    # Nói rõ để công dân tự bỏ ra nếu không muốn chứng thực thẻ đó.
    assert "Căn cước công dân" in r.display_md and "xoá" in r.display_md


async def test_khong_co_the_can_cuoc_thi_khong_noi_thua(monkeypatch):
    moved, _ = _switch_env(monkeypatch, [{"doc_key": "khac", "name": "a.pdf"}])
    r = await _jump_to_attach(_collecting())
    assert not moved
    assert "Căn cước công dân" not in r.display_md


async def test_client_cu_giu_nguyen_duong_cu(monkeypatch):
    _switch_env(monkeypatch, [{"doc_key": "khac", "name": "a.pdf"}])
    conv = _collecting(OLD_CLIENT)
    r = await _jump_to_attach(conv)
    assert not r.display_md and not r.chips, "bản trên chợ chỉ đổi nhãn nút chốt như trước"
    assert r.actions and r.actions[0]["type"] == "update_docs_done_chip"


async def test_phien_da_dung_checklist_buoc_nay_thi_khong_lam_gi_them(monkeypatch):
    from app.channels.handfree.documents import service

    async def _get(_sid):
        return {"_id": "sid", "files": [], "required_docs": [{"key": "khac"}]}

    monkeypatch.setattr(flow.up_store, "get", _get)
    monkeypatch.setattr(service, "sync_for_conversation",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("không được gọi")))
    conv = _conv(state="collecting_docs", docs_target="attachment")
    assert await flow._guided_docs_target_switch(conv, flow.get_procedure(KEY)) is None


# ── "Không chứng thực" phải thật sự không đính ────────────────────────────────────────────

def test_tra_loi_khong_thi_planner_nhan_lenh_bo_the_can_cuoc():
    assert flow._attachment_options(_conv(certify_identity=False))["excludeIdentityDocuments"]
    # Chưa hỏi, hoặc trả lời có → KHÔNG gửi khóa này (phiên cũ cũng không có).
    assert "excludeIdentityDocuments" not in flow._attachment_options(_conv())
    assert "excludeIdentityDocuments" not in flow._attachment_options(_conv(certify_identity=True))


def test_bo_the_can_cuoc_thi_xep_lai_vai_cac_muc_con_lai():
    """Mục đầu tiên ứng với dòng STT1 có sẵn của cổng; bỏ mục đầu mà không xếp lại là để
    trống đúng dòng bắt buộc."""
    from app.pipelines.chung_thuc_ban_sao.attach import planner

    items = [
        {"documentName": "Căn cước công dân", "detectedType": "Căn cước công dân",
         "componentName": planner.DEFAULT_COPY_CERTIFICATION_COMPONENT,
         "target": "existing", "componentIndex": 1, "needsAddComponent": False},
        {"documentName": "Bằng tốt nghiệp", "detectedType": "Bằng tốt nghiệp",
         "componentName": "Bằng tốt nghiệp",
         "target": "new", "componentIndex": None, "needsAddComponent": True},
    ]
    kept = planner._drop_identity_documents(items, [], drop_identity_types=True)
    assert [item["documentName"] for item in kept] == ["Bằng tốt nghiệp"]
    assert kept[0]["target"] == "existing" and kept[0]["componentIndex"] == 1
    assert kept[0]["needsAddComponent"] is False
    assert kept[0]["componentName"] == planner.DEFAULT_COPY_CERTIFICATION_COMPONENT


def test_bo_theo_DUNG_TEP_da_phan_loai_chu_khong_doan_lai():
    """Đã phân loại lúc upload thì biết đích danh tệp nào là căn cước CỦA CHỦ HỒ SƠ.
    Căn cước của NGƯỜI KHÁC vẫn là giấy cần chứng thực, phải giữ lại."""
    from app.pipelines.chung_thuc_ban_sao.attach import planner

    items = [
        {"fileName": "cccd-chu-ho-so.pdf", "documentName": "Căn cước công dân",
         "detectedType": "Căn cước công dân", "componentName": "x",
         "target": "existing", "componentIndex": 1, "needsAddComponent": False},
        {"fileName": "cccd-nguoi-khac.pdf", "documentName": "Căn cước công dân",
         "detectedType": "Căn cước công dân", "componentName": "y",
         "target": "new", "componentIndex": None, "needsAddComponent": True},
    ]
    kept = planner._drop_identity_documents(items, ["cccd-chu-ho-so.pdf"])
    assert [item["fileName"] for item in kept] == ["cccd-nguoi-khac.pdf"]
    assert kept[0]["target"] == "existing", "tệp còn lại phải nhận dòng STT1 có sẵn"


def test_khong_co_danh_sach_phan_loai_thi_van_suy_theo_loai_giay():
    """Phiên cũ chỉ có một ô nên không hề phân loại — giữ đường suy cũ làm dự phòng."""
    from app.pipelines.chung_thuc_ban_sao.attach import planner

    items = [
        {"fileName": "a.pdf", "documentName": "Căn cước công dân",
         "detectedType": "Căn cước công dân", "componentName": "x",
         "target": "existing", "componentIndex": 1, "needsAddComponent": False},
        {"fileName": "b.pdf", "documentName": "Bằng tốt nghiệp",
         "detectedType": "Bằng tốt nghiệp", "componentName": "y",
         "target": "new", "componentIndex": None, "needsAddComponent": True},
    ]
    assert [i["fileName"] for i in planner._drop_identity_documents(
        items, [], drop_identity_types=True)] == ["b.pdf"]


# ── Phân loại phải neo vào ĐÚNG người, không phải cứ căn cước là của chủ hồ sơ ────────────

def test_spec_phan_loai_duoc_dang_ky_va_nhan_moc_chu_ho_so():
    from app.upload_session import classifier_registry

    classifier = classifier_registry.get_upload_classifier(KEY)
    assert classifier, "thiếu spec phân loại cho chứng thực bản sao"
    assert sorted(classifier.spec.allowed_keys) == ["cccd_chu_ho_so", "giay_uy_quyen", "khac"]
    assert classifier.spec.build_user_prompt_with_context, "phải nhận được mốc chủ hồ sơ"
    prompt = classifier.spec.build_user_prompt_with_context(
        "x.pdf", "CĂN CƯỚC CÔNG DÂN 040203015844",
        {"owner": {"fullName": "VŨ ĐÌNH THIẾT", "identityNumber": "040203015844"}},
    )
    assert "040203015844" in prompt and "VŨ ĐÌNH THIẾT" in prompt
    assert "x.pdf" not in prompt, "tên file không được thành bằng chứng"


def test_spec_hong_thi_ve_giay_can_chung_thuc_chu_khong_ve_o_chu_ho_so():
    """Khóa bắt đầu bằng 'cccd' nên luật chung route_to_slot sẽ hút MỌI căn cước vào ô chủ
    hồ sơ — đó là lý do thủ tục này phải có fallback riêng."""
    from app.upload_session import classifier_registry

    classifier = classifier_registry.get_upload_classifier(KEY)
    docs = [{"key": "cccd_chu_ho_so", "sides": 1}, {"key": "khac", "sides": 1, "repeatable": True}]
    assert classifier.fallback_to_slot("CĂN CƯỚC CÔNG DÂN", docs, [], None)[0] == "khac"
    # Công dân tự chọn ô trên điện thoại thì tôn trọng — đó là ý người thật, không phải đoán.
    assert classifier.fallback_to_slot("x", docs, [], "cccd_chu_ho_so")[0] == "cccd_chu_ho_so"


def test_cac_spec_cu_khong_phai_sua_gi():
    """Trường nhận ngữ cảnh là TÙY CHỌN — 13 spec đang chạy phải giữ nguyên hợp đồng cũ."""
    from app.upload_session import classifier_registry

    other = classifier_registry.get_upload_classifier("khai-tu")
    assert other and other.spec.build_user_prompt_with_context is None


def test_khong_co_the_can_cuoc_thi_ke_hoach_giu_nguyen():
    from app.pipelines.chung_thuc_ban_sao.attach import planner

    items = [{"documentName": "Bằng tốt nghiệp", "detectedType": "Bằng tốt nghiệp",
              "componentName": "x", "target": "existing", "componentIndex": 1,
              "needsAddComponent": False}]
    assert planner._drop_identity_documents(items, [], drop_identity_types=True) is items


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])


# ── Bẫy hai ngày sinh trong giấy ủy quyền ─────────────────────────────────────────────────

def test_prompt_uy_quyen_chi_ro_lay_ngay_sinh_cua_ben_nao():
    """Sự cố 22/09/2026: ô "Ngày tháng năm sinh" của khối ủy quyền không được điền.

    Engine FE không hỏng (đã thử gõ tay trên cổng thật: dò ra ô, gõ ăn ngay). Giá trị chưa
    bao giờ về — mô hình bỏ trống. Lý do: giấy ủy quyền ghi ngày sinh của CẢ HAI bên mà hợp
    đồng chỉ có MỘT trường ngày sinh (của bên ủy quyền), không có trường cho bên được ủy
    quyền; gặp hai ngày mà chỉ một ô, cách an toàn của mô hình là bỏ trống.
    Họ tên và số giấy tờ không dính bẫy này vì có trường cho cả hai vai.
    """
    from app.channels.handfree.owner_info import prompt as owner_prompt
    from app.channels.handfree.owner_info import schema as owner_schema

    rules = owner_prompt.build_rules({"fullName": "VŨ ĐÌNH THIẾT"}, include_authorization=True)
    assert "CẢ HAI bên" in rules, "phải nói thẳng tài liệu có hai ngày sinh"
    assert "bên A" in rules and "bên B" in rules, "phải neo vào vai, không nói chung chung"
    assert "KHÔNG phải là lý do để bỏ trống" in rules

    desc = next(f["desc"] for f in owner_schema.AUTHORIZATION_FIELDS
                if f["name"] == "Authorization_GrantorDateOfBirth")
    assert "BÊN ỦY QUYỀN" in desc and "bên được ủy quyền" in desc


def test_nhanh_tu_lam_khong_dinh_luat_uy_quyen():
    """Luật hai ngày sinh chỉ có nghĩa ở nhánh ủy quyền — nhánh tự làm phải sạch."""
    from app.channels.handfree.owner_info import prompt as owner_prompt

    rules = owner_prompt.build_rules({"fullName": "X"}, include_authorization=False)
    assert "ngày sinh" not in rules.lower()


# ── Tự đính giấy ủy quyền ngay sau khi điền ───────────────────────────────────────────────

def _auth_conv(**kw):
    return _conv(SCAN_CLIENT, state="owner_filling", owner_phase=True,
                 authorization_page=True, docs_target="owner",
                 owner_fields=[{"name": "Owner_IssueDate", "label": "Ngày cấp",
                                "reportLabel": "ngày cấp", "value": "30/07/2026"}], **kw)


def _session(files):
    async def _get(_sid):
        return {"_id": "sid", "files": files, "required_docs": [
            {"key": "cccd_chu_ho_so"}, {"key": "giay_uy_quyen"}, {"key": "khac"},
        ]}
    return _get


async def test_dien_xong_thi_dinh_luon_giay_uy_quyen(monkeypatch):
    monkeypatch.setattr(flow.up_store, "get", _session([
        {"name": "uy-quyen.pdf", "doc_key": "giay_uy_quyen"},
        {"name": "cccd.pdf", "doc_key": "cccd_chu_ho_so"},
    ]))
    r = await _fill_report(_auth_conv())
    action = next(a for a in r.actions if a["type"] == "attach_authorization_doc")
    assert action["fileName"] == "uy-quyen.pdf", "phải chỉ đích danh tệp, không để FE tự đoán"


async def test_khong_co_giay_uy_quyen_dat_chuan_thi_khong_dinh_bua(monkeypatch):
    """Bộ phân loại từ chối (giấy của cặp người khác) → không có tệp nào ở ô đó → im."""
    monkeypatch.setattr(flow.up_store, "get", _session([{"name": "la.pdf", "doc_key": None}]))
    r = await _fill_report(_auth_conv())
    assert not any(a["type"] == "attach_authorization_doc" for a in r.actions)


async def test_chi_dinh_mot_lan(monkeypatch):
    monkeypatch.setattr(flow.up_store, "get", _session([
        {"name": "uy-quyen.pdf", "doc_key": "giay_uy_quyen"},
    ]))
    conv = _auth_conv()
    await _fill_report(conv)
    conv["state"] = "owner_filling"
    r = await _fill_report(conv)
    assert not any(a["type"] == "attach_authorization_doc" for a in r.actions)


async def test_nhanh_tu_lam_khong_dinh_giay_uy_quyen(monkeypatch):
    monkeypatch.setattr(flow.up_store, "get", _session([
        {"name": "uy-quyen.pdf", "doc_key": "giay_uy_quyen"},
    ]))
    conv = _auth_conv()
    conv["authorization_page"] = False
    r = await _fill_report(conv)
    assert not any(a["type"] == "attach_authorization_doc" for a in r.actions)


async def test_bao_ket_qua_dinh_giay_uy_quyen():
    conv = _conv(state="owner_waiting_next", authorization_page=True)
    ok = await flow.handle_turn(conv, Intent("action", "authorization_attach_report", {"ok": True}))
    assert "giấy ủy quyền" in ok.display_md
    bad = await flow.handle_turn(conv, Intent("action", "authorization_attach_report", {
        "ok": False, "error": "trang chưa có dòng giấy ủy quyền",
    }))
    assert "Chọn tệp đính kèm" in bad.display_md, "phải chỉ đường làm tay khi tự đính hỏng"


def test_nhan_nut_chot_giay_to_o_nhanh_uy_quyen():
    conv = _conv(authorization_page=True, docs_target="owner")
    assert flow._docs_done_label_for_conv(conv) == "✅ Đã đưa đủ giấy tờ, điền thông tin và đính kèm đi"
    conv["authorization_page"] = False
    assert "điền chủ hồ sơ" in flow._docs_done_label_for_conv(conv)


# ── Gộp/tách hồ sơ: luồng mới vẫn phải tôn trọng Cài đặt của quầy ─────────────────────────

async def test_ap_dung_cach_dinh_kem_da_chon_trong_cai_dat(monkeypatch):
    """Giấy tờ nhận ở bước chủ hồ sơ nên nhánh hỏi gộp/tách trong _docs_complete không đi qua.
    Bỏ sót là hai thủ tục chứng thực âm thầm mất lựa chọn "mỗi tài liệu một hồ sơ riêng"."""
    spawned = []
    monkeypatch.setattr(
        "app.channels.handfree.chat.pipeline_runner.spawn",
        lambda coro: (spawned.append(coro), coro.close()),
    )
    await _progress_stub(monkeypatch)
    conv = _conv(state="owner_waiting_next", owner_info_done=True,
                 attachment_preferences={"attachMode": "split"})
    await flow.handle_turn(conv, Intent("event", "page_status", {
        "wizardStep": 3, "attachmentTarget": True, "attachmentComponentCount": 1,
    }))
    assert conv["attach_mode"] == "split", "phải áp cài đặt, không âm thầm gộp một hồ sơ"
    assert conv["state"] == "attaching", "đã có cài đặt thì KHÔNG hỏi lại giữa luồng"


async def test_khong_co_cai_dat_thi_moi_hoi(monkeypatch):
    """Bản extension cũ không gửi preference → giữ nguyên câu hỏi + hai chip như trước."""
    await _progress_stub(monkeypatch)
    conv = _conv(state="owner_waiting_next", owner_info_done=True)
    r = await flow.handle_turn(conv, Intent("event", "page_status", {
        "wizardStep": 3, "attachmentTarget": True, "attachmentComponentCount": 1,
    }))
    assert conv["state"] == "choosing_attach_mode"
    assert [chip["send"] for chip in r.chips] == [
        '__action:attach_mode:{"value":"merge"}',
        '__action:attach_mode:{"value":"split"}',
    ]
