"""Lazy process entrypoint cho đăng ký khai tử lưu động (1.000419)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.khai_tu_luu_dong.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
