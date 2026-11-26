"""Dùng lại giấy tờ trong Ví cá nhân của cổng ở bước Thành phần hồ sơ (chat/wallet_reuse.py)."""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import flow, pipeline_runner, store, tracing, wallet_reuse
from app.channels.handfree.chat.intents import Intent
from app.channels.handfree.documents import service as upload_service

PROC = "chung-thuc-ban-sao"
CAPS = {"supportsGuidedSteps": True, "supportsOwnerScan": True, "supportsPageBoundDocsComplete": True,
        "supportsAttachmentContext": True, wallet_reuse.CAPABILITY: True}
PAGE = {"wizardStep": 3, "attachmentTarget": True}
ORIGIN = "https://apidvc.moj.gov.vn"
ITEMS = [{"id": f"w{i}", "uri": f"{i:08x}-aaaa-bbbb-cccc-0123456789ab", "name": f"Scan_{i}.pdf",
          "size": 1000 + i, "createdAt": f"2026-11-1{i}T10:00:00"} for i in range(3)]
LISTED = {"ok": True, "items": ITEMS, "total": 3, "origin": ORIGIN}
ONLY = "__action:wallet_only"


@pytest.fixture(autouse=True)
def _no_io(monkeypatch):
    spawned = []
    monkeypatch.setattr(pipeline_runner, "spawn", lambda coro: spawned.append(coro))
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a, **k: "run_attach")
    monkeypatch.setattr(tracing, "set_report", AsyncMock())
    monkeypatch.setattr(upload_service, "progress_of", AsyncMock(return_value={"files_count": 2}))
    monkeypatch.setattr(wallet_reuse.up_store, "get", AsyncMock(return_value={"_id": "s1", "owner_user_id": "u1"}))
    monkeypatch.setattr(wallet_reuse.up_store, "save", AsyncMock())
    monkeypatch.setattr(wallet_reuse.up_store, "delete_session", AsyncMock())
    # Mặc định LLM không trả lời → dò số dự phòng; test hiểu câu bằng LLM tự đặt câu trả lời.
    monkeypatch.setattr(wallet_reuse, "llm_chat", AsyncMock(side_effect=RuntimeError("không gọi LLM trong test")))
    return spawned


def _conv(caps=CAPS, **extra) -> dict:
    conv = store.new_conversation()
    conv.update({"procedure_key": PROC, "state": "owner_waiting_next", "client_capabilities": dict(caps),
                 "upload_session_id": "s1",
                 "auth_user": {"id": "u1", wallet_reuse.SETTING: True, wallet_reuse.SETTING_SAVED: True},
                 "attachment_preferences": {"attachMode": "merge"},
                 "attachment_context": {"components": [{"name": "Bản chính"}]}})
    conv.update(extra)
    return conv


def _types(reply):
    return [a.get("type") for a in reply.actions]


def _sends(reply):
    return [c.get("send") for c in reply.chips]


async def _arrive(conv):
    return await flow.handle_turn(conv, Intent("event", "page_status", PAGE), PAGE)


async def _listed(conv):
    await _arrive(conv)
    return await flow.handle_turn(conv, Intent("event", "wallet_list", LISTED))


# ── Bật / tắt ──
async def test_extension_cu_khong_khai_capability_thi_di_thang_dinh_kem():
    conv = _conv(caps={k: v for k, v in CAPS.items() if k != wallet_reuse.CAPABILITY})
    reply = await _arrive(conv)
    assert "wallet_list" not in _types(reply)
    assert conv["state"] == "attaching"


async def test_tai_khoan_tat_cai_dat_thi_khong_hoi():
    conv = _conv(auth_user={"id": "u1", wallet_reuse.SETTING: False, wallet_reuse.SETTING_SAVED: False})
    await _arrive(conv)
    assert conv["state"] == "attaching"


async def test_che_do_tieng_mong_thi_khong_hoi():
    conv = _conv(lang="hmong")
    await _arrive(conv)
    assert conv["state"] == "attaching"


# ── Đọc danh sách, hỏi, hiện thẻ ngay ──
async def test_toi_thanh_phan_ho_so_thi_doc_danh_sach_vi_truoc_khi_dinh():
    conv = _conv()
    reply = await _arrive(conv)
    assert conv["state"] == wallet_reuse.STATE and conv["wallet_phase"] == "checking"
    assert reply.actions == [{"type": "wallet_list", "limit": wallet_reuse.LIMIT}]
    assert flow.build_progress(conv)["label"] == "Dùng lại giấy tờ trên cổng"


async def test_page_status_trong_luc_cho_khong_lam_gi():
    conv = _conv()
    await _arrive(conv)
    reply = await _arrive(conv)
    assert reply.display_md == "" and conv["wallet_phase"] == "checking"


async def test_vi_trong_thi_dinh_kem_luon_va_khong_hoi_lai(_no_io):
    conv = _conv()
    await _arrive(conv)
    await flow.handle_turn(conv, Intent("event", "wallet_list", {"ok": True, "items": [], "origin": ORIGIN}))
    assert conv["state"] == "attaching" and conv["wallet_reuse_done"] is True
    assert "run_attach" in _no_io


async def test_doc_vi_hong_thi_bao_roi_dinh_kem():
    conv = _conv()
    await _arrive(conv)
    reply = await flow.handle_turn(conv, Intent("event", "wallet_list", {"ok": False, "error": "x"}))
    assert "chưa đọc được Ví cá nhân" in reply.display_md
    assert conv["state"] == "attaching"


async def test_origin_khong_phai_cong_nha_nuoc_thi_khong_dung():
    conv = _conv()
    await _arrive(conv)
    reply = await flow.handle_turn(conv, Intent("event", "wallet_list", {**LISTED, "origin": "https://evil.example.com"}))
    assert not reply.cards and conv["state"] == "attaching"


async def test_vi_co_giay_thi_hoi_va_bo_qua_thi_dinh_giay_vua_nhan():
    conv = _conv()
    reply = await _listed(conv)
    assert _sends(reply) == ["__action:wallet_use", "__action:wallet_skip"]
    await flow.handle_turn(conv, Intent("action", "wallet_skip", {}))
    assert conv["state"] == "attaching" and "wallet_items" not in conv


async def test_dong_y_thi_hien_the_ngay_khong_tai_khong_doc_noi_dung(_no_io):
    conv = _conv()
    await _listed(conv)
    reply = await flow.handle_turn(conv, Intent("action", "wallet_use", {}))
    assert reply.actions == [] and not _no_io, "chưa tải, chưa chạy nền gì"
    card = reply.cards[0]
    assert card["kind"] == "wallet_docs" and card["origin"] == ORIGIN
    assert card["downloadPath"] == wallet_reuse.DOWNLOAD_PATH
    assert [(e["no"], e["name"], e["size"], e["date"]) for e in card["entries"]] == [
        (1, "Scan_0.pdf", 1000, "2026-11-10T10:00:00"), (2, "Scan_1.pdf", 1001, "2026-11-11T10:00:00"),
        (3, "Scan_2.pdf", 1002, "2026-11-12T10:00:00")]
    assert conv["wallet_phase"] == "choosing"
    wallet_reuse.up_store.save.assert_not_awaited()


# ── Chọn → chỉ tải giấy được chọn → chép sang hồ sơ ──
async def _choosing():
    conv = _conv()
    await _listed(conv)
    await flow.handle_turn(conv, Intent("action", "wallet_use", {}))
    return conv


async def test_chon_giay_thi_chi_tai_dung_giay_do_vao_phien_tam():
    conv = await _choosing()
    reply = await flow.handle_turn(conv, Intent("action", "wallet_pick", {"picked": [3, 1, 9, "x"]}))
    read = next(a for a in reply.actions if a["type"] == "wallet_read")
    assert [i["id"] for i in read["items"]] == ["w0", "w2"]
    assert read["session_id"] == conv["wallet_session_id"] != "s1"
    assert read["origin"] == ORIGIN and read["downloadPath"] == wallet_reuse.DOWNLOAD_PATH
    assert conv["wallet_phase"] == "fetching"
    saved = wallet_reuse.up_store.save.await_args.args[0]
    assert saved["purpose"] == "wallet" and saved["manual_complete_only"] is True and saved["owner_user_id"] == "u1"


async def test_tai_xong_thi_chep_vao_ho_so_roi_dinh(monkeypatch):
    conv = await _choosing()
    await flow.handle_turn(conv, Intent("action", "wallet_pick", {"picked": [1, 2]}))
    staging = conv["wallet_session_id"]
    imported = AsyncMock(return_value=2)
    monkeypatch.setattr(wallet_reuse, "import_staged", imported)
    files = [{"id": "w0", "fid": "f0.pdf"}, {"id": "w1", "fid": "f1.pdf"}]
    reply = await flow.handle_turn(conv, Intent("event", "wallet_uploaded", {"ok": True, "files": files}))
    assert imported.await_args.args[1] == {"f0.pdf": "w0", "f1.pdf": "w1"}
    assert "Đã thêm **2 giấy tờ**" in reply.display_md
    assert conv["state"] == "attaching" and "wallet_session_id" not in conv
    wallet_reuse.up_store.delete_session.assert_awaited_with(staging)


async def test_tai_hong_het_thi_bao_roi_dinh_giay_vua_nhan():
    conv = await _choosing()
    await flow.handle_turn(conv, Intent("action", "wallet_pick", {"picked": [1]}))
    reply = await flow.handle_turn(conv, Intent("event", "wallet_uploaded", {"ok": False, "files": [], "failed": 1}))
    assert "chưa đọc được Ví cá nhân" in reply.display_md and conv["state"] == "attaching"


async def test_llm_loi_thi_do_chu_so_de_chon_bo_va_xong():
    conv = await _choosing()
    reply = await flow.handle_turn(conv, Intent("action", "wallet_answer", {"text": "chọn số 2 và 3"}))
    assert conv["wallet_picked"] == [2, 3] and "2, 3" in reply.display_md
    assert [e["picked"] for e in reply.cards[0]["entries"]] == [False, True, True]
    await flow.handle_turn(conv, Intent("action", "wallet_answer", {"text": "bỏ số 3"}))
    assert conv["wallet_picked"] == [2]
    reply = await flow.handle_turn(conv, Intent("action", "wallet_answer", {"text": "xong rồi"}))
    read = next(a for a in reply.actions if a["type"] == "wallet_read")
    assert [i["id"] for i in read["items"]] == ["w1"]


async def test_chot_giay_to_ngay_o_buoc_thanh_phan_ho_so_cung_hoi_vi(monkeypatch):
    monkeypatch.setattr(upload_service, "complete_session", AsyncMock())
    monkeypatch.setattr(upload_service, "progress_of",
                        AsyncMock(return_value={"files_count": 2, "received": 1, "total": 1}))
    conv = _conv(state="collecting_docs", docs_target="attachment", doc_method="scan")
    reply = await flow.handle_turn(conv, Intent("action", "docs_done", {}))
    assert conv["state"] == wallet_reuse.STATE and _types(reply) == ["wallet_list"]
    await flow.handle_turn(conv, Intent("event", "wallet_list", {"ok": True, "items": []}))
    assert conv["state"] == "attaching" and conv["docs_target"] == "attachment"


def test_danh_sach_vi_chi_nhan_ma_tep_hop_le_va_toi_da_20():
    raw = [{"id": "a", "uri": "../etc/passwd"}, {"id": "b", "uri": "ok-1"}, {"id": "b", "uri": "ok-2"}]
    raw += [{"id": f"x{i}", "uri": f"u{i}"} for i in range(30)]
    items = wallet_reuse._clean_items(raw)
    assert items[0]["uri"] == "ok-1" and len(items) == wallet_reuse.LIMIT
    assert all(i["uri"] != "../etc/passwd" for i in items)


async def test_chep_tep_tu_phien_tam_sang_phien_ho_so_giu_byte_ten_goc_va_mo_lai_phien_da_chot(monkeypatch, tmp_path):
    monkeypatch.setattr(wallet_reuse.up_store.settings, "storage_dir", str(tmp_path))
    for fid, data in (("f0.pdf", b"%PDF-a"), ("f1.pdf", b"%PDF-b")):
        wallet_reuse.up_store.save_file_bytes("W1", fid, data)
    wallet = {"_id": "W1", "files": [{"fid": f, "name": f, "type": "application/pdf"} for f in ("f0.pdf", "f1.pdf")]}
    main = {"_id": "s1", "complete": True, "procedure_key": PROC, "files": [{"fid": "x", "name": "Scan_0.pdf"}],
            "required_docs": [{"key": "khac", "sides": 1}]}
    monkeypatch.setattr(wallet_reuse.up_store, "get", AsyncMock(side_effect=lambda sid: {"W1": wallet, "s1": main}[sid]))
    calls = []
    monkeypatch.setattr(wallet_reuse.up_store, "reopen_for_supplement", AsyncMock(side_effect=lambda s: calls.append("reopen")))
    monkeypatch.setattr(wallet_reuse.up_store, "set_complete", AsyncMock(side_effect=lambda s, v: calls.append(("complete", v))))
    appended = []

    async def append(sid, metas, limit):
        calls.append("append")
        appended.extend(metas)
        return {**main, "files": main["files"] + metas}
    monkeypatch.setattr(wallet_reuse.up_store, "append_files_with_limit", append)
    monkeypatch.setattr(wallet_reuse, "broadcast", AsyncMock())
    conv = _conv(wallet_session_id="W1", wallet_items=ITEMS)
    count = await wallet_reuse.import_staged(conv, {"f0.pdf": "w0", "f1.pdf": "w1"})
    assert count == 2 and calls == ["reopen", "append", ("complete", True)]
    assert [m["name"] for m in appended] == ["Scan_0-2.pdf", "Scan_1.pdf"], "tên gốc trong ví, không trùng tên đã có"
    assert {m["doc_key"] for m in appended} == {"khac"}
    datas = sorted((tmp_path / "upload_sessions" / "s1" / m["fid"]).read_bytes() for m in appended)
    assert datas == [b"%PDF-a", b"%PDF-b"]
    assert wallet_reuse.broadcast.await_args.args[1]["files_count"] == 3


# ── Nút "Chỉ chọn giấy tờ trong Ví cá nhân" lúc nhận giấy tờ ở bước Thành phần hồ sơ ──
def _ask_conv(**extra):
    return _conv(**{"state": "guide_login", "owner_phase": False, **extra})


async def test_hoi_cach_gui_giay_o_buoc_thanh_phan_ho_so_co_nut_chi_vi():
    conv = _ask_conv()
    reply = await flow.handle_turn(conv, Intent("event", "page_status", PAGE), PAGE)
    assert conv["state"] == "ask_doc_method" and ONLY in _sends(reply)


async def test_buoc_chu_ho_so_khong_co_nut_chi_vi():
    assert ONLY not in _sends(flow._to_ask_doc_method(_ask_conv(owner_phase=True)))


async def test_tat_cai_dat_thi_khong_co_nut_chi_vi():
    conv = _ask_conv(auth_user={"id": "u1", wallet_reuse.SETTING: False, wallet_reuse.SETTING_SAVED: False})
    reply = await flow.handle_turn(conv, Intent("event", "page_status", PAGE), PAGE)
    assert ONLY not in _sends(reply)


async def test_chon_scan_chua_co_tep_van_co_nut_chi_vi(monkeypatch):
    monkeypatch.setattr(upload_service, "create_for_conversation", AsyncMock(return_value={"type": "show_qr"}))
    monkeypatch.setattr(upload_service, "sync_for_conversation", AsyncMock())
    monkeypatch.setattr(upload_service, "progress_of", AsyncMock(return_value={"files_count": 0}))
    conv = _ask_conv(state="ask_doc_method")
    assert ONLY in _sends(await flow._apply_doc_method(conv, "scan", reuse_session=False))
    monkeypatch.setattr(upload_service, "progress_of", AsyncMock(return_value={"files_count": 2}))
    assert ONLY not in _sends(await flow._apply_doc_method(conv, "scan", reuse_session=True))


async def _only_start(monkeypatch, files_count=0):
    monkeypatch.setattr(upload_service, "progress_of", AsyncMock(return_value={"files_count": files_count}))
    conv = _ask_conv(state="collecting_docs", doc_method="scan")
    reply = await flow.handle_turn(conv, Intent("action", "wallet_only", {}))
    return conv, reply


async def test_chi_vi_hien_the_luon_khong_hoi_lai(monkeypatch):
    conv, reply = await _only_start(monkeypatch)
    assert _types(reply) == ["wallet_list"] and conv["wallet_only"] is True
    reply = await flow.handle_turn(conv, Intent("event", "wallet_list", LISTED))
    assert reply.cards[0]["kind"] == "wallet_docs" and conv["wallet_phase"] == "choosing"
    assert _sends(reply) == ["__action:wallet_skip"] and reply.chips[0]["label"] == "↩️ Gửi giấy tờ cách khác"


async def test_chi_vi_ma_vi_trong_thi_ve_buoc_chon_cach_gui(monkeypatch):
    conv, _ = await _only_start(monkeypatch)
    reply = await flow.handle_turn(conv, Intent("event", "wallet_list", {"ok": True, "items": [], "origin": ORIGIN}))
    assert conv["state"] == "ask_doc_method" and "chưa có giấy tờ nào" in reply.display_md
    assert ONLY not in _sends(reply), "đã thử ví rồi thì không mời lại"


async def test_chi_vi_khong_chon_gi_thi_ve_buoc_chon_cach_gui(monkeypatch):
    conv, _ = await _only_start(monkeypatch)
    await flow.handle_turn(conv, Intent("event", "wallet_list", LISTED))
    reply = await flow.handle_turn(conv, Intent("action", "wallet_skip", {}))
    assert conv["state"] == "ask_doc_method" and "chưa chọn giấy nào" in reply.display_md


async def test_chi_vi_chon_giay_tai_xong_thi_dinh_kem(monkeypatch):
    conv, _ = await _only_start(monkeypatch)
    await flow.handle_turn(conv, Intent("event", "wallet_list", LISTED))
    await flow.handle_turn(conv, Intent("action", "wallet_pick", {"picked": [1]}))
    monkeypatch.setattr(wallet_reuse, "import_staged", AsyncMock(return_value=1))
    reply = await flow.handle_turn(conv, Intent("event", "wallet_uploaded", {"ok": True,
                                                                          "files": [{"id": "w0", "fid": "f0.pdf"}]}))
    assert conv["state"] == "attaching" and "Đã thêm **1 giấy tờ**" in reply.display_md


async def test_chi_vi_tai_hong_thi_ve_buoc_chon_cach_gui(monkeypatch):
    conv, _ = await _only_start(monkeypatch)
    await flow.handle_turn(conv, Intent("event", "wallet_list", LISTED))
    await flow.handle_turn(conv, Intent("action", "wallet_pick", {"picked": [1]}))
    reply = await flow.handle_turn(conv, Intent("event", "wallet_uploaded", {"ok": False, "files": []}))
    assert conv["state"] == "ask_doc_method" and "chưa đọc được Ví cá nhân" in reply.display_md


async def test_da_gui_tep_roi_bam_nut_chi_vi_thi_hoi_nhu_thuong(monkeypatch):
    conv, _ = await _only_start(monkeypatch, files_count=3)
    assert conv["wallet_only"] is False


# ── Bản có supportsWalletPick: hai tab, đính bằng nút "Chọn" của ví ──
PICK_CAPS = {**CAPS, wallet_reuse.PICK_CAPABILITY: True}
DEFAULT_ONLY = {"id": "u1", wallet_reuse.SETTING: True, wallet_reuse.SETTING_SAVED: False}


async def test_cai_dat_mac_dinh_chi_bat_cho_ban_chon_tu_vi():
    old = _conv(auth_user=dict(DEFAULT_ONLY))
    await _arrive(old)
    assert old["state"] == "attaching", "bản trên chợ: tài khoản chưa tự bật thì không hỏi như trước"
    new = _conv(caps=PICK_CAPS, auth_user=dict(DEFAULT_ONLY))
    reply = await _arrive(new)
    assert reply.actions == [{"type": "wallet_list", "limit": wallet_reuse.READ_LIMIT, "tabs": ["uploaded", "issued"]}]


async def test_ban_cu_khong_xin_tab_duoc_cap():
    reply = await _arrive(_conv())
    assert reply.actions == [{"type": "wallet_list", "limit": wallet_reuse.LIMIT}]


def test_danh_sach_hai_tab_tai_len_truoc_moi_tab_toi_da_20():
    raw = [{"id": f"c{i}", "uri": f"c{i}", "tab": "issued", "signed": True} for i in range(25)]
    raw += [{"id": f"u{i}", "uri": f"u{i}", "tab": "uploaded"} for i in range(25)]
    raw += [{"id": "z", "uri": "z", "tab": "lạ"}]
    items = wallet_reuse._clean_items(raw)
    assert [i["tab"] for i in items] == ["uploaded"] * 20 + ["issued"] * 20
    assert items[0]["id"] == "u0" and items[20]["id"] == "c0" and items[20]["signed"] is True
    entries = wallet_reuse._entries({"wallet_items": items})
    assert entries[20]["no"] == 21 and entries[20]["tab"] == "issued"


async def test_chep_tep_ban_chon_tu_vi_mang_dau_vi(monkeypatch, tmp_path):
    monkeypatch.setattr(wallet_reuse.up_store.settings, "storage_dir", str(tmp_path))
    wallet_reuse.up_store.save_file_bytes("W1", "f0.pdf", b"%PDF-a")
    wallet = {"_id": "W1", "files": [{"fid": "f0.pdf", "name": "f0.pdf", "type": "application/pdf"}]}
    main = {"_id": "s1", "files": [], "required_docs": [{"key": "khac", "sides": 1}]}
    monkeypatch.setattr(wallet_reuse.up_store, "get", AsyncMock(side_effect=lambda sid: {"W1": wallet, "s1": main}[sid]))
    appended = []

    async def append(sid, metas, limit):
        appended.extend(metas)
        return {**main, "files": metas}
    monkeypatch.setattr(wallet_reuse.up_store, "append_files_with_limit", append)
    monkeypatch.setattr(wallet_reuse, "broadcast", AsyncMock())
    items = wallet_reuse._clean_items([{"id": "c1", "uri": "c1", "name": "KQ_1.pdf", "tab": "issued"}])
    conv = _conv(caps=PICK_CAPS, wallet_session_id="W1", wallet_items=items, wallet_picked=[1])
    assert await wallet_reuse.import_staged(conv, {"f0.pdf": "c1"}) == 1
    assert appended[0]["wallet"] == {"id": "c1", "name": "KQ_1.pdf", "tab": "issued"}


def _item(index, name, **extra):
    return {"fileIndex": index, "fileName": f"f{index}", "documentName": name, "componentName": name,
            "target": "new", "componentIndex": None, "needsAddComponent": True, **extra}


FILES = [{"name": "scan.pdf"}, {"name": "vi-a.pdf", "wallet": {"id": "a", "name": "vi-a.pdf", "tab": "uploaded"}},
         {"name": "vi-b.pdf", "wallet": {"id": "b", "name": "vi-b.pdf", "tab": "issued"}}]


def test_ban_cu_khong_gan_chon_tu_vi():
    plan = [_item(1, "Học bạ")]
    assert wallet_reuse.apply_picks(_conv(), plan, FILES) is plan


def test_muc_dung_nguyen_tep_vi_thi_gan_walletpick():
    plan = [_item(0, "CCCD", target="existing", componentIndex=1), _item(1, "Học bạ")]
    out = wallet_reuse.apply_picks(_conv(caps=PICK_CAPS), plan, FILES)
    assert "walletPick" not in out[0]
    assert out[1]["walletPick"] == {"id": "a", "name": "vi-a.pdf", "tab": "uploaded"}
    assert out[1]["documentName"] == "Học bạ"


def test_muc_gop_tep_vi_voi_tep_scan_thi_tach_moi_tep_vi_mot_dong():
    segs = [{"fileIndex": 0, "pageIndexes": None}, {"fileIndex": 1, "pageIndexes": None},
            {"fileIndex": 2, "pageIndexes": None}]
    plan = [_item(0, "Hợp đồng", target="existing", componentIndex=1, componentName="Bản chính", sourceSegments=segs)]
    out = wallet_reuse.apply_picks(_conv(caps=PICK_CAPS), plan, FILES)
    assert [o.get("walletPick", {}).get("id") for o in out] == [None, "a", "b"]
    assert out[0]["target"] == "existing" and out[0]["componentName"] == "Bản chính" and "sourceSegments" not in out[0]
    assert [o["documentName"] for o in out] == ["Hợp đồng phần 1", "Hợp đồng phần 2", "Hợp đồng phần 3"]
    assert all(o["target"] == "new" and o["componentName"] == o["documentName"] for o in out[1:])
    assert all("sourceSegments" not in o for o in out[1:])


def test_tep_vi_bi_cat_ra_nhieu_giay_thi_giu_tai_len():
    plan = [_item(1, "Giấy A", sourceSegments=[{"fileIndex": 1, "pageIndexes": [0]}]),
            _item(1, "Giấy B", sourceSegments=[{"fileIndex": 1, "pageIndexes": [1]}])]
    out = wallet_reuse.apply_picks(_conv(caps=PICK_CAPS), plan, FILES)
    assert out == plan and all("walletPick" not in o for o in out)


# ── Câu chọn giấy hiểu bằng LLM (ASR trả số bằng chữ) ──
def _llm(monkeypatch, *answers):
    mock = AsyncMock(side_effect=list(answers))
    monkeypatch.setattr(wallet_reuse, "llm_chat", mock)
    return mock


async def test_noi_so_bang_chu_thi_llm_hieu_va_chon(monkeypatch):
    conv = await _choosing()
    llm = _llm(monkeypatch, '{"y": "chon", "so": [1, 2]}', '{"y": "chon", "so": [1, 2, 9]}')
    reply = await flow.handle_turn(conv, Intent("action", "wallet_answer", {"text": "số một và số hai"}))
    assert conv["wallet_picked"] == [1, 2] and "1, 2" in reply.display_md
    prompt = llm.await_args.args[0][0]["content"]
    assert "[1] (Tài liệu tải lên) Scan_0.pdf" in prompt and "chưa chọn giấy nào" in prompt
    await flow.handle_turn(conv, Intent("action", "wallet_answer", {"text": "thêm số chín"}))
    assert conv["wallet_picked"] == [1, 2], "số ngoài danh sách bị bỏ"
    assert "Đang chọn: 1, 2" in llm.await_args.args[0][0]["content"]


async def test_llm_hieu_xong_thi_tai_giay_da_chon(monkeypatch):
    conv = await _choosing()
    _llm(monkeypatch, '{"y": "xong", "so": [2]}')
    reply = await flow.handle_turn(conv, Intent("action", "wallet_answer", {"text": "lấy số hai thôi, xong"}))
    read = next(a for a in reply.actions if a["type"] == "wallet_read")
    assert [i["id"] for i in read["items"]] == ["w1"]


async def test_llm_hieu_bo_qua_thi_roi_buoc_vi(monkeypatch):
    conv = await _choosing()
    _llm(monkeypatch, '{"y": "bo_qua", "so": []}')
    await flow.handle_turn(conv, Intent("action", "wallet_answer", {"text": "thôi không cần đâu"}))
    assert conv["state"] != wallet_reuse.STATE and conv.get("wallet_reuse_done") is True


async def test_llm_khong_ro_thi_hoi_lai(monkeypatch):
    conv = await _choosing()
    _llm(monkeypatch, '{"y": "khong_ro", "so": []}')
    reply = await flow.handle_turn(conv, Intent("action", "wallet_answer", {"text": "ờ ừ"}))
    assert reply.display_md.startswith("Tôi chưa nghe ra số nào") and conv["wallet_picked"] == []


# ── Bản chọn từ ví: chỉ đưa ra giấy đã ký số ──
def _w(i, tab="uploaded", signed=False, name=None, size=None):
    return {"id": f"{tab}{i}", "uri": f"{tab}-{i:04d}", "name": name or f"Giay_{tab}_{i}.pdf",
            "size": 2000 + i if size is None else size, "tab": tab, "signed": signed}


MIXED = {"ok": True, "origin": ORIGIN, "total": 5,
         "items": [_w(0), _w(1, signed=True), _w(2), _w(0, "issued", True, size=0), _w(1, "issued", size=0)]}


async def _pick_listed(listed=MIXED, caps=PICK_CAPS):
    conv = _conv(caps=caps)
    await _arrive(conv)
    reply = await flow.handle_turn(conv, Intent("event", "wallet_list", listed))
    return conv, reply


async def test_ban_chon_tu_vi_chi_dua_ra_giay_da_ky_so():
    conv, reply = await _pick_listed()
    assert [i["id"] for i in conv["wallet_items"]] == ["uploaded1", "issued0"]
    assert "**2 giấy tờ đã ký số**" in reply.display_md and "**1** tài liệu được cấp" in reply.display_md
    assert "bỏ qua **3 giấy tờ chưa ký số**" in reply.display_md
    assert reply.chips[0]["label"] == wallet_reuse.vi.WALLET_YES_SIGNED_LABEL
    reply = await flow.handle_turn(conv, Intent("action", "wallet_use", {}))
    card = reply.cards[0]
    assert [e["no"] for e in card["entries"]] == [1, 2] and all(e["signed"] for e in card["entries"])
    assert [h["tab"] for h in card["hidden"]] == ["uploaded", "uploaded", "issued"]
    assert card["stats"]["hidden"] == 3
    assert "bỏ qua **3 giấy tờ chưa ký số**" in reply.display_md and "bấm vào để xem tên" not in reply.display_md


async def test_extension_ve_duoc_danh_sach_an_thi_moi_bam_xem_ten():
    conv, _ = await _pick_listed(caps={**PICK_CAPS, wallet_reuse.HIDDEN_CAPABILITY: True})
    reply = await flow.handle_turn(conv, Intent("action", "wallet_use", {}))
    assert "bấm vào để xem tên" in reply.display_md


async def test_vi_khong_co_giay_ky_so_thi_bao_roi_dinh_kem_luon():
    listed = {"ok": True, "origin": ORIGIN, "total": 2, "items": [_w(0), _w(1)]}
    conv, reply = await _pick_listed(listed)
    assert conv["state"] == "attaching" and "wallet_hidden" not in conv
    assert "**2 giấy tờ** mới nhất" in reply.display_md and "chưa có giấy tờ nào đã ký số" in reply.display_md


async def test_chi_vi_khong_co_giay_ky_so_thi_ve_buoc_chon_cach_gui(monkeypatch):
    monkeypatch.setattr(upload_service, "progress_of", AsyncMock(return_value={"files_count": 0}))
    conv = _conv(caps=PICK_CAPS, state="collecting_docs", doc_method="scan", owner_phase=False)
    await flow.handle_turn(conv, Intent("action", "wallet_only", {}))
    reply = await flow.handle_turn(conv, Intent("event", "wallet_list",
                                                {"ok": True, "origin": ORIGIN, "items": [_w(0)]}))
    assert conv["state"] == "ask_doc_method" and "chưa có giấy tờ nào đã ký số" in reply.display_md


async def test_ban_cu_van_hien_ca_giay_chua_ky_so():
    conv, reply = await _pick_listed(caps=CAPS)
    assert len(conv["wallet_items"]) == 5 and "đã ký số" not in reply.display_md


def test_bo_ban_trung_cung_ten_goc_cung_dung_luong():
    raw = [_w(0, signed=True, name="Bằng cử nhân.pdf", size=500),
           _w(1, signed=True, name="Bằng cử nhân (1).pdf", size=500),
           _w(2, signed=True, name="Bằng cử nhân - Copy.pdf", size=500),
           _w(3, signed=True, name="Bằng cử nhân.pdf", size=900),
           _w(0, "issued", True, name="GKS.pdf", size=0), _w(1, "issued", True, name="GKS.pdf", size=0)]
    info = {"hidden": [], "duplicates": 0}
    items = wallet_reuse._clean_items(raw, signed_only=True, info=info)
    assert [i["id"] for i in items] == ["uploaded0", "uploaded3", "issued0", "issued1"]
    assert info["duplicates"] == 2


def test_loc_ky_so_moi_muc_van_toi_da_20_giay():
    raw = [_w(i, signed=i % 2 == 0) for i in range(50)]
    info = {"hidden": [], "duplicates": 0}
    items = wallet_reuse._clean_items(raw, signed_only=True, info=info)
    assert len(items) == 20 and all(i["signed"] for i in items) and len(info["hidden"]) == 25
