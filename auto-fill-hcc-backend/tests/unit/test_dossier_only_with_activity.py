"""Hồ sơ RỖNG không được vào sổ quản trị.

Handfree chấm mốc bắt đầu ngay lúc xác nhận thủ tục, nên cán bộ bấm chọn thủ tục rồi bỏ giữa
chừng cũng đẻ ra một dòng trong danh sách — không có lượt điền/đính kèm nào, không nộp, nhìn
vào không biết để làm gì. Auto Fill vốn không có chuyện đó vì chỉ upsert ở /process và
/attachments/plan.
"""
from datetime import datetime, timezone

import pytest

import app.channels.handfree.chat.router as chat_router

_STARTED = datetime(2026, 9, 12, 9, 23, tzinfo=timezone.utc)


@pytest.fixture()
def calls(monkeypatch):
    seen: list[dict] = []

    async def fake_upsert(**kwargs):
        seen.append(kwargs)

    async def noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(chat_router.dossiers_repo, "upsert_started", fake_upsert)
    # _sync_dossier còn ghi sự kiện nộp rồi lưu lại conv — chặn cả hai để test không chạm Mongo.
    monkeypatch.setattr(chat_router.dossiers_repo, "add_submit_event", noop)
    monkeypatch.setattr(chat_router.store, "save", noop)
    return seen


def _conv(**extra):
    return {
        "_id": "conv-1", "dossier_started_at": _STARTED, "procedure_key": "chung-thuc-chu-ky",
        "auth_user": {"id": "u1", "username": "hcc", "name": "Phường Việt Yên"},
        "location": {"province": "Tỉnh Bắc Ninh", "ward": "Phường Việt Yên"},
        **extra,
    }


async def test_chon_thu_tuc_roi_bo_thi_khong_vao_so(calls):
    await chat_router._sync_dossier(_conv())
    assert calls == [], "chưa điền/đính kèm/nộp gì thì không được tạo dòng hồ sơ"


@pytest.mark.parametrize("marker", [
    {"trace_request_id": "req-1"},        # đã có lượt điền
    {"attach_trace_request_id": "req-2"},  # đã có lượt đính kèm
    {"attach_done": True},
    {"submit_clicked_at": _STARTED},       # attach-only: bấm nộp là đủ nghĩa
])
async def test_co_viec_that_thi_vao_so(calls, marker):
    await chat_router._sync_dossier(_conv(**marker))
    assert len(calls) == 1


async def test_giu_nguyen_moc_bat_dau_cu(calls):
    # $setOnInsert giữ started_at, nên hồ sơ vẫn mang mốc lúc xác nhận thủ tục chứ không phải
    # lúc điền — "Thời gian làm" không được ngắn đi vì thay đổi này.
    await chat_router._sync_dossier(_conv(trace_request_id="req-1"))
    assert calls[0]["started_at"] == _STARTED


async def test_co_dinh_luon_sau_khi_da_co_viec(calls):
    # Bước "bổ sung giấy tờ" reset trace_request_id về None. Mất cờ thì các lượt chat sau
    # ngừng cập nhật tên công dân / nhãn thủ tục cho hồ sơ ĐÃ nằm trong sổ.
    conv = _conv(trace_request_id="req-1")
    await chat_router._sync_dossier(conv)
    assert conv.get("dossier_has_activity") is True

    conv["trace_request_id"] = None
    conv["applicant_name"] = "TỐNG ĐỨC HẢI"
    await chat_router._sync_dossier(conv)
    assert len(calls) == 2, "hồ sơ đã vào sổ thì vẫn phải tiếp tục được cập nhật"
