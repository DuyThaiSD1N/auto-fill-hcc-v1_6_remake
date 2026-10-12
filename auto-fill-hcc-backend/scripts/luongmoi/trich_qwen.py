"""Qwen đọc ẢNH và trích thông tin chính (thay cho OCR toàn văn), kèm độ chắc từng giá trị (logprobs).

Hai cách để so:
- ``trich_ho_so``: mỗi TRANG một lượt, chép nguyên văn các ô chính theo loại giấy (PROMPT_TRICH), các trang
  chạy song song. Kết quả theo giấy/khối có nhãn in sẵn — không tự suy vai người.
- ``trich_nguyen_con``: một lượt cho cả hồ sơ, dùng NGUYÊN prompt trích xuất TTHN (cùng schema với v1) nhưng
  đưa ảnh thay text OCR.

Độ chắc của một giá trị = xác suất thấp nhất trong các token tạo nên giá trị đó; kèm các chữ yếu (p < 0.9) và
phương án thứ hai của máy.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import math
import re
import time

import httpx

from app.config import settings
from app.services import ocr_qwen

PROMPT_TRICH = """Bạn là máy đọc giấy tờ hộ tịch. Ảnh là MỘT trang trong hồ sơ "Xác nhận tình trạng hôn nhân". Nhận ra trên trang có những giấy gì và CHÉP các thông tin chính của từng giấy ra JSON.

CÁCH CHÉP
- Chép NGUYÊN VĂN như trên giấy: đúng từng chữ cái, dấu thanh, chữ số, chữ hoa/thường. KHÔNG sửa chính tả, KHÔNG đổi
  sang tên quen thuộc hơn, KHÔNG chuẩn hoá ngày (giấy ghi "4/7/1979" thì chép "4/7/1979"), KHÔNG đổi địa danh cũ sang
  mới, KHÔNG viết tắt hay viết đầy đủ khác giấy.
- Mỗi giá trị lấy ĐÚNG dòng có nhãn đó trên trang này. Không suy ra, không lấy từ giấy khác, không dùng dòng mã máy
  đọc (MRZ) để sửa chữ ở mặt trước thẻ.
- Dòng để trống hoặc không có trên trang thì BỎ key đó. Chữ bị gạch rồi viết lại thì chép chữ viết lại.
- Chữ viết tay khó đọc vẫn chép theo cách đọc đúng nhất, không bỏ.

CÁC LOẠI GIẤY ("loai") VÀ KEY CẦN CHÉP
- "to_khai": Tờ khai cấp Giấy xác nhận tình trạng hôn nhân (kể cả trang tiếp theo của tờ khai).
  "nguoi_yeu_cau": {"ho_ten","ngay_sinh","so_giay_to","ngay_cap","noi_cap","noi_cu_tru","quan_he"} — khối người
  yêu cầu ở đầu tờ khai ("quan_he" = quan hệ với người được cấp giấy).
  "nguoi_duoc_cap": {"ho_ten","ngay_sinh","gioi_tinh","dan_toc","quoc_tich","so_giay_to","ngay_cap","noi_cap",
  "noi_cu_tru"} — khối người được cấp / đề nghị xác nhận tình trạng hôn nhân.
  "thoi_gian_cu_tru": dòng khoảng thời gian cư trú đề nghị xác nhận (nguyên văn).
  "tinh_trang_hon_nhan": dòng tình trạng hôn nhân (nguyên văn, cả phần số giấy chứng tử / bản án ghi kèm).
  "muc_dich": dòng mục đích sử dụng (nguyên văn, đủ mọi dòng nối tiếp).
- "the_mat_truoc": mặt trước CCCD / Căn cước / CMND: {"so","ho_ten","ngay_sinh","gioi_tinh","quoc_tich","que_quan",
  "noi_cu_tru"} ("noi_cu_tru" = dòng "Nơi thường trú" hoặc "Nơi cư trú").
- "the_mat_sau": mặt sau thẻ: {"ngay_cap","noi_cap","mrz":["dòng 1","dòng 2","dòng 3"]} ("mrz" = 3 dòng chữ máy
  đọc bắt đầu bằng IDVNM, chép đủ từng ký tự kể cả "<").
- "khai_tu": giấy chứng tử / trích lục khai tử / giấy báo tử: {"so" (số ở nhãn "Số:" đầu trang),"ngay_cap",
  "co_quan_cap","ho_ten_nguoi_chet","ngay_chet","dang_ky_goc":{"so","ngay","noi"}} ("dang_ky_goc" = dòng "Đã
  được đăng ký khai tử tại ... số ... ngày ...").
- "ly_hon": bản án / quyết định ly hôn / công nhận thuận tình ly hôn: {"so","ngay","co_quan","ten_hai_ben":[...]}.
- "ket_hon": giấy chứng nhận / trích lục kết hôn: {"so","quyen_so","ngay_dang_ky","co_quan",
  "chong":{"ho_ten","ngay_sinh","so_giay_to"},"vo":{"ho_ten","ngay_sinh","so_giay_to"}}.
- "xntthn_cu": giấy xác nhận tình trạng hôn nhân đã cấp: {"so","ngay_cap","co_quan","ho_ten","ngay_sinh",
  "so_giay_to","tinh_trang_hon_nhan","muc_dich"} ("muc_dich" = dòng "Giấy này được sử dụng để").
- "uy_quyen": giấy ủy quyền: {"ben_uy_quyen":{"ho_ten","ngay_sinh","so_giay_to","ngay_cap","noi_cap","dia_chi"},
  "ben_duoc_uy_quyen":{cùng các key},"noi_dung"}.
- "cu_tru": giấy xác nhận thông tin cư trú / kết quả tra cứu thông tin công dân: {"ho_ten","ngay_sinh",
  "so_dinh_danh","gioi_tinh","dan_toc","quoc_tich","noi_thuong_tru","noi_o_hien_tai"}.
- "khac": giấy khác: {"tieu_de"}.

Một trang có nhiều giấy (cả hai mặt thẻ, thẻ của hai người...) thì mỗi giấy một phần tử, theo thứ tự trên trang.
Trả DUY NHẤT một JSON, không giải thích:
{"giay":[{"loai":"...", ...}]}"""

_PAGE_MAX_TOKENS = 900
_WEAK_P = 0.9
_PAGE_CONCURRENCY = 4
_TRICH_CACHE = "qwen_trich_cache.json"
_NGUYEN_CON_CACHE = "qwen_nguyencon_cache.json"


def _sha(file: dict) -> str:
    return hashlib.sha256(file["dataUrl"].encode()).hexdigest()


def _model() -> str:
    return settings.ocr_qwen_model or settings.llm_model


async def _chat_lp(messages: list[dict], max_tokens: int) -> dict:
    """Một lượt gọi máy OCR Qwen có logprobs → {content, finish_reason, usage, ms, logprobs}."""
    base = settings.ocr_qwen_base_url or settings.llm_base_url
    payload = {"model": _model(), "messages": messages, "temperature": 0, "max_tokens": max_tokens,
               "logprobs": True, "top_logprobs": 3, "chat_template_kwargs": {"enable_thinking": False}}
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=httpx.Timeout(240), verify=False) as client:
        resp = await client.post(ocr_qwen._endpoint(base), json=payload)
    ms = int((time.monotonic() - t0) * 1000)
    if resp.status_code >= 400:
        raise RuntimeError(f"Qwen HTTP {resp.status_code}: {resp.text[:300]}")
    choice = resp.json()["choices"][0]
    return {"content": (choice.get("message") or {}).get("content") or "", "finish_reason": choice.get("finish_reason"),
            "usage": resp.json().get("usage") or {}, "ms": ms,
            "logprobs": (choice.get("logprobs") or {}).get("content") or []}


# ------------------------------------------------------------------ JSON + logprobs → giá trị kèm độ chắc

def _json_spans(text: str) -> list[tuple[tuple, str, int, int]]:
    """Mọi giá trị lá trong JSON đầu tiên của ``text`` → (đường dẫn, giá trị, vị trí đầu, vị trí cuối) theo KÝ TỰ.
    json.loads không trả vị trí nên tự duyệt; JSON hỏng → []."""
    out: list[tuple[tuple, str, int, int]] = []

    def ws(i: int) -> int:
        while i < len(text) and text[i] in " \t\r\n":
            i += 1
        return i

    def string(i: int) -> tuple[str, int, int, int]:
        j = i + 1
        while j < len(text) and text[j] != '"':
            j += 2 if text[j] == "\\" else 1
        return json.loads(text[i:j + 1]), i + 1, j, j + 1

    def value(i: int, path: tuple) -> int:
        i = ws(i)
        ch = text[i]
        if ch in "{[":
            close, k = ("}" if ch == "{" else "]"), 0
            i = ws(i + 1)
            if text[i] == close:
                return i + 1
            while True:
                if ch == "{":
                    key, _, _, i = string(ws(i))
                    i = ws(i)
                    i = value(i + 1, path + (key,))
                else:
                    i = value(i, path + (k,))
                    k += 1
                i = ws(i)
                if text[i] == ",":
                    i += 1
                    continue
                return i + 1
        if ch == '"':
            val, start, end, i = string(i)
            out.append((path, val, start, end))
            return i
        m = re.match(r"-?\d+(?:\.\d+)?|true|false|null", text[i:])
        if m.group(0) != "null":
            out.append((path, m.group(0), i, i + m.end()))
        return i + m.end()

    start = text.find("{")
    if start < 0:
        return []
    try:
        value(start, ())
    except (IndexError, ValueError, AttributeError, json.JSONDecodeError):
        return []
    return out


def _confidences(content: str, logprobs: list[dict]):
    """→ hàm (đầu, cuối theo ký tự) → (p thấp nhất, [chữ yếu]) — ánh xạ qua BYTE vì token tiếng Việt hay cắt
    giữa một ký tự nhiều byte."""
    ranges, pos = [], 0
    for tok in logprobs:
        raw = bytes(tok.get("bytes") or tok.get("token", "").encode())
        alts = [a.get("token") for a in tok.get("top_logprobs") or [] if a.get("token") != tok.get("token")]
        ranges.append((pos, pos + len(raw), math.exp(tok["logprob"]), tok.get("token"), alts[:1]))
        pos += len(raw)
    char_byte = [0]
    for ch in content:
        char_byte.append(char_byte[-1] + len(ch.encode()))

    def conf(start: int, end: int) -> tuple[float, list]:
        b0, b1 = char_byte[start], char_byte[end]
        toks = [r for r in ranges if r[0] < b1 and r[1] > b0]
        if not toks:
            return 1.0, []
        weak = [[t, round(p, 2), alt] for _s, _e, p, t, alt in toks if p < _WEAK_P]
        return round(min(p for _s, _e, p, _t, _a in toks), 3), weak

    return conf


def _values(res: dict) -> tuple[dict | None, list[dict]]:
    content = res["content"]
    spans = _json_spans(content)
    if not spans:
        return None, []
    conf = _confidences(content, res["logprobs"])
    values = []
    for path, val, start, end in spans:
        p, weak = conf(start, end)
        values.append({"path": list(path), "value": val, "p": p, "weak": weak})
    try:
        data = json.loads(content[content.find("{"):content.rfind("}") + 1])
    except json.JSONDecodeError:
        data = None
    return data, values


# ------------------------------------------------------------------ cách 1: từng trang, ô chính

def _image_url(image: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(image).decode()


async def _trich_trang(image: bytes, sem: asyncio.Semaphore) -> dict:
    async with sem:
        res = await _chat_lp([{"role": "user", "content": [
            {"type": "text", "text": PROMPT_TRICH},
            {"type": "image_url", "image_url": {"url": _image_url(image)}}]}], _PAGE_MAX_TOKENS)
    data, values = _values(res)
    return {"data": data, "values": values, "raw": res["content"], "ms": res["ms"],
            "out_tokens": res["usage"].get("completion_tokens"), "finish": res["finish_reason"]}


def _prompt_key(prompt: str) -> str:
    return hashlib.sha256(f"{prompt}|{_model()}".encode()).hexdigest()[:16]


def _load_cache(path, key: str) -> dict:
    cache = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return cache if cache.get("_key") == key else {"_key": key}


async def trich_ho_so(case: dict, refresh: bool = False) -> dict:
    """→ {"trang": [{tep, trang, data, values, ms, out_tokens}], "wall_s", "cached"}; cache ở <mã>/qwen_trich_cache.json."""
    path = case["dir"] / _TRICH_CACHE
    cache = {} if refresh else _load_cache(path, _prompt_key(PROMPT_TRICH))
    cache["_key"] = _prompt_key(PROMPT_TRICH)
    keys = [_sha(d) for d in case["docs"]]
    if all(k in cache for k in keys):
        pages = [p for k in keys for p in cache[k]]
        return {"trang": pages, "wall_s": cache.get("_wall_s"), "cached": True}
    sem = asyncio.Semaphore(_PAGE_CONCURRENCY)
    t0 = time.monotonic()

    async def one_file(fi: int, doc: dict) -> list[dict]:
        raw, mime = ocr_qwen._decode(doc)
        images = await asyncio.to_thread(ocr_qwen._page_images, raw, mime)
        rows = await asyncio.gather(*(_trich_trang(img, sem) for img in images))
        return [{"tep": fi, "trang": pi, **row} for pi, row in enumerate(rows)]

    per_file = await asyncio.gather(*(one_file(i, d) for i, d in enumerate(case["docs"])))
    for k, rows in zip(keys, per_file):
        cache[k] = rows
    cache["_wall_s"] = round(time.monotonic() - t0, 1)
    path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return {"trang": [p for rows in per_file for p in rows], "wall_s": cache["_wall_s"], "cached": False}


# ------------------------------------------------------------------ cách 2: nguyên bộ trích xuất, đọc từ ảnh

_ANH_THAY_TEXT = ("\n\nLƯU Ý LẦN NÀY: KHÔNG có text OCR. Mỗi tài liệu được gửi dưới dạng ẢNH từng trang ngay sau "
                  "dòng tiêu đề \"### Tài liệu N\"; đọc trực tiếp từ ảnh và áp dụng mọi quy tắc trên như với text OCR.")


def _system_prompt_tthn() -> str:
    from app.pipelines.xac_nhan_tthn.process import base_prompt
    from app.pipelines.xac_nhan_tthn.process.prompt import EXTRA_RULES
    from app.pipelines.xac_nhan_tthn.process.schema import FIELDS
    return base_prompt.build_system_prompt(FIELDS, EXTRA_RULES) + _ANH_THAY_TEXT


async def trich_nguyen_con(case: dict, refresh: bool = False, max_tokens: int = 2000) -> dict:
    """→ {"data", "values", "ms", "out_tokens", "in_tokens", "finish"}; cache ở <mã>/qwen_nguyencon_cache.json."""
    from app.pipelines.xac_nhan_tthn.process import base_prompt

    system = _system_prompt_tthn()
    key = _prompt_key(system)
    path = case["dir"] / _NGUYEN_CON_CACHE
    cache = {} if refresh else _load_cache(path, key)
    sig = ",".join(_sha(d) for d in case["docs"])
    if cache.get("sig") == sig:
        return {**cache["res"], "cached": True}
    content: list[dict] = []
    account = base_prompt._account_block(case.get("options"))
    if account:
        content.append({"type": "text", "text": account})
    for i, doc in enumerate(case["docs"], 1):
        raw, mime = ocr_qwen._decode(doc)
        images = await asyncio.to_thread(ocr_qwen._page_images, raw, mime)
        content.append({"type": "text", "text": f"### Tài liệu {i} (tên file: {doc['name']}, {len(images)} trang)"})
        content += [{"type": "image_url", "image_url": {"url": _image_url(img)}} for img in images]
    res = await _chat_lp([{"role": "system", "content": system}, {"role": "user", "content": content}], max_tokens)
    data, values = _values(res)
    out = {"data": data, "values": values, "raw": res["content"], "ms": res["ms"], "finish": res["finish_reason"],
           "out_tokens": res["usage"].get("completion_tokens"), "in_tokens": res["usage"].get("prompt_tokens")}
    path.write_text(json.dumps({"_key": key, "sig": sig, "res": out}, ensure_ascii=False), encoding="utf-8")
    return {**out, "cached": False}
