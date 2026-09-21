"""Ba chốt an toàn của trang Quản lý tài khoản.

1. KHÔNG tự đổi vai trò của chính mình. require_admin đọc lại user từ DB mỗi request nên tự
   hạ quyền là mất trang quản trị NGAY, không đợi token hết hạn — tự khóa mình ra ngoài y hệt
   trường hợp CANNOT_DISABLE_SELF đã chặn từ trước.
2. KHÔNG để hệ thống hết quản trị viên. Mất hết admin thì phải chạy scripts/seed_user.py trên
   server mới cứu được.
3. Xóa tài khoản là xóa MỀM. Trước đây `delete_one` bốc thẳng document khỏi Mongo, kéo theo
   đơn vị đó biến khỏi bảng báo cáo và không có đường quay lại.
"""
from bson import ObjectId
import pytest

from app.auth.access_control import (
    DELETED_MESSAGE,
    MAINTENANCE_MESSAGE,
    ensure_account_available,
)
from app.core.errors import AppError
from app.users import service
from app.users.schemas import UserUpdate


class _Users:
    """Giả lập tối thiểu: khớp _id, và đếm được count_documents cho chốt admin cuối."""

    def __init__(self, users: list[dict]):
        self.users = users
        self.last_update = None

    def _find(self, query):
        oid = query.get("_id")
        if isinstance(oid, dict):  # {"$ne": ...} trong count_documents
            return None
        return next((u for u in self.users if u["_id"] == oid), None)

    async def find_one(self, query):
        return self._find(query)

    async def find_one_and_update(self, query, update, return_document):
        user = self._find(query)
        if user is None or not _matches(user, query):
            return None
        self.last_update = update
        user.update(update.get("$set", {}))
        for field in update.get("$unset", {}):
            user.pop(field, None)
        return dict(user)

    async def update_one(self, query, update):
        user = self._find(query)
        matched = user is not None and _matches(user, query)
        if matched:
            self.last_update = update
            user.update(update.get("$set", {}))
        return type("Result", (), {"matched_count": 1 if matched else 0})()

    async def count_documents(self, query):
        return sum(1 for u in self.users if _matches(u, query))


def _matches(user: dict, query: dict) -> bool:
    for field, expected in query.items():
        value = user.get(field)
        if isinstance(expected, dict):
            if "$ne" in expected and value == expected["$ne"]:
                return False
            if "$in" in expected and value not in expected["$in"]:
                return False
        elif field == "_id":
            if value != expected:
                return False
        elif value != expected:
            return False
    return True


class _RefreshTokens:
    def __init__(self):
        self.calls = []

    async def update_many(self, query, update):
        self.calls.append((query, update))
        return type("Result", (), {"modified_count": 0})()


class _Db:
    def __init__(self, users: list[dict]):
        self.users = _Users(users)
        self.refresh_tokens = _RefreshTokens()


def _admin(username="admin1", **extra) -> dict:
    return {"_id": ObjectId(), "username": username, "role": "admin",
            "access_disabled": False, **extra}


def _commune(**extra) -> dict:
    return {"_id": ObjectId(), "username": "hccnghiahung", "role": "commune",
            "access_disabled": False, **extra}


@pytest.fixture()
def db_factory(monkeypatch):
    def make(users: list[dict]) -> _Db:
        db = _Db(users)
        monkeypatch.setattr(service, "get_db", lambda: db)
        return db
    return make


# ── 1. Tự đổi vai trò ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_khong_tu_doi_vai_tro_cua_chinh_minh(db_factory):
    me = _admin()
    db_factory([me, _admin("admin2")])
    with pytest.raises(AppError) as err:
        await service.update_user(str(me["_id"]), UserUpdate(role="user"), str(me["_id"]))
    assert err.value.error == "CANNOT_CHANGE_OWN_ROLE"
    assert me["role"] == "admin", "không được ghi gì khi đã chặn"


@pytest.mark.asyncio
async def test_gui_lai_DUNG_vai_tro_cu_thi_khong_bi_chan(db_factory):
    """FE gửi nguyên form nên `role` luôn có mặt. Chặn cả khi không đổi gì là admin không sửa
    nổi tên hiển thị của chính mình."""
    me = _admin()
    db_factory([me])
    result = await service.update_user(
        str(me["_id"]), UserUpdate(name="Quản trị hệ thống", role="admin"), str(me["_id"])
    )
    assert result["name"] == "Quản trị hệ thống"


@pytest.mark.asyncio
async def test_doi_vai_tro_NGUOI_KHAC_van_binh_thuong(db_factory):
    me, other = _admin(), _commune()
    db_factory([me, other])
    result = await service.update_user(str(other["_id"]), UserUpdate(role="province"), str(me["_id"]))
    assert result["role"] == "province"


# ── 2. Quản trị viên cuối cùng ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_con_hai_admin_thi_ha_mot_cai_van_duoc(db_factory):
    """Chốt phải đếm số admin CÒN LẠI sau thao tác, không phải tổng số admin."""
    me, other = _admin("admin1"), _admin("admin2")
    db_factory([me, other])
    result = await service.update_user(str(other["_id"]), UserUpdate(role="user"), str(me["_id"]))
    assert result["role"] == "user"


@pytest.mark.asyncio
async def test_chan_khi_that_su_chi_con_mot_admin(db_factory):
    """admin2 bị tạm khóa → không dùng được → admin1 là người cuối cùng thật sự."""
    me, locked = _admin("admin1"), _admin("admin2", access_disabled=True)
    db_factory([me, locked])
    for body in (UserUpdate(role="user"), UserUpdate(access_disabled=True)):
        with pytest.raises(AppError) as err:
            await service.update_user(str(me["_id"]), body, str(ObjectId()))
        assert err.value.error in {"LAST_ADMIN", "CANNOT_CHANGE_OWN_ROLE"}


@pytest.mark.asyncio
async def test_khong_xoa_duoc_admin_cuoi_cung(db_factory):
    last = _admin()
    db_factory([last, _commune()])
    with pytest.raises(AppError) as err:
        await service.delete_user(str(last["_id"]), str(ObjectId()))
    assert err.value.error == "LAST_ADMIN"
    assert last.get("deleted_at") is None


@pytest.mark.asyncio
async def test_admin_bi_khoa_khong_tinh_la_admin_con_lai(db_factory):
    """Đếm phải loại tài khoản đang tạm khóa: chúng không đăng nhập được nên không cứu được ai."""
    target, locked = _admin("admin1"), _admin("admin2", access_disabled=True)
    db_factory([target, locked])
    with pytest.raises(AppError) as err:
        await service.delete_user(str(target["_id"]), str(ObjectId()))
    assert err.value.error == "LAST_ADMIN"


# ── 3. Xóa mềm ───────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_xoa_la_dong_dau_chu_khong_boc_khoi_mongo(db_factory):
    target = _commune()
    actor = str(ObjectId())
    db = db_factory([_admin(), target])
    await service.delete_user(str(target["_id"]), actor)
    assert target in db.users.users, "document phải còn nguyên trong Mongo"
    assert target["deleted_at"] is not None
    assert target["deleted_by"] == actor


@pytest.mark.asyncio
async def test_xoa_thu_hoi_refresh_token(db_factory):
    """Access token đang sống bị ensure_account_available chặn; refresh token phải thu hồi,
    nếu không phiên cũ tự gia hạn được vô hạn."""
    target = _commune()
    db = db_factory([_admin(), target])
    await service.delete_user(str(target["_id"]), str(ObjectId()))
    query, update = db.refresh_tokens.calls[0]
    assert query == {"user_id": str(target["_id"]), "revoked_at": None}
    assert update["$set"]["revoked_at"] is not None


@pytest.mark.asyncio
async def test_bam_xoa_hai_lan_khong_bao_loi(db_factory):
    target = _commune()
    db_factory([_admin(), target])
    await service.delete_user(str(target["_id"]), str(ObjectId()))
    await service.delete_user(str(target["_id"]), str(ObjectId()))  # không được ném


@pytest.mark.asyncio
async def test_tai_khoan_da_xoa_khong_sua_duoc(db_factory):
    target = _commune(deleted_at=service._now())
    db_factory([_admin(), target])
    with pytest.raises(AppError) as err:
        await service.update_user(str(target["_id"]), UserUpdate(name="X"), str(ObjectId()))
    assert err.value.error == "USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_khoi_phuc_go_dau_xoa(db_factory):
    target = _commune(deleted_at=service._now(), deleted_by="ai-do")
    db_factory([target])
    result = await service.restore_user(str(target["_id"]))
    assert result["deleted_at"] is None
    assert "deleted_at" not in target and "deleted_by" not in target


@pytest.mark.asyncio
async def test_khong_khoi_phuc_tai_khoan_chua_bi_xoa(db_factory):
    target = _commune()
    db_factory([target])
    with pytest.raises(AppError):
        await service.restore_user(str(target["_id"]))


# ── Chốt đăng nhập: xóa mềm phải CHẶN, không chỉ giấu đi ─────────────────────────────────

def test_tai_khoan_da_xoa_khong_dang_nhap_duoc():
    """ensure_account_available là cổng chung của đăng nhập / refresh / require_auth / WS voice.
    Thiếu kiểm ở đây thì tài khoản đã xóa vẫn dùng được như chưa có chuyện gì."""
    with pytest.raises(AppError) as err:
        ensure_account_available({"deleted_at": service._now()})
    assert err.value.message == DELETED_MESSAGE

    with pytest.raises(AppError) as err:
        ensure_account_available({"access_disabled": True})
    assert err.value.message == MAINTENANCE_MESSAGE

    ensure_account_available({})  # tài khoản cũ chưa có trường deleted_at → vẫn vào được
    ensure_account_available({"deleted_at": None, "access_disabled": False})
