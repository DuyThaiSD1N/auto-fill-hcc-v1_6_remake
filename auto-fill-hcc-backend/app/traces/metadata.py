"""Dựng metadata định danh hồ sơ/tài liệu cho trace thống kê.

Lượt tách tab dùng ID nghiệp vụ. Lượt thường được repo thống kê theo tập tên file;
SHA-256 chỉ phục vụ thống kê tài liệu dùng lại, không tham gia gom hồ sơ.
"""
from __future__ import annotations

import unicodedata


_IDENTITY_HINTS = (
    "can cuoc", "cccd", "chung minh nhan dan", "cmnd",
    "ho chieu", "passport", "giay thong hanh", "giay to tuy than",
)


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower()).replace("đ", "d")
    return "".join(char for char in text if not unicodedata.combining(char))


def normalized_attachment_name_set(attachments: list[dict] | None) -> frozenset[str]:
    """Tập tên file theo tiêu chí thống kê cũ: lowercase và gộp khoảng trắng."""
    return frozenset(
        " ".join(str(item.get("name") or "").split()).lower()
        for item in (attachments or [])
        if item and item.get("name")
    )


def count_distinct_attachment_sets(file_sets: list[frozenset[str]]) -> int:
    """Đếm hồ sơ theo tiêu chí cũ, nhưng chỉ so sánh các tập file duy nhất.

    Hai lượt thuộc cùng hồ sơ nếu tập file của một lượt là tập con của lượt kia.
    Quan hệ được nối bắc cầu. Tập rỗng không tự gộp với bất kỳ lượt nào.
    """
    non_empty_sets = list(dict.fromkeys(item for item in file_sets if item))
    empty_count = sum(1 for item in file_sets if not item)
    parent = list(range(len(non_empty_sets)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for left_index, left in enumerate(non_empty_sets):
        for right_index in range(left_index + 1, len(non_empty_sets)):
            right = non_empty_sets[right_index]
            if left <= right or right <= left:
                parent[find(left_index)] = find(right_index)

    components = len({find(index) for index in range(len(non_empty_sets))})
    return components + empty_count


def _source_indexes(item: dict, count: int) -> list[int]:
    raw = item.get("sourceFileIndexes")
    if (not isinstance(raw, list) or not raw) and isinstance(item.get("sourceSegments"), list):
        # Tài liệu được dựng từ các đoạn trang vẫn phải truy được đầy đủ file gốc trong trace.
        raw = [segment.get("fileIndex") for segment in item["sourceSegments"] if isinstance(segment, dict)]
    if not isinstance(raw, list) or not raw:
        raw = [item.get("fileIndex")]
    indexes: list[int] = []
    for value in raw:
        if isinstance(value, int) and 0 <= value < count and value not in indexes:
            indexes.append(value)
    return indexes


def _is_identity_item(item: dict) -> bool:
    haystack = _fold(" ".join(str(item.get(key) or "") for key in (
        "fileName", "documentName", "componentName", "detectedType", "slotName",
    )))
    return any(hint in haystack for hint in _IDENTITY_HINTS)


def legacy_dossier_count(*, attachments: list[dict], procedure: str, split: bool) -> int:
    """Fallback tuyến tính cho trace v1; kết quả luôn được gắn nhãn ước tính."""
    if not split:
        return 1
    if procedure == "chung-thuc-chu-ky":
        return max(sum(1 for item in attachments or [] if not _is_identity_item(item)), 1)
    return max(len(attachments or []), 1)


def build_process_trace_attachments(files_meta: list[dict]) -> list[dict]:
    return [
        {
            "name": item.get("name") or "",
            "role": item.get("role") or "",
            "sha256": item.get("sha256"),
            "uses": 1,
        }
        for item in files_meta
    ]


def build_attach_trace_attachments(plan: list[dict], files_meta: list[dict]) -> list[dict]:
    """Metadata trace kiểu Handfree: giữ file gốc và bổ sung vai trò từ attach plan.

    Auto Fill vẫn dùng ``build_attach_trace_metadata`` để tính dossier id. Hàm nhỏ này
    chỉ là adapter cho channel sidebar, nơi mỗi lượt attach được ghi thành một trace.
    """
    attachments = [
        {
            "name": item.get("name") or "",
            "role": item.get("role") or "",
            "sha256": item.get("sha256"),
            "uses": 1,
        }
        for item in files_meta
    ]
    roles_by_index: list[list[str]] = [[] for _ in files_meta]
    for fallback_index, item in enumerate(plan or []):
        role = str(
            item.get("componentName")
            or item.get("documentName")
            or item.get("slotName")
            or ""
        ).strip()
        if not role:
            continue
        indexes = _source_indexes(item, len(files_meta))
        if not indexes and 0 <= fallback_index < len(files_meta):
            indexes = [fallback_index]
        for index in indexes:
            if role not in roles_by_index[index]:
                roles_by_index[index].append(role)

    for index, roles in enumerate(roles_by_index):
        if roles:
            attachments[index]["role"] = " · ".join(roles)
    return attachments


def build_attach_trace_metadata(
    *,
    request_id: str,
    session_id: str | None,
    procedure: str,
    split: bool,
    plan: list[dict],
    files_meta: list[dict],
) -> tuple[list[dict], list[str]]:
    """Trả metadata file GỐC và các dossier_id do một lượt plan tạo ra.

    ``plan.fileName`` có thể là tên PDF FE sẽ tạo sau khi tách/gộp. Trace phải giữ đúng
    ``files_meta`` theo thứ tự upload để tên, số file và endpoint ``/files/{index}`` cùng
    trỏ vào một tài liệu; kế hoạch đã được lưu riêng trong ``llm_output.attachments``.
    """
    count = len(files_meta)
    attachments = build_process_trace_attachments(files_meta)
    plan_items: list[tuple[dict, list[int]]] = []
    roles_by_index: list[list[str]] = [[] for _ in files_meta]

    for item in plan:
        indexes = _source_indexes(item, count)
        if not indexes:
            continue
        plan_items.append((item, indexes))
        role = str(
            item.get("componentName") or item.get("documentName") or item.get("slotName") or ""
        ).strip()
        if role:
            for index in indexes:
                if role not in roles_by_index[index]:
                    roles_by_index[index].append(role)

    for index, roles in enumerate(roles_by_index):
        if roles:
            attachments[index]["role"] = " · ".join(roles)

    base_id = (session_id or "").strip() or request_id
    if not split:
        return attachments, [base_id]

    if procedure == "chung-thuc-chu-ky":
        primary_items = [
            (item, indexes) for item, indexes in plan_items if not _is_identity_item(item)
        ]
        dossier_count = max(len(primary_items), 1)
        # STT2 được extension gắn lại vào từng tab chữ ký; phản ánh số lượt tài liệu
        # thực sự dùng.
        for item, indexes in plan_items:
            if _is_identity_item(item):
                for index in indexes:
                    attachments[index]["uses"] = dossier_count
    else:
        # Chứng thực bản sao: mọi item của kế hoạch, kể cả CCCD, là một bản cần chứng thực.
        dossier_count = max(len(plan_items), len(attachments), 1)
        # Một file gốc có thể được tách thành nhiều tài liệu/tab. Vẫn chỉ hiển thị một file
        # nguồn trong trace nhưng ghi đúng số lần nội dung đó được sử dụng.
        uses_by_index = [0 for _ in files_meta]
        for _item, indexes in plan_items:
            for index in indexes:
                uses_by_index[index] += 1
        for index, uses in enumerate(uses_by_index):
            attachments[index]["uses"] = max(uses, 1)

    return attachments, [f"{base_id}:{index}" for index in range(1, dossier_count + 1)]
