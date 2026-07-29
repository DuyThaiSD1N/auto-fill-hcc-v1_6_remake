"""Process pipeline for chuyển đổi tên hợp đồng nước sạch."""


async def run(files_by_role, options):
    from app.pipelines.doi_ten_nuoc_sach.process.runner import run as _run

    return await _run(files_by_role, options)

