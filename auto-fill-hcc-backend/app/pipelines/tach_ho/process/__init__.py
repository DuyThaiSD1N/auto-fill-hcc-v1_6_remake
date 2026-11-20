"""Process pipeline for Tách hộ."""


async def run(files_by_role, options):
    from app.pipelines.tach_ho.process.runner import run as _run

    return await _run(files_by_role, options)
