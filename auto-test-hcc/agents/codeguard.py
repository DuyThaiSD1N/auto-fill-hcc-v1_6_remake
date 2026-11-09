"""Chốt chặn phần code: ảnh chụp trước khi sửa, giới hạn phạm vi, tạo patch, hoàn tác, quét dữ liệu thật.

Không dùng git ở đây: repo cấm tự ý dùng git để gộp/đẩy code, và người dùng hay commit giữa phiên nên
stash/checkout dễ đạp lên việc đang làm. Hoàn tác chỉ đụng đúng file agent đã Edit.

Mọi đường dẫn tính từ gốc repo, vì agent sửa được cả backend lẫn extension.
"""
from __future__ import annotations

import difflib
import hashlib
import re
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from config import REPO

BE_DIR = "auto-fill-hcc-backend"
EXT_DIR = "auto-fill-hcc-extension"
# Extension trợ lý: chỉ job "Thêm thủ tục mới" có bật đưa lên trợ lý mới được sửa.
TROLY_DIR = "tro-ly-nguoi-dan-extension-main"
BE_SCOPES = (f"{BE_DIR}/app", f"{BE_DIR}/tests")
FORBIDDEN = (
    f"{BE_DIR}/tests/conftest.py",  # bản BE dán đè sẽ ghi lại, và nó là chốt chặn mạng của cả bộ test
    f"{EXT_DIR}/api/config.js",  # đổi là extension trỏ sang server khác
    f"{EXT_DIR}/manifest.json",  # thêm quyền hay host là việc người phải quyết
    f"{TROLY_DIR}/api/config.js",
    f"{TROLY_DIR}/manifest.json",
)
# Bộ đọc form chính là thước đo kết quả: agent sửa được nó thì có thể làm phép chấm đạt giả.
FORBIDDEN_DIRS = (f"{EXT_DIR}/content/form-snapshot/", f"{EXT_DIR}/background/form-snapshot.js")
_SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "node_modules", ".git")


@dataclass
class Change:
    rel: str  # tương đối so với gốc repo, dùng dấu /
    before: bytes | None  # None = file agent tạo mới
    after: bytes | None  # None = file agent xoá


def to_rel(path: str) -> str | None:
    """Đường dẫn tool Edit báo → tương đối so với gốc repo. Ngoài repo trả None."""
    raw = Path(path)
    absolute = raw if raw.is_absolute() else REPO / raw
    try:
        return absolute.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return None


def in_scope(rel: str | None, extension: bool = True, troly: bool = False) -> bool:
    if not rel or rel in FORBIDDEN or rel.startswith(FORBIDDEN_DIRS):
        return False
    roots = (*BE_SCOPES, EXT_DIR) if extension else BE_SCOPES
    if troly:
        roots = (*roots, TROLY_DIR)
    return any(rel.startswith(f"{root}/") for root in roots)


def touches_backend(changes: list[Change]) -> bool:
    return any(c.rel.startswith(f"{BE_DIR}/") for c in changes)


def touches_backend_app(changes: list[Change]) -> bool:
    return any(c.rel.startswith(f"{BE_DIR}/app/") for c in changes)


def touches_extension(changes: list[Change]) -> bool:
    return any(c.rel.startswith(f"{EXT_DIR}/") for c in changes)


def touches_troly(changes: list[Change]) -> bool:
    return any(c.rel.startswith(f"{TROLY_DIR}/") for c in changes)


def sha(data: bytes | None) -> str | None:
    return None if data is None else hashlib.sha256(data).hexdigest()


_SCOPE_ROOTS = (*BE_SCOPES, EXT_DIR, TROLY_DIR)


def remove_created(target: Path) -> None:
    """Xoá file agent tạo, rồi dọn thư mục cha chỉ còn rỗng hoặc __pycache__ (test, build đã import thì có pycache).

    Không dọn thì thư mục pipeline rỗng nằm lại: job sau tưởng pipeline đã có. Dừng ở gốc phạm vi, không bao giờ xoá nó.
    """
    target.unlink(missing_ok=True)
    roots = {(REPO / root).resolve() for root in _SCOPE_ROOTS}
    folder = target.parent
    while True:
        resolved = folder.resolve()
        if resolved in roots or REPO.resolve() not in resolved.parents or not folder.is_dir():
            return
        if any(p.name != "__pycache__" for p in folder.iterdir()):
            return
        shutil.rmtree(folder, ignore_errors=True)
        folder = folder.parent


class Guard:
    def __init__(self, job_dir: Path, troly: bool = False):
        self.snapshot = job_dir / "snapshot"
        self.preimage = job_dir / "preimage"
        self.troly = troly

    @property
    def taken(self) -> bool:
        return self.snapshot.is_dir()

    def take(self) -> None:
        if self.taken:
            return
        for scope in (*BE_SCOPES, EXT_DIR, *((TROLY_DIR,) if self.troly else ())):
            if (REPO / scope).is_dir():
                shutil.copytree(REPO / scope, self.snapshot / scope, ignore=_SKIP)

    def changes(self, touched: list[str], extension: bool = True) -> tuple[list[Change], list[str]]:
        """(thay đổi trong phạm vi, đường dẫn agent chạm ngoài phạm vi)."""
        changes: list[Change] = []
        outside: list[str] = []
        for path in sorted(set(touched)):
            rel = to_rel(path)
            if not in_scope(rel, extension, self.troly):
                outside.append(path)
                continue
            old, new = self.snapshot / rel, REPO / rel
            before = old.read_bytes() if old.is_file() else None
            after = new.read_bytes() if new.is_file() else None
            if before != after:
                changes.append(Change(rel, before, after))
        return changes, outside

    def restore(self, changes: list[Change]) -> None:
        for change in changes:
            target = REPO / change.rel
            if change.before is None:
                remove_created(target)
            else:
                target.write_bytes(change.before)

    def keep_preimages(self, changes: list[Change]) -> list[dict]:
        """Lưu bản trước sửa của riêng các file đã đổi, để hoàn tác được sau khi job kết thúc."""
        records = []
        for change in changes:
            if change.before is not None:
                target = self.preimage / change.rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(change.before)
            records.append({"path": change.rel, "created": change.before is None, "afterSha": sha(change.after)})
        return records

    def discard_snapshot(self) -> None:
        shutil.rmtree(self.snapshot, ignore_errors=True)

    def revert(self, records: list[dict]) -> tuple[list[str], list[str]]:
        """Hoàn tác bản sửa đã giữ. File bị ai đó sửa tiếp sau đó thì không đè, trả về để báo."""
        reverted: list[str] = []
        skipped: list[str] = []
        for record in records:
            rel = record["path"]
            target = REPO / rel
            current = target.read_bytes() if target.is_file() else None
            if sha(current) != record.get("afterSha"):
                skipped.append(rel)
                continue
            if record.get("created"):
                remove_created(target)
            else:
                target.write_bytes((self.preimage / rel).read_bytes())
            reverted.append(rel)
        return reverted, skipped


def _lines(data: bytes | None) -> list[str]:
    return [] if data is None else data.decode("utf-8", errors="replace").splitlines(keepends=True)


def make_patch(changes: list[Change]) -> str:
    chunks: list[str] = []
    for change in changes:
        diff = difflib.unified_diff(
            _lines(change.before), _lines(change.after),
            fromfile=f"a/{change.rel}", tofile=f"b/{change.rel}", n=3,
        )
        chunks.extend(line if line.endswith("\n") else line + "\n" for line in diff)
    return "".join(chunks)


_NAME_FIELD = re.compile(r"ho.?ten|hoten|fullname|ten.?nguoi|name", re.IGNORECASE)
_ADDRESS_FIELD = re.compile(r"dia.?chi|address|thuong.?tru|tam.?tru|noi.?o", re.IGNORECASE)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip().casefold()


def private_terms(fields: list[dict], request_id: str) -> set[str]:
    """Chuỗi nhận diện được người thật trong hồ sơ: CCCD/SĐT, họ tên, địa chỉ, mã req."""
    terms = {_norm(request_id)} if request_id else set()
    for field in fields or []:
        value = field.get("value")
        if not isinstance(value, str):
            continue
        name = str(field.get("name") or "")
        digits = re.sub(r"\D", "", value)
        if len(digits) >= 9:
            terms.add(digits)
        if _NAME_FIELD.search(name) and len(value.split()) >= 2:
            terms.add(_norm(value))
        if _ADDRESS_FIELD.search(name) and len(value) >= 15:
            terms.add(_norm(value))
    return {t for t in terms if t}


def leaked_terms(patch: str, terms: set[str]) -> list[str]:
    """Dữ liệu thật lọt vào dòng thêm mới của patch. Quy tắc repo: không đưa dữ liệu thật vào code, test."""
    added = "\n".join(
        line[1:] for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++")
    )
    haystack = _norm(added)
    digits = re.sub(r"\D", "", added)
    return sorted(t for t in terms if t in haystack or (t.isdigit() and t in digits))
