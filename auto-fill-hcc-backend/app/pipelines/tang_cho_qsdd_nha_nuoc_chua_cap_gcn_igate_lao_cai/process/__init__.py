"""Process pipeline cho [Lào Cai - cổng iGate mới] tặng cho quyền sử dụng đất mở rộng đường giao thông (1.115690)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.tang_cho_qsdd_nha_nuoc_chua_cap_gcn_igate_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
