"""Xuất hồ sơ đã xử lý của một hoặc nhiều thủ tục thành một gói ZIP chia sẻ được.

Gói ZIP chỉ chứa file vật lý còn tồn tại trong ``STORAGE_DIR`` cùng hai manifest:
``tong_hop.xlsx`` cho người đọc và ``manifest.json`` cho máy xử lý. Mỗi hồ sơ nằm ở:

    ho_so/<thu-tuc>/<tinh>__<xa-phuong>__<request_id>/

Ví dụ:

    .venv/bin/python -m scripts.export_procedure_dossiers \
      --procedure dang-ky-khai-tu \
      --output exports/khai-tu.zip

    .venv/bin/python -m scripts.export_procedure_dossiers \
      --procedure dang-ky-khai-tu \
      --procedure khai-sinh-lien-thong \
      --from 01/08/2026 --to 31/08/2026 \
      --size-only

Mặc định chỉ lấy tài khoản HCC chính thức (role commune/province). Dùng
``--include-test-accounts`` khi thật sự cần xuất cả tài khoản user/test/admin.

Lưu ý nghiệp vụ: trace ``done`` chứng minh backend đã nhận và xử lý file thành công; nó không
phải bằng chứng hồ sơ đã được bấm Nộp thành công trên cổng dịch vụ công.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import unicodedata
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Sequence

from bson import ObjectId
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings  # noqa: E402
from app.procedures.registry import PROCEDURES  # noqa: E402
from app.users.roles import OFFICIAL_ACCOUNT_ROLES, normalized_role  # noqa: E402


VN_TZ = timezone(timedelta(hours=7))
_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_INVALID_PATH_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_CHUNK_SIZE = 1000


@dataclass
class ExportFile:
    original_name: str
    media_type: str
    role: str
    size: int
    sha256: str
    abs_path: Path
    archive_name: str = ""


@dataclass
class ExportDossier:
    request_id: str
    procedure: str
    procedure_label: str
    created_at: datetime | None
    user_id: str
    username: str
    unit_name: str
    province: str
    commune: str
    dossier_ids: list[str]
    files: list[ExportFile]
    fingerprint: str
    related_request_ids: list[str] = field(default_factory=list)
    related_procedures: list[str] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(item.size for item in self.files)


@dataclass
class ExcludedDossier:
    request_id: str
    procedure: str
    reason: str
    detail: str = ""
    canonical_request_id: str = ""


@dataclass
class ExportResult:
    dossiers: list[ExportDossier]
    excluded: list[ExcludedDossier]
    selected_trace_count: int

    @property
    def file_count(self) -> int:
        return sum(len(item.files) for item in self.dossiers)

    @property
    def logical_bytes(self) -> int:
        return sum(item.total_bytes for item in self.dossiers)

    @property
    def unique_content_bytes(self) -> int:
        by_hash: dict[str, int] = {}
        for dossier in self.dossiers:
            for item in dossier.files:
                by_hash.setdefault(item.sha256, item.size)
        return sum(by_hash.values())


def _parse_date(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    parsed = None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        raise argparse.ArgumentTypeError(
            f"Ngày không hợp lệ: {value!r}. Dùng YYYY-MM-DD hoặc DD/MM/YYYY."
        )
    parsed = parsed.replace(tzinfo=VN_TZ)
    if end_of_day:
        parsed = parsed + timedelta(days=1)
    return parsed.astimezone(timezone.utc)


def _safe_segment(value: object, *, fallback: str, limit: int = 100) -> str:
    """Tạo tên thư mục/file tương thích Windows nhưng giữ tiếng Việt dễ đọc."""
    text = unicodedata.normalize("NFC", str(value or "")).strip()
    text = _INVALID_PATH_CHARS_RE.sub("_", text)
    text = re.sub(r"\s+", " ", text).strip(" ._")
    return (text or fallback)[:limit].rstrip(" .") or fallback


def _format_bytes(value: int) -> str:
    size = float(max(value, 0))
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.2f} {unit}"
        size /= 1024
    return f"{value} B"


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bundle_fingerprint(files: Sequence[ExportFile]) -> str:
    """Nhận diện bộ file không phụ thuộc tên và thứ tự, nhưng giữ số lần xuất hiện."""
    hashes = sorted(item.sha256.lower() for item in files)
    payload = json.dumps(hashes, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(b"hcc-export-dossier-v1\0" + payload).hexdigest()


def _resolve_file(storage_root: Path, meta: dict) -> tuple[ExportFile | None, str]:
    rel_path = str(meta.get("path") or "").strip()
    if not rel_path:
        return None, "metadata không có path"

    candidate = (storage_root / rel_path).resolve()
    try:
        candidate.relative_to(storage_root)
    except ValueError:
        return None, "path nằm ngoài STORAGE_DIR"
    if not candidate.is_file():
        return None, "file vật lý không còn trên server"

    actual_size = candidate.stat().st_size
    if actual_size <= 0:
        return None, "file rỗng"

    stored_hash = str(meta.get("sha256") or "").strip().lower()
    sha256 = stored_hash if _HASH_RE.fullmatch(stored_hash) else _hash_file(candidate)
    return ExportFile(
        original_name=str(meta.get("name") or candidate.name),
        media_type=str(meta.get("type") or "application/octet-stream"),
        role=str(meta.get("role") or ""),
        size=actual_size,
        sha256=sha256,
        abs_path=candidate,
    ), ""


def _latest_requests(requests: Iterable[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for item in requests:
        request_id = str(item.get("request_id") or "").strip()
        if not request_id:
            continue
        previous = result.get(request_id)
        if previous is None or _document_time(item) > _document_time(previous):
            result[request_id] = item
    return result


def _document_time(document: dict) -> datetime:
    created = document.get("created_at")
    if not isinstance(created, datetime):
        return datetime.min.replace(tzinfo=timezone.utc)
    if created.tzinfo is None:
        return created.replace(tzinfo=timezone.utc)
    return created.astimezone(timezone.utc)


def _trace_sort_key(trace: dict) -> tuple[datetime, str]:
    return _document_time(trace), str(trace.get("request_id") or "")


def collect_export_records(
    *,
    traces: Sequence[dict],
    requests_by_id: dict[str, dict],
    users_by_id: dict[str, dict],
    storage_root: Path,
    official_only: bool = True,
) -> ExportResult:
    """Lọc file thật và gộp các lượt có cùng bộ nội dung file.

    Trace được duyệt từ mới đến cũ nên lượt mới nhất làm hồ sơ đại diện. Các request bị gộp
    vẫn được lưu trong manifest để đối soát, không bị mất dấu vết.
    """
    storage_root = storage_root.resolve()
    dossiers_by_fingerprint: dict[str, ExportDossier] = {}
    excluded: list[ExcludedDossier] = []

    for trace in sorted(traces, key=_trace_sort_key, reverse=True):
        request_id = str(trace.get("request_id") or "").strip()
        procedure = str(trace.get("procedure") or "").strip()
        if not request_id:
            excluded.append(ExcludedDossier("", procedure, "Thiếu mã hồ sơ"))
            continue
        if trace.get("status") != "done":
            excluded.append(ExcludedDossier(request_id, procedure, "Trace chưa hoàn tất"))
            continue

        user_id = str(trace.get("user_id") or "")
        user = users_by_id.get(user_id)
        if official_only and (
            not user or normalized_role(user.get("role")) not in OFFICIAL_ACCOUNT_ROLES
        ):
            excluded.append(
                ExcludedDossier(request_id, procedure, "Không phải tài khoản HCC chính thức")
            )
            continue

        request = requests_by_id.get(request_id)
        if not request:
            excluded.append(
                ExcludedDossier(request_id, procedure, "Không có bản ghi process_requests")
            )
            continue
        if str(request.get("user_id") or "") != user_id:
            excluded.append(
                ExcludedDossier(request_id, procedure, "Sai liên kết tài khoản giữa trace và request")
            )
            continue

        files_meta = request.get("files") or []
        if not files_meta:
            excluded.append(ExcludedDossier(request_id, procedure, "Không có file nguồn"))
            continue

        files: list[ExportFile] = []
        invalid_details: list[str] = []
        for index, meta in enumerate(files_meta, start=1):
            file_item, reason = _resolve_file(storage_root, meta)
            if file_item is None:
                invalid_details.append(f"file {index}: {reason}")
            else:
                files.append(file_item)
        if invalid_details:
            excluded.append(
                ExcludedDossier(
                    request_id,
                    procedure,
                    "Hồ sơ thiếu file hợp lệ",
                    "; ".join(invalid_details),
                )
            )
            continue

        fingerprint = _bundle_fingerprint(files)
        canonical = dossiers_by_fingerprint.get(fingerprint)
        if canonical:
            if request_id not in canonical.related_request_ids:
                canonical.related_request_ids.append(request_id)
            if procedure and procedure not in canonical.related_procedures:
                canonical.related_procedures.append(procedure)
            excluded.append(
                ExcludedDossier(
                    request_id,
                    procedure,
                    "Trùng toàn bộ nội dung file",
                    canonical_request_id=canonical.request_id,
                )
            )
            continue

        user = user or {}
        dossier = ExportDossier(
            request_id=request_id,
            procedure=procedure,
            procedure_label=str(trace.get("procedure_label") or procedure),
            created_at=trace.get("created_at") if isinstance(trace.get("created_at"), datetime) else None,
            user_id=user_id,
            username=str(user.get("username") or trace.get("username") or ""),
            unit_name=str(user.get("name") or trace.get("name") or ""),
            province=str(user.get("tinh") or ""),
            commune=str(user.get("xa") or ""),
            dossier_ids=[str(item) for item in (trace.get("dossier_ids") or []) if item],
            files=files,
            fingerprint=fingerprint,
            related_request_ids=[request_id],
            related_procedures=[procedure] if procedure else [],
        )
        dossiers_by_fingerprint[fingerprint] = dossier

    dossiers = sorted(
        dossiers_by_fingerprint.values(),
        key=lambda item: (item.procedure, item.province, item.commune, item.request_id),
    )
    return ExportResult(dossiers=dossiers, excluded=excluded, selected_trace_count=len(traces))


def _unique_archive_names(dossier: ExportDossier) -> None:
    used: Counter[str] = Counter()
    for index, item in enumerate(dossier.files, start=1):
        original = _safe_segment(item.original_name, fallback=f"file_{index}", limit=120)
        count = used[original]
        used[original] += 1
        if count:
            stem, suffix = os.path.splitext(original)
            original = f"{stem}_{count}{suffix}"
        item.archive_name = f"{index:02d}_{original}"


def _folder_for(dossier: ExportDossier) -> str:
    procedure = _safe_segment(dossier.procedure, fallback="khong-ro-thu-tuc", limit=100)
    province = _safe_segment(dossier.province, fallback="khong-ro-tinh", limit=70)
    commune = _safe_segment(
        dossier.commune or dossier.unit_name,
        fallback="khong-ro-xa-phuong",
        limit=70,
    )
    request_id = _safe_segment(dossier.request_id, fallback="khong-ro-ma", limit=60)
    # Ba cấp: ho_so / thủ tục / địa bàn + request_id.
    return f"ho_so/{procedure}/{province}__{commune}__{request_id}"


def _vn_time(value: datetime | None) -> str:
    if not isinstance(value, datetime):
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(VN_TZ).strftime("%d/%m/%Y %H:%M:%S")


def _manifest(result: ExportResult, procedures: Sequence[str]) -> dict:
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "timezone": "Asia/Ho_Chi_Minh",
        "procedures": list(procedures),
        "summary": {
            "selectedTraces": result.selected_trace_count,
            "exportedDossiers": len(result.dossiers),
            "exportedFiles": result.file_count,
            "excludedRecords": len(result.excluded),
            "logicalBytes": result.logical_bytes,
            "uniqueContentBytes": result.unique_content_bytes,
        },
        "dossiers": [
            {
                "requestId": dossier.request_id,
                "relatedRequestIds": dossier.related_request_ids,
                "dossierIds": dossier.dossier_ids,
                "procedure": dossier.procedure,
                "relatedProcedures": dossier.related_procedures,
                "procedureLabel": dossier.procedure_label,
                "createdAt": dossier.created_at.isoformat() if dossier.created_at else None,
                "province": dossier.province,
                "commune": dossier.commune,
                "unitName": dossier.unit_name,
                "username": dossier.username,
                "fileCount": len(dossier.files),
                "totalBytes": dossier.total_bytes,
                "fingerprint": dossier.fingerprint,
                "archiveFolder": _folder_for(dossier),
                "files": [
                    {
                        "originalName": item.original_name,
                        "archiveName": item.archive_name,
                        "mediaType": item.media_type,
                        "role": item.role,
                        "size": item.size,
                        "sha256": item.sha256,
                    }
                    for item in dossier.files
                ],
            }
            for dossier in result.dossiers
        ],
        "excluded": [
            {
                "requestId": item.request_id,
                "procedure": item.procedure,
                "reason": item.reason,
                "detail": item.detail,
                "canonicalRequestId": item.canonical_request_id,
            }
            for item in result.excluded
        ],
    }


def _style_sheet(ws, widths: Sequence[int]) -> None:
    header_fill = PatternFill("solid", fgColor="245A9C")
    header_font = Font(color="FFFFFF", bold=True)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for index, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(index)].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def _excel_bytes(result: ExportResult, procedures: Sequence[str]) -> bytes:
    wb = Workbook()
    summary = wb.active
    summary.title = "Tổng quan"
    summary.append(["Thông tin", "Giá trị"])
    summary_rows = [
        ("Thủ tục", "\n".join(procedures)),
        ("Số trace đã xét", result.selected_trace_count),
        ("Số hồ sơ xuất", len(result.dossiers)),
        ("Số file xuất", result.file_count),
        ("Số bản ghi loại bỏ", len(result.excluded)),
        ("Tổng dung lượng theo hồ sơ", result.logical_bytes),
        ("Tổng dung lượng theo hồ sơ (dễ đọc)", _format_bytes(result.logical_bytes)),
        ("Dung lượng nội dung file duy nhất", result.unique_content_bytes),
        ("Dung lượng nội dung duy nhất (dễ đọc)", _format_bytes(result.unique_content_bytes)),
        ("Thời gian xuất", _vn_time(datetime.now(timezone.utc))),
    ]
    for row in summary_rows:
        summary.append(row)
    _style_sheet(summary, [38, 90])

    dossiers_ws = wb.create_sheet("Hồ sơ")
    dossiers_ws.append([
        "Mã hồ sơ", "Các mã liên quan", "Dossier IDs", "Thủ tục", "Tên thủ tục",
        "Thời gian", "Tỉnh", "Xã/phường", "Đơn vị", "Tài khoản", "Số file",
        "Dung lượng (byte)", "Dung lượng", "Thư mục trong ZIP", "Fingerprint",
    ])
    for dossier in result.dossiers:
        dossiers_ws.append([
            dossier.request_id,
            ", ".join(dossier.related_request_ids),
            ", ".join(dossier.dossier_ids),
            ", ".join(dossier.related_procedures),
            dossier.procedure_label,
            _vn_time(dossier.created_at),
            dossier.province,
            dossier.commune,
            dossier.unit_name,
            dossier.username,
            len(dossier.files),
            dossier.total_bytes,
            _format_bytes(dossier.total_bytes),
            _folder_for(dossier),
            dossier.fingerprint,
        ])
    _style_sheet(dossiers_ws, [18, 30, 28, 30, 55, 20, 20, 24, 30, 20, 10, 18, 15, 60, 68])

    files_ws = wb.create_sheet("Tệp tin")
    files_ws.append([
        "Mã hồ sơ", "STT", "Tên file gốc", "Tên trong ZIP", "Loại file", "Vai trò",
        "Dung lượng (byte)", "Dung lượng", "SHA-256",
    ])
    for dossier in result.dossiers:
        for index, item in enumerate(dossier.files, start=1):
            files_ws.append([
                dossier.request_id,
                index,
                item.original_name,
                item.archive_name,
                item.media_type,
                item.role,
                item.size,
                _format_bytes(item.size),
                item.sha256,
            ])
    _style_sheet(files_ws, [18, 7, 45, 50, 28, 35, 18, 15, 68])

    excluded_ws = wb.create_sheet("Loại bỏ")
    excluded_ws.append(["Mã hồ sơ", "Thủ tục", "Lý do", "Chi tiết", "Mã hồ sơ giữ lại"])
    for item in result.excluded:
        excluded_ws.append([
            item.request_id,
            item.procedure,
            item.reason,
            item.detail,
            item.canonical_request_id,
        ])
    _style_sheet(excluded_ws, [18, 36, 36, 70, 20])

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _readme(result: ExportResult) -> str:
    return (
        "GÓI XUẤT HỒ SƠ AUTO FILL HCC\n"
        "\n"
        "- tong_hop.xlsx: danh sách hồ sơ, file và các bản ghi bị loại.\n"
        "- manifest.json: dữ liệu tương tự ở dạng máy đọc.\n"
        "- ho_so/: file gốc theo cấu trúc 3 cấp thủ tục / địa bàn + mã hồ sơ.\n"
        "\n"
        f"Hồ sơ đã xuất: {len(result.dossiers)}\n"
        f"File đã xuất: {result.file_count}\n"
        f"Tổng dung lượng theo hồ sơ: {_format_bytes(result.logical_bytes)}\n"
        f"Dung lượng nội dung duy nhất: {_format_bytes(result.unique_content_bytes)}\n"
        "\n"
        "Hồ sơ trùng được xác định theo toàn bộ SHA-256 nội dung file, không theo tên file.\n"
        "Gói này có dữ liệu cá nhân; chỉ chia sẻ qua kênh được đơn vị cho phép.\n"
        "Trace thành công không đồng nghĩa cổng dịch vụ công đã tiếp nhận/nộp hồ sơ thành công.\n"
    )


def write_zip(output_path: Path, result: ExportResult, procedures: Sequence[str]) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for dossier in result.dossiers:
        _unique_archive_names(dossier)

    manifest = _manifest(result, procedures)
    with zipfile.ZipFile(
        output_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
        allowZip64=True,
    ) as archive:
        archive.writestr("README.txt", _readme(result).encode("utf-8"))
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
        )
        archive.writestr("tong_hop.xlsx", _excel_bytes(result, procedures))
        for dossier in result.dossiers:
            folder = _folder_for(dossier)
            for item in dossier.files:
                archive.write(item.abs_path, arcname=f"{folder}/{item.archive_name}")
    return output_path.stat().st_size


def _chunks(values: Sequence[str], size: int = _CHUNK_SIZE) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield list(values[index:index + size])


def _load_documents(
    db,
    *,
    procedures: Sequence[str],
    date_from: datetime | None,
    date_to: datetime | None,
    kind: str | None = None,
) -> tuple[list[dict], dict[str, dict], dict[str, dict]]:
    trace_query: dict = {
        "procedure": {"$in": list(procedures)},
        "status": "done",
    }
    date_query: dict = {}
    if date_from:
        date_query["$gte"] = date_from
    if date_to:
        date_query["$lt"] = date_to
    if date_query:
        trace_query["created_at"] = date_query
    if kind:
        trace_query["kind"] = kind

    projection = {
        "request_id": 1,
        "user_id": 1,
        "username": 1,
        "name": 1,
        "procedure": 1,
        "procedure_label": 1,
        "dossier_ids": 1,
        "kind": 1,
        "status": 1,
        "created_at": 1,
    }
    traces = list(db.traces.find(trace_query, projection).sort("created_at", -1))

    request_ids = sorted({str(item.get("request_id")) for item in traces if item.get("request_id")})
    request_docs: list[dict] = []
    for batch in _chunks(request_ids):
        request_docs.extend(
            db.process_requests.find(
                {"request_id": {"$in": batch}},
                {"request_id": 1, "user_id": 1, "procedure": 1, "files": 1, "created_at": 1},
            )
        )
    requests_by_id = _latest_requests(request_docs)

    user_ids = sorted({str(item.get("user_id")) for item in traces if item.get("user_id")})
    object_ids: list[ObjectId] = []
    for user_id in user_ids:
        try:
            object_ids.append(ObjectId(user_id))
        except Exception:  # noqa: BLE001 - ID legacy sai định dạng sẽ bị loại có kiểm soát.
            continue
    users_by_id = {
        str(item["_id"]): item
        for item in db.users.find(
            {"_id": {"$in": object_ids}},
            {"username": 1, "name": 1, "tinh": 1, "xa": 1, "role": 1},
        )
    }
    return traces, requests_by_id, users_by_id


def _procedure_values(raw_values: Sequence[str]) -> list[str]:
    values: list[str] = []
    for raw in raw_values:
        for item in str(raw or "").split(","):
            item = item.strip()
            if item and item not in values:
                values.append(item)
    return values


def _print_summary(result: ExportResult, *, archive_bytes: int | None = None) -> None:
    reasons = Counter(item.reason for item in result.excluded)
    print(f"Trace đã xét: {result.selected_trace_count}")
    print(f"Hồ sơ thực tế, không trùng: {len(result.dossiers)}")
    print(f"File được xuất: {result.file_count}")
    print(f"Tổng dung lượng theo hồ sơ: {_format_bytes(result.logical_bytes)} ({result.logical_bytes} byte)")
    print(
        "Dung lượng nội dung file duy nhất: "
        f"{_format_bytes(result.unique_content_bytes)} ({result.unique_content_bytes} byte)"
    )
    if archive_bytes is not None:
        print(f"Dung lượng ZIP: {_format_bytes(archive_bytes)} ({archive_bytes} byte)")
    if reasons:
        print("Bản ghi bị loại:")
        for reason, count in sorted(reasons.items()):
            print(f"  - {reason}: {count}")


def _default_output() -> Path:
    stamp = datetime.now(VN_TZ).strftime("%Y%m%d_%H%M%S")
    return Path("exports") / f"ho_so_{stamp}.zip"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Xuất file thật của hồ sơ theo một hoặc nhiều thủ tục thành ZIP."
    )
    parser.add_argument(
        "--procedure",
        action="append",
        default=[],
        help="Key thủ tục; lặp nhiều lần hoặc phân tách bằng dấu phẩy.",
    )
    parser.add_argument("--from", dest="date_from", help="Từ ngày (giờ Việt Nam).")
    parser.add_argument("--to", dest="date_to", help="Đến hết ngày (giờ Việt Nam).")
    parser.add_argument("--output", type=Path, default=None, help="Đường dẫn ZIP đầu ra.")
    parser.add_argument(
        "--storage-dir",
        type=Path,
        default=None,
        help="Ghi đè STORAGE_DIR nếu chạy script ngoài thư mục backend.",
    )
    parser.add_argument(
        "--include-test-accounts",
        action="store_true",
        help="Lấy cả tài khoản không có role commune/province.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Chỉ kiểm tra, không tạo ZIP.")
    parser.add_argument(
        "--size-only",
        action="store_true",
        help="Chỉ tính số hồ sơ/file/dung lượng, không tạo ZIP.",
    )
    parser.add_argument("--force", action="store_true", help="Cho phép ghi đè ZIP đã tồn tại.")
    args = parser.parse_args(argv)
    args.procedures = _procedure_values(args.procedure)
    if not args.procedures:
        parser.error("Cần ít nhất một --procedure.")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    known = {str(item.get("key")) for item in PROCEDURES}
    unknown = [item for item in args.procedures if item not in known]
    if unknown:
        raise SystemExit(f"Thủ tục không tồn tại trong registry: {', '.join(unknown)}")

    try:
        date_from = _parse_date(args.date_from)
        date_to = _parse_date(args.date_to, end_of_day=True)
    except argparse.ArgumentTypeError as exc:
        raise SystemExit(str(exc)) from exc
    if date_from and date_to and date_from >= date_to:
        raise SystemExit("Khoảng ngày không hợp lệ: --from phải trước hoặc bằng --to.")

    storage_root = (args.storage_dir or Path(settings.storage_dir)).resolve()
    if not storage_root.is_dir():
        raise SystemExit(f"STORAGE_DIR không tồn tại: {storage_root}")

    client = MongoClient(settings.mongo_dsn)
    try:
        db = client[settings.mongo_db]
        traces, requests_by_id, users_by_id = _load_documents(
            db,
            procedures=args.procedures,
            date_from=date_from,
            date_to=date_to,
        )
        result = collect_export_records(
            traces=traces,
            requests_by_id=requests_by_id,
            users_by_id=users_by_id,
            storage_root=storage_root,
            official_only=not args.include_test_accounts,
        )
    finally:
        client.close()

    if args.dry_run or args.size_only:
        _print_summary(result)
        return 0

    output = args.output or _default_output()
    if output.exists() and not args.force:
        raise SystemExit(f"File đã tồn tại: {output}. Dùng --force nếu muốn ghi đè.")
    archive_bytes = write_zip(output, result, args.procedures)
    _print_summary(result, archive_bytes=archive_bytes)
    print(f"Đã xuất: {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
