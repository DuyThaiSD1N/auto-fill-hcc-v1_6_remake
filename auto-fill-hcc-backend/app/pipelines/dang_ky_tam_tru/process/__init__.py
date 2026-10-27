"""Process pipeline for Đăng ký tạm trú."""


async def run(files_by_role, options):
    from app.pipelines.dang_ky_tam_tru.process.runner import run as _run

    return await _run(files_by_role, options)
