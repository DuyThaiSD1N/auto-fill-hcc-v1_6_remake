"""Process pipeline cho [Lào Cai - cổng iGate mới] đăng ký, cấp GCN khi đã chuyển quyền trước 01/8/2024 (1.115666)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_gcn_chuyen_quyen_igate_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
