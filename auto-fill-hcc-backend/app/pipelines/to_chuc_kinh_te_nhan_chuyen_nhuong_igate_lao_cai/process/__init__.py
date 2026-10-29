"""Process pipeline cho [Lào Cai - cổng iGate mới] tổ chức kinh tế nhận chuyển nhượng QSDĐ dự án (1.115681)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhuong_igate_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
