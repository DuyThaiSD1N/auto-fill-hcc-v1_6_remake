from __future__ import annotations

import hashlib
import hmac
import re

from app.archive.config import archive_settings

KEY_PREFIX = "k:"
_ASCII_UPPER = re.compile(r"[A-Z]")
_TOKEN = re.compile(r"[^ \t\n\v\f\r]+")
_FILE_SUFFIX_RE = re.compile(r"\.[^./\\]+$")
_IDENTITY_RE = re.compile(
    r"cccd|căn\s*cước|can\s*cuoc|chứng\s*minh|chung\s*minh|"
    r"hộ\s*chiếu|ho\s*chieu|passport|giấy\s*tờ\s*tùy\s*thân",
    re.IGNORECASE,
)


def mongo_normalized_name(name: object) -> str:
    text = "" if name is None else str(name)
    text = _ASCII_UPPER.sub(lambda m: m.group(0).lower(), text)
    return " ".join(_TOKEN.findall(text))


def _hmac(value: str) -> str:
    digest = hmac.new(archive_settings.archive_hmac_key.encode("utf-8"), value.encode("utf-8"),
                      hashlib.sha256).hexdigest()
    return KEY_PREFIX + digest[:32]


def has_key() -> bool:
    return bool(archive_settings.archive_hmac_key)


def attachment_keys(name: object, role: object) -> dict:
    normalized = mongo_normalized_name(name)
    stem = _FILE_SUFFIX_RE.sub("", normalized)
    identity_text = f"{'' if name is None else name} {'' if role is None else role}"
    return {
        "nk": _hmac(normalized) if normalized else "",
        "sk": _hmac(stem) if stem else "",
        "idd": bool(_IDENTITY_RE.search(identity_text)),
    }


def with_keys(attachments: list[dict] | None) -> list[dict]:
    if not has_key():
        return list(attachments or [])
    out = []
    for item in attachments or []:
        if not isinstance(item, dict):
            out.append(item)
            continue
        out.append({**item, **attachment_keys(item.get("name"), item.get("role"))})
    return out
