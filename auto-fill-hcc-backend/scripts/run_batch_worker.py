"""Chạy worker batch độc lập với Uvicorn.

    python -m scripts.run_batch_worker
"""
from __future__ import annotations

import asyncio
import logging
import signal

from app.batch.worker import run_worker
from app.db.mongo import close, connect


async def _main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    connect()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass
    try:
        await run_worker(stop)
    finally:
        close()


if __name__ == "__main__":
    asyncio.run(_main())
