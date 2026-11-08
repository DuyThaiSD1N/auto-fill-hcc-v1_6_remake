"""Khôi phục hồ sơ đang làm dở (chat/resume/) — thí điểm đăng ký kết hôn, tư pháp form cũ.

Kho bản ghi thay bằng dict trong bộ nhớ; flow chạy thật. Luồng: lưu mốc → gợi ý khi chọn lại thủ tục → khôi phục
→ tới bước nhận giấy tờ thì nạp lại phiên cũ (không xin đồng ý lại) → tới bước nào đưa lại dữ liệu bước đó.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import flow, pipeline_runner, store as conv_store
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.intents import Intent
from app.channels.handfree.chat.resume import registry, replay, service
from app.channels.handfree.chat.resume import store as resume_store
from app.channels.handfree.chat.resume.base import merge_fields
from app.channels.handfree.chat.resume.tu_phap_cu import TuPhapCuAdapter

CAPS = {"supportsResume": True}
OLD_SID = "HS-OLD"
OWNER_FIELDS = [{"key": "Owner_HoTen", "value": "Tên mẫu", "overwrite": False}]
TOOL_FIELDS = [{"name": "HoTen", "comp": "x-input", "value": "A"}, {"name": "NoiCuTru", "comp": "x-input", "value": "B"}]


class FakeStore:
    def __init__(self):
        self.docs: dict[str, dict] = {}

    async def get(self, record_id):
        return self.docs.get(record_id)

    async def latest(self, user_id, procedure_key):
        found = [d for d in self.docs.values() if d.get("user_id") == user_id and d.get("procedure_key") == procedure_key]
        return found[-1] if found else None

    async def save(self, record_id, fields):
        now = datetime.now(timezone.utc)
        self.docs.setdefault(record_id, {"_id": record_id}).update(
            {**fields, "last_activity_at": now, "expires_at": now + resume_store.WINDOW})

    async def rekey(self, record, new_id):
        moved = {**record, "_id": new_id, "resumed_from": record["_id"]}
        self.docs.pop(record["_id"], None)
        self.docs[new_id] = moved
        return moved

    async def close(self, record_id, reason):
        if record_id in self.docs:
            self.docs[record_id].update(close_reason=reason, closed_at=datetime.now(timezone.utc))

    async def delete(self, record_id):
        self.docs.pop(record_id, None)


@pytest.fixture()
def fake(monkeypatch):
    fake = FakeStore()
    for name in ("get", "latest", "save", "rekey", "close", "delete"):
        monkeypatch.setattr(resume_store, name, getattr(fake, name))
    session = {"_id": OLD_SID, "files": [{"fid": "f1", "doc_key": "cccd_nam"}, {"fid": "f2", "doc_key": "cccd_nu"}]}
    monkeypatch.setattr(service.up_store, "get", AsyncMock(side_effect=lambda sid: session if sid == OLD_SID else None))
    monkeypatch.setattr(service.up_store, "rebind_conversation", AsyncMock())
    monkeypatch.setattr(flow.upload_service, "sync_for_conversation", AsyncMock())
    monkeypatch.setattr(flow.upload_service, "progress_of",
                        AsyncMock(return_value={"received": 2, "total": 2, "files_count": 2}))
    spawned = []

    def _spawn(coro):
        spawned.append(coro.__qualname__)
        coro.close()

    monkeypatch.setattr(pipeline_runner, "spawn", _spawn)
    fake.spawned = spawned
    return fake


def _conv(state="confirm_procedure", **extra):
    conv = conv_store.new_conversation()
    conv.update({"procedure_key": "ket-hon", "state": state, "client_capabilities": dict(CAPS),
                 "auth_user": {"id": "u1"}})
    conv.update(extra)
    return conv


def _record(**steps):
    now = datetime.now(timezone.utc)
    return {"_id": "c-old", "user_id": "u1", "procedure_key": "ket-hon", "family": "tu-phap",
            "principal": {"name": "NGƯỜI MẪU", "cccd": "001"}, "upload_session_id": OLD_SID, "doc_method": "scan",
            "consent": {"accepted": True, "id": "TLND-1"}, "steps": steps,
            "last_activity_at": now, "expires_at": now + timedelta(minutes=25)}


async def _turn(conv, kind, value="", payload=None, page=None):
    return await flow.handle_turn(conv, Intent(kind, value, payload or {}), page)


# ── Bật / tắt ──

def test_chi_bat_cho_thu_tuc_thi_diem_khi_extension_khai_co():
    assert isinstance(registry.adapter_for(_conv()), TuPhapCuAdapter)
    assert registry.adapter_for(_conv(client_capabilities={})) is None, "bản extension cũ trên chợ: không đổi gì"
    assert registry.adapter_for(_conv(procedure_key="khai-tu")) is None
    assert registry.adapter_for(_conv(lang="hmong")) is None, "câu khôi phục chưa có bản Mông"


# ── Gợi ý khi chọn lại thủ tục ──

async def test_chon_lai_thu_tuc_co_ho_so_do_thi_goi_y_khoi_phuc(fake):
    fake.docs["c-old"] = _record(owner={"fields": OWNER_FIELDS})
    conv = _conv()
    reply = await _turn(conv, "confirm")
    assert "NGƯỜI MẪU" in reply.display_md and "đã điền chủ hồ sơ" in reply.display_md
    assert [c["send"] for c in reply.chips] == [service.ACCEPT_SEND, service.DECLINE_SEND]
    assert conv["state"] == "confirm_procedure", "chưa đi tiếp khi công dân chưa chọn"


async def test_khong_co_ho_so_do_hoac_tai_khoan_khac_thi_di_tiep_nhu_cu(fake):
    fake.docs["c-old"] = {**_record(), "user_id": "u2"}
    conv = _conv()
    await _turn(conv, "confirm")
    assert conv["state"] == "guide_login" and "resume_offer" not in conv


async def test_lam_moi_hoan_toan_thi_xoa_ho_so_do(fake):
    fake.docs["c-old"] = _record()
    conv = _conv()
    await _turn(conv, "confirm")
    await _turn(conv, "action", "resume_decline")
    assert conv["state"] == "guide_login" and not fake.docs and "resume" not in conv


async def test_khoi_phuc_thi_chuyen_ban_ghi_sang_hoi_thoai_moi(fake):
    fake.docs["c-old"] = _record(owner={"fields": OWNER_FIELDS})
    conv = _conv()
    await _turn(conv, "confirm")
    reply = await _turn(conv, "action", "resume_accept")
    assert conv["state"] == "guide_login"
    assert reply.display_md.startswith("✓ Tôi khôi phục hồ sơ dở")
    assert list(fake.docs) == [conv["_id"]], "lần gián đoạn sau vẫn khôi phục được"
    assert conv["resume"]["steps"]["owner"]["fields"] == OWNER_FIELDS


# ── Khôi phục từng bước ──

async def _resumed(fake, **steps):
    fake.docs["c-old"] = _record(**steps)
    conv = _conv()
    await _turn(conv, "confirm")
    await _turn(conv, "action", "resume_accept")
    return conv


OWNER_PAGE = {"wizardStep": 1, "loggedIn": True, "principal": {"name": "NGƯỜI MẪU", "cccd": "001"},
              "ownerContext": {"fullName": "NGƯỜI MẪU", "identityNumber": "001"}}


async def test_toi_buoc_chu_ho_so_nap_lai_giay_to_khong_xin_dong_y_va_dien_lai_chu_ho_so(fake):
    conv = await _resumed(fake, owner={"fields": OWNER_FIELDS, "match": {"matched": True}})
    reply = await _turn(conv, "event", "page_status", dict(OWNER_PAGE))
    assert conv["upload_session_id"] == OLD_SID and conv["consent"]["id"] == "TLND-1"
    service.up_store.rebind_conversation.assert_awaited_once_with(OLD_SID, conv["_id"])
    types = [a["type"] for a in reply.actions]
    assert types[0] == "resume_upload_session" and "fill_owner_fields" in types
    assert next(a for a in reply.actions if a["type"] == "fill_owner_fields")["fields"] == OWNER_FIELDS
    assert not any(c.get("kind") in ("consent", "consent_form") for c in reply.cards), "không xin đồng ý lại"
    assert "Đã khôi phục **2 tệp**" in reply.display_md
    assert fake.spawned == ["run_owner_info"], "flow vẫn đi đường cũ, tác vụ OCR/LLM bị chặn trong replay"


async def test_ho_so_do_chua_co_dong_y_thi_van_xin_dong_y_truoc(fake):
    fake.docs["c-old"] = {**_record(owner={"fields": OWNER_FIELDS}), "consent": None}
    conv = _conv()
    await _turn(conv, "confirm")
    await _turn(conv, "action", "resume_accept")
    reply = await _turn(conv, "event", "page_status", dict(OWNER_PAGE))
    assert conv["state"] == "consent" and not conv["resume"]["docs_restored"]
    assert not any(a["type"] == "resume_upload_session" for a in reply.actions)


async def test_buoc_chua_luu_thi_chay_pipeline_nhu_thuong(fake):
    conv = await _resumed(fake)
    reply = await _turn(conv, "event", "page_status", dict(OWNER_PAGE))
    assert conv["state"] == "owner_filling" and conv["pipeline_status"] == "running"
    assert not any(a["type"] == "fill_owner_fields" for a in reply.actions)
    assert not replay.skip_pipeline("owner")


async def test_dang_nhap_nguoi_khac_thi_khong_khoi_phuc(fake):
    conv = await _resumed(fake, owner={"fields": OWNER_FIELDS})
    page = {**OWNER_PAGE, "principal": {"name": "KHÁC", "cccd": "999"}, "ownerContext": {"fullName": "KHÁC"}}
    reply = await _turn(conv, "event", "page_status", page)
    assert "resume" not in conv and not fake.docs
    assert conv.get("upload_session_id") != OLD_SID
    assert "không phải người của hồ sơ dở" in reply.display_md


async def test_toi_buoc_to_khai_dien_lai_uu_tien_ban_can_bo_sua(fake):
    declaration = {"fields": TOOL_FIELDS, "request_id": "req-1", "answers": [{"key": "NoiCuTru", "value": "C"}]}
    conv = await _resumed(fake, declaration=declaration)
    conv["resume"]["snapshot"] = {"request_id": "req-1", "at": 1, "fields": [
        {"name": "HoTen", "comp": "x-input", "value": "A sửa"}, {"name": "GhiChu", "comp": "x-input", "value": "thêm"}]}
    conv.update(state="owner_waiting_next", upload_session_id=OLD_SID, owner_info_done=True,
                consent={"accepted": True}, resume={**conv["resume"], "docs_restored": True})
    reply = await _turn(conv, "event", "page_status", {"wizardStep": 2, "formKind": "legacy"})
    fill = next(a for a in reply.actions if a["type"] == "fill_fields")
    assert {f["name"]: f["value"] for f in fill["fields"]} == {"HoTen": "A sửa", "NoiCuTru": "C", "GhiChu": "thêm"}
    assert fill["formSnapshot"]["requestId"] == "req-1", "ảnh chụp lần này vẫn nối về bản ghi khôi phục"
    assert "điền lại tờ khai" in reply.display_md
    assert fake.spawned == ["run_process"]


# ── Lưu mốc / đóng phiên ──

async def test_luu_moc_chi_khi_da_co_giay_to_va_xoa_khi_da_nop(fake):
    conv = _conv("owner_waiting_next", upload_session_id="HS-NONE")
    await service.checkpoint(conv)
    assert not fake.docs, "chưa đưa giấy tờ → không có gì để khôi phục"
    conv.update(upload_session_id=OLD_SID, owner_fields=OWNER_FIELDS, owner_fields_dispatched=True,
                portal_principal={"name": "NGƯỜI MẪU", "cccd": "001"}, consent={"accepted": True, "id": "X"})
    await service.checkpoint(conv)
    saved = fake.docs[conv["_id"]]
    assert saved["steps"]["owner"]["fields"] == OWNER_FIELDS and saved["principal"]["name"] == "NGƯỜI MẪU"
    conv["submit_clicked_at"] = datetime.now(timezone.utc)
    await service.checkpoint(conv)
    assert not fake.docs


@pytest.mark.parametrize("reason, kept", [("idle", True), ("dvc-home", True), ("manual", False),
                                          ("new_procedure", False), ("completed", False), ("", False)])
async def test_dong_phien_chi_giu_khi_gian_doan_ngoai_y_can_bo(fake, reason, kept):
    fake.docs["c-old"] = _record()
    await service.on_close("c-old", reason)
    assert ("c-old" in fake.docs) is kept


# ── Lớp chung ──

def test_ghep_lenh_dien_ban_sua_moi_nhat_thang_o_trong_khong_xoa():
    fields = [{"name": "A", "value": "1"}, {"name": "B", "value": "2", "occurrence": 1}]
    out = merge_fields(fields, [{"key": "A", "value": "1b"}],
                       [{"name": "A", "value": "1c"}, {"name": "B", "value": "", "occurrence": 1}])
    assert out == [{"name": "A", "value": "1c"}, {"name": "B", "value": "2", "occurrence": 1}]


def test_ke_hoach_dinh_kem_chi_dung_lai_khi_danh_sach_tep_khong_doi():
    adapter = TuPhapCuAdapter()
    conv = _conv(attach_plan=[{"fileIndex": 0}], attach_trace_request_id="att-1")
    data = adapter.capture_attach(conv, {}, ["f1", "f2"])
    resume = {"steps": {"attach": data}, "replayed": []}
    assert adapter.replayable(resume, ["f1", "f2"]) == {"attach"}
    assert adapter.replayable(resume, ["f1", "f2", "f3"]) == set(), "thêm giấy → lập lại kế hoạch"
    assert adapter.capture_attach(conv, data, ["f1", "f2", "f3"])["fids"] == ["f1", "f2"], "cùng kế hoạch giữ mốc tệp"


async def test_tac_vu_nen_cua_buoc_dang_nap_lai_tu_bo_qua(monkeypatch):
    get = AsyncMock()
    monkeypatch.setattr(pipeline_runner.up_store, "get", get)
    replay.set_kinds({"process"})
    try:
        await pipeline_runner.run_process("c-1", "s-1", "ket-hon")
    finally:
        replay.set_kinds(())
    get.assert_not_awaited()


def test_cau_thoai_khoi_phuc_du_cho_moi_buoc():
    assert set(vi.RESUME_STEP_REPLAYED) == {s.key for s in TuPhapCuAdapter.steps} <= set(vi.RESUME_PROGRESS)


# ── Bản chủ hồ sơ cán bộ sửa tay: đọc lúc bấm sang bước sau ──

OWNER_SPECS = [{"key": k, "label": k, "value": "máy", "overwrite": False}
               for k in ("Owner_HoTen", "Owner_NgaySinh", "Owner_SoGiayTo", "Owner_DiaChi")]


def _report(values, ok=True):
    return Intent("action", "guided_step_report", {"phase": "field_review_owner", "ok": ok, "wizardStep": 2,
                                                    "ownerFields": {k: {"value": v, "required": True}
                                                                    for k, v in values.items()}})


def test_nut_sang_buoc_sau_nho_extension_doc_o_chu_ho_so():
    conv = _conv("owner_waiting_next", owner_fields=OWNER_SPECS)
    reply = flow.Reply()
    reply.actions = [{"type": "guided_click_next", "phase": "field_review_owner", "expectStep": 2}]
    TuPhapCuAdapter().decorate(conv, reply)
    specs = reply.actions[0]["readOwnerFields"]
    assert [s["key"] for s in specs] == [f["key"] for f in OWNER_SPECS]
    assert all("value" not in s and "overwrite" not in s for s in specs), "chỉ gửi cách tìm ô, không gửi giá trị"


@pytest.mark.parametrize("values, ok, saved", [
    ({"Owner_HoTen": "A", "Owner_NgaySinh": "01/01/1990", "Owner_SoGiayTo": "001", "Owner_DiaChi": "X"}, True, True),
    ({"Owner_HoTen": "A", "Owner_NgaySinh": "01/01/1990", "Owner_SoGiayTo": "001", "Owner_DiaChi": ""}, True, False),
    ({"Owner_HoTen": "A", "Owner_NgaySinh": "01/01/1990", "Owner_SoGiayTo": "001"}, True, False),
    ({"Owner_HoTen": "A", "Owner_NgaySinh": "01/01/1990", "Owner_SoGiayTo": "001", "Owner_DiaChi": "X"}, False, False),
])
def test_chi_luu_ban_chu_ho_so_khi_du_o_va_da_sang_buoc(values, ok, saved):
    conv = _conv("owner_waiting_next", owner_fields=OWNER_SPECS)
    TuPhapCuAdapter().observe(conv, _report(values, ok))
    assert ("owner_edited" in conv) is saved


async def test_khoi_phuc_chu_ho_so_dung_ban_can_bo_sua(fake):
    edited = {"Owner_HoTen": "A sửa", "Owner_NgaySinh": "02/02/1990", "Owner_SoGiayTo": "001", "Owner_DiaChi": "Y"}
    conv = _conv("owner_waiting_next", upload_session_id=OLD_SID, owner_fields=OWNER_SPECS,
                 owner_fields_dispatched=True)
    await _turn(conv, "action", "guided_step_report", _report(edited).payload)
    await service.checkpoint(conv)
    assert fake.docs[conv["_id"]]["steps"]["owner"]["edited"] == edited
    fake.docs["c-old"] = {**fake.docs.pop(conv["_id"]), "_id": "c-old", "user_id": "u1", "procedure_key": "ket-hon",
                          "consent": {"accepted": True}, "principal": {"cccd": "001"}}
    again = _conv()
    await _turn(again, "confirm")
    await _turn(again, "action", "resume_accept")
    reply = await _turn(again, "event", "page_status", dict(OWNER_PAGE))
    fill = next(a for a in reply.actions if a["type"] == "fill_owner_fields")
    assert {f["key"]: f["value"] for f in fill["fields"]} == edited
    assert all(f["overwrite"] is False for f in fill["fields"]), "ô cổng đã có sẵn vẫn giữ nguyên"


async def test_ban_extension_cu_khong_khai_co_thi_khong_goi_y_khong_luu_khong_chan_tac_vu(fake):
    fake.docs["c-old"] = _record(owner={"fields": OWNER_FIELDS})
    conv = _conv(client_capabilities={})
    reply = await _turn(conv, "confirm")
    assert conv["state"] == "guide_login" and service.ACCEPT_SEND not in [c["send"] for c in reply.chips]
    assert not replay.skip_pipeline("owner") and not replay.skip_pipeline("process")
    conv.update(upload_session_id=OLD_SID, owner_fields=OWNER_SPECS, owner_fields_dispatched=True)
    await service.checkpoint(conv)
    assert list(fake.docs) == ["c-old"], "không ghi bản ghi cho hội thoại của bản cũ"
    click = flow.Reply()
    click.actions = [{"type": "guided_click_next", "phase": "field_review_owner", "expectStep": 2}]
    out = await service.after_turn(conv, Intent("action", "x"), click, None)
    assert out.actions == [{"type": "guided_click_next", "phase": "field_review_owner", "expectStep": 2}]
