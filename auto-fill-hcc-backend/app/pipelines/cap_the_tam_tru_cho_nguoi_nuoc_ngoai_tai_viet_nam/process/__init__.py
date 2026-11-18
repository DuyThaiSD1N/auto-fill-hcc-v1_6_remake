"""Process pipeline cho Cấp thẻ tạm trú cho người nước ngoài tại Việt Nam (1.003460)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.cap_the_tam_tru_cho_nguoi_nuoc_ngoai_tai_viet_nam.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
