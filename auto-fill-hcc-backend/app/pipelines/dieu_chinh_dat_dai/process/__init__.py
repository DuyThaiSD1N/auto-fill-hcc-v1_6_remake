"""Process pipeline for Điều chỉnh đất đai."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dieu_chinh_dat_dai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
