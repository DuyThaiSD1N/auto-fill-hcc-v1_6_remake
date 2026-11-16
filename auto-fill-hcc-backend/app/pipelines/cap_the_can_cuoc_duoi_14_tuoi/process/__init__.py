"""Process pipeline for Cấp thẻ căn cước cho người dưới 14 tuổi."""


async def run(files_by_role, options):
    from app.pipelines.cap_the_can_cuoc_duoi_14_tuoi.process.runner import run as _run

    return await _run(files_by_role, options)
