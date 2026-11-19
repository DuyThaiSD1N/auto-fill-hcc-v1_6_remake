"""Process pipeline cho Trình báo mất hộ chiếu phổ thông (thực hiện tại cấp xã) (1.010386)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.trinh_bao_mat_ho_chieu_pho_thong_cap_xa.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
