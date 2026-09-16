"""Process pipeline cho [Lào Cai] cấp GCN cho người nhận chuyển nhượng trong dự án BĐS (1.115667)."""


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    from app.pipelines.cap_GCN_nhan_chuyen_nhuong.process.runner import run as _run

    return await _run(files_by_role, options)


__all__ = ["run"]
