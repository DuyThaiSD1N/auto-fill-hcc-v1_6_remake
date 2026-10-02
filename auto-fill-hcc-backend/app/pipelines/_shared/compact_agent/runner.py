"""Runner for compact agent output: OCR files -> compact fields -> validated UI fields."""

import base64
import hashlib
import io
import json
import mimetypes
import time
import zipfile
import xml.etree.ElementTree as ET

from app.config import settings
from app.monitor import recorder as mon
from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines._shared.documents import join_ocr_documents
from app.pipelines._shared.formatting import normalize_date
from app.services.llm import client

_COMPACT_AGENT_MAX_TOKENS = 1800
_DATE_COMPS = {"x-date", "x-date-text", "date"}
_DOCX_TYPES = {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
_DOCX_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def flatten(files_by_role: dict[str, list[dict]]) -> list[dict]:
    files: list[dict] = []
    for arr in files_by_role.values():
        files.extend(arr or [])
    return files


def _is_docx(file: dict) -> bool:
    name = str(file.get("name") or "").lower()
    return file.get("type") in _DOCX_TYPES or name.endswith(".docx")


def _decode_data_url(data_url: str) -> bytes:
    b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
    return base64.b64decode(b64)


_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _docx_para_text(paragraph) -> str:
    """Text của 1 đoạn <w:p>: nối các run <w:t>, đổi <w:tab> thành khoảng trắng."""
    parts: list[str] = []
    for node in paragraph.iter():
        tag = node.tag
        if tag == _W_NS + "t":
            parts.append(node.text or "")
        elif tag in (_W_NS + "tab", _W_NS + "br"):
            parts.append(" ")
    return " ".join("".join(parts).split()).strip()


def _docx_walk(container) -> list[str]:
    """Duyệt con trực tiếp của body/cell theo THỨ TỰ tài liệu, GIỮ cấu trúc bảng:
    - <w:p> → 1 dòng text.
    - <w:tbl> → mỗi <w:tr> thành 1 dòng, các ô <w:tc> nối bằng ' | ' (giữ ranh giới cột để LLM khớp
      đúng cột — vd 'Số khung' vs 'Số máy' trong bảng phương tiện, thay vì bị làm phẳng lẫn nhau)."""
    lines: list[str] = []
    for child in container:
        tag = child.tag
        if tag == _W_NS + "p":
            txt = _docx_para_text(child)
            if txt:
                lines.append(txt)
        elif tag == _W_NS + "tbl":
            for row in child.findall(_W_NS + "tr"):
                cells: list[str] = []
                for cell in row.findall(_W_NS + "tc"):
                    cells.append(" ".join(_docx_walk(cell)).strip())
                if any(c for c in cells):
                    lines.append(" | ".join(cells))
    return lines


def _extract_docx_text(file: dict) -> dict:
    # Dùng chung cho bước điền và 8 planner đính kèm: text DOCX không đi qua dịch vụ OCR nên
    # ghi vào Monitor ngay tại đây để bước nào cũng có "OCR text" của file DOCX.
    with mon.span("pre.docx", name=file.get("name")):
        item = _extract_docx_text_impl(file)
    rec = mon.current()
    if rec is not None:
        text = item.get("text") or ""
        rec.ocr_files.append({
            "idx": len(rec.ocr_files), "name": item.get("name"), "type": item.get("type"),
            "sha256": item.pop("_sha256", None), "cache": "docx", "reason": None, "pages": None,
            "chars": len(text), "provider": "docx", "error": item.get("error"), "text": text,
        })
    item.pop("_sha256", None)
    return item


def _extract_docx_text_impl(file: dict) -> dict:
    item = {"name": file.get("name"), "type": file.get("type"), "text": "", "provider": "docx"}
    try:
        raw = _decode_data_url(file.get("dataUrl") or "")
        if mon.current() is not None:
            item["_sha256"] = hashlib.sha256(raw).hexdigest()
        lines: list[str] = []
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            names = ["word/document.xml"]
            names.extend(n for n in zf.namelist() if n.startswith("word/header") or n.startswith("word/footer"))
            for name in names:
                if name not in zf.namelist():
                    continue
                root = ET.fromstring(zf.read(name))
                body = root.find(_W_NS + "body")
                lines.extend(_docx_walk(body if body is not None else root))
        item["text"] = "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        item["error"] = str(e)
    return item


def _extract_docx_images(file: dict) -> list[dict]:
    """Return embedded DOCX images as OCR-able virtual files."""
    try:
        raw = _decode_data_url(file.get("dataUrl") or "")
        out: list[dict] = []
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            for name in zf.namelist():
                if not name.startswith("word/media/"):
                    continue
                suffix = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
                if suffix not in _DOCX_IMAGE_EXTENSIONS:
                    continue
                data = zf.read(name)
                mime = mimetypes.guess_type(name)[0] or "image/jpeg"
                out.append({
                    "name": f"{file.get('name') or 'document.docx'}::{name.rsplit('/', 1)[-1]}",
                    "type": mime,
                    "dataUrl": "data:" + mime + ";base64," + base64.b64encode(data).decode("ascii"),
                    "_sourceDocxName": file.get("name"),
                })
        return out
    except Exception:  # noqa: BLE001
        return []


def validate(raw_fields, allowed: set[str], comp_by_name: dict[str, str],
             aliases: dict[str, list[str]] | None = None,
             dropped: list[dict] | None = None) -> list[dict]:
    """Accept compact {name: value}; keep array format compatibility during rollout.

    ``dropped`` (tuỳ chọn) nhận các field LLM trả nhưng bị loại, kèm lý do — cho web Monitor.
    """
    aliases = aliases or {}
    out: list[dict] = []
    seen: set[str] = set()

    if isinstance(raw_fields, dict):
        items = raw_fields.items()
    elif isinstance(raw_fields, list):
        items = []
        for f in raw_fields:
            if isinstance(f, dict):
                items.append((f.get("name"), f.get("value")))
    else:
        return out

    for name, value in items:
        if name not in allowed or name in seen:
            if dropped is not None:
                dropped.append({"name": name, "value": value,
                                "reason": "duplicate" if name in seen else "not_allowed"})
            continue
        if value in (None, "", {}, []):
            if dropped is not None:
                dropped.append({"name": name, "value": value, "reason": "empty"})
            continue
        comp = comp_by_name[name]
        if comp in _DATE_COMPS and isinstance(value, str):
            value = normalize_date(value)
        field = {"name": name, "comp": comp, "value": value}
        if name in aliases:
            field["aliases"] = aliases[name]
        out.append(field)
        seen.add(name)
    return out


async def run(
    files_by_role: dict[str, list[dict]],
    *,
    fields: list[dict],
    allowed: set[str],
    comp_by_name: dict[str, str],
    aliases: dict[str, list[str]] | None = None,
    extra_rules: str = "",
    compact_field_fallback=None,
    options: dict | None = None,
    context_builder=None,
    document_filter=None,
    max_tokens: int = _COMPACT_AGENT_MAX_TOKENS,
    system_prompt_builder=None,
    user_content_builder=None,
) -> dict:
    errors: list[str] = []
    files = flatten(files_by_role)

    from app.services import ocr

    t0 = time.monotonic()
    docx_files = [f for f in files if _is_docx(f)]
    regular_ocr_files = [f for f in files if not _is_docx(f)]
    docx_results_by_name = {r.get("name"): r for r in (_extract_docx_text(f) for f in docx_files)}
    docx_image_files: list[dict] = []
    if docx_files:
        with mon.span("pre.docx_images", files=len(docx_files)):
            for f in docx_files:
                docx_image_files.extend(_extract_docx_images(f))
    ocr_files = regular_ocr_files + docx_image_files
    ocr_results_raw = await ocr.ocr_per_file(ocr_files) if ocr_files else []
    regular_results = ocr_results_raw[:len(regular_ocr_files)]
    docx_image_results = ocr_results_raw[len(regular_ocr_files):]
    ocr_iter = iter(regular_results)
    docx_image_texts: dict[str, list[str]] = {}
    docx_image_errors: dict[str, list[str]] = {}
    docx_image_providers: dict[str, set[str]] = {}
    for f, r in zip(docx_image_files, docx_image_results):
        source = f.get("_sourceDocxName")
        if not source:
            continue
        if r.get("text"):
            docx_image_texts.setdefault(source, []).append(r["text"])
        if r.get("error"):
            docx_image_errors.setdefault(source, []).append(f"{r.get('name')}: {r['error']}")
        if r.get("provider"):
            docx_image_providers.setdefault(source, set()).add(r["provider"])
    ocr_results = []
    for f in files:
        if _is_docx(f):
            item = docx_results_by_name.get(f.get("name"), {
                "name": f.get("name"), "type": f.get("type"), "text": "", "provider": "docx",
            })
            image_text = "\n".join(docx_image_texts.get(f.get("name"), []))
            if image_text:
                item["text"] = "\n".join(t for t in (item.get("text"), image_text) if t).strip()
                providers = sorted(docx_image_providers.get(f.get("name"), []))
                item["provider"] = "docx+" + "+".join(providers) if providers else "docx"
            if docx_image_errors.get(f.get("name")):
                item["error"] = "; ".join([item.get("error") or "", *docx_image_errors[f.get("name")]]).strip("; ")
            ocr_results.append(item)
        else:
            ocr_results.append(next(ocr_iter))
    ocr_ms = int((time.monotonic() - t0) * 1000)

    documents = []
    for r in ocr_results:
        if r.get("error"):
            errors.append(f"OCR {r.get('name')}: {r['error']}")
        if r.get("text"):
            documents.append({"name": r.get("name"), "text": r["text"], "provider": r.get("provider")})

    # Giữ cách gom tổng quát vì DOCX có thể mang nhãn "docx+tiengnoi"; OCR ảnh/PDF là tiengnoi.
    _provs = {r.get("provider") for r in ocr_results if r.get("provider")}
    effective_provider = "both" if len(_provs) > 1 else (next(iter(_provs)) if _provs else None)

    # Pipeline có thể gạn tài liệu lạc thủ tục TRƯỚC khi gửi LLM (trace vẫn giữ đủ OCR). Lọc lỗi
    # hoặc lọc ra rỗng -> gửi đủ như cũ.
    llm_documents = documents
    if document_filter and documents:
        try:
            llm_documents = document_filter(documents) or documents
        except Exception as e:  # noqa: BLE001
            errors.append(f"filter: {e}")

    # Tầng suy luận (PA1): chốt vai trò từng người TRƯỚC khi trích, nối vào prompt trích xuất.
    # Lỗi/không suy được -> context rỗng, bước trích chạy như cũ.
    reasoning_context = ""
    if context_builder and llm_documents:
        try:
            # Phần tất định tính vào hậu xử lý; LLM gọi bên trong (3 thủ tục) tự tách thành llm.reason.
            async with mon.span("post.reason"):
                reasoning_context = await context_builder(llm_documents, options or {}) or ""
        except Exception as e:  # noqa: BLE001
            errors.append(f"reason: {e}")
        mon.output("reasoning_context", reasoning_context)

    result_fields: list[dict] = []
    llm_output: dict | None = None  # JSON thô LLM parse được (lưu trace).
    t1 = time.monotonic()
    if llm_documents:
        # Thủ tục có prompt nền riêng truyền builder của mình; mặc định là khung dùng chung.
        build_system = system_prompt_builder or compact_prompt.build_system_prompt
        user_content = (user_content_builder(llm_documents, options or {}) if user_content_builder
                        else compact_prompt.build_user_content(llm_documents))
        messages = [
            {"role": "system", "content": build_system(fields, extra_rules + reasoning_context)},
            {"role": "user", "content": user_content},
        ]
        try:
            raw = await client.chat(
                messages,
                max_tokens=max_tokens,
                enable_thinking=settings.agent_reasoning,
            )
            parsed = client.extract_json_block(raw)
            llm_output = parsed
            raw_fields = parsed.get("fields")
            if compact_field_fallback:
                with mon.span("post.fallback"):
                    raw_fields = compact_field_fallback(raw_fields, llm_documents)
            dropped: list[dict] | None = [] if mon.current() is not None else None
            with mon.span("post.validate") as vspan:
                result_fields = validate(raw_fields, allowed, comp_by_name, aliases, dropped=dropped)
            if dropped is not None:
                vspan.attrs["kept"] = len(result_fields)
                vspan.attrs["dropped"] = len(dropped)
                mon.output("validate_dropped", dropped)
                # Chụp chuỗi JSON (bất biến): mapper phía sau có thể sửa chính các dict này.
                mon.output("fields_after_validate",
                           json.dumps(result_fields, ensure_ascii=False, default=str))
        except Exception as e:  # noqa: BLE001
            errors.append(f"agent: {e}")
    llm_ms = int((time.monotonic() - t1) * 1000)
    # Mốc runner chung xong → phần còn lại tới khi pipeline package trả = hậu xử lý/mapper.
    mon.mark("agent_end")

    return {
        "fields": result_fields,
        "extracted": {"documents": [d["name"] for d in documents]},
        "errors": errors,
        # Trace: gộp OCR text mọi file thành 1 chuỗi (header tên file, ngăn bằng ---)
        # và JSON thô LLM trả về. Dùng cho màn trace, không ảnh hưởng response /process.
        "ocr_text": join_ocr_documents(documents),
        "ocr_provider": effective_provider,  # "tiengnoi" hoặc "docx+tiengnoi"
        "llm_output": llm_output,
        "reasoning_context": reasoning_context,
        "stats": {
            "ocr_latency_ms": ocr_ms,
            "llm_latency_ms": llm_ms,
            "total_latency_ms": ocr_ms + llm_ms,
        },
    }
