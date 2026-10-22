"""Bước đánh giá trải nghiệm trước đăng xuất (handfree) + lưu bền + backward-compat.

- Client có supportsRating: nộp xong → card 'rating' TRƯỚC 2 nút đăng xuất.
- Cú BẤM nút nộp chỉ chấm mốc, KHÔNG hỏi đánh giá (21/10/2026): phiếu chỉ hiện khi cổng báo nộp
  thành công (event `submitted`).
- Ba nhánh rate_level/rate/rate_skip nằm ở TẦNG TOÀN CỤC (không trong _handle_done): phiên cũ có
  card dựng từ cú bấm lúc state còn "attaching" → phải gọi qua handle_turn mới đúng đường chạy thật.
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
    # Hồ sơ đã có lượt đính kèm của trợ lý — không có thì cú bấm không được tính và không hỏi
    # đánh giá (flow.dossier_has_real_work).
    return {"_id": "c-rate", "client_capabilities": {"supportsRating": True}, "state": "done",
            "attach_trace_request_id": "req-1"}


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


# ── Cú BẤM nút nộp KHÔNG mở màn đánh giá (21/10/2026) ───────────────────────────────────────
# Phiếu chỉ hiện khi cổng báo "nộp hồ sơ thành công". Hỏi lúc bấm thì cổng còn có thể báo thiếu
# giấy tờ, và nút khớp nhầm ở bước giữa làm phiếu bật ra ngay sau khi đính kèm.

def _mid_flow_conv():
    """Đang dở bước đính kèm — đúng tình huống lúc công dân bấm nút nộp trên cổng."""
    return {"_id": "c-click", "client_capabilities": {"supportsRating": True}, "state": "attaching",
            "attach_trace_request_id": "req-1"}


async def test_bam_nut_nop_chi_cham_moc_khong_hoi_danh_gia(mock_save):
    conv = _mid_flow_conv()
    r = await flow.handle_turn(conv, Intent("event", "submit_clicked", {"host": "x.gov.vn"}))

    assert r.cards == [] and r.display_md == "" and r.actions == []
    assert not conv.get("awaiting_rating")
    assert conv.get("submit_clicked_at"), "vẫn phải chấm mốc nộp như trước"
    assert conv["state"] == "attaching", "chấm mốc không được đổi bước đang làm"


async def test_bam_nut_roi_cong_bao_thanh_cong_moi_hien_danh_gia(mock_save):
    conv = _mid_flow_conv()
    await flow.handle_turn(conv, Intent("event", "submit_clicked", {}))
    conv["state"] = "done"
    r = await flow.handle_turn(conv, Intent("event", "submitted"))

    assert [c.get("kind") for c in r.cards] == ["rating"]
    assert conv.get("awaiting_rating") is True
    assert conv["submit_clicked_source"] == "click", "mốc nộp vẫn lấy từ cú bấm"


async def test_phien_cu_card_tu_cu_bam_thi_cong_xac_nhan_khong_dung_card_thu_hai(mock_save):
    # Phiên tạo trước bản này: card đã dựng từ cú bấm (awaiting_rating) → cổng xác nhận chỉ hẹn giờ.
    conv = {**_mid_flow_conv(), "awaiting_rating": True}
    await flow.handle_turn(conv, Intent("event", "submit_clicked", {}))
    conv["state"] = "done"
    r = await flow.handle_turn(conv, Intent("event", "submitted"))

    assert r.cards == [], "card đã có trên màn — không được chồng thêm cái nữa"
    assert [a["type"] for a in r.actions] == ["await_logout_choice"], "giờ mới đúng lúc hẹn đăng xuất"


async def test_phien_cu_danh_gia_truoc_khi_cong_xac_nhan_chua_hen_gio(mock_save):
    # Phiên cũ có card từ cú bấm: đánh giá xong hiện 2 nút NGAY nhưng chưa khởi động đồng hồ tự
    # đăng xuất (cổng chưa xác nhận, còn có thể báo thiếu giấy tờ).
    conv = {**_mid_flow_conv(), "awaiting_rating": True}
    r = await flow.handle_turn(conv, Intent("action", "rate", {"level": 4, "reasons": [], "note": ""}))

    assert conv["rating"]["level"] == 4
    assert [c["send"] for c in r.chips] == _LOGOUT_CHIPS
    assert [a["type"] for a in r.actions] == [], "chưa cổng xác nhận thì chưa hẹn tự đăng xuất"


async def test_da_danh_gia_roi_thi_cong_xac_nhan_chi_hen_gio_khong_lap_nut(mock_save):
    conv = {**_mid_flow_conv(), "awaiting_rating": True}
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


# ── Nút đăng xuất phải BẤM ĐƯỢC ở MỌI state (không chỉ "done") ─────────────────────────────
# 2 nút hiện ngay sau đánh giá, lúc đó cổng thường chưa phát `submitted` nên state vẫn "attaching".
# Handler logout/continue TRƯỚC ĐÂY kẹt trong _handle_done → bấm nút rơi vào fallback "chưa nhận rõ".

async def test_bam_dang_xuat_khi_state_attaching_van_chay(mock_save):
    conv = {"_id": "c-lo", "state": "attaching", "client_capabilities": {"supportsRating": True},
            "submitted_logout_decision": "pending"}
    r = await flow.handle_turn(conv, Intent("action", "logout_citizen"))
    assert [a["type"] for a in r.actions] == ["logout_citizen"]
    assert conv["submitted_logout_decision"] == "logout"


async def test_bam_nop_them_khi_state_attaching_van_chay(mock_save):
    conv = {"_id": "c-lo2", "state": "attaching", "client_capabilities": {"supportsRating": True},
            "submitted_logout_decision": "pending"}
    r = await flow.handle_turn(conv, Intent("action", "continue_dossiers"))
    assert [a["type"] for a in r.actions] == ["continue_dossiers"]
    assert conv["submitted_logout_decision"] == "continue"


def test_nhan_dien_giong_noi_dang_xuat_khi_dang_cho_chon():
    # Rảnh tay gửi giọng nói dạng text tự do → phải bắt tất định (LLM hay trả unknown).
    from app.channels.handfree.chat.intents import resolve_logout_choice as R
    assert R("đăng xuất") == "logout_citizen"
    assert R("Có, hãy đăng xuất") == "logout_citizen"
    assert R("có") == "logout_citizen"
    assert R("đăng xuất tài khoản") == "logout_citizen"
    assert R("không, nộp thêm hồ sơ") == "continue_dossiers"
    assert R("nộp thêm") == "continue_dossiers"
    # Câu KHÁC (không phải trả lời đăng xuất) → None, để không cướp intent khác.
    assert R("đính kèm giấy tờ") is None


async def test_formio_chua_bam_nop_thi_bo_qua_submitted(mock_save):
    """Cổng Form.io dựng sẵn panel "Nộp hồ sơ thành công" (ẩn) — chữ dò được khi chưa bấm nộp không phải nộp."""
    conv = dict(_new_conv(), procedure_key="cap-giay-phep-xay-dung-moi-nha-o-rieng-le")
    r = await flow._handle_done(conv, Intent("event", "submitted"))
    assert r.cards == [] and r.actions == []
    assert not conv.get("submitted_completed")
    # Đã bắt được cú bấm nút nộp → chữ thành công là thật.
    conv["submit_clicked_at"] = "2026-10-21T00:00:00Z"
    r = await flow._handle_done(conv, Intent("event", "submitted"))
    assert conv.get("submitted_completed") is True


async def test_formio_client_cu_giu_hanh_vi_cu(mock_save):
    conv = {"_id": "c-old-formio", "client_capabilities": {}, "state": "done",
            "procedure_key": "cap-giay-phep-xay-dung-moi-nha-o-rieng-le"}
    await flow._handle_done(conv, Intent("event", "submitted"))
    assert conv.get("submitted_completed") is True
