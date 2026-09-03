"""Xuất một ``request_id`` đại diện cho mỗi bộ hồ sơ thành JSON.

Script dùng đúng bộ lọc và cách nhận diện hồ sơ trùng của
``export_procedure_dossiers.py`` nhưng không tạo ZIP và không sao chép file nguồn.
Nếu nhiều request có cùng toàn bộ nội dung file, request mới nhất được giữ lại.

Ví dụ:

    .venv/bin/python -m scripts.export_procedure_request_ids \
      --procedure khai-tu \
      --from 01/08/2026 --to 31/08/2026

Có thể dùng ``--limit 200`` thay cho khoảng ngày. Khi đó số hồ sơ được chia đều
theo các tài khoản HCC thực tế có hồ sơ; tài khoản không đủ quota sẽ nhường phần
còn thiếu cho các tài khoản còn hồ sơ.

Đầu ra mặc định: ``exports/request_ids_<thời-gian>.json`` với nội dung:

    [
      "req_abc123",
      "req_def456"
    ]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict, deque
from typing import Sequence

from pymongo import MongoClient

from app.config import settings
from app.procedures.registry import PROCEDURES
from scripts.export_procedure_dossiers import (
    VN_TZ,
    ExportResult,
    ExportDossier,
    _load_documents,
    _parse_date,
    _procedure_values,
    collect_export_records,
)


def request_ids_from_result(result: ExportResult) -> list[str]:
    """Mỗi hồ sơ đã khử trùng chỉ lấy request đại diện mới nhất."""
    return [dossier.request_id for dossier in result.dossiers]


def select_balanced_dossiers(
    dossiers: Sequence[ExportDossier],
    limit: int | None,
) -> list[ExportDossier]:
    """Chia vòng tròn theo tài khoản, ưu tiên hồ sơ mới nhất trong từng tài khoản.

    Chỉ tạo bucket cho tài khoản thực sự có hồ sơ. Khi một bucket hết, các lượt sau
    tự đi qua tài khoản đó nên phần thiếu được phân phối cho những bucket còn lại.
    """
    if limit is None:
        return list(dossiers)

    buckets: dict[str, list[ExportDossier]] = defaultdict(list)
    for dossier in dossiers:
        account_key = dossier.user_id or dossier.username or "khong-ro-tai-khoan"
        buckets[account_key].append(dossier)

    for account_dossiers in buckets.values():
        account_dossiers.sort(
            key=lambda item: (
                item.created_at.timestamp() if item.created_at else float("-inf"),
                item.request_id,
            ),
            reverse=True,
        )

    # Thứ tự ổn định giúp cùng một snapshot dữ liệu luôn xuất cùng kết quả.
    account_order = sorted(
        buckets,
        key=lambda key: (
            (buckets[key][0].username or buckets[key][0].unit_name or key).casefold(),
            key,
        ),
    )
    queues = {key: deque(buckets[key]) for key in account_order}
    selected: list[ExportDossier] = []
    target = min(limit, len(dossiers))
    while len(selected) < target:
        progressed = False
        for key in account_order:
            if not queues[key]:
                continue
            selected.append(queues[key].popleft())
            progressed = True
            if len(selected) >= target:
                break
        if not progressed:
            break
    return selected


def _print_distribution(dossiers: Sequence[ExportDossier]) -> None:
    counts = Counter(dossier.user_id or dossier.username for dossier in dossiers)
    representatives: dict[str, ExportDossier] = {}
    for dossier in dossiers:
        representatives.setdefault(dossier.user_id or dossier.username, dossier)
    if not counts:
        return
    print("Phân bổ theo tài khoản:")
    for account_key, count in sorted(
        counts.items(),
        key=lambda item: (
            (representatives[item[0]].username or representatives[item[0]].unit_name).casefold(),
            item[0],
        ),
    ):
        dossier = representatives[account_key]
        label = dossier.username or dossier.unit_name or account_key
        print(f"  - {label}: {count}")


def write_request_ids(output_path: Path, request_ids: Sequence[str]) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(list(request_ids), ensure_ascii=False, indent=2) + "\n"
    output_path.write_text(content, encoding="utf-8")
    return output_path.stat().st_size


def _default_output() -> Path:
    stamp = datetime.now(VN_TZ).strftime("%Y%m%d_%H%M%S")
    return Path("exports") / f"request_ids_{stamp}.json"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Xuất một request_id đại diện cho mỗi bộ hồ sơ thành JSON."
    )
    parser.add_argument(
        "--procedure",
        action="append",
        default=[],
        help="Key thủ tục; lặp nhiều lần hoặc phân tách bằng dấu phẩy.",
    )
    parser.add_argument("--from", dest="date_from", help="Từ ngày (giờ Việt Nam).")
    parser.add_argument("--to", dest="date_to", help="Đến hết ngày (giờ Việt Nam).")
    parser.add_argument(
        "--limit", "--quantity", "--so-luong",
        dest="limit",
        type=int,
        default=None,
        help="Tổng số hồ sơ cần lấy, chia đều theo tài khoản HCC; dùng thay cho --from/--to.",
    )
    parser.add_argument("--output", type=Path, default=None, help="Đường dẫn JSON đầu ra.")
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
    parser.add_argument("--force", action="store_true", help="Cho phép ghi đè JSON đã tồn tại.")
    args = parser.parse_args(argv)
    args.procedures = _procedure_values(args.procedure)
    if not args.procedures:
        parser.error("Cần ít nhất một --procedure.")
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit phải lớn hơn 0.")
    if args.limit is not None and (args.date_from or args.date_to):
        parser.error("--limit dùng thay cho khoảng ngày; không nhập cùng --from/--to.")
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
            kind="autofill",
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

    selected_dossiers = select_balanced_dossiers(result.dossiers, args.limit)
    selected_result = ExportResult(
        dossiers=selected_dossiers,
        excluded=result.excluded,
        selected_trace_count=result.selected_trace_count,
    )
    request_ids = request_ids_from_result(selected_result)
    output = args.output or _default_output()
    if output.exists() and not args.force:
        raise SystemExit(f"File đã tồn tại: {output}. Dùng --force nếu muốn ghi đè.")
    output_bytes = write_request_ids(output, request_ids)

    print(f"Trace đã xét: {result.selected_trace_count}")
    print(f"Hồ sơ thực tế, không trùng: {len(request_ids)}")
    print(f"Request ID đã xuất: {len(request_ids)}")
    _print_distribution(selected_dossiers)
    print(f"Dung lượng JSON: {output_bytes} byte")
    print(f"Đã xuất: {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
