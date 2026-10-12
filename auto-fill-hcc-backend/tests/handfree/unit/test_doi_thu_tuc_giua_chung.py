"""Đang làm dở thủ tục A mà công dân gọi tên thủ tục B: đi CHUNG đường với "Làm thủ tục khác".

Trước đây chỉ đổi procedure_key tại chỗ → B mang theo chấp thuận, cách nộp giấy và hồ sơ trên sổ
của A. Một conversation = một hồ sơ → đã có hồ sơ thì FE mở phiên mới và tự chọn B.
"""
from datetime import datetime, timezone

from app.channels.handfree.chat import flow, store
from app.channels.handfree.chat.intents import Intent

BN = {"province": "Thành phố Bắc Ninh", "province_slug": "bacninh", "ward": "Phường Phương Liễu"}
A, B = "khai-sinh-dang-ky-thuong", "chung-thuc-ban-sao"


def _conv_dang_lam_do(started=True):
    c = store.new_conversation(location=dict(BN))
    c["auth_user"] = {"province_slug": "bacninh"}
    c["state"] = "collecting_docs"
    c["procedure_key"] = A
    c["consent"] = {"accepted": True}
    c["doc_method"] = "qr"
    c["attach_mode"] = "merge"
    if started:
        c["dossier_started_at"] = datetime.now(timezone.utc)
    return c


async def test_doi_sang_thu_tuc_khac_bo_het_thu_gan_voi_thu_tuc_cu_va_mo_phien_moi():
    conv = _conv_dang_lam_do()
    r = await flow.handle_turn(conv, Intent("pick_procedure", B))
    assert conv["procedure_key"] == B and conv["state"] == "confirm_procedure"
    assert conv["consent"] is None and conv["doc_method"] is None and conv["attach_mode"] is None
    assert {"type": "new_conversation", "reason": "new_procedure", "procedure_key": B} in r.actions


async def test_chua_co_ho_so_thi_doi_tai_cho_khong_mo_phien_moi():
    conv = _conv_dang_lam_do(started=False)
    r = await flow.handle_turn(conv, Intent("pick_procedure", B))
    assert conv["procedure_key"] == B and conv["consent"] is None
    assert not any(a.get("type") == "new_conversation" for a in r.actions)


async def test_nhac_lai_dung_thu_tuc_dang_lam_thi_khong_reset():
    conv = _conv_dang_lam_do()
    r = await flow.handle_turn(conv, Intent("pick_procedure", A))
    assert conv["state"] == "collecting_docs" and conv["consent"] == {"accepted": True}
    assert not r.actions


async def test_noi_lam_thu_tuc_khac_bang_loi_van_chay_nhu_cu():
    conv = _conv_dang_lam_do()
    r = await flow.handle_turn(conv, Intent("action", "new_procedure"))
    assert conv["state"] == "greet" and conv["procedure_key"] is None and conv["consent"] is None
    assert r.actions == [{"type": "new_conversation", "reason": "new_procedure"}]
