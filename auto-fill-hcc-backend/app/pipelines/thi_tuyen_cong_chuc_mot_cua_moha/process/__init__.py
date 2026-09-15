"""Process pipeline for "Thi tuyển công chức"."""

__all__ = ["run"]


def __getattr__(name: str):
    if name == "run":
        from app.pipelines.thi_tuyen_cong_chuc_mot_cua_moha.process.runner import run

        return run
    raise AttributeError(name)
