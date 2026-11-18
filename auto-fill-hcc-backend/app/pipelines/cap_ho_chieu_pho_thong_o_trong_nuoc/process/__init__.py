"""Process pipeline cho Cấp hộ chiếu phổ thông ở trong nước (1.001456)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
