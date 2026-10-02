"""Cộng dồn số liệu của tổ dân phố vào HCC xã cha.

Tổ dân phố (role "tdp") là tài khoản con của một HCC xã (`users.parent_id`), không phải một đơn
vị: mọi nơi đếm hồ sơ theo đơn vị (bảng thống kê, báo cáo Excel, màn Thống kê quản trị) phải
tính hồ sơ của nó vào xã cha. Chỗ áp dụng duy nhất là app/stats/cutover.py.

Quy tắc gộp: chỉ gộp khi xã cha NẰM TRONG phạm vi đang đếm (hoặc phạm vi không giới hạn). Tổ
dân phố tự xem bảng thống kê của mình (phạm vi = chính nó) vẫn thấy số của nó, không bị dồn đi
mất thành 0.

Tổ dân phố đã xóa mềm vẫn được tính: hồ sơ cũ của nó vẫn là hồ sơ của xã cha.
"""
from bson import ObjectId
from bson.errors import InvalidId

from app.db.mongo import get_db
from app.users.roles import TDP_PARENT_ROLE, TDP_ROLE

_NUMERIC_WARD_FIELDS = ("total", "exact", "estimated", "requests")
_NUMERIC_PROCEDURE_FIELDS = ("count", "exact", "estimated", "requests")


async def load_tdp_parents() -> dict[str, dict]:
    """{id tổ dân phố: {"parentId", "parentName"}} — rỗng khi chưa có tổ dân phố nào."""
    db = get_db()
    children = [
        doc async for doc in db.users.find(
            {"role": TDP_ROLE, "parent_id": {"$nin": [None, ""]}}, {"parent_id": 1},
        )
    ]
    if not children:
        return {}
    parent_oids = []
    for child in children:
        try:
            parent_oids.append(ObjectId(child["parent_id"]))
        except (InvalidId, TypeError):
            continue
    parents = {
        str(doc["_id"]): doc async for doc in db.users.find(
            {"_id": {"$in": parent_oids}}, {"name": 1, "username": 1},
        )
    }
    links: dict[str, dict] = {}
    for child in children:
        parent_id = str(child["parent_id"])
        parent = parents.get(parent_id)
        if parent is None:
            continue
        links[str(child["_id"])] = {
            "parentId": parent_id,
            "parentName": parent.get("name") or parent.get("username") or parent_id,
        }
    return links


class TdpRollup:
    """Ánh xạ tổ dân phố → xã cha cho MỘT phạm vi đếm (`scope_ids` None = không giới hạn)."""

    def __init__(self, links: dict[str, dict], scope_ids: list[str] | None):
        self._links = links
        self._scope = None if scope_ids is None else {str(value) for value in scope_ids}

    @property
    def active(self) -> bool:
        return bool(self._links)

    def unit(self, user_id: str) -> str:
        link = self._links.get(str(user_id))
        if link and (self._scope is None or link["parentId"] in self._scope):
            return link["parentId"]
        return str(user_id)

    def expand(self, user_ids: list[str] | None) -> list[str] | None:
        """Thêm tổ dân phố của các xã trong phạm vi vào danh sách cần đếm."""
        if user_ids is None or not self._links:
            return user_ids
        scope = {str(value) for value in user_ids}
        children = [child for child, link in self._links.items() if link["parentId"] in scope]
        return list(dict.fromkeys([*user_ids, *children]))

    def rows(self, rows: list[dict]) -> list[dict]:
        """Dòng phẳng có `userId` (số hồ sơ theo thủ tục / theo ngày) → đổi sang xã cha."""
        if not self._links:
            return rows
        out = []
        for row in rows:
            user_id = str(row.get("userId") or "")
            unit = self.unit(user_id)
            if unit == user_id:
                out.append(row)
                continue
            moved = {**row, "userId": unit}
            if "name" in row:
                moved["name"] = self._links[user_id]["parentName"]
            out.append(moved)
        return out

    def stats(self, stats: dict) -> dict:
        """Kết quả dạng `{wards: [...]}` → gộp ward của tổ dân phố vào ward xã cha.

        Chỉ đụng `wards`; các tổng toàn phạm vi (`procedures`, `totalDossiers`…) không đổi vì
        gộp chỉ chuyển số giữa các dòng.
        """
        if not self._links or not stats.get("wards"):
            return stats
        merged: dict[str, dict] = {}
        for ward in stats["wards"]:
            user_id = str(ward.get("userId") or "")
            unit = self.unit(user_id)
            target = merged.get(unit)
            if unit == user_id:
                if target is None:
                    merged[unit] = {**ward, "procedures": [dict(p) for p in ward.get("procedures") or []]}
                else:
                    # Dòng xã cha đến SAU dòng con: lấy tên/thuộc tính của chính xã cha.
                    for key, value in ward.items():
                        if key not in _NUMERIC_WARD_FIELDS and key != "procedures":
                            target[key] = value
                    _add_ward(target, ward)
                continue
            if target is None:
                target = {
                    **{k: v for k, v in ward.items() if k not in _NUMERIC_WARD_FIELDS},
                    "userId": unit,
                    "name": self._links[user_id]["parentName"],
                    "procedures": [],
                    **{field: 0 for field in _NUMERIC_WARD_FIELDS if field in ward},
                }
                if "role" in ward:
                    target["role"] = TDP_PARENT_ROLE
                merged[unit] = target
            _add_ward(target, ward)
        wards = sorted(
            merged.values(),
            key=lambda item: (-int(item.get("total") or 0), str(item.get("name") or "")),
        )
        return {**stats, "wards": wards}


def _add_ward(target: dict, ward: dict) -> None:
    for field in _NUMERIC_WARD_FIELDS:
        if field in ward:
            target[field] = int(target.get(field) or 0) + int(ward.get(field) or 0)
    by_key = {str(p.get("key")): p for p in target.setdefault("procedures", [])}
    for procedure in ward.get("procedures") or []:
        key = str(procedure.get("key"))
        existing = by_key.get(key)
        if existing is None:
            existing = dict(procedure)
            target["procedures"].append(existing)
            by_key[key] = existing
            continue
        for field in _NUMERIC_PROCEDURE_FIELDS:
            if field in procedure:
                existing[field] = int(existing.get(field) or 0) + int(procedure.get(field) or 0)
    target["procedures"].sort(key=lambda p: (-int(p.get("count") or 0), str(p.get("label") or "")))
