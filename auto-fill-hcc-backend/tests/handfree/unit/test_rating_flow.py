"""Bước đánh giá trải nghiệm trước đăng xuất (handfree) + lưu bền + backward-compat.

- Client có supportsRating: nộp xong → card 'rating' TRƯỚC 2 nút đăng xuất.
- Ba nhánh rate_level/rate/rate_skip nằm ở TẦNG TOÀN CỤC (không trong _handle_done) vì card
  dựng được ngay từ cú BẤM nút nộp, lúc đó state có thể vẫn là "attaching" → phải gọi qua
  handle_turn mới đúng đường chạy thật.
- rate / rate_skip → lưu vào dossiers (save_rating) + hiện 2 nút đăng xuất.
- Client CŨ (không supportsRating): giữ NGUYÊN luồng cũ (2 nút ngay, không card).
"""
from unittest.mock import AsyncMock

import pytest

from app.channels.handfree.chat import flow
from app.channels.handfree.chat.intents import Intent

_LOGOUT_CHIPS = ["__action:logout_citizen", "__action:continue_dossiers"]


@pytest.fixture
def mock_save(monkeypatch):
    m = AsyncMock()
    monkeypatch.setattr(flow.dossiers_repo, "save_rating", m)
    return m


def _new_conv():
    return {"_id": "c-rate", "client_capabilities": {"supportsRating": True}, "state": "done"}


async def test_submitted_new_client_shows_rating_before_logout(mock_save):
    conv = _new_conv()
    r = await flow._handle_done(conv, Intent("event", "submitted"))
    assert [c.get("kind") for c in r.cards] == ["rating"]
    assert r.chips == []                       # CHƯA hiện 2 nút đăng xuất
    assert r.display_md == ""                  # KHÔNG bong bóng mời (title card đã là câu mời)
    assert r.tts_text                          # nhưng vẫn ĐỌC câu mời
    assert conv.get("awaiting_rating") is True


async def test_rate_saves_and_then_logout_choice(mock_save):
    conv = _new_conv()
    await flow._handle_done(conv, Intent("event", "submitted"))
    r = await flow.handle_turn(conv, Intent("action", "rate",
        {"level": 5, "reasons": ["Làm nhanh hơn trước", "Nói được, không cần gõ"], "note": "tốt lắm"}))
    assert conv["rating"]["level"] == 5
    assert conv["rating"]["level_label"] == "Rất hài lòng"
    assert conv["rating"]["reasons"] == ["Làm nhanh hơn trước", "Nói được, không cần gõ"]
    assert conv["rating"]["skipped"] is False
    assert conv.get("awaiting_rating") is False
    assert mock_save.await_count == 1
    assert [c["send"] for c in r.chips] == _LOGOUT_CHIPS
    # Cảm ơn hiện TRONG card (FE) → khối sau chỉ là câu hỏi đăng xuất, không bong bóng cảm ơn.
    assert "đăng xuất" in r.display_md.lower()


async def test_rate_clamps_level_and_trims(mock_save):
    conv = _new_conv()
    await flow._handle_done(conv, Intent("event", "submitted"))
    await flow.handle_turn(conv, Intent("action", "rate",
        {"level": 99, "reasons": ["x" * 500], "note": "y" * 5000}))
    assert conv["rating"]["level"] == 5           # clamp 1..5
    assert len(conv["rating"]["reasons"][0]) <= 120
    assert len(conv["rating"]["note"]) <= 1000


async def test_rate_level_logs_immediately_without_finalizing(mock_save):
    # Chọn mức (bước 1) → LƯU NGAY, giữ awaiting_rating, KHÔNG hiện 2 nút, KHÔNG đổi card.
    conv = _new_conv()
    await flow._handle_done(conv, Intent("event", "submitted"))
    r = await flow.handle_turn(conv, Intent("action", "rate_level", {"level": 4}))
    assert conv["rating"]["level"] == 4
    assert conv["rating"]["skipped"] is False
    assert conv.get("awaiting_rating") is True     # CHƯA chốt — vẫn ở bước 2
    assert r.chips == [] and r.cards == []          # im lặng
    assert mock_save.await_count == 1               # đã ghi log mức


async def test_reload_after_level_reshows_card(mock_save):
    conv = _new_conv()
    await flow._handle_done(conv, Intent("event", "submitted"))
    await flow.handle_turn(conv, Intent("action", "rate_level", {"level": 3}))
    # Reload khi đã log mức nhưng chưa chốt → dựng lại card (không nhảy sang đăng xuất).
    r = await flow._handle_done(conv, Intent("event", "submitted"))
    assert [c.get("kind") for c in r.cards] == ["rating"]


async def test_step2_skip_keeps_level(mock_save):
    # Bỏ qua Ở BƯỚC 2 = chốt GIỮ mức (reasons rỗng), KHÔNG phải skipped.
    conv = _new_conv()
    await flow._handle_done(conv, Intent("event", "submitted"))
    await flow.handle_turn(conv, Intent("action", "rate_level", {"level": 5}))
    r = await flow.handle_turn(conv, Intent("action", "rate", {"level": 5, "reasons": [], "note": ""}))
    assert conv["rating"]["level"] == 5
    assert conv["rating"]["skipped"] is False
    assert [c["send"] for c in r.chips] == _LOGOUT_CHIPS


async def test_rate_skip_marks_skipped(mock_save):
    conv = _new_conv()
    await flow._handle_done(conv, Intent("event", "submitted"))
    r = await flow.handle_turn(conv, Intent("action", "rate_skip"))
    assert conv["rating"]["skipped"] is True
    assert conv["rating"]["level"] is None
    assert mock_save.await_count == 1
    assert [c["send"] for c in r.chips] == _LOGOUT_CHIPS


async def test_old_client_keeps_old_logout_flow(mock_save):
    # KHÔNG khai supportsRating → luồng cũ: 2 nút đăng xuất NGAY, không card rating.
    conv = {"_id": "c-old", "client_capabilities": {}, "state": "done"}
    r = await flow._handle_done(conv, Intent("event", "submitted"))
    assert r.cards == []
    assert [c["send"] for c in r.chips] == _LOGOUT_CHIPS
    assert conv.get("awaiting_rating") is None
    mock_save.assert_not_awaited()


async def test_submitted_reload_reshows_rating(mock_save):
    conv = _new_conv()
    await flow._handle_done(conv, Intent("event", "submitted"))
    # Sidebar reload → phát lại 'submitted' khi chưa đánh giá → dựng lại card (không bong bóng).
    r = await flow._handle_done(conv, Intent("event", "submitted"))
    assert [c.get("kind") for c in r.cards] == ["rating"]
    assert r.display_md == ""


# ── Mốc thứ hai: CÚ BẤM nút nộp cũng mở màn đánh giá (thống nhất với Auto Fill) ─────────────
# "Bấm nộp = coi như đã nộp". Chờ cổng báo "nộp hồ sơ thành công" thì phần lớn cổng không bao
# giờ hỏi được — câu chữ khác nhau và chỉ thu thập được bằng cách nộp hồ sơ thật.

def _mid_flow_conv():
    """Đang dở bước đính kèm — đúng tình huống lúc công dân bấm nút nộp trên cổng."""
    return {"_id": "c-click", "client_capabilities": {"supportsRating": True}, "state": "attaching"}


async def test_bam_nut_nop_mo_ngay_man_danh_gia(mock_save):
    conv = _mid_flow_conv()
    r = await flow.handle_turn(conv, Intent("event", "submit_clicked", {"host": "x.gov.vn"}))

    assert [c.get("kind") for c in r.cards] == ["rating"]
    assert conv.get("awaiting_rating") is True
    assert conv.get("submit_clicked_at"), "vẫn phải chấm mốc nộp như trước"
    assert conv["state"] == "attaching", "chấm mốc không được đổi bước đang làm"
    # Cổng CHƯA xác nhận → tuyệt đối không khởi động đồng hồ tự đăng xuất 2 phút: cổng còn có
    # thể báo thiếu giấy tờ và công dân phải sửa tiếp.
    assert [a["type"] for a in r.actions] == []


async def test_cham_muc_giua_chung_van_luu_va_van_khong_dem_gio(mock_save):
    conv = _mid_flow_conv()
    await flow.handle_turn(conv, Intent("event", "submit_clicked", {}))
    r = await flow.handle_turn(conv, Intent("action", "rate_level", {"level": 5}))

    assert conv["rating"]["level"] == 5, "mức chọn ở bước 1 phải lưu ngay, kể cả khi chưa 'done'"
    assert mock_save.await_count == 1
    assert [a["type"] for a in r.actions] == [], "chưa xác nhận nộp thì chưa hẹn đăng xuất"


async def test_danh_gia_xong_hien_nut_nhung_chua_hen_gio_khi_cong_chua_xac_nhan(mock_save):
    # Đánh giá xong = HIỆN 2 nút đăng xuất NGAY: event `submitted` phần lớn cổng không fire, chờ nó
    # thì khối chọn đăng xuất "lúc có lúc không" (bug thật). NHƯNG chưa khởi động đồng hồ tự đăng
    # xuất 2 phút vì cổng chưa xác nhận (còn có thể báo thiếu giấy tờ) — nút vẫn bấm tay được.
    conv = _mid_flow_conv()
    await flow.handle_turn(conv, Intent("event", "submit_clicked", {}))
    r = await flow.handle_turn(conv, Intent("action", "rate", {"level": 4, "reasons": [], "note": ""}))

    assert conv["rating"]["level"] == 4
    assert [c["send"] for c in r.chips] == _LOGOUT_CHIPS
    assert [a["type"] for a in r.actions] == [], "chưa cổng xác nhận thì chưa hẹn tự đăng xuất"


async def test_cong_xac_nhan_muon_khong_dung_card_thu_hai(mock_save):
    conv = _mid_flow_conv()
    await flow.handle_turn(conv, Intent("event", "submit_clicked", {}))
    conv["state"] = "done"
    r = await flow.handle_turn(conv, Intent("event", "submitted"))

    assert r.cards == [], "card đã dựng từ lúc bấm nút — không được chồng thêm cái nữa"
    assert [a["type"] for a in r.actions] == ["await_logout_choice"], "giờ mới đúng lúc hẹn đăng xuất"


async def test_da_danh_gia_roi_thi_cong_xac_nhan_chi_hen_gio_khong_lap_nut(mock_save):
    conv = _mid_flow_conv()
    await flow.handle_turn(conv, Intent("event", "submit_clicked", {}))
    r1 = await flow.handle_turn(conv, Intent("action", "rate_skip"))
    # Đánh giá xong: nút đăng xuất hiện NGAY (chưa kèm đồng hồ vì cổng chưa xác nhận).
    assert [c["send"] for c in r1.chips] == _LOGOUT_CHIPS
    assert [a["type"] for a in r1.actions] == []
    conv["state"] = "done"
    r2 = await flow.handle_turn(conv, Intent("event", "submitted"))
    # Cổng xác nhận MUỘN: KHÔNG đẻ khối nút thứ hai, chỉ khởi động đồng hồ tự đăng xuất.
    assert r2.cards == []
    assert r2.chips == []
    assert [a["type"] for a in r2.actions] == ["await_logout_choice"]


async def test_client_cu_khong_khai_co_thi_bam_nut_van_im_lang(mock_save):
    conv = {"_id": "c-old", "state": "attaching"}   # không có supportsRating
    r = await flow.handle_turn(conv, Intent("event", "submit_clicked", {}))

    assert r.cards == [] and r.display_md == ""
    assert conv.get("submit_clicked_at"), "bản cũ vẫn phải chấm được mốc nộp"
