"""Compact agent process pipeline cho "Đăng ký biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất".

Thủ tục CHỈ có chế độ người nộp theo tờ khai: cán bộ một cửa nộp hộ bằng tài khoản của mình nên mốc tài khoản
không bao giờ khớp người trong hồ sơ → không đưa mốc vào prompt. Chủ hồ sơ = người yêu cầu đăng ký (Phiếu
01a Mục 1 / tổ chức cử người theo Giấy giới thiệu), người nộp = người được giới thiệu/ủy quyền.
"""

from app.pipelines._shared.compact_agent import runner
from app.pipelines.dang_ky_bien_phap_bao_dam_qsdd.process import mapper
from app.pipelines.dang_ky_bien_phap_bao_dam_qsdd.process.prompt import EXTRA_RULES
from app.pipelines.dang_ky_bien_phap_bao_dam_qsdd.process.schema import (
    ALIASES,
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    FIELDS,
)


async def run(files_by_role: dict[str, list[dict]], options: dict) -> dict:
    res = await runner.run(
        files_by_role,
        fields=FIELDS,
        allowed=ALLOWED,
        comp_by_name=COMPACT_COMP_BY_NAME,
        aliases=ALIASES,
        extra_rules=EXTRA_RULES,
        options=options,
    )
    mapped_fields, warnings = mapper.enrich(res["fields"], options)
    res["fields"] = mapped_fields
    if warnings:
        res.setdefault("errors", []).extend(warnings)
    return res
