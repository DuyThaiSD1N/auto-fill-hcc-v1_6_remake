"""Process pipeline cho [Lào Cai] xác định lại diện tích đất ở (GCN cấp trước 01/7/2004) — 1.115685."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.xac_dinh_lai_dien_tich_dat_o.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
