"""Dựng metadata định danh hồ sơ/tài liệu cho trace thống kê.

Lượt thường giữ tiêu chí cũ theo tập tên file; lượt tách tab dùng ID nghiệp vụ. SHA-256 nhận diện
tài liệu dùng lại, không tham gia gom hồ sơ.
"""
from __future__ import annotations

import hashlib
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
    if not isinstance(raw, list) or not raw:
        raw = [item.get("fileIndex")]
    indexes: list[int] = []
    for value in raw:
        if isinstance(value, int) and 0 <= value < count and value not in indexes:
            indexes.append(value)
    return indexes


def _bundle_hash(indexes: list[int], files_meta: list[dict]) -> str | None:
    hashes = [str(files_meta[index].get("sha256") or "") for index in indexes]
    if not hashes or any(len(value) != 64 for value in hashes):
        return None
    if len(hashes) == 1:
        return hashes[0]
    # Một item FE có thể là PDF ghép từ nhiều file nguồn. Fingerprint bundle có thứ tự giúp
    # nhận đúng cùng một tài liệu ghép mà không phải dựng lại PDF chỉ để làm thống kê.
    try:
        payload = b"hcc-source-bundle-v1\0" + b"".join(bytes.fromhex(value) for value in hashes)
    except ValueError:
        return None
    return hashlib.sha256(payload).hexdigest()


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


def build_attach_trace_metadata(
    *,
    request_id: str,
    session_id: str | None,
    procedure: str,
    split: bool,
    plan: list[dict],
    files_meta: list[dict],
) -> tuple[list[dict], list[str]]:
    """Trả attachments có hash/uses và các dossier_id do một lượt plan tạo ra."""
    count = len(files_meta)
    attachments: list[dict] = []
    plan_items: list[tuple[dict, dict]] = []

    for item in plan:
        indexes = _source_indexes(item, count)
        if not indexes:
            continue
        primary = files_meta[indexes[0]]
        trace_item = {
            "name": item.get("fileName") or item.get("documentName") or primary.get("name") or "",
            "role": item.get("componentName") or item.get("documentName") or item.get("slotName") or "",
            "sha256": _bundle_hash(indexes, files_meta),
            "uses": 1,
        }
        attachments.append(trace_item)
        plan_items.append((item, trace_item))

    # Planner lỗi/kiểu cũ không có fileIndex: vẫn giữ trace tài liệu nguồn và ID hồ sơ chính xác.
    if not attachments:
        attachments = build_process_trace_attachments(files_meta)

    base_id = (session_id or "").strip() or request_id
    if not split:
        return attachments, [base_id]

    if procedure == "chung-thuc-chu-ky":
        primary_items = [(item, trace_item) for item, trace_item in plan_items if not _is_identity_item(item)]
        dossier_count = max(len(primary_items), 1)
        # STT2 được extension gắn lại vào từng tab chữ ký; phản ánh số lượt tài liệu
        # thực sự dùng.
        for item, trace_item in plan_items:
            if _is_identity_item(item):
                trace_item["uses"] = dossier_count
    else:
        # Chứng thực bản sao: mọi item của kế hoạch, kể cả CCCD, là một bản cần chứng thực.
        dossier_count = max(len(plan_items), len(attachments), 1)

    return attachments, [f"{base_id}:{index}" for index in range(1, dossier_count + 1)]
