# -*- coding: utf-8 -*-
"""Gọi model Qwen trên máy chủ chuẩn OpenAI (vLLM, SGLang...) qua /v1/chat/completions, nhận chữ trả về dần (stream).

- Tắt chế độ suy nghĩ (chat_template_kwargs.enable_thinking = false); phần <think> nếu có vẫn được lọc bỏ.
- stream_options.continuous_usage_stats: vLLM báo số token ở mọi đoạn, nên dừng giữa chừng vẫn biết đã tốn bao nhiêu.
- Chặn lặp vô hạn: detect_loop theo dõi chữ đang nhận; khi model kẹt lặp (một dòng / khối lặp liền nhau từ 8 lần, một
  dòng dài trên 2.000 ký tự, một cụm lặp trên 60 lần, hoặc lặp theo chu kỳ) thì đóng kết nối để máy chủ thôi sinh chữ,
  stop_reason = "loop". trim_loop bỏ phần lặp khỏi kết quả; clean_output gỡ khối ```markdown và lời dẫn thừa.

Trích nguyên văn từ ocr_engine.py của web.
"""
from __future__ import annotations

import base64
import io
import json as _json
import re
import urllib.error
import urllib.request

from PIL import Image

from .chuan_bi_anh import to_openai_content


class ServerError(Exception):
    def __init__(self, message: str, status: int | None = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


def friendly_server_error(e: Exception, base_url: str = "") -> str:
    msg = str(e)
    low = (msg + " " + getattr(e, "body", "")).lower()
    status = getattr(e, "status", None)
    if status is None and "không kết nối được" in msg:
        return (f"Không kết nối được máy chủ {base_url}. Kiểm tra máy chủ đang chạy, địa chỉ và cổng đúng, "
                "và máy này đã vào cùng mạng với máy chủ (VPN/Tailscale nếu dùng địa chỉ 100.x.x.x).")
    if "image" in low and ("at most" in low or "limit_mm" in low or "limit-mm" in low or "exceeds the limit" in low):
        return ("Máy chủ giới hạn số ảnh trong một lần gửi. Vào Cài đặt giảm \"Số ảnh tối đa mỗi lần gửi\" "
                "(đặt 1 nếu máy chủ chỉ nhận 1 ảnh), hoặc khởi động vLLM với --limit-mm-per-prompt '{\"image\": 10}'. "
                f"Chi tiết: {msg[:300]}")
    if ("image" in low or "multimodal" in low or "vision" in low) and any(
            k in low for k in ("not support", "does not support", "unsupported", "text-only", "not a multimodal", "no image")):
        return ("Model đang chạy trên máy chủ không đọc được ảnh (không phải model vision). "
                "Cần chạy một model có thị giác, ví dụ dòng Qwen-VL. "
                f"Chi tiết: {msg[:300]}")
    if "context length" in low or "maximum context" in low or "too long" in low or "max_model_len" in low:
        return ("Yêu cầu vượt độ dài ngữ cảnh của model. Giảm \"Độ dài tối đa\", giảm \"Kích thước mỗi ảnh\" "
                f"hoặc chọn lưới phóng to nhỏ hơn. Chi tiết: {msg[:300]}")
    if status in (401, 403):
        return "Máy chủ yêu cầu khóa truy cập (API key) hoặc khóa không đúng. Nhập khóa trong Cài đặt."
    if status == 404:
        return ("Không tìm thấy đường dẫn hoặc model trên máy chủ. Địa chỉ gốc thường kết thúc bằng /v1, "
                f"ví dụ http://<may-chu>:<cong>/v1. Chi tiết: {msg[:300]}")
    return f"Máy chủ báo lỗi{f' ({status})' if status else ''}: {msg[:500]}"


def _endpoint(base_url: str, path: str) -> str:
    return base_url.strip().rstrip("/") + path


def _open(url: str, payload: dict | None = None, api_key: str = "", timeout: float = 900):
    data = _json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        msg = body
        try:
            j = _json.loads(body)
            err = j.get("error")
            if isinstance(err, dict):
                msg = err.get("message") or body
            else:
                msg = j.get("message") or j.get("detail") or err or body
        except Exception:
            pass
        raise ServerError(str(msg)[:1000], e.code, body) from None
    except urllib.error.URLError as e:
        raise ServerError(f"không kết nối được tới {url} ({e.reason})") from None
    except (TimeoutError, OSError) as e:
        raise ServerError(f"không kết nối được tới {url} ({e})") from None


class _ThinkStripper:
    """Bỏ khối <think>...</think> ở đầu câu trả lời (model Qwen đôi khi vẫn trả về)."""

    def __init__(self):
        self.buf, self.mode = "", "start"

    def feed(self, s: str) -> str:
        if self.mode == "pass":
            return s
        self.buf += s
        if self.mode == "start":
            head = self.buf.lstrip()
            if not head:
                return ""
            if head.startswith("<think>"):
                self.mode = "think"
            elif "<think>".startswith(head):
                return ""
            else:
                out, self.buf, self.mode = self.buf, "", "pass"
                return out
        i = self.buf.find("</think>")
        if i < 0:
            return ""
        out = self.buf[i + len("</think>"):].lstrip("\n")
        self.buf, self.mode = "", "pass"
        return out

    def flush(self) -> str:
        out = self.buf if self.mode == "start" else ""
        self.buf = ""
        return out


def clean_output(text: str) -> str:
    """Gỡ khối <think> sót lại và lớp ```markdown bọc ngoài toàn bộ kết quả."""
    import re as _re
    t = _re.sub(r"^\s*<think>.*?</think>\s*", "", text or "", flags=_re.S).strip()
    m = _re.match(r"^```(?:markdown|md)?\s*\n(.*)\n```\s*$", t, flags=_re.S | _re.I)
    if m:
        return m.group(1).strip()
    # khung mở ở dòng đầu mà không có dòng đóng (lượt đọc bị dừng, chạm giới hạn) hoặc dòng đóng nằm giữa chừng
    lines = t.split("\n")
    if lines and _re.fullmatch(r"```(?:markdown|md)?\s*", lines[0].strip(), flags=_re.I):
        close = next((j for j in range(1, len(lines)) if lines[j].strip() == "```"), None)
        if close is not None:
            del lines[close]
        del lines[0]
        t = "\n".join(lines).strip()
    return t


# ---------------------------------------------------------------- chặn lặp vô hạn
# Model hay "kẹt" khi gặp bảng Markdown: chép mãi hàng trống "| | |", dòng kẻ "|---|---|…" dài vô tận, hoặc lặp lại
# hàng tiêu đề bảng. Đo trên bộ test 99 tệp: 7 tệp như vậy chiếm 62% token đầu ra của chế độ tách 4 phần.
LOOP_REPEAT = 8            # một dòng (hoặc một khối tối đa 4 dòng) lặp liền nhau từng này dòng thì coi là kẹt


LOOP_LONG_LINE = 2000      # một dòng dài bất thường (nội dung thật dài nhất đo được trên bộ test: ~1.050 ký tự)


_LOOP_FRAGMENT = re.compile(r"(.{1,40}?)\1{60,}", re.S)


_FILLER = set(".…_- \t")   # dòng chấm, gạch để điền: không tính là lặp


LOOP_PERIODIC = 6          # một dòng dài cứ vài dòng lại quay lại (lặp theo chu kỳ, có biến đổi) từng này lần…


LOOP_WINDOW = 80           # …trong từng này dòng gần nhất


def _periodic_key(line: str) -> str:
    k = line.strip()
    return k if len(k) >= 12 and not set(k) <= set("|-: ") and not set(k) <= _FILLER else ""


def _periodic_start(keys: list[str], lines: list[str] | None = None) -> int | None:
    """Chỉ số dòng nơi bắt đầu lặp theo chu kỳ (lần xuất hiện thứ hai của dòng quay lại), None nếu không có.
    Chỉ tính là kẹt khi ba vòng gần nhất giống nhau từ 60% trở lên: nội dung thật có lặp (cùng một tờ khai qua nhiều trang,
    danh sách người) thì giữa các lần lặp vẫn có chữ khác."""
    body = [x.strip() for x in (lines if lines is not None else keys)]
    pos: dict[str, list[int]] = {}
    for i, k in enumerate(keys):
        if not k:
            continue
        p = pos.setdefault(k, [])
        p.append(i)
        recent = [j for j in p if j > i - LOOP_WINDOW]
        if len(recent) >= LOOP_PERIODIC:
            cycles = [set(body[a:b]) - {""} for a, b in zip(recent[-4:], recent[-3:])]
            if all(len(x & y) >= 0.6 * max(len(x), len(y), 1) for x, y in zip(cycles, cycles[1:])):
                return recent[1]
    return None


def _fragment_loop(s: str):
    for m in _LOOP_FRAGMENT.finditer(s):
        if not set(m.group(1)) <= _FILLER:
            return m
    return None


def _repeat_block(lines: list[str]) -> int:
    """Số dòng ở cuối danh sách đang là một khối 1–4 dòng lặp liền nhau (0 nếu không lặp đủ nhiều)."""
    for b in range(1, 5):
        block = lines[-b:]
        if len(lines) < b * 2 or not any(x.strip() for x in block):
            continue
        n, i = 1, len(lines) - 2 * b
        while i >= 0 and lines[i:i + b] == block:
            n += 1
            i -= b
        if n * b >= LOOP_REPEAT and n >= 3:
            return n * b
    return 0


def detect_loop(text: str) -> bool:
    """Kiểm tra phần cuối chữ model đang trả có dấu hiệu lặp vô hạn không (gọi liên tục khi nhận chữ)."""
    tail = text[-6000:]
    lines = tail.split("\n")
    if len(lines[-1]) > LOOP_LONG_LINE:
        return True
    done = [l.strip() for l in lines[:-1]]
    if done and _repeat_block(done):
        return True
    if _periodic_start([_periodic_key(l) for l in done[-LOOP_WINDOW:]], done[-LOOP_WINDOW:]) is not None:
        return True
    return bool(_fragment_loop(tail[-2500:]))


def trim_loop(text: str) -> str:
    """Bỏ phần lặp: khối dòng lặp liền nhau từ LOOP_REPEAT dòng trở lên chỉ giữ một lần, cụm ký tự lặp dài trong
    một dòng chỉ giữ ba lần, bỏ dòng cuối dở dang nếu lượt đọc bị dừng giữa dòng lặp. Đoạn lặp ngắn không bị đụng."""
    lines = []
    for line in text.split("\n"):
        m = _fragment_loop(line) if len(line) > 200 else None
        while m:
            line = line[:m.start()] + m.group(1) * 3 + line[m.end():]
            m = _fragment_loop(line)
        if len(line) > LOOP_LONG_LINE:          # dòng dài bất thường mà không lặp y hệt: model bịa, không giữ
            n = f"{len(line):,}".replace(",", ".")      # dấu chấm ngăn hàng nghìn, giữ dấu phẩy trong câu
            line = f"[Bỏ một dòng model đọc lặp hoặc bịa, dài {n} ký tự]"
        lines.append(line)
    key = [x.strip() for x in lines]
    out, i = [], 0
    while i < len(lines):
        best = None                                   # (cỡ khối, số dòng của cả đoạn lặp)
        for b in range(1, 5):
            block = key[i:i + b]
            if len(block) < b or not any(block):
                continue
            n = 1
            while key[i + n * b:i + (n + 1) * b] == block:
                n += 1
            if n * b >= LOOP_REPEAT and n >= 3 and (best is None or n * b > best[1]):
                best = (b, n * b)
        if best:
            out.extend(lines[i:i + best[0]])
            i += best[1]
        else:
            out.append(lines[i])
            i += 1
    # lặp theo chu kỳ: giữ đến hết một vòng, bỏ phần sau (sau khi model kẹt, phần còn lại không còn là nội dung giấy)
    start = _periodic_start([_periodic_key(l) for l in out], out)
    if start is not None:
        out = out[:start]
        while out and not out[-1].strip():
            out.pop()
    # lượt đọc bị dừng giữa dòng lặp: dòng cuối là mẩu dở của dòng trước
    if len(out) >= 2 and out[-1].strip() and out[-2].strip().startswith(out[-1].strip()) and len(out[-1]) < len(out[-2]):
        out.pop()
    return "\n".join(out)


def stream_openai(base_url: str, api_key: str, model: str, system: str, content: list,
                  temperature: float, max_tokens: int, disable_thinking: bool, repetition_penalty: float,
                  stop_check=None):
    """stop_check(chữ_đã_nhận) -> True thì dừng ngay (đóng kết nối để máy chủ thôi sinh chữ), stop_reason = "loop"."""
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": to_openai_content(content)}],
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
        "stream": True,
        # continuous_usage_stats: vLLM báo số token ở mọi đoạn, nên dừng giữa chừng vẫn biết đã tốn bao nhiêu
        "stream_options": {"include_usage": True, "continuous_usage_stats": True},
    }
    if disable_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    if repetition_penalty and abs(float(repetition_penalty) - 1.0) > 1e-6:
        payload["repetition_penalty"] = float(repetition_penalty)

    try:
        resp = _open(_endpoint(base_url, "/chat/completions"), payload, api_key)
    except ServerError as e:
        if e.status != 400 or "stream_options" not in (e.body or str(e)):
            raise
        payload["stream_options"] = {"include_usage": True}      # máy chủ không nhận tùy chọn này
        resp = _open(_endpoint(base_url, "/chat/completions"), payload, api_key)
    usage, finish, started, thinking = {}, None, False, False
    acc, chunks = "", 0
    strip = _ThinkStripper()
    with resp:
        if "text/event-stream" not in (resp.headers.get("Content-Type") or ""):
            j = _json.loads(resp.read().decode("utf-8", "replace"))
            ch = (j.get("choices") or [{}])[0]
            text = strip.feed((ch.get("message") or {}).get("content") or "") + strip.flush()
            if text:
                yield {"type": "text", "text": text}
            usage, finish = j.get("usage") or {}, ch.get("finish_reason")
        else:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    j = _json.loads(data)
                except ValueError:
                    continue
                if j.get("error"):
                    err = j["error"]
                    raise ServerError(err.get("message", str(err)) if isinstance(err, dict) else str(err))
                if j.get("usage"):
                    usage = j["usage"]
                for ch in j.get("choices") or []:
                    d = ch.get("delta") or {}
                    if (d.get("reasoning_content") or d.get("reasoning")) and not thinking and not started:
                        thinking = True
                        yield {"type": "status", "text": "Model đang suy nghĩ…"}
                    piece = d.get("content")
                    if piece:
                        chunks += 1
                        out = strip.feed(piece)
                        if out:
                            if not started:
                                started = True
                                yield {"type": "status", "text": "Model đang chép nội dung…"}
                            yield {"type": "text", "text": out}
                            acc += out
                    if ch.get("finish_reason"):
                        finish = ch["finish_reason"]
                if stop_check and finish is None and stop_check(acc):
                    finish = "loop"       # ra khỏi vòng đọc: kết nối đóng lại, máy chủ thôi sinh chữ
                    break
            tail = strip.flush()
            if tail:
                yield {"type": "text", "text": tail}
    yield {
        "type": "usage",
        "input_tokens": int(usage.get("prompt_tokens") or 0),
        # máy chủ không báo số token liên tục thì mỗi đoạn nhận được tính là một token
        "output_tokens": int(usage.get("completion_tokens") or (chunks if finish == "loop" else 0)),
        "stop_reason": "max_tokens" if finish == "length" else finish,
    }


def openai_check(base_url: str, api_key: str, model: str, disable_thinking: bool) -> tuple[bool, str, list]:
    """Kiểm tra: (1) máy chủ trả lời, có model đã chọn; (2) model có nhận ảnh không."""
    try:
        with _open(_endpoint(base_url, "/models"), None, api_key, timeout=20) as r:
            ids = [m.get("id") for m in (_json.loads(r.read().decode("utf-8", "replace")).get("data") or []) if m.get("id")]
    except ServerError as e:
        return False, friendly_server_error(e, base_url), []
    except ValueError:
        ids = []
    parts = []
    if ids and model not in ids:
        return False, f"Máy chủ đang chạy nhưng không có model \"{model}\". Các model hiện có: {', '.join(ids)}.", ids
    parts.append(f"Kết nối tốt, máy chủ có model \"{model}\"." if ids else "Kết nối tốt.")

    # ảnh thử: một ô vuông đỏ
    buf = io.BytesIO()
    Image.new("RGB", (96, 96), (220, 20, 30)).save(buf, format="PNG")
    content = [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                            "data": base64.b64encode(buf.getvalue()).decode()}},
               {"type": "text", "text": "Ảnh này màu gì? Trả lời đúng một từ tiếng Việt."}]
    payload = {"model": model, "messages": [{"role": "user", "content": to_openai_content(content)}],
               "temperature": 0, "max_tokens": 16, "stream": False}
    if disable_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    try:
        with _open(_endpoint(base_url, "/chat/completions"), payload, api_key, timeout=120) as r:
            j = _json.loads(r.read().decode("utf-8", "replace"))
        answer = clean_output(((j.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
        parts.append(f"Model nhận được ảnh (thử hỏi màu của một ô đỏ, model trả lời: \"{answer[:40]}\").")
        return True, " ".join(parts), ids
    except ServerError as e:
        parts.append("Nhưng gửi ảnh thì lỗi: " + friendly_server_error(e, base_url))
        return False, " ".join(parts), ids
