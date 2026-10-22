"""Khóa phần chi tiết của object địa chỉ: model thấy "chiTietDuoiXa", code/extension vẫn nhận "diaChi"."""

import asyncio
import io
import json
import pathlib
import tokenize

from app.services.llm import client

_ROOT = pathlib.Path(__file__).resolve().parents[2] / "app"


def test_gui_doi_ten_cho_model_nhan_ve_doi_lai():
    sent = client.to_model_keys([
        {"role": "system", "content": 'object {quocGia,tinh,xa,diaChi}; "diaChi":"Thôn A"'},
        {"role": "user", "content": [{"type": "text", "text": "diaChi"}, {"type": "image_url", "image_url": {}}]},
    ])
    assert sent[0]["content"] == 'object {quocGia,tinh,xa,chiTietDuoiXa}; "chiTietDuoiXa":"Thôn A"'
    assert sent[1]["content"][0]["text"] == "chiTietDuoiXa"
    assert client.from_model_keys('{"X":{"tinh":"T","chiTietDuoiXa":"Tổ 1"}}') == '{"X":{"tinh":"T","diaChi":"Tổ 1"}}'


def test_khong_doi_field_key_cong():
    text = "data[diaChi] CongDan_diaChi ChuHoSo_diaChiChuHoSo Don_DiaChiCoSo diaChiThuongTru"
    assert client.to_model_text(text) == text


def test_chat_doi_ten_hai_chieu(monkeypatch):
    seen = {}

    async def fake_primary(messages, *_a, **_k):
        seen["system"] = messages[0]["content"]
        return '{"fields":{"NoiCuTru":{"tinh":"T","xa":"X","chiTietDuoiXa":"Thôn 1"}}}'

    monkeypatch.setattr(client, "_chat_primary", fake_primary)
    raw = asyncio.run(client.chat([{"role": "system", "content": "{tinh,xa,diaChi}"}]))
    assert seen["system"] == "{tinh,xa,chiTietDuoiXa}"
    assert json.loads(raw)["fields"]["NoiCuTru"]["diaChi"] == "Thôn 1"


def _prompt_strings(path: pathlib.Path):
    """Chuỗi văn bản (không phải docstring, không phải khóa code đứng riêng) của một file prompt/schema."""
    toks = [t for t in tokenize.generate_tokens(io.StringIO(path.read_text(encoding="utf-8")).readline)
            if t.type not in (tokenize.NL, tokenize.COMMENT)]
    kinds = {tokenize.STRING, getattr(tokenize, "FSTRING_MIDDLE", tokenize.STRING)}
    for i, tok in enumerate(toks):
        if tok.type not in kinds:
            continue
        prev = toks[i - 1].type if i else tokenize.NEWLINE
        nxt = toks[i + 1].type if i + 1 < len(toks) else tokenize.NEWLINE
        if tok.type == tokenize.STRING and prev in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT,
                                                    tokenize.ENCODING) and nxt == tokenize.NEWLINE:
            continue
        if tok.string.strip("'\"") == "diaChi":
            continue
        yield tok


def test_prompt_va_schema_khong_con_ten_cu():
    stale = []
    for name in ("prompt.py", "schema.py", "base_prompt.py"):
        for path in _ROOT.rglob(name):
            for tok in _prompt_strings(path):
                if client._ADDRESS_DETAIL_OLD_RE.search(tok.string):
                    stale.append(f"{path.relative_to(_ROOT.parent)}:{tok.start[0]}")
    assert not stale, "Prompt/desc còn khóa cũ, đổi sang chiTietDuoiXa: " + ", ".join(stale[:20])


def test_khai_sinh_lien_thong_bo_chi_tiet_trung_tinh():
    from app.pipelines.khai_sinh_lien_thong.process.mapper import _area

    for detail in ("T.P Hải Phòng", "Thành phố Hải Phòng", "TP. Hải Phòng", "Hải Phòng"):
        assert not _area({"tinh": "Hải Phòng", "xa": "", "diaChi": detail}).get("diaChi"), detail
    assert _area({"tinh": "Hải Phòng", "xa": "", "diaChi": "Tổ 3"})["diaChi"] == "Tổ 3"
    assert _area({"tinh": "Hải Phòng", "xa": "", "diaChi": "Số 5 đường Hải Phòng"})["diaChi"] == "Số 5 đường Hải Phòng"
