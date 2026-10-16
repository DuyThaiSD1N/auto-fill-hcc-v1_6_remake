"""Process pipeline cho [Lào Cai] đăng ký biến động đổi tên, thay đổi thông tin người sử dụng đất (1.013833)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_lao_cai.process.runner import (
        run as _run,
    )

    return await _run(files_by_role, options)


__all__ = ["run"]
