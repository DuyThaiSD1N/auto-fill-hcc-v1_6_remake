"""Cấu hình theo tài khoản: xã Nghĩa Hưng (Ninh Bình) KHÔNG đính kèm Tờ khai.

Cán bộ xã Nghĩa Hưng không đính Tờ khai cấp Giấy xác nhận tình trạng hôn nhân (bản giấy hay bản
scan đều vậy) vào thành phần hồ sơ; các giấy tờ khác (CCCD, quyết định ly hôn, giấy chứng nhận kết
hôn, ủy quyền…) vẫn đính như thường.

Planner không biết tài khoản nên router (Auto Fill) và pipeline_runner (Handfree) gọi
``with_account_attach_options`` để server tự đặt cờ ``omitPaperDeclaration``. Cờ luôn bị ghi đè
theo tài khoản, client không tự bật được cho xã khác. Mọi thủ tục/tài khoản khác: không có cờ,
hành vi giữ y hệt.

Phường Đông Hà (Quảng Trị) CHỈ đính văn bản ủy quyền, mọi giấy tờ khác (tờ khai, CCCD, giấy tờ hôn
nhân…) không đính — cờ ``onlyAuthorization``, cũng do server đặt theo tài khoản như trên.
"""
from app.pipelines._shared import fold

PROCEDURE_KEY = "xac-nhan-tinh-trang-hon-nhan"
OMIT_PAPER_DECLARATION_OPTION = "omitPaperDeclaration"
OMITTED_DECLARATION_NOTE = "Không đính kèm Tờ khai theo cấu hình xã Nghĩa Hưng"
ONLY_AUTHORIZATION_OPTION = "onlyAuthorization"

_WARD_PREFIXES = ("xa ", "phuong ", "thi tran ")


def _is_account(user: dict | None, tinh_key: str, xa_key: str) -> bool:
    """Tỉnh khớp lỏng ("Tỉnh Ninh Bình"/"Ninh Bình"); xã khớp ĐÚNG tên sau khi bỏ tiền tố để không
    dính xã khác có tên chứa tên này ("Nam Đông Hà"…)."""
    if not user:
        return False
    tinh = fold(user.get("tinh") or "")
    xa = fold(user.get("xa") or "")
    for prefix in _WARD_PREFIXES:
        if xa.startswith(prefix):
            xa = xa[len(prefix):].strip()
            break
    return tinh_key in tinh and xa == xa_key


def is_ninh_binh_nghia_hung(user: dict | None) -> bool:
    """True khi tài khoản thuộc xã Nghĩa Hưng, tỉnh Ninh Bình."""
    return _is_account(user, "ninh binh", "nghia hung")


def is_quang_tri_dong_ha(user: dict | None) -> bool:
    """True khi tài khoản thuộc phường Đông Hà, tỉnh Quảng Trị."""
    return _is_account(user, "quang tri", "dong ha")


def with_account_attach_options(options: dict | None, user: dict | None, procedure: str) -> dict:
    """Trả bản sao options với cờ bỏ Tờ khai / chỉ đính ủy quyền do server quyết theo tài khoản."""
    result = dict(options or {})
    result.pop(OMIT_PAPER_DECLARATION_OPTION, None)
    result.pop(ONLY_AUTHORIZATION_OPTION, None)
    if procedure == PROCEDURE_KEY and is_ninh_binh_nghia_hung(user):
        result[OMIT_PAPER_DECLARATION_OPTION] = True
    if procedure == PROCEDURE_KEY and is_quang_tri_dong_ha(user):
        result[ONLY_AUTHORIZATION_OPTION] = True
    return result


def omits_paper_declaration(options: dict | None) -> bool:
    return (options or {}).get(OMIT_PAPER_DECLARATION_OPTION) is True


def only_authorization(options: dict | None) -> bool:
    return (options or {}).get(ONLY_AUTHORIZATION_OPTION) is True


def keep_only_authorization(attachments: list[dict]) -> None:
    """Phường Đông Hà: bỏ mọi mục đính kèm không phải văn bản ủy quyền (sửa tại chỗ).

    Bỏ im lặng, không ghi vào ``errors``: đây là cấu hình chủ ý của phường, extension không được báo
    "Chưa đính kèm được" cho các giấy bị bỏ (kể cả khi hồ sơ không có ủy quyền nào)."""
    attachments[:] = [a for a in attachments if a.get("detectedType") == "authorization"]
