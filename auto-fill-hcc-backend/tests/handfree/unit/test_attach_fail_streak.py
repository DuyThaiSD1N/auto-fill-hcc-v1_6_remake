"""Đính kèm ra 0 tệp hai lần liên tiếp thì DỪNG mời bấm lại.

Sự cố Nghĩa Hưng 21/09/2026: kế hoạch đính kèm chỉ lập MỘT lần rồi được phát lại y nguyên, nên
"Đính kèm lại" luôn ra đúng lỗi cũ; watcher trang lại tự phát lệnh mỗi lần thấy bước Thành phần hồ
sơ → cặp "thử → lỗi" tự sinh mãi trên màn hình.
"""
import pytest

from app.channels.handfree.chat import flow
from app.channels.handfree.chat.flow import Intent


def _conv(**kw):
    base = {
        "_id": "t-fail-streak", "state": "attaching", "history": [],
        "procedure_key": "chung-thuc-chu-ky", "upload_session_id": "sid",
        "attach_plan": [{"fileName": "van-ban.pdf", "componentName": "STT1"}],
        "attach_mode": "split", "attach_done": False,
    }
    base.update(kw)
    return base


async def _report_zero(conv):
    return await flow.handle_turn(
        conv,
        Intent("action", "attach_report", {"attached": 0, "errors": ["Kế hoạch thiếu quan hệ"]}),
    )


@pytest.mark.asyncio
async def test_lan_dau_van_moi_bam_dinh_kem_lai():
    conv = _conv()
    r = await _report_zero(conv)
    assert conv["attach_fail_streak"] == 1
    assert [chip["send"] for chip in r.chips] == ["__event:attach_ready"]


@pytest.mark.asyncio
async def test_lan_hai_doi_sang_duong_thoat_sua_giay_to():
    conv = _conv()
    await _report_zero(conv)
    r = await _report_zero(conv)
    assert conv["attach_fail_streak"] == 2
    # Nút sửa giấy tờ đứng TRƯỚC: đó mới là đường lập lại kế hoạch; bấm lại chỉ phát lại kế hoạch cũ.
    assert [chip["send"] for chip in r.chips] == ["__action:add_documents", "__event:attach_ready"]
    assert "Bấm lại cũng ra kết quả cũ" in r.display_md


@pytest.mark.asyncio
async def test_hong_hai_lan_thi_watcher_khong_tu_phat_lenh_nua():
    conv = _conv()
    await _report_zero(conv)
    await _report_zero(conv)
    r = await flow.handle_turn(
        conv, Intent("event", "page_status", {"attachmentTarget": True, "wizardStep": 3}),
    )
    assert not r.actions, "phải chờ cán bộ tự bấm, không được tự chạy lại kế hoạch hỏng"


@pytest.mark.asyncio
async def test_dinh_duoc_tep_thi_xoa_bo_dem():
    conv = _conv()
    await _report_zero(conv)
    await flow.handle_turn(conv, Intent("action", "attach_report", {"attached": 2, "errors": []}))
    assert conv["attach_fail_streak"] == 0
    assert conv["attach_done"] is True
