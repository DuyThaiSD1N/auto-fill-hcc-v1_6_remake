"""Process pipeline for "Giải quyết chế độ trợ cấp thờ cúng liệt sĩ"."""

__all__ = ["run"]


def __getattr__(name: str):
    if name == "run":
        from app.pipelines.tro_cap_tho_cung_liet_si.process.runner import run

        return run
    raise AttributeError(name)
