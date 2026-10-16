"""Lazy attachment entrypoint cho [Lào Cai] đăng ký biến động đổi tên, thay đổi thông tin (1.013833)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dang_ky_bien_dong_doi_ten_nguoi_su_dung_dat_lao_cai.attach.planner import (
        plan as _plan,
    )

    return await _plan(files, options, session)


__all__ = ["plan"]
