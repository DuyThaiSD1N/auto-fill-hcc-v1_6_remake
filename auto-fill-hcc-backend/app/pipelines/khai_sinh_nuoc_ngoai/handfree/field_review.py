"""Bổ sung ô còn trống trên form SurveyJS khai sinh có yếu tố nước ngoài (dichvucong.gov.vn/nop-ho-so).

Cùng tờ khai điện tử với 1.001193 nên dùng đúng bộ ô không hỏi / ô tra cứu của khai_sinh_dvc_moi.
"""

from app.pipelines.khai_sinh_dvc_moi.handfree.field_review import LOOKUP, NO_ASK  # noqa: F401

PROCEDURE_KEYS = ("khai-sinh-nuoc-ngoai",)

REQUIRED = ()
