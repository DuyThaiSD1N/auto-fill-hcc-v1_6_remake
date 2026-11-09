"""Process pipeline cho Chuyển mục đích sử dụng đất (xã miền núi, biên giới...) — Lai Châu (1.115578)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.chuyen_muc_dich_su_dung_dat_mien_nui_lai_chau.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
