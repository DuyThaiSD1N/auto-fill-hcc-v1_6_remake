"""Process pipeline cho [Lào Cai - cổng iGate mới] đính chính Giấy chứng nhận đã cấp (1.115686)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dinh_chinh_gcn_da_cap_igate_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
