"""Đơn vị TẠM KHÓA vẫn nằm trong báo cáo; đơn vị ĐÃ XÓA thì không.

Trước đây scope.py bỏ qua mọi tài khoản `access_disabled` — đây là chỗ DUY NHẤT trong backend
lọc theo cờ đó. Hệ quả: khóa một tài khoản để bảo trì là đơn vị đó cùng toàn bộ hồ sơ đã làm
biến khỏi bảng dashboard, trong khi màn Thống kê quản trị vẫn tính → hai màn nói hai con số
khác nhau về cùng một kỳ.

Công việc đã hoàn thành tháng trước không có lý do biến mất vì hôm nay khóa tài khoản. Giờ:
  - tạm khóa → VẪN là một đơn vị, có cờ accessDisabled để FE gắn nhãn;
  - xóa mềm  → không còn là đơn vị (đó mới là ý nghĩa của "xóa").
Khóa vẫn chặn ĐĂNG NHẬP như cũ — việc đó nằm ở ensure_account_available, không phải ở đây.
"""
from bson import ObjectId
import pytest

from app.dashboard import scope


class _Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, _limit):
        return self.rows


class _Users:
    def __init__(self, rows):
        self.rows = rows
        self.last_query = None

    def find(self, query, _projection):
        self.last_query = query
        return _Cursor([r for r in self.rows if _matches(r, query)])


def _matches(row, query):
    for field, expected in query.items():
        value = row.get(field)
        if isinstance(expected, dict):
            if "$in" in expected and value not in expected["$in"]:
                return False
            if "$ne" in expected and value == expected["$ne"]:
                return False
        elif value != expected:
            return False
    return True


def _acct(username, *, disabled=False, deleted=False, role="commune", xa="Xã A"):
    row = {"_id": ObjectId(), "username": username, "name": username,
           "xa": xa, "tinh": "Tỉnh Lai Châu", "role": role, "access_disabled": disabled}
    if deleted:
        row["deleted_at"] = "2026-09-20T00:00:00+00:00"
    return row


@pytest.fixture()
def rows(monkeypatch):
    data = [
        _acct("hccbinh"),
        _acct("hcckhoa", disabled=True),
        _acct("hccxoa", deleted=True),
        _acct("hcctinh", role="province", xa=None),
    ]
    monkeypatch.setattr(scope, "get_db", lambda: type("Db", (), {"users": _Users(data)})())
    return data


@pytest.mark.asyncio
async def test_don_vi_tam_khoa_van_trong_pham_vi(rows):
    units = await scope._units_matching("Tỉnh Lai Châu")
    names = {u["name"] for u in units}
    assert "hcckhoa" in names, "tạm khóa không được làm mất đơn vị khỏi báo cáo"


@pytest.mark.asyncio
async def test_co_co_accessDisabled_de_FE_gan_nhan(rows):
    units = {u["name"]: u for u in await scope._units_matching("Tỉnh Lai Châu")}
    assert units["hcckhoa"]["accessDisabled"] is True
    assert units["hccbinh"]["accessDisabled"] is False


@pytest.mark.asyncio
async def test_don_vi_da_xoa_mem_bi_loai(rows):
    units = await scope._units_matching("Tỉnh Lai Châu")
    assert "hccxoa" not in {u["name"] for u in units}


@pytest.mark.asyncio
async def test_tai_khoan_tinh_khong_co_xa_van_la_mot_don_vi(rows):
    """Giữ nguyên hành vi có chủ ý: HCC tỉnh không gán xã nhưng vẫn là đơn vị."""
    units = {u["name"]: u for u in await scope._units_matching("Tỉnh Lai Châu")}
    assert units["hcctinh"]["xa"] is None
