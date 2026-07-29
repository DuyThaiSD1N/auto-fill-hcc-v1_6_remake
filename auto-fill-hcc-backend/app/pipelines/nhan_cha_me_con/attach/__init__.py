"""Attachment entrypoint for "Đăng ký nhận cha, mẹ, con"."""

from app.pipelines.nhan_cha_me_con.attach.planner import plan

__all__ = ["plan"]
