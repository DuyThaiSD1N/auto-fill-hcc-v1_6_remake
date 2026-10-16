"""Process pipeline cho [Lào Cai] đăng ký biến động chuyển nhượng, thừa kế, tặng cho (1.013831)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_thua_ke_tang_cho_dvcqg_lao_cai.process.runner import (
        run as _run,
    )

    return await _run(files_by_role, options)


__all__ = ["run"]
