"""Process pipeline cho [Lào Cai - cổng iGate mới] cấp GCN cho người nhận chuyển nhượng trong dự án BĐS (1.115667)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.cap_gcn_nhan_chuyen_nhuong_igate_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
