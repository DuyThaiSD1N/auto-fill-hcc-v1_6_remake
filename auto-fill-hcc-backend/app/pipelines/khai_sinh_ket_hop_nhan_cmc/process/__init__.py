"""Process entrypoint for the combined civil-status procedure."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.khai_sinh_ket_hop_nhan_cmc.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]

