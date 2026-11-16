"""Process pipeline for Cấp lại thẻ căn cước."""


async def run(files_by_role, options):
    from app.pipelines.cap_lai_the_can_cuoc.process.runner import run as _run

    return await _run(files_by_role, options)
