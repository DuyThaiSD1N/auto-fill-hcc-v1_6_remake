"""Process pipeline for Cấp thẻ căn cước cho người từ đủ 14 tuổi trở lên."""


async def run(files_by_role, options):
    from app.pipelines.cap_the_can_cuoc_tu_du_14_tuoi.process.runner import run as _run

    return await _run(files_by_role, options)
