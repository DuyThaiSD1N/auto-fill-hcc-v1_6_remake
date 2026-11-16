"""Process pipeline for Xác nhận thông tin về cư trú."""


async def run(files_by_role, options):
    from app.pipelines.xac_nhan_thong_tin_ve_cu_tru.process.runner import run as _run

    return await _run(files_by_role, options)
