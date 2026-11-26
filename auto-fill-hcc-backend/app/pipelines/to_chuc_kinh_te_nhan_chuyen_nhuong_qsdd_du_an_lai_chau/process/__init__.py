"""Process pipeline cho Tổ chức kinh tế nhận chuyển nhượng QSDĐ để thực hiện dự án — Lai Châu (1.115591)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhuong_qsdd_du_an_lai_chau.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
