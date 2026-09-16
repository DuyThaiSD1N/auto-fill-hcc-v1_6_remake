"""Process pipeline cho [Lào Cai] Đăng ký biến động quyền sử dụng đất (1.115668)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
