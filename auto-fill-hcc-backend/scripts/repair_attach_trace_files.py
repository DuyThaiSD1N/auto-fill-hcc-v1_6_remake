"""Khôi phục metadata file GỐC cho các trace đính kèm đã lưu sai tên file kế hoạch.

Mặc định chỉ thống kê, không ghi Mongo:

    python -m scripts.repair_attach_trace_files
    python -m scripts.repair_attach_trace_files --apply

Có thể giới hạn một thủ tục:

    python -m scripts.repair_attach_trace_files --procedure trich-luc-ks --apply
"""
from __future__ import annotations

import argparse
import asyncio

from app.db.mongo import close, connect, get_db
from app.traces.metadata import build_attach_trace_metadata


def rebuild_attachments(trace: dict, request: dict) -> list[dict] | None:
    files_meta = request.get("files") or []
    if not files_meta:
        return None
    llm_output = trace.get("llm_output") or {}
    plan = llm_output.get("attachments") or []
    attachments, _ = build_attach_trace_metadata(
        request_id=str(trace.get("request_id") or ""),
        session_id=None,
        procedure=str(trace.get("procedure") or ""),
        split=trace.get("split") is True,
        plan=plan,
        files_meta=files_meta,
    )
    return attachments


async def repair(*, procedure: str | None, apply: bool) -> int:
    connect()
    try:
        db = get_db()
        query: dict = {"kind": "attach"}
        if procedure:
            query["procedure"] = procedure

        checked = changed = skipped = 0
        async for trace in db.traces.find(query):
            checked += 1
            request = await db.process_requests.find_one({"request_id": trace.get("request_id")})
            rebuilt = rebuild_attachments(trace, request or {})
            if rebuilt is None:
                skipped += 1
                continue
            if rebuilt == (trace.get("attachments") or []):
                continue
            changed += 1
            if apply:
                await db.traces.update_one(
                    {"_id": trace["_id"]},
                    {"$set": {"attachments": rebuilt, "trace_files_version": 2}},
                )

        print(f"Trace đính kèm đã kiểm tra: {checked}")
        print(f"Trace cần sửa: {changed}")
        print(f"Trace thiếu process_requests/files nên bỏ qua: {skipped}")
        print(
            "Đã cập nhật Mongo."
            if apply
            else "DRY RUN: chưa cập nhật. Thêm --apply để thực hiện."
        )
        return 0
    finally:
        close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--procedure", help="Chỉ sửa một procedure key")
    parser.add_argument("--apply", action="store_true", help="Thực sự cập nhật Mongo")
    args = parser.parse_args()
    return asyncio.run(repair(procedure=args.procedure, apply=args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
