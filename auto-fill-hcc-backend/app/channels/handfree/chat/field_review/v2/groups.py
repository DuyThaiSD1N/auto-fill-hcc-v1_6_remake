"""Cụm ô của tờ khai cho vòng bổ sung bản 2: các ô hỏi liền nhau và hỏi gộp một câu (giấy tờ tùy thân, nơi cư trú…).

Thủ tục khai cụm trong ``GROUPS`` (app/pipelines/<tt>/handfree/field_review.py); các ô cùng một khối địa chỉ (Quốc gia /
Tỉnh / Xã / Địa chỉ) luôn là một cụm. Cụm chỉ quyết THỨ TỰ hỏi và cách đặt câu hỏi — công dân nói thông tin của ô nào
thì agent điều phối vẫn giao ô đó, kể cả ô ngoài cụm.
"""


def _configured(proc_config: dict | None) -> tuple:
    return tuple((proc_config or {}).get("groups") or ())


def group_id(field: dict, groups: tuple) -> str:
    name = field.get("name") or ""
    for i, (_, members) in enumerate(groups):
        if name in members:
            return f"g{i}"
    if field.get("role"):
        return "area:" + name
    return "o:" + str(field.get("key") or "")


def title(field: dict, groups: tuple) -> str:
    gid = group_id(field, groups)
    if gid.startswith("g"):
        return groups[int(gid[1:])][0]
    if gid.startswith("area:"):
        return field.get("where") or field.get("label") or ""
    return field.get("label") or ""


def _open(catalog: list[dict], skip: set) -> list[dict]:
    return [f for f in catalog if not f.get("value") and f.get("key") not in skip]


def next_key(catalog: list[dict], proc_config: dict | None, st: dict, done: tuple = ()) -> str:
    """Ô nên hỏi kế tiếp theo thứ tự trên trang: đang dở cụm nào thì hỏi nốt cụm đó; hỏi ô bắt buộc trước (luồng bản 2)
    thì tới cụm đầu tiên còn ô bắt buộc trống — hỏi cả các ô không bắt buộc của cụm đó cho liền mạch (loại giấy tờ, số,
    ngày cấp, cơ quan cấp); hết thì ô trống đầu tiên. `done`: ô đang được điền trong cùng lệnh, coi như đã có giá trị."""
    groups = _configured(proc_config)
    pending = _open(catalog, {*(st.get("skip") or []), *done})
    if not pending:
        return ""
    anchor = st.get("group_anchor")
    if anchor:
        same = [f for f in pending if group_id(f, groups) == anchor]
        if same:
            return same[0]["key"]
    if st.get("required_first"):
        first_required = next((f for f in pending if f.get("required")), None)
        if first_required:
            gid = group_id(first_required, groups)
            return next(f for f in pending if group_id(f, groups) == gid)["key"]
    return pending[0]["key"]


def open_members(catalog: list[dict], proc_config: dict | None, st: dict, field: dict) -> list[dict]:
    """Các ô còn trống (chưa bỏ qua) cùng cụm với `field`, theo thứ tự trên trang; ô đang hỏi đứng đầu."""
    groups = _configured(proc_config)
    gid = group_id(field, groups)
    members = [f for f in _open(catalog, set(st.get("skip") or []))
               if group_id(f, groups) == gid and f.get("key") != field.get("key")]
    return [field, *members]
