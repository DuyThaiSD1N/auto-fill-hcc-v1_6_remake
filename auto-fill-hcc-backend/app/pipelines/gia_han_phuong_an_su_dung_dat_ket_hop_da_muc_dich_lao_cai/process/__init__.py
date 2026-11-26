"""Process pipeline cho [Lào Cai - cổng iGate mới] gia hạn phương án sử dụng đất kết hợp (1.115683)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.gia_han_phuong_an_su_dung_dat_ket_hop_da_muc_dich_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
