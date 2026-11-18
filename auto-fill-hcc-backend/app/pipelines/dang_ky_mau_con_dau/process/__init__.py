"""Process pipeline cho Đăng ký mẫu con dấu mới (2.001428)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_mau_con_dau.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
