"""Process pipeline cho [Lào Cai] Đăng ký đất đai, cấp GCN lần đầu (1.115688)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dk_dat_dai_gan_tai_san_lao_cai.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
