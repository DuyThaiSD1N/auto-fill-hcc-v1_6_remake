"""Process pipeline for "Bổ sung tình hình thân nhân trong hồ sơ liệt sĩ"."""

__all__ = ["run"]


def __getattr__(name: str):
    if name == "run":
        from app.pipelines.bo_sung_than_nhan_liet_si.process.runner import run

        return run
    raise AttributeError(name)
