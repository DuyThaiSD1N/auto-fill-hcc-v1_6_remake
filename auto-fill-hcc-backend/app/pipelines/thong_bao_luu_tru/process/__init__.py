"""Process pipeline for Thông báo lưu trú."""


async def run(files_by_role, options):
    from app.pipelines.thong_bao_luu_tru.process.runner import run as _run

    return await _run(files_by_role, options)
