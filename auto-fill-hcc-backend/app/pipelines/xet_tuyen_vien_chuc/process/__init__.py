"""Process pipeline for "Thủ tục xét tuyển Viên chức (85/2023/NĐ-CP)"."""

__all__ = ["run"]


def __getattr__(name: str):
    if name == "run":
        from app.pipelines.xet_tuyen_vien_chuc.process.runner import run

        return run
    raise AttributeError(name)
