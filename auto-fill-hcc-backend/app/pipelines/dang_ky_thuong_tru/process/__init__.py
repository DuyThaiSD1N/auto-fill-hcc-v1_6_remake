"""Process pipeline for Đăng ký thường trú."""


async def run(files_by_role, options):
    from app.pipelines.dang_ky_thuong_tru.process.runner import run as _run

    return await _run(files_by_role, options)
