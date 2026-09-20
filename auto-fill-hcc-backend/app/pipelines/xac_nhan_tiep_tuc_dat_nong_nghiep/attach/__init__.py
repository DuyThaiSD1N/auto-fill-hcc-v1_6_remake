"""Lazy attachment entrypoint cho [Lào Cai] xác nhận tiếp tục sử dụng đất nông nghiệp (1.115677)."""


async def plan(files, options=None, session=None):
    from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
