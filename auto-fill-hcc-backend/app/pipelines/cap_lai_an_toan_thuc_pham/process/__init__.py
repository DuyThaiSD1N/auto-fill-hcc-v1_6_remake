"""Process pipeline entrypoint for ATTP certificate reissue."""

try:
    from app.pipelines.cap_lai_an_toan_thuc_pham.process.runner import run
except Exception:  # pragma: no cover - defensive import for partial startup
    run = None  # type: ignore[assignment]

__all__ = ["run"]

