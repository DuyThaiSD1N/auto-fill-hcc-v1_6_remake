"""Process pipeline cho [Lào Cai] Thu hồi GCN cấp lần đầu không đúng quy định, cấp lại (1.115687)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
