"""Process pipeline for Xóa đăng ký tạm trú."""


async def run(files_by_role, options):
    from app.pipelines.xoa_dang_ky_tam_tru.process.runner import run as _run

    return await _run(files_by_role, options)
