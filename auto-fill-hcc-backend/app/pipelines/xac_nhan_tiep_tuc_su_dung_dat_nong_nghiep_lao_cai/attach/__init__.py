"""Lazy attachment entrypoint cho [Lào Cai] xác nhận tiếp tục sử dụng đất nông nghiệp (1.013947)."""


async def plan(files, options=None, session=None):
    from app.pipelines.xac_nhan_tiep_tuc_su_dung_dat_nong_nghiep_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
