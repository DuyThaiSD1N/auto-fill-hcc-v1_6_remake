"""Đính tách nhiều hồ sơ (mỗi tài liệu một tab): chỉ mời đánh giá khi MỌI tab đã bấm nộp.

Tab gốc có sidebar nên báo "nộp thành công" được; tab tách không có sidebar, background chuyển cú
bấm nộp của nó về tab gốc. Không có sổ này thì tab gốc nộp trước là phiếu đánh giá + đồng hồ tự
đăng xuất bật ngay, đăng xuất giữa chừng các tab tách chưa nộp.

Đếm theo TAB chứ không theo cú bấm (một tab bấm lại nhiều lần vẫn là một hồ sơ) và không theo
`ref` (nhiều cổng không có mã hồ sơ trên URL). Tab tách đóng mà chưa bấm nộp → coi như bỏ hồ sơ
đó, trừ khỏi tổng. Cú bấm lọt (Enter, nút lạ) thì cán bộ có nút thoát `split_submit_done`.

Tương thích: chỉ bật khi extension khai `supportsSplitSubmitTabs` (gửi kèm mã tab). Bản trên
chợ không khai → không có sổ, `submitted` của tab gốc mời đánh giá ngay như cũ.
"""

CAPABILITY = "supportsSplitSubmitTabs"
DONE_ACTION = "split_submit_done"


def supported(conv: dict) -> bool:
    return (conv.get("client_capabilities") or {}).get(CAPABILITY) is True


def start(conv: dict, total: int) -> None:
    """Gọi lúc đính tách xong. Lượt đính kèm mới thay sổ cũ."""
    if supported(conv) and total > 1:
        conv["split_submit"] = {"total": total, "tabs": [], "closed": [],
                                "held": False, "released": False}
    else:
        conv.pop("split_submit", None)


def clear(conv: dict) -> None:
    conv.pop("split_submit", None)


def _tab(payload: dict | None) -> int | None:
    try:
        tab = int((payload or {}).get("tab_id"))
    except (TypeError, ValueError):
        return None
    return tab if tab > 0 else None


def _open(conv: dict) -> dict | None:
    book = conv.get("split_submit")
    return book if isinstance(book, dict) and not book.get("released") else None


def _expected(book: dict) -> int:
    return max(1, int(book.get("total") or 0) - len(book.get("closed") or []))


def _complete(book: dict) -> bool:
    return len(book.get("tabs") or []) >= _expected(book)


def _release_if_complete(book: dict) -> bool:
    """True đúng một lần: phiếu đang bị giữ và giờ mới đủ hồ sơ."""
    if book.get("held") and _complete(book):
        book["released"] = True
        return True
    return False


def note_click(conv: dict, payload: dict | None) -> bool:
    """Một tab vừa bấm nộp. True = cú bấm này làm đủ hồ sơ trong lúc phiếu đang chờ."""
    book, tab = _open(conv), _tab(payload)
    if book is None or tab is None:
        return False
    if tab not in book["tabs"]:
        book["tabs"].append(tab)
    return _release_if_complete(book)


def note_closed(conv: dict, payload: dict | None) -> bool:
    """Tab tách bị đóng. Đã bấm nộp thì vẫn tính là đã nộp; chưa bấm thì trừ khỏi tổng."""
    book, tab = _open(conv), _tab(payload)
    if book is None or tab is None:
        return False
    if tab not in book["tabs"] and tab not in book["closed"]:
        book["closed"].append(tab)
    return _release_if_complete(book)


def hold(conv: dict, payload: dict | None) -> str:
    """Tab gốc báo nộp thành công. "" = cho đi tiếp; "new" = mới giữ phiếu; "again" = đang giữ."""
    book = _open(conv)
    if book is None:
        return ""
    tab = _tab(payload)
    if tab is not None and tab not in book["tabs"]:
        book["tabs"].append(tab)
    if _complete(book):
        book["released"] = True
        return ""
    if book.get("held"):
        return "again"
    book["held"] = True
    return "new"


def release(conv: dict) -> bool:
    """Cán bộ bấm "Đã nộp hết" — chỉ có tác dụng khi phiếu đang bị giữ."""
    book = _open(conv)
    if book is None or not book.get("held"):
        return False
    book["released"] = True
    return True


def progress(conv: dict) -> tuple[int, int]:
    book = conv.get("split_submit") or {}
    done = len(book.get("tabs") or [])
    return done, max(done, _expected(book))


def done_chip() -> dict:
    return {"label": "Đã nộp hết, đánh giá", "send": f"__action:{DONE_ACTION}"}
