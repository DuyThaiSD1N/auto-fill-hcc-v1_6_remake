"""Process pipeline cho "Cấp trích lục hoặc sao hồ sơ người có công với cách mạng" (1.010828)."""

__all__ = ["run"]


def __getattr__(name: str):
    if name == "run":
        from app.pipelines.cap_trich_luc_sao_ho_so_nguoi_co_cong.process.runner import run

        return run
    raise AttributeError(name)
