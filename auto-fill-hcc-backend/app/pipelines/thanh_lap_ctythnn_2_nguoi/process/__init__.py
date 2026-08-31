"""Lazy process entrypoint for thanh-lap-cong-ty-tnhh-hai-thanh-vien."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.thanh_lap_ctythnn_2_nguoi.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
