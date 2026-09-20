"""Process pipeline cho [Lào Cai] xác nhận tiếp tục sử dụng đất nông nghiệp (1.115677)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
