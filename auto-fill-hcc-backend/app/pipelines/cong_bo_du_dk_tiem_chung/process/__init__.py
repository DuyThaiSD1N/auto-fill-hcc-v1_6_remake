"""Lazy process entrypoint for cong-bo-co-so-du-dieu-kien-tiem-chung."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.cong_bo_du_dk_tiem_chung.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
