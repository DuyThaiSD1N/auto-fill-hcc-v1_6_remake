"""Process pipeline cho [Lào Cai] thửa đất có diện tích tăng thêm do thay đổi ranh giới (1.115693)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi.process.runner import (
        run as _run,
    )

    return await _run(files_by_role, options)


__all__ = ["run"]
