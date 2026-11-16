"""Process pipeline cho Đăng ký xe lần đầu toàn trình — xe sản xuất, lắp ráp trong nước (1.012575)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_xe_lan_dau_san_xuat_lap_rap_trong_nuoc.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
