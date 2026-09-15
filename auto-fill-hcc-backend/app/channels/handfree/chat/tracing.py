"""Ghi vết lượt điền/đính kèm của KÊNH SIDEBAR vào traces + process_requests.

Sidebar đăng nhập tài khoản quầy/kiosk → user_id/username lấy từ conv["auth_user"]
(ghi lúc tạo conversation); phiên cũ chưa có thì fallback nặc danh "citizen"/"sidebar".
Cột `name` dùng tên tài khoản đăng nhập giống Auto Fill. Không lấy conv.location vì
đó là nơi công dân chọn làm thủ tục và có thể khác đơn vị của tài khoản đang thao tác.
Phiên cũ chưa có auth_user mới fallback về địa điểm của phiên để không mất nhãn.

Ảnh giấy tờ lưu qua save_request_files + bản ghi process_requests — CÙNG NGUỒN với
nút xem file/tải ZIP của trang quản lý (traces router đọc theo request_id). Phạm vi
lưu trữ này đã ghi trong nội dung chấp thuận v1.1; nút "Xóa dữ liệu" của người dân
xoá phiên upload/hồ sơ đã lưu, KHÔNG xoá bản lưu đối soát.

Mọi hàm đều best-effort: lỗi ghi vết không được chặn luồng điền của công dân.
"""
import logging
from datetime import datetime, timezone

from app.process import requests_repo
from app.process.schemas import FileItem
from app.services import ocr
from app.storage.files import save_request_files
from app.traces import repo as traces_repo
from app.traces.applicant import resolve_applicant_name
from app.traces.key_fields import count_key_fields
from app.traces.metadata import build_attach_trace_attachments

logger = logging.getLogger(__name__)

_CITIZEN_USER = "citizen"  # kênh sidebar không có tài khoản — cột user cố định


def _identity(conv: dict) -> tuple[str, str]:
    au = conv.get("auth_user") or {}
    return str(au.get("id") or _CITIZEN_USER), str(au.get("username") or "sidebar")


def _location_name(conv: dict) -> str:
    loc = conv.get("location") or {}
    return ", ".join(x for x in (loc.get("ward"), loc.get("province")) if x) or "Người dân"


def _account_name(conv: dict) -> str:
    """Tên hiển thị của tài khoản, cùng nguồn với trace Auto Fill.

    `username` là fallback có chủ đích: nếu tài khoản cũ chưa có `name`, bảng trace
    vẫn chỉ ra đúng tài khoản thay vì gán nhầm địa điểm công dân chọn trong phiên.
    """
    auth_user = conv.get("auth_user") or {}
    return str(auth_user.get("name") or auth_user.get("username") or "").strip() or _location_name(conv)


def _ocr_label() -> str:
    return ocr.resolved_label()


async def _save_request(request_id: str, created_at: datetime, conv: dict,
                        procedure_key: str, files: list[dict]) -> tuple[str | None, list[dict]]:
    """Lưu ảnh xuống disk + bản ghi process_requests (nguồn xem file/ZIP của trang quản lý)."""
    files_meta = save_request_files(request_id, created_at, [FileItem(**f) for f in files])
    doc_id = await requests_repo.create_request(
        request_id=request_id, created_at=created_at, user_id=_identity(conv)[0],
        procedure=procedure_key,
        options={"channel": "sidebar", "conversation_id": conv.get("_id"),
                 "upload_session_id": conv.get("upload_session_id"),
                 "consent_id": (conv.get("consent") or {}).get("id")},
        files_meta=files_meta, experience="handfree",
    )
    return doc_id, files_meta


async def record_process(
    conv: dict,
    procedure_key: str,
    proc: dict,
    files: list[dict],
    result: dict,
    pipe_ms: int,
) -> str | None:
    """Trace kind=autofill sau khi pipeline trích field xong. Trả request_id để flow
    cập nhật kết quả điền THẬT (fill_report) vào đúng trace."""
    try:
        stats = dict(result.get("stats") or {})
        stats.setdefault("total_latency_ms", pipe_ms)

        kf_total, kf_filled = count_key_fields(procedure_key, result.get("fields", []))
        uid, uname = _identity(conv)
        request_id = traces_repo.new_request_id()
        created_at = datetime.now(timezone.utc)

        doc_id, _files_meta = await _save_request(
            request_id, created_at, conv, procedure_key, files
        )
        await requests_repo.finish_request(
            doc_id, status="done", stats=stats,
            fields_count=len(result.get("fields", [])),
            fields=result.get("fields", []), extracted=result.get("extracted", {}),
        )

        await traces_repo.create_trace(
            request_id=request_id, user_id=uid, username=uname,
            name=_account_name(conv),
            applicant_name=resolve_applicant_name({}, result),
            attachments=[{"name": f.get("name", ""), "role": ""} for f in files],
            kind="autofill", key_fields_total=kf_total, key_fields_filled=kf_filled,
            procedure=procedure_key, procedure_label=proc.get("label"),
            ocr_provider=result.get("ocr_provider") or _ocr_label(),
            ocr_text=result.get("ocr_text", ""), llm_output=result.get("llm_output"),
            fields_count=len(result.get("fields", [])), status="done",
            stats=stats, created_at=created_at, experience="handfree",
            dossier_id=conv.get("_id"),  # 1 conversation = 1 hồ sơ (khóa chung 2 kênh)
        )
        return request_id
    except Exception as e:  # noqa: BLE001 — ghi vết là phụ, không chặn luồng điền
        logger.warning("[tracing] ghi trace process lỗi (%s): %s", conv.get("_id"), e)
        return None


async def record_attach(conv: dict, procedure_key: str, proc: dict, files: list[dict],
                        result: dict, split: bool | None = None) -> str | None:
    """Trace kind=attach sau khi lập xong kế hoạch đính kèm (mỗi file → ô/component đích)."""
    try:
        request_id = traces_repo.new_request_id()
        created_at = datetime.now(timezone.utc)
        stats = dict(result.get("stats") or {}) or None
        doc_id, files_meta = await _save_request(
            request_id, created_at, conv, procedure_key, files
        )
        plan = result.get("attachments") or []
        await requests_repo.finish_request(doc_id, status="done",
                                           stats=stats,
                                           fields_count=len(plan),
                                           extracted=result.get("extracted", {}))
        attachments = build_attach_trace_attachments(plan, files_meta)
        uid, uname = _identity(conv)
        await traces_repo.create_trace(
            request_id=request_id, user_id=uid, username=uname,
            name=_account_name(conv),
            applicant_name=resolve_applicant_name({}, result),
            attachments=attachments, kind="attach",
            procedure=procedure_key, procedure_label=proc.get("label"),
            # Pipeline đính kèm có thể ép provider riêng hoặc fallback theo từng file;
            # dùng engine thực tế pipeline báo về thay vì cấu hình OCR chung của sidebar.
            ocr_provider=result.get("ocr_provider") or _ocr_label(),
            ocr_text=result.get("ocr_text", ""),
            llm_output={"classification": result.get("llm_output"),
                        "attachments": plan, "extracted": result.get("extracted")},
            fields_count=len(plan), status="done", stats=stats, split=split,
            created_at=created_at, experience="handfree",
            dossier_id=conv.get("_id"),  # 1 conversation = 1 hồ sơ (khóa chung 2 kênh)
        )
        return request_id
    except Exception as e:  # noqa: BLE001
        logger.warning("[tracing] ghi trace attach lỗi (%s): %s", conv.get("_id"), e)
        return None


async def record_error(conv: dict, procedure_key: str, kind: str, error: str) -> None:
    """Lượt hỏng cũng lên bảng (status=error) — dashboard thấy được tỉ lệ lỗi thật."""
    try:
        error_code = str(error)[:200]
        proc_label = (conv.get("procedure_key") or procedure_key)
        uid, uname = _identity(conv)
        await traces_repo.create_trace(
            request_id=traces_repo.new_request_id(), user_id=uid, username=uname,
            name=_account_name(conv), kind=kind,
            procedure=procedure_key, procedure_label=proc_label,
            ocr_provider=_ocr_label(), ocr_text="", llm_output=None,
            fields_count=0, status="error", error_code=error_code,
            created_at=datetime.now(timezone.utc), experience="handfree",
            dossier_id=conv.get("_id"),  # 1 conversation = 1 hồ sơ (khóa chung 2 kênh)
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("[tracing] ghi trace lỗi-của-lỗi (%s): %s", conv.get("_id"), e)


async def set_report(request_id: str | None, kind: str, report: dict) -> None:
    """FE báo kết quả THẬT trên form (fill_report/attach_report) → gắn vào trace.

    Khác auto-fill: bên đó chỉ biết số field TRÍCH được; sidebar biết cả số ô ĐIỀN thật."""
    if not request_id:
        return
    try:
        await traces_repo.set_report(request_id, kind, report)
    except Exception as e:  # noqa: BLE001
        logger.warning("[tracing] set_report lỗi (%s): %s", request_id, e)
