"""Process pipeline cho Thu hồi chứng nhận đăng ký xe, biển số xe tại Cục (2.000311)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.thu_hoi_chung_nhan_dang_ky_bien_so_xe_tai_cuc.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
