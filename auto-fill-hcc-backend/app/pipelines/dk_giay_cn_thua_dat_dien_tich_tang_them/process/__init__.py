"""Process pipeline cho [Lào Cai] đăng ký, cấp GCN thửa đất có diện tích tăng thêm (1.115694)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.dk_giay_cn_thua_dat_dien_tich_tang_them.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
