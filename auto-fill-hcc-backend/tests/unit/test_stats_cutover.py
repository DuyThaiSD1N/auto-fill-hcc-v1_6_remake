"""Mốc 15/9/2026: trước mốc đếm hồ sơ theo cách cũ, từ mốc đếm hồ sơ ĐÃ NỘP.

Ràng buộc quan trọng nhất: số liệu các kỳ ĐÃ XUẤT EXCEL NỘP TỈNH phải bất động. Vì vậy khoảng
nằm trọn trước mốc bắt buộc trả đúng kết quả của app/traces/repo.py, không thêm bớt gì.

ĐỪNG nhầm với mốc 14/9/2026 của quy tắc "chứng thực bản sao đa tab = 1 hồ sơ" — mốc đó sớm
hơn một ngày và nằm gọn trong cách đếm cũ (xem tests/unit/test_chung_thuc_mot_ho_so.py).
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.stats import cutover

CUTOVER = cutover.SUBMITTED_COUNT_FROM
BEFORE = CUTOVER - timedelta(days=3)
AFTER = CUTOVER + timedelta(days=2)


def _old_stats(count: int, *, estimated: int, requests: int = 0) -> dict:
    """Hình dạng trả về của traces_repo.stats_by_user_ids (rút gọn phần đang kiểm)."""
    return {
        "wards": [{
            "userId": "u1",
            "name": "Phường Tân Phong",
            "total": count,
            "exact": count - estimated,
            "estimated": estimated,
            "requests": requests,
            "procedures": [{
                "key": "chung-thuc-ban-sao",
                "label": "Chứng thực bản sao",
                "count": count,
                "exact": count - estimated,
                "estimated": estimated,
                "requests": requests,
            }],
        }],
        "procedures": [{
            "key": "chung-thuc-ban-sao", "label": "Chứng thực bản sao",
            "count": count, "requests": requests, "exact": count - estimated, "estimated": estimated,
        }],
        "totalDossiers": count,
        "exactDossiers": count - estimated,
        "estimatedDossiers": estimated,
        "dataQuality": "estimated" if estimated == count else "mixed",
        "totalRequests": requests,
        "estimatedRequests": 0,
        "uniqueDocuments": 7,
        "totalDocumentUses": 9,
        "reusedDocumentUses": 2,
        "documentDataQuality": "exact",
    }


@pytest.fixture()
def spy(monkeypatch):
    """Bắt mọi lần gọi hai nguồn, kèm khoảng ngày từng lần — mấu chốt của việc cắt mốc."""
    calls: dict[str, list[tuple[datetime, datetime]]] = {"old": [], "new": [], "old_daily": [], "new_daily": []}
    answers: dict[str, object] = {"old": _old_stats(0, estimated=0), "new": [], "old_daily": [], "new_daily": []}

    async def fake_old(*, user_ids, date_from, date_to, experience="autofill"):
        calls["old"].append((date_from, date_to))
        return answers["old"]

    async def fake_new(*, user_ids, date_from, date_to, experience="autofill"):
        calls["new"].append((date_from, date_to))
        return answers["new"]

    async def fake_old_daily(*, user_ids, date_from, date_to, experience="autofill"):
        calls["old_daily"].append((date_from, date_to))
        return answers["old_daily"]

    async def fake_new_daily(*, user_ids, date_from, date_to, experience="autofill"):
        calls["new_daily"].append((date_from, date_to))
        return answers["new_daily"]

    monkeypatch.setattr(cutover.traces_repo, "stats_by_user_ids", fake_old)
    monkeypatch.setattr(cutover.traces_repo, "daily_dossier_counts_by_user_ids", fake_old_daily)
    monkeypatch.setattr(cutover.dossiers_stats, "submitted_counts", fake_new)
    monkeypatch.setattr(cutover.dossiers_stats, "submitted_daily_counts", fake_new_daily)
    return calls, answers


async def _stats(date_from, date_to):
    return await cutover.dossier_stats(user_ids=["u1"], date_from=date_from, date_to=date_to)


async def test_khoang_truoc_moc_tra_nguyen_van_cach_cu(spy):
    """Kỳ đã nộp tỉnh mở lại phải ra ĐÚNG con số cũ — không được đụng vào, không được đếm bù."""
    calls, answers = spy
    answers["old"] = _old_stats(12, estimated=12, requests=30)
    result = await _stats(BEFORE, CUTOVER)
    assert result is answers["old"], "trước mốc phải trả thẳng kết quả cách cũ, không dựng lại"
    assert calls["new"] == [], "trước mốc tuyệt đối không được chạm vào cách đếm mới"


async def test_khoang_sau_moc_dem_ho_so_da_nop(spy):
    calls, answers = spy
    answers["old"] = _old_stats(99, estimated=99, requests=30)  # số hồ sơ của cách cũ phải bị BỎ
    answers["new"] = [{
        "userId": "u1", "procedure": "chung-thuc-ban-sao",
        "label": "Chứng thực bản sao", "name": "Phường Tân Phong", "count": 4,
    }]
    result = await _stats(CUTOVER, AFTER)
    assert result["totalDossiers"] == 4
    assert calls["old_daily"] == [], "sau mốc không cần cách cũ để đếm hồ sơ"
    assert result["totalRequests"] == 30, "số LƯỢT xử lý vẫn lấy từ trace, không đổi theo mốc"
    assert result["uniqueDocuments"] == 7, "thống kê tài liệu dùng lại giữ nguyên"
    assert result["dataQuality"] == "exact", "đếm theo mốc nộp thật thì không còn ước tính"


async def test_khoang_vat_qua_moc_cong_hai_nua(spy):
    """Nửa cũ phải chạy LẠI trên đúng [đầu khoảng, mốc) — không mượn số của cả khoảng."""
    calls, answers = spy
    answers["old"] = _old_stats(5, estimated=5, requests=30)
    answers["new"] = [{
        "userId": "u1", "procedure": "chung-thuc-ban-sao",
        "label": "Chứng thực bản sao", "name": "Phường Tân Phong", "count": 3,
    }]
    result = await _stats(BEFORE, AFTER)
    assert result["totalDossiers"] == 8, "5 (trước mốc) + 3 (đã nộp, từ mốc)"
    assert (BEFORE, CUTOVER) in calls["old"], "nửa cũ phải bị chặn đúng tại mốc"
    assert calls["new"] == [(CUTOVER, AFTER)], "nửa mới bắt đầu đúng tại mốc"
    assert result["dataQuality"] == "mixed", "nửa ước tính + nửa chính xác = mixed"
    assert result["estimatedDossiers"] == 5 and result["exactDossiers"] == 3


async def test_don_vi_co_luot_nhung_chua_nop_van_hien_dong(spy):
    """Bảng 'Theo đơn vị' phải thấy đơn vị đang làm mà chưa nộp được hồ sơ nào."""
    _calls, answers = spy
    answers["old"] = _old_stats(0, estimated=0, requests=12)
    answers["new"] = []
    result = await _stats(CUTOVER, AFTER)
    assert [ward["userId"] for ward in result["wards"]] == ["u1"]
    assert result["wards"][0]["requests"] == 12
    assert result["wards"][0]["total"] == 0


async def test_bieu_do_theo_ngay_noi_hai_nua(spy):
    calls, answers = spy
    answers["old_daily"] = [{"userId": "u1", "date": "2026-09-12", "count": 2}]
    answers["new_daily"] = [{"userId": "u1", "date": "2026-09-15", "count": 3}]
    rows = await cutover.daily_dossier_counts(user_ids=["u1"], date_from=BEFORE, date_to=AFTER)
    assert rows == [
        {"userId": "u1", "date": "2026-09-12", "count": 2},
        {"userId": "u1", "date": "2026-09-15", "count": 3},
    ]
    assert calls["old_daily"] == [(BEFORE, CUTOVER)]
    assert calls["new_daily"] == [(CUTOVER, AFTER)]


async def test_bieu_do_truoc_moc_khong_goi_nguon_moi(spy):
    calls, answers = spy
    answers["old_daily"] = [{"userId": "u1", "date": "2026-09-12", "count": 2}]
    rows = await cutover.daily_dossier_counts(user_ids=["u1"], date_from=BEFORE, date_to=CUTOVER)
    assert rows == [{"userId": "u1", "date": "2026-09-12", "count": 2}]
    assert calls["new_daily"] == []


@pytest.fixture()
def admin_spy(monkeypatch):
    """Thống kê quản trị: phạm vi là VAI TRÒ tài khoản, hai đầu khoảng có thể bỏ trống."""
    calls: dict[str, list] = {"old": [], "new": [], "scope_ids": []}
    answers: dict[str, object] = {"old": _old_stats(0, estimated=0), "new": []}

    async def fake_stats(*, date_from, date_to, scope="all", experience="autofill"):
        calls["old"].append((date_from, date_to, scope, experience))
        return answers["old"]

    async def fake_scope_ids(scope):
        calls["scope_ids"].append(scope)
        return ["official-1"]

    async def fake_new(*, user_ids, date_from, date_to, experience="autofill"):
        calls["new"].append((user_ids, date_from, date_to, experience))
        return answers["new"]

    monkeypatch.setattr(cutover.traces_repo, "stats", fake_stats)
    monkeypatch.setattr(cutover.traces_repo, "stats_scope_user_ids", fake_scope_ids)
    monkeypatch.setattr(cutover.dossiers_stats, "submitted_counts", fake_new)
    return calls, answers


async def test_quan_tri_truoc_moc_khong_doi(admin_spy):
    calls, answers = admin_spy
    answers["old"] = _old_stats(8, estimated=8, requests=20)
    result = await cutover.admin_stats(date_from=BEFORE, date_to=CUTOVER, scope="all")
    assert result is answers["old"]
    assert calls["new"] == []


async def test_quan_tri_pham_vi_all_khong_gioi_han_tai_khoan(admin_spy):
    """scope 'all' phải truyền None, KHÔNG phải danh sách rỗng — rỗng nghĩa là không đếm gì."""
    calls, answers = admin_spy
    answers["new"] = [{"userId": "u1", "procedure": "p1", "label": "P1", "name": "Phường A", "count": 6}]
    result = await cutover.admin_stats(date_from=CUTOVER, date_to=AFTER, scope="all")
    assert calls["new"][0][0] is None
    assert calls["scope_ids"] == [], "scope 'all' thì khỏi phải liệt kê tài khoản"
    assert result["totalDossiers"] == 6


async def test_quan_tri_pham_vi_official_lay_dung_bo_loc_vai_tro(admin_spy):
    """Hai bên mốc phải cùng một phạm vi tài khoản, nếu không số liệu là của hai tập khác nhau."""
    calls, _answers = admin_spy
    await cutover.admin_stats(date_from=CUTOVER, date_to=AFTER, scope="official")
    assert calls["scope_ids"] == ["official"]
    assert calls["new"][0][0] == ["official-1"]


async def test_quan_tri_bo_trong_khoang_van_ap_moc(admin_spy):
    """'Xem tất cả' (không chọn ngày) vẫn phải cắt tại mốc, không rơi hết về cách cũ."""
    calls, _answers = admin_spy
    await cutover.admin_stats(date_from=None, date_to=None, scope="all")
    assert (None, CUTOVER, "all", "autofill") in calls["old"], "nửa cũ chặn tại mốc"
    assert calls["new"][0][1] == CUTOVER


async def test_quan_tri_giu_lai_cot_vai_tro_cua_don_vi(admin_spy):
    """`role` do màn quản trị gắn thêm vào từng dòng đơn vị — dựng lại không được làm rơi."""
    _calls, answers = admin_spy
    stats = _old_stats(3, estimated=3, requests=9)
    stats["wards"][0]["role"] = "hcc_xa"
    answers["old"] = stats
    result = await cutover.admin_stats(date_from=BEFORE, date_to=AFTER, scope="all")
    assert result["wards"][0]["role"] == "hcc_xa"


@pytest.mark.parametrize(("date_from", "date_to", "mode"), [
    (BEFORE, CUTOVER, "legacy"),
    (CUTOVER, AFTER, "submitted"),
    (BEFORE, AFTER, "mixed"),
])
def test_bao_dung_cach_dem_cho_man_hinh(date_from, date_to, mode):
    """Bộ lọc 'Tất cả' luôn là mixed — màn hình phải nói ra, không thì cán bộ tưởng số tụt."""
    info = cutover.counting_info(date_from, date_to)
    assert info["mode"] == mode
    assert info["submittedFrom"] == "2026-09-15"


def test_moc_doi_cach_dem_la_00h00_ngay_15_9_gio_viet_nam():
    """KHÁC mốc 14/9 của quy tắc "chứng thực đa tab = 1 hồ sơ" — hai mốc cố ý lệch một ngày."""
    assert CUTOVER == datetime(2026, 9, 14, 17, 0, tzinfo=timezone.utc), "15/9/2026 00:00 giờ VN"
