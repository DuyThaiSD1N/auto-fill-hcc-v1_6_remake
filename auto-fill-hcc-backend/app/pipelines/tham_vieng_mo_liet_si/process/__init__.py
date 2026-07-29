"""Process pipeline for "Thăm viếng mộ liệt sĩ"."""

__all__ = ["run"]


def __getattr__(name: str):
    if name == "run":
        from app.pipelines.tham_vieng_mo_liet_si.process.runner import run

        return run
    raise AttributeError(name)
