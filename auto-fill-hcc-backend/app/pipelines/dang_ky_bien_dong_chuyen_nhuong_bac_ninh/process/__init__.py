"""Process pipeline for [Bắc Ninh] Đăng ký biến động QSDĐ (chuyển nhượng/thừa kế/tặng cho)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_bac_ninh.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
