"""Lazy process entrypoint cho đăng ký khai tử có yếu tố nước ngoài (1.001766)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.khai_tu_nuoc_ngoai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
