"""Process pipeline cho Cấp thị thực cho người nước ngoài tại Việt Nam (1.001194)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.cap_thi_thuc_cho_nguoi_nuoc_ngoai_tai_viet_nam.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
