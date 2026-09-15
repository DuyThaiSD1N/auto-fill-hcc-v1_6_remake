"""Chứng thực bản sao tách nhiều tab: từ 14/9/2026 chỉ còn tính MỘT hồ sơ.

Mốc này SỚM HƠN MỘT NGÀY so với mốc 15/9 đổi hẳn sang đếm hồ sơ đã nộp (app/stats/cutover.py),
nên ngày 14/9 vẫn chạy cách đếm cũ nhưng đã áp quy tắc mới — đó là lý do phải vá thẳng vào
pipeline trace chứ không thể để cách đếm mới lo hộ.

Ràng buộc kèm theo: đến hết 13/9 số liệu phải y nguyên (Excel đã nộp tỉnh), nên quy tắc bắt
buộc có CHỐT NGÀY chứ không áp cho toàn bộ lịch sử.
"""
from datetime import datetime, timezone

from app.traces.repo import (
    _CERT_SINGLE_DOSSIER_FROM,
    _CERT_SINGLE_DOSSIER_PROCEDURES,
    _daily_stats_pipeline,
    _stats_pipeline,
)


def _collapse_stage(pipeline):
    """Stage thu mảng hồ sơ của lượt tách về đúng một phần tử."""
    for stage in pipeline:
        expr = stage.get("$set", {}).get("_stats_dossier_ids")
        if isinstance(expr, dict) and "$cond" in expr and "$slice" in str(expr):
            return expr["$cond"]
    return None


def test_moc_la_00h00_ngay_14_9_gio_viet_nam():
    assert _CERT_SINGLE_DOSSIER_FROM == datetime(2026, 9, 13, 17, 0, tzinfo=timezone.utc)


def test_chi_ap_cho_chung_thuc_ban_sao():
    """Chứng thực CHỮ KÝ mỗi văn bản vẫn là một hồ sơ — không được gộp lây."""
    assert _CERT_SINGLE_DOSSIER_PROCEDURES == ("chung-thuc-ban-sao",)
    assert "chung-thuc-chu-ky" not in _CERT_SINGLE_DOSSIER_PROCEDURES


def test_thu_mang_ho_so_ve_mot_phan_tu():
    cond = _collapse_stage(_stats_pipeline({}))
    assert cond is not None, "phải có stage gom lượt tách về một hồ sơ"
    test, when_true, when_false = cond
    assert when_true == {"$slice": ["$_stats_dossier_ids", 1]}
    assert when_false == "$_stats_dossier_ids", "ngoài phạm vi thì giữ NGUYÊN cách cũ"
    assert {"$in": ["$procedure", ["chung-thuc-ban-sao"]]} in test["$and"]


def test_co_chot_ngay_de_khong_sua_nguoc_lich_su():
    cond = _collapse_stage(_stats_pipeline({}))
    gate = next(item for item in cond[0]["$and"] if "$gte" in item)
    assert gate["$gte"][1] == _CERT_SINGLE_DOSSIER_FROM


def test_trace_thieu_ngay_thi_giu_so_cu():
    """Không rõ thời điểm thì thà giữ số cũ còn hơn sửa ngược lịch sử."""
    cond = _collapse_stage(_stats_pipeline({}))
    gate = next(item for item in cond[0]["$and"] if "$gte" in item)
    fallback = gate["$gte"][0]["$ifNull"][1]
    assert fallback < _CERT_SINGLE_DOSSIER_FROM, "created_at rỗng phải rơi về phía TRƯỚC mốc"


def test_giu_phan_tu_dau_chu_khong_dung_id_moi():
    """Hai lượt đính kèm của CÙNG một phiên phải ra cùng id thì $group mới khử trùng được.

    Dựng id mới theo request_id là mỗi lượt lại thành một hồ sơ — đúng thứ đang phải sửa.
    """
    cond = _collapse_stage(_stats_pipeline({}))
    assert "request_id" not in str(cond[1]), "không được dựng id mới từ request_id"


def test_bieu_do_theo_ngay_cung_ap_quy_tac():
    """Cột theo ngày và KPI tổng phải cùng một cách đếm, không thì nhìn vào thấy vênh."""
    assert _collapse_stage(_daily_stats_pipeline({})) is not None
