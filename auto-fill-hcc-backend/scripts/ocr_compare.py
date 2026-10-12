"""So OCR Qwen với kết quả trích xuất của pipeline thật — CÔNG CỤ THỬ ở máy dev, không chạy trên prod.

Luồng cho mỗi hồ sơ (1 và 2 chạy song song, xong mới tới 3):
  1. Pipeline thật của thủ tục: OCR Tiếng Nói (Vintern) → LLM trích xuất → mapper. Cache OCR tắt để
     Vintern đọc lại từ đầu, đúng như một lượt mới.
  2. OCR Qwen (app/services/ocr_qwen.py) trên cùng các tệp.
  3. Agent Qwen đánh giá từng field LLM bóc ra: có khớp với chữ Qwen đọc được không, lệch do OCR hay
     do bước trích xuất, và field nào đang trống mà Qwen đọc thấy.

Chạy từ thư mục auto-fill-hcc-backend:
    .venv/bin/python -m scripts.ocr_compare req_xxx                 # thiếu thì tự tải trace + tệp gốc từ prod
    .venv/bin/python -m scripts.ocr_compare req_xxx req_yyy --think # agent đánh giá bật suy luận
    .venv/bin/python -m scripts.ocr_compare --procedure xac-nhan-tinh-trang-hon-nhan --file a.jpg --file b.pdf
    # cả đợt do `prod_trace.py collect` lấy về, 3 hồ sơ song song, bỏ hồ sơ đã có compare_*:
    .venv/bin/python -m scripts.ocr_compare --manifest ../traces-prod/_batch_x/manifest.json --concurrency 3 --skip-done --quiet

Mỗi lần chạy ra một thư mục <PROD_TRACE_OUT>/<mã>/compare_<giờ>/ (mặc định hcc/traces-prod) gồm:
    ocr_vintern.txt   OCR Tiếng Nói mà pipeline đã dùng
    ocr_qwen.txt      OCR Qwen trên cùng tệp
    parse.json        JSON LLM trích xuất + field sau mapper + lỗi/thời gian
    danh_gia.json     kết quả agent đánh giá (kèm mô tả lệch từng ký tự) + meta thời gian/model
Chứa dữ liệu thật, không commit. Pipeline chạy bằng CODE LOCAL và không có formContext, nên field sau mapper có thể khác
prod; phần đánh giá chỉ so JSON LLM trích xuất (trước mapper).
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import difflib
import hashlib
import importlib
import json
import mimetypes
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.procedures import registry
from app.services import ocr_qwen
from app.services.llm.client import extract_json_block
from scripts import prod_trace

_EVAL_MAX_TOKENS = 6000
_EVAL_TIMEOUT_S = 300
_DESC_MAX_CHARS = 220

EVAL_PROMPT = """Bạn là kiểm định viên dữ liệu hồ sơ hành chính.
Pipeline đã đọc giấy tờ bằng OCR VINTERN rồi dùng LLM trích xuất ra KẾT QUẢ TRÍCH XUẤT. Một OCR độc lập là OCR QWEN đọc lại CÙNG các giấy tờ đó.
Nhiệm vụ: với TỪNG field trong KẾT QUẢ TRÍCH XUẤT, đối chiếu giá trị với chữ OCR QWEN đọc được ở đúng vị trí tương ứng trên giấy. Dùng MÔ TẢ FIELD để biết field lấy ở giấy nào, khối nào (vd khối người yêu cầu khác khối người được cấp).

Quy tắc:
- Chỉ dựa vào text được cung cấp. KHÔNG suy đoán, KHÔNG tự sửa, KHÔNG phán OCR nào đúng hơn — chỉ báo khớp hay lệch. Không dùng chữ "đúng"/"sai" trong ghi_chu.
- Nhiều tệp có cùng nội dung (upload trùng) thì chỉ đối chiếu một lần; mỗi field chỉ một dòng.
- "khop": cùng nội dung, chỉ khác định dạng — ngày "6/5/2025" = "06/05/2025" = "6-5-2025"; hoa/thường; khoảng trắng; dấu chấm dẫn dòng; địa chỉ dạng object so với dòng chữ khi cùng tỉnh, xã và phần chi tiết.
- "lech_nhe": cùng nội dung nhưng khác cách viết — viết tắt/đầy đủ ("UBND" ~ "Ủy ban nhân dân"), thêm/bớt tiền tố "Xã/Phường/Tỉnh", tên cơ quan cấp viết gọn.
- "lech": khác NỘI DUNG — khác bất kỳ chữ số nào; tên riêng khác dấu thanh hoặc khác chữ (vd "Lan" khác "Lân"); khác tên xã/tỉnh; khác giá trị lựa chọn (giới tính, dân tộc, quốc tịch).
- "khong_thay": OCR QWEN không có thông tin tương ứng (không đọc ra, hoặc field là giá trị suy ra chứ không in trên giấy).
- Field logic/suy ra (true/false, trạng thái đã chuẩn hóa): so với ý nghĩa câu chữ trên giấy.
- nguyen_nhan (chỉ ghi khi lech hoặc lech_nhe, còn lại null): "ocr" nếu OCR VINTERN ở chỗ đó đọc KHÁC OCR QWEN; "trich_xuat" nếu hai OCR đọc GIỐNG nhau mà kết quả trích xuất lại khác; "khong_ro" nếu không xác định được.
- bo_sot: field đang TRỐNG trong MÔ TẢ FIELD mà OCR QWEN đọc thấy rõ đúng thông tin field đó mô tả. Không liệt kê suy đoán.
- Trường giá trị dài thì rút gọn còn phần liên quan, tối đa 80 ký tự.

Trả DUY NHẤT một JSON trong code block:
```json
{"fields":[{"name":"<field>","trich_xuat":"<giá trị kết quả>","qwen":"<chữ Qwen đọc ở chỗ đó hoặc null>","vintern":"<chữ Vintern đọc ở chỗ đó hoặc null>","ket_luan":"khop|lech_nhe|lech|khong_thay","nguyen_nhan":"ocr|trich_xuat|khong_ro|null","ghi_chu":"<ngắn, chỉ khi không khớp>"}],
 "bo_sot":[{"name":"<field đang trống>","qwen":"<chữ Qwen đọc được>","ghi_chu":"<ngắn>"}],
 "tom_tat":"<1-2 câu>"}
```"""

_VERDICT_LABEL = {"khop": "KHỚP", "lech_nhe": "LỆCH NHẸ", "lech": "LỆCH", "khong_thay": "KHÔNG THẤY"}
_CAUSE_LABEL = {
    "ocr": "do OCR — Vintern và Qwen đọc khác nhau, trích xuất theo Vintern",
    "trich_xuat": "do bước trích xuất — hai OCR đọc giống nhau",
    "ca_hai": "OCR lệch nhau VÀ trích xuất cũng khác chữ Vintern",
    "khong_ro": "chưa rõ nguyên nhân",
}
_MAX_DIFF_OPS = 5


def _nfc(text: str) -> str:
    # macOS lưu tên file dạng NFD; tên trong trace là NFC — so khớp phải cùng dạng.
    return unicodedata.normalize("NFC", str(text or ""))


def _out_root() -> Path:
    value = os.environ.get("PROD_TRACE_OUT", "")
    env_file = prod_trace._REPO_ROOT / ".env"
    if not value and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, sep, raw = line.strip().partition("=")
            if sep and name == "PROD_TRACE_OUT":
                value = raw.strip().strip('"').strip("'")
    return Path(value or prod_trace._REPO_ROOT.parent / "traces-prod").expanduser()


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")


def describe_diff(base, other) -> str:
    """Mô tả ``base`` (kết quả trích xuất) khác ``other`` (chữ OCR) ở đâu, theo từng ký tự.

    Chỉ để người đọc thấy nhanh "lệch như nào"; kết luận khớp/lệch vẫn là của agent.
    """
    a, b = _nfc(base).strip(), _nfc(other).strip()
    if not a or not b or a == b:
        return ""
    if a.lower() == b.lower():
        return "chỉ khác chữ hoa/thường"
    if " ".join(a.split()) == " ".join(b.split()):
        return "chỉ khác khoảng trắng"
    digits_only = re.fullmatch(r"[\d\s/.\-]+", a) and re.fullmatch(r"[\d\s/.\-]+", b)
    ops = []
    changed_digits = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        changed_digits += sum(ch.isdigit() for ch in a[i1:i2]) or sum(ch.isdigit() for ch in b[j1:j2])
        left, right = _short(a[i1:i2], 25), _short(b[j1:j2], 25)
        if tag == "replace":
            ops.append(f"vị trí {i1 + 1}: '{left}' → '{right}'")
        elif tag == "delete":
            ops.append(f"vị trí {i1 + 1}: trích xuất thừa '{left}'")
        else:
            ops.append(f"vị trí {i1 + 1}: trích xuất thiếu '{right}'")
    if digits_only:
        kind = f"khác {changed_digits} chữ số"
    elif _fold(a).lower() == _fold(b).lower():
        kind = "chỉ khác dấu"
    else:
        kind = "khác chữ"
    more = f" (+{len(ops) - _MAX_DIFF_OPS} chỗ khác)" if len(ops) > _MAX_DIFF_OPS else ""
    return f"{kind}: " + "; ".join(ops[:_MAX_DIFF_OPS]) + more


def _norm_cmp(value) -> str:
    """Dạng so sánh thô: bỏ hoa/thường, dấu câu, khoảng trắng và số 0 đứng đầu ("08/06" = "8/6")."""
    if value is None:
        return ""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = re.sub(r"\d+", lambda m: str(int(m.group())), _nfc(text).casefold())
    return re.sub(r"[\W_]+", "", text)


def _same(left, right) -> bool | None:
    """Hai đoạn chữ agent chép ra có cùng nội dung không; thiếu một bên → None."""
    a, b = _norm_cmp(left), _norm_cmp(right)
    if not a or not b:
        return None
    if a == b:
        return True
    short, long = sorted((a, b), key=len)
    # Agent hay chép kèm nhãn ("ngày 13/11/1975") — chứa trọn nhau vẫn là cùng nội dung.
    return len(short) >= 6 and short in long


def _cause(row: dict) -> str | None:
    """Lệch do đâu, suy từ BA đoạn chữ agent chép ra — agent tự gán thì hay nhầm OCR với trích xuất."""
    if row.get("ket_luan") not in ("lech", "lech_nhe"):
        return None
    ocr_same = _same(row.get("vintern"), row.get("qwen"))
    extracted_from_vintern = _same(row.get("vintern"), row.get("trich_xuat"))
    if ocr_same is True:
        return "trich_xuat"
    if ocr_same is False:
        return "ocr" if extracted_from_vintern is not False else "ca_hai"
    return "khong_ro"


def _annotate(result: dict) -> None:
    """Gắn mô tả lệch + nguyên nhân tính bằng code vào từng dòng agent trả."""
    for row in result.get("fields") or []:
        if row.get("ket_luan") not in ("lech", "lech_nhe"):
            continue
        row["nguyen_nhan_agent"] = row.get("nguyen_nhan")
        row["nguyen_nhan"] = _cause(row)
        row["chi_tiet_lech"] = describe_diff(row.get("trich_xuat"), row.get("qwen"))
        vintern, qwen = row.get("vintern"), row.get("qwen")
        # Trích xuất chép đúng Vintern thì hai mô tả trùng nhau — chỉ in khi Vintern lệch Qwen KHÁC kiểu.
        if vintern and qwen and _nfc(vintern).strip() != _nfc(row.get("trich_xuat")).strip():
            row["vintern_so_voi_qwen"] = describe_diff(vintern, qwen).replace("trích xuất", "Vintern")


def _short(value, width: int) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = " ".join(str(text).split())
    return text if len(text) <= width else text[: width - 1] + "…"


# ---------------------------------------------------------------- đầu vào

# Chỉ đuôi của giấy tờ người dùng upload: thư mục của mã còn chứa trace JSON và file phân tích.
_DOC_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tif", ".tiff", ".bmp", ".docx"}


def _local_files(folder: Path) -> list[Path]:
    """Tệp gốc trong thư mục của mã."""
    if not folder.is_dir():
        return []
    return [
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in _DOC_SUFFIXES and not p.name.startswith(".")
    ]


def _prepare_request(request_id: str, out_root: Path) -> tuple[str, list[Path], dict]:
    """Trace + tệp gốc của mã từ thư mục output; chưa có thì tải từ prod (chỉ GET)."""
    meta_path = out_root / request_id / f"{request_id}_autofill.json"
    files = _local_files(out_root / request_id)
    if not meta_path.is_file() or not files:
        cfg = prod_trace._load_config()
        client = prod_trace.Client(cfg["PROD_TRACE_API"], cfg["PROD_TRACE_USER"], cfg["PROD_TRACE_PASS"])
        data = prod_trace._fetch_run(client, request_id, "autofill")
        if data is None:
            sys.exit(f"✗ Không tìm thấy lượt điền (autofill) của {request_id} trên prod")
        meta_path = prod_trace._save(out_root, request_id, "autofill", data)
        prod_trace._download_files(client, data, out_root, request_id)
        files = _local_files(out_root / request_id)
    trace = json.loads(meta_path.read_text(encoding="utf-8")).get("trace") or {}
    # Giữ đúng thứ tự tệp như lượt gốc: thứ tự tài liệu ảnh hưởng prompt ("### Tài liệu N").
    order = [_nfc(a.get("name")) for a in trace.get("attachments") or []]
    files.sort(key=lambda p: order.index(_nfc(p.name)) if _nfc(p.name) in order else len(order))
    return trace.get("procedure") or "", files, trace


def _file_dict(path: Path) -> dict:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    data = base64.b64encode(path.read_bytes()).decode()
    return {"name": _nfc(path.name), "type": mime, "dataUrl": f"data:{mime};base64,{data}"}


def _schema_fields(procedure: str) -> list[dict]:
    run = registry.get_pipeline(procedure)
    module = importlib.import_module(run.__module__)
    fields = getattr(module, "FIELDS", None)
    if fields is None:
        try:
            fields = importlib.import_module(run.__module__.rsplit(".", 1)[0] + ".schema").FIELDS
        except (ImportError, AttributeError):
            fields = []
    return fields


def _extracted(result: dict) -> dict:
    raw = (result.get("llm_output") or {}).get("fields")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        return {f.get("name"): f.get("value") for f in raw if isinstance(f, dict)}
    return {}


# ---------------------------------------------------------------- 3 bước

async def _timed(coro):
    t0 = time.monotonic()
    value = await coro
    return value, int((time.monotonic() - t0) * 1000)


async def _run_pipeline(procedure: str, files: list[dict]) -> dict:
    run = registry.get_pipeline(procedure)
    return await run({"doc": files}, {})


def _qwen_text(qwen_results: list[dict]) -> str:
    """Cùng dạng header "===== tên tệp =====" như OCR Vintern trong trace, để đặt cạnh nhau so."""
    return "\n\n".join(
        f"===== {r.get('name')} (qwen) =====\n{r.get('text') or '(không đọc được: ' + str(r.get('error')) + ')'}"
        for r in qwen_results
    )


async def _evaluate(schema: list[dict], extracted: dict, qwen_results: list[dict],
                    vintern_text: str, thinking: bool) -> dict:
    schema_lines = [
        f'- {f["name"]} [{"CÓ GIÁ TRỊ" if f["name"] in extracted else "trống"}]: {_short(f.get("desc"), _DESC_MAX_CHARS)}'
        for f in schema
    ]
    qwen_text = _qwen_text(qwen_results)
    user = (
        "## KẾT QUẢ TRÍCH XUẤT\n" + json.dumps(extracted, ensure_ascii=False, indent=1)
        + "\n\n## MÔ TẢ FIELD\n" + "\n".join(schema_lines)
        + "\n\n## OCR QWEN\n" + qwen_text
        + "\n\n## OCR VINTERN (nguồn pipeline đã dùng)\n" + (vintern_text or "(trống)")
    )
    resp = await ocr_qwen.chat(
        [{"role": "system", "content": EVAL_PROMPT}, {"role": "user", "content": user}],
        max_tokens=_EVAL_MAX_TOKENS, timeout_s=_EVAL_TIMEOUT_S, thinking=thinking,
    )
    try:
        parsed = extract_json_block(resp["content"])
    except Exception as exc:  # noqa: BLE001 — giữ output thô để xem vì sao agent trả sai định dạng
        parsed = {"_parse_error": str(exc), "_raw": resp["content"][:4000]}
    return {"result": parsed, "ms": resp["ms"], "finish_reason": resp["finish_reason"],
            "usage": resp["usage"], "prompt_chars": len(EVAL_PROMPT) + len(user)}


# ---------------------------------------------------------------- in kết quả

def _print_report(label: str, procedure: str, pipeline_ms: int, pipeline: dict,
                  qwen_ms: int, qwen_results: list[dict], evaluation: dict, eval_ms: int) -> None:
    stats = pipeline.get("stats") or {}
    print("═" * 110)
    print(f"{label} — {procedure}")
    print(f"Pipeline (Vintern + LLM + mapper): {pipeline_ms} ms  (OCR {stats.get('ocr_latency_ms')} ms · "
          f"LLM {stats.get('llm_latency_ms')} ms)  · lỗi: {pipeline.get('errors') or '-'}")
    for r in qwen_results:
        print(f"OCR Qwen   {r.get('name')}: {r.get('pages')} trang · {r.get('ms')} ms · {len(r.get('text') or '')} ký tự"
              + (f" · ⚠ {r['error']}" if r.get("error") else ""))
    print(f"(song song: tổng bước 1+2 = {max(pipeline_ms, qwen_ms)} ms) · Agent đánh giá: {eval_ms} ms "
          f"· finish {evaluation.get('finish_reason')}")

    result = evaluation.get("result") or {}
    if "_parse_error" in result:
        print(f"\n✗ Agent trả sai định dạng: {result['_parse_error']}\n{result.get('_raw', '')[:1500]}")
        return
    rows = result.get("fields") or []
    counts: dict[str, int] = {}
    print()
    # Field lệch in trước và in đủ chi tiết; field khớp chỉ một dòng để không lấp mất chỗ lệch.
    order = {"lech": 0, "lech_nhe": 1, "khong_thay": 2, "khop": 3}
    for row in sorted(rows, key=lambda r: order.get(r.get("ket_luan"), 9)):
        verdict = row.get("ket_luan") or "?"
        counts[verdict] = counts.get(verdict, 0) + 1
        label = _VERDICT_LABEL.get(verdict, verdict.upper())
        if verdict == "khop":
            print(f"[{label}] {row.get('name')}: {_short(row.get('trich_xuat'), 90)}")
            continue
        if verdict == "khong_thay":
            print(f"[{label}] {row.get('name')}: {_short(row.get('trich_xuat'), 70)} — Qwen không đọc thấy chỗ này")
            continue
        cause = _CAUSE_LABEL.get(row.get("nguyen_nhan"), "")
        print(f"\n[{label}] {row.get('name')}" + (f"  ({cause})" if cause else ""))
        print(f"    trích xuất : {_short(row.get('trich_xuat'), 100)}")
        print(f"    Qwen đọc   : {_short(row.get('qwen'), 100)}")
        print(f"    Vintern đọc: {_short(row.get('vintern'), 100)}")
        if row.get("chi_tiet_lech"):
            print(f"    lệch thế nào: {row['chi_tiet_lech']}")
        if row.get("vintern_so_voi_qwen"):
            print(f"    Vintern so với Qwen: {row['vintern_so_voi_qwen']}")
        if row.get("ghi_chu"):
            print(f"    ghi chú agent: {_short(row['ghi_chu'], 160)}")
    missed = result.get("bo_sot") or []
    if missed:
        print("\n[BỎ SÓT] Qwen đọc thấy nhưng trích xuất để trống:")
        for row in missed:
            print(f"    {row.get('name')}: {_short(row.get('qwen'), 80)} — {_short(row.get('ghi_chu'), 100)}")
    summary = " · ".join(f"{_VERDICT_LABEL.get(k, k)}: {v}" for k, v in sorted(counts.items(), key=lambda kv: order.get(kv[0], 9)))
    print(f"\nTổng: {len(rows)} field — {summary}" + (f" · BỎ SÓT: {len(missed)}" if missed else ""))
    if result.get("tom_tat"):
        print(f"Tóm tắt: {result['tom_tat']}")


async def _qwen_ocr_unique(files: list[dict]) -> list[dict]:
    """OCR Qwen mỗi NỘI DUNG một lần — cán bộ hay upload trùng một tệp; pipeline vẫn nhận đủ như prod."""
    unique: dict[str, dict] = {}
    keys = []
    for f in files:
        key = hashlib.sha256(f["dataUrl"].encode()).hexdigest()
        keys.append(key)
        unique.setdefault(key, f)
    results = dict(zip(unique, await ocr_qwen.ocr_per_file(list(unique.values()))))
    out = []
    for f, key in zip(files, keys):
        row = dict(results[key])
        if row.get("name") != f["name"]:
            row["trung_noi_dung_voi"] = row.get("name")
            row["name"] = f["name"]
        out.append(row)
    return out


async def _compare(label: str, procedure: str, paths: list[Path], out_dir: Path, thinking: bool,
                   quiet: bool = False) -> dict:
    if not registry.get_pipeline(procedure):
        print(f"✗ {label}: không có pipeline process cho thủ tục '{procedure}'")
        return {"label": label, "error": "không có pipeline"}
    files = [_file_dict(p) for p in paths]
    # Cache OCR tắt: Vintern phải đọc lại tệp như lượt mới, và harness không cần Mongo.
    settings.ocr_cache_enabled = False

    (pipeline, pipeline_ms), (qwen_results, qwen_ms) = await asyncio.gather(
        _timed(_run_pipeline(procedure, files)),
        _timed(_qwen_ocr_unique(files)),
    )
    extracted = _extracted(pipeline)
    evaluation, eval_ms = await _timed(_evaluate(
        _schema_fields(procedure), extracted, qwen_results, pipeline.get("ocr_text") or "", thinking,
    ))

    result = evaluation.get("result")
    if isinstance(result, dict) and "_parse_error" not in result:
        _annotate(result)
    if not quiet:
        _print_report(label, procedure, pipeline_ms, pipeline, qwen_ms, qwen_results, evaluation, eval_ms)

    # Mỗi lần chạy một thư mục riêng: chạy lại cùng hồ sơ (sau khi sửa prompt) không đè kết quả cũ.
    run_dir = out_dir / f"compare_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "ocr_vintern.txt").write_text(pipeline.get("ocr_text") or "", encoding="utf-8")
    (run_dir / "ocr_qwen.txt").write_text(_qwen_text(qwen_results), encoding="utf-8")
    _write_json(run_dir / "parse.json", {
        "procedure": procedure,
        "files": [p.name for p in paths],
        "llm_output": pipeline.get("llm_output"),
        "fields_sau_mapper": pipeline.get("fields"),
        "errors": pipeline.get("errors"),
        "stats": pipeline.get("stats"),
    })
    _write_json(run_dir / "danh_gia.json", {
        **(result if isinstance(result, dict) else {"_raw": result}),
        "meta": {
            "label": label,
            "model": settings.llm_model,
            "thinking": thinking,
            "qwen_ocr_sampling": ocr_qwen.OCR_SAMPLING,
            "timing_ms": {"pipeline": pipeline_ms, "qwen_ocr": qwen_ms, "danh_gia": eval_ms},
            "qwen_ocr_files": [{k: r.get(k) for k in ("name", "pages", "ms", "error")} for r in qwen_results],
            "finish_reason": evaluation.get("finish_reason"),
            "usage": evaluation.get("usage"),
            "prompt_chars": evaluation.get("prompt_chars"),
        },
    })
    counts: dict[str, int] = {}
    for row in (result.get("fields") if isinstance(result, dict) else None) or []:
        counts[row.get("ket_luan") or "?"] = counts.get(row.get("ket_luan") or "?", 0) + 1
    if not quiet:
        print(f"\n📁 {run_dir}")
        for name in ("ocr_vintern.txt", "ocr_qwen.txt", "parse.json", "danh_gia.json"):
            print(f"   {name}")
    return {
        "label": label, "run_dir": str(run_dir), "counts": counts,
        "bo_sot": len((result.get("bo_sot") if isinstance(result, dict) else None) or []),
        "timing_ms": {"pipeline": pipeline_ms, "qwen_ocr": qwen_ms, "danh_gia": eval_ms},
        "errors": (pipeline.get("errors") or []) + [r["error"] for r in qwen_results if r.get("error")]
                  + ([result["_parse_error"]] if isinstance(result, dict) and "_parse_error" in result else []),
    }


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


async def _compare_request(request_id: str, out_root: Path, args, sem: asyncio.Semaphore) -> dict:
    async with sem:
        try:
            procedure, paths, _trace = _prepare_request(request_id, out_root)
            if not paths:
                return {"label": request_id, "error": "không có tệp gốc"}
            return await _compare(request_id, procedure, paths, out_root / request_id, args.think, args.quiet)
        except Exception as exc:  # noqa: BLE001 — một hồ sơ lỗi không được dừng cả đợt
            return {"label": request_id, "error": f"{type(exc).__name__}: {exc}"}


async def main() -> None:
    parser = argparse.ArgumentParser(description="So OCR Qwen với kết quả trích xuất của pipeline.")
    parser.add_argument("request_ids", nargs="*", help="Mã hỗ trợ req_… (tự tải từ prod nếu chưa có)")
    parser.add_argument("--manifest", help="manifest.json do `prod_trace.py collect` tạo — chạy cả đợt")
    parser.add_argument("--procedure", help="Key thủ tục khi chạy với tệp local (--file)")
    parser.add_argument("--file", action="append", default=[], help="Tệp local, lặp lại cho nhiều tệp")
    parser.add_argument("--think", action="store_true", help="Bật suy luận cho agent đánh giá (chậm hơn)")
    parser.add_argument("--concurrency", type=int, default=1, help="Số hồ sơ chạy song song")
    parser.add_argument("--skip-done", action="store_true", help="Bỏ hồ sơ đã có thư mục compare_*")
    parser.add_argument("--quiet", action="store_true", help="Mỗi hồ sơ in một dòng thay cho bảng chi tiết")
    args = parser.parse_args()
    request_ids = list(args.request_ids)
    manifest = Path(args.manifest).expanduser() if args.manifest else None
    if manifest:
        request_ids += [row["request_id"] for row in json.loads(manifest.read_text(encoding="utf-8"))["picked"]]
    if not request_ids and not args.file:
        parser.error("cần ít nhất một mã req_…, --manifest hoặc --file")
    if args.file and not args.procedure:
        parser.error("--file cần kèm --procedure")

    out_root = _out_root()
    print(f"Qwen: {settings.llm_model} · Vintern: {settings.ocr_tiengnoi_base_url}")
    if args.skip_done:
        before = len(request_ids)
        request_ids = [rid for rid in request_ids if not any((out_root / rid).glob("compare_*"))]
        print(f"Bỏ {before - len(request_ids)} hồ sơ đã so, còn {len(request_ids)}")
    sem = asyncio.Semaphore(max(1, args.concurrency))
    t0 = time.monotonic()
    tasks = [asyncio.create_task(_compare_request(rid, out_root, args, sem)) for rid in request_ids]
    summaries = []
    for done, task in enumerate(asyncio.as_completed(tasks), 1):
        summary = await task
        summaries.append(summary)
        if args.quiet or summary.get("error"):
            counts = " ".join(f"{_VERDICT_LABEL.get(k, k)}={v}" for k, v in (summary.get("counts") or {}).items())
            print(f"[{done}/{len(tasks)}] {summary['label']} · "
                  + (f"✗ {summary['error']}" if summary.get("error") else
                     f"{counts} BỎ SÓT={summary.get('bo_sot')} · {summary.get('timing_ms')}"), flush=True)
    if manifest and summaries:
        index = manifest.parent / "compare_index.json"
        old = json.loads(index.read_text(encoding="utf-8")) if index.is_file() else {}
        old.update({s["label"]: s for s in summaries})
        _write_json(index, old)
        print(f"Xong {len(summaries)} hồ sơ trong {int(time.monotonic() - t0)} s · 📄 {index}")
    if args.file:
        paths = [Path(f).expanduser() for f in args.file]
        label = f"local_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        await _compare(label, args.procedure, paths, out_root / label, args.think)


if __name__ == "__main__":
    asyncio.run(main())
