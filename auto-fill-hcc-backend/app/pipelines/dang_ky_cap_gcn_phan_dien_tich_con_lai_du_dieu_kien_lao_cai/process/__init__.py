"""Process pipeline cho [Lào Cai - cổng iGate mới] cấp GCN phần diện tích còn lại nay đủ điều kiện (1.115692)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dang_ky_cap_gcn_phan_dien_tich_con_lai_du_dieu_kien_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
