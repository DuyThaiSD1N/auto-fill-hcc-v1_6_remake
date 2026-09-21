"""Process pipeline cho [Lào Cai] Chuyển mục đích sử dụng đất cấp phường/xã (1.115679)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.chuyen_md_sd_dat_phuong_xa_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
