"""Process pipeline cho [Lào Cai] xác nhận tiếp tục sử dụng đất nông nghiệp (1.013947)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
