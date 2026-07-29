"""Process pipeline for food safety certificate procedure."""

__all__ = ["run"]


def __getattr__(name: str):
    if name == "run":
        from app.pipelines.an_toan_thuc_pham.process.runner import run

        return run
    raise AttributeError(name)

