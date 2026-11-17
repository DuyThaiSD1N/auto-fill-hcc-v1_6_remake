"""Ca đã sửa đạt → một ca hồi quy ẩn danh trong auto-test-hcc/regression/cases, phát lại được trong CI (regression/run.py).

Ca gồm: thủ tục, xã/tỉnh + username tài khoản test chạy lại, options, mỗi tệp một đoạn OCR, các câu trả lời LLM theo thứ
tự của MỘT lượt chạy lại đã đạt sau khi sửa, và tiêu chí của trọng tài. Không có ảnh hay PDF gốc.

Dữ liệu thật bị thay trước khi ghi: họ tên, số giấy tờ / điện thoại (≥ 9 chữ số), email, phần số nhà / thôn / đường của
địa chỉ. Giữ ngày tháng và đơn vị hành chính (mapper, remap cần). Sau đó quét lại bằng codeguard: còn chuỗi thật nào thì
không ghi ca. Ca chỉ được ghi khi phát lại ĐẠT trên code đã sửa; trượt trên code production thì ghi là bắt được lỗi cũ.
Tệp ca nằm trong thư mục làm việc, chưa commit: người soát lại rồi mới commit.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import codeguard

# Khoá chứa họ tên người. Không bắt "name" chung chung: documentName / fileName là tên giấy tờ, thay đi là hỏng phân loại.
_NAME_KEY = re.compile(r"ho.?(va.?)?ten|fullname|full_name|ten.?(nguoi|cha|me|vo|chong|con|chu|ban|tre)|^(ten|name)$|"
                       r"(applicant|owner|person|nguoi).?name", re.I)
_ADDRESS_KEY = re.compile(r"dia.?chi|address|thuong.?tru|tam.?tru|noi.?o|que.?quan|noi.?sinh|cho.?o", re.I)
_NAME_LABEL = re.compile(
    r"(?im)^[ \t>*-]*(?:h[ọo][, ]*(?:ch[ữu] [đd][ệe]m)?[, ]*(?:v[àa] )?t[êe]n(?: khai sinh)?|full name|name)"
    r"[^:\n]{0,30}[:：][ \t]*([^\n]{3,80})$"
)
_DIGITS = re.compile(r"\d(?:[ .]?\d){8,15}")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_ADMIN = re.compile(r"^(x[ãa]|ph[ưu][ờo]ng|th[ịi] tr[ấa]n|th[ịi] x[ãa]|huy[ệe]n|qu[ậa]n|th[àa]nh ph[ốo]|tp\.?|t[ỉi]nh|"
                    r"đ[ặa]c khu|vi[ệe]t nam)\b", re.I)
_UNICODE_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")
_THINK = re.compile(r"<think>.*?</think>", re.S)
_FAKE_NAMES = ["Nguyễn Văn An", "Trần Thị Bình", "Lê Văn Cường", "Phạm Thị Dung", "Hoàng Văn Em", "Vũ Thị Giang",
               "Đặng Văn Hùng", "Bùi Thị Lan", "Đỗ Văn Minh", "Ngô Thị Nga", "Dương Văn Phúc", "Lý Thị Quỳnh"]


class Skip(Exception):
    """Không dựng được ca hồi quy, kèm lý do cho người xem."""


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def _styled(original: str, fake: str) -> str:
    if original.isupper():
        return fake.upper()
    if original.islower():
        return fake.lower()
    return fake


class Anonymizer:
    def __init__(self) -> None:
        self.names: dict[str, str] = {}
        self.segments: dict[str, str] = {}

    # ---- thu thập -------------------------------------------------------------------------------------------------

    def add_name(self, value: Any) -> None:
        if not isinstance(value, str):
            return
        value = _norm(value)
        words = value.split()
        if not 2 <= len(words) <= 6 or any(ch.isdigit() for ch in value) or len(value) > 60:
            return
        key = value.casefold()
        if key not in self.names:
            self.names[key] = _FAKE_NAMES[len(self.names) % len(_FAKE_NAMES)]

    def add_address(self, value: Any) -> None:
        if not isinstance(value, str):
            return
        for part in re.split(r"[,;\n]", value):
            part = _norm(part)
            if len(part) < 3 or _ADMIN.match(part):
                continue
            key = part.casefold()
            if key not in self.segments:
                village = re.match(r"^(th[ôo]n|x[óo]m|t[ổo]|[ấa]p|b[ảa]n|khu|tdp|t[ổo] d[âa]n ph[ốo]|kh[ốo]i)\b", part, re.I)
                self.segments[key] = f"{village.group(1)} Mẫu {len(self.segments) + 1}" if village else f"Số {len(self.segments) + 1} đường Mẫu"

    def collect(self, data: Any, key: str = "") -> None:
        """Duyệt dict/list (fields, JSON LLM, options): giá trị dưới khoá tên / địa chỉ là dữ liệu thật."""
        if isinstance(data, dict):
            if "name" in data and "value" in data and isinstance(data.get("name"), str):  # một field {name, value}
                self.collect(data.get("value"), data["name"])
            for k, v in data.items():
                self.collect(v, str(k))
        elif isinstance(data, list):
            for item in data:
                self.collect(item, key)
        elif isinstance(data, str) and key:
            plain = _fold(key)
            if _NAME_KEY.search(plain):
                self.add_name(data)
            if _ADDRESS_KEY.search(plain):
                self.add_address(data)

    def collect_text(self, text: str) -> None:
        for found in _NAME_LABEL.finditer(text or ""):
            self.add_name(re.split(r"\s{2,}|\t|\s[-–]\s|\b(?:sinh ngày|ngày sinh|giới tính)\b", found.group(1), flags=re.I)[0])

    # ---- thay ---------------------------------------------------------------------------------------------------

    def _replace_terms(self, text: str, mapping: dict[str, str]) -> str:
        for original in sorted(mapping, key=len, reverse=True):
            fake = mapping[original]
            for variant in {original, _fold(original)}:
                pattern = re.compile(r"(?<!\w)" + r"\s+".join(map(re.escape, variant.split())) + r"(?!\w)", re.I)
                text = pattern.sub(lambda m, f=fake, v=variant: _styled(m.group(0), f if v == original else _fold(f)), text)
        return text

    @staticmethod
    def _digits(match: re.Match) -> str:
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if len(digits) < 9:
            return raw
        seed = hashlib.sha256(digits.encode()).hexdigest()
        fake = digits[:3] + "".join(str(int(c, 16) % 10) for c in seed[: len(digits) - 3])
        out, i = [], 0
        for ch in raw:  # giữ dấu cách / chấm ở đúng chỗ cũ
            if ch.isdigit():
                out.append(fake[i])
                i += 1
            else:
                out.append(ch)
        return "".join(out)

    def text(self, text: str) -> str:
        if not isinstance(text, str) or not text:
            return text
        text = self._replace_terms(text, self.names)
        text = self._replace_terms(text, self.segments)
        text = _EMAIL.sub("mau@example.com", text)
        return _DIGITS.sub(self._digits, text)

    def deep(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: self.deep(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self.deep(v) for v in data]
        return self.text(data) if isinstance(data, str) else data


def _clean_raw(raw: str) -> str:
    """Bỏ phần suy nghĩ của model và giải mã \\uXXXX ngoài ASCII, kẻo họ tên mã hoá lọt qua bước thay."""
    raw = _THINK.sub("<think></think>", raw or "")
    return _UNICODE_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)) if int(m.group(1), 16) >= 0x80 else m.group(0), raw)


def _json_blocks(raw: str) -> list[Any]:
    found = []
    for block in re.findall(r"\{.*\}", raw or "", re.S):
        try:
            found.append(json.loads(block))
        except ValueError:
            continue
    return found


def _steps_llm(steps: dict) -> list[dict]:
    llm = steps.get("llm") or []
    if isinstance(llm, dict) and "_json" in llm:
        try:
            llm = json.loads(llm["_json"])
        except ValueError as reason:
            raise Skip("Trace của lượt chạy lại bị cắt, không đọc được các lần gọi LLM.") from reason
    return sorted((c for c in llm if isinstance(c, dict)), key=lambda c: c.get("n") or 0)


def recorded(db, request_id: str) -> tuple[dict[str, str], list[dict], list[dict]]:
    """(OCR theo tên tệp, các lần gọi LLM {purpose, raw}, fields) của một lượt chạy lại, đọc từ Mongo của backend thử."""
    steps = db.trace_steps.find_one({"_id": f"{request_id}:autofill"}) or db.trace_steps.find_one({"request_id": request_id})
    if not steps:
        raise Skip("Không thấy trace_steps của lượt chạy lại đạt (backend thử chưa bật ghi trace đầy đủ?).")
    ocr: dict[str, str] = {}
    for ref in steps.get("ocr") or []:
        name = ref.get("name")
        if not name or name in ocr:
            continue
        doc = db.ocr_texts.find_one({"_id": ref.get("sha256")}) if ref.get("sha256") else None
        if doc and doc.get("truncated"):
            raise Skip(f"OCR của tệp {name} bị cắt khi ghi trace, phát lại sẽ khác lượt thật.")
        ocr[name] = (doc or {}).get("text") or ref.get("text") or ""
    calls = []
    for call in _steps_llm(steps):
        if call.get("raw") is None:
            raise Skip("Câu trả lời LLM của lượt chạy lại bị cắt khi ghi trace.")
        calls.append({"purpose": call.get("purpose"), "raw": call["raw"]})
    request = db.process_requests.find_one({"request_id": request_id}, {"fields": 1}) or {}
    return ocr, calls, request.get("fields") or []


def build(*, job: dict, case: dict, decision: dict, run_request_id: str, db, account: dict, options: dict) -> dict:
    """Dựng ca ẩn danh. Ném Skip nếu thiếu dữ liệu hoặc còn dữ liệu thật sau khi thay."""
    ocr, calls, run_fields = recorded(db, run_request_id)
    if not calls:
        raise Skip("Lượt chạy lại không gọi LLM, không có gì để phát lại.")
    checks = decision.get("acceptance") or []
    files = [{"name": f.get("name"), "role": f.get("role") or "doc", "ocr": ocr.get(f.get("name"), "")}
             for f in case.get("storedFiles") or []]
    raws = [_clean_raw(c["raw"]) for c in calls]

    anon = Anonymizer()
    anon.collect(case.get("fields") or [])
    anon.collect(run_fields)
    anon.collect(options)
    for raw in raws:
        for block in _json_blocks(raw):
            anon.collect(block)
    for item in files:
        anon.collect_text(item["ocr"])

    procedure = case.get("procedure")
    out = {
        "version": 1,
        "id": job["id"],
        "procedure": procedure,
        "label": case.get("label"),
        "createdAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "Ca hồi quy sinh tự động từ một ca Agent tự sửa đã đạt. Dữ liệu đã ẩn danh: soát lại trước khi commit.",
        "account": {k: account.get(k) for k in ("username", "xa", "tinh", "role") if account.get(k)},
        "options": anon.deep(options),
        "files": [{"name": anon.text(f["name"]), "role": f["role"], "ocr": anon.text(f["ocr"])} for f in files],
        "llm": [{"purpose": c["purpose"], "raw": anon.text(raw)} for c, raw in zip(calls, raws)],
        "checks": [{**c, "expected": anon.text(c["expected"]) if isinstance(c.get("expected"), str) else c.get("expected")}
                   for c in checks],
    }
    terms = codeguard.private_terms([*(case.get("fields") or []), *run_fields], job.get("requestId") or "")
    terms |= {codeguard._norm(name) for name in anon.names} | {codeguard._norm(s) for s in anon.segments if len(s) >= 8}
    dumped = json.dumps(out, ensure_ascii=False)
    leaks = codeguard.leaked_terms("\n".join("+" + line for line in dumped.splitlines()), terms)
    if leaks:
        raise Skip(f"Sau khi ẩn danh vẫn còn {len(leaks)} chuỗi dữ liệu thật, không ghi ca hồi quy.")
    return out


def path_for(root: Path, case: dict) -> Path:
    return root / re.sub(r"[^\w.-]", "_", str(case.get("procedure") or "khac")) / f"{case['id']}.json"
