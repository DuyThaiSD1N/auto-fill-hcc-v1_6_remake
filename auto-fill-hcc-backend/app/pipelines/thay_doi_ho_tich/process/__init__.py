"""Lazy process entrypoint for thay-doi-cai-chinh-ho-tich."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.thay_doi_ho_tich.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
