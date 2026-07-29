"""Process bước 2 cho thủ tục đăng ký khai sinh thường."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.khai_sinh_thuong.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
