"""Process pipeline cho Đăng ký sang tên, di chuyển xe tại Công an cấp tỉnh (2.000076)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_sang_ten_di_chuyen_xe_cap_tinh.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
