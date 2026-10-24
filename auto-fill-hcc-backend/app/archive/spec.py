from __future__ import annotations

from typing import Any

from app.archive.keys import has_key, with_keys

_TRACE_FIELDS = ("applicant_name", "ocr_text", "llm_output", "report", "errors")
_ATTACHMENT_KEEP = ("sha256", "uses", "nk", "sk", "idd")

_LLM_KEEP = ("n", "t0", "purpose", "caller", "fn", "max_tokens", "thinking", "prompt_chars",
             "system_hash", "span", "think_chars", "ms", "tokens_in", "tokens_out",
             "finish_reason", "model", "target")
_OCR_KEEP = ("idx", "type", "sha256", "bytes", "cache", "reason", "pages", "chars", "provider")

_PREQ_FIELDS = ("options", "fields", "extracted")
_PREQ_FILE_KEEP = ("type", "role", "size", "sha256")

_DOSSIER_FIELDS = ("applicant_name", "portal_dossier_ref")


def _pick(item: Any, keys: tuple[str, ...]) -> Any:
    if not isinstance(item, dict):
        return item
    return {k: item[k] for k in keys if k in item}


def _present(doc: dict, keys: tuple[str, ...]) -> dict:
    return {k: doc[k] for k in keys if doc.get(k) not in (None, "", [], {})}


def split_trace(doc: dict) -> tuple[dict, dict, list[str]]:
    attachments = doc.get("attachments") or []
    if has_key() and any(isinstance(a, dict) and "nk" not in a for a in attachments):
        attachments = with_keys(attachments)
    payload = _present(doc, _TRACE_FIELDS)
    names = [{"name": a.get("name"), "role": a.get("role"), "sha256": a.get("sha256")}
             for a in attachments if isinstance(a, dict) and a.get("name")]
    if names:
        payload["attachments"] = names
    set_ = {"attachments": [_pick(a, _ATTACHMENT_KEEP) for a in attachments]}
    unset = [k for k in _TRACE_FIELDS if k in doc]
    return payload, set_, unset


def split_trace_steps(doc: dict) -> tuple[dict, dict, list[str]]:
    payload = _present(doc, ("outputs", "errors", "truncated"))
    llm = doc.get("llm")
    ocr = doc.get("ocr")
    spans = doc.get("spans")
    set_: dict = {}
    if isinstance(llm, list):
        payload["llm"] = llm
        set_["llm"] = [{**_pick(c, _LLM_KEEP),
                        **({"tries": [_pick(t, ("target", "ms", "ok")) for t in c.get("tries") or []]}
                           if isinstance(c, dict) and c.get("tries") else {})}
                       for c in llm]
    elif llm is not None:
        payload["llm"] = llm
        set_["llm"] = []
    if isinstance(ocr, list):
        payload["ocr"] = ocr
        set_["ocr"] = [_pick(o, _OCR_KEEP) for o in ocr]
    if isinstance(spans, list):
        payload["span_attrs"] = {str(s.get("i")): s.get("a") for s in spans
                                   if isinstance(s, dict) and s.get("a")}
        set_["spans"] = [{**{k: v for k, v in s.items() if k != "a"},
                          "a": {k: v for k, v in (s.get("a") or {}).items()
                                if isinstance(v, (int, float, bool)) and not isinstance(v, str)}}
                         if isinstance(s, dict) else s for s in spans]
    unset = [k for k in ("outputs", "errors", "truncated") if k in doc]
    if isinstance(doc.get("errors"), list):
        set_["errors_count"] = len(doc["errors"])
    return payload, set_, unset


def split_process_request(doc: dict) -> tuple[dict, dict, list[str]]:
    payload = _present(doc, _PREQ_FIELDS)
    files = doc.get("files") or []
    if files:
        payload["files"] = files
    set_ = {"files": [_pick(f, _PREQ_FILE_KEEP) for f in files]}
    unset = [k for k in _PREQ_FIELDS if k in doc]
    return payload, set_, unset


def split_dossier(doc: dict) -> tuple[dict, dict, list[str]]:
    payload = _present(doc, _DOSSIER_FIELDS)
    events = doc.get("submit_events") or []
    refs = [{"at": e.get("at"), "ref": e.get("ref")} for e in events if isinstance(e, dict) and e.get("ref")]
    if refs:
        payload["submit_refs"] = refs
    set_ = {"archive_pending": False}
    if refs:
        set_["submit_events"] = [{k: v for k, v in e.items() if k != "ref"} if isinstance(e, dict) else e
                                 for e in events]
    unset = [k for k in _DOSSIER_FIELDS if k in doc]
    return payload, set_, unset


def split_upload_log(doc: dict) -> tuple[dict, dict, list[str]]:
    events = doc.get("events") or []
    names = [{"i": i, "name": e.get("name"), "names": e.get("names")} for i, e in enumerate(events)
             if isinstance(e, dict) and (e.get("name") or e.get("names"))]
    payload = {"events": names} if names else {}
    set_ = {"events": [{k: v for k, v in e.items() if k not in ("name", "names")}
                       if isinstance(e, dict) else e for e in events]}
    return payload, set_, []


_PUBLIC_ATTACHMENT = ("sha256", "uses")


def public_trace(doc: dict) -> dict:
    out = {k: v for k, v in doc.items() if k not in _TRACE_FIELDS}
    if "attachments" in doc:
        out["attachments"] = [_pick(a, _PUBLIC_ATTACHMENT) for a in doc.get("attachments") or []]
    return out


def public_trace_steps(doc: dict) -> dict:
    _payload, set_, unset = split_trace_steps(doc)
    out = {k: v for k, v in doc.items() if k not in unset}
    out.update(set_)
    return out
