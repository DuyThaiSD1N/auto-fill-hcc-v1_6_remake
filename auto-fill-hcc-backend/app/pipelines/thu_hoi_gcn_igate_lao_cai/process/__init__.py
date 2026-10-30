"""Process pipeline cho [Lào Cai - cổng iGate mới] thu hồi GCN cấp lần đầu không đúng quy định (1.115687)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.thu_hoi_gcn_igate_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
