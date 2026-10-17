"""Process pipeline cho "Cấp bổ sung hoặc cấp lại giấy chứng nhận người có công" (1.010814)."""

__all__ = ["run"]


def __getattr__(name: str):
    if name == "run":
        from app.pipelines.cap_bo_sung_cap_lai_giay_chung_nhan_nguoi_co_cong.process.runner import run

        return run
    raise AttributeError(name)
