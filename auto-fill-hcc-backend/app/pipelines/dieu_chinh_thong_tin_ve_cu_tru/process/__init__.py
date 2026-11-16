"""Process pipeline for Điều chỉnh thông tin về cư trú."""


async def run(files_by_role, options):
    from app.pipelines.dieu_chinh_thong_tin_ve_cu_tru.process.runner import run as _run

    return await _run(files_by_role, options)
