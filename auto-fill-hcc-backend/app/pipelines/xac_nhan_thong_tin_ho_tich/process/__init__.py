"""Lazy process entrypoint for xac-nhan-thong-tin-ho-tich."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.xac_nhan_thong_tin_ho_tich.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
