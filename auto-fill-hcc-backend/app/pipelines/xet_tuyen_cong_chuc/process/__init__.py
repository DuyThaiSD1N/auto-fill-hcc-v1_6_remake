"""Process pipeline for "Xét tuyển công chức"."""

__all__ = ["run"]


def __getattr__(name: str):
    if name == "run":
        from app.pipelines.xet_tuyen_cong_chuc.process.runner import run

        return run
    raise AttributeError(name)
