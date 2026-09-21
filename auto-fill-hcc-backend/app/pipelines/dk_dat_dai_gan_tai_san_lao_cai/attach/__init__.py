"""Lazy attachment entrypoint cho [Lào Cai] Đăng ký đất đai, cấp GCN lần đầu (1.115688)."""


async def plan(files, options=None, session=None):
    from app.pipelines.dk_dat_dai_gan_tai_san_lao_cai.attach.planner import plan as _plan

    return await _plan(files, options, session)


__all__ = ["plan"]
