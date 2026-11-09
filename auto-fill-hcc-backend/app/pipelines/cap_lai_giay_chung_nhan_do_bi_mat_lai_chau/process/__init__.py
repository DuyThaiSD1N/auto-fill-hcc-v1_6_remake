"""Process pipeline cho Cấp lại Giấy chứng nhận do bị mất — Lai Châu (1.115557)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.cap_lai_giay_chung_nhan_do_bi_mat_lai_chau.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
