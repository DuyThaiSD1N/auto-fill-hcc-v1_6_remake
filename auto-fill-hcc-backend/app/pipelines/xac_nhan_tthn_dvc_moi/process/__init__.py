"""Lazy process entrypoint for xac-nhan-tinh-trang-hon-nhan (Cổng DVC quốc gia mới)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.xac_nhan_tthn_dvc_moi.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
