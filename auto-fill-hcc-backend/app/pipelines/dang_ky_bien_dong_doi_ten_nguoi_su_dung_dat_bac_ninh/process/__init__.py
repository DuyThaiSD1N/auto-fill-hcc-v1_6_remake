"""Process pipeline for [Bắc Ninh] Đăng ký biến động do đổi tên / thay đổi thông tin người sử dụng đất (1.115460)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_bac_ninh.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
