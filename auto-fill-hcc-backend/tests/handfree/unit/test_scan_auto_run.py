"""Scan tại quầy tự chốt sau mỗi đợt chọn tệp: action pick_files mang auto_run (True lượt
thường, False lượt Điều chỉnh giấy tờ) — FE dựa cờ này để tự gửi docs_done thay nút bấm."""
import pytest

from app.channels.handfree.chat import flow
from app.channels.handfree.chat.intents import Intent
from app.channels.handfree.documents import service as upload_service


@pytest.fixture
def stub_upload_session(monkeypatch):
    async def fake_create(conv):
        conv["upload_session_id"] = "HS-TEST"
        return {"type": "show_qr", "session_id": "HS-TEST", "mobile_url": "", "qr_png_base64": ""}

    monkeypatch.setattr(upload_service, "create_for_conversation", fake_create)


def _conv(**kw):
    base = {"_id": "t-scan-auto", "state": "ask_doc_method", "history": [],
            "procedure_key": "ket-hon",
            "client_capabilities": {"supportsScanAutoRun": True}}
    base.update(kw)
    return base


async def test_scan_luot_dau_auto_run_va_bao_truoc(stub_upload_session):
    conv = _conv()
    r = await flow._apply_doc_method(conv, "scan", reuse_session=False)
    action = next(a for a in r.actions if a["type"] == "pick_files")
    assert action["auto_run"] is True
    assert "Đã đưa đủ giấy tờ" in r.display_md, "phải hướng dẫn bấm Đã đưa đủ khi scan xong"


async def test_extension_cu_khong_khai_capability_giu_chot_tay(stub_upload_session):
    """Bản chợ cũ không khai supportsScanAutoRun → KHÔNG auto và KHÔNG nối câu bấm 'Đã đưa đủ'."""
    conv = _conv(client_capabilities={})
    r = await flow._apply_doc_method(conv, "scan", reuse_session=False)
    action = next(a for a in r.actions if a["type"] == "pick_files")
    assert action["auto_run"] is False
    assert "Đã đưa đủ giấy tờ" not in r.display_md


async def test_scan_luot_dieu_chinh_giu_chot_tay(stub_upload_session):
    conv = _conv(supplementing_documents=True, supplement_reuse_session=True,
                 upload_session_id="HS-CU")
    r = await flow._apply_doc_method(conv, "scan", reuse_session=True)
    action = next(a for a in r.actions if a["type"] == "pick_files")
    assert action["auto_run"] is False, "điều chỉnh có thể chỉ xóa tệp — phải giữ nút hoàn tất"
    assert "tự xử lý luôn" not in r.display_md


async def test_pick_files_again_mang_cung_co(stub_upload_session):
    conv = _conv(state="collecting_docs", doc_method="scan", upload_session_id="HS-TEST")
    r = await flow._handle_collecting_docs(conv, Intent("action", "pick_files_again"))
    action = next(a for a in r.actions if a["type"] == "pick_files")
    assert action["auto_run"] is True

    conv2 = _conv(state="collecting_docs", doc_method="scan", upload_session_id="HS-TEST",
                  supplementing_documents=True)
    r2 = await flow._handle_collecting_docs(conv2, Intent("action", "pick_files_again"))
    assert next(a for a in r2.actions if a["type"] == "pick_files")["auto_run"] is False
