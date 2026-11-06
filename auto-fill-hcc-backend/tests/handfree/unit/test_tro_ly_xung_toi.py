"""Trợ lý tự xưng "tôi" ngay trong câu thoại gốc — không còn bước đổi "em" → "tôi" ở đầu ra."""
import io
import pathlib
import re
import tokenize

ROOT = pathlib.Path(__file__).resolve().parents[3]
FILES = [
    "app/channels/handfree/chat/script_vi.py",
    "app/channels/handfree/chat/flow.py",
    "app/channels/handfree/chat/tu_phap_moi.py",
    "app/channels/handfree/procedure_registry.py",
    "app/channels/handfree/documents/mobile_page.py",
    "app/channels/handfree/voice/ws_asr.py",
    "app/upload_session/mobile_page.py",
]
# "em" là đại từ của trợ lý; giữ "trẻ em", "anh/chị em", "em ruột/gái/…" (quan hệ trên tờ khai), "Em" là tên người.
_NOT_FAMILY_BEFORE = r"(?<!trẻ )(?<!Trẻ )(?<!anh )(?<!Anh )(?<!chị )(?<!Chị )(?<!/)"
_RELATION_AFTER = r"(?!\s+(?:ruột|gái|trai|bé|họ|dâu|rể|út|nhỏ|vợ|chồng|kết nghĩa)(?!\w))"
_PRONOUN = re.compile(_NOT_FAMILY_BEFORE + r"(?:(?<!\w)em|(?<!\w )(?<!\w)Em)(?!\w)" + _RELATION_AFTER)


def _string_literals(path: pathlib.Path):
    src = path.read_text(encoding="utf-8")
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        # Python 3.11 (CI, image prod): f-string là một token STRING; từ 3.12 tách ra FSTRING_MIDDLE.
        if tok.type in (tokenize.STRING, getattr(tokenize, "FSTRING_MIDDLE", tokenize.STRING)):
            yield tok.start[0], tok.string


def test_cau_thoai_khong_con_tro_ly_xung_em():
    left = [f"{name}:{line}: {text.strip()[:80]}"
            for name in FILES for line, text in _string_literals(ROOT / name) if _PRONOUN.search(text)]
    assert not left, left[:5]


def test_khong_con_buoc_doi_xung_ho_o_dau_ra():
    for name in ("app/channels/handfree/chat/router.py", "app/channels/handfree/voice/router.py"):
        assert "xung_ho" not in (ROOT / name).read_text(encoding="utf-8")
