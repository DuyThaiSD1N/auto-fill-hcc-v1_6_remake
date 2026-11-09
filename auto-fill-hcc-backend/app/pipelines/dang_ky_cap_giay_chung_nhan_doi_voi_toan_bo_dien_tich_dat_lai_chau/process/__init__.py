"""Process pipeline cho Đăng ký, cấp GCN đối với toàn bộ diện tích đất đang sử dụng — Lai Châu (1.115590)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_cap_giay_chung_nhan_doi_voi_toan_bo_dien_tich_dat_lai_chau.process.runner import (
        run as _run,
    )

    return await _run(files_by_role, options)


__all__ = ["run"]
