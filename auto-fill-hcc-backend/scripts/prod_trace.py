"""Lấy trace từ backend PROD về máy để chẩn đoán — chạy ở MÁY DEV, không chạy trong container.

Chỉ dùng thư viện chuẩn (không import app) để chạy được bằng bất kỳ python3 nào.

Cấu hình (biến môi trường; thiếu thì đọc ./.env của repo — file này đã nằm trong .gitignore và
.dockerignore):
    PROD_TRACE_API    URL gốc backend prod, vd https://api.example.vn (không có "/" cuối)
    PROD_TRACE_USER   tài khoản super_admin (cùng tài khoản đăng nhập web Monitor)
    PROD_TRACE_PASS   mật khẩu
    PROD_TRACE_OUT    thư mục lưu JSON (mặc định <thư mục hcc>/traces-prod — ngoài mọi repo git)

Ví dụ:
    .venv/bin/python scripts/prod_trace.py get 8f3a2c1e
    .venv/bin/python scripts/prod_trace.py get 8f3a2c1e --kind attach --ocr
    .venv/bin/python scripts/prod_trace.py get 8f3a2c1e --files      # tải kèm tệp gốc người dùng upload
    .venv/bin/python scripts/prod_trace.py list --procedure xac-nhan-tinh-trang-hon-nhan --from 2026-09-01
    .venv/bin/python scripts/prod_trace.py list --procedure xac-nhan-tinh-trang-hon-nhan --outcome issues --download
    .venv/bin/python scripts/prod_trace.py procedures --grep "hôn nhân"
    # 50 hồ sơ KHÁC NHAU mới nhất của một tài khoản (bỏ lượt chạy lại), kèm tệp gốc:
    .venv/bin/python scripts/prod_trace.py collect --user hccphuongnghialo --procedure xac-nhan-tinh-trang-hon-nhan --count 50

Trace chứa text OCR giấy tờ thật của người dân: không commit, không gửi thư mục output đi nơi khác.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import ssl
import sys
import unicodedata
import zipfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_VN_TZ = timezone(timedelta(hours=7))
_TIMEOUT_S = 60


def _ssl_context() -> ssl.SSLContext:
    # Python cài từ python.org trên macOS không kèm kho CA hệ thống → lỗi CERTIFICATE_VERIFY_FAILED
    # dù chứng chỉ server hợp lệ. certifi có sẵn trong .venv (httpx kéo theo); thiếu thì dùng mặc định.
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _load_config() -> dict:
    keys = ("PROD_TRACE_API", "PROD_TRACE_USER", "PROD_TRACE_PASS", "PROD_TRACE_OUT")
    cfg = {k: os.environ.get(k, "") for k in keys}
    env_file = _REPO_ROOT / ".env"
    if not all(cfg[k] for k in keys[:3]) and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.strip().partition("=")
            if sep and name in keys and not cfg[name]:
                cfg[name] = value.strip().strip('"').strip("'")
    missing = [k for k in keys[:3] if not cfg[k]]
    if missing:
        sys.exit(f"Thiếu cấu hình: {', '.join(missing)} (đặt biến môi trường hoặc thêm vào {env_file})")
    cfg["PROD_TRACE_API"] = cfg["PROD_TRACE_API"].rstrip("/")
    cfg["PROD_TRACE_OUT"] = cfg["PROD_TRACE_OUT"] or str(_REPO_ROOT.parent / "traces-prod")
    return cfg


class Client:
    def __init__(self, base: str, username: str, password: str):
        self.base = base
        login = self._call("POST", "/auth/login", body={
            "username": username, "password": password, "superAdminOnly": True,
        })
        self.token = login["accessToken"]

    def _call(self, method: str, path: str, *, params: dict | None = None, body: dict | None = None,
              raw: bool = False):
        query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v not in (None, "")})
        url = f"{self.base}{path}" + (f"?{query}" if query else "")
        # Cloudflare chặn (lỗi 1010) User-Agent mặc định "Python-urllib" → tự khai tên công cụ.
        headers = {"Accept": "application/json", "User-Agent": "hcc-prod-trace/1.0"}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if getattr(self, "token", None):
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT_S, context=_ssl_context()) as resp:
                content = resp.read()
                return content if raw else json.loads(content.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise ApiError(exc.code, detail) from None
        except urllib.error.URLError as exc:
            sys.exit(f"Không kết nối được {self.base}: {exc.reason}")

    def get(self, path: str, **params):
        return self._call("GET", path, params=params)

    def get_bytes(self, path: str) -> bytes:
        return self._call("GET", path, raw=True)


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status


def _vn_time(value) -> str:
    if not value:
        return "-"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_VN_TZ).strftime("%d/%m/%Y %H:%M:%S")


def _unwrap(value):
    """persist.py cắt phần quá dài thành {"_json": "<chuỗi JSON bị cắt>"} — mở lại nếu còn parse được."""
    if isinstance(value, dict) and set(value) == {"_json"}:
        try:
            return json.loads(value["_json"])
        except (TypeError, ValueError):
            return value
    return value


def _short(value, width: int = 90) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1] + "…"


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", str(text or ""))
    return "".join(c for c in text if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D").lower()


# ---------------------------------------------------------------- get

def _resolve_request_ids(client: Client, code: str) -> list[dict]:
    """Mã hỗ trợ cán bộ gửi hay thiếu/dư ký tự → dùng tìm gần đúng của /api/v1/traces."""
    res = client.get("/api/v1/traces", requestId=code, pageSize=20)
    return res.get("items") or []


def _fetch_run(client: Client, request_id: str, kind: str | None) -> dict | None:
    try:
        return client.get(f"/api/v1/monitor/runs/{urllib.parse.quote(request_id)}", kind=kind)
    except ApiError as exc:
        if exc.status == 404:
            return None
        raise


def _save(out_dir: Path, request_id: str, kind: str | None, data: dict) -> Path:
    # Mỗi mã một thư mục: trace JSON, tệp gốc (--files) và các lần so sánh OCR nằm chung một chỗ.
    folder = out_dir / request_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{request_id}{'_' + kind if kind else ''}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def _print_fields(title: str, fields) -> None:
    fields = _unwrap(fields)
    if isinstance(fields, dict) and "fields" in fields:
        fields = fields["fields"]
    if isinstance(fields, dict):
        fields = [{"name": k, "value": v} for k, v in fields.items()]
    if not isinstance(fields, list) or not fields:
        return
    print(f"\n── {title} ({len(fields)})")
    for f in fields:
        if not isinstance(f, dict):
            print(f"   {_short(f)}")
            continue
        flag = " [default]" if f.get("default") else ""
        comp = f" <{f['comp']}>" if f.get("comp") else ""
        print(f"   {f.get('name')}{comp}{flag} = {_short(f.get('value'), 110)}")


def _print_run(data: dict, show_ocr: bool) -> None:
    trace = data.get("trace") or {}
    steps = data.get("steps") or {}
    meta = steps.get("meta") or {}
    stats = trace.get("stats") or {}
    timing = steps.get("timing") or {}

    print("═" * 100)
    print(f"Mã: {trace.get('request_id') or steps.get('request_id')}   kind: {trace.get('kind') or steps.get('kind')}"
          f"   nguồn: {trace.get('experience') or steps.get('experience')}")
    print(f"Thủ tục: {trace.get('procedure') or meta.get('procedure')} — {trace.get('procedure_label') or meta.get('procedure_label') or ''}")
    print(f"Lúc: {_vn_time(trace.get('created_at') or steps.get('created_at'))}   "
          f"đơn vị: {trace.get('name') or meta.get('name') or '-'} ({trace.get('username') or meta.get('username') or '-'})")
    print(f"Kết quả: {trace.get('outcome') or steps.get('outcome') or trace.get('status')}   "
          f"lỗi: {trace.get('error_code') or '-'}   số field: {trace.get('fields_count')}   "
          f"field then chốt: {trace.get('key_fields_filled')}/{trace.get('key_fields_total')}")
    if stats or timing:
        print(f"Thời gian: OCR {stats.get('ocr_latency_ms')} ms · LLM {stats.get('llm_latency_ms')} ms · "
              f"tổng {stats.get('total_latency_ms')} ms · chờ {timing.get('wait')} ms")
    files = trace.get("attachments") or []
    if files:
        print("Tệp: " + "; ".join(f"{f.get('name')}" + (f" ({f.get('role')})" if f.get("role") else "") for f in files))
    errors = list(trace.get("errors") or []) + list(steps.get("errors") or [])
    for err in errors:
        print(f"  ⚠ {_short(err, 200)}")

    calls = _unwrap(steps.get("llm")) or []
    if isinstance(calls, list) and calls:
        print(f"\n── Lần gọi LLM ({len(calls)})")
        for c in calls:
            if not isinstance(c, dict):
                continue
            print(f"   #{c.get('n')} {c.get('purpose')} · {c.get('target') or 'primary'} · {c.get('ms')} ms · "
                  f"prompt {c.get('prompt_chars')} ký tự · max_tokens {c.get('max_tokens')} · "
                  f"finish {c.get('finish_reason') or '-'}" + (f" · LỖI {c.get('error')}" if c.get("error") else ""))

    outputs = _unwrap(steps.get("outputs")) or {}
    if not isinstance(outputs, dict):
        outputs = {}
    llm_output = trace.get("llm_output")
    if llm_output:
        _print_fields("LLM trả về", llm_output.get("fields", llm_output) if isinstance(llm_output, dict) else llm_output)
    dropped = _unwrap(outputs.get("validate_dropped"))
    if dropped:
        print(f"\n── Bị validate loại ({len(dropped)}): {_short(dropped, 300)}")
    _print_fields("Trả cho extension", outputs.get("response"))
    if outputs.get("reasoning_context"):
        print(f"\n── reasoning_context: {_short(outputs['reasoning_context'], 400)}")

    ocr_text = trace.get("ocr_text") or ""
    print(f"\n── OCR: {len(ocr_text)} ký tự" + ("" if show_ocr else " (thêm --ocr để in)"))
    if show_ocr and ocr_text:
        print(ocr_text)


def cmd_get(client: Client, args, out_dir: Path) -> None:
    for code in args.request_ids:
        data = _fetch_run(client, code, args.kind)
        request_id = code
        if data is None:
            matches = _resolve_request_ids(client, code)
            ids = sorted({m.get("request_id") for m in matches if m.get("request_id")})
            if not ids:
                print(f"✗ Không tìm thấy lượt nào có mã chứa '{code}'")
                continue
            if len(ids) > 1:
                print(f"✗ '{code}' khớp {len(ids)} mã, ghi rõ hơn: {', '.join(ids[:10])}")
                continue
            request_id = ids[0]
            data = _fetch_run(client, request_id, args.kind)
            if data is None:
                print(f"✗ Không mở được lượt {request_id}")
                continue
        kind = args.kind or (data.get("trace") or {}).get("kind") or (data.get("steps") or {}).get("kind")
        path = _save(out_dir, request_id, kind, data)
        if args.raw:
            print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        else:
            _print_run(data, args.ocr)
        print(f"\n💾 {path}")
        if args.files:
            _download_files(client, data, out_dir, request_id)


def _download_files(client: Client, data: dict, out_dir: Path, request_id: str,
                    quiet: bool = False) -> list[Path]:
    """Tệp gốc của lượt (ảnh/PDF người dùng upload) → <out>/<request_id>/, để chạy lại OCR so sánh."""
    trace_id = (data.get("trace") or {}).get("id")
    if not trace_id:
        if not quiet:
            print("   (lượt này không có trace nên không tải được tệp gốc)")
        return []
    try:
        blob = client.get_bytes(f"/api/v1/traces/{urllib.parse.quote(trace_id)}/download")
    except ApiError as exc:
        if not quiet:
            print(f"   ✗ Không tải được tệp gốc: {exc}")
        return []
    target = out_dir / request_id
    target.mkdir(parents=True, exist_ok=True)
    paths = []
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            # Chỉ lấy tên file: tên trong zip do BE đặt theo tên người dùng upload, không tin đường dẫn.
            path = target / Path(member.filename).name
            path.write_bytes(zf.read(member))
            paths.append(path)
            if not quiet:
                print(f"📎 {path}")
    return paths


# ---------------------------------------------------------------- list

def cmd_list(client: Client, args, out_dir: Path) -> None:
    res = client.get(
        "/api/v1/monitor/runs",
        procedure=args.procedure, source=args.source, kind=args.kind, outcome=args.outcome,
        dateFrom=args.date_from, dateTo=args.date_to, q=args.q, pageSize=args.limit, page=1,
    )
    items = res.get("items") or []
    print(f"{len(items)}/{res.get('total')} lượt"
          + (f" — {args.procedure}" if args.procedure else ""))
    print(f"{'Lúc (VN)':19}  {'Mã':38}  {'kind':8}  {'nguồn':8}  {'kết quả':8}  {'chờ(s)':>6}  {'tệp':>3}  {'then chốt':>9}  Đơn vị")
    for it in items:
        wait = it.get("wait_ms")
        key = f"{it.get('key_fields_filled')}/{it.get('key_fields_total')}" if it.get("key_fields_total") else "-"
        print(f"{_vn_time(it.get('created_at')):19}  {str(it.get('request_id')):38}  {str(it.get('kind')):8}  "
              f"{str(it.get('experience')):8}  {str(it.get('outcome')):8}  "
              f"{(wait / 1000 if wait else 0):6.1f}  {str(it.get('files') or 0):>3}  {key:>9}  {it.get('name') or it.get('username') or ''}")
    if args.download:
        print()
        for it in items:
            rid, kind = it.get("request_id"), it.get("kind")
            if not rid:
                continue
            data = _fetch_run(client, rid, kind)
            if data is not None:
                print(f"💾 {_save(out_dir, rid, kind, data)}")
                if args.files:
                    _download_files(client, data, out_dir, rid)


# ---------------------------------------------------------------- collect

def _user_id(client: Client, username: str) -> str:
    for user in client.get("/api/v1/monitor/facets").get("users") or []:
        if (user.get("username") or "").lower() == username.lower():
            return user["userId"]
    sys.exit(f"✗ Không có tài khoản '{username}' trong dữ liệu trace")


def _llm_fields(trace: dict) -> dict:
    output = trace.get("llm_output")
    raw = output.get("fields") if isinstance(output, dict) else None
    if isinstance(raw, list):
        return {f.get("name"): f.get("value") for f in raw if isinstance(f, dict)}
    return raw if isinstance(raw, dict) else {}


def _person_keys(trace: dict) -> set[str]:
    """Dấu hiệu nhận ra CÙNG một hồ sơ khi cán bộ chạy lại nhiều lượt.

    Người yêu cầu (tên VNeID), mọi số định danh 12 chữ số và họ tên trong kết quả trích xuất. Họ tên
    so sau khi bỏ dấu vì OCR hay đọc lệch dấu giữa các lượt của cùng một tờ giấy.
    """
    keys = set()
    applicant = " ".join(_fold(trace.get("applicant_name") or "").upper().split())
    if applicant:
        keys.add("app:" + applicant)
    for name, value in _llm_fields(trace).items():
        if not isinstance(value, str) or not name:
            continue
        if name.endswith(("SoDinhDanh", "IdNumber")):
            digits = re.sub(r"\D", "", value)
            if len(digits) == 12:
                keys.add("id:" + digits)
        elif name.endswith(("HoTen", "SubjectName")):
            folded = " ".join(_fold(value).upper().split())
            if len(folded.split()) >= 2:
                keys.add("name:" + folded)
    return keys


def cmd_collect(client: Client, args, out_dir: Path) -> None:
    """N hồ sơ KHÁC NHAU mới nhất (bỏ lượt chạy lại), mỗi hồ sơ lấy lượt điền mới nhất + tệp gốc."""
    user_id = _user_id(client, args.user) if args.user else None
    seen: set[str] = set()
    picked, skipped = [], []
    page = 1
    while len(picked) < args.count:
        res = client.get(
            "/api/v1/monitor/runs", userId=user_id, procedure=args.procedure, kind="autofill",
            source=args.source, dateFrom=args.date_from, dateTo=args.date_to, pageSize=100, page=page,
        )
        items = res.get("items") or []
        if not items:
            break
        for item in items:
            if len(picked) >= args.count:
                break
            rid = item.get("request_id")
            account = _fold(f"{item.get('username') or ''} {item.get('name') or ''}").lower()
            if any(_fold(word).lower() in account for word in args.skip_account):
                continue
            data = _fetch_run(client, rid, "autofill") or {}
            trace = data.get("trace") or {}
            if not trace or not _llm_fields(trace):
                skipped.append({"request_id": rid, "ly_do": "không có kết quả trích xuất"})
                continue
            keys = _person_keys(trace)
            hashes = [a.get("sha256") for a in trace.get("attachments") or []]
            if hashes and all(hashes):
                keys.add("files:" + ",".join(sorted(hashes)))
            duplicate = keys & seen
            if duplicate:
                seen |= keys
                skipped.append({"request_id": rid, "ly_do": "trùng hồ sơ đã chọn", "khoa": sorted(duplicate)[:3]})
                continue
            paths = _download_files(client, data, out_dir, rid, quiet=True)
            if not paths:
                # Không đánh dấu đã thấy: lượt cũ hơn của cùng hồ sơ có thể còn tệp gốc.
                skipped.append({"request_id": rid, "ly_do": "không tải được tệp gốc"})
                continue
            # Lượt handfree/scan có thể không ghi sha256 và trích xuất trống tên/số → so thêm theo
            # từng tệp đã tải; chung dù một tệp cũng là cùng hồ sơ (chạy lại với bớt/thêm tệp).
            file_keys = {"file:" + hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
            if file_keys & seen:
                seen |= keys | file_keys
                skipped.append({"request_id": rid, "ly_do": "trùng hồ sơ đã chọn", "khoa": ["tệp giống"]})
                continue
            seen |= keys | file_keys
            _save(out_dir, rid, "autofill", data)
            picked.append({
                "request_id": rid, "created_at": trace.get("created_at"),
                "experience": trace.get("experience"), "files": [p.name for p in paths],
            })
            print(f"[{len(picked):>2}/{args.count}] {_vn_time(trace.get('created_at'))}  {rid}  "
                  f"{trace.get('experience') or '':8} tệp={len(paths)}")
        page += 1

    batch_dir = out_dir / f"_batch_{args.user or 'all'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    manifest = batch_dir / "manifest.json"
    manifest.write_text(json.dumps({
        "user": args.user, "procedure": args.procedure, "count": len(picked),
        "picked": picked, "skipped": skipped,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    reasons: dict[str, int] = {}
    for row in skipped:
        reasons[row["ly_do"]] = reasons.get(row["ly_do"], 0) + 1
    print(f"\nChọn {len(picked)} hồ sơ · bỏ {len(skipped)} lượt {reasons}")
    print(f"📄 {manifest}")


def cmd_procedures(client: Client, args, _out_dir: Path) -> None:
    procedures = client.get("/api/v1/monitor/facets").get("procedures") or []
    want = _fold(args.grep) if args.grep else ""
    for p in procedures:
        if want and want not in _fold(f"{p.get('key')} {p.get('label')}"):
            continue
        print(f"{str(p.get('key')):55}  {p.get('label') or ''}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lấy trace từ backend PROD (web Monitor API).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_get = sub.add_parser("get", help="Chi tiết một hoặc nhiều lượt theo mã hỗ trợ (request_id)")
    p_get.add_argument("request_ids", nargs="+", help="Mã hỗ trợ; thiếu vài ký tự vẫn tìm được")
    p_get.add_argument("--kind", choices=["autofill", "attach", "classify", "owner_info"],
                       help="Bước cần xem (mặc định: bước mới nhất của mã đó)")
    p_get.add_argument("--ocr", action="store_true", help="In toàn bộ text OCR")
    p_get.add_argument("--raw", action="store_true", help="In nguyên JSON thay cho bản tóm tắt")
    p_get.add_argument("--files", action="store_true", help="Tải kèm tệp gốc người dùng upload")

    p_list = sub.add_parser("list", help="Danh sách lượt theo thủ tục / ngày / kết quả")
    p_list.add_argument("--procedure", help="Key thủ tục, vd xac-nhan-tinh-trang-hon-nhan")
    p_list.add_argument("--from", dest="date_from", help="YYYY-MM-DD (giờ VN)")
    p_list.add_argument("--to", dest="date_to", help="YYYY-MM-DD (giờ VN, tính cả ngày này)")
    p_list.add_argument("--source", choices=["all", "autofill", "handfree"], default="all")
    p_list.add_argument("--kind", choices=["all", "autofill", "attach", "classify", "owner_info"], default="all")
    p_list.add_argument("--outcome", choices=["all", "ok", "partial", "error", "issues"], default="all")
    p_list.add_argument("--q", help="Tìm theo mã / tên đơn vị / người làm thủ tục")
    p_list.add_argument("--limit", type=int, default=20, help="Số lượt (tối đa 200)")
    p_list.add_argument("--download", action="store_true", help="Tải chi tiết từng lượt về thư mục output")
    p_list.add_argument("--files", action="store_true", help="Cùng --download: tải kèm tệp gốc từng lượt")

    p_col = sub.add_parser("collect", help="N hồ sơ khác nhau mới nhất (bỏ lượt chạy lại) + tệp gốc")
    p_col.add_argument("--procedure", required=True, help="Key thủ tục")
    p_col.add_argument("--user", help="Username tài khoản (vd hccphuongnghialo)")
    p_col.add_argument("--count", type=int, default=50)
    p_col.add_argument("--source", choices=["all", "autofill", "handfree"], default="all")
    p_col.add_argument("--from", dest="date_from", help="YYYY-MM-DD (giờ VN)")
    p_col.add_argument("--to", dest="date_to", help="YYYY-MM-DD (giờ VN)")
    p_col.add_argument("--skip-account", action="append", default=[],
                       help="Bỏ tài khoản có username/tên chứa chuỗi này (lặp lại được), vd --skip-account test")

    p_proc = sub.add_parser("procedures", help="Danh sách key thủ tục đã có trace")
    p_proc.add_argument("--grep", help="Lọc theo key/tên, không phân biệt dấu")

    args = parser.parse_args()
    cfg = _load_config()
    out_dir = Path(cfg["PROD_TRACE_OUT"]).expanduser()
    try:
        client = Client(cfg["PROD_TRACE_API"], cfg["PROD_TRACE_USER"], cfg["PROD_TRACE_PASS"])
        {"get": cmd_get, "list": cmd_list, "collect": cmd_collect, "procedures": cmd_procedures}[args.cmd](client, args, out_dir)
    except ApiError as exc:
        sys.exit(f"✗ {exc}")


if __name__ == "__main__":
    main()
