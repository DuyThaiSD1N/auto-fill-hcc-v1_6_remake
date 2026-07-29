"""Process pipeline for đăng ký lắp đặt sử dụng nước sạch."""


async def run(files_by_role, options):
    from app.pipelines.cap_nuoc_sach.process.runner import run as _run

    return await _run(files_by_role, options)

