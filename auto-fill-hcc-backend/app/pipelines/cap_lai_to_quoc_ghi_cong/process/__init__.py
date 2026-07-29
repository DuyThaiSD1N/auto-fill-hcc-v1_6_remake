"""Process pipeline for "Cấp lại Bằng Tổ quốc ghi công"."""

__all__ = ["run"]


def __getattr__(name: str):
    if name == "run":
        from app.pipelines.cap_lai_to_quoc_ghi_cong.process.runner import run

        return run
    raise AttributeError(name)
