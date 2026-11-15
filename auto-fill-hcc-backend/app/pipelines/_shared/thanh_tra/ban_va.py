"""Bản vá của lượt soát: các ô UI lượt soát đổi so với lượt điền đầu."""


def diff(before: list[dict], after: list[dict], names, follows: dict | None = None) -> list[dict]:
    """Ô thuộc ``names`` có giá trị khác lượt đầu, hoặc lượt đầu chưa có. Khoá "from" là giá trị lượt đầu để bên điền
    đối chiếu trước khi ghi. Ô lượt đầu có mà lượt soát không còn thì không đưa vào: bản vá chỉ ghi, không xoá.

    ``follows`` = {ô con: ô cha}: ô cha đổi thì ô con đi kèm dù giá trị không đổi — form xoá ô con khi ô cha đổi
    (xã theo tỉnh)."""
    first = {f.get("name"): f for f in before or [] if isinstance(f, dict)}
    follows = follows or {}

    def changed(field: dict) -> bool:
        old = first.get(field.get("name"))
        return old is None or old.get("value") != field.get("value")

    moved = {f.get("name") for f in after or [] if f.get("name") in names and changed(f)}
    out: list[dict] = []
    for field in after or []:
        name = field.get("name")
        if name in moved or (name in names and follows.get(name) in moved):
            old = first.get(name)
            out.append({**field, "from": old.get("value") if old else None})
    return out
