"""Process pipeline cho Đăng ký xe lần đầu toàn trình — xe nhập khẩu (1.013066)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_xe_lan_dau_nhap_khau.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
