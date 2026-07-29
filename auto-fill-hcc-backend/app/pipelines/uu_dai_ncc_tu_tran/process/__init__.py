"""Process pipeline for "Hưởng trợ cấp khi người có công đang hưởng trợ cấp ưu đãi từ trần"."""

__all__ = ["run"]


def __getattr__(name: str):
    if name == "run":
        from app.pipelines.uu_dai_ncc_tu_tran.process.runner import run

        return run
    raise AttributeError(name)
