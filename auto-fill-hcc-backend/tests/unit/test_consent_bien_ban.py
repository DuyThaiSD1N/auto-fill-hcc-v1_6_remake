"""Biên bản chấp thuận xử lý dữ liệu cá nhân: chép NGUYÊN VĂN thẻ đã hiển thị + toàn văn Điều 4 Luật 91/2025/QH15,
trình bày theo thể thức Nghị định 30/2020 (Times New Roman, A4, lề, Quốc hiệu, số trang), có mã băm để đối chiếu."""
import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import fitz
import pytest

from app.channels.handfree.chat import consent as hf_consent
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat.consent_pdf import build_consent_pdf as build_handfree_pdf
from app.config import settings
from app.consent import pdf as consent_pdf
from app.consent import store, texts

AT = datetime(2026, 10, 26, 2, 42, 31, tzinfo=timezone.utc)  # 09:42:31 giờ Việt Nam
NOTICE = texts.AUTOFILL_NOTICES["v1.1"]


def _plain(s: str) -> str:
    # NFC: Times New Roman dùng chung hình chữ cho ";" và U+037E → chữ trích ra là U+037E, NFC đưa về ";".
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s.replace("**", ""))).strip()


def _text(pdf: bytes) -> str:
    doc = fitz.open("pdf", pdf)
    # Chỉ vùng nội dung (bỏ số trang ở lề trên để câu vắt trang không bị chen số); Times New Roman trả gạch mềm cho "-".
    body = fitz.Rect(0, 20 * 72 / 25.4 - 6, doc[0].rect.width, doc[0].rect.height)
    return _plain("".join(page.get_text(clip=body) for page in doc).replace("\xad", "-"))


def _autofill(**kw) -> tuple[bytes, dict]:
    args = dict(log_id="HS-C12345", username="hcc_mau", name="Phường Mẫu tỉnh Mẫu", place="Phường Mẫu",
                procedure_label="Đăng ký khai sinh", version="v1.1", statements=list(NOTICE["statements"]),
                optimize=False, client_time="09:42:30 26/10/2026", created_at=AT,
                principal_cccd=None, principal_name="NGUYỄN VĂN MẪU")
    args.update(kw)
    return consent_pdf.build_consent_pdf(**args)


def test_auto_fill_chep_nguyen_van_the_xac_nhan_va_dieu_4():
    pdf, evidence = _autofill()
    text = _text(pdf)
    notice = texts.autofill_notice("v1.1", "Đăng ký khai sinh")
    for part in (notice["intro"], notice["scope"], notice["purpose"], *notice["documents"], *notice["statements"],
                 notice["optional_statement"]):
        assert _plain(part) in text, part[:40]
    assert "“Đăng ký khai sinh”" in text, "tên thủ tục trong lời mở như popup dựng"
    for clause, points in texts.LEGAL_ARTICLE_4:
        assert _plain(clause) in text
        for point in points:
            assert _plain(point) in text
    assert "Không đồng ý" in text, "mục tùy chọn không tick phải ghi rõ"
    assert evidence["notice"]["intro"] == notice["intro"]


def test_the_thuc_nghi_dinh_30():
    pdf, _ = _autofill()
    doc = fitz.open("pdf", pdf)
    first = re.sub(r"\s+", " ", doc[0].get_text().replace("\xad", "-"))
    for part in ("TRỢ LÝ NHÂN DÂN", "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", "Độc lập - Tự do - Hạnh phúc",
                 "Số: HS-C12345", "Phường Mẫu, ngày 26 tháng 10 năm 2026", "BIÊN BẢN",
                 "Ghi nhận chấp thuận xử lý dữ liệu cá nhân"):
        assert part in first, part
    assert doc[0].rect == fitz.paper_rect("a4")
    assert len(doc) >= 2, "đủ nội dung + toàn văn Điều 4 không gói trong một trang"
    # Số trang canh giữa lề trên, không hiện ở trang 1.
    top = fitz.Rect(0, 0, doc[0].rect.width, 20 * 72 / 25.4)
    assert not re.search(r"\d", doc[0].get_text(clip=top))
    assert doc[1].get_text(clip=top).strip() == "2"
    # Lề trái 30 mm: không chữ nào lấn vào lề.
    assert min(b[0] for p in doc for b in p.get_text("blocks")) >= 30 * 72 / 25.4 - 1


@pytest.mark.skipif(not consent_pdf._find_fonts(), reason="máy không có Times New Roman")
def test_nhung_times_new_roman():
    pdf, _ = _autofill()
    fonts = {f[3] for page in fitz.open("pdf", pdf) for f in page.get_fonts()}
    assert {"Times New Roman Regular", "Times New Roman Bold"} <= fonts


def test_gio_viet_nam_va_ma_bam():
    pdf, evidence = _autofill()
    text = _text(pdf)
    assert "Hồi 09 giờ 42 phút, ngày 26 tháng 10 năm 2026" in text
    assert "09:42:31 ngày 26/10/2026 (giờ Việt Nam)" in text
    assert evidence["content_sha256"] in text.replace(" ", "")
    assert evidence["pdf_sha256"] == hashlib.sha256(pdf).hexdigest()
    meta = fitz.open("pdf", pdf).metadata
    assert meta["subject"] == "HS-C12345" and evidence["content_sha256"] in meta["keywords"]


def test_phien_ban_khong_co_ban_luu_thi_ghi_ro():
    pdf, evidence = _autofill(version="v9.9", statements=["Câu đã xác nhận."])
    text = _text(pdf)
    assert "không có bản lưu nguyên văn nội dung xác nhận phiên bản v9.9" in text
    assert "“Câu đã xác nhận.” — Đã đánh dấu" in text
    assert evidence["notice"] is None


def test_dieu_4_trung_nguyen_van_the_handfree():
    legal = _plain(re.sub(r"^\s*-\s*", "", vi.CONSENT_LEGAL_MD, flags=re.M).replace("*", ""))
    for clause, points in texts.LEGAL_ARTICLE_4:
        assert _plain(clause) in legal
        for point in points:
            assert _plain(point) in legal


CONV = {"_id": "conv-1", "procedure_key": "khai-sinh",
        "location": {"province": "Tỉnh Mẫu", "ward": "Phường Mẫu"}, "auth_user": {"username": "hccmau"}}


def test_handfree_chep_nguyen_van_the_dien():
    proc = {"label": "Đăng ký khai sinh", "requiredDocs": [{"name": "Giấy chứng sinh"}]}
    entry = hf_consent.build_entry(CONV, proc, accepted=True, checks=[True, True], prechecked=True)
    pdf, _ = build_handfree_pdf(entry)
    text = _text(pdf)
    card = vi.CONSENT_CARD_TEXT
    for part in (card["intro_md"], card["scope_md"], card["purpose_md"], *card["checks"], "Giấy chứng sinh"):
        assert _plain(part) in text, part[:40]
    assert "đánh dấu sẵn" in text
    assert "Bấm nút “Đồng ý và tự động điền”" in text


def test_handfree_thu_tuc_dinh_kem_ghi_dung_cau_cam_ket_va_tieng_mong():
    proc = {"label": "Chứng thực bản sao", "mode": "attach", "requiredDocs": [{"name": "Giấy tờ cần chứng thực"}]}
    entry = hf_consent.build_entry(dict(CONV, lang="hmong"), proc, accepted=True, method="verbal", checks=[True, True])
    assert entry["statements"] == vi.CONSENT_ATTACH_CARD_TEXT["checks"]
    pdf, _ = build_handfree_pdf(entry)
    text = _text(pdf)
    assert _plain(vi.CONSENT_ATTACH_CARD_TEXT["purpose_md"]) in text
    assert "tiếng Mông" in text and "Nói hoặc gõ đồng ý" in text


async def test_auto_fill_luu_nguyen_van_va_ma_bam(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    db = MagicMock()
    db.consent_logs.insert_one = AsyncMock(return_value=MagicMock(inserted_id="x"))
    with patch.object(store, "get_db", return_value=db):
        await store.save_consent(log_id="HS-C12345", user={"id": "u1", "username": "hcc_mau", "xa": "Phường Mẫu"},
                                 procedure="khai-sinh", procedure_label="Đăng ký khai sinh", version="v1.1",
                                 statements=list(NOTICE["statements"]), optimize=True, at="09:42 26/10/2026")
    doc = db.consent_logs.insert_one.call_args.args[0]
    saved = (tmp_path / doc["pdf_path"]).read_bytes()
    assert doc["pdf_sha256"] == hashlib.sha256(saved).hexdigest()
    assert doc["notice"]["statements"] == NOTICE["statements"] and doc["content_sha256"]
    assert "Phường Mẫu, ngày" in _text(saved)


async def test_handfree_persist_luu_ma_bam(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    entry = hf_consent.build_entry(CONV, {"label": "Đăng ký khai sinh"}, accepted=True, checks=[True, True])
    db = MagicMock()
    db.consent_logs.insert_one = AsyncMock()
    with patch.object(hf_consent, "get_db", return_value=db):
        await hf_consent.persist(entry)
    doc = db.consent_logs.insert_one.call_args.args[0]
    saved = (tmp_path / doc["pdf_path"]).read_bytes()
    assert doc["pdf_sha256"] == hashlib.sha256(saved).hexdigest() and doc["content_sha256"]
    assert doc["notice"]["purpose_md"] == vi.CONSENT_CARD_TEXT["purpose_md"]
