"""Cấu hình theo tài khoản: xã Nghĩa Hưng (Ninh Bình) KHÔNG đính kèm Tờ khai.

Cán bộ xã Nghĩa Hưng không đính Tờ khai (bản giấy hay bản scan đều vậy) vào thành phần hồ sơ của
hai thủ tục: cấp Giấy xác nhận tình trạng hôn nhân và đăng ký kết hôn. Các giấy tờ khác (CCCD,
quyết định ly hôn, giấy xác nhận tình trạng hôn nhân, bản cam đoan, ủy quyền…) vẫn đính như thường.

Planner không biết tài khoản nên router (Auto Fill) và pipeline_runner (Handfree) gọi
``with_account_attach_options`` để server tự đặt cờ ``omitPaperDeclaration``. Cờ luôn bị ghi đè
theo tài khoản, client không tự bật được cho xã khác. Mọi thủ tục/tài khoản khác: không có cờ,
hành vi giữ y hệt.
"""
from app.pipelines._shared import fold

PROCEDURE_KEYS = frozenset({"xac-nhan-tinh-trang-hon-nhan", "ket-hon"})
OMIT_PAPER_DECLARATION_OPTION = "omitPaperDeclaration"
OMITTED_DECLARATION_NOTE = "Không đính kèm Tờ khai theo cấu hình xã Nghĩa Hưng"

_WARD_PREFIXES = ("xa ", "phuong ", "thi tran ")


def is_ninh_binh_nghia_hung(user: dict | None) -> bool:
    """True khi tài khoản thuộc xã Nghĩa Hưng, tỉnh Ninh Bình.

    Tỉnh khớp lỏng ("Tỉnh Ninh Bình"/"Ninh Bình"); xã khớp ĐÚNG tên sau khi bỏ tiền tố để không
    dính xã khác có tên chứa "Nghĩa Hưng".
    """
    if not user:
        return False
    tinh = fold(user.get("tinh") or "")
    xa = fold(user.get("xa") or "")
    for prefix in _WARD_PREFIXES:
        if xa.startswith(prefix):
            xa = xa[len(prefix):].strip()
            break
    return "ninh binh" in tinh and xa == "nghia hung"


def with_account_attach_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Trả bản sao options với cờ bỏ Tờ khai do server quyết theo tài khoản."""
    result = dict(options or {})
    result.pop(OMIT_PAPER_DECLARATION_OPTION, None)
    if procedure in PROCEDURE_KEYS and is_ninh_binh_nghia_hung(user):
        result[OMIT_PAPER_DECLARATION_OPTION] = True
    return result


def omits_paper_declaration(options: dict | None) -> bool:
    return (options or {}).get(OMIT_PAPER_DECLARATION_OPTION) is True
