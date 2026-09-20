"""Process pipeline cho [Lào Cai] Đăng ký biến động (1.115671)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_bien_dong_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
